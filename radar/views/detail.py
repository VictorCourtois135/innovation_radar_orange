"""Page 3 — one opportunity in full, including its stored score inputs.

The backend pipeline calculates the opportunity scores and saves them in
Azure SQL. This Streamlit page does not recalculate the final attractiveness
score. It presents the stored final score, its five stored component scores,
and the supporting signals.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from radar import config as C
from radar import data as data_module
from radar import theme


# Metadata used only to explain the stored component scores.
# No scoring or weighting is performed on this page.
SCORE_COMPONENTS = [
    {
        "column": "market_signal_strength",
        "component": "Market signal strength",
        "short": "Market",
        "source": "⚙ code",
        "explanation": (
            "Strength of the market signal based on the number of supporting "
            "articles and available trend information."
        ),
    },
    {
        "column": "source_diversity_score",
        "component": "Source diversity",
        "short": "Diversity",
        "source": "⚙ code",
        "explanation": (
            "Variety of independent sources supporting the opportunity."
        ),
    },
    {
        "column": "evidence_quality",
        "component": "Evidence quality",
        "short": "Evidence",
        "source": "⚙ code",
        "explanation": (
            "Quality and reliability of the sources behind the opportunity."
        ),
    },
    {
        "column": "urgency_time_horizon",
        "component": "Urgency",
        "short": "Urgency",
        "source": "⚙ code",
        "explanation": (
            "How recent and time-sensitive the supporting signals are."
        ),
    },
    {
        "column": "strategic_relevance",
        "component": "Strategic relevance",
        "short": "Strategic",
        "source": "◆ LLM judgement",
        "explanation": (
            "Relevance of the opportunity to Orange's strategy, capabilities, "
            "markets and business priorities."
        ),
    },
]


def _stored_components(row: pd.Series) -> pd.DataFrame:
    """Return the five component scores exactly as stored in the data source."""

    records = []

    for component in SCORE_COMPONENTS:
        value = pd.to_numeric(
            pd.Series([row.get(component["column"])]),
            errors="coerce",
        ).iloc[0]

        records.append(
            {
                "column": component["column"],
                "component": component["component"],
                "short": component["short"],
                "score": value,
                "source": component["source"],
                "explanation": component["explanation"],
            }
        )

    return pd.DataFrame(records)


def _portfolio_average(df: pd.DataFrame, columns: list[str]) -> list[float] | None:
    """Mean of each component across every opportunity currently in view.

    Returns None when there is nothing to compare against — a single row, or no
    numeric values — so the detail chart quietly drops the reference ring rather
    than drawing a line identical to the one in front of it.
    """
    if df is None or len(df) < 2:
        return None
    values: list[float] = []
    for column in columns:
        if column not in df.columns:
            return None
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            return None
        values.append(float(series.mean()))
    return values


def _render_status_control(data: dict, row: pd.Series) -> None:
    """Selectbox + button to change this opportunity's status in Azure SQL.

    Disabled with an explanation when the app is running off the CSV
    snapshot: there's no live database connection to write through in that
    mode, and silently editing only the in-memory dataframe would make the
    change disappear on the next refresh without saying so.
    """
    current_status = row.get("status", C.STATUS_UNKNOWN)

    # If a status value in the data isn't one of the configured options
    # (e.g. C.STATUS_UNKNOWN, or something set directly in the database
    # outside this dropdown's choices), add it so the selectbox can still
    # show the real current value instead of silently defaulting to the
    # first option in the list.
    options = list(C.STATUS_OPTIONS)
    if current_status not in options:
        options = [current_status] + options

    is_live = data.get("source") == "azure_sql"

    st.markdown("### Status")
    status_col, button_col = st.columns([2, 1])

    with status_col:
        chosen_status = st.selectbox(
            "Status",
            options,
            index=options.index(current_status),
            key=f"status_select_{row['id']}",
            label_visibility="collapsed",
            disabled=not is_live,
        )

    with button_col:
        update_clicked = st.button(
            "Update status",
            disabled=not is_live or chosen_status == current_status,
            use_container_width=True,
        )

    if not is_live:
        st.caption(
            "Status can only be changed when connected to the live Azure SQL "
            "database — the app is currently showing the CSV snapshot."
        )
    elif chosen_status == current_status:
        st.caption(f"Current status: **{current_status}**.")

    if update_clicked:
        success, message = data_module.update_status(row["id"], chosen_status)
        if success:
            st.success(message)
            # The cached load_data() result still has the old status; clear
            # it so the next run re-reads the value that was just written,
            # rather than showing a stale one until the cache's TTL expires.
            st.cache_data.clear()
            # Re-select the same opportunity after the rerun triggered by
            # the cache clear, since a fresh "filtered" dataframe means this
            # page's own widget state (built from the old data) can't be
            # trusted to line up with the new one on its own.
            st.session_state["selected_opportunity_id"] = row["id"]
            st.rerun()
        else:
            st.error(message)


def render(data: dict, df: pd.DataFrame) -> None:
    theme.banner(
        "Opportunity detail",
        "The full case, its stored scores and supporting evidence",
    )

    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    ranked = df.sort_values("attractiveness_score", ascending=False)

    labels = {
        (
            f"{row['code']} · {row['name']} "
            f"({float(row['attractiveness_score']):.1f})"
        ): row["id"]
        for _, row in ranked.iterrows()
    }

    # If the "Top opportunities" table/chart was clicked, opportunities.py
    # leaves the chosen id here. Consumed with pop() so it only forces the
    # selectbox once — after that, the selectbox's own key drives its value
    # like normal, so the user can still change the choice by hand.
    incoming_id = st.session_state.pop("selected_opportunity_id", None)
    if incoming_id is not None:
        match = next((label for label, oid in labels.items() if oid == incoming_id), None)
        if match is not None:
            st.session_state["detail_selectbox"] = match

    # Guard against a stale selection: if the current filters (sidebar or
    # persona) have narrowed df so the previously chosen label no longer
    # exists, drop it rather than letting the widget raise on a value that
    # isn't among its current options.
    if st.session_state.get("detail_selectbox") not in labels:
        st.session_state.pop("detail_selectbox", None)

    chosen_label = st.selectbox(
        "Opportunity space",
        list(labels.keys()),
        key="detail_selectbox",
    )

    row = df[df["id"] == labels[chosen_label]].iloc[0]

    # ---------------------------------------------------------------- header
    horizon = row.get("time_horizon", "Later")

    horizon_color = C.HORIZON_COLORS.get(str(horizon), C.NEUTRAL)
    status_label = str(row.get("status", C.STATUS_UNKNOWN))
    status_color = C.STATUS_COLORS.get(status_label, C.NEUTRAL)

    st.markdown(
        f"""
        <div class="obx-card">
            <span class="obx-pill" style="background-color:{horizon_color}">
                {str(horizon).upper()} HORIZON</span>
            <span class="obx-pill" style="background-color:{status_color}">
                {status_label.upper()}</span>
            <span class="obx-pill obx-pill-muted">{row['code']}</span>
            <h3>{row['name']}</h3>
            <p style="color:{C.GREY_MED};margin:0">
                <b>Vertical:</b> {row.get('vertical', '?')} &nbsp;·&nbsp;
                <b>Use case:</b> {row.get('use_case', '?')} &nbsp;·&nbsp;
                <b>Technology:</b> {row.get('technology', '?')} &nbsp;·&nbsp;
                <b>Markets:</b> {row.get('countries', 'Unknown')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_status_control(data, row)

    left, right = st.columns([3, 2], gap="large")

    # ---------------------------------------------------------- explanation
    with left:
        detailed_summary = row.get("detailed_summary")

        if (
            "detailed_summary" in row.index
            and detailed_summary is not None
            and not pd.isna(detailed_summary)
            and str(detailed_summary).strip()
        ):
            st.markdown("### Overview")
            st.write(detailed_summary)

        st.markdown("### Why this is hot now")
        st.write(row.get("why_hot", "Not recorded."))

        st.markdown("### Why it matters to Orange")
        st.write(row.get("why_matters", "Not recorded."))

        st.markdown("### Recommended next action")
        st.success(row.get("next_action", "Not recorded."))

        capability_note = row.get("capability_check_note")

        if (
            capability_note is not None
            and not pd.isna(capability_note)
            and str(capability_note).strip()
        ):
            st.markdown("### Capability check")
            st.info(capability_note)
            st.caption(
                "Before scoring, each cluster is compared against Orange's "
                "known deployed capabilities, including their geographic scope. "
                "If Orange already sells this in this market, the cluster is "
                "skipped and does not become an opportunity."
            )

    # --------------------------------------------------------- stored score
    with right:
        st.markdown("### Attractiveness")

        attractiveness_score = pd.to_numeric(
            pd.Series([row.get("attractiveness_score")]),
            errors="coerce",
        ).iloc[0]

        if pd.isna(attractiveness_score):
            st.warning("No stored attractiveness score is available.")
        else:
            st.markdown(
                f"""
                <div style="
                    font-size:64px;
                    line-height:1;
                    font-weight:700;
                    color:{C.ORANGE};
                ">
                    {attractiveness_score:.1f}
                </div>
                <div style="color:{C.GREY_MED};font-size:13px">
                    out of 100
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(
            "This is the final score stored by the backend pipeline. "
            "The dashboard does not recalculate it."
        )

        components = _stored_components(row)
        available_components = components.dropna(subset=["score"])

        if available_components.empty:
            st.info("No stored component scores are available for this opportunity.")
        else:
            # A five-axis shape on its own tells you almost nothing: 54 on
            # evidence quality is only meaningful next to what the other
            # opportunities score. So the portfolio average is drawn behind it as
            # a neutral dashed reference. Grey and dashed on purpose — it is not
            # a second series competing for attention, and the dash means the
            # two are distinguishable without relying on colour.
            radar_figure = go.Figure()

            baseline = _portfolio_average(df, available_components["column"].tolist())
            if baseline is not None:
                radar_figure.add_trace(
                    go.Scatterpolar(
                        r=list(baseline) + [baseline[0]],
                        theta=list(available_components["short"])
                        + [available_components["short"].iloc[0]],
                        name=f"Average of all {len(df)}",
                        mode="lines",
                        line=dict(color=C.NEUTRAL, width=2, dash="dot"),
                        fill="toself",
                        fillcolor="rgba(138,138,138,0.10)",
                        hovertemplate="%{theta}<br>portfolio average %{r:.1f}<extra></extra>",
                    )
                )

            scores = list(available_components["score"])
            labels = list(available_components["short"])
            radar_figure.add_trace(
                go.Scatterpolar(
                    r=scores + scores[:1],
                    theta=labels + labels[:1],
                    name=str(row["code"]),
                    mode="lines+markers",
                    line=dict(color=C.CAT[0], width=3),
                    marker=dict(size=8, color=C.CAT[0],
                                line=dict(width=2, color=C.WHITE)),
                    fill="toself",
                    fillcolor="rgba(255,121,0,0.22)",
                    hovertemplate="%{theta}<br>%{r:.1f} / 100<extra></extra>",
                )
            )

            radar_figure.update_polars(
                radialaxis=dict(
                    range=[0, 100],
                    gridcolor=C.GREY_BORDER,
                    tickfont=dict(size=11, color=C.GREY_MED),
                ),
                angularaxis=dict(
                    gridcolor=C.GREY_BORDER,
                    tickfont=dict(size=13),
                ),
                bgcolor=C.WHITE,
            )

            radar_figure.update_layout(
                # Was 700px inside a narrow right-hand column, which pushed the
                # chart most of a screen below the score it belongs to.
                height=380,
                margin=dict(t=56, b=30, l=60, r=60),
                paper_bgcolor=C.WHITE,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.06,
                            xanchor="center", x=0.5, title_text=""),
            )

            st.plotly_chart(radar_figure, width="stretch")
            st.caption(
                "The five component scores as stored in Azure SQL, against the "
                "average across every opportunity currently in view. Nothing is "
                "recalculated here."
            )

    # -------------------------------------------------- stored score inputs
    st.markdown("### Stored scoring components")
    st.caption(
        "These are the component values produced by the backend scoring "
        "pipeline and saved with the opportunity. This page does not apply "
        "weights or calculate a new final score."
    )

    components = _stored_components(row)

    st.dataframe(
        components[
            [
                "component",
                "score",
                "source",
                "explanation",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "component": "Component",
            "score": st.column_config.NumberColumn(
                "Stored score (0–100)",
                format="%.1f",
            ),
            "source": "Originally produced by",
            "explanation": st.column_config.TextColumn(
                "What it measures",
                width="large",
            ),
        },
    )

    missing_components = components.loc[
        components["score"].isna(),
        "component",
    ].tolist()

    if missing_components:
        st.warning(
            "No stored value was found for: "
            + ", ".join(missing_components)
            + "."
        )

    st.caption(
        "Four components are produced from signal data. Strategic relevance "
        "is an LLM judgement. The backend pipeline combines these components "
        "and stores the final attractiveness score."
    )

    # ------------------------------------------------------- evidence trail
    st.markdown("### Supporting signals")

    signals = data_module.signals_for_opportunity(
        row["id"],
        data["signals"],
        data["links"],
    )

    if signals.empty:
        st.info(
            "No linked signals are available. In snapshot mode, individual "
            "signals may not be exported. Connect to Azure SQL or run "
            "`python scripts/export_snapshot.py` to see the evidence trail."
        )
        return

    show = signals.copy()

    columns = [
        column
        for column in [
            "source_name",
            "title",
            "signal_type",
            "publication_date",
            "country",
            "source_url",
        ]
        if column in show.columns
    ]

    if "publication_date" in show.columns:
        show = show.sort_values(
            "publication_date",
            ascending=False,
        )

    st.dataframe(
        show[columns],
        width="stretch",
        hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn(
                "Link",
                display_text="open",
            ),
            "publication_date": st.column_config.DateColumn(
                "Published",
                format="YYYY-MM-DD",
            ),
        },
    )

    st.caption(
        f"{len(signals)} signals feed this opportunity, traced through the "
        "`opportunity_space_signals` join table. The stored scores were "
        "produced from this evidence by the backend pipeline."
    )