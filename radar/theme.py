"""Orange Business styling and one shared Plotly layout.

Colour strategy, decided deliberately:

The app uses **no categorical colour palette at all**. Every chart is either a
single-hue sequential ramp (magnitude), one flat orange (a single series), or
recessive grey (grid, axes, non-data ink). Two reasons:

1. The obvious categorical field, ``status``, is NULL on every row the pipeline
   writes, so colouring by it produces one flat grey chart that looks broken.
2. A single-hue ramp is read by lightness, which means it stays legible under
   every form of colour-vision deficiency and in greyscale print without
   needing a validated multi-hue palette. The ramp in config.ORANGE_RAMP was
   checked for monotonic lightness steps.

Where a chart needs to distinguish two kinds of thing (code-computed versus
LLM-judged sub-scores), that distinction is carried by a **text label and an
icon**, never by colour alone.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from radar import config as C


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {C.WHITE}; }}

        /* --------------------------------------------------------------
         * Trim Streamlit's default top space.
         * Two separate things add empty space above the content: (1) the
         * toolbar/header bar Streamlit renders at the very top of the
         * viewport (visible as the "⋮" menu), which has its own reserved
         * height, and (2) generous top padding Streamlit adds to the
         * first block of both the main content area and the sidebar to
         * clear that header. With this app's own banner already carrying
         * the page title, both add up to a large empty gap before
         * anything shows up on screen.
         *
         * Every selector below is listed twice — once scoped to a
         * data-testid container, once as a bare class — because the exact
         * DOM/testid names Streamlit uses for these containers have
         * changed across versions. Unmatched selectors are simply inert,
         * so this is safe to keep even after a Streamlit upgrade.
         * -------------------------------------------------------------- */
        header[data-testid="stHeader"] {{
            height: 2.25rem;
            min-height: 2.25rem;
        }}
        div[data-testid="stAppViewContainer"] .main .block-container,
        div[data-testid="stMainBlockContainer"],
        .main .block-container {{
            padding-top: 1rem !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"],
        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
        section[data-testid="stSidebar"] .block-container,
        section[data-testid="stSidebar"] > div:first-child > div:first-child {{
            padding-top: 1rem !important;
        }}

        section[data-testid="stSidebar"] {{ background-color: {C.BLACK}; }}
        section[data-testid="stSidebar"] * {{ color: {C.WHITE} !important; }}

        h1, h2, h3 {{
            color: {C.BLACK};
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }}

        .obx-banner {{
            background-color: {C.BLACK};
            color: {C.WHITE};
            padding: 18px 24px;
            border-left: 8px solid {C.ORANGE};
            margin-bottom: 18px;
            border-radius: 4px;
        }}
        .obx-banner h1 {{ color: {C.WHITE}; margin: 0; font-size: 26px; }}
        .obx-banner p {{ color: {C.GREY_LIGHT}; margin: 4px 0 0 0; font-size: 14px; }}

        .obx-card {{
            background-color: {C.GREY_LIGHT};
            border-radius: 8px;
            padding: 16px 20px;
            border-top: 4px solid {C.ORANGE};
            margin-bottom: 12px;
        }}
        .obx-card h3 {{ margin-top: 4px; }}

        .obx-pill {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: {C.WHITE};
            background-color: {C.ORANGE};
        }}
        .obx-pill-muted {{ background-color: {C.GREY_MED}; }}

        .obx-note {{
            border-left: 3px solid {C.ORANGE};
            background: {C.ORANGE_PALE};
            padding: 10px 14px;
            border-radius: 0 4px 4px 0;
            font-size: 13px;
            color: {C.GREY_DARK};
            margin-bottom: 12px;
        }}

        div.stButton > button {{
            background-color: {C.ORANGE};
            color: {C.WHITE};
            border: none;
            font-weight: 600;
        }}
        div.stButton > button:hover {{
            background-color: {C.ORANGE_DARK};
            color: {C.WHITE};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def register_plotly_template() -> None:
    """One template so every chart shares type, grid weight and spacing."""
    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(
            family="Helvetica Neue, Helvetica, Arial, sans-serif",
            size=13,
            color=C.GREY_DARK,
        ),
        paper_bgcolor=C.WHITE,
        plot_bgcolor=C.WHITE,
        colorway=[C.ORANGE],           # single series default
        margin=dict(t=48, b=40, l=48, r=24),
        xaxis=dict(showgrid=False, linecolor=C.GREY_BORDER),
        yaxis=dict(showgrid=True, gridcolor=C.GREY_BORDER, zeroline=False),
    )
    pio.templates["orange_business"] = template
    pio.templates.default = "plotly_white+orange_business"


def banner(title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="obx-banner"><h1>{title}</h1><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )


def note(text: str) -> None:
    st.markdown(f"""<div class="obx-note">{text}</div>""", unsafe_allow_html=True)


def style_axes(fig, y_title: str = "", x_title: str = ""):
    """Recessive grid and axes: the data should be the darkest thing present."""
    fig.update_xaxes(
        showgrid=False,
        linecolor=C.GREY_BORDER,
        title_text=x_title,
        title_font_size=12,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=C.GREY_BORDER,
        gridwidth=1,
        zeroline=False,
        linecolor="rgba(0,0,0,0)",
        title_text=y_title,
        title_font_size=12,
    )
    fig.update_layout(
        paper_bgcolor=C.WHITE,
        plot_bgcolor=C.WHITE,
        font_color=C.GREY_DARK,
        margin=dict(t=48, b=40, l=48, r=24),
    )
    return fig