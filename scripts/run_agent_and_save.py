"""
Calls the Azure AI Foundry agent (with Bing Search grounding), computes an
embedding for each signal, and saves everything into Azure SQL Database.

Before running, set these environment variables:
  SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_EMBEDDING_DEPLOYMENT
  AZURE_AI_PROJECT_ENDPOINT, AZURE_AI_AGENT_NAME
"""

import os
import json
import pyodbc
import requests
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()  # reads variables from a .env file in the same folder, if present

# --- Config -----------------------------------------------------
SQL_SERVER = os.environ["SQL_SERVER"]          # e.g. radar-sql-server.database.windows.net
SQL_DATABASE = os.environ["SQL_DATABASE"]      # e.g. radar
SQL_USER = os.environ["SQL_USER"]
SQL_PASSWORD = os.environ["SQL_PASSWORD"]

SQL_CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{SQL_SERVER},1433;"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
)

AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = os.environ["AZURE_OPENAI_KEY"]
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
AGENT_NAME = os.environ["AZURE_AI_AGENT_NAME"]


# --- Step 1: call the agent and get its structured JSON response ----
def run_agent() -> dict:
    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
    openai_client = project.get_openai_client(agent_name=AGENT_NAME)

    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        conversation=conversation.id,
        input="Lance la recherche.",
    )

    text = response.output_text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


# --- Step 2: compute an embedding for a signal's summary ------------
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-large supports truncated output; Azure SQL VECTOR caps at 1998

def get_embedding(text: str) -> list[float]:
    embed_url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}"
        f"/embeddings?api-version={AZURE_OPENAI_API_VERSION}"
    )
    response = requests.post(
        embed_url,
        headers={"api-key": AZURE_OPENAI_KEY, "content-type": "application/json"},
        json={"input": text, "dimensions": EMBEDDING_DIMENSIONS},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


# --- Step 3: save each signal to Azure SQL Database -------------------
def save_signals(conn, signals: list[dict]):
    cur = conn.cursor()
    for s in signals:
        # Skip if this URL already exists (SQL Server has no native ON CONFLICT)
        cur.execute("SELECT COUNT(*) FROM signals WHERE source_url = ?", s["source_url"])
        if cur.fetchone()[0] > 0:
            continue

        embedding_json = json.dumps(get_embedding(s["summary"]))

        cur.execute(
            """
            INSERT INTO signals (source_url, source_name, title, publication_date, targeted_vertical, country, summary, raw_excerpt, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(1536)))
            """,
            s["source_url"], s["source_name"], s.get("title"), s.get("publication_date"),
            s.get("targeted_vertical"), s.get("country"), s["summary"], s.get("raw_excerpt"), embedding_json,
        )
    conn.commit()


# --- Step 4: deduplicate the table -------------------------------------
def deduplicate_signals(conn):
    cur = conn.cursor()

    # Exact match on source_name + title (safe, always correct)
    cur.execute(
        """
        DELETE s1
        FROM signals s1
        JOIN signals s2
            ON s1.source_name = s2.source_name
            AND s1.title = s2.title
            AND s1.id > s2.id
        """
    )
    removed = cur.rowcount
    conn.commit()

    print(f"Dedup: removed {removed} exact duplicates.")


# --- Main -----------------------------------------------------------
def main():
    print("Calling the agent...")
    result = run_agent()
    signals = result["signals"]
    print(f"Agent returned {len(signals)} signals.")

    conn = pyodbc.connect(SQL_CONN_STRING)
    try:
        save_signals(conn, signals)
        print("Saved to database.")

        print("Running deduplication...")
        deduplicate_signals(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()