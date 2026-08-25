"""Page 2 — the ranked list.

The client said in the QA session that they would realistically address the top
50 at a time, and for narrowed B2B work 10 to 20. So this page is a ranking
first and a table second: the point is to answer "what are the strongest few",
not to browse everything.
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from radar import config as C
from radar import theme


def render(data: dict, df) -> None:
    theme.banner(
        "Top opportunity spaces",
        "Vertical × Use case × Technology, ranked by attractiveness",
    )

    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    top_n = st.slider(
        "How many to show", min_value=3, max_value=max(3, len(df)),
        value=min(10, len(df)), step=1,
    )
    ranked = df.sort_values("attractiveness_score", ascending=False).head(top_n)

    fig = px.bar(
        ranked.sort_values("attractiveness_score"),
        x="attractiveness_score",
        y="name",
        orientation="h",
        color="attractiveness_score",
        color_continuous_scale=C.ORANGE_RAMP,
        range_color=(C.SCORE_MIN, C.SCORE_MAX),
        text="attractiveness_score",
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        textfont=dict(color=C.GREY_DARK, size=12),
        marker=dict(
            cornerradius=4,                                  # rounded data-end
            line=dict(width=2, color=C.WHITE),               # 2px surface gap
        ),
        hovertemplate="<b>%{y}</b><br>Attractiveness: %{x:.1f}<extra></extra>",
    )
    fig.update_layout(
        height=max(320, 46 * len(ranked)),
        showlegend=False,
        coloraxis_showscale=False,
        xaxis_range=[0, 100],
    )
    theme.style_axes(fig, x_title="Attractiveness score (0-100)")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "A single series, so no legend: every bar is the same measure. "
        "Values are labelled directly rather than read off the axis."
    )

    st.markdown("### Full table")
    cols = [c for c in [
        "code", "name", "vertical", "use_case", "technology", "time_horizon",
        "attractiveness_score", "market_signal_strength", "source_diversity_score",
        "evidence_quality", "urgency_time_horizon", "strategic_relevance",
        "total_articles", "distinct_sources", "countries",
    ] if c in df.columns]

    st.dataframe(
        df[cols].sort_values("attractiveness_score", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "attractiveness_score": st.column_config.ProgressColumn(
                "Attractiveness", min_value=0, max_value=100, format="%.1f",
            ),
        },
    )

    st.download_button(
        "Download this table as CSV",
        df[cols].sort_values("attractiveness_score", ascending=False).to_csv(index=False),
        file_name="innovation_radar_opportunities.csv",
        mime="text/csv",
    )
