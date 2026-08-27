"""
Standalone script: for every opportunity_space that doesn't yet have a
detailed_summary, gathers the summaries of its linked signals and asks
GPT-5-mini directly (NOT through the Foundry agent) to synthesize one
coherent narrative paragraph. Updates the row in place.

Can be re-run any time -- only touches rows where detailed_summary IS NULL,
so it's safe to run repeatedly and cheap to re-run after adding new signals
to an existing opportunity space (just clear that row's detailed_summary
first if you want it regenerated).

Requires the same environment variables as run_agent_and_save.py:
  SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT
"""

import os
import time
import pyodbc
import requests
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.environ["SQL_SERVER"]
SQL_DATABASE = os.environ["SQL_DATABASE"]
SQL_USER = os.environ["SQL_USER"]
SQL_PASSWORD = os.environ["SQL_PASSWORD"]
SQL_CONNECTION_TIMEOUT= 60

SQL_CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{SQL_SERVER},1433;"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout={SQL_CONNECTION_TIMEOUT};"
)

AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = os.environ["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")


def generate_detailed_summary(vertical: str, use_case: str, technology: str,
                               signal_summaries: list[str]) -> str:
    combined = "\n\n".join(f"- {s}" for s in signal_summaries)

    prompt = f"""You are writing the main descriptive overview for a business-facing innovation
opportunity card. The opportunity is: {vertical} / {use_case} / {technology}.

Here are the summaries of the underlying signals that informed this opportunity:
{combined}

Write ONE coherent, flowing narrative paragraph (5-8 sentences) that synthesizes all of this into
a single self-contained story. Do NOT write a list or bullet points. Do NOT just concatenate the
summaries. Cover: what is happening, who is driving it, the scale/timeline, and why it matters in
context. A business reader should understand the full picture from this paragraph alone, without
needing to read the individual source signals.

Respond with ONLY the paragraph text, no title, no markdown, no preamble."""

    chat_url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}"
        f"/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
    )
    response = requests.post(
        chat_url,
        headers={"api-key": AZURE_OPENAI_KEY, "content-type": "application/json"},
        json={"messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def connect_with_retry(max_retries: int = 5, initial_wait: int = 10):
    """Azure SQL serverless (auto-pause) databases can take 30-60s to wake up
    from a paused state on the first connection after inactivity. Retries with
    increasing waits rather than failing immediately on a timeout."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return pyodbc.connect(SQL_CONN_STRING, timeout=60)
        except pyodbc.OperationalError as e:
            last_error = e
            wait = initial_wait * attempt
            print(f"  [DB] Connection attempt {attempt}/{max_retries} failed "
                  f"(database may be waking up from auto-pause). Retrying in {wait}s...")   
            time.sleep(wait)
    raise last_error


def main():
    conn = connect_with_retry()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, vertical, use_case, technology
        FROM opportunity_spaces
        WHERE detailed_summary IS NULL
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} opportunity spaces missing a detailed_summary.\n")

    for opp_id, vertical, use_case, technology in rows:
        cur.execute("""
            SELECT s.summary
            FROM signals s
            JOIN opportunity_space_signals osl ON osl.signal_id = s.id
            WHERE osl.opportunity_space_id = ?
        """, opp_id)
        summaries = [r[0] for r in cur.fetchall() if r[0]]

        if not summaries:
            print(f"[{opp_id}] {vertical}/{use_case}/{technology} -- no linked signals found, skipping.")
            continue

        print(f"[{opp_id}] {vertical}/{use_case}/{technology} -- synthesizing from {len(summaries)} signal(s)...")
        detailed_summary = generate_detailed_summary(vertical, use_case, technology, summaries)

        cur.execute(
            "UPDATE opportunity_spaces SET detailed_summary = ?, updated_at = SYSUTCDATETIME() WHERE id = ?",
            detailed_summary, opp_id,
        )
        conn.commit()
        print(f"  -> saved ({len(detailed_summary)} chars)")

    print(f"\nDone. {len(rows)} opportunity spaces processed.")
    conn.close()


if __name__ == "__main__":
    main()