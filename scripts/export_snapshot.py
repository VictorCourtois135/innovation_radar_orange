"""Export a CSV snapshot of the database for the dashboard to fall back on.

Why this exists:

The dashboard reads Azure SQL when it can. It cannot always:

* **Streamlit Community Cloud cannot install the Microsoft ODBC driver**, which
  `pyodbc` needs, and its outbound IPs are not fixed, so letting it through the
  Azure SQL firewall would mean opening a very wide range on a shared account.
* Azure SQL serverless **auto-pauses**, so the first request after a quiet
  period can fail or take a minute.
* A conference-room network can simply be blocked.

Committing a snapshot means the deployed app always has something to show, and
a demo never dies in front of a client. Run this after each pipeline run, then
commit the changed CSVs.

    python scripts/export_snapshot.py

Requires the same environment variables as the rest of the pipeline:
SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data"

REQUIRED = ["SQL_SERVER", "SQL_DATABASE", "SQL_USER", "SQL_PASSWORD"]

# Never exported: the embedding column. It is 1536 floats per row, it is only
# needed by the clustering step which runs against the live database, and it
# would make the committed CSV enormous for no benefit.
SIGNAL_COLUMNS = [
    "id", "source_url", "source_name", "title", "publication_date",
    "targeted_vertical", "country", "summary", "raw_excerpt",
    "date_of_scrape", "signal_type",
]


def connection_string() -> str:
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        sys.exit(
            "Missing environment variables: " + ", ".join(missing) +
            "\nPut them in a .env file in the project root, or export them."
        )
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{os.environ['SQL_SERVER']},1433;"
        f"DATABASE={os.environ['SQL_DATABASE']};"
        f"UID={os.environ['SQL_USER']};PWD={os.environ['SQL_PASSWORD']};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Connecting to Azure SQL (a paused database can take up to a minute)...")
    conn = pyodbc.connect(connection_string(), timeout=60)

    try:
        opp = pd.read_sql("SELECT * FROM opportunity_spaces", conn)

        try:
            columns = ", ".join(SIGNAL_COLUMNS)
            sig = pd.read_sql(f"SELECT {columns} FROM signals", conn)
        except Exception:
            print("  (falling back to SELECT * on signals, schema differs)")
            sig = pd.read_sql("SELECT * FROM signals", conn)
            sig = sig.drop(columns=["embedding"], errors="ignore")

        link = pd.read_sql("SELECT * FROM opportunity_space_signals", conn)
    finally:
        conn.close()

    # Belt and braces: make sure no embedding column slipped through.
    for frame in (opp, sig, link):
        frame.drop(columns=["embedding"], errors="ignore", inplace=True)

    targets = [
        ("snapshot_opportunities.csv", opp),
        ("snapshot_signals.csv", sig),
        ("snapshot_links.csv", link),
    ]
    for filename, frame in targets:
        path = OUTPUT_DIR / filename
        frame.to_csv(path, index=False)
        size_kb = path.stat().st_size / 1024
        print(f"  wrote {filename:<28} {len(frame):>5} rows  ({size_kb:,.0f} KB)")

    print(
        "\nDone. Commit the files in data/ so the deployed app picks them up:\n"
        "    git add data/ && git commit -m 'Refresh dashboard snapshot'"
    )


if __name__ == "__main__":
    main()
