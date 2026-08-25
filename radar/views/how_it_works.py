"""Page 6 — the pipeline, the schema, and honest caveats.

Vanessa's advice was to focus less on the dashboard and more on the process
behind it, and the client's own feedback was "don't focus too much on the
dashboard, their perspective is more about a structured process to discover the
opportunity space, what is behind it". This page is that answer.
"""

from __future__ import annotations

import streamlit as st

from radar import theme

PIPELINE = """
```
  ┌──────────────────────────────────────────────────────────────┐
  │ 1. COLLECTION AGENT        Azure AI Foundry + Bing grounding │
  │    Searches independent regulators, trade press, competitor  │
  │    coverage. Never an Orange-owned source. Returns strict    │
  │    JSON only.                                                │
  └───────────────────────────┬──────────────────────────────────┘
                              │  one row per article
  ┌───────────────────────────▼──────────────────────────────────┐
  │ 2. signals TABLE           Azure SQL Database                │
  │    Deduplicated on source_url, then on source_name + title.  │
  │    Each summary embedded with text-embedding-3-large,        │
  │    stored as VECTOR(1536).                                   │
  └───────────────────────────┬──────────────────────────────────┘
                              │  cosine similarity > 0.82
  ┌───────────────────────────▼──────────────────────────────────┐
  │ 3. CLUSTERING              pure SQL, union-find in Python    │
  │    Groups of 3+ semantically related signals. A single       │
  │    article never becomes an opportunity on its own.          │
  └───────────────────────────┬──────────────────────────────────┘
                              │
  ┌───────────────────────────▼──────────────────────────────────┐
  │ 4. CAPABILITY CHECK        skip logic                        │
  │    Compared against Orange's deployed capabilities including │
  │    geographic scope. Already sold here? Skipped, not scored. │
  └───────────────────────────┬──────────────────────────────────┘
                              │
  ┌───────────────────────────▼──────────────────────────────────┐
  │ 5. SCORING + EXTRACTION                                      │
  │    4 components computed from data, 1 judged by the model.   │
  │    Near-duplicate opportunities merged.                      │
  └───────────────────────────┬──────────────────────────────────┘
                              │
  ┌───────────────────────────▼──────────────────────────────────┐
  │ 6. opportunity_spaces TABLE  →  this dashboard                │
  └──────────────────────────────────────────────────────────────┘
```
"""


def render(data: dict, df) -> None:
    theme.banner("How it works", "The pipeline behind the numbers, and what to be careful about")

    st.markdown("### From an article to an opportunity")
    st.markdown(PIPELINE)

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

    st.markdown("### Built by")
    st.markdown(
        """
BeCode AI and Data Science bootcamp, two-week project.

Gunay Bayramova (team lead) · Victor Courtois (repo and tech lead) ·
Mahalakshmi Palanivel (data architect) · Anna Diacofotaki (documentation)
        """
    )
