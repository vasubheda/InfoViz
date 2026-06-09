"""Multivariate views: per-substance regression facets (Q1)."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .. import theme
from . import helpers
from .cache import memoize_figure

LABELS = {"Typical_USD": "Price (USD/g)", "Typical": "Purity (%)",
          "Kilograms": "Kilograms seized"}


@memoize_figure()
def regression_facets(data, filtered_combined, x_axis, y_axis):
    """Per-substance scatter + OLS line; returns (figure, stats_children)."""
    from dash import html
    subs = sorted(s for s in filtered_combined["Substance"].unique() if s != "Other")
    if len(subs) == 0 or len(filtered_combined) == 0:
        return helpers.empty_fig("No data for selected filters", 400), \
            "No correlation data available"
    ncols = min(3, len(subs))
    nrows = int(np.ceil(len(subs) / ncols))
    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=subs,
                        horizontal_spacing=0.1, vertical_spacing=0.15)
    results = []
    for i, sub in enumerate(subs):
        r, c = i // ncols + 1, i % ncols + 1
        s = filtered_combined[filtered_combined["Substance"] == sub]
        if len(s) >= 2:
            fig.add_trace(go.Scatter(
                x=s[x_axis], y=s[y_axis], mode="markers", name=sub,
                marker=dict(color=data.substance_color_map.get(sub, theme.TOL_MUTED[0]),
                            size=9, opacity=0.7, line=dict(width=1, color="white")),
                showlegend=False,
                hovertemplate=f"{LABELS[x_axis]}: %{{x:.2f}}<br>"
                              f"{LABELS[y_axis]}: %{{y:.2f}}<extra></extra>"),
                row=r, col=c)
            if s[x_axis].std() > 0 and s[y_axis].std() > 0:
                z = np.polyfit(s[x_axis], s[y_axis], 1)
                xs = np.linspace(s[x_axis].min(), s[x_axis].max(), 50)
                fig.add_trace(go.Scatter(x=xs, y=np.poly1d(z)(xs), mode="lines",
                              line=dict(color=theme.ACCENT, width=2, dash="dash"),
                              showlegend=False, hoverinfo="skip"), row=r, col=c)
                results.append(f"{sub}: r={s[x_axis].corr(s[y_axis]):.3f}")
            else:
                results.append(f"{sub}: N/A (no variance)")
        else:
            results.append(f"{sub}: N/A (n<2)")
        fig.update_xaxes(title_text=LABELS[x_axis], row=r, col=c, gridcolor=theme.GRID)
        fig.update_yaxes(title_text=LABELS[y_axis], row=r, col=c, gridcolor=theme.GRID)
    fig.update_layout(height=max(400, 300 * nrows), showlegend=False,
                      title_text=f"{LABELS[y_axis]} vs {LABELS[x_axis]} by substance",
                      plot_bgcolor=theme.PLOT_BG)
    stats = html.Div([html.Strong("Correlation coefficients: "), html.Br(),
                      *[html.Div(r) for r in results]])
    return fig, stats
