"""Page 5 — explanation of the backend scoring methodology.

The backend pipeline calculates the component scores and final attractiveness
score, then stores them in Azure SQL. This Streamlit page documents that
methodology but does not recalculate scores or create alternative rankings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from radar import config as C
from radar import theme


def render(data: dict, df: pd.DataFrame) -> None:
    theme.banner(
        "Scoring methodology",
        "How the backend pipeline calculates the stored attractiveness score",
    )

    # ------------------------------------------------------------- formula
    st.markdown("### The formula")

    st.latex(
        r"""
        \text{attractiveness} =
        0.30\,S_{\text{market}} +
        0.20\,S_{\text{diversity}} +
        0.15\,S_{\text{evidence}} +
        0.15\,S_{\text{urgency}} +
        0.20\,S_{\text{strategic}}
        """
    )

    st.caption(
        "All five component scores use a 0–100 scale, so the final result also "
        "uses a 0–100 scale. These weights are defined in the backend scoring "
        "pipeline. The resulting scores are stored in Azure SQL and displayed "
        "by the dashboard without recalculation."
    )

    # --------------------------------------------------------- components
    st.markdown("### The five components")

    components = pd.DataFrame(
        [
            {
                "Component": label,
                "Weight": f"{weight:.0%}",
                "Source": (
                    "◆ LLM judgement"
                    if column == "strategic_relevance"
                    else "⚙ code"
                ),
                "What it measures": explanation,
            }
            for column, label, weight, explanation in C.SCORE_COMPONENTS
        ]
    )

    st.dataframe(
        components,
        width="stretch",
        hide_index=True,
        column_config={
            "Component": "Component",
            "Weight": "Weight",
            "Source": "Originally produced by",
            "What it measures": st.column_config.TextColumn(
                "What it measures",
                width="large",
            ),
        },
    )

    theme.note(
        "<b>Design principle:</b> calculate everything that can be calculated "
        "from the available signal data, and reserve model judgement for the "
        "component that requires strategic interpretation. Four of the five "
        "components are produced from signal data. Only "
        "<b>strategic relevance</b> requires an LLM judgement because whether "
        "an opportunity matters to Orange cannot be determined from article "
        "counts alone."
    )

    st.info(
        "This page explains the scoring model only. It does not apply different "
        "weights, recalculate opportunity scores or write anything to Azure SQL."
    )

    # -------------------------------------------------- source credibility
    st.markdown("### Source credibility tiers")

    st.caption(
        "Evidence quality is calculated as: "
        "100 − (average source tier − 1) × 25. For example, a cluster with an "
        "average source tier of 4 receives an evidence-quality score of 25."
    )

    tiers = pd.DataFrame(
        [
            {
                "Tier": tier,
                "Source type": source_type,
                "Examples": examples,
                "Score if all sources use this tier": score,
            }
            for tier, source_type, examples, score in C.SOURCE_TIERS
        ]
    )

    st.dataframe(
        tiers,
        width="stretch",
        hide_index=True,
        column_config={
            "Tier": st.column_config.NumberColumn(
                "Tier",
                format="%d",
            ),
            "Source type": "Source type",
            "Examples": st.column_config.TextColumn(
                "Examples",
                width="large",
            ),
            "Score if all sources use this tier": st.column_config.NumberColumn(
                "Evidence-quality score",
                format="%d",
            ),
        },
    )

    # ------------------------------------------------------ recency curve
    st.markdown("### The recency curve")

    st.caption(
        "Urgency uses continuous exponential decay with a 270-day half-life. "
        "This avoids broad date buckets and allows signals published at "
        "different times to receive different urgency values."
    )

    days = np.arange(0, 1100, 10)
    decay = np.maximum(
        100.0 * (0.5 ** (days / 270.0)),
        5.0,
    )

    figure = go.Figure(
        go.Scatter(
            x=days,
            y=decay,
            mode="lines",
            line=dict(
                color=C.ORANGE,
                width=2,
            ),
            hovertemplate=(
                "%{x} days old"
                "<br>Urgency score: %{y:.0f}"
                "<extra></extra>"
            ),
        )
    )

    reference_points = [
        (270, "9 months → 50"),
        (540, "18 months → 25"),
    ]

    for day, label in reference_points:
        figure.add_vline(
            x=day,
            line_width=1,
            line_dash="dot",
            line_color=C.GREY_MED,
        )

        figure.add_annotation(
            x=day,
            y=100,
            text=label,
            showarrow=False,
            yshift=8,
            font=dict(
                size=11,
                color=C.GREY_MED,
            ),
        )

    figure.update_layout(
        height=320,
        hovermode="x",
    )

    theme.style_axes(
        figure,
        y_title="Urgency score",
        x_title="Age of the signal (days)",
    )

    st.plotly_chart(
        figure,
        width="stretch",
    )

    # --------------------------------------------------------- limitations
    st.markdown("### Known limitations")

    st.markdown(
        """
- **Volume reflects what the agent found, not total market activity.** The
  collection agent runs a limited number of searches. A topic that was not
  searched thoroughly may receive a low market-volume score even when the
  wider market is active.

- **Google Trends is accessed through an unofficial API.** It may be
  rate-limited or temporarily unavailable. Results are cached, and the backend
  may fall back to article volume when trend data cannot be retrieved.

- **Source tiers contain team judgement.** Classifying a source into a
  credibility tier is a methodological decision rather than an objective fact.
  The source registry should therefore be reviewed periodically.

- **Strategic relevance is an LLM judgement.** It is grounded in the available
  information about Orange's strategy and capabilities, but it remains a model
  assessment and represents 20% of the final attractiveness score.

- **The dashboard displays stored results.** Changes to the scoring formula or
  weights must be made in the backend pipeline and applied when scores are
  generated again. Streamlit does not recalculate existing database records.
        """
    )