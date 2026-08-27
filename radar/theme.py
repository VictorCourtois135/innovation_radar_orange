"""Orange Business styling and one shared Plotly layout.

Colour strategy
---------------
The previous version of this file argued for using **no categorical palette at
all** - every chart a single-hue orange ramp - on the grounds that one hue read
by lightness is always safe under colour-vision deficiency. That reasoning is
right about lightness and wrong about everything else, and the app showed it:

* On the radar, colour and size both encoded ``attractiveness_score``. The seven
  stored scores span 48.8 to 76.1 but the ramp was stretched over 0 to 100, so
  every bubble came out the same mid-orange and the colour bar spent half its
  length on a range containing no data. Two encoding channels, no readable
  variation from either.
* On every bar chart ``color=`` was set to the same column as the bar length, so
  colour restated what position already said. The identity channel was spent,
  and the charts still could not tell a regulator from a press release.
* ``opportunities.py`` already had to break the rule to ship its comparison
  chart, hard-coding three hues locally with a comment explaining that the
  single-orange template "collapses to near-identical shades". When a rule needs
  a local exception before a feature works, the rule is the problem.

So colour now does exactly one job per chart, and the four jobs live in
``config``:

    identity  -> ``config.CAT``            fixed order, brand orange in slot 1
    magnitude -> ``config.ORANGE_RAMP``    one hue, and only where nothing else
                                           already encodes that same number
    state     -> ``config.STATUS_COLORS``  reserved, always shown with its word
    no value  -> ``config.NEUTRAL``        grey, never a categorical slot

The palette was validated rather than eyeballed - ``config.py`` records the
measured colour-vision and normal-vision separations. Brand orange sits below
the 3:1 contrast mark on white, which is only allowed when the number is legible
another way, so every chart using it carries direct labels and a table view.
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
        # The full categorical order, not a single colour. A one-series chart
        # still comes out brand orange because that is slot 1; a multi-series
        # chart now gets distinguishable hues instead of five shades of orange.
        colorway=C.CAT,
        margin=dict(t=48, b=40, l=48, r=24),
        xaxis=dict(showgrid=False, linecolor=C.GREY_BORDER),
        yaxis=dict(showgrid=True, gridcolor=C.GREY_BORDER, zeroline=False),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, title_text="",
        ),
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
