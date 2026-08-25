"""Persona presets: Strategist, Sales, Presales.

BE HONEST ABOUT WHAT THIS IS. The original architecture tagged each
opportunity space with the personas it was relevant for, using an
``opportunity_space_personas`` join table and an LLM judgement per row:

    "sales needs backing internal content, presales needs a matchable
     offering, strategist just needs a developed opportunity"

That table existed in the PostgreSQL draft. It did not survive the move to
Azure SQL, and nothing in the pipeline writes persona tags today. So there is
no persona data to filter on.

What follows is therefore NOT that feature. These are filter presets built from
columns that do exist, chosen to approximate the three audiences. The UI says
so explicitly, because presenting a rule-of-thumb as a model judgement would be
overclaiming in front of the client.

Turning this into the real thing means: add the join table, add persona tagging
to the builder agent's prompt, re-run the extraction. See the README.
"""

from __future__ import annotations

import pandas as pd

from radar import config

PERSONAS = {
    "Everyone": {
        "blurb": "No preset applied. Every opportunity space, ranked by attractiveness.",
        "rule": None,
    },
    "Strategist": {
        "blurb": (
            "The full picture, including slower-moving themes. Sorted by "
            "attractiveness so the strongest opportunities lead, but nothing "
            "is filtered out: a strategist is the one person who should see "
            "the Later horizon too."
        ),
        "rule": "strategist",
    },
    "Sales": {
        "blurb": (
            "Act-this-quarter opportunities. Filtered to the Now horizon, "
            "meaning the underlying signals are recent, and to opportunities "
            "with a concrete recommended next action."
        ),
        "rule": "sales",
    },
    "Presales": {
        "blurb": (
            "Where Orange has a capability question to answer. Filtered to "
            "opportunities whose capability check flagged a gap, a partial "
            "gap, or an unclear status, which are the ones needing a solution "
            "design or a partner before anyone can sell them."
        ),
        "rule": "presales",
    },
}

GAP_MARKERS = ("gap", "unclear", "partial", "no equivalent", "not confirmed",
               "discontinued", "no public evidence")


def _has_concrete_action(value) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip()
    # A real next action is a sentence, not a placeholder like "TBD" or "-".
    return len(text) > 25


def _flags_capability_gap(value) -> bool:
    if pd.isna(value):
        return False
    text = str(value).lower()
    return any(marker in text for marker in GAP_MARKERS)


def apply(df: pd.DataFrame, persona: str) -> pd.DataFrame:
    """Apply one persona preset. Unknown personas return the frame unchanged."""
    rule = PERSONAS.get(persona, {}).get("rule")
    if rule is None or df.empty:
        return df.sort_values("attractiveness_score", ascending=False)

    out = df.copy()

    if rule == "strategist":
        pass  # everything, just ranked

    elif rule == "sales":
        out = out[out["time_horizon"] == "Now"]
        if "next_action" in out.columns:
            out = out[out["next_action"].apply(_has_concrete_action)]

    elif rule == "presales":
        if "capability_check_note" in out.columns:
            flagged = out[out["capability_check_note"].apply(_flags_capability_gap)]
            # If the capability column is empty across the board (it is only
            # populated when the agent had something to say), fall back to
            # opportunities where Orange's strategic fit is uncertain rather
            # than returning an empty page.
            out = flagged if not flagged.empty else out[
                out["strategic_relevance"].fillna(0) < 75
            ]

    return out.sort_values("attractiveness_score", ascending=False)


def caveat(persona: str) -> str | None:
    """The disclaimer to render under a persona selection, or None."""
    if PERSONAS.get(persona, {}).get("rule") in (None,):
        return None
    return (
        "This is a **filter preset**, not a model-assigned persona tag. The "
        "pipeline does not currently tag opportunities by persona, so this "
        "rule approximates the audience using the columns that exist."
    )
