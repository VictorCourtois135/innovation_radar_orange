"""Loading the radar's data.

Design goal: the dashboard must never show a blank screen.

There are two sources, tried in order:

1. **Azure SQL Database**, when credentials are available. This is the live
   data and what you develop against.
2. **A CSV snapshot** committed under ``data/``. This is what makes the app
   deployable to Streamlit Community Cloud (which cannot install the Microsoft
   ODBC driver) and what keeps a demo alive if the database is asleep,
   unreachable, or behind a firewall you cannot open from where the app runs.

Credentials are read from ``st.secrets`` first and environment variables
second, so the same code runs locally with a ``.env`` and in the cloud with
Streamlit secrets. Nothing is read at import time: a missing variable produces
a message in the sidebar, not a crash on startup.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from radar import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = PROJECT_ROOT / config.SNAPSHOT_DIR

REQUIRED_KEYS = ["SQL_SERVER", "SQL_DATABASE", "SQL_USER", "SQL_PASSWORD"]


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
def get_sql_config() -> dict | None:
    """Return the four SQL settings, or None if they are not all available.

    Looks in st.secrets["azure_sql"] first (Streamlit Cloud, or a local
    .streamlit/secrets.toml), then falls back to environment variables, which
    is what a local .env file populates via python-dotenv.
    """
    try:
        section = st.secrets["azure_sql"]
        found = {k: section.get(k) for k in REQUIRED_KEYS}
        if all(found.values()):
            return found
    except Exception:
        # No secrets file at all, or no azure_sql section in it. Both fine.
        pass

    found = {k: os.environ.get(k) for k in REQUIRED_KEYS}
    if all(found.values()):
        return found
    return None


def _connection_string(cfg: dict) -> str:
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{cfg['SQL_SERVER']},1433;"
        f"DATABASE={cfg['SQL_DATABASE']};"
        f"UID={cfg['SQL_USER']};PWD={cfg['SQL_PASSWORD']};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )


# ---------------------------------------------------------------------------
# Azure SQL
# ---------------------------------------------------------------------------
def _connect(cfg: dict, max_retries: int = 3, wait_seconds: int = 15):
    """Connect, retrying because Azure SQL serverless auto-pauses.

    A paused database takes 30-60 seconds to resume, and the first connection
    attempt against it fails rather than blocking. Three tries at 15 seconds
    covers the normal resume window in about 45 seconds. The original version
    of this used five tries with an increasing wait, which could block for two
    and a half minutes with nothing on screen. If it still fails after this,
    the caller falls back to the snapshot rather than leaving the user waiting.
    """
    import pyodbc  # imported here so the app still runs where pyodbc is absent

    conn_str = _connection_string(cfg)
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return pyodbc.connect(conn_str, timeout=30)
        except Exception as exc:  # pyodbc.OperationalError and friends
            last_error = exc
            if attempt < max_retries:
                time.sleep(wait_seconds)
    raise last_error  # type: ignore[misc]


def _load_from_sql(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    conn = _connect(cfg)
    try:
        opp_df = pd.read_sql("SELECT * FROM opportunity_spaces", conn)

        # Explicit column list, not SELECT *. The signals table carries a
        # VECTOR(1536) embedding used by the clustering step and never by the
        # dashboard. On 400+ rows that is over half a million floats pulled
        # across the network on every cache miss, for nothing.
        columns = ", ".join(config.SIGNAL_COLUMNS)
        try:
            sig_df = pd.read_sql(f"SELECT {columns} FROM signals", conn)
        except Exception:
            # Tolerate a schema that is missing one of the optional columns
            # (signal_type and country were added partway through the project).
            sig_df = pd.read_sql("SELECT * FROM signals", conn)
            sig_df = sig_df.drop(columns=["embedding"], errors="ignore")

        link_df = pd.read_sql("SELECT * FROM opportunity_space_signals", conn)
    finally:
        conn.close()
    return opp_df, sig_df, link_df


# ---------------------------------------------------------------------------
# CSV snapshot
# ---------------------------------------------------------------------------
def _read_csv_if_present(name: str) -> pd.DataFrame:
    path = SNAPSHOT_PATH / name
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _load_from_snapshot() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    opp_df = _read_csv_if_present(config.SNAPSHOT_OPPORTUNITIES)
    sig_df = _read_csv_if_present(config.SNAPSHOT_SIGNALS)
    link_df = _read_csv_if_present(config.SNAPSHOT_LINKS)

    # Fall back to the older preview export if no snapshot has been generated.
    if opp_df.empty:
        legacy = PROJECT_ROOT / "opportunity_spaces_preview.csv"
        if legacy.exists():
            opp_df = pd.read_csv(legacy)

    return opp_df, sig_df, link_df


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def _normalise_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Make one dataframe the rest of the app can rely on.

    Column names drifted during the project: the CSV export still says
    ``novelty_momentum`` where the database says ``urgency_time_horizon``, and
    an earlier draft used ``why_now`` and ``capability_gap``. Rather than
    scatter that knowledge across seven page modules, every alias is resolved
    once, here.
    """
    if df.empty:
        return df

    df = df.rename(columns=config.COLUMN_ALIASES).copy()

    # De-duplicate columns that collided during renaming (e.g. a file that has
    # both novelty_momentum and urgency_time_horizon).
    df = df.loc[:, ~df.columns.duplicated()]

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    # `name` is NOT NULL in the schema but the pipeline's INSERT never supplies
    # it, so live rows can come back empty. Rebuild it from its three parts.
    parts = ["vertical", "use_case", "technology"]
    if all(p in df.columns for p in parts):
        rebuilt = (
            df["vertical"].fillna("?") + " × "
            + df["use_case"].fillna("?") + " × "
            + df["technology"].fillna("?")
        )
        if "name" in df.columns:
            df["name"] = df["name"].fillna("").replace("", pd.NA).fillna(rebuilt)
        else:
            df["name"] = rebuilt

    # Same story for `code`, the human-friendly OS-001 identifier.
    if "code" not in df.columns or df["code"].isna().all():
        df["code"] = ["OS-%03d" % int(i) for i in df["id"]]
    else:
        df["code"] = df["code"].fillna(
            pd.Series(["OS-%03d" % int(i) for i in df["id"]], index=df.index)
        )

    # `status` is read by the app but never written by the pipeline.
    if "status" not in df.columns:
        df["status"] = config.STATUS_UNKNOWN
    else:
        df["status"] = df["status"].fillna(config.STATUS_UNKNOWN).replace(
            "", config.STATUS_UNKNOWN
        )

    for col in config.SCORE_COLUMNS + ["attractiveness_score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA

    df["time_horizon"] = df["urgency_time_horizon"].apply(classify_horizon)
    return df


def _normalise_signals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.rename(columns=config.COLUMN_ALIASES).copy()
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.drop(columns=["embedding"], errors="ignore")

    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce")
        df["publication_month"] = df["publication_date"].dt.to_period("M").astype(str)
        df["publication_year"] = df["publication_date"].dt.year

    for col in ("country", "signal_type", "source_name", "targeted_vertical"):
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").replace("", "Unknown")
    return df


def classify_horizon(urgency) -> str:
    """Bucket the 0-100 recency score into Now / Next / Later."""
    if pd.isna(urgency):
        return "Later"
    if urgency >= config.HORIZON_NOW:
        return "Now"
    if urgency >= config.HORIZON_NEXT:
        return "Next"
    return "Later"


def attach_countries(opp_df: pd.DataFrame, sig_df: pd.DataFrame,
                     link_df: pd.DataFrame) -> pd.DataFrame:
    """Roll country up from signals onto each opportunity space.

    `country` exists on `signals` but not on `opportunity_spaces`, so the only
    way to answer "which markets does this opportunity concern" is through the
    join table. An opportunity backed by five signals can legitimately span
    several countries, so this produces a comma-separated list plus a single
    primary country (the most frequent one) for map and filter use.
    """
    if opp_df.empty or sig_df.empty or link_df.empty:
        opp_df = opp_df.copy()
        opp_df["countries"] = "Unknown"
        opp_df["primary_country"] = "Unknown"
        return opp_df
    if "country" not in sig_df.columns:
        opp_df = opp_df.copy()
        opp_df["countries"] = "Unknown"
        opp_df["primary_country"] = "Unknown"
        return opp_df

    merged = link_df.merge(
        sig_df[["id", "country"]], left_on="signal_id", right_on="id", how="left"
    )
    grouped = merged.groupby("opportunity_space_id")["country"]

    countries = grouped.apply(
        lambda s: ", ".join(sorted(set(x for x in s.dropna() if x)))
    )
    primary = grouped.apply(
        lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else "Unknown"
    )

    opp_df = opp_df.copy()
    opp_df["countries"] = opp_df["id"].map(countries).fillna("Unknown").replace("", "Unknown")
    opp_df["primary_country"] = opp_df["id"].map(primary).fillna("Unknown")
    return opp_df


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner="Loading radar data…")
def load_data() -> dict:
    """Load everything the dashboard needs.

    Returns a dict with the three dataframes plus provenance fields, so every
    page can tell the user exactly where the numbers on screen came from.
    """
    cfg = get_sql_config()
    source = "snapshot"
    note = ""

    if cfg is None:
        note = (
            "No Azure SQL credentials found, so the committed CSV snapshot is "
            "being shown. Add them to .env locally or to Streamlit secrets to "
            "read live data."
        )
        opp_df, sig_df, link_df = _load_from_snapshot()
    else:
        try:
            opp_df, sig_df, link_df = _load_from_sql(cfg)
            source = "azure_sql"
        except Exception as exc:
            note = (
                f"Could not reach Azure SQL ({type(exc).__name__}), so the "
                "committed CSV snapshot is being shown instead. The database "
                "may be paused, or this machine may not be allowed through the "
                "firewall."
            )
            opp_df, sig_df, link_df = _load_from_snapshot()

    opp_df = _normalise_opportunities(opp_df)
    sig_df = _normalise_signals(sig_df)
    opp_df = attach_countries(opp_df, sig_df, link_df)

    return {
        "opportunities": opp_df,
        "signals": sig_df,
        "links": link_df,
        "source": source,
        "note": note,
    }


def signals_for_opportunity(opportunity_id, sig_df: pd.DataFrame,
                            link_df: pd.DataFrame) -> pd.DataFrame:
    """The signals that support one opportunity space, via the join table."""
    if sig_df.empty or link_df.empty:
        return pd.DataFrame()
    ids = link_df.loc[
        link_df["opportunity_space_id"] == opportunity_id, "signal_id"
    ].tolist()
    return sig_df[sig_df["id"].isin(ids)]
