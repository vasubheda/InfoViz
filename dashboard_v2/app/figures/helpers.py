"""Shared figure helpers: empty-state figures, geo maps, and the imputation
marker styling used to visually flag originally-missing values.
"""
import plotly.graph_objects as go

from .. import theme


def empty_fig(msg: str, height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_layout(height=height, plot_bgcolor="white",
                      margin=dict(l=20, r=20, t=20, b=20))
    return fig


def filter_note_fig(height: int = 400) -> go.Figure:
    """Placeholder shown for cross-country views while a country filter is active.

    These views (regional heatmaps, choropleths) only make sense across all of
    Europe; rendering them for a hand-picked subset would mislead, so we replace
    the figure with a short instruction instead.
    """
    return empty_fig(
        "Clear the country filter (select all countries) to compare across markets.",
        height,
    )


def base_geo_layout(fig: go.Figure, height: int = 400, right_margin: int = 0):
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(margin=dict(l=0, r=right_margin, t=30, b=0),
                      height=height, clickmode="event+select")
    return fig


def imputed_legend_note():
    """A short reusable caption describing the hollow-marker convention."""
    return "◌ hollow / dotted markers mark imputed (originally-missing) values"


def marker_line_for_imputed(is_imputed_series, base_color, imputed_color="#000000"):
    """Return per-point marker-line colours: dark dotted ring on imputed points."""
    return [imputed_color if bool(v) else base_color for v in is_imputed_series]


def split_imputed_symbols(is_imputed_series):
    """Per-point symbols: hollow circle for imputed, solid for observed."""
    return ["circle-open" if bool(v) else "circle" for v in is_imputed_series]
