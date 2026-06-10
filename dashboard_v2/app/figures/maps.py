"""Choropleth maps: the semantic-zoom enforcement map, the retail-wholesale
margin map (Q2), and the cross-border price-arbitrage exposure map (Q3).
"""
import pandas as pd
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


# Inlined geojson per facet×frame trace balloons the payload; coarse outline is
# indistinguishable at this map size (same trick as the Temporal-tab maps).
_MARGIN_SIMPLIFY_TOL = 0.2


def _margin_winners(prices, substances, selection):
    """Per (Country, Year), the substance with the highest retail–wholesale
    markup — computed twice, once ranked by relative % and once by absolute $/g.

    Margins are recomputed per year from `prices` (the `inland_margin` artifact
    is collapsed across years and so can't drive an animation). Returns a long
    frame with a `Metric`/`Value` pair per facet, or None if nothing qualifies.
    """
    p = prices[prices["Substance"] != "Other"]
    if substances:
        p = p[p["Substance"].isin(set(substances))]
    if selection.get("substance"):
        p = p[p["Substance"] == selection["substance"]]
    if selection.get("countries"):
        p = p[p["Country"].isin(selection["countries"])]
    if len(p) == 0:
        return None

    # Mean retail & wholesale per (Country, Substance, Year), then the spread.
    wide = (p.groupby(["Country", "Substance", "Year", "LevelOfSale"])
            ["Typical_USD"].mean().unstack("LevelOfSale").reset_index())
    if "Retail" not in wide or "Wholesale" not in wide:
        return None
    wide = wide.dropna(subset=["Retail", "Wholesale"])
    wide = wide[wide["Wholesale"] > 0]
    if len(wide) == 0:
        return None
    wide["Margin"] = wide["Retail"] - wide["Wholesale"]
    wide["RelativeMargin"] = wide["Margin"] / wide["Wholesale"] * 100

    frames = []
    for metric, rank_col, val_col in (
            (_REL_LABEL, "RelativeMargin", "RelativeMargin"),
            (_ABS_LABEL, "Margin", "Margin")):
        win = wide.loc[wide.groupby(["Country", "Year"])[rank_col].idxmax()].copy()
        win["Metric"] = metric
        win["Value"] = win[val_col]
        frames.append(win)
    return pd.concat(frames, ignore_index=True)


_REL_LABEL = "Highest relative markup (%)"
_ABS_LABEL = "Highest absolute markup ($/g)"
_MARGIN_NO_DATA = "#e0e0e0"   # grey fill for countries without a winner


def _discrete_colorscale(colors):
    """A piecewise-constant colorscale mapping integer index i -> colors[i].

    Used so a single Choropleth can show categorical substance colours: with
    cmin=-0.5, cmax=N-0.5 and z=i, each integer sits at the centre of its band.
    """
    n = len(colors)
    scale = []
    for i, c in enumerate(colors):
        scale.append([i / n, c])
        scale.append([(i + 1) / n, c])
    return scale


@memoize_figure()
def margin_map(data, selection, substances=None, year_range=None, height=520):
    """Q2: per country, the substance with the highest retail-vs-wholesale markup.

    Two side-by-side animated choropleths — ranked by relative % (left) and by
    absolute $/g (right). Countries are coloured by the *winning* substance,
    reusing the master-panel substance palette (no separate legend); the full
    continent is always drawn (grey base) so countries with no winner read as
    "no data". `substances` (the active master-legend set) restricts which
    substances can win each country, so deselecting one drops it from the
    per-country max and the next-highest selected substance takes over. A play
    button + year slider step through `year_range`, latest year by default.
    """
    yr = year_range or [int(data.prices["Year"].min()),
                        int(data.prices["Year"].max())]
    p = data.prices[data.prices["Year"].between(yr[0], yr[1])]
    p = p[p["Country"].isin(set(data.europe_gdf["NAME"]))]

    win = _margin_winners(p, substances, selection)
    if win is None or len(win) == 0:
        return helpers.base_geo_layout(helpers.empty_fig("No markup data"),
                                       right_margin=10)

    gdf = data.europe_gdf.copy()
    gdf["geometry"] = gdf["geometry"].simplify(_MARGIN_SIMPLIFY_TOL,
                                               preserve_topology=True)
    geojson = gdf.__geo_interface__
    all_countries = list(gdf["NAME"])

    win = win.assign(Year=win["Year"].astype(int))
    years = sorted(win["Year"].unique())

    # Stable substance -> index (canonical order) so a substance keeps its colour
    # across both panels and every frame. Colours come from the master palette.
    subs = [s for s in data.substances if s in set(win["Substance"])]
    idx = {s: i for i, s in enumerate(subs)}
    colors = [data.substance_color_map.get(s, _MARGIN_NO_DATA) for s in subs]
    n = len(subs)
    colorscale = _discrete_colorscale(colors)

    panels = [(_REL_LABEL, "RelativeMargin"), (_ABS_LABEL, "Margin")]
    geos = ["geo", "geo2"]

    def base(geo):
        """Grey all-Europe layer so countries with no winner still appear."""
        return go.Choropleth(
            geojson=geojson, featureidkey="properties.NAME",
            locations=all_countries, z=[0] * len(all_countries), showscale=False,
            hoverinfo="skip", colorscale=[[0, _MARGIN_NO_DATA], [1, _MARGIN_NO_DATA]],
            geo=geo, marker_line_color="white", marker_line_width=0.4)

    def layer(metric, year, geo):
        """Coloured winners for one panel / year on the discrete substance scale."""
        d = win[(win["Metric"] == metric) & (win["Year"] == year)]
        return go.Choropleth(
            geojson=geojson, featureidkey="properties.NAME",
            locations=d["Country"], z=[idx[s] for s in d["Substance"]],
            zmin=-0.5, zmax=n - 0.5, colorscale=colorscale, showscale=False,
            geo=geo, marker_line_color="white", marker_line_width=0.4,
            text=d["Substance"], customdata=d[["Value", "Retail", "Wholesale"]],
            hovertemplate=("<b>%{location}</b><br>%{text}<br>"
                           "markup: %{customdata[0]:,.1f}<br>"
                           "retail $%{customdata[1]:,.0f}/g · "
                           "wholesale $%{customdata[2]:,.0f}/g<extra></extra>"))

    default_year = years[-1]
    initial, data_idx = [], []
    for i, ((metric, _), geo) in enumerate(zip(panels, geos)):
        initial.append(base(geo))
        initial.append(layer(metric, default_year, geo))
        data_idx.append(2 * i + 1)        # frames update only the coloured layers
    fig = go.Figure(
        data=initial,
        frames=[go.Frame(name=str(y),
                         data=[layer(metric, y, geo)
                               for (metric, _), geo in zip(panels, geos)],
                         traces=data_idx)
                for y in years])

    geo_common = dict(visible=False, projection_type="mercator",
                      fitbounds="locations", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        height=height, margin=dict(l=0, r=10, t=55, b=10),
        clickmode="event+select", showlegend=False,
        geo=dict(domain=dict(x=[0.0, 0.49], y=[0, 0.92]), **geo_common),
        geo2=dict(domain=dict(x=[0.51, 1.0], y=[0, 0.92]), **geo_common),
        annotations=[
            dict(text=_REL_LABEL, x=0.245, y=1.0, xref="paper", yref="paper",
                 showarrow=False, font=dict(size=13), xanchor="center",
                 yanchor="bottom"),
            dict(text=_ABS_LABEL, x=0.755, y=1.0, xref="paper", yref="paper",
                 showarrow=False, font=dict(size=13), xanchor="center",
                 yanchor="bottom"),
        ])

    # Single year -> nothing to animate; skip the slider/play controls.
    if len(years) > 1:
        fig.update_layout(
            sliders=[dict(
                active=len(years) - 1, x=0.05, len=0.7, xanchor="left",
                currentvalue=dict(prefix="Year: "), pad=dict(t=0, b=8),
                steps=[dict(method="animate", label=str(y),
                            args=[[str(y)], dict(mode="immediate",
                                  frame=dict(duration=0, redraw=True),
                                  transition=dict(duration=0))])
                       for y in years])],
            updatemenus=[dict(
                type="buttons", showactive=False, x=0.0, xanchor="right",
                y=0, yanchor="bottom", pad=dict(r=10),
                buttons=[dict(
                    label="▶ ⏸", method="animate",
                    args=[None, dict(frame=dict(duration=700, redraw=True),
                                     fromcurrent=True,
                                     transition=dict(duration=300))],
                    args2=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")])])])
    return fig
