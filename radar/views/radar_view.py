"""Page 1 — the radar itself.

Encoding, and why:

    ring   = time horizon (Now / Next / Later), derived from urgency
    sector = vertical
    size   = attractiveness score
    colour = attractiveness score, on a single-hue orange ramp

Size and colour deliberately encode the same variable. That is redundant
encoding, and it is on purpose: the reader can find the strongest opportunities
by area or by darkness, whichever they notice first, and the chart stays
readable in greyscale and under colour-vision deficiency because the ramp
varies by lightness.

The earlier version coloured by ``status``. Since the extraction pipeline never
writes that column, every bubble came out the same grey, which reads as a bug.
"""

from __future__ import annotations

import numpy as np
import plotly.express as px
import streamlit as st

from radar import config as C
from radar import theme


def render(data: dict, df) -> None:
    theme.banner(
        "Innovation Radar",
        "Competitor opportunity spaces by vertical (sector) and time horizon (ring)",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opportunity spaces", len(df))
    c2.metric("Now horizon", int((df["time_horizon"] == "Now").sum()))
    c3.metric(
        "Avg. attractiveness",
        f"{df['attractiveness_score'].mean():.1f}" if len(df) else "–",
    )
    c4.metric(
        "Evidence articles",
        int(df["total_articles"].fillna(0).sum()) if "total_articles" in df else 0,
    )

    if df.empty:
        st.warning(
            "No opportunity spaces match the current filters. Widen them in the "
            "sidebar, or clear the persona preset."
        )
        return

    plot_df = df.copy()

    # Place each bubble inside its horizon ring. The jitter is deterministic so
    # the chart does not reshuffle on every rerun, which would be disorienting.
    ring_base = {"Now": 1.0, "Next": 2.0, "Later": 3.0}
    plot_df["ring"] = plot_df["time_horizon"].map(ring_base).fillna(3.0)
    rng = np.random.default_rng(7)
    plot_df["r"] = plot_df["ring"] - rng.uniform(0.15, 0.75, size=len(plot_df))

    fig = px.scatter_polar(
        plot_df,
        r="r",
        theta="vertical",
        size="attractiveness_score",
        color="attractiveness_score",
        color_continuous_scale=C.ORANGE_RAMP,
        range_color=(C.SCORE_MIN, C.SCORE_MAX),
        size_max=34,
        hover_name="name",
        custom_data=["code", "technology", "use_case", "attractiveness_score",
                     "time_horizon", "countries"],
    )
    fig.update_traces(
        marker=dict(line=dict(width=2, color=C.WHITE)),  # 2px surface ring
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "%{customdata[0]}<br>"
            "Technology: %{customdata[1]}<br>"
            "Use case: %{customdata[2]}<br>"
            "Attractiveness: %{customdata[3]:.1f}<br>"
            "Horizon: %{customdata[4]}<br>"
            "Markets: %{customdata[5]}"
            "<extra></extra>"
        ),
    )
    fig.update_polars(
        radialaxis=dict(
            range=[0, 3],
            tickvals=[0.5, 1.5, 2.5],
            ticktext=["Now", "Next", "Later"],
            showline=False,
            gridcolor=C.GREY_BORDER,
            tickfont=dict(size=11, color=C.GREY_MED),
        ),
        angularaxis=dict(gridcolor=C.GREY_BORDER, tickfont=dict(size=12)),
        bgcolor=C.WHITE,
    )
    fig.update_layout(
        height=640,
        paper_bgcolor=C.WHITE,
        font_color=C.GREY_DARK,
        coloraxis_colorbar=dict(
            title="Attractiveness", thickness=12, len=0.55, y=0.5,
        ),
        margin=dict(t=40, b=40, l=40, r=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Ring = time horizon, inner is more urgent. Sector = vertical. "
        "Bubble size and colour both = attractiveness score."
    )

    if len(df) < 10:
        theme.note(
            f"Only <b>{len(df)}</b> opportunity spaces exist. The clustering step "
            "requires 3 or more signals above 0.82 cosine similarity to form a "
            "group, which is strict. Lowering <code>MIN_CLUSTER_SIZE</code> or the "
            "threshold in <code>scripts/opportunity_spaces.py</code> would surface "
            "more, at the cost of weaker evidence per opportunity. The client said "
            "they would realistically work with 10 to 20 at a time."
        )

    with st.expander("Table view of the same data"):
        cols = [c for c in ["code", "name", "vertical", "technology",
                            "time_horizon", "attractiveness_score",
                            "total_articles", "distinct_sources", "countries"]
                if c in df.columns]
        st.dataframe(
            df[cols].sort_values("attractiveness_score", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
