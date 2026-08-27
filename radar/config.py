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

# ---------------------------------------------------------------------------
# Chart colour system
# ---------------------------------------------------------------------------
# Colour does exactly one of four jobs, and each job gets its own set. Mixing
# them up is what made the earlier all-orange version unreadable: a sequential
# ramp was used to colour bars whose LENGTH already carried the same number, so
# the colour channel was spent twice on one variable and never once on identity.
#
#   CATEGORICAL  identity  - which series is this            -> CAT, fixed order
#   SEQUENTIAL   magnitude - how much                        -> ORANGE_RAMP
#   ORDINAL      rank      - which step in an ordered set    -> ORANGE_RAMP
#   STATUS       state     - good / warning / serious / bad  -> STATUS_COLORS
#
# CAT keeps the Orange Business brand orange in slot 1, so the first (and often
# only) series on any chart is still brand-coloured. Slots 2-5 are taken from a
# palette validated for colour-vision deficiency; the order below was checked
# rather than eyeballed, with `dataviz/scripts/validate_palette.js`:
#
#   CAT[:5] on white, adjacent pairs (bars, stacks, lines):
#       worst CVD dE 23.1 (protan) / normal-vision dE 24.0   - PASS
#   HORIZON trio on white, ALL pairs (the radar is a bubble chart, where any two
#   marks can end up side by side, so every pair has to hold up, not just
#   neighbours):
#       worst CVD dE 13.0 (deutan) / normal-vision dE 16.3   - PASS
#
# The one warning the validator raises is that brand orange sits at 2.63:1
# against a white background, under the 3:1 mark threshold. That is allowed only
# when the value is also readable some other way, so every chart using it ships
# direct labels or a table view underneath. Do not drop those.
CAT = [
    ORANGE,     # 1 - Orange Business brand
    "#2A78D6",  # 2 - blue
    "#1BAF7A",  # 3 - aqua
    "#4A3AA7",  # 4 - violet
    "#E87BA4",  # 5 - magenta
]

# Non-data ink: "no value", "not classified", a reference line. Deliberately
# grey and deliberately NOT in CAT, so an unknown can never be mistaken for a
# real category.
NEUTRAL = "#8A8A8A"
NEUTRAL_LIGHT = "#C9C9C9"

# Sequential ramp, magnitude only (light = low, dark = high). Never use this to
# colour a bar chart by the same value the bar length already shows.
ORANGE_RAMP = ["#FFE3CC", "#FFC499", "#FFA566", "#FF8C33", "#FF7900", "#D06A00"]

# Reserved status scale. Kept apart from CAT so a workflow state can never be
# read as a data series, and always rendered with a word next to it, never as
# colour alone.
STATUS_UNKNOWN = "unclassified"
STATUS_COLORS = {
    "Candidate": "#FAB219",   # warning  - looked at, not decided
    "Validated": "#0CA30C",   # good     - kept
    "Rejected": "#D03B3B",    # critical - dropped
    "Watchlist": "#2A78D6",   # info     - parked, revisit
    STATUS_UNKNOWN: NEUTRAL,
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

# Three distinct hues rather than three tints of one. On the radar the ring
# already carries the order, so hue is free to carry identity - which is what
# makes a legend possible and what lets a reader pick the "Now" ring out of a
# screenshot. Validated all-pairs (see the CAT note above).
HORIZON_COLORS = {"Now": CAT[0], "Next": CAT[1], "Later": CAT[3]}

# Signal type is nominal: four kinds of evidence with no natural order. It gets
# categorical slots; anything unclassified gets neutral grey, never a slot.
SIGNAL_TYPE_COLORS = {
    "regulation": CAT[1],
    "analyst_report": CAT[2],
    "news": CAT[0],
    "press_release": CAT[4],
    "Unknown": NEUTRAL,
}

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
# Neither the collection agent nor the opportunity-space agent constrains the
# vertical it writes. `signals.targeted_vertical` currently holds 132 distinct
# strings across 619 rows, and `opportunity_spaces.vertical` is free text with a
# "2-6 words" instruction and nothing else. So the same industry arrives as
# "Industry", "Industry & Manufacturing", "Manufacturing / Industry" and
# "Manufacturing & Energy" depending on which prompt version was running.
#
# The real fix belongs upstream, in the prompt: give the agent a closed list and
# make it pick from it. Until that happens this map is the containment layer,
# and it has to be checked against the DATA, not written from memory - the
# previous version listed values such as "Enterprise IT" and "Cloud
# infrastructure" that appear in neither table, and so pushed five of the seven
# real opportunity verticals into "Other".
#
# Keys below are matched case-insensitively as substrings, which is what lets one
# entry absorb a family of near-identical labels instead of needing a line per
# spelling. Order matters: the first matching pattern wins.
VERTICAL_GROUP_PATTERNS: list[tuple[str, list[str]]] = [
    # Checked before "Industry" so "Industry & Manufacturing" does not swallow
    # a logistics signal that also says industry.
    ("Logistics & transport", ["port", "logistic", "transport", "supply chain",
                               "automotive", "mobility"]),
    ("Public sector & defence", ["public sector", "public serv", "government",
                                 "defense", "defence", "health"]),
    ("Finance & insurance", ["financ", "insurance", "bank", "fintech"]),
    ("Retail & FMCG", ["retail", "fmcg", "consumer", "customer experience",
                       "grocery", "food"]),
    # Before "Energy", so "Manufacturing & Energy" groups on its leading noun.
    ("Industry & manufacturing", ["industr", "manufactur"]),
    ("Energy & utilities", ["energy", "utilit"]),
    ("Telecom & connectivity", ["telecom", "network", "fiber", "fibre",
                                "broadband", "connectivity", "5g", "edge"]),
    ("IT services & cloud", ["it services", "it and services", "cloud",
                             "enterprise it", "data cent", "software",
                             "ai infrastructure", "cyber", "security"]),
]

VERTICAL_GROUP_FALLBACK = "Other"


def vertical_group(value) -> str:
    """Collapse one raw vertical string into a coarse, stable group label."""
    if value is None:
        return VERTICAL_GROUP_FALLBACK
    text = str(value).strip().lower()
    if not text or text in {"nan", "none", "unknown"}:
        return VERTICAL_GROUP_FALLBACK
    for group, patterns in VERTICAL_GROUP_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return group
    return VERTICAL_GROUP_FALLBACK


def vertical_group_map(values) -> dict[str, str]:
    """Map every raw vertical present in `values` to its group label.

    Built from the data rather than from a hard-coded vocabulary, so a vertical
    the agent invents on the next run still lands somewhere - in its matching
    group if the wording is recognisable, in "Other" if it is genuinely new.
    """
    return {value: vertical_group(value) for value in set(values)}


STATUS_DISPLAY_TO_STORED = {
    "Candidate": "candidate",
    "Validated": "kept",
    "Rejected": "rejected",
    "Watchlist": "watchlist",
}
STATUS_OPTIONS = list(STATUS_DISPLAY_TO_STORED.keys())