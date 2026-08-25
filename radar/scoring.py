"""The attractiveness score, and how to explain it.

The project's own acceptance criteria say the scoring model must not produce
only a number, it must explain the number: "if a user cannot explain why a
topic is ranked, the scoring is not good enough."

That is what this module is for. :func:`contributions` breaks a single
opportunity's score into the five weighted amounts that add up to it, so the
dashboard can show *where* a 76.1 came from rather than just printing 76.1.
"""

from __future__ import annotations

import pandas as pd

from radar import config


def recompute(df: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    """Recompute attractiveness from the five sub-scores.

    With the default weights this reproduces the stored ``attractiveness_score``
    exactly, which is worth knowing: it means the dashboard is not inventing a
    parallel number. Pass custom weights to answer "what would the ranking look
    like if we cared more about evidence quality", without touching the
    database.
    """
    weights = weights or config.DEFAULT_WEIGHTS
    total = pd.Series(0.0, index=df.index)
    for column, weight in weights.items():
        if column in df.columns:
            total = total + df[column].fillna(0) * weight
    return total.round(1)


def contributions(row) -> pd.DataFrame:
    """Break one opportunity's score into its five weighted parts.

    Returns a tidy frame with the raw sub-score, the weight, and the number of
    points that component actually contributed. The ``points`` column sums to
    the attractiveness score.
    """
    rows = []
    for column, label, weight, explanation in config.SCORE_COMPONENTS:
        raw = row.get(column)
        raw = 0.0 if pd.isna(raw) else float(raw)
        rows.append({
            "component": label,
            "column": column,
            "raw": round(raw, 1),
            "weight": weight,
            "weight_pct": f"{weight:.0%}",
            "points": round(raw * weight, 1),
            "explanation": explanation,
            "computed_by": "LLM judgement" if column == "strategic_relevance" else "code",
        })
    return pd.DataFrame(rows)


def verify_stored_score(row, tolerance: float = 0.15) -> tuple[bool, float, float]:
    """Check the stored score against a recomputation from the sub-scores.

    A mismatch means the row was written under different weights than the ones
    the dashboard is explaining, which would make the explanation misleading.
    Cheap to check, so the detail page checks it and says so when it fails.
    Returns (matches, stored, recomputed).
    """
    stored = row.get("attractiveness_score")
    stored = float(stored) if not pd.isna(stored) else 0.0
    recomputed = round(
        sum(
            (0.0 if pd.isna(row.get(col)) else float(row.get(col))) * weight
            for col, _, weight, _ in config.SCORE_COMPONENTS
        ),
        1,
    )
    return abs(stored - recomputed) <= tolerance, stored, recomputed


def evidence_note(row) -> str:
    """A one-line, plain-English reading of the evidence behind a score."""
    total = row.get("total_articles")
    distinct = row.get("distinct_sources")
    if pd.isna(total) or pd.isna(distinct):
        return "Evidence counts are not recorded for this opportunity."
    total, distinct = int(total), int(distinct)
    if distinct <= 1:
        strength = "a single source, so treat this as weak evidence"
    elif distinct == total:
        strength = "every article from a different source, which is the strongest pattern"
    else:
        strength = f"{distinct} independent sources corroborating each other"
    return f"Built from {total} articles across {distinct} distinct sources: {strength}."
