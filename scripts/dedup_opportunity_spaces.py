"""
Standalone script: compares ALL opportunity_spaces currently in the database
against each other (not just within a single run) using fuzzy name/why_matters
similarity, and merges genuine duplicates -- keeping the highest-scoring row,
re-pointing its linked signals, and deleting the redundant row(s).

Safe to re-run any time. Run this after every extraction pass to catch
duplicates that slightly different wording let slip past the exact
(vertical, use_case, technology) UNIQUE constraint.
"""

import os
import time
import pyodbc
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.environ["SQL_SERVER"]
SQL_DATABASE = os.environ["SQL_DATABASE"]
SQL_USER = os.environ["SQL_USER"]
SQL_PASSWORD = os.environ["SQL_PASSWORD"]

SQL_CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{SQL_SERVER},1433;"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
)

NAME_SIMILARITY_THRESHOLD = 0.6
WHY_MATTERS_SIMILARITY_THRESHOLD = 0.55


def connect_with_retry(max_retries: int = 5, initial_wait: int = 10):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return pyodbc.connect(SQL_CONN_STRING, timeout=30)
        except pyodbc.OperationalError as e:
            last_error = e
            wait = initial_wait * attempt
            print(f"  [DB] Connection attempt {attempt}/{max_retries} failed. Retrying in {wait}s...")
            time.sleep(wait)
    raise last_error


def find_duplicate_groups(rows: list[dict]) -> list[list[dict]]:
    groups = []
    used = [False] * len(rows)

    for i, a in enumerate(rows):
        if used[i]:
            continue
        group = [a]
        used[i] = True

        for j in range(i + 1, len(rows)):
            if used[j]:
                continue
            b = rows[j]

            name_sim = SequenceMatcher(None, a["name"].lower(), b["name"].lower()).ratio()
            wm_sim = SequenceMatcher(None, (a["why_matters"] or "").lower(),
                                      (b["why_matters"] or "").lower()).ratio()

            if name_sim >= NAME_SIMILARITY_THRESHOLD or wm_sim >= WHY_MATTERS_SIMILARITY_THRESHOLD:
                group.append(b)
                used[j] = True

        if len(group) > 1:
            groups.append(group)

    return groups


def main():
    conn = connect_with_retry()
    cur = conn.cursor()

    cur.execute("SELECT id, name, why_matters, attractiveness_score FROM opportunity_spaces")
    rows = [
        {"id": r[0], "name": r[1], "why_matters": r[2], "attractiveness_score": float(r[3])}
        for r in cur.fetchall()
    ]
    print(f"Loaded {len(rows)} opportunity spaces from the database.\n")

    groups = find_duplicate_groups(rows)
    if not groups:
        print("No cross-run duplicates found.")
        conn.close()
        return

    print(f"Found {len(groups)} duplicate group(s):\n")

    for group in groups:
        winner = max(group, key=lambda o: o["attractiveness_score"])
        losers = [o for o in group if o["id"] != winner["id"]]

        print(f"  KEEP  [{winner['id']}] {winner['name']}  (score={winner['attractiveness_score']})")
        for loser in losers:
            print(f"  MERGE [{loser['id']}] {loser['name']}  (score={loser['attractiveness_score']}) -> into {winner['id']}")

            # Re-point this loser's linked signals to the winner, skipping any
            # that are already linked to the winner (avoid PK violation)
            cur.execute("""
                INSERT INTO opportunity_space_signals (opportunity_space_id, signal_id)
                SELECT ?, signal_id FROM opportunity_space_signals
                WHERE opportunity_space_id = ?
                  AND signal_id NOT IN (
                      SELECT signal_id FROM opportunity_space_signals WHERE opportunity_space_id = ?
                  )
            """, winner["id"], loser["id"], winner["id"])

            # Now safe to remove the loser's own signal links and the row itself
            cur.execute("DELETE FROM opportunity_space_signals WHERE opportunity_space_id = ?", loser["id"])
            cur.execute("DELETE FROM opportunity_spaces WHERE id = ?", loser["id"])

        conn.commit()
        print()

    total_merged = sum(len(g) - 1 for g in groups)
    print(f"Done. {total_merged} duplicate row(s) merged into {len(groups)} winner(s).")
    conn.close()


if __name__ == "__main__":
    main()
