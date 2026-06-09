"""Choropleth maps: the semantic-zoom enforcement map, the retail-wholesale
margin map (Q2), and the cross-border price-arbitrage exposure map (Q3).
"""
import plotly.express as px
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure


def subregion_order(data):
    """Deterministic sorted list of the subregions actually drawn on the map
    (countries that matched the geojson). The enforcement-map legend traces are
    built in this order, so the selection callback can map a legend-trace index
    back to its subregion."""
    cs = data.prices[["Country", "SubRegion"]].drop_duplicates()
    cs = cs[cs["Country"].isin(set(data.europe_gdf["NAME"]))]
    return sorted(cs["SubRegion"].dropna().unique())


def _selected_countries(selection):
    if selection.get("country"):
        return [selection["country"]]
    return list(selection.get("countries") or [])


@memoize_figure()
def enforcement_map(data, map_seizures, selection):
    """Single-level choropleth: every country coloured by its subregion.

    Interaction (wired in callbacks/zoom.py): clicking a country toggles that
    country in the global country filter; clicking a subregion in the legend
    toggles the whole region. Currently-selected countries are outlined.
    Seizure tonnage (for the active substance/year window) is shown on hover.
    """
    country_subregion = data.prices[["Country", "SubRegion"]].drop_duplicates()
    order = subregion_order(data)
    colors = theme.subregion_color_map(order)
    gdf = data.europe_gdf.merge(country_subregion, how="left",
                                left_on="NAME", right_on="Country")
    valid = gdf.dropna(subset=["SubRegion"]).copy()
    if len(valid) == 0:
        return helpers.empty_fig("No map data")

    tons = (map_seizures.groupby("Country")["Kilograms"].sum() / 1000).reset_index()
    tons.columns = ["Country", "Tons"]
    valid = valid.merge(tons, how="left", left_on="NAME", right_on="Country")
    valid["Tons"] = valid["Tons"].fillna(0)

    fig = px.choropleth(
        valid, geojson=valid.geometry.__geo_interface__, locations=valid.index,
        color="SubRegion", hover_name="NAME", color_discrete_map=colors,
        category_orders={"SubRegion": order}, hover_data={"Tons": ":.1f"},
    )
    fig.update_layout(legend=dict(title="Subregion", orientation="v",
                      yanchor="middle", y=0.5, xanchor="left", x=1.02,
                      bgcolor="rgba(255,255,255,0.9)", bordercolor="#333",
                      borderwidth=1))

    # Outline currently-selected countries (added last so legend indices,
    # which the toggle callback relies on, stay aligned with `order`).
    selected = _selected_countries(selection)
    sel_gdf = data.europe_gdf[data.europe_gdf["NAME"].isin(selected)]
    if len(sel_gdf):
        # hoverinfo="none" (not "skip") so the outline overlay still emits click
        # events: otherwise it swallows clicks on an already-selected country and
        # you could never toggle it back off. The click handler resolves the
        # country from the polygon index, so the missing hovertext is fine.
        fig.add_trace(go.Choropleth(
            geojson=sel_gdf.geometry.__geo_interface__, locations=sel_gdf.index,
            z=[1] * len(sel_gdf), showscale=False, showlegend=False,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_color="#111", marker_line_width=2.5, hoverinfo="none"))

    return helpers.base_geo_layout(fig, right_margin=10)


@memoize_figure()
def margin_map(data, selection):
    """Q2: substance with the highest retail-vs-wholesale markup per country."""
    margin = data.inland_margin
    margin = margin[margin["Substance"] != "Other"]
    if selection.get("substance"):
        margin = margin[margin["Substance"] == selection["substance"]]
    if selection.get("countries"):
        margin = margin[margin["Country"].isin(selection["countries"])]
    if len(margin) == 0:
        return helpers.base_geo_layout(helpers.empty_fig("No data"), right_margin=150)

    best = margin.loc[margin.groupby("Country")["RelativeMargin"].idxmax()]
    gdf = data.europe_gdf.merge(best, how="left", left_on="NAME", right_on="Country")
    valid = gdf.dropna(subset=["Substance"])
    if len(valid) == 0:
        return helpers.base_geo_layout(helpers.empty_fig("No data"), right_margin=150)
    cmap = {s: data.substance_color_map[s] for s in valid["Substance"].unique()
            if s in data.substance_color_map}
    fig = px.choropleth(
        valid, geojson=valid.geometry.__geo_interface__, locations=valid.index,
        color="Substance", hover_name="NAME",
        hover_data={"RelativeMargin": ":.0f"}, color_discrete_map=cmap,
        title="Highest retail–wholesale markup, by substance",
    )
    fig.update_layout(legend=dict(title="Substance", orientation="v",
                      yanchor="middle", y=0.5, xanchor="left", x=1.02,
                      bgcolor="rgba(255,255,255,0.9)", bordercolor="#333",
                      borderwidth=1))
    return helpers.base_geo_layout(fig, right_margin=150)
