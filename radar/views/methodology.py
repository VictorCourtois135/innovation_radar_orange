"""Page 5 — the scoring method, made testable.

The point of this page is to survive a sceptical question from the client. Move
a weight, watch the ranking change: that shows the number is a model with
assumptions, not a verdict handed down by an AI.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from radar import config as C
from radar import scoring, theme


def render(data: dict, df) -> None:
    theme.banner("Scoring methodology", "How the attractiveness score is built, and what happens if you disagree with it")

    st.markdown("### The formula")
    st.latex(
        r"""
        \text{attractiveness} =
        0.30\,S_{\text{market}} + 0.20\,S_{\text{diversity}} +
        0.15\,S_{\text{evidence}} + 0.15\,S_{\text{urgency}} +
        0.20\,S_{\text{strategic}}
        """
    )
    st.caption(
        "All five sub-scores are on a 0-100 scale, so the result is too. These "
        "weights are the ones in `scripts/opportunity_spaces.py`, which is what "
        "actually produced the numbers in the database."
    )

    st.markdown("### The five components")
    comp = pd.DataFrame([
        {
            "Component": label,
            "Weight": f"{weight:.0%}",
            "Source": "LLM judgement" if col == "strategic_relevance" else "code",
            "What it measures": explanation,
        }
        for col, label, weight, explanation in C.SCORE_COMPONENTS
    ])
    st.dataframe(comp, use_container_width=True, hide_index=True,
                 column_config={"What it measures": st.column_config.TextColumn(width="large")})

    theme.note(
        "<b>Design principle:</b> compute everything that can be computed, and "
        "reserve the model for the one thing that genuinely needs judgement. "
        "Four of the five components come from the signal data. Only "
        "<b>strategic relevance</b> asks the model, because whether an "
        "opportunity matters to Orange is not derivable from article counts."
    )

    # ------------------------------------------------------ interactive weights
    st.markdown("### What if the weights were different?")
    st.caption(
        "Session-only. Nothing is written back to the database. Use this to test "
        "whether the ranking is robust or whether it hinges on one assumption."
    )

    cols = st.columns(5)
    weights = {}
    for i, (col, label, default, _) in enumerate(C.SCORE_COMPONENTS):
        weights[col] = cols[i].slider(label, 0.0, 1.0, default, 0.05, key=f"w_{col}")

    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.001:
        st.warning(
            f"Weights sum to {total_weight:.2f}, not 1.00. Scores below are "
            "rescaled so they stay comparable on a 0-100 scale."
        )
        weights = {k: v / total_weight for k, v in weights.items()} if total_weight else weights

    if df.empty:
        st.info("No opportunity spaces to re-rank.")
        return

    reranked = df.copy()
    reranked["custom_score"] = scoring.recompute(reranked, weights)
    reranked["rank_default"] = reranked["attractiveness_score"].rank(ascending=False, method="min")
    reranked["rank_custom"] = reranked["custom_score"].rank(ascending=False, method="min")
    reranked["rank_change"] = (reranked["rank_default"] - reranked["rank_custom"]).astype(int)

    show = reranked.sort_values("custom_score", ascending=False)[
        ["code", "name", "attractiveness_score", "custom_score", "rank_change"]
    ]
    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={
            "code": "Code",
            "name": "Opportunity space",
            "attractiveness_score": st.column_config.NumberColumn("Stored score", format="%.1f"),
            "custom_score": st.column_config.NumberColumn("With your weights", format="%.1f"),
            "rank_change": st.column_config.NumberColumn(
                "Rank change", format="%+d",
                help="Positive means it moved up under your weights.",
            ),
        },
    )

    moved = int((reranked["rank_change"] != 0).sum())
    if moved == 0:
        st.success(
            "No opportunity changed rank under these weights. The ranking is "
            "robust to this much reweighting, which is a good sign."
        )
    else:
        st.info(
            f"{moved} of {len(reranked)} opportunities changed rank. The ones "
            "that move most are the ones whose case rests on a single component."
        )

    # ----------------------------------------------------- supporting detail
    st.markdown("### Source credibility tiers")
    st.caption(
        "Evidence quality = 100 − (average tier − 1) × 25. A cluster of three "
        "press releases and one Reuters piece averages tier 4.0, giving 25."
    )
    tiers = pd.DataFrame(
        [{"Tier": t, "Source type": name, "Examples": ex, "Score if all this tier": s}
         for t, name, ex, s in C.SOURCE_TIERS]
    )
    st.dataframe(tiers, use_container_width=True, hide_index=True)

    st.markdown("### The recency curve")
    st.caption(
        "Urgency uses continuous exponential decay with a 270-day half-life, not "
        "step buckets, so two signals a month apart are actually distinguishable."
    )
    days = np.arange(0, 1100, 10)
    decay = np.maximum(100.0 * (0.5 ** (days / 270.0)), 5.0)
    fig = go.Figure(go.Scatter(
        x=days, y=decay, mode="lines",
        line=dict(color=C.ORANGE, width=2),
        hovertemplate="%{x} days old<br>score %{y:.0f}<extra></extra>",
    ))
    for d, lbl in [(270, "9 months → 50"), (540, "18 months → 25")]:
        fig.add_vline(x=d, line_width=1, line_dash="dot", line_color=C.GREY_MED)
        fig.add_annotation(x=d, y=100, text=lbl, showarrow=False, yshift=8,
                           font=dict(size=11, color=C.GREY_MED))
    fig.update_layout(height=320, hovermode="x")
    theme.style_axes(fig, y_title="Urgency score", x_title="Age of the signal (days)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Known limitations")
    st.markdown(
        """
- **Volume reflects what the agent found**, not total market activity. The
  collection agent runs a capped number of searches, so a topic it happened not
  to search for scores low on volume regardless of how hot it really is.
- **Google Trends is an unofficial API** and gets rate-limited. Results are
  cached for 7 days and a persistent cooldown is recorded on failure, after
  which scoring falls back to volume only.
- **The tiers are themselves a judgement.** Deciding that Gartner is tier 2 and
  Light Reading is tier 3 was a team decision, not a fact. Worth revisiting
  together rather than treating the registry as settled.
- **Strategic relevance is one model call.** It is grounded in Orange's stated
  plan rather than general intuition, but it is still a single opinion and it
  is 20% of the headline number.
        """
    )
