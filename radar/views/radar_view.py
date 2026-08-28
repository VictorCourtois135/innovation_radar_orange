"""Page 1 - the radar itself.

Encoding, and why
-----------------

    radius = urgency, continuously — the ring boundaries are the same
             thresholds data.classify_horizon uses, so a bubble's distance from
             the centre means "how soon" both within a ring and across rings
    ring   = the horizon it lands in (Now / Next / Later) — drawn as concentric
             bands and named in annotations, not colour
    colour = status (Candidate / Watchlist / Validated / Rejected), solid fill —
             this is the one thing on the page a reader needs to separate at a
             glance across the whole chart, so it gets the whole colour channel
    sector = vertical group
    size   = attractiveness score
    label  = the opportunity code, printed on every bubble

What changed, and the measurement behind it
-------------------------------------------
Colour used to encode time horizon, with status relegated to a thin marker
border. Two problems with that:

* horizon was already fully legible from ring position (radius) and from the
  ring annotations/backdrop — colour was carrying the same information twice;
* status — which the reader can't get from position at all — was squeezed into
  a 3px outline, the weakest channel on the chart, on top of an already-busy
  fill colour.

So the assignment has been swapped: fill colour is now status, solid (not just
an outline), and horizon has been left to do its existing job through ring
position alone. Because colour now varies *within* each horizon trace rather
than being constant per trace, the horizon legend can no longer show a single
correct swatch per entry — so horizon counts are shown as plain annotations
instead, and a proper status legend is built from small dummy traces so each
status gets its own correct-coloured swatch.

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

# Solid fill colour per status. Keys are matched case-insensitively against the
# "status" column; anything unmatched falls back to "unknown".
STATUS_FILL_COLORS = {
    "candidate": "#F5C518",   # yellow
    "watchlist": "#4D1FF5",   # orange
    "validated": "#2E9E4F",   # green
    "rejected": "#D93B3B",    # red
    "unknown": C.GREY_MED,
}

STATUS_LABELS = {
    "candidate": "Candidate",
    "watchlist": "Watchlist",
    "validated": "Validated",
    "rejected": "Rejected",
    "unknown": "Unknown",
}


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


def _status_key(status) -> str:
    key = str(status).strip().lower()
    return key if key in STATUS_FILL_COLORS else "unknown"


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
    """Alternating-contrast bands behind each ring, so Now/Next/Later read as
    three distinct zones on sight, not just from the axis gridlines.

    Colour no longer marks horizon (that channel now belongs to status), so
    the zones need a non-hue cue instead: greyscale shade, stepped up and down
    band to band (zebra-striping) rather than a single flat tint, since a
    monotonic gradient would make Now and Later look like more/less of the
    same thing rather than three separate zones.

    Each band is drawn as an annulus: the outer edge anticlockwise, the inner
    edge back clockwise, closed with ``fill="toself"``. The innermost band
    (Now) is a plain filled circle since it has no inner edge to reverse.
    """
    outer = list(np.linspace(0, 360, 181))
    inner = outer[::-1]

    bands = [
        (0.0, 1.0, "rgba(17,17,17,0.065)"),   # Now  — darker
        (1.0, 2.0, "rgba(17,17,17,0.022)"),   # Next — lighter
        (2.0, 3.0, "rgba(17,17,17,0.065)"),   # Later — darker again
    ]

    for low, high, fillcolor in bands:
        if low == 0.0:
            r = [high] * len(outer)
            theta = outer
        else:
            r = [high] * len(outer) + [low] * len(inner)
            theta = outer + inner
        fig.add_trace(
            go.Scatterpolar(
                r=r,
                theta=theta,
                mode="lines",
                line=dict(width=0),
                fill="toself",
                fillcolor=fillcolor,
                hoverinfo="skip",
                showlegend=False,
            )
        )


def render(data: dict, df) -> None:
    theme.banner(
        "Discover verified opportunities across horizons",
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

    # One trace per status, not per horizon. Each trace now has a single solid
    # colour, which is what lets the legend actually control the data: a click
    # can isolate "only Rejected" because Rejected *is* a trace, rather than a
    # colour scattered across three horizon-traces that all show/hide together.
    # Ring position (radius) still comes from horizon via plot_df["r"], computed
    # earlier — splitting by status here doesn't touch that.
    status_order = ["candidate", "watchlist", "validated", "rejected", "unknown"]
    plot_df["_status_key"] = plot_df["status"].fillna(C.STATUS_UNKNOWN).map(_status_key)

    for key in status_order:
        subset = plot_df[plot_df["_status_key"] == key]
        if subset.empty:
            continue
        subset_size = sized.loc[subset.index]
        fig.add_trace(
            go.Scatterpolar(
                r=subset["r"],
                theta=subset["theta"],
                mode="markers+text",
                name=STATUS_LABELS[key],
                showlegend=True,
                text=[
                    _format_radar_label(technology) if code in top_label_codes else ""
                    for code, technology in zip(subset["code"], subset["technology"])
                ],
                textposition="top center",
                textfont=dict(size=11, color=C.GREY_DARK),
                marker=dict(
                    size=subset_size,
                    sizemode="area",
                    # One shared reference across all five status traces, so a
                    # bubble in one trace is comparable in area to any other.
                    sizeref=(2.0 * float(sized.max())) / (36.0 ** 2),
                    sizemin=8,
                    color=STATUS_FILL_COLORS[key],
                    opacity=0.92,
                    line=dict(width=1.5, color=C.WHITE),
                ),
                customdata=np.stack([
                    subset["name"].astype(str),
                    subset["code"].astype(str),
                    subset["technology"].astype(str),
                    subset["use_case"].astype(str),
                    scores.loc[subset.index].astype(float),
                    subset["vertical"].astype(str),
                    subset.get("countries", pd.Series("Unknown", index=subset.index)).astype(str),
                    subset["time_horizon"].astype(str),
                ], axis=-1),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]} · %{customdata[5]}<br>"
                    "Technology: %{customdata[2]}<br>"
                    "Use case: %{customdata[3]}<br>"
                    "Attractiveness: %{customdata[4]:.1f} / 100<br>"
                    "Horizon: %{customdata[7]}<br>"
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
    # space. With colour no longer tied to horizon, these annotations (plus the
    # ring boundaries themselves) are now the only source for horizon names —
    # counts are appended here since the legend no longer carries them either.
    label_deg = (spokes[-1] + step_deg / 2.0) if spokes else 45.0
    horizon_counts = plot_df["time_horizon"].value_counts().to_dict()
    ring_annotations = [
        dict(
            text=f"{horizon} ({horizon_counts.get(horizon, 0)})",
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
            xanchor="center", x=0.5,
            font=dict(size=12),
        ),
        # Plotly's default is click=toggle-this-one, double-click=isolate.
        # Swapped here so a single click on a status does what was asked —
        # shows only that status's bubbles, hiding the rest — and a
        # double-click on an already-isolated status switches it off on its
        # own instead. Clicking any status again restores everyone (Plotly's
        # native behaviour once nothing is isolated).
        legend_itemclick="toggleothers",
        legend_itemdoubleclick="toggle",
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
        "Ring = time horizon (labelled on the chart), inner being most urgent. "
        "Sector = vertical group. Colour = status — yellow candidate, orange "
        "watchlist, green validated, red rejected. Bubble size = attractiveness "
        "score, and every bubble is labelled with its code — the exact numbers "
        "are in the table below."
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
                            "time_horizon", "status", "attractiveness_score",
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
                "status": "Status",
                "attractiveness_score": st.column_config.ProgressColumn(
                    "Attractiveness", min_value=0, max_value=100, format="%.1f",
                ),
                "total_articles": "Articles",
                "distinct_sources": "Sources",
            },
        )
