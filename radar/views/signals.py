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

    with g1:
        by_country = (
            view.groupby("country").size().reset_index(name="signals")
            .sort_values("signals", ascending=True).tail(12)
        )
        # One series: bar length already encodes the count, so colouring by the
        # same number spends the identity channel restating it. Flat brand
        # colour, value labelled directly.
        fig2 = px.bar(
            by_country, x="signals", y="country", orientation="h", text="signals",
        )
        fig2.update_traces(
            textposition="outside",
            textfont=dict(color=C.GREY_DARK, size=11),
            marker=dict(color=C.CAT[0], cornerradius=4,
                        line=dict(width=2, color=C.WHITE)),
            hovertemplate="<b>%{y}</b><br>%{x} signals<extra></extra>",
        )
        fig2.update_layout(height=380, showlegend=False)
        theme.style_axes(fig2, x_title="Signals")
        fig2.update_yaxes(title_text="")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Top 12 markets by signal count.")

    with g2:
        belgium = int((view["country"].str.contains("Belgium", case=False, na=False)).sum())
        rest = len(view) - belgium
        split = pd.DataFrame({
            "scope": ["Belgium", "Rest of world"],
            "signals": [belgium, rest],
        })
        # Two named scopes, not a magnitude ramp: these are identities, so they
        # take categorical slots.
        fig3 = px.bar(split, x="scope", y="signals", text="signals",
                      color="scope",
                      color_discrete_map={"Belgium": C.CAT[0],
                                          "Rest of world": C.CAT[1]})
        fig3.update_traces(
            textposition="outside",
            textfont=dict(color=C.GREY_DARK, size=12),
            marker=dict(cornerradius=4, line=dict(width=2, color=C.WHITE)),
            hovertemplate="<b>%{x}</b><br>%{y} signals<extra></extra>",
        )
        fig3.update_layout(height=380, showlegend=False)
        theme.style_axes(fig3, y_title="Signals")
        fig3.update_xaxes(title_text="")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(
            f"{belgium} Belgian, {rest} elsewhere. Orange Business is a global "
            "operator, so a low Belgian share is not automatically a problem, "
            "but the prompt does ask for BIPT/IBPT as a regional baseline."
        )

    # ------------------------------------------------------- type + sources
    st.markdown("### Signal type and source mix")
    h1, h2 = st.columns(2)

    with h1:
        if "signal_type" in view.columns:
            by_type = (view.groupby("signal_type").size()
                       .reset_index(name="signals").sort_values("signals"))
            # Coloured by the type itself, using exactly the map the stacked
            # area chart above uses — so "regulation" is the same blue in both
            # places and a reader can carry the legend between them.
            fig4 = px.bar(by_type, x="signals", y="signal_type", orientation="h",
                          color="signal_type",
                          color_discrete_map=C.SIGNAL_TYPE_COLORS,
                          text="signals")
            fig4.update_traces(
                textposition="outside", textfont=dict(color=C.GREY_DARK, size=11),
                marker=dict(cornerradius=4, line=dict(width=2, color=C.WHITE)),
                hovertemplate="<b>%{y}</b><br>%{x} signals<extra></extra>",
            )
            fig4.update_layout(height=320, showlegend=False)
            theme.style_axes(fig4, x_title="Signals")
            fig4.update_yaxes(title_text="")
            st.plotly_chart(fig4, use_container_width=True)
            st.caption(
                "Regulator and wire-service signals carry more weight in the "
                "evidence quality score than company press releases."
            )

    with h2:
        by_source = (view.groupby("source_name").size()
                     .reset_index(name="signals")
                     .sort_values("signals", ascending=True).tail(12))
        fig5 = px.bar(by_source, x="signals", y="source_name", orientation="h",
                      text="signals")
        fig5.update_traces(
            textposition="outside", textfont=dict(color=C.GREY_DARK, size=11),
            marker=dict(color=C.CAT[0], cornerradius=4,
                        line=dict(width=2, color=C.WHITE)),
            hovertemplate="<b>%{y}</b><br>%{x} signals<extra></extra>",
        )
        fig5.update_layout(height=320, showlegend=False)
        theme.style_axes(fig5, x_title="Signals")
        fig5.update_yaxes(title_text="")
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
