"""Page 5 — the backend scoring formula, plus an interactive weight sandbox.

The backend pipeline calculates the component scores and the final
attractiveness score, then stores them in Azure SQL. This page documents
that formula and lets the user explore "what if the weights were different"
against the *stored* component scores — entirely client-side, in the
session. Nothing here recalculates or overwrites anything in Azure SQL; the
backend pipeline remains the only writer of attractiveness_score.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from radar import config as C
from radar import theme

# Component columns as (column, label, default_weight, explanation), reused
# from config so the sandbox's defaults always match the backend formula.
COMPONENT_COLUMNS = [column for column, *_ in C.SCORE_COMPONENTS]


def _default_weight_pct(column: str) -> int:
    for col, _label, weight, _explanation in C.SCORE_COMPONENTS:
        if col == column:
            return round(weight * 100)
    return 0


def _reset_weights() -> None:
    for column in COMPONENT_COLUMNS:
        st.session_state[f"weight_slider_{column}"] = _default_weight_pct(column)


def _go_to_detail(opportunity_id) -> None:
    """Request navigation to the detail page for one opportunity.

    Mirrors opportunities.py's _go_to_detail: writes to "pending_page"
    rather than "page_name" directly, since app.py has already instantiated
    the sidebar radio with key="page_name" for this run and Streamlit
    forbids writing to a widget's own key after it's created. app.py picks
    "pending_page" up and applies it BEFORE creating the radio on the next
    run.
    """
    st.session_state["selected_opportunity_id"] = opportunity_id
    st.session_state["pending_page"] = "Opportunity detail"
    st.rerun()


def _render_formula() -> None:
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


def _render_weight_sliders() -> dict[str, float]:
    """Five sliders, one per component. Returns normalised weights (sum to 1)."""

    st.markdown("### Try your own weights")
    st.write(
        "Adjust how much each component counts, and every opportunity space "
        "below is re-scored instantly using its **stored** component values. "
        "This is a sandbox: it runs only in your browser session and never "
        "changes the weights or scores in Azure SQL."
    )

    for column in COMPONENT_COLUMNS:
        st.session_state.setdefault(
            f"weight_slider_{column}", _default_weight_pct(column)
        )

    slider_cols = st.columns(len(C.SCORE_COMPONENTS))
    raw_weights: dict[str, int] = {}

    for slider_col, (column, label, _weight, _explanation) in zip(
        slider_cols, C.SCORE_COMPONENTS
    ):
        with slider_col:
            raw_weights[column] = st.slider(
                label,
                min_value=0,
                max_value=100,
                step=5,
                key=f"weight_slider_{column}",
            )

    total = sum(raw_weights.values())

    reset_col, status_col = st.columns([1, 4])
    with reset_col:
        st.button("Reset to backend weights", on_click=_reset_weights)

    if total == 0:
        with status_col:
            st.warning(
                "All weights are at 0%, so every component is being treated "
                "equally instead."
            )
        normalised = {column: 1 / len(COMPONENT_COLUMNS) for column in COMPONENT_COLUMNS}
    else:
        normalised = {column: value / total for column, value in raw_weights.items()}
        with status_col:
            badges = " &nbsp;·&nbsp; ".join(
                f"<b>{label}</b> {normalised[column]:.0%}"
                for column, label, _w, _e in C.SCORE_COMPONENTS
            )
            st.markdown(
                f"<span style='color:{C.GREY_MED};font-size:13px'>"
                f"Normalised to 100% → {badges}</span>",
                unsafe_allow_html=True,
            )

    return normalised


def _render_recalculated_list(df: pd.DataFrame, weights: dict[str, float]) -> None:
    st.markdown("### Opportunity spaces under your weights")

    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    scored = df.dropna(subset=COMPONENT_COLUMNS).copy()
    missing_count = len(df) - len(scored)

    if scored.empty:
        st.info(
            "None of the opportunity spaces in the current view have all five "
            "stored component scores, so nothing can be re-scored."
        )
        return

    scored["adjusted_score"] = sum(
        scored[column] * weight for column, weight in weights.items()
    )
    scored["delta"] = scored["adjusted_score"] - scored["attractiveness_score"]

    scored["rank_stored"] = scored["attractiveness_score"].rank(
        ascending=False, method="min"
    )
    scored["rank_adjusted"] = scored["adjusted_score"].rank(
        ascending=False, method="min"
    )
    scored["rank_change"] = scored["rank_stored"] - scored["rank_adjusted"]

    def _format_rank_change(value: float) -> str:
        if pd.isna(value) or value == 0:
            return "—"
        arrow = "▲" if value > 0 else "▼"
        return f"{arrow} {abs(int(value))}"

    scored["rank_change_display"] = scored["rank_change"].apply(_format_rank_change)
    scored = scored.sort_values("adjusted_score", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------- summary
    moved_up = int((scored["rank_change"] > 0).sum())
    moved_down = int((scored["rank_change"] < 0).sum())
    avg_abs_delta = scored["delta"].abs().mean()

    metric_cols = st.columns(4)
    metric_cols[0].metric("Opportunity spaces scored", len(scored))
    metric_cols[1].metric("Moved up in rank", moved_up)
    metric_cols[2].metric("Moved down in rank", moved_down)
    metric_cols[3].metric("Avg. score change", f"{avg_abs_delta:.1f} pts")

    if missing_count:
        st.caption(
            f"{missing_count} opportunity space(s) in the current view are "
            "missing one or more stored component scores and are excluded "
            "from this sandbox."
        )

    # --------------------------------------------------------------- table
    display_columns = {
        "code": "Code",
        "name": "Opportunity space",
        "attractiveness_score": "Stored score",
        "adjusted_score": "Your score",
        "delta": "Change",
        "rank_change_display": "Position change",
    }

    available = [c for c in display_columns if c in scored.columns]

    st.caption("Click a row's checkbox to open that opportunity's detail page.")

    table_event = st.dataframe(
        scored[available].rename(columns=display_columns),
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="scoring_table",
        column_config={
            "Stored score": st.column_config.NumberColumn(format="%.1f"),
            "Your score": st.column_config.NumberColumn(format="%.1f"),
            "Change": st.column_config.NumberColumn(format="%+.1f"),
        },
    )

    # st.dataframe's on_select reports the selected row(s) as *positional*
    # indices into the dataframe passed to it — which line up 1:1 with
    # "scored" here since it was reset_index()'d right before display, and
    # nothing reorders it afterwards. "id" isn't part of the displayed
    # columns, so it's looked up from "scored" itself rather than from
    # what's on screen.
    selected_rows = (
        table_event.get("selection", {}).get("rows", []) if table_event else []
    )
    if selected_rows:
        selected_index = selected_rows[0]
        if 0 <= selected_index < len(scored) and "id" in scored.columns:
            _go_to_detail(scored.iloc[selected_index]["id"])

    # ------------------------------------------------------------- scatter
    st.markdown("### Stored score vs. your score")
    st.caption(
        "Points above the dashed line score higher under your weights than "
        "the stored formula; points below score lower. On the line, your "
        "weights make no difference for that opportunity."
    )

    figure = go.Figure()

    axis_min = 0
    axis_max = 100

    figure.add_trace(
        go.Scatter(
            x=[axis_min, axis_max],
            y=[axis_min, axis_max],
            mode="lines",
            line=dict(color=C.GREY_MED, width=1, dash="dot"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    figure.add_trace(
        go.Scatter(
            x=scored["attractiveness_score"],
            y=scored["adjusted_score"],
            mode="markers",
            marker=dict(
                color=C.ORANGE,
                size=10,
                opacity=0.85,
                line=dict(color=C.WHITE, width=1),
            ),
            customdata=scored[["code", "name"]],
            hovertemplate=(
                "%{customdata[0]} · %{customdata[1]}"
                "<br>Stored: %{x:.1f}"
                "<br>Yours: %{y:.1f}"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    figure.update_layout(height=420)
    figure.update_xaxes(range=[axis_min, axis_max])
    figure.update_yaxes(range=[axis_min, axis_max])

    theme.style_axes(
        figure,
        x_title="Stored attractiveness score",
        y_title="Your attractiveness score",
    )

    st.plotly_chart(figure, width="stretch")


def render(data: dict, df: pd.DataFrame) -> None:
    theme.banner(
        "Scoring model & simulator",
        "The backend's formula, and a sandbox to test alternative weightings",
    )

    _render_formula()

    weights = _render_weight_sliders()
    _render_recalculated_list(df, weights)