"""Page 1 - the radar itself.

Encoding, and why
-----------------

    radius = urgency, continuously — the ring boundaries are the same
             thresholds data.classify_horizon uses, so a bubble's distance from
             the centre means "how soon" both within a ring and across rings
    hue    = the ring it lands in (Now / Next / Later), so it is nameable
    sector = vertical group
    size   = attractiveness score
    label  = the opportunity code, printed on every bubble

What changed, and the measurement behind it
-------------------------------------------
The earlier version encoded ``attractiveness_score`` as **both** colour and
size, and described that as deliberate redundancy. Redundant encoding is a real
technique, but it only works when the variable actually varies across the range
you give it. Here it did not:

* the seven stored scores span **48.8 to 76.1**, while ``range_color`` was set to
  ``(0, 100)`` - so every bubble landed in the same narrow band of the ramp and
  came out the same mid-orange, with half the colour bar covering values no row
  has;
* Plotly sizes bubbles by area, so 48.8 against 76.1 is a radius ratio of 0.80 -
  visually near-identical too.

Two channels, one variable, nothing readable from either. So colour has been
moved to the one thing on this page a reader actually needs to separate at a
glance - the horizon ring - and size has been given an explicit ``sizeref`` fitted
to the data instead of the default, so the spread that does exist is visible.

The number itself is no longer left to a colour bar: every bubble is labelled
with its code, the hover carries the score, and the table below repeats it. That
also satisfies the contrast relief the palette requires (see ``theme``).

Angular collisions
------------------
``vertical`` is free text, so seven opportunities produced seven single-point
spokes and a mostly empty circle. Bubbles are now placed on the coarse vertical
*group*, and any two landing on the same spoke are fanned apart by a small,
deterministic angular offset instead of drawing on top of each other.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from radar import config as C
from radar import theme

# Radial band each horizon occupies. Inner = more urgent.
RING_BOUNDS = {"Now": (0.15, 0.95), "Next": (1.15, 1.95), "Later": (2.15, 2.95)}
RING_MAX = 3.0
TOP_LABEL_COUNT = 10

def _format_radar_label(value) -> str:
    """Split a technology label over two short lines."""
    words = str(value).strip().split()

    if len(words) <= 1:
        return str(value).strip()

    midpoint = (len(words) + 1) // 2
    first_line = " ".join(words[:midpoint])
    second_line = " ".join(words[midpoint:])

    return f"{first_line}<br>{second_line}"


def _radius_for(row) -> float:
    """Radius from the actual urgency score, not from random jitter.

    The first version scattered each bubble at a random radius inside its ring.
    That looked like a placement decision but carried no information, and worse,
    it *implied* one: a reader comparing two bubbles in the Next ring would take
    the inner one for the more urgent, when the difference was a random draw.

    Urgency runs 0-100 and the ring boundaries are the same thresholds
    ``data.classify_horizon`` uses, so each ring's band maps straight onto its
    slice of the score. Radius decreases as urgency rises, so "closer to the
    centre" means "sooner" everywhere on the chart, not just between rings.
    """
    horizon = row.get("time_horizon", "Later")
    low, high = RING_BOUNDS.get(horizon, RING_BOUNDS["Later"])

    urgency = pd.to_numeric(pd.Series([row.get("urgency_time_horizon")]),
                            errors="coerce").iloc[0]
    if pd.isna(urgency):
        return (low + high) / 2.0

    score_bands = {
        "Now": (C.HORIZON_NOW, 100.0),
        "Next": (C.HORIZON_NEXT, C.HORIZON_NOW),
        "Later": (0.0, C.HORIZON_NEXT),
    }
    band_low, band_high = score_bands.get(horizon, (0.0, C.HORIZON_NEXT))
    span = max(band_high - band_low, 1e-6)
    position = min(max((float(urgency) - band_low) / span, 0.0), 1.0)
    return high - position * (high - low)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Give every opportunity an (angle, radius) that does not collide."""
    plot_df = df.copy()

    plot_df["vertical_group"] = [C.vertical_group(v) for v in plot_df["vertical"]]

    # One spoke per group present, evenly spaced. Sorted so the layout is stable
    # between reruns and between filter changes.
    groups = sorted(plot_df["vertical_group"].unique())
    step = 360.0 / max(len(groups), 1)
    base_angle = {group: index * step for index, group in enumerate(groups)}

    thetas: list[float] = []
    radii: list[float] = []
    # How many bubbles are already on this spoke, so the n-th one is fanned off
    # centre rather than drawn on top of the first.
    group_sizes = plot_df["vertical_group"].value_counts().to_dict()

    seen: dict[str, int] = {}

    for _, row in plot_df.iterrows():
        group = row["vertical_group"]
        index = seen.get(group, 0)
        seen[group] = index + 1

        # Spread every bubble evenly across the available sector instead of
        # repeatedly placing crowded bubbles at the same maximum offset.
        group_size = group_sizes[group]

        if group_size == 1:
            offset = 0.0
        else:
            sector_limit = step * 0.42
            offsets = np.linspace(-sector_limit, sector_limit, group_size)
            offset = float(offsets[index])

        thetas.append(base_angle[group] + offset)
        radii.append(_radius_for(row))

    plot_df["theta"] = thetas
    plot_df["r"] = radii
    return plot_df


def _ring_backdrop(fig: go.Figure) -> None:
    """A faint band behind the middle ring, so the three zones read as zones.

    Drawn as an annulus: the outer edge anticlockwise, the inner edge back
    clockwise, closed with ``fill="toself"``. Without the reversed inner arc the
    fill would cross the centre and shade the Now ring too.
    """
    outer = list(np.linspace(0, 360, 181))
    inner = outer[::-1]
    low, high = 1.0, 2.0
    fig.add_trace(
        go.Scatterpolar(
            r=[high] * len(outer) + [low] * len(inner),
            theta=outer + inner,
            mode="lines",
            line=dict(width=0),
            fill="toself",
            fillcolor="rgba(17,17,17,0.028)",
            hoverinfo="skip",
            showlegend=False,
        )
    )


def render(data: dict, df) -> None:
    theme.banner(
        "Find the opportunity before the competitor does",
        "Opportunity spaces by vertical (sector) and time horizon (ring)",
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

    plot_df = _prepare(df)
    top_label_codes = set(
    plot_df.nlargest(TOP_LABEL_COUNT, "attractiveness_score")["code"]
)
    groups = sorted(plot_df["vertical_group"].unique())

    # Size: fit the reference to the data actually on screen rather than letting
    # Plotly pick one, so a 27-point spread in score is a visible spread in area.
    scores = pd.to_numeric(plot_df["attractiveness_score"], errors="coerce")
    top = float(scores.max()) if scores.notna().any() else 100.0
    floor = float(scores.min()) if scores.notna().any() else 0.0
    # Subtract a baseline below the smallest score so the weakest opportunity is
    # a small dot rather than a large one. Clamped so it can never go negative.
    baseline = max(0.0, floor - 0.35 * max(top - floor, 1.0))
    sized = (scores - baseline).clip(lower=1.0)

    fig = go.Figure()
    _ring_backdrop(fig)

    for horizon in C.HORIZONS:
        subset = plot_df[plot_df["time_horizon"] == horizon]
        if subset.empty:
            continue
        subset_size = sized.loc[subset.index]
        fig.add_trace(
            go.Scatterpolar(
                r=subset["r"],
                theta=subset["theta"],
                mode="markers+text",
                name=f"{horizon} ({len(subset)})",
                text=[
                    _format_radar_label(technology) if code in top_label_codes else ""
                    for code, technology in zip(subset["code"], subset["technology"])
                ],
                textposition="top center",
                textfont=dict(size=11, color=C.GREY_DARK),
                marker=dict(
                    size=subset_size,
                    sizemode="area",
                    # One shared reference across all three traces, so a bubble in
                    # the Later ring is comparable to one in the Now ring.
                    sizeref=(2.0 * float(sized.max())) / (36.0 ** 2),
                    sizemin=8,
                    color=C.HORIZON_COLORS[horizon],
                    opacity=0.88,
                    line=dict(width=3, color=[
                        C.STATUS_COLORS.get(
                            status,
                            C.STATUS_COLORS[C.STATUS_UNKNOWN],
                        )
                        for status in subset["status"].fillna(C.STATUS_UNKNOWN)
                    ],
                ),
                ),
                customdata=np.stack([
                    subset["name"].astype(str),
                    subset["code"].astype(str),
                    subset["technology"].astype(str),
                    subset["use_case"].astype(str),
                    scores.loc[subset.index].astype(float),
                    subset["vertical"].astype(str),
                    subset.get("countries", pd.Series("Unknown", index=subset.index)).astype(str),
                ], axis=-1),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]} · %{customdata[5]}<br>"
                    "Technology: %{customdata[2]}<br>"
                    "Use case: %{customdata[3]}<br>"
                    "Attractiveness: %{customdata[4]:.1f} / 100<br>"
                    "Markets: %{customdata[6]}"
                    "<extra></extra>"
                ),
            )
        )

    step_deg = 360.0 / max(len(groups), 1)
    spokes = [index * step_deg for index in range(len(groups))]

    # Ring names used to be radial tick labels, which Plotly draws inside the
    # plotting area along one radius — they landed on top of the bubbles and,
    # rotated upright, read as broken text. They are drawn instead as plain
    # annotations on the emptiest half-sector, horizontal, so they sit in white
    # space. The legend names the same three rings by colour, so this is a
    # convenience label rather than the only route to the information.
    label_deg = (spokes[-1] + step_deg / 2.0) if spokes else 45.0
    ring_annotations = [
        dict(
            text=horizon,
            showarrow=False,
            font=dict(size=11, color=C.GREY_MED),
            xref="paper", yref="paper",
            x=0.5 + 0.5 * (radius / RING_MAX) * np.cos(np.radians(label_deg + 90)),
            y=0.5 + 0.5 * (radius / RING_MAX) * np.sin(np.radians(label_deg + 90)),
        )
        for horizon, radius in zip(C.HORIZONS, (0.6, 1.6, 2.6))
    ]

    fig.update_polars(
        radialaxis=dict(
            range=[0, RING_MAX],
            tickvals=[1.0, 2.0, 3.0],
            ticktext=["", "", ""],   # gridlines kept, labels moved out (above)
            showline=False,
            gridcolor=C.GREY_BORDER,
        ),
        angularaxis=dict(
            tickmode="array",
            tickvals=spokes,
            ticktext=groups,
            gridcolor=C.GREY_BORDER,
            linecolor=C.GREY_BORDER,
            tickfont=dict(size=12, color=C.GREY_DARK),
            rotation=90,
            direction="clockwise",
        ),
        bgcolor=C.WHITE,
        # Leave room around the circle so long sector names are not clipped.
        domain=dict(x=[0.04, 0.96], y=[0.02, 0.94]),
    )
    fig.update_layout(
        height=1000,
        paper_bgcolor=C.WHITE,
        font_color=C.GREY_DARK,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="top", y=1.0,
            xanchor="center", x=0.5, title_text="Time horizon  ",
            font=dict(size=12),
        ),
        annotations=ring_annotations,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    empty_rings = [h for h in C.HORIZONS if not (plot_df["time_horizon"] == h).any()]
    if empty_rings:
        st.caption(
            f"The {', '.join(empty_rings)} ring is empty under the current "
            "filters. The ring is still drawn, because an empty horizon is "
            "itself a finding — nothing here is slow-moving."
        )

    st.caption(
        "Ring and colour both = time horizon, inner and orange being the most "
        "urgent. Sector = vertical group. Bubble size = attractiveness score, "
        "and every bubble is labelled with its code — the exact numbers are in "
        "the table below."
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

    with st.expander("Table view of the same data", expanded=True):
        table = plot_df.copy()
        cols = [c for c in ["code", "name", "vertical_group", "vertical", "technology",
                            "time_horizon", "attractiveness_score",
                            "total_articles", "distinct_sources", "countries"]
                if c in table.columns]
        st.dataframe(
            table[cols].sort_values("attractiveness_score", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "code": "Code",
                "vertical_group": "Vertical group",
                "vertical": "Vertical (as written by the agent)",
                "time_horizon": "Horizon",
                "attractiveness_score": st.column_config.ProgressColumn(
                    "Attractiveness", min_value=0, max_value=100, format="%.1f",
                ),
                "total_articles": "Articles",
                "distinct_sources": "Sources",
            },
        )
