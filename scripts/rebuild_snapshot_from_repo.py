"""Rebuild the two missing snapshot CSVs from files already in this repository.

Why this exists
---------------
``radar/data.py`` reads three files out of ``data/`` when there are no Azure SQL
credentials (which is the case on Streamlit Community Cloud, and on any laptop
without a ``.env``)::

    data/snapshot_opportunities.csv     <- present
    data/snapshot_signals.csv           <- MISSING
    data/snapshot_links.csv             <- MISSING

Because the last two are missing, the deployed dashboard silently loses:

* the whole **Signal explorer** page ("No signals available"),
* the **Supporting signals** evidence table on the detail page,
* every **country / market** value, which ``attach_countries()`` rolls up from
  signals through the join table and otherwise fills with "Unknown".

The proper fix is ``scripts/export_snapshot.py`` run against the live database.
This script is the offline stand-in: it rebuilds both files from data that is
**already committed here**, so nothing is invented.

    signals  <- tmp/signals.csv          (619 real rows, minus the embedding column)
    links    <- the `signal_ids` column already inside snapshot_opportunities.csv

Both inputs are checked before anything is written, and the run prints a
reconciliation so you can see that every declared link resolved.

    python scripts/rebuild_snapshot_from_repo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

SOURCE_SIGNALS = PROJECT_ROOT / "tmp" / "signals.csv"
SOURCE_OPPORTUNITIES = DATA_DIR / "snapshot_opportunities.csv"

OUT_SIGNALS = DATA_DIR / "snapshot_signals.csv"
OUT_LINKS = DATA_DIR / "snapshot_links.csv"

# tmp/signals.csv was exported through a tool that wrote Windows-1252, not UTF-8
# (byte 0x92 where a right single quote belongs -- "BIPT's" arrives as "BIPT\x92s").
# Read it as cp1252 and write UTF-8, so the mojibake stops here instead of being
# copied into data/.
SOURCE_ENCODING = "cp1252"

# Never exported: the 1536-float embedding. It is only used by the clustering
# step, which runs against the live database, and it is what makes tmp/signals.csv
# a multi-megabyte file.
DROP_COLUMNS = ["embedding"]


def main() -> None:
    for path in (SOURCE_SIGNALS, SOURCE_OPPORTUNITIES):
        if not path.exists():
            sys.exit(f"Missing input: {path.relative_to(PROJECT_ROOT)}")

    # ---------------------------------------------------------------- signals
    signals = pd.read_csv(SOURCE_SIGNALS, encoding=SOURCE_ENCODING)
    signals = signals.drop(columns=DROP_COLUMNS, errors="ignore")

    # The agent writes the string "NULL" rather than an empty cell for an
    # unclassified signal_type. Leave the value alone but make it a real blank so
    # data.py's own "Unknown" substitution takes over and the charts do not grow a
    # category literally called NULL.
    if "signal_type" in signals.columns:
        signals["signal_type"] = signals["signal_type"].replace("NULL", pd.NA)

    # ------------------------------------------------------------------ links
    opportunities = pd.read_csv(SOURCE_OPPORTUNITIES)
    if "signal_ids" not in opportunities.columns:
        sys.exit(
            "snapshot_opportunities.csv has no `signal_ids` column, so the join "
            "table cannot be rebuilt offline. Run scripts/export_snapshot.py "
            "against the live database instead."
        )

    known_ids = set(signals["id"].astype(int))
    rows: list[dict[str, int]] = []
    unresolved: list[tuple[int, int]] = []

    for _, opportunity in opportunities.iterrows():
        opportunity_id = int(opportunity["id"])
        for raw in str(opportunity["signal_ids"]).split(","):
            raw = raw.strip()
            if not raw:
                continue
            signal_id = int(raw)
            if signal_id in known_ids:
                rows.append(
                    {"opportunity_space_id": opportunity_id, "signal_id": signal_id}
                )
            else:
                unresolved.append((opportunity_id, signal_id))

    links = pd.DataFrame(rows, columns=["opportunity_space_id", "signal_id"])

    # ------------------------------------------------------------------ write
    DATA_DIR.mkdir(exist_ok=True)
    signals.to_csv(OUT_SIGNALS, index=False, encoding="utf-8")
    links.to_csv(OUT_LINKS, index=False, encoding="utf-8")

    print(f"  wrote {OUT_SIGNALS.name:<26} {len(signals):>5} rows")
    print(f"  wrote {OUT_LINKS.name:<26} {len(links):>5} rows")
    print(
        f"\n  {len(links)} of {len(links) + len(unresolved)} declared links resolved "
        f"against {len(signals)} signals."
    )
    if unresolved:
        print("  Unresolved (signal not present in tmp/signals.csv):")
        for opportunity_id, signal_id in unresolved:
            print(f"    opportunity {opportunity_id} -> signal {signal_id}")

    print(
        "\nThis is a stand-in built from files already in the repo. Once the "
        "database is reachable, prefer:\n    python scripts/export_snapshot.py"
    )


if __name__ == "__main__":
    main()
