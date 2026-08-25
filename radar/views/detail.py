"""Page 3 — one opportunity in full, and where its score came from.

This is the page the project's acceptance criteria actually ask for:

    "The scoring model must not produce only a number. It must explain the
     number. [...] This makes the radar testable: if a user cannot explain why
     a topic is ranked, the scoring is not good enough."

So the score is not printed as a fact. It is broken into the five weighted
amounts that sum to it, each labelled with what it measures and whether it was
computed from data or judged by the model.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from radar import config as C
from radar import data as data_module
from radar import scoring, theme


def _field(label: str, value, empty: str = "Not recorded.") -> None:
    text = empty if (value is None or pd.isna(value) or str(value).strip() == "") else value
    st.markdown(f"**{label}**")
    st.write(text)


def render(data: dict, df) -> None:
    theme.banner("Opportunity detail", "The full case, and how the score was built")

    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    ranked = df.sort_values("attractiveness_score", ascending=False)
    labels = {
        f"{row['code']} · {row['name']} ({row['attractiveness_score']:.1f})": row["id"]
        for _, row in ranked.iterrows()
    }
    chosen_label = st.selectbox("Opportunity space", list(labels.keys()))
    row = df[df["id"] == labels[chosen_label]].iloc[0]

    # ---------------------------------------------------------------- header
    horizon = row.get("time_horizon", "Later")
    st.markdown(
        f"""<div class="obx-card">
        <span class="obx-pill">{horizon.upper()} HORIZON</span>
        <span class="obx-pill obx-pill-muted">{row['code']}</span>
        <h3>{row['name']}</h3>
        <p style="color:{C.GREY_MED};margin:0">
        <b>Vertical:</b> {row.get('vertical', '?')} &nbsp;·&nbsp;
        <b>Use case:</b> {row.get('use_case', '?')} &nbsp;·&nbsp;
        <b>Technology:</b> {row.get('technology', '?')} &nbsp;·&nbsp;
        <b>Markets:</b> {row.get('countries', 'Unknown')}
        </p></div>""",
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2], gap="large")

    with left:
        if "detailed_summary" in row.index and not pd.isna(row.get("detailed_summary")):
            st.markdown("### Overview")
            st.write(row["detailed_summary"])

        st.markdown("### Why this is hot now")
        st.write(row.get("why_hot", "Not recorded."))

        st.markdown("### Why it matters to Orange")
        st.write(row.get("why_matters", "Not recorded."))

        st.markdown("### Recommended next action")
        st.success(row.get("next_action", "Not recorded."))

        cap = row.get("capability_check_note")
        if cap is not None and not pd.isna(cap) and str(cap).strip():
            st.markdown("### Capability check")
            st.info(cap)
            st.caption(
                "Before scoring, each cluster is compared against Orange's known "
                "deployed capabilities including their geographic scope. If Orange "
                "already sells this in this market, the cluster is skipped entirely "
                "and never becomes an opportunity."
            )

    # ------------------------------------------------------------ the score
    with right:
        st.markdown("### Attractiveness")
        st.markdown(
            f"""<div style="font-size:64px;line-height:1;font-weight:700;
            color:{C.ORANGE}">{row['attractiveness_score']:.1f}</div>
            <div style="color:{C.GREY_MED};font-size:13px">out of 100</div>""",
            unsafe_allow_html=True,
        )

        matches, stored, recomputed = scoring.verify_stored_score(row)
        if not matches:
            st.warning(
                f"The stored score ({stored:.1f}) does not match a recomputation "
                f"from its own sub-scores ({recomputed:.1f}). This row was "
                "probably written under different weights than the ones shown "
                "below, so treat the breakdown as indicative."
            )

        st.caption(scoring.evidence_note(row))

        # Shape of the five sub-scores. One series, one colour, no legend.
        # Short labels here only: the full ones are clipped by the plot margin
        # at this width. The table below carries the full names.
        contrib = scoring.contributions(row)
        contrib_short = contrib.assign(
            short=contrib["column"].map(C.SCORE_SHORT_LABELS)
        )
        radar_fig = px.line_polar(
            contrib_short, r="raw", theta="short", line_close=True,
            range_r=[0, 100],
        )
        radar_fig.update_traces(
            fill="toself",
            line=dict(color=C.ORANGE, width=2),
            fillcolor="rgba(255,121,0,0.28)",
            hovertemplate="%{theta}<br>%{r:.1f} / 100<extra></extra>",
        )
        radar_fig.update_polars(
            radialaxis=dict(gridcolor=C.GREY_BORDER, tickfont=dict(size=10)),
            angularaxis=dict(gridcolor=C.GREY_BORDER, tickfont=dict(size=10)),
            bgcolor=C.WHITE,
        )
        radar_fig.update_layout(height=340, margin=dict(t=50, b=40, l=90, r=90),
                                paper_bgcolor=C.WHITE)
        st.plotly_chart(radar_fig, use_container_width=True)
        st.caption("Raw sub-scores, before weighting. Full names in the table below.")

    # ------------------------------------------------ where the points came from
    st.markdown("### Where the score came from")
    st.caption(
        "Each component's raw 0-100 value multiplied by its weight. "
        "These five numbers add up to the headline score."
    )

    contrib = scoring.contributions(row)

    bar = px.bar(
        contrib.sort_values("points"),
        x="points", y="component", orientation="h",
        color="points", color_continuous_scale=C.ORANGE_RAMP,
        range_color=(0, 30), text="points",
    )
    bar.update_traces(
        texttemplate="%{text:.1f} pts",
        textposition="outside",
        textfont=dict(color=C.GREY_DARK, size=12),
        marker=dict(cornerradius=4, line=dict(width=2, color=C.WHITE)),
        hovertemplate="<b>%{y}</b><br>%{x:.1f} points<extra></extra>",
    )
    bar.update_layout(
        height=300, showlegend=False, coloraxis_showscale=False,
        xaxis_range=[0, max(30, contrib["points"].max() * 1.25)],
    )
    theme.style_axes(bar, x_title="Points contributed to the final score")
    bar.update_yaxes(title_text="")
    st.plotly_chart(bar, use_container_width=True)

    display = contrib.copy()
    display["computed_by"] = display["computed_by"].map({
        "code": "⚙ code",
        "LLM judgement": "◆ LLM judgement",
    })
    st.dataframe(
        display[["component", "raw", "weight_pct", "points", "computed_by", "explanation"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "component": "Component",
            "raw": st.column_config.NumberColumn("Raw (0-100)", format="%.1f"),
            "weight_pct": "Weight",
            "points": st.column_config.NumberColumn("Points", format="%.1f"),
            "computed_by": "Source",
            "explanation": st.column_config.TextColumn("What it measures", width="large"),
        },
    )
    st.caption(
        f"Total: **{contrib['points'].sum():.1f}**. Four of the five components are "
        "calculated from the signal data. Only strategic relevance is a model "
        "judgement, marked ◆ above."
    )

    # ------------------------------------------------------- the evidence trail
    st.markdown("### Supporting signals")
    signals = data_module.signals_for_opportunity(
        row["id"], data["signals"], data["links"]
    )

    if signals.empty:
        st.info(
            "No linked signals available. In snapshot mode the individual "
            "signals are not exported. Connect to Azure SQL, or run "
            "`python scripts/export_snapshot.py`, to see the evidence trail."
        )
        return

    show = signals.copy()
    cols = [c for c in ["source_name", "title", "signal_type", "publication_date",
                        "country", "source_url"] if c in show.columns]
    st.dataframe(
        show[cols].sort_values("publication_date", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn("Link", display_text="open"),
            "publication_date": st.column_config.DateColumn("Published", format="YYYY-MM-DD"),
        },
    )
    st.caption(
        f"{len(signals)} signals feed this opportunity, traced through the "
        "`opportunity_space_signals` join table. Every score above is derived "
        "from these rows."
    )
