"""
Orange Business Belgium — Innovation Radar
Competitive Intelligence Dashboard (MVP)

Data model: signals -> opportunity_space_signals -> opportunity_spaces (live Azure SQL)
Run with:  streamlit run app.py
"""

import os
import time
import pyodbc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------------------
# PAGE CONFIG + ORANGE BUSINESS BRANDING
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Orange Business | Innovation Radar",
    page_icon="🟠",
    layout="wide",
    initial_sidebar_state="expanded",
)

ORANGE = "#FF7900"
ORANGE_DARK = "#D06A00"
BLACK = "#000000"
GREY_DARK = "#333333"
GREY_MED = "#666666"
GREY_LIGHT = "#F2F2F2"
WHITE = "#FFFFFF"

# Matches the real CHECK constraint on opportunity_spaces.status
STATUSES = ["candidate", "kept", "rejected", "watchlist"]

STATUS_COLORS = {
    "watchlist": "#B7B7B7",
    "candidate": "#FFB27A",
    "kept": ORANGE,
    "rejected": "#4A4A4A",
}

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {WHITE}; }}
    section[data-testid="stSidebar"] {{ background-color: {BLACK}; }}
    section[data-testid="stSidebar"] * {{ color: {WHITE} !important; }}
    div[data-baseweb="radio"] label {{ color: {WHITE} !important; }}
    h1, h2, h3 {{ color: {BLACK}; font-family: 'Helvetica Neue', sans-serif; }}
    .obx-banner {{
        background-color: {BLACK}; color: {WHITE}; padding: 18px 24px;
        border-left: 8px solid {ORANGE}; margin-bottom: 18px; border-radius: 4px;
    }}
    .obx-banner h1 {{ color: {WHITE}; margin: 0; font-size: 26px; }}
    .obx-banner p {{ color: {GREY_LIGHT}; margin: 4px 0 0 0; font-size: 14px; }}
    .obx-card {{
        background-color: {GREY_LIGHT}; border-radius: 8px; padding: 14px 18px;
        border-top: 4px solid {ORANGE}; margin-bottom: 10px;
    }}
    .obx-summary {{
        background-color: {WHITE}; border: 1px solid #E0E0E0; border-radius: 6px;
        padding: 14px 16px; font-size: 15px; line-height: 1.5; margin-bottom: 8px;
    }}
    .obx-pill {{
        display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px;
        font-weight: 600; color: {WHITE}; background-color: {ORANGE};
    }}
    div.stButton > button {{ background-color: {ORANGE}; color: {WHITE}; border: none; font-weight: 600; }}
    div.stButton > button:hover {{ background-color: {ORANGE_DARK}; color: {WHITE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# DATABASE CONNECTION
# ----------------------------------------------------------------------------
SQL_SERVER = os.environ["SQL_SERVER"]
SQL_DATABASE = os.environ["SQL_DATABASE"]
SQL_USER = os.environ["SQL_USER"]
SQL_PASSWORD = os.environ["SQL_PASSWORD"]

SQL_CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{SQL_SERVER},1433;"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
)


def connect_with_retry(max_retries: int = 5, initial_wait: int = 10):
    """Azure SQL serverless (auto-pause) databases can take 30-60s to wake up
    from a paused state on the first connection after inactivity."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return pyodbc.connect(SQL_CONN_STRING, timeout=30)
        except pyodbc.OperationalError as e:
            last_error = e
            wait = initial_wait * attempt
            time.sleep(wait)
    raise last_error


@st.cache_data(ttl=300)  # refresh from DB at most every 5 minutes
def load_data():
    conn = connect_with_retry()
    try:
        opp_df = pd.read_sql("SELECT * FROM opportunity_spaces", conn)
        sig_df = pd.read_sql("SELECT * FROM signals", conn)
        link_df = pd.read_sql("SELECT * FROM opportunity_space_signals", conn)
    finally:
        conn.close()
    return opp_df, sig_df, link_df


opp_df, sig_df, link_df = load_data()

if opp_df.empty:
    st.warning("No opportunity spaces found in the database yet. Run the extraction pipeline first.")
    st.stop()

# session-state store so "promote to active" demo actions persist during the session
if "status_overrides" not in st.session_state:
    st.session_state.status_overrides = {}


def get_effective_status(row):
    return st.session_state.status_overrides.get(row["id"], row["status"])


opp_df = opp_df.copy()
opp_df["status"] = opp_df.apply(get_effective_status, axis=1)


def classify_horizon(urgency):
    # urgency_time_horizon is on a 0-100 scale
    if urgency >= 66:
        return "Now"
    elif urgency >= 33:
        return "Next"
    return "Later"


opp_df["time_horizon"] = opp_df["urgency_time_horizon"].apply(classify_horizon)

VERTICALS = sorted(opp_df["vertical"].dropna().unique().tolist())
TECHNOLOGIES = sorted(opp_df["technology"].dropna().unique().tolist())

# ----------------------------------------------------------------------------
# SIDEBAR — NAVIGATION + GLOBAL FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("## 🟠 Orange Business")
st.sidebar.caption("Innovation Radar · Belgium")

PAGE = st.sidebar.radio(
    "Navigate",
    [
        "🎯 Radar Dashboard",
        "📊 Opportunity Spaces",
        "📡 Signal Explorer",
        "⭐ Watchlist",
        "🕒 Time Horizon Board",
        "⚙️ Scoring Methodology",
        "ℹ️ About / Data Model",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
f_verticals = st.sidebar.multiselect("Vertical", VERTICALS, default=[])
f_tech = st.sidebar.multiselect("Technology", TECHNOLOGIES, default=[])
f_status = st.sidebar.multiselect("Status", STATUSES, default=[])
f_min_attract = st.sidebar.slider("Min. attractiveness score", 0, 100, 0, 1)


def apply_filters(df):
    out = df.copy()
    if f_verticals:
        out = out[out["vertical"].isin(f_verticals)]
    if f_tech:
        out = out[out["technology"].isin(f_tech)]
    if f_status:
        out = out[out["status"].isin(f_status)]
    out = out[out["attractiveness_score"] >= f_min_attract]
    return out


st.sidebar.markdown("---")
st.sidebar.caption(f"Live data from Azure SQL · {len(opp_df)} opportunity spaces · {len(sig_df)} signals")
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# PAGE: RADAR DASHBOARD
# ----------------------------------------------------------------------------
def page_radar():
    st.markdown(
        f"""<div class="obx-banner"><h1>🎯 Innovation Radar</h1>
        <p>Competitor opportunity spaces plotted by vertical (sector) and time horizon (ring)</p></div>""",
        unsafe_allow_html=True,
    )

    df = apply_filters(opp_df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opportunity Spaces", len(df))
    c2.metric("Kept", int((df["status"] == "kept").sum()))
    c3.metric("Watchlist", int((df["status"] == "watchlist").sum()))
    c4.metric("Avg. Attractiveness", f"{df['attractiveness_score'].mean():.1f}" if len(df) else "–")

    if df.empty:
        st.warning("No opportunity spaces match the current filters.")
        return

    ring_map = {"Now": 1.0, "Next": 2.0, "Later": 3.0}
    df = df.copy()
    df["ring_base"] = df["time_horizon"].map(ring_map)
    rng = np.random.default_rng(7)
    df["r"] = df["ring_base"] - rng.uniform(0.05, 0.45, size=len(df))
    df["theta"] = df["vertical"]

    fig = px.scatter_polar(
        df, r="r", theta="theta",
        color="status", size="attractiveness_score",
        size_max=26,
        color_discrete_map=STATUS_COLORS,
        hover_name="name",
        hover_data={
            "technology": True, "use_case": True, "attractiveness_score": ":.1f",
            "r": False, "theta": False,
        },
    )
    fig.update_polars(
        radialaxis=dict(
            range=[0, 3], tickvals=[0.5, 1.5, 2.5], ticktext=["Now", "Next", "Later"],
            showline=False, gridcolor="#DDDDDD",
        ),
        angularaxis=dict(gridcolor="#DDDDDD"),
        bgcolor=WHITE,
    )
    fig.update_layout(height=650, paper_bgcolor=WHITE, legend_title_text="Status", font_color=GREY_DARK)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Ring = time horizon (Now → Later, inner to outer). Sector = vertical. Bubble size = attractiveness score. Color = status.")

    with st.expander("View underlying opportunity spaces"):
        st.dataframe(
            df[["name", "vertical", "technology", "status", "time_horizon", "attractiveness_score"]]
            .sort_values("attractiveness_score", ascending=False),
            use_container_width=True, hide_index=True,
        )


# ----------------------------------------------------------------------------
# PAGE: OPPORTUNITY SPACES (list + drill-down)
# ----------------------------------------------------------------------------
def page_opportunity_spaces():
    st.markdown(
        f"""<div class="obx-banner"><h1>📊 Opportunity Spaces</h1>
        <p>Vertical × Use Case × Technology — scored and tracked</p></div>""",
        unsafe_allow_html=True,
    )
    df = apply_filters(opp_df).sort_values("attractiveness_score", ascending=False)
    st.dataframe(
        df[["name", "vertical", "use_case", "technology", "status",
            "time_horizon", "attractiveness_score", "total_articles", "distinct_sources"]],
        use_container_width=True, hide_index=True,
    )

    st.markdown("### Detail view")
    if df.empty:
        st.info("No opportunity spaces to display.")
        return
    selected_id = st.selectbox(
        "Select opportunity space",
        df["id"].tolist(),
        format_func=lambda x: df.loc[df["id"] == x, "name"].values[0],
    )
    row = df[df["id"] == selected_id].iloc[0]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""<div class="obx-card">
            <span class="obx-pill">{row['status'].upper()}</span>
            <h3>{row['name']}</h3>
            <p>
                <b>Vertical:</b> {row['vertical']} &nbsp;|&nbsp;
                <b>Use case:</b> {row['use_case']} &nbsp;|&nbsp;
                <b>Technology:</b> {row['technology']}
            </p>
        </div>""", unsafe_allow_html=True)

        if pd.notna(row.get("detailed_summary")):
            st.markdown("#### Overview")
            st.markdown(f"<div class='obx-summary'>{row['detailed_summary']}</div>", unsafe_allow_html=True)
            st.divider()

        st.markdown("#### Why it's hot")
        st.write(row.get("why_hot") or "—")

        st.markdown("#### Why it matters to Orange")
        st.write(row.get("why_matters") or "—")

        st.markdown("#### Recommended next action")
        st.write(row.get("next_action") or "—")

        if pd.notna(row.get("capability_check_note")):
            with st.expander("🔍 Capability verification note"):
                st.caption(
                    "What the agent checked against Orange's known capabilities before "
                    "creating this opportunity (Step 0 freshness check)."
                )
                st.write(row["capability_check_note"])

        created = row.get("created_at")
        updated = row.get("updated_at")
        st.caption(
            f"📅 Created {created} · Last updated {updated} · "
            f"Based on {row['total_articles']} article(s) from {row['distinct_sources']} distinct source(s)"
        )

        st.divider()

        linked_signal_ids = link_df[link_df["opportunity_space_id"] == row["id"]]["signal_id"]
        linked_signals = sig_df[sig_df["id"].isin(linked_signal_ids)]
        st.markdown(f"**Supporting signals ({len(linked_signals)})**")

        for _, sig in linked_signals.iterrows():
            title = sig.get("title") or "(untitled)"
            with st.expander(f"📰 {sig['source_name']} — {title}"):
                meta_bits = []
                if pd.notna(sig.get("publication_date")):
                    meta_bits.append(f"Published: {sig['publication_date']}")
                if pd.notna(sig.get("country")):
                    meta_bits.append(f"Country: {sig['country']}")
                if pd.notna(sig.get("targeted_vertical")):
                    meta_bits.append(f"Vertical: {sig['targeted_vertical']}")
                if meta_bits:
                    st.caption(" · ".join(meta_bits))

                if pd.notna(sig.get("summary")):
                    st.write(sig["summary"])
                if pd.notna(sig.get("raw_excerpt")):
                    st.markdown(f"> {sig['raw_excerpt']}")
                if pd.notna(sig.get("source_url")):
                    st.markdown(f"[Open original article]({sig['source_url']})")

    with col2:
        radar_fig = go.Figure()
        dims = ["market_signal_strength", "source_diversity_score", "evidence_quality",
                "urgency_time_horizon", "strategic_relevance"]
        labels = ["Market signal", "Source diversity", "Evidence quality", "Urgency/timing", "Strategic fit"]
        values = [row[d] for d in dims] + [row[dims[0]]]
        radar_fig.add_trace(go.Scatterpolar(
            r=values, theta=labels + [labels[0]], fill="toself",
            line_color=ORANGE, fillcolor="rgba(255,121,0,0.35)",
        ))
        radar_fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False, height=380, margin=dict(t=20, b=20),
        )
        st.plotly_chart(radar_fig, use_container_width=True)
        st.metric("Attractiveness score", f"{row['attractiveness_score']:.1f}")

        st.markdown("**Score breakdown**")
        for dim, label in zip(dims, labels):
            st.progress(min(row[dim] / 100, 1.0), text=f"{label}: {row[dim]:.1f}")

        st.divider()

        new_status = st.selectbox("Update status", STATUSES, index=STATUSES.index(row["status"]), key="status_update")
        if st.button("Save status"):
            st.session_state.status_overrides[row["id"]] = new_status
            st.rerun()


# ----------------------------------------------------------------------------
# PAGE: SIGNAL EXPLORER
# ----------------------------------------------------------------------------
def page_signal_explorer():
    st.markdown(
        f"""<div class="obx-banner"><h1>📡 Signal Explorer</h1>
        <p>Raw external signals feeding the opportunity spaces</p></div>""",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    f_source = c1.multiselect("Source", sorted(sig_df["source_name"].dropna().unique().tolist()))
    f_country = c2.multiselect("Country", sorted(sig_df["country"].dropna().unique().tolist()))

    df = sig_df.copy()
    if f_source:
        df = df[df["source_name"].isin(f_source)]
    if f_country:
        df = df[df["country"].isin(f_country)]

    fig1 = px.histogram(df, x="targeted_vertical", color_discrete_sequence=[ORANGE],
                         title="Signals by targeted vertical")
    fig1.update_layout(showlegend=False, height=320, paper_bgcolor=WHITE)
    st.plotly_chart(fig1, use_container_width=True)

    st.dataframe(
        df[["source_name", "title", "targeted_vertical", "country", "publication_date"]]
        .sort_values("publication_date", ascending=False),
        use_container_width=True, hide_index=True,
    )


# ----------------------------------------------------------------------------
# PAGE: WATCHLIST
# ----------------------------------------------------------------------------
def page_watchlist():
    st.markdown(
        f"""<div class="obx-banner"><h1>⭐ Watchlist</h1>
        <p>Early-stage topics kept for monitoring before becoming a full opportunity space</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("""
**Watchlist logic:** a topic stays on the watchlist — instead of being marked `kept` — when it has
**low source diversity**, **weak evidence quality**, or **insufficient article volume** despite an
interesting theme. Promote it to `candidate` or `kept` using the controls below or on the detail page.
    """)

    watch_df = opp_df[opp_df["status"] == "watchlist"].sort_values("attractiveness_score", ascending=False)
    if watch_df.empty:
        st.info("Nothing on the watchlist under the current filters.")
        return

    for _, row in apply_filters(watch_df).iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{row['name']}** — {row['vertical']} · {row['use_case']}")
            st.caption(f"{row['total_articles']} articles / {row['distinct_sources']} sources · score {row['attractiveness_score']:.1f}")
        with col2:
            st.write(f"Horizon: **{row['time_horizon']}**")
        with col3:
            if st.button("Promote → candidate", key=f"promote_{row['id']}"):
                st.session_state.status_overrides[row["id"]] = "candidate"
                st.rerun()
        st.markdown("---")


# ----------------------------------------------------------------------------
# PAGE: TIME HORIZON BOARD
# ----------------------------------------------------------------------------
def page_time_horizon():
    st.markdown(
        f"""<div class="obx-banner"><h1>🕒 Time Horizon Board</h1>
        <p>Now / Next / Later classification of opportunity spaces</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("""
**Time horizon logic:** each opportunity space's `urgency_time_horizon` score (0–100, based on
signal recency) is bucketed as: **Now** ≥ 66 · **Next** 33–66 · **Later** < 33.
    """)

    df = apply_filters(opp_df)
    cols = st.columns(3)
    for col, horizon, color in zip(cols, ["Now", "Next", "Later"], [ORANGE, "#FFB27A", "#B7B7B7"]):
        with col:
            st.markdown(f"<h3 style='color:{color}'>{horizon}</h3>", unsafe_allow_html=True)
            sub = df[df["time_horizon"] == horizon].sort_values("attractiveness_score", ascending=False)
            for _, row in sub.iterrows():
                st.markdown(f"""<div class="obx-card">
                    <b>{row['name']}</b><br>
                    <span style="font-size:12px;color:{GREY_MED}">{row['vertical']} · score {row['attractiveness_score']:.1f}</span>
                </div>""", unsafe_allow_html=True)
            if sub.empty:
                st.caption("No items.")


# ----------------------------------------------------------------------------
# PAGE: SCORING METHODOLOGY (interactive weights)
# ----------------------------------------------------------------------------
def page_scoring():
    st.markdown(
        f"""<div class="obx-banner"><h1>⚙️ Attractiveness Scoring Methodology</h1>
        <p>How opportunity spaces are ranked</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Adjust weights to see how the ranking of top opportunity spaces would change "
        "(session-only preview — the default weights below match what's actually stored in the database)."
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    w_market = c1.slider("Market signal strength", 0.0, 1.0, 0.30, 0.05)
    w_source = c2.slider("Source diversity", 0.0, 1.0, 0.20, 0.05)
    w_evid = c3.slider("Evidence quality", 0.0, 1.0, 0.15, 0.05)
    w_urg = c4.slider("Urgency / time horizon", 0.0, 1.0, 0.15, 0.05)
    w_strat = c5.slider("Strategic relevance", 0.0, 1.0, 0.20, 0.05)
    total_w = w_market + w_source + w_evid + w_urg + w_strat
    if total_w == 0:
        st.error("At least one weight must be greater than zero.")
        return

    df = opp_df.copy()
    df["custom_score"] = (
        w_market * df["market_signal_strength"] + w_source * df["source_diversity_score"]
        + w_evid * df["evidence_quality"] + w_urg * df["urgency_time_horizon"]
        + w_strat * df["strategic_relevance"]
    ) / total_w

    st.latex(r"""
    \text{attractiveness} = \frac{w_1 \cdot \text{market} + w_2 \cdot \text{diversity} + w_3 \cdot \text{evidence} + w_4 \cdot \text{urgency} + w_5 \cdot \text{strategic}}{\sum w_i}
    """)

    top = df.sort_values("custom_score", ascending=False).head(10)
    fig = px.bar(
        top, x="custom_score", y="name", orientation="h",
        color_discrete_sequence=[ORANGE],
        title="Top 10 opportunity spaces under current weights",
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), height=450, paper_bgcolor=WHITE)
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------------
# PAGE: ABOUT / DATA MODEL
# ----------------------------------------------------------------------------
def page_about():
    st.markdown(
        f"""<div class="obx-banner"><h1>ℹ️ About this Radar</h1>
        <p>Orange Business Belgium — competitive innovation intelligence, MVP</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
### Purpose
This radar tracks competitor and market signals across the verticals and technologies Orange
Business is tracking, turning them into scored, actionable opportunity spaces.

### Data model (live, Azure SQL)
- **`signals`** — raw external evidence (articles, filings, press releases).
- **`opportunity_spaces`** — a structured `Vertical × Use Case × Technology` combination, scored
  on five dimensions and rolled up into an `attractiveness_score` (0-100).
- **`opportunity_space_signals`** — many-to-many link table connecting evidence to opportunity spaces.

### Current data
{len(opp_df)} opportunity spaces, {len(sig_df)} signals, refreshed from the database
(cached for 5 minutes — use "🔄 Refresh data" in the sidebar to force an update).
    """)


# ----------------------------------------------------------------------------
# ROUTER
# ----------------------------------------------------------------------------
PAGES = {
    "🎯 Radar Dashboard": page_radar,
    "📊 Opportunity Spaces": page_opportunity_spaces,
    "📡 Signal Explorer": page_signal_explorer,
    "⭐ Watchlist": page_watchlist,
    "🕒 Time Horizon Board": page_time_horizon,
    "⚙️ Scoring Methodology": page_scoring,
    "ℹ️ About / Data Model": page_about,
}

PAGES[PAGE]()