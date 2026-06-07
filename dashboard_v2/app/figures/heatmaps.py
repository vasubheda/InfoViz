"""Retail / wholesale price heatmaps (region x substance) for Q2."""
import plotly.graph_objects as go

from .. import theme
from . import helpers


def price_heatmap(data, filtered_prices, price_level, selection):
    if len(filtered_prices) == 0:
        return helpers.empty_fig("No data available", 400)
    latest = filtered_prices["Year"].max()
    sub = filtered_prices[
        (filtered_prices["Year"] == latest)
        & (filtered_prices["LevelOfSale"] == price_level)
    ].copy()
    if len(sub) == 0:
        return helpers.empty_fig(f"No {price_level.lower()} data", 400)
    sub["RegionShort"] = sub["SubRegion"].str.replace(" Europe", "", regex=False)
    hm = sub.pivot_table(values="Typical_USD", index="RegionShort",
                         columns="Substance", aggfunc="mean")
    fig = go.Figure(go.Heatmap(
        z=hm.values, x=list(hm.columns), y=list(hm.index),
        colorscale=theme.SEQUENTIAL, hoverongaps=False,
        colorbar=dict(title="USD/g", thickness=15, len=0.7, x=1.02),
        hovertemplate="Region: %{y}<br>Substance: %{x}<br>$%{z:.2f}/g<extra></extra>"))

    # Highlight the brushed cell.
    sel_region = (selection.get("subregion") or "")
    sel_region = sel_region.replace(" Europe", "")
    sel_sub = selection.get("substance")
    if sel_region in hm.index and sel_sub in hm.columns:
        ri = list(hm.index).index(sel_region)
        ci = list(hm.columns).index(sel_sub)
        fig.add_shape(type="rect", x0=ci - 0.5, x1=ci + 0.5,
                      y0=ri - 0.5, y1=ri + 0.5,
                      line=dict(color=theme.ACCENT, width=4))
    fig.update_layout(title=f"{price_level} prices ({latest})",
                      xaxis_title="Substance", yaxis_title="European region",
                      height=400, plot_bgcolor="white",
                      margin=dict(l=110, r=80, t=50, b=50))
    return fig
