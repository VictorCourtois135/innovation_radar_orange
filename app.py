"""Orange Business — Innovation Radar.

Streamlit entry point. This file is deliberately thin: it sets up the page,
builds the sidebar, and dispatches to one module per page under radar/views/.
Everything else lives in the radar package.

Run it with:

    streamlit run app.py

Data comes from Azure SQL when credentials are available and from the
committed CSV snapshot otherwise. See radar/data.py and the README for the
details.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Orange Business | Innovation Radar",
    page_icon="🟠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from radar import config as C          # noqa: E402
from radar import data as data_module  # noqa: E402
from radar import personas, theme      # noqa: E402
from radar.views import (              # noqa: E402
    detail,
    how_it_works,
    methodology,
    opportunities,
    radar_view,
    signals,
)

theme.inject_css()
theme.register_plotly_template()

# Two separate sidebar issues are fixed here:
#
# 1. Spacing: Streamlit's default vertical gap between sidebar widgets
#    (radios, multiselects, the slider) is generous enough that the filter
#    block reads as sparse and disconnected rather than one grouped
#    section.
#
#    The larger gap above "Orange Business" itself doesn't come from the
#    content area at all — recent Streamlit versions render a separate
#    `stSidebarHeader` block above the content, reserved for the sidebar's
#    own collapse/expand arrow, with its own fixed height. That's the
#    empty space the title was sitting below. It's shrunk directly here
#    (with `!important` since Streamlit sets some of this inline) so the
#    title can sit as high as the sidebar allows.
#
# 2. Overscroll bounce: scrolling the sidebar up past its own top (common
#    on trackpads) rubber-bands the whole sidebar content down for a
#    moment, which visibly shoves "Orange Business" downward and leaves a
#    blank gap above it before it springs back. `overscroll-behavior:
#    contain` stops that bounce from happening at all.
#
# Several selectors are targeted together for both fixes since the exact
# container Streamlit uses has changed across versions, and not every
# version exposes the same data-testid.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
        overscroll-behavior: contain;
    }

    section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
        min-height: 0 !important;
        height: auto !important;
        padding: 0.25rem 0.5rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
        padding-top: 0 !important;
    }
    /* stSidebarHeader still reserves a bit of fixed height beyond its own
       padding (room for the collapse arrow). Pulling the first content
       block up with a negative margin closes that remaining gap directly,
       rather than continuing to chase whatever internal height rule is
       causing it. */
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] > div:first-child {
        margin-top: -4.5rem;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.35rem;
    }
    section[data-testid="stSidebar"] .element-container {
        margin-bottom: 0.1rem;
    }
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0.1rem;
    }
    /* The `gap` above still leaves visible daylight between filter widgets
       (multiselects, the slider, the "---" dividers) because each widget
       also carries its own internal top/bottom margin on top of that gap.
       A negative margin on every element in the sidebar collapses that
       remaining space directly. */
    section[data-testid="stSidebar"] .element-container {
        margin-top: -0.0rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = {
    "Radar": radar_view.render,
    "Top opportunities": opportunities.render,
    "Opportunity detail": detail.render,
    "Signal explorer": signals.render,
    "Scoring model & simulator": methodology.render,
    "How it works": how_it_works.render,
}

# ---------------------------------------------------------------------------
# Load once, share with every page
# ---------------------------------------------------------------------------
data = data_module.load_data()
opp_df = data["opportunities"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🟠 Orange Business")
st.sidebar.caption("Innovation Radar")

# A page can't write directly to st.session_state["page_name"] once the
# radio below has been instantiated this run (Streamlit forbids mutating a
# widget's own key after creation). So other pages request navigation by
# setting "pending_page" instead; it's consumed here, BEFORE the radio is
# created, which is allowed.
if "pending_page" in st.session_state:
    st.session_state["page_name"] = st.session_state.pop("pending_page")

page_name = st.sidebar.radio(
    "Go to", list(PAGES.keys()), label_visibility="collapsed", key="page_name",
)

st.sidebar.markdown("---")

# --- persona presets -------------------------------------------------------
st.sidebar.markdown("### View as")
persona = st.sidebar.radio(
    "Persona", list(personas.PERSONAS.keys()), label_visibility="collapsed"
)
st.sidebar.caption(personas.PERSONAS[persona]["blurb"])

# --- filters -----------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")

if opp_df.empty:
    st.sidebar.info("No data loaded.")
    filtered = opp_df
else:
    verticals = sorted(opp_df["vertical"].dropna().unique().tolist())
    technologies = sorted(opp_df["technology"].dropna().unique().tolist())
    horizons = [h for h in C.HORIZONS if h in set(opp_df["time_horizon"])]

    f_vertical = st.sidebar.multiselect("Vertical", verticals)
    f_tech = st.sidebar.multiselect("Technology", technologies)
    f_horizon = st.sidebar.multiselect("Time horizon", horizons)
    f_min = st.sidebar.slider("Minimum attractiveness", 0, 100, 0, 5)

    filtered = opp_df.copy()
    if f_vertical:
        filtered = filtered[filtered["vertical"].isin(f_vertical)]
    if f_tech:
        filtered = filtered[filtered["technology"].isin(f_tech)]
    if f_horizon:
        filtered = filtered[filtered["time_horizon"].isin(f_horizon)]
    filtered = filtered[filtered["attractiveness_score"].fillna(0) >= f_min]

    filtered = personas.apply(filtered, persona)

# --- provenance --------------------------------------------------------------
st.sidebar.markdown("---")
if data["source"] == "azure_sql":
    st.sidebar.success("🟢 Live · Azure SQL")
else:
    st.sidebar.warning("🟡 CSV snapshot")
st.sidebar.caption(
    f"{len(opp_df)} opportunity spaces · {len(data['signals'])} signals"
)
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
if data["note"]:
    st.info(data["note"], icon="ℹ️")

caveat = personas.caveat(persona)
if caveat:
    st.caption(caveat)

PAGES[page_name](data, filtered)