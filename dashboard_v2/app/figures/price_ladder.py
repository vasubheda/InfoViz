"""Q2 price-ladder dumbbell: per region & substance, a wholesale dot (filled)
joined to a retail dot (hollow) by a bar whose length encodes the
retail-wholesale markup. Replaces the old pair of retail/wholesale heatmaps so
the markup story reads directly instead of by eye across two figures.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .. import theme
from . import helpers
from .cache import memoize_figure


@memoize_figure()
def price_ladder(data, filtered_prices, selection, height=400):
    if len(filtered_prices) == 0:
        return helpers.empty_fig("No data available", height)

    latest = filtered_prices["Year"].max()
    sub = filtered_prices[filtered_prices["Year"] == latest].copy()
    sub["RegionShort"] = sub["SubRegion"].str.replace(
        " Europe", "", regex=False)

    # Retail & wholesale side by side per (region, substance); keep only rows
    # where both levels exist so a rung always has two ends.
    hm = sub.pivot_table(values="Typical_USD",
                         index=["RegionShort", "Substance"],
                         columns="LevelOfSale", aggfunc="mean")
    if "Retail" not in hm.columns or "Wholesale" not in hm.columns:
        return helpers.empty_fig("No retail/wholesale pairs", height)
    hm = hm.dropna(subset=["Retail", "Wholesale"]).reset_index()
    if len(hm) == 0:
        return helpers.empty_fig("No retail/wholesale pairs", height)

    regions = list(hm["RegionShort"].unique())
    fig = make_subplots(rows=1, cols=len(regions), shared_yaxes=True,
                        subplot_titles=regions, horizontal_spacing=0.04)

    sel_region = (selection.get("subregion") or "").replace(" Europe", "")
    sel_sub = selection.get("substance")

    showed_legend = False
    for ci, region in enumerate(regions, start=1):
        g = hm[hm["RegionShort"] == region].sort_values("Substance")
        for _, r in g.iterrows():
            substance = r["Substance"]
            ws, rt = r["Wholesale"], r["Retail"]
            markup = rt - ws
            selected = (region == sel_region and substance == sel_sub)
            bar_w = 9 if selected else 5
            bar_c = theme.ACCENT if selected else theme.GRID
            cdata = [[substance, region, ws, rt, markup]]

            # Connecting rung (the markup).
            fig.add_trace(go.Scatter(
                x=[ws, rt], y=[substance, substance], mode="lines",
                line=dict(color=bar_c, width=bar_w),
                hoverinfo="skip", showlegend=False), row=1, col=ci)
            # Wholesale end (filled blue).
            fig.add_trace(go.Scatter(
                x=[ws], y=[substance], mode="markers", name="Wholesale",
                legendgroup="Wholesale", showlegend=not showed_legend,
                marker=dict(symbol="circle", size=12,
                            color=theme.ACCENT_ALT),
                customdata=cdata,
                hovertemplate=("Region: %{customdata[1]}<br>"
                               "Substance: %{customdata[0]}<br>"
                               "Wholesale: $%{customdata[2]:.2f}/g<br>"
                               "Retail: $%{customdata[3]:.2f}/g<br>"
                               "Markup: $%{customdata[4]:.2f}/g"
                               "<extra></extra>")), row=1, col=ci)
            # Retail end (hollow orange).
            fig.add_trace(go.Scatter(
                x=[rt], y=[substance], mode="markers", name="Retail",
                legendgroup="Retail", showlegend=not showed_legend,
                marker=dict(symbol="circle-open", size=12,
                            line=dict(width=3, color=theme.ACCENT)),
                customdata=cdata,
                hovertemplate=("Region: %{customdata[1]}<br>"
                               "Substance: %{customdata[0]}<br>"
                               "Wholesale: $%{customdata[2]:.2f}/g<br>"
                               "Retail: $%{customdata[3]:.2f}/g<br>"
                               "Markup: $%{customdata[4]:.2f}/g"
                               "<extra></extra>")), row=1, col=ci)
            showed_legend = True

        fig.update_xaxes(title_text="USD/g", gridcolor=theme.GRID,
                         rangemode="tozero", row=1, col=ci)

    fig.update_yaxes(autorange="reversed", gridcolor=theme.GRID,
                     row=1, col=1)
    fig.update_layout(
        title=f"Wholesale to retail price ladder ({latest})",
        height=height, plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.08,
                    xanchor="right", x=1),
        margin=dict(l=110, r=30, t=70, b=50))
    return fig
