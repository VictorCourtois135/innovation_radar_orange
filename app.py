"""
Orange Business Belgium — Innovation Radar
Competitive Intelligence Dashboard (MVP)

Data model mirrors: signals -> opportunity_space_signals -> opportunity_spaces
Run with:  streamlit run app.py
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

STATUS_COLORS = {
    "watchlist": "#B7B7B7",
    "candidate": "#FFB27A",
    "active": ORANGE,
    "archived": "#4A4A4A",
}

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {WHITE}; }}
    section[data-testid="stSidebar"] {{
        background-color: {BLACK};
    }}
    section[data-testid="stSidebar"] * {{ color: {WHITE} !important; }}
    div[data-baseweb="radio"] label {{ color: {WHITE} !important; }}
    h1, h2, h3 {{ color: {BLACK}; font-family: 'Helvetica Neue', sans-serif; }}
    .obx-banner {{
        background-color: {BLACK};
        color: {WHITE};
        padding: 18px 24px;
        border-left: 8px solid {ORANGE};
        margin-bottom: 18px;
        border-radius: 4px;
    }}
    .obx-banner h1 {{ color: {WHITE}; margin: 0; font-size: 26px; }}
    .obx-banner p {{ color: {GREY_LIGHT}; margin: 4px 0 0 0; font-size: 14px; }}
    .obx-card {{
        background-color: {GREY_LIGHT};
        border-radius: 8px;
        padding: 14px 18px;
        border-top: 4px solid {ORANGE};
        margin-bottom: 10px;
    }}
    .obx-pill {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        color: {WHITE};
        background-color: {ORANGE};
    }}
    div.stButton > button {{
        background-color: {ORANGE};
        color: {WHITE};
        border: none;
        font-weight: 600;
    }}
    div.stButton > button:hover {{ background-color: {ORANGE_DARK}; color: {WHITE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# TAXONOMIES (matches schema + slide "ideas for extra content")
# ----------------------------------------------------------------------------
VERTICALS = [
    "Industry", "Retail", "IT and services", "Finance", "FMCG",
    "Automotive & Mobility", "Healthcare & Life Sciences",
    "Energy & Utilities", "Logistics & Transport",
]

TECHNOLOGIES = [
    "Sovereign Cloud / Cloud Avenue", "Cloud MVP Legacy Migration",
    "AI-Orchestrated Micro-SOC", "Anti-Drone / Airspace Defense",
    "Unified CRM-CCaaS", "Data Quality & Governance",
    "Sovereign LLM Hosting", "Edge & IoT Analytics", "Fiber / Fixed Network",
]

USE_CASES = [
    "Legacy database modernization", "Multilingual LLM hosting (EU sovereignty)",
    "Critical-site drone detection", "Autonomous threat triage",
    "Unified contact-center experience", "Automated data lineage & quality",
    "Cloud data lake migration", "Predictive maintenance via IoT",
    "Fixed-fiber B2B connectivity",
]

SIGNAL_TYPES = ["regulation", "analyst_report", "press_release", "news"]
SIGNAL_CATEGORIES = [
    "trend", "regulation", "buying_signal", "market_move",
    "technology_maturity", "proof_signal",
]
STATUSES = ["watchlist", "candidate", "active", "archived"]

COMPETITORS = [
    "Deutsche Telekom", "Vodafone", "Telefónica", "AT&T", "Verizon",
    "BT Group", "Lumen Technologies", "MTN Group", "IBM Consulting", "Proximus",
]

# ----------------------------------------------------------------------------
# MOCK DATA GENERATION (stand-in for the SQL database until connected)
# ----------------------------------------------------------------------------
@st.cache_data
def generate_data(seed: int = 42):
    rng = random.Random(seed)
    np.random.seed(seed)

    n_opps = 34
    opp_rows = []
    for i in range(1, n_opps + 1):
        vertical = rng.choice(VERTICALS)
        tech = rng.choice(TECHNOLOGIES)
        use_case = rng.choice(USE_CASES)
        market_signal = round(np.random.beta(2, 2), 2)
        source_diversity = round(np.random.beta(2, 2), 2)
        evidence_quality = round(np.random.beta(2, 2), 2)
        urgency_timing = round(np.random.beta(2, 2), 2)
        strategic_rel = round(np.random.beta(2, 2), 2)
        attractiveness = round(
            0.25 * market_signal + 0.15 * source_diversity + 0.20 * evidence_quality
            + 0.20 * urgency_timing + 0.20 * strategic_rel, 3
        )
        status = rng.choices(STATUSES, weights=[0.30, 0.25, 0.35, 0.10])[0]
        total_articles = rng.randint(1, 14)
        distinct_sources = rng.randint(1, min(total_articles, 8))
        opp_rows.append({
            "id": i,
            "code": f"OS-{i:03d}",
            "vertical": vertical,
            "use_case": use_case,
            "technology": tech,
            "name": f"{tech} for {vertical}",
            "why_hot": f"Competitors accelerating {tech.lower()} adoption in {vertical.lower()}.",
            "why_now": f"Recent {use_case.lower()} signals surged in the last quarter.",
            "next_action": rng.choice([
                "Brief Orange Business BU lead", "Draft solution one-pager",
                "Schedule competitor teardown", "Monitor for 30 more days",
            ]),
            "capability_gap": rng.choice([
                "None — ready to pitch", "Partner needed", "Internal PoC required",
            ]),
            "status": status,
            "market_signal_strength": market_signal,
            "source_diversity": source_diversity,
            "evidence_quality": evidence_quality,
            "urgency_timing": urgency_timing,
            "strategic_relevance": strategic_rel,
            "attractiveness_score": attractiveness,
            "total_articles": total_articles,
            "distinct_sources": distinct_sources,
            "created_at": datetime(2026, 1, 1) + timedelta(days=rng.randint(0, 230)),
            "updated_at": datetime(2026, 6, 1) + timedelta(days=rng.randint(0, 60)),
        })
    opp_df = pd.DataFrame(opp_rows)

    n_signals = 140
    sig_rows = []
    for i in range(1, n_signals + 1):
        competitor = rng.choice(COMPETITORS)
        tech = rng.choice(TECHNOLOGIES)
        sig_type = rng.choice(SIGNAL_TYPES)
        sig_cat = rng.choice(SIGNAL_CATEGORIES)
        sig_rows.append({
            "id": i,
            "source_url": f"https://example.com/article-{i}",
            "source_name": rng.choice([
                "Light Reading", "RCR Wireless News", "Fierce Network",
                "BIPT / IBPT", "Ofcom", "BEREC", "Gartner", "Analysys Mason",
                "PR Newswire", f"{competitor} Newsroom", "DataCenterDynamics",
                "CSO Online", "Help Net Security",
            ]),
            "title": f"{competitor} advances {tech.lower()} strategy",
            "publication_date": datetime(2026, 1, 1) + timedelta(days=rng.randint(0, 230)),
            "target_vertical": rng.choice(VERTICALS),
            "country": rng.choice(["Belgium", "Germany", "Spain", "USA", "Global", "UK"]),
            "summary": f"{competitor} is scaling {tech.lower()} capabilities, "
                       f"outpacing legacy fixed-network operators in the region.",
            "raw_excerpt": f"\"{competitor} accelerates {tech.lower()} rollout...\"",
            "date_of_scrape": datetime(2026, 8, 1) + timedelta(days=rng.randint(0, 20)),
            "signal_type": sig_type,
            "signal_category": sig_cat,
            "competitor": competitor,
        })
    sig_df = pd.DataFrame(sig_rows)

    # link table: each opportunity space linked to 2-8 random signals
    link_rows = []
    link_id = 1
    for opp_id in opp_df["id"]:
        for sig_id in rng.sample(range(1, n_signals + 1), k=rng.randint(2, 8)):
            link_rows.append({"id": link_id, "opportunity_space_id": opp_id, "signal_id": sig_id})
            link_id += 1
    link_df = pd.DataFrame(link_rows)

    return opp_df, sig_df, link_df


opp_df, sig_df, link_df = generate_data()

# session-state store so "promote to active" demo actions persist during the session
if "status_overrides" not in st.session_state:
    st.session_state.status_overrides = {}

def get_effective_status(row):
    return st.session_state.status_overrides.get(row["id"], row["status"])

opp_df = opp_df.copy()
opp_df["status"] = opp_df.apply(get_effective_status, axis=1)


def classify_horizon(urgency):
    if urgency >= 0.66:
        return "Now"
    elif urgency >= 0.33:
        return "Next"
    return "Later"


opp_df["time_horizon"] = opp_df["urgency_timing"].apply(classify_horizon)

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
f_min_attract = st.sidebar.slider("Min. attractiveness score", 0.0, 1.0, 0.0, 0.05)

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
st.sidebar.caption("Data source: mock generator (replace with live SQL query on `signals` / `opportunity_spaces`).")

# ----------------------------------------------------------------------------
# PAGE: RADAR DASHBOARD (tech-radar style: rings = horizon, sectors = vertical)
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
    c2.metric("Active", int((df["status"] == "active").sum()))
    c3.metric("Watchlist", int((df["status"] == "watchlist").sum()))
    c4.metric("Avg. Attractiveness", f"{df['attractiveness_score'].mean():.2f}" if len(df) else "–")

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
            "technology": True, "use_case": True, "attractiveness_score": ":.2f",
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
    fig.update_layout(
        height=650, paper_bgcolor=WHITE,
        legend_title_text="Status",
        font_color=GREY_DARK,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Ring = time horizon (Now → Later, inner to outer). Sector = vertical. Bubble size = attractiveness score. Color = status.")

    with st.expander("View underlying opportunity spaces"):
        st.dataframe(
            df[["code", "name", "vertical", "technology", "status", "time_horizon", "attractiveness_score"]]
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
        df[["code", "name", "vertical", "use_case", "technology", "status",
            "time_horizon", "attractiveness_score", "total_articles", "distinct_sources"]],
        use_container_width=True, hide_index=True,
    )

    st.markdown("### Detail view")
    if df.empty:
        st.info("No opportunity spaces to display.")
        return
    selected_code = st.selectbox("Select opportunity space", df["code"])
    row = df[df["code"] == selected_code].iloc[0]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""<div class="obx-card">
            <span class="obx-pill">{row['status'].upper()}</span>
            <h3>{row['name']}</h3>
            <p><b>Vertical:</b> {row['vertical']} &nbsp;|&nbsp; <b>Use case:</b> {row['use_case']}</p>
            <p><b>Why hot:</b> {row['why_hot']}</p>
            <p><b>Why now:</b> {row['why_now']}</p>
            <p><b>Next action:</b> {row['next_action']} &nbsp;|&nbsp; <b>Capability gap:</b> {row['capability_gap']}</p>
        </div>""", unsafe_allow_html=True)

        linked_signal_ids = link_df[link_df["opportunity_space_id"] == row["id"]]["signal_id"]
        linked_signals = sig_df[sig_df["id"].isin(linked_signal_ids)]
        st.markdown(f"**Supporting signals ({len(linked_signals)})**")
        st.dataframe(
            linked_signals[["source_name", "title", "signal_type", "signal_category", "publication_date", "country"]],
            use_container_width=True, hide_index=True,
        )

    with col2:
        radar_fig = go.Figure()
        dims = ["market_signal_strength", "source_diversity", "evidence_quality",
                "urgency_timing", "strategic_relevance"]
        labels = ["Market signal", "Source diversity", "Evidence quality", "Urgency/timing", "Strategic fit"]
        values = [row[d] for d in dims] + [row[dims[0]]]
        radar_fig.add_trace(go.Scatterpolar(
            r=values, theta=labels + [labels[0]], fill="toself",
            line_color=ORANGE, fillcolor="rgba(255,121,0,0.35)",
        ))
        radar_fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False, height=380, margin=dict(t=20, b=20),
        )
        st.plotly_chart(radar_fig, use_container_width=True)
        st.metric("Attractiveness score", f"{row['attractiveness_score']:.2f}")

        new_status = st.selectbox("Update status", STATUSES, index=STATUSES.index(row["status"]), key="status_update")
        if st.button("Save status"):
            st.session_state.status_overrides[row["id"]] = new_status
            st.rerun()


# ----------------------------------------------------------------------------
# PAGE: SIGNAL EXPLORER (source type + content taxonomy)
# ----------------------------------------------------------------------------
def page_signal_explorer():
    st.markdown(
        f"""<div class="obx-banner"><h1>📡 Signal Explorer</h1>
        <p>Raw external signals feeding the opportunity spaces</p></div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    f_type = c1.multiselect("Signal type (source)", SIGNAL_TYPES)
    f_cat = c2.multiselect("Signal category (taxonomy)", SIGNAL_CATEGORIES)
    f_comp = c3.multiselect("Competitor", COMPETITORS)

    df = sig_df.copy()
    if f_type:
        df = df[df["signal_type"].isin(f_type)]
    if f_cat:
        df = df[df["signal_category"].isin(f_cat)]
    if f_comp:
        df = df[df["competitor"].isin(f_comp)]

    cc1, cc2 = st.columns(2)
    with cc1:
        fig1 = px.histogram(df, x="signal_type", color="signal_type",
                             color_discrete_sequence=px.colors.sequential.Oranges_r,
                             title="Signals by type")
        fig1.update_layout(showlegend=False, height=320, paper_bgcolor=WHITE)
        st.plotly_chart(fig1, use_container_width=True)
    with cc2:
        fig2 = px.histogram(df, x="signal_category", color="signal_category",
                             color_discrete_sequence=px.colors.sequential.Oranges_r,
                             title="Signals by taxonomy category")
        fig2.update_layout(showlegend=False, height=320, paper_bgcolor=WHITE)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Signal taxonomy — definitions")
    with st.expander("What each signal_category means"):
        st.markdown("""
- **trend** — an emerging pattern observed across multiple independent sources over time.
- **regulation** — a rule, filing, or policy change from a regulator or standards body.
- **buying_signal** — evidence a customer/market segment is actively procuring or budgeting for a capability.
- **market_move** — a competitor's strategic action: acquisition, partnership, market entry.
- **technology_maturity** — evidence a technology has crossed from pilot into production-grade deployment.
- **proof_signal** — a concrete case study, benchmark, or deployment result validating the opportunity.
        """)

    st.dataframe(
        df[["source_name", "title", "signal_type", "signal_category", "competitor",
            "target_vertical", "country", "publication_date"]].sort_values("publication_date", ascending=False),
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
**Watchlist logic:** a topic stays on the watchlist — instead of becoming a main opportunity space —
when it has **low source diversity** (fewer than 3 distinct outlets), **weak evidence quality**
(no primary source such as a regulator filing or vendor case study), or **insufficient article volume**
(fewer than 3 articles) despite an interesting theme. Once a watchlist item crosses these thresholds,
promote it to `candidate`, then `active`, using the status control below or on the detail page.
    """)

    watch_df = opp_df[opp_df["status"] == "watchlist"].sort_values("attractiveness_score", ascending=False)
    if watch_df.empty:
        st.info("Nothing on the watchlist under the current filters.")
        return

    for _, row in apply_filters(watch_df).iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{row['name']}** — {row['vertical']} · {row['use_case']}")
            st.caption(f"{row['total_articles']} articles / {row['distinct_sources']} sources · score {row['attractiveness_score']:.2f}")
        with col2:
            st.write(f"Horizon: **{row['time_horizon']}**")
        with col3:
            if st.button("Promote → candidate", key=f"promote_{row['id']}"):
                st.session_state.status_overrides[row["id"]] = "candidate"
                st.rerun()
        st.markdown("---")


# ----------------------------------------------------------------------------
# PAGE: TIME HORIZON BOARD (Now / Next / Later kanban)
# ----------------------------------------------------------------------------
def page_time_horizon():
    st.markdown(
        f"""<div class="obx-banner"><h1>🕒 Time Horizon Board</h1>
        <p>Now / Next / Later classification of opportunity spaces</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("""
**Time horizon logic:** each opportunity space's `urgency_timing` score (0–1, weighted from signal
recency, competitor deployment stage, and buying-signal density) is bucketed as follows:
**Now** ≥ 0.66 (act within this quarter) · **Next** 0.33–0.66 (plan for next 2–3 quarters) ·
**Later** < 0.33 (monitor, revisit in 6+ months).
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
                    <span style="font-size:12px;color:{GREY_MED}">{row['vertical']} · score {row['attractiveness_score']:.2f}</span>
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
    st.markdown("Adjust weights to see how the ranking of top opportunity spaces would change (session-only, does not persist to the database).")

    c1, c2, c3, c4, c5 = st.columns(5)
    w_market = c1.slider("Market signal strength", 0.0, 1.0, 0.25, 0.05)
    w_source = c2.slider("Source diversity", 0.0, 1.0, 0.15, 0.05)
    w_evid = c3.slider("Evidence quality", 0.0, 1.0, 0.20, 0.05)
    w_urg = c4.slider("Urgency / timing", 0.0, 1.0, 0.20, 0.05)
    w_strat = c5.slider("Strategic relevance", 0.0, 1.0, 0.20, 0.05)
    total_w = w_market + w_source + w_evid + w_urg + w_strat
    if total_w == 0:
        st.error("At least one weight must be greater than zero.")
        return

    df = opp_df.copy()
    df["custom_score"] = (
        w_market * df["market_signal_strength"] + w_source * df["source_diversity"]
        + w_evid * df["evidence_quality"] + w_urg * df["urgency_timing"]
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
    st.markdown("""
### Purpose
This radar tracks how Orange Business's global competitors — Deutsche Telekom, Vodafone, Telefónica,
AT&T, Verizon, BT Group, Lumen, MTN Group, IBM Consulting, and Proximus — are advancing in Cloud
Infrastructure, Cybersecurity, AI, Analytics, IoT, and Fixed/Fiber networks (5G explicitly excluded).

### Data model
- **`signals`** — raw external evidence (articles, filings, press releases) with `signal_type`
  (source: regulation / analyst_report / press_release / news) and `signal_category`
  (taxonomy: trend / regulation / buying_signal / market_move / technology_maturity / proof_signal).
- **`opportunity_spaces`** — a structured `Vertical × Use Case × Technology` combination, scored
  on five dimensions and rolled up into an `attractiveness_score`.
- **`opportunity_space_signals`** — many-to-many link table connecting evidence to opportunity spaces.

### MVP scope covered here
1. Opportunity spaces defined as Vertical × Use Case × Technology
2. Structured, refreshable process for discovering & saving opportunity spaces (status workflow)
3. Attractiveness scoring system (5-dimension weighted model, adjustable)
4. Visual radar dashboard (ring = time horizon, sector = vertical)
5. Watchlist logic for early-stage signals
6. External signal taxonomy (signal_type + signal_category)
7. Time horizon logic (Now / Next / Later)

### Next steps
Replace `generate_data()` with a live query against the production SQL database
(`signals`, `opportunity_spaces`, `opportunity_space_signals`) once connected.
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
