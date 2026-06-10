import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# simplified geometry keeps the inlined geojson payload small
_SIMPLIFY_TOL = 0.2
_NO_DATA = "#e0e0e0"
_LEVELS = ["Retail", "Wholesale"]

# per-metric config
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


def temporal_agg(data, metric, substance, year_range, countries=None):
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
    from dash import html

    if not substance:
        return html.Small("Select a substance to see highlights.",
                          className="text-muted")

    cfg = _METRICS.get(metric or "purity", _METRICS["purity"])
    res = temporal_agg(data, metric, substance, year_range, countries)
    if res is None:
        return html.Small(f"No {cfg['label']} data for the current selection.",
                          className="text-muted")
    agg, cfg, _ = res
    value_col = cfg["value"]
    swatch_color = data.substance_color_map.get(substance, "#888")

    def make_li(label, d):
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
        items = [make_li("retail: ", agg[agg["LevelOfSale"] == "Retail"]),
                 make_li("wholesale: ", agg[agg["LevelOfSale"] == "Wholesale"])]
    else:
        items = [make_li("", agg)]
    items = [li for li in items if li is not None]

    return html.Div([
        html.Strong(f"Highest {cfg['label']} for {substance} "
                    "in the current selection:"),
        html.Ul(items, className="mt-2 mb-0"),
    ], className="small")


@memoize_figure()
def temporal_maps(data, metric, substance, year_range, countries=None, height=520):
    if not substance:
        return helpers.empty_fig("Select a substance to map", height)
    cfg = _METRICS.get(metric or "purity", _METRICS["purity"])

    df = getattr(data, cfg["table"])
    # purity reported in % only
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
        sub = " for the selected countries" if countries else ""
        return helpers.empty_fig(
            f"No {cfg['label']} data for {substance} in this period{sub}", height)

    df = df.assign(Year=df["Year"].astype(int))
    # seizures are kg, map shows tonnes
    scale = 0.001 if metric == "seizures" else 1.0

    group_cols = (["LevelOfSale", "Country", "Year"] if cfg["split"]
                  else ["Country", "Year"])
    agg = (df.groupby(group_cols)[cfg["value"]].agg(cfg["agg"]) * scale).reset_index()

    lo, hi = float(agg[cfg["value"]].min()), float(agg[cfg["value"]].max())
    years = sorted(agg["Year"].unique())

    gdf = data.europe_gdf.copy()
    gdf["geometry"] = gdf["geometry"].simplify(_SIMPLIFY_TOL, preserve_topology=True)
    geojson = gdf.__geo_interface__
    all_countries = list(gdf["NAME"])

    panels = _LEVELS if cfg["split"] else [None]
    geos = ["geo", "geo2"][:len(panels)]

    def base(geo):
        return go.Choropleth(
            geojson=geojson, featureidkey="properties.NAME", locations=all_countries,
            z=[0] * len(all_countries), showscale=False, hoverinfo="skip",
            colorscale=[[0, _NO_DATA], [1, _NO_DATA]], geo=geo,
            marker_line_color="white", marker_line_width=0.4)

    def layer(panel, year, geo):
        d = agg[agg["Year"] == year]
        if panel is not None:
            d = d[d["LevelOfSale"] == panel]
        return go.Choropleth(
            geojson=geojson, featureidkey="properties.NAME",
            locations=d["Country"], z=d[cfg["value"]], coloraxis="coloraxis",
            geo=geo, marker_line_color="white", marker_line_width=0.4,
            hovertemplate=f"<b>%{{location}}</b><br>{cfg['hover']}<extra></extra>")

    default_year = years[-1]
    # data layers sit at odd indices, frames update only those
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

    # only show slider/play when there's more than one year
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
