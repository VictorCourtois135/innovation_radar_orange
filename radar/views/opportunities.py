"""Page 2 — the ranked list.

The client said in the QA session that they would realistically address the top
50 at a time, and for narrowed B2B work 10 to 20. So this page is a ranking
first and a table second: the point is to answer "what are the strongest few",
not to browse everything.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from radar import config as C
from radar import theme


SORT_OPTIONS = [
    ("attractiveness_score", "Attractiveness"),
    ("market_signal_strength", "Market signal strength"),
    ("source_diversity_score", "Source diversity"),
    ("evidence_quality", "Evidence quality"),
    ("urgency_time_horizon", "Urgency"),
    ("strategic_relevance", "Strategic relevance"),
]

# The five stored component scores, same set detail.py shows in its own
# radar chart. Kept as a short local list (column, short axis label) rather
# than importing from detail.py, since this page only needs the bare column
# names, not detail.py's longer explanations.
COMPARE_COMPONENTS = [
    ("market_signal_strength", "Market"),
    ("source_diversity_score", "Diversity"),
    ("evidence_quality", "Evidence"),
    ("urgency_time_horizon", "Urgency"),
    ("strategic_relevance", "Strategic"),
]

MAX_COMPARE = 3

# The first three categorical slots. These used to be hard-coded here, because
# the old global template set colorway=[ORANGE] and px.line_polar's discrete
# sequence therefore collapsed to near-identical shades. The template now
# carries the whole validated order, so this is just a pointer to it — and the
# first three slots are exactly the set that clears the all-pairs colour-vision
# check, which is the right bar for overlaid shapes that touch each other.
COMPARE_COLORS = C.CAT[:3]


def _opportunity_label(row) -> str:
    return f"{row['code']} · {row['name']}"


def _clean_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _short_summary(row) -> str:
    """The always-visible summary line on a comparison card: why it matters."""
    return _clean_text(row.get("why_matters")) or "Not recorded."


def _detailed_summary(row) -> str:
    """The longer summary shown inside "Read more" on a comparison card.

    Falls back to "why_hot" (also shown in full on detail.py, under "Why
    this is hot now") when the pipeline hasn't produced a detailed_summary
    for this opportunity, so "Read more" still says something rather than
    just repeating the short line above it.
    """
    detailed = _clean_text(row.get("detailed_summary"))
    if detailed:
        return detailed

    why_hot = _clean_text(row.get("why_hot"))
    if why_hot:
        return why_hot

    return "No additional detail recorded."


def _render_filters(df):
    """Filters: vertical group, time horizon, status.

    The vertical group filter uses C.vertical_group_map() to collapse
    near-duplicate raw vertical values (e.g. "Enterprise IT" and
    "Enterprise Security") into a handful of coarse categories. Time
    horizon and status are used as-is since they're already small,
    meaningful categories (Now/Next/Later and the four configured status
    labels).

    Each multiselect's key includes "filters_version", a counter bumped by
    "Clear filters". Popping session_state keys by name can leave a filter
    looking uncleared if anything else in the app ever touches that same
    key, or if a widget's internal state doesn't fully reset from a pop
    alone. Changing the key instead forces Streamlit to create a brand new
    widget with no memory of the old one, which clears reliably regardless
    of the cause — this is what fixed "Status" not clearing.
    """
    st.markdown("### Filters")
    filtered = df.copy()

    version = st.session_state.get("filters_version", 0)

    has_vertical = "vertical" in df.columns

    if has_vertical:
        # Built from the values actually present, not from a fixed vocabulary.
        # The old hard-coded VERTICAL_GROUPS listed verticals ("Enterprise IT",
        # "Cloud infrastructure", ...) that appear in neither table, so five of
        # the seven real opportunity verticals fell through to "Other" and the
        # filter was close to useless.
        filtered["vertical_group"] = [C.vertical_group(v) for v in filtered["vertical"]]

    filter_specs = []
    if has_vertical:
        filter_specs.append(("vertical_group", "Vertical group", sorted(filtered["vertical_group"].unique())))
    if "time_horizon" in df.columns:
        filter_specs.append(("time_horizon", "Time horizon", sorted(x for x in df["time_horizon"].dropna().unique() if x)))
    if "status" in df.columns:
        filter_specs.append(("status", "Status", sorted(x for x in df["status"].dropna().unique() if x)))

    cols = st.columns(len(filter_specs)) if filter_specs else []
    selections = {}
    for (col_name, label, options), col in zip(filter_specs, cols):
        with col:
            selections[col_name] = st.multiselect(
                label, options, key=f"filter_{col_name}_{version}",
            )

    for col_name, values in selections.items():
        if values:
            filtered = filtered[filtered[col_name].isin(values)]

    if has_vertical:
        filtered = filtered.drop(columns=["vertical_group"])

    active = sum(1 for v in selections.values() if v)
    if active:
        st.caption(f"{len(filtered)} of {len(df)} opportunity spaces match {active} active filter(s).")
        if st.button("Clear filters"):
            # Bumping the version changes every filter widget's key on the
            # next run, so they're recreated empty — rather than trying to
            # pop each old key, which is what silently failed to clear the
            # status filter.
            st.session_state["filters_version"] = version + 1
            st.rerun()

    return filtered


def _render_sort_controls(df):
    """Sort control that drives BOTH the chart and the table.

    st.dataframe's built-in click-to-sort-by-column is purely client-side —
    it never round-trips to Python, so there is no way for code (and
    therefore the chart above it) to know a header was clicked. This
    control replaces that with an explicit Streamlit widget, so "sort by"
    is a single piece of state both the chart and the table read from.
    """
    available = [(col, label) for col, label in SORT_OPTIONS if col in df.columns]
    if not available:
        return "attractiveness_score", False

    col_left, col_right = st.columns([3, 1])
    with col_left:
        sort_col = st.selectbox(
            "Sort by",
            options=[col for col, _ in available],
            format_func=lambda c: dict(available)[c],
            key="sort_column",
        )
    with col_right:
        ascending = st.selectbox(
            "Order",
            options=[False, True],
            format_func=lambda a: "Descending" if not a else "Ascending",
            key="sort_ascending",
        )
    return sort_col, ascending


def _go_to_detail(opportunity_id) -> None:
    """Request navigation to the detail page for one opportunity.

    Writes to "pending_page" rather than "page_name" directly: by the time
    this page's render() runs, app.py has already instantiated the sidebar
    radio with key="page_name" for this run, and Streamlit forbids writing
    to a widget's own key after it's created. app.py picks "pending_page"
    up and applies it BEFORE creating the radio on the next run.
    """
    st.session_state["selected_opportunity_id"] = opportunity_id
    st.session_state["pending_page"] = "Opportunity detail"
    st.rerun()


def _add_to_comparison(row) -> None:
    """Add one opportunity's label to the comparison multiselect's state.

    This must run BEFORE the "compare_select" widget is instantiated later
    in this same script run — safe here since the chart click is handled
    earlier in render() than the call to _render_comparison(), and this
    function calls st.rerun() immediately, so execution never reaches that
    widget's creation in the current run anyway.
    """
    label = _opportunity_label(row)
    current = list(st.session_state.get("compare_select", []))

    if label in current:
        st.toast(f"{row['code']} is already in the comparison.", icon="ℹ️")
        return
    if len(current) >= MAX_COMPARE:
        st.toast(f"Comparison is full (max {MAX_COMPARE}). Remove one first.", icon="⚠️")
        return

    current.append(label)
    st.session_state["compare_select"] = current
    st.session_state["compare_expanded"] = True
    st.toast(f"Added {row['code']} to comparison.", icon="✅")
    st.rerun()


def _resolve_clicked_id(point: dict, ranked_sorted):
    """Get the opportunity id behind a clicked chart point.

    Streamlit/Plotly versions have shipped a click point's "customdata" as
    either a list (the normal case: [id]) or, on some versions, a dict.
    Rather than assume one shape and crash on the other (KeyError: 0 is
    exactly what happens indexing a dict with an int), this tries both,
    then falls back to the point's position, which lines up 1:1 with
    ranked_sorted since that's the exact dataframe the chart was built
    from.
    """
    customdata = point.get("customdata")

    if isinstance(customdata, (list, tuple)) and customdata:
        return customdata[0]
    if isinstance(customdata, dict) and customdata:
        return next(iter(customdata.values()))

    idx = point.get("point_index", point.get("pointIndex", point.get("point_number")))
    if idx is not None and 0 <= idx < len(ranked_sorted):
        return ranked_sorted.iloc[idx]["id"]

    return None


def _point_signature(point: dict):
    """A hashable fingerprint for a clicked point.

    Plotly/Streamlit KEEPS a chart's selection in session_state across
    reruns that have nothing to do with the chart — toggling an unrelated
    checkbox, changing a filter, or re-sorting all trigger a rerun that
    still carries the same "points" list from the last actual click. Acting
    on that stale selection every time is what made the comparison toggle
    seem to randomly reopen the detail page: flipping the toggle reran the
    script, found the old click still "selected", and treated it as a new
    one. Comparing this signature against the last one actually handled
    lets the click handler tell a genuinely new click apart from a rerun
    that merely re-delivered the previous one.
    """
    return (
        point.get("curve_number", point.get("curveNumber")),
        point.get("point_index", point.get("pointIndex", point.get("point_number"))),
    )


def _render_summary_cards(subset, available_components) -> None:
    """One card per compared opportunity: identity, score, text summary,
    and best/weakest trait.

    The radar chart shows shape at a glance but not what any of it *means*
    for a given opportunity, or what it actually is; this spells both out
    in words — a short "why it matters" line (with the pipeline's fuller
    detailed_summary a click away), plus which component is pulling the
    profile up or dragging it down — so the takeaway doesn't require
    reading five axis values off the chart by eye or opening each detail
    page separately.
    """
    st.markdown("#### Summary")
    cols = st.columns(len(subset))

    for col, (_, row) in zip(cols, subset.iterrows()):
        scores = {
            short: pd.to_numeric(pd.Series([row.get(col_name)]), errors="coerce").iloc[0]
            for col_name, short in available_components
        }
        valid_scores = {k: v for k, v in scores.items() if pd.notna(v)}

        attractiveness = pd.to_numeric(
            pd.Series([row.get("attractiveness_score")]), errors="coerce"
        ).iloc[0]

        with col:
            st.markdown(f"**{row['code']}**")
            st.caption(row["name"])
            st.metric("Attractiveness", f"{attractiveness:.1f}" if pd.notna(attractiveness) else "—")

            # _clean_text, not str(): str(nan) is the four-character string
            # "nan", which is truthy, so a missing vertical used to render as a
            # literal "nan" on the card.
            meta_bits = [
                _clean_text(row.get("vertical")),
                _clean_text(row.get("time_horizon")),
            ]
            meta_bits = [b for b in meta_bits if b]
            if meta_bits:
                st.caption(" · ".join(meta_bits))

            st.write(_short_summary(row))
            with st.expander("Read more"):
                st.write(_detailed_summary(row))

            if valid_scores:
                best = max(valid_scores, key=valid_scores.get)
                worst = min(valid_scores, key=valid_scores.get)
                st.markdown(f"🟢 Strongest: **{best}** ({valid_scores[best]:.0f})")
                if worst != best:
                    st.markdown(f"🔴 Weakest: **{worst}** ({valid_scores[worst]:.0f})")
            else:
                st.caption("No component scores available.")


def _render_comparison(df) -> None:
    """Pick 2-3 opportunities and compare their five stored component scores.

    An overlaid radar chart makes the shape of each opportunity's profile
    comparable at a glance (e.g. "this one is evidence-heavy, that one is
    urgency-heavy"); the summary cards spell out what that shape means in
    words, with a short text description of each opportunity; the table
    underneath gives the exact numbers for anyone who wants precise values
    rather than comparing shapes or reading a summary.
    """
    available_components = [(col, short) for col, short in COMPARE_COMPONENTS if col in df.columns]
    if not available_components or df.empty:
        return

    # Consumed here, BEFORE the "compare_select" multiselect below is
    # created for this run — writing to it after that point is what
    # crashed the "Clear comparison" button previously.
    if st.session_state.pop("compare_clear_requested", False):
        st.session_state["compare_select"] = []

    expanded = st.session_state.get("compare_expanded", False) or bool(
        st.session_state.get("compare_select")
    )

    with st.expander("Compare opportunities", expanded=expanded):
        st.caption(
            f"Pick 2 to {MAX_COMPARE} opportunities here, or turn on comparison "
            "mode above the chart and click bars to add them directly."
        )

        labels = {
            _opportunity_label(row): row["id"]
            for _, row in df.sort_values("attractiveness_score", ascending=False).iterrows()
        }
        # Labels added via a chart click (by id) may not match this run's
        # options if filters changed since — drop anything no longer valid
        # rather than letting the multiselect widget raise on a stale value.
        current = [l for l in st.session_state.get("compare_select", []) if l in labels]
        if current != st.session_state.get("compare_select"):
            st.session_state["compare_select"] = current

        chosen = st.multiselect(
            "Opportunities to compare",
            list(labels.keys()),
            max_selections=MAX_COMPARE,
            key="compare_select",
        )

        if len(chosen) < 2:
            st.info("Select at least 2 opportunities to compare.")
            return

        chosen_ids = [labels[label] for label in chosen]
        # Preserve the order opportunities were chosen in, rather than
        # df's own row order, so summary cards line up with the order the
        # user picked them (and with the legend order in the radar chart).
        subset = pd.concat([df[df["id"] == oid] for oid in chosen_ids])

        _render_summary_cards(subset, available_components)

        records = []
        for _, row in subset.iterrows():
            for col, short in available_components:
                value = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
                records.append({
                    "opportunity": row["code"],
                    "component": short,
                    "score": value,
                })
        radar_df = pd.DataFrame(records)

        fig = px.line_polar(
            radar_df,
            r="score",
            theta="component",
            color="opportunity",
            line_close=True,
            range_r=[0, 100],
            color_discrete_sequence=COMPARE_COLORS,
        )
        fig.update_traces(fill="toself", opacity=0.45, line=dict(width=3))
        fig.update_polars(
            radialaxis=dict(gridcolor=C.GREY_BORDER, tickfont=dict(size=10)),
            angularaxis=dict(gridcolor=C.GREY_BORDER, tickfont=dict(size=10)),
            bgcolor=C.WHITE,
        )
        fig.update_layout(
            height=420,
            paper_bgcolor=C.WHITE,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig, use_container_width=True)

        pivot = radar_df.pivot(index="component", columns="opportunity", values="score")
        # Keep the axis order consistent with the radar chart rather than
        # whatever order pivot() happens to produce.
        pivot = pivot.reindex([short for _, short in available_components])
        st.dataframe(
            pivot,
            use_container_width=True,
            column_config={
                code: st.column_config.NumberColumn(code, format="%.1f")
                for code in pivot.columns
            },
        )

        if st.button("Clear comparison"):
            # Deferred via a flag rather than writing "compare_select"
            # directly here: the multiselect above already instantiated
            # that key for this run, and Streamlit forbids mutating a
            # widget's own key after it's created in the same run.
            st.session_state["compare_clear_requested"] = True
            st.session_state["compare_expanded"] = False
            st.rerun()


def render(data: dict, df) -> None:
    theme.banner(
        "Top opportunity spaces",
        "Vertical × Use case × Technology, ranked by attractiveness",
    )

    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    df = _render_filters(df)
    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    sort_col, sort_ascending = _render_sort_controls(df)
    sort_label = dict(SORT_OPTIONS).get(sort_col, sort_col)

    # Slider needs min_value < max_value strictly. With 3 or fewer rows
    # left after filtering, max(3, len(df)) would equal min_value=3 and
    # Streamlit raises StreamlitAPIException. Below that threshold, skip
    # the slider entirely and just show everything there is.
    if len(df) <= 3:
        top_n = len(df)
        st.caption(f"Showing all {top_n} opportunity space(s) matching the current filters.")
    else:
        top_n = st.slider(
            "How many to show", min_value=3, max_value=len(df),
            value=min(10, len(df)), step=1,
        )

    df_sorted = df.sort_values(sort_col, ascending=sort_ascending, na_position="last")
    ranked = df_sorted.head(top_n)
    # For the horizontal bar chart, plotly draws bottom-to-top, so this
    # reverses the display order to put the "best" bar (per the chosen
    # sort/direction) at the top rather than the bottom.
    ranked_sorted = ranked.iloc[::-1].reset_index(drop=True)

    compare_mode = st.toggle(
        "Comparison mode — click bars to add them to the comparison instead of opening details",
        key="compare_mode",
    )

    # One series, one colour. The previous version passed color=sort_col with a
    # sequential ramp, so the shade of each bar restated the number its LENGTH
    # already showed — the colour channel spent on nothing, plus a colour bar
    # that had to be switched off again with coloraxis_showscale=False. Position
    # is the strongest encoding there is; let it do the work alone.
    fig = px.bar(
        ranked_sorted,
        x=sort_col,
        y="name",
        orientation="h",
        text=sort_col,
        custom_data=["id"],  # carried through so a click resolves back to a row
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        textfont=dict(color=C.GREY_DARK, size=12),
        marker=dict(
            color=C.CAT[0],
            cornerradius=4,                                  # rounded data-end
            line=dict(width=2, color=C.WHITE),               # 2px surface gap
        ),
        hovertemplate=f"<b>%{{y}}</b><br>{sort_label}: %{{x:.1f}}<extra></extra>",
    )
    fig.update_layout(
        height=max(320, 46 * len(ranked)),
        showlegend=False,
        # Headroom for the outside value labels, which would otherwise be
        # clipped on a bar sitting near 100.
        xaxis_range=[0, 108],
    )
    theme.style_axes(fig, x_title=f"{sort_label} (0-100)")
    fig.update_yaxes(title_text="")

    # Remove gridlines that would otherwise cut straight through the
    # middle of each bar — showgrid=False on both axes, and zeroline=False
    # so the x=0 reference line (drawn thicker by default) doesn't leave
    # one behind either. theme.style_axes may set other axis properties
    # (titles, fonts, etc.), so this runs after it rather than replacing
    # that call, to only touch the gridlines.
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)

    chart_event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="ranked_chart",
    )

    st.caption(
        "A single series, so no legend: every bar is the same measure. "
        "Values are labelled directly rather than read off the axis. "
        + ("Click a bar to add it to the comparison below." if compare_mode
           else "Click a bar to open its detail page.")
    )

    # Only act on a click that's actually new. The chart's selection is
    # kept in session_state and gets re-delivered on every rerun — even
    # ones caused by flipping the toggle above, changing a filter, or
    # re-sorting — so without this check, those unrelated actions would
    # replay whatever bar was last clicked (e.g. re-opening the detail page
    # the instant comparison mode was switched off). See _point_signature.
    raw_points = chart_event.get("selection", {}).get("points", []) if chart_event else []
    if raw_points:
        signature = _point_signature(raw_points[0])
        if signature != st.session_state.get("_last_chart_signature"):
            st.session_state["_last_chart_signature"] = signature
            clicked_id = _resolve_clicked_id(raw_points[0], ranked_sorted)
            if clicked_id is not None:
                if compare_mode:
                    clicked_row = df[df["id"] == clicked_id].iloc[0]
                    _add_to_comparison(clicked_row)
                else:
                    _go_to_detail(clicked_id)
    else:
        # Selection was cleared (e.g. the user clicked empty space on the
        # chart) — forget the last handled point so re-clicking the same
        # bar later is treated as a fresh click again.
        st.session_state["_last_chart_signature"] = None

    _render_comparison(df)

    st.markdown("### Full table")
    st.caption(
        "Sorted the same way as the chart above. Clicking a column header "
        "here only reorders this table visually — it won't change the "
        "chart, since that click never reaches the app's code. Use the "
        "\"Sort by\" control above to change both at once."
    )
    cols = [c for c in [
        "code", "name", "vertical", "use_case", "technology", "time_horizon",
        "attractiveness_score", "market_signal_strength", "source_diversity_score",
        "evidence_quality", "urgency_time_horizon", "strategic_relevance",
        "total_articles", "distinct_sources", "countries",
    ] if c in df.columns]

    table_df = df[cols].sort_values(sort_col, ascending=sort_ascending, na_position="last")

    st.dataframe(
        table_df,
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
        table_df.to_csv(index=False),
        file_name="innovation_radar_opportunities.csv",
        mime="text/csv",
    )