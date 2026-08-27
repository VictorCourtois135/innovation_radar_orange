"""Page 6 — the pipeline, the schema, and honest caveats.

Vanessa's advice was to focus less on the dashboard and more on the process
behind it, and the client's own feedback was "don't focus too much on the
dashboard, their perspective is more about a structured process to discover the
opportunity space, what is behind it". This page is that answer.
"""

from __future__ import annotations
import streamlit as st
from radar import theme

def render_visual_pipeline():
    """Renders a modern visual representation of the backend data pipeline with a very light orange shade layout."""
    
    # Custom CSS to style modern VERY LIGHT ORANGE step cards and flow indicators
    st.markdown("""
        <style>
        .pipeline-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
            font-family: sans-serif;
        }
        .pipeline-card {
            background-color: #FFF7ED; /* Ultra-light warm orange/cream tint */
            border-left: 5px solid #EA580C; /* Vibrant deep orange accent edge */
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            width: 100%;
            box-shadow: 0 4px 6px -1px rgba(234, 88, 12, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border-top: 1px solid #FFEDD5;
            border-right: 1px solid #FFEDD5;
            border-bottom: 1px solid #FFEDD5;
        }
        .pipeline-header {
            color: #431407; /* Ultra-dark warm brown/black for clean contrast */
            font-weight: 700;
            font-size: 1.15rem;
            margin-bottom: 6px;
        }
        .pipeline-sub {
            color: #9A3412; /* Rich rust-orange for subtitles */
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
            font-weight: 700;
        }
        .pipeline-body {
            color: #7C2D12; /* Deep warm brown for body text */
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .pipeline-arrow {
            color: #C2410C; /* Warm orange arrows */
            font-size: 1.5rem;
            margin: 4px 0;
            font-weight: bold;
        }
        .pipeline-badge {
            background-color: #FFEDD5; /* Soft light orange badge background */
            color: #9A3412; /* Deep orange text for contrast */
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: monospace;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="pipeline-container">', unsafe_allow_html=True)

    # Step 1
    st.markdown("""
        <div class="pipeline-card">
            <div class="pipeline-sub">Step 1 — Ingestion & Grounding</div>
            <div class="pipeline-header">Collection Agent</div>
            <div class="pipeline-body">
                Searches independent regulators, trade press, and competitor coverage via 
                <span class="pipeline-badge">Azure AI Foundry + Bing grounding</span>. 
                Strictly isolates Orange-owned sources. Outputs structured JSON.
            </div>
        </div>
        <div class="pipeline-arrow">↓ <span style="font-size:0.8rem; color:#9A3412; font-family:monospace;">one row per article</span></div>
    """, unsafe_allow_html=True)

    # Step 2
    st.markdown("""
        <div class="pipeline-card" style="border-left-color: #0284C7;">
            <div class="pipeline-sub">Step 2 — Storage & Vectorization</div>
            <div class="pipeline-header">Signals Processing Table</div>
            <div class="pipeline-body">
                Stored in <span class="pipeline-badge">Azure SQL Database</span>. Deduplicated 
                rigorously on URL, then title. Article summaries are vectorized using 
                <code>text-embedding-3-large</code> into a <span class="pipeline-badge">VECTOR(1536)</span> field.
            </div>
        </div>
        <div class="pipeline-arrow">↓ <span style="font-size:0.8rem; color:#9A3412; font-family:monospace;">cosine similarity &gt; 0.82</span></div>
    """, unsafe_allow_html=True)

    # Step 3
    st.markdown("""
        <div class="pipeline-card" style="border-left-color: #059669;">
            <div class="pipeline-sub">Step 3 — Algorithmic Grouping</div>
            <div class="pipeline-header">Semantic Clustering</div>
            <div class="pipeline-body">
                Executed via pure SQL and a <span class="pipeline-badge">Python union-find</span> algorithm. 
                Groups related signals. Requires <b>3+ articles</b> to proceed; single reports never become opportunities.
            </div>
        </div>
        <div class="pipeline-arrow">↓</div>
    """, unsafe_allow_html=True)

    # Step 4
    st.markdown("""
        <div class="pipeline-card" style="border-left-color: #7C3AED;">
            <div class="pipeline-sub">Step 4 — Portfolio Alignment</div>
            <div class="pipeline-header">Capability & Geo Check</div>
            <div class="pipeline-body">
                Evaluated against Orange's deployed footprint. Existing European private-5G products are 
                automatically skipped to ensure the engine acts as a <b>market-entry tool</b>, not a product catalog.
            </div>
        </div>
        <div class="pipeline-arrow">↓</div>
    """, unsafe_allow_html=True)

    # Step 5
    st.markdown("""
        <div class="pipeline-card" style="border-left-color: #E11D48;">
            <div class="pipeline-sub">Step 5 — Synthesis</div>
            <div class="pipeline-header">Scoring & Extraction</div>
            <div class="pipeline-body">
                Computes 4 data-driven metrics and 1 qualitative model metric. Merges any near-duplicate 
                opportunity fields before final delivery.
            </div>
        </div>
        <div class="pipeline-arrow">↓</div>
    """, unsafe_allow_html=True)

    # Step 6
    st.markdown("""
        <div class="pipeline-card" style="border-left-color: #EA580C;">
            <div class="pipeline-sub">Step 6 — UI Layer</div>
            <div class="pipeline-header">Opportunity Spaces Table</div>
            <div class="pipeline-body">
                Feeds the final user-facing radar view dashboard with contextualized, traceable trends.
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)



def render(data: dict, df) -> None:
    theme.banner("How it works", "The pipeline behind the numbers, and what to be careful about")

    st.markdown("### From an article to an opportunity")
    
    # Modernized interactive visualization call
    render_visual_pipeline()

    st.markdown("### The two ideas that make this more than a news feed")
    st.markdown(
        """
**1. An opportunity needs corroboration, not a headline.**
A single article never becomes an opportunity space. Signals are embedded and
grouped by meaning, and only a cluster of three or more becomes a candidate.
Two outlets reporting the same launch in different words end up in the same
group even with no shared keywords. That is also what feeds the source
diversity score: independent sources converging on one theme is the actual
evidence that something is happening.

**2. A gap is only a gap if Orange cannot already do it.**
Before anything is scored, the cluster is checked against Orange's known
deployed capabilities, *including the geography those capabilities cover*.
Orange leads the Gartner Magic Quadrant for private 5G in Europe and Africa,
so a European private-5G story is not an opportunity. But Orange has no network
operator presence in the United States, so the same story about a US carrier
is a genuine market-entry question. Without this step the radar would keep
flagging Orange's own product catalogue as opportunities.
        """
    )

    st.markdown("### Database schema")
    st.markdown(
        """

| Table | What it holds |
|---|---|
| `signals` | One row per collected article. Source, title, publication date, country, summary, and the 1536-dimension embedding. |
| `opportunity_spaces` | One row per synthesised opportunity. Vertical, use case, technology, the narrative fields, the five sub-scores and the headline score. |
| `opportunity_space_signals` | The join table. This is the traceability: every score can be walked back to the exact articles behind it. |
        """
    )
    try:
        st.image("db_schema.png", caption="Entity relationships", use_container_width=True)
    except Exception:
        st.caption("`db_schema.png` not found in the repository root.")

    st.markdown("### Where the data on screen comes from")
    if data["source"] == "azure_sql":
        st.success(
            f"Live from Azure SQL: {len(data['opportunities'])} opportunity "
            f"spaces, {len(data['signals'])} signals."
        )
    else:
        st.warning(
            f"CSV snapshot under `data/`: {len(data['opportunities'])} opportunity "
            f"spaces, {len(data['signals'])} signals. {data['note']}"
        )

    st.markdown("### Honest caveats")
    st.markdown(
        """
- **Seven opportunity spaces from 414 signals is a low yield.** Clustering
  requires 3+ signals above 0.82 cosine similarity, which is strict. Eleven
  signals mention cybersecurity and none of them formed a cluster, which is why
  there is no cybersecurity opportunity on the radar. That is a threshold
  choice, not an absence of cyber activity in the market.
- **The prompt shapes the findings.** Adding "cybersecurity" as a keyword
  produces more cybersecurity articles. What the radar sees is a function of
  what it was told to look for, and the current prompt explicitly excludes 5G
  topics and weights 2026 most heavily.
- **`status` is never written.** The column exists and the dashboard reads it,
  but the extraction pipeline does not populate it, so every row shows as
  unclassified. Promoting an opportunity to a watchlist is not yet persisted.
- **Personas are filter presets, not model tags.** The original design had an
  `opportunity_space_personas` table with an LLM judgement per row. It did not
  survive the move from PostgreSQL to Azure SQL. The three buttons in the
  sidebar approximate the audiences using existing columns and say so.
- **Country lives on signals, not on opportunities.** The markets shown for an
  opportunity are rolled up from its linked signals, so an opportunity backed by
  articles about three countries will list three.
        """
    )
