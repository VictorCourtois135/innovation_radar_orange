"""Page 4 — the raw signals underneath everything.

Two charts here were asked for by name in the project notes: "a graph with the
number of articles per month for a year, so we can see if they increase,
decrease or stay the same", and "a graph centred on the Belgian market, and
another one focused on the market around the world".
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from radar import config as C
from radar import theme


def render(data: dict, df) -> None:
    theme.banner("Signal explorer", "The raw external evidence the radar is built on")

    sig = data["signals"]
    if sig.empty:
        st.info(
            "No signals available. In snapshot mode only the opportunity spaces "
            "are exported. Connect to Azure SQL, or run "
            "`python scripts/export_snapshot.py` while connected, to populate this page."
        )
        return

    # ------------------------------------------------------------- filters row
    f1, f2, f3 = st.columns(3)
    countries = sorted(sig["country"].dropna().unique()) if "country" in sig else []
    types = sorted(sig["signal_type"].dropna().unique()) if "signal_type" in sig else []
    years = sorted(sig["publication_year"].dropna().unique()) if "publication_year" in sig else []

    sel_country = f1.multiselect("Country", countries)
    sel_type = f2.multiselect("Signal type", types)
    sel_year = f3.multiselect("Year", [int(y) for y in years])

    view = sig.copy()
    if sel_country:
        view = view[view["country"].isin(sel_country)]
    if sel_type:
        view = view[view["signal_type"].isin(sel_type)]
    if sel_year:
        view = view[view["publication_year"].isin(sel_year)]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Signals", len(view))
    m2.metric("Distinct sources", view["source_name"].nunique() if "source_name" in view else 0)
    m3.metric("Countries", view["country"].nunique() if "country" in view else 0)
    m4.metric(
        "Median age",
        f"{(pd.Timestamp.today() - view['publication_date']).dt.days.median():.0f} days"
        if "publication_date" in view and view["publication_date"].notna().any() else "–",
    )

    if view.empty:
        st.warning("No signals match these filters.")
        return

    # --------------------------------------------------- volume over time
    st.markdown("### Signal volume over time")
    if "publication_month" in view.columns:
        # Stacked by signal type rather than one flat orange area. The total is
        # unchanged, but the composition is the more useful question: a rising
        # line made only of press releases means something different from one
        # made of regulator filings, and evidence_quality scores that difference.
        # It is also the one chart on this page where colour has real identity
        # work to do.
        by_month = (
            view.dropna(subset=["publication_date"])
            .groupby(["publication_month", "signal_type"]).size()
            .reset_index(name="signals").sort_values("publication_month")
        )
        present = set(by_month["signal_type"])
        order = [t for t in C.SIGNAL_TYPE_COLORS if t in present]
        fig = px.area(
            by_month, x="publication_month", y="signals",
            color="signal_type",
            category_orders={"signal_type": order},
            color_discrete_map=C.SIGNAL_TYPE_COLORS,
        )
        # px.area derives each band's fillcolor from its line colour, so setting
        # the line to white in a blanket update_traces() turns every fill white
        # and the chart renders blank. Pin the fill explicitly first, then the
        # white separator line on top of it.
        def _band(trace):
            hex_color = C.SIGNAL_TYPE_COLORS.get(trace.name, C.NEUTRAL)
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
            trace.update(
                fillcolor=f"rgba({r},{g},{b},0.85)",
                # 2px surface line between stacked fills, so adjacent bands stay
                # separable without leaning on hue alone.
                line=dict(width=2, color=C.WHITE),
                hovertemplate="%{y} signals<extra>%{fullData.name}</extra>",
            )

        fig.for_each_trace(_band)
        fig.update_layout(height=340, hovermode="x unified", legend_title_text="")
        theme.style_axes(fig, y_title="Signals published", x_title="Month")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "By publication date, not collection date, and stacked by evidence "
            "type. The shape is partly a property of the agent's search prompt, "
            "which favours 2024-2026 and weights 2026 most heavily, so this is "
            "not an unbiased measure of how much the world published."
        )

    # ------------------------------------------------- Belgium vs the world
    st.markdown("### Where the signals come from")
    g1, g2 = st.columns(2)

    def _lollipop(data, cat_col, val_col, height, hover_label):
        # Stem + dot instead of a filled bar: same ranking legibility, lighter
        # ink. Stems drawn first as thin lines, dots layered on top as a
        # scatter trace so the value label can sit inside/beside the marker.
        import plotly.graph_objects as go

        fig = go.Figure()
        for _, row in data.iterrows():
            fig.add_shape(
                type="line",
                x0=0, x1=row[val_col], y0=row[cat_col], y1=row[cat_col],
                line=dict(color=C.GREY_LIGHT if hasattr(C, "GREY_LIGHT") else C.GREY_DARK,
                           width=2),
                layer="below",
            )
        fig.add_trace(go.Scatter(
            x=data[val_col], y=data[cat_col],
            mode="markers+text",
            marker=dict(size=14, color=C.CAT[0],
                        line=dict(width=2, color=C.WHITE)),
            text=data[val_col], textposition="middle right",
            textfont=dict(color=C.GREY_DARK, size=11),
            hovertemplate=f"<b>%{{y}}</b><br>%{{x}} {hover_label}<extra></extra>",
            showlegend=False,
        ))
        fig.update_layout(height=height, showlegend=False)
        theme.style_axes(fig, x_title="Signals")
        fig.update_yaxes(title_text="")
        fig.update_xaxes(range=[0, data[val_col].max() * 1.2])
        return fig

    with g1:
        by_country = (
            view.groupby("country").size().reset_index(name="signals")
            .sort_values("signals", ascending=True).tail(12)
        )
        fig2 = _lollipop(by_country, "country", "signals", 380, "signals")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Top 12 markets by signal count.")

    with g2:
        by_source = (view.groupby("source_name").size()
                     .reset_index(name="signals")
                     .sort_values("signals", ascending=True).tail(12))
        fig5 = _lollipop(by_source, "source_name", "signals", 380, "signals")
        st.plotly_chart(fig5, use_container_width=True)
        st.caption("Top 12 publications. Concentration here lowers source diversity.")

    # ----------------------------------------------------------- the table
    st.markdown("### All signals")
    cols = [c for c in ["id", "source_name", "title", "signal_type",
                        "publication_date", "country", "targeted_vertical",
                        "source_url"] if c in view.columns]
    st.dataframe(
        view[cols].sort_values("publication_date", ascending=False),
        use_container_width=True, hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn("Link", display_text="open"),
            "publication_date": st.column_config.DateColumn("Published", format="YYYY-MM-DD"),
        },
    )
