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

PAGES = {
    "Radar": radar_view.render,
    "Top opportunities": opportunities.render,
    "Opportunity detail": detail.render,
    "Signal explorer": signals.render,
    "Scoring methodology": methodology.render,
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

