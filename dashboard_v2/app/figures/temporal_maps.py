"""Temporal spatial view: one metric for one substance, mapped across Europe and
animated over the selected years.

The dashboard shows the analytic charts but never lets you watch a single metric
move across the map year by year. This builder does: pick a metric (price,
purity, or seizures) and a substance, and get Europe choropleth(s) with a play
button + year slider, starting on the latest year.

Price and purity carry a retail/wholesale split, so they render as two side-by-
side maps; seizures are a single per-country total, so they render as one
full-width map. Every country is always drawn (a grey base layer), so a country
with no value for the active metric/substance/year reads as "no data" rather than
vanishing.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# The full europe.geojson (~1.5 MB) is inlined into every Choropleth trace, so an
# un-simplified geometry balloons the payload. At this map size the coarse
# outline is indistinguishable from the detailed one.
_SIMPLIFY_TOL = 0.2
_NO_DATA = "#e0e0e0"           # grey fill for countries without a value
_LEVELS = ["Retail", "Wholesale"]

# Per-metric config: which artifact, value column, aggregation, hover formatting,
# colour-axis title, and whether the metric splits by sale level.
_METRICS = {
    "price": dict(table="prices", value="Typical_USD", agg="mean", split=True,
                  label="Price (USD/g)", hover="Price: $%{z:,.0f}/g",
                  cbar="USD/g", hover_fmt="${:,.0f}/g"),
    "purity": dict(table="purity", value="Typical", agg="mean", split=True,
                   label="Purity (%)", hover="Purity: %{z:.1f}%",
                   cbar="Purity (%)", hover_fmt="{:.1f}%"),
    "seizures": dict(table="seizures", value="Kilograms", agg="sum", split=False,
                     label="Seizures (t)", hover="Seizures: %{z:,.1f} t",
                     cbar="Seizures (t)", hover_fmt="{:,.1f} t"),
}


def _temporal_agg(data, metric, substance, year_range, countries=None):
    """Shared aggregation for the temporal map and its highlights: one value per
    (panel, Country, Year) for `metric`/`substance` over `year_range`.

    Returns (agg_df, cfg, scale) or None when there is no data. For split
    metrics (price/purity) the panel column is LevelOfSale; seizures have none.
    """
    cfg = _METRICS.get(metric or "purity", _METRICS["purity"])
    df = getattr(data, cfg["table"])
    if metric == "purity":
        df = df[df["Measurement"].astype(str).str.contains("percent", case=False,
                                                            na=False)]
    df = df[df["Substance"] == substance]
    df = df[df["Year"].between(year_range[0], year_range[1])]
    df = df[df["Country"].isin(set(data.europe_gdf["NAME"]))]
    if countries:
        df = df[df["Country"].isin(set(countries))]
    df = df.dropna(subset=[cfg["value"]])
    if len(df) == 0:
        return None
    df = df.assign(Year=df["Year"].astype(int))
    scale = 0.001 if metric == "seizures" else 1.0
    group_cols = (["LevelOfSale", "Country", "Year"] if cfg["split"]
                  else ["Country", "Year"])
    agg = (df.groupby(group_cols)[cfg["value"]].agg(cfg["agg"])
           * scale).reset_index()
    return agg, cfg, scale


def temporal_highlights(data, metric, substance, year_range, countries=None):
    """Ranked HTML callout of the highest-valued countries for the temporal
    map's current metric/substance/selection.

    Mirrors the profitability tab's markup highlights: a coloured substance
    swatch, the country in bold, and the figure in small text. Split metrics
    (price/purity) surface one winner per sale level (retail & wholesale);
    seizures surface a single overall winner. Surfaced above the temporal map.
    """
    from dash import html

    if not substance:
        return html.Small("Select a substance to see highlights.",
                          className="text-muted")

    cfg = _METRICS.get(metric or "purity", _METRICS["purity"])
    res = _temporal_agg(data, metric, substance, year_range, countries)
    if res is None:
        return html.Small(f"No {cfg['label']} data for the current selection.",
                          className="text-muted")
    agg, cfg, _ = res
    value_col = cfg["value"]
    swatch_color = data.substance_color_map.get(substance, "#888")

    def _li(label, d):
        if len(d) == 0:
            return None
        row = d.loc[d[value_col].idxmax()]
        return html.Li([
            html.Span(style={"display": "inline-block", "width": "10px",
                             "height": "10px", "borderRadius": "50%",
                             "backgroundColor": swatch_color,
                             "marginRight": "6px"}),
            html.Strong(f"{row['Country']} "),
            html.Span(f"{label}{cfg['hover_fmt'].format(row[value_col])} "
                      f"({int(row['Year'])})", className="small"),
        ], className="mb-1")

    if cfg["split"]:
        items = [_li("retail: ", agg[agg["LevelOfSale"] == "Retail"]),
                 _li("wholesale: ", agg[agg["LevelOfSale"] == "Wholesale"])]
    else:
        items = [_li("", agg)]
    items = [li for li in items if li is not None]

    return html.Div([
        html.Strong(f"Highest {cfg['label']} for {substance} "
                    "in the current selection:"),
        html.Ul(items, className="mt-2 mb-0"),
    ], className="small")


@memoize_figure()
def temporal_maps(data, metric, substance, year_range, countries=None, height=520):
    """Animated choropleth(s) of `metric` for `substance` over `year_range`.

    Returns two side-by-side maps (retail | wholesale) for price/purity, or a
    single full-width map for seizures. The colour scale is fixed to the
    *displayed* selection's min-max so every panel and frame are comparable —
    and so that restricting `countries` (a subset selected on the master map)
    rescales the colours, letting the user exclude outliers. The full continent
    is always drawn as a grey base regardless of the subset.
    """
    if not substance:
        return helpers.empty_fig("Select a substance to map", height)
    cfg = _METRICS.get(metric or "purity", _METRICS["purity"])

    df = getattr(data, cfg["table"])
    # Purity in % only — mg/tablet potency is a different scale.
    if metric == "purity":
        df = df[df["Measurement"].astype(str).str.contains("percent", case=False,
                                                            na=False)]
    df = df[df["Substance"] == substance]
    df = df[df["Year"].between(year_range[0], year_range[1])]
    df = df[df["Country"].isin(set(data.europe_gdf["NAME"]))]
    # A country subset (from the master map) restricts which countries are
    # coloured and, in turn, the colour-scale min-max below — so deselecting an
    # outlier country rescales the remaining values.
    if countries:
        df = df[df["Country"].isin(set(countries))]
    df = df.dropna(subset=[cfg["value"]])
    if len(df) == 0:
        sub = " for the selected countries" if countries else ""
        return helpers.empty_fig(
            f"No {cfg['label']} data for {substance} in this period{sub}", height)

    df = df.assign(Year=df["Year"].astype(int))
    # Seizures are reported in kg; the map shows tonnes.
    scale = 0.001 if metric == "seizures" else 1.0

    # Aggregate to one value per (panel, Country, Year). For split metrics the
    # panel is LevelOfSale; for seizures there is a single implicit panel.
    group_cols = (["LevelOfSale", "Country", "Year"] if cfg["split"]
                  else ["Country", "Year"])
    agg = (df.groupby(group_cols)[cfg["value"]].agg(cfg["agg"]) * scale).reset_index()

    lo, hi = float(agg[cfg["value"]].min()), float(agg[cfg["value"]].max())
    years = sorted(agg["Year"].unique())

    # Simplified geometry + the full country list for the grey "no data" base.
    gdf = data.europe_gdf.copy()
    gdf["geometry"] = gdf["geometry"].simplify(_SIMPLIFY_TOL, preserve_topology=True)
    geojson = gdf.__geo_interface__
    all_countries = list(gdf["NAME"])

    panels = _LEVELS if cfg["split"] else [None]
    geos = ["geo", "geo2"][:len(panels)]

    def base(geo):
        """Grey all-Europe layer so countries with no value still appear."""
        return go.Choropleth(
            geojson=geojson, featureidkey="properties.NAME", locations=all_countries,
            z=[0] * len(all_countries), showscale=False, hoverinfo="skip",
            colorscale=[[0, _NO_DATA], [1, _NO_DATA]], geo=geo,
            marker_line_color="white", marker_line_width=0.4)

    def layer(panel, year, geo):
        """Coloured metric layer for one panel / year, on the shared coloraxis."""
        d = agg[agg["Year"] == year]
        if panel is not None:
            d = d[d["LevelOfSale"] == panel]
        return go.Choropleth(
            geojson=geojson, featureidkey="properties.NAME",
            locations=d["Country"], z=d[cfg["value"]], coloraxis="coloraxis",
            geo=geo, marker_line_color="white", marker_line_width=0.4,
            hovertemplate=f"<b>%{{location}}</b><br>{cfg['hover']}<extra></extra>")

    default_year = years[-1]   # latest year on load
    # Trace order per panel: grey base, then the coloured data layer. The data
    # layers are at odd indices (1, 3, ...) — frames update only those.
    initial, data_idx = [], []
    for i, (panel, geo) in enumerate(zip(panels, geos)):
        initial.append(base(geo))
        initial.append(layer(panel, default_year, geo))
        data_idx.append(2 * i + 1)
    fig = go.Figure(
        data=initial,
        frames=[go.Frame(name=str(y),
                         data=[layer(panel, y, geo)
                               for panel, geo in zip(panels, geos)],
                         traces=data_idx)
                for y in years])

    geo_common = dict(visible=False, projection_type="mercator",
                      fitbounds="locations", bgcolor="rgba(0,0,0,0)")
    layout = dict(
        height=height, margin=dict(l=0, r=0, t=55, b=10),
        coloraxis=dict(colorscale=theme.SEQUENTIAL, cmin=lo, cmax=hi,
                       colorbar=dict(title=cfg["cbar"])))
    if cfg["split"]:
        # Maps stop just below the top so the panel labels sit in their own strip
        # above the heatmaps rather than overlapping them.
        layout["geo"] = dict(domain=dict(x=[0.0, 0.49], y=[0, 0.93]), **geo_common)
        layout["geo2"] = dict(domain=dict(x=[0.51, 1.0], y=[0, 0.93]), **geo_common)
        layout["annotations"] = [
            dict(text="Retail", x=0.245, y=1.0, xref="paper", yref="paper",
                 showarrow=False, font=dict(size=13), xanchor="center",
                 yanchor="bottom"),
            dict(text="Wholesale", x=0.755, y=1.0, xref="paper", yref="paper",
                 showarrow=False, font=dict(size=13), xanchor="center",
                 yanchor="bottom"),
        ]
    else:
        layout["geo"] = dict(domain=dict(x=[0.0, 1.0], y=[0, 0.93]), **geo_common)
    fig.update_layout(**layout)

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
