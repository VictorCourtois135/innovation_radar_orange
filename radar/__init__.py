"""Innovation Radar dashboard package.

The Streamlit entry point is ``app.py`` at the repository root. Everything the
app needs lives here:

    radar.config     constants, colours, scoring weights
    radar.data       loading opportunity spaces / signals (Azure SQL or snapshot)
    radar.scoring    the attractiveness formula and its per-component breakdown
    radar.personas   the Strategist / Sales / Presales filter presets
    radar.theme      Orange Business styling and shared Plotly layout
    radar.views      one module per dashboard page
"""

__all__ = ["config", "data", "scoring", "personas", "theme", "views"]
