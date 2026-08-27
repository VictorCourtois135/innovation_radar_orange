"""Constants for the Innovation Radar dashboard.

Everything that more than one page needs to agree on lives here, so there is a
single place to change a colour, a weight or a threshold.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Orange Business brand palette
# ---------------------------------------------------------------------------
ORANGE = "#FF7900"
ORANGE_DARK = "#D06A00"
ORANGE_LIGHT = "#FFB27A"
ORANGE_PALE = "#FFE3CC"
BLACK = "#000000"
GREY_DARK = "#333333"
GREY_MED = "#666666"
GREY_LIGHT = "#F2F2F2"
GREY_BORDER = "#DDDDDD"
WHITE = "#FFFFFF"

# Sequential ramp used for anything ordered low -> high.
ORANGE_RAMP = ["#FFE3CC", "#FFC499", "#FFA566", "#FF8C33", "#FF7900", "#D06A00"]

# Status is a workflow field on opportunity_spaces. The extraction pipeline does
# not currently write it, so most rows come back NULL. STATUS_UNKNOWN is what
# data.py substitutes so the app never has to deal with NaN.
STATUS_UNKNOWN = "unclassified"
STATUS_COLORS = {
    "watchlist": "#B7B7B7",
    "candidate": ORANGE_LIGHT,
    "kept": ORANGE,
    "active": ORANGE,
    "rejected": "#8A8A8A",
    "archived": "#4A4A4A",
    STATUS_UNKNOWN: "#9E9E9E",
}

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
# These must stay identical to scripts/opportunity_spaces.py. If the pipeline
# weights change, change them here too or the dashboard will explain a number
# that the database did not actually produce.
SCORE_COMPONENTS = [
    # (column, label, weight, short explanation shown in the UI)
    ("market_signal_strength", "Market signal strength", 0.30,
     "How much noise the topic is making: article volume on a log curve, "
     "combined with Google Trends search interest."),
    ("source_diversity_score", "Source diversity", 0.20,
     "Distinct sources divided by total articles. Ten articles from one "
     "outlet is weaker evidence than four articles from four outlets."),
    ("evidence_quality", "Evidence quality", 0.15,
     "Average credibility tier of the sources. Regulators and wire services "
     "score 100, company press releases score 0."),
    ("urgency_time_horizon", "Urgency / time horizon", 0.15,
     "Average recency of the signals, on an exponential decay with a 9-month "
     "half-life. Published today is about 100, 18 months ago is about 25."),
    ("strategic_relevance", "Strategic relevance", 0.20,
     "The one judgement call. The model rates fit against Orange's stated "
     "'Trust the Future' 2026-2030 priorities."),
]

SCORE_COLUMNS = [c for c, _, _, _ in SCORE_COMPONENTS]
SCORE_LABELS = {c: label for c, label, _, _ in SCORE_COMPONENTS}
DEFAULT_WEIGHTS = {c: w for c, _, w, _ in SCORE_COMPONENTS}

# Short forms for the polar/spider chart, where the full labels sit at the
# chart edge and get clipped by the plot margin.
SCORE_SHORT_LABELS = {
    "market_signal_strength": "Market signal",
    "source_diversity_score": "Diversity",
    "evidence_quality": "Evidence",
    "urgency_time_horizon": "Urgency",
    "strategic_relevance": "Strategic fit",
}

# All five sub-scores and the headline score are on a 0-100 scale.
SCORE_MIN, SCORE_MAX = 0, 100

# ---------------------------------------------------------------------------
# Time horizon
# ---------------------------------------------------------------------------
# Derived from urgency_time_horizon, which is itself a recency decay score.
# 66 corresponds to roughly 5 months old, 33 to roughly 14 months old.
HORIZON_NOW = 66
HORIZON_NEXT = 33
HORIZONS = ["Now", "Next", "Later"]
HORIZON_COLORS = {"Now": ORANGE, "Next": ORANGE_LIGHT, "Later": "#B7B7B7"}

# ---------------------------------------------------------------------------
# Source credibility tiers (mirrors source/source_registry.csv)
# ---------------------------------------------------------------------------
SOURCE_TIERS = [
    (1, "Regulators, wire services", "BIPT, FCC, Ofcom, BEREC, Reuters, Bloomberg", 100),
    (2, "Paid analyst firms", "Gartner, Omdia, Analysys Mason, GSMA", 75),
    (3, "Specialised trade press", "Light Reading, Fierce Network, Telecoms.com", 50),
    (4, "Aggregators, press wires", "BusinessWire, EuropaWire", 25),
    (5, "Company-owned press releases", "Vodafone Newsroom, AT&T Press", 0),
]

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
# Columns we actually read. Listing them explicitly instead of SELECT * matters
# for `signals`, which carries a VECTOR(1536) embedding column the dashboard
# never uses: pulling it drags roughly 1536 floats per row across the wire.
SIGNAL_COLUMNS = [
    "id", "source_url", "source_name", "title", "publication_date",
    "targeted_vertical", "country", "summary", "raw_excerpt",
    "date_of_scrape", "signal_type",
]

CACHE_TTL_SECONDS = 300  # refresh from the database at most every 5 minutes

SNAPSHOT_DIR = "data"
SNAPSHOT_OPPORTUNITIES = "snapshot_opportunities.csv"
SNAPSHOT_SIGNALS = "snapshot_signals.csv"
SNAPSHOT_LINKS = "snapshot_links.csv"

# Column names that changed during the project. Keys are old names still found
# in older CSV exports, values are the names the database and the app now use.
COLUMN_ALIASES = {
    "novelty_momentum": "urgency_time_horizon",
    "source_diversity": "source_diversity_score",
    "urgency_timing": "urgency_time_horizon",
    "why_now": "why_matters",
    "capability_gap": "capability_check_note",
    "opportunity_number": "id",
    "target_vertical": "targeted_vertical",
}
# Vertical grouping
# ---------------------------------------------------------------------------
# Raw vertical values from the data are granular ("Enterprise IT",
# "Enterprise Security", ...). For filtering, several of these are variants
# of the same broader category. This dict is the single place to adjust
# that grouping — edit the lists below to reassign a vertical to a
# different group, or add a new group entirely.
VERTICAL_GROUPS: dict[str, list[str]] = {
    "Enterprise": [
        "Enterprise",
        "Enterprise AI infrastructure",
        "Enterprise IT",
        "Enterprise Security",
    ],
    "Telecom & connectivity": [
        "Cloud infrastructure",
        "Fixed broadband",
        "IoT connectivity",
        "Telecom / Edge",
        "Telecom Infrastructure",
        "Telecommunications",
        "Telecoms / Cloud",
        "Telecoms regulation",
    ],
    "Manufacturing": [
        "Manufacturing",
    ],
    "Public sector": [
        "Public sector",
    ],
}


def vertical_group_map() -> dict[str, str]:
    """Map each raw vertical value to its group label.

    Any vertical value present in the data but not listed above falls back
    to "Other" at lookup time, so a new vertical appearing in a future data
    refresh doesn't silently disappear from the filters — it just shows up
    ungrouped until someone adds it to VERTICAL_GROUPS.
    """
    return {
        value: group
        for group, values in VERTICAL_GROUPS.items()
        for value in values
    }
    
STATUS_DISPLAY_TO_STORED = {
    "Candidate": "candidate",
    "Validated": "kept",
    "Rejected": "rejected",
    "Watchlist": "watchlist",
}
STATUS_OPTIONS = list(STATUS_DISPLAY_TO_STORED.keys())