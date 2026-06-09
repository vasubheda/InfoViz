"""Quality-adjusted price (proposal feature 5): price normalised by purity.

Raw $/g vs purity-adjusted cost ($/g per %purity) per substance. Normalising
for potency reorders the "true" market cost: a cheap-but-impure drug can be more
expensive per effective unit than a pricier, purer one.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure


@memoize_figure()
def quality_adjusted_price(data, filtered_combined, selection, height=420):
    df = filtered_combined
    df = df[(df["Substance"] != "Other") & (df["Typical"] > 0)]
    if len(df) == 0:
        return helpers.empty_fig("No price/purity data for selected filters",
                                 height)

    df = df.copy()
    df["qap"] = df["Typical_USD"] / df["Typical"]
    g = df.groupby("Substance").agg(
        raw=("Typical_USD", "mean"), purity=("Typical", "mean"),
        qap=("qap", "mean")).reset_index()
    # Order by quality-adjusted cost so the "true" ranking reads top-down.
    g = g.sort_values("qap")

    colors = [data.substance_color_map.get(s, theme.TOL_MUTED[0])
              for s in g["Substance"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=g["Substance"], x=g["raw"], orientation="h", name="Raw $/g",
        marker_color=theme.GRID, opacity=0.9,
        hovertemplate="Raw price: $%{x:.2f}/g<extra>%{y}</extra>"))
    fig.add_trace(go.Bar(
        y=g["Substance"], x=g["qap"], orientation="h",
        name="Quality-adjusted ($/g per %purity)", marker_color=colors,
        customdata=g[["purity"]],
        hovertemplate=("Quality-adjusted: $%{x:.3f} per %purity<br>"
                       "Mean purity: %{customdata[0]:.1f}%<extra>%{y}</extra>")))

    fig.update_layout(
        title="Raw vs quality-adjusted price by substance",
        barmode="group", height=height, plot_bgcolor=theme.PLOT_BG,
        xaxis=dict(title="USD", gridcolor=theme.GRID),
        yaxis=dict(gridcolor=theme.GRID),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        margin=dict(l=120, r=30, t=70, b=50))
    return fig
