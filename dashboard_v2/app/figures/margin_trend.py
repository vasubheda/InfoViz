"""Q2 retail-wholesale markup over time.

Complements the latest-year price ladder: relative markup (%) per substance
across 2019-2023, so the gap reads as a trajectory (widening / narrowing) rather
than a single snapshot. Per-year margins are computed here from prices because
the inland_margin artifact is aggregated across years.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure


@memoize_figure()
def margin_trend(data, filtered_prices, selection, height=420):
    if len(filtered_prices) == 0:
        return helpers.empty_fig("No data available", height)

    # Mean retail & wholesale per (Substance, Year), then relative markup.
    agg = (filtered_prices.groupby(["Substance", "Year", "LevelOfSale"])
           ["Typical_USD"].mean().reset_index())
    piv = agg.pivot_table(values="Typical_USD",
                          index=["Substance", "Year"],
                          columns="LevelOfSale")
    if "Retail" not in piv.columns or "Wholesale" not in piv.columns:
        return helpers.empty_fig("No retail/wholesale pairs", height)
    piv = piv.dropna(subset=["Retail", "Wholesale"]).reset_index()
    piv = piv[piv["Wholesale"] > 0]
    if len(piv) == 0:
        return helpers.empty_fig("No retail/wholesale pairs", height)
    piv["RelativeMargin"] = (piv["Retail"] - piv["Wholesale"]) \
        / piv["Wholesale"] * 100

    fig = go.Figure()
    for substance, s in piv.sort_values("Year").groupby("Substance"):
        if len(s) < 2:
            continue
        color = data.substance_color_map.get(substance, theme.TOL_MUTED[0])
        fig.add_trace(go.Scatter(
            x=s["Year"], y=s["RelativeMargin"], mode="lines+markers",
            name=substance, legendgroup=substance,
            line=dict(width=3, color=color),
            marker=dict(size=8, line=dict(width=2, color="white"),
                        color=color),
            hovertemplate=(f"{substance}<br>%{{x}}: %{{y:.0f}}% markup"
                           "<extra></extra>")))

    if not fig.data:
        return helpers.empty_fig("Need 2+ years per substance for a trend",
                                 height)

    if selection.get("year"):
        fig.add_vline(x=selection["year"], line_dash="dash",
                      line_color=theme.ACCENT, line_width=3,
                      annotation_text=f"Selected: {selection['year']}",
                      annotation_position="top")

    fig.update_layout(
        title="Retail-wholesale markup over time",
        height=height, plot_bgcolor=theme.PLOT_BG,
        xaxis=dict(title="Year", tickmode="linear", dtick=1,
                   tickformat="d", gridcolor=theme.GRID),
        yaxis=dict(title="Relative markup (%)", gridcolor=theme.GRID,
                   rangemode="tozero"),
        legend=dict(title="Substance", orientation="v", yanchor="middle",
                    y=0.5, xanchor="left", x=1.02),
        margin=dict(l=60, r=150, t=50, b=50))
    return fig
