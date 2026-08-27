"""Innovation Radar dashboard package.

The Streamlit entry point is ``app.py`` at the repository root. Everything the
app needs lives here:

    radar.config        constants, colours, scoring weights
    radar.data          loading opportunity spaces / signals (Azure SQL or snapshot)
    radar.personas      the Strategist / Sales / Presales filter presets
    radar.theme         Orange Business styling and shared Plotly layout
    radar.views         one module per dashboard page

The attractiveness formula itself lives in scripts/scores.py, on the pipeline
side. The dashboard only ever displays the score the pipeline stored.
"""

__all__ = ["config", "data", "personas", "theme", "views"]
           
