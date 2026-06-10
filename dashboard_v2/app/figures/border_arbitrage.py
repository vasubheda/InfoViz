import math

import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# land-border adjacency, geojson NAME spelling
_LAND_BORDERS = {
    "Albania": ["Greece", "Montenegro", "Serbia",
                "The former Yugoslav Republic of Macedonia"],
    "Andorra": ["France", "Spain"],
    "Austria": ["Czech Republic", "Germany", "Hungary", "Italy",
                "Liechtenstein", "Slovakia", "Slovenia"],
    "Belarus": ["Latvia", "Lithuania", "Poland", "Russia", "Ukraine"],
    "Belgium": ["France", "Germany", "Luxembourg", "Netherlands"],
    "Bosnia and Herzegovina": ["Croatia", "Montenegro", "Serbia"],
    "Bulgaria": ["Greece", "Romania", "Serbia",
                 "The former Yugoslav Republic of Macedonia", "Turkey"],
    "Croatia": ["Bosnia and Herzegovina", "Hungary", "Montenegro", "Serbia",
                "Slovenia"],
    "Cyprus": [],
    "Czech Republic": ["Austria", "Germany", "Poland", "Slovakia"],
    "Denmark": ["Germany"],
    "Estonia": ["Latvia", "Russia"],
    "Finland": ["Norway", "Russia", "Sweden"],
    "France": ["Andorra", "Belgium", "Germany", "Italy", "Luxembourg", "Spain"],
    "Germany": ["Austria", "Belgium", "Czech Republic", "Denmark", "France",
                "Luxembourg", "Netherlands", "Poland"],
    "Gibraltar": [],
    "Greece": ["Albania", "Bulgaria",
               "The former Yugoslav Republic of Macedonia", "Turkey"],
    "Hungary": ["Austria", "Croatia", "Romania", "Serbia", "Slovakia",
                "Slovenia", "Ukraine"],
    "Iceland": [],
    "Ireland": ["United Kingdom"],
    "Italy": ["Austria", "France", "Slovenia"],
    "Latvia": ["Belarus", "Estonia", "Lithuania", "Russia"],
    "Liechtenstein": ["Austria"],
    "Lithuania": ["Belarus", "Latvia", "Poland", "Russia"],
    "Luxembourg": ["Belgium", "France", "Germany"],
    "Malta": [],
    "Montenegro": ["Albania", "Bosnia and Herzegovina", "Croatia", "Serbia"],
    "Netherlands": ["Belgium", "Germany"],
    "Norway": ["Finland", "Russia", "Sweden"],
    "Poland": ["Belarus", "Czech Republic", "Germany", "Lithuania", "Russia",
               "Slovakia", "Ukraine"],
    "Portugal": ["Spain"],
    "Republic of Moldova": ["Romania", "Ukraine"],
    "Romania": ["Bulgaria", "Hungary", "Republic of Moldova", "Serbia",
                "Ukraine"],
    "Russia": ["Belarus", "Estonia", "Finland", "Latvia", "Lithuania",
               "Norway", "Poland", "Ukraine"],
    "Serbia": ["Albania", "Bosnia and Herzegovina", "Bulgaria", "Croatia",
               "Hungary", "Montenegro", "Romania",
               "The former Yugoslav Republic of Macedonia"],
    "Slovakia": ["Austria", "Czech Republic", "Hungary", "Poland", "Ukraine"],
    "Slovenia": ["Austria", "Croatia", "Hungary", "Italy"],
    "Spain": ["Andorra", "France", "Portugal"],
    "Sweden": ["Finland", "Norway"],
    "The former Yugoslav Republic of Macedonia": ["Albania", "Bulgaria",
                                                  "Greece", "Serbia"],
    "Turkey": ["Bulgaria", "Greece"],
    "Ukraine": ["Belarus", "Hungary", "Poland", "Republic of Moldova",
                "Romania", "Russia", "Slovakia"],
    "United Kingdom": ["Ireland"],
}


def neighbours_of(data, country):
    priced = set(data.prices["Country"].unique())
    return sorted(n for n in _LAND_BORDERS.get(country, []) if n in priced)


def mean_price(prices, country, substance, level):
    sel = prices[(prices["Country"] == country)
                 & (prices["Substance"] == substance)
                 & (prices["LevelOfSale"] == level)]
    return sel["Typical_USD"].mean() if len(sel) else None


def seized_tons(seizures, country, substance):
    sel = seizures[(seizures["Country"] == country)
                   & (seizures["Substance"] == substance)]
    return sel["Kilograms"].sum() / 1000 if len(sel) else 0.0


def bearing(origin, dest):
    # clockwise-from-north angle so the arrowhead lines up with the segment
    (lon0, lat0), (lon1, lat1) = origin, dest

    def merc_y(lat):
        return math.degrees(math.log(math.tan(math.pi / 4
                                               + math.radians(lat) / 2)))

    dx = lon1 - lon0
    dy = merc_y(lat1) - merc_y(lat0)
    return (math.degrees(math.atan2(dx, dy))) % 360


def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


def tercile_thresholds(values):
    s = sorted(values)
    if len(s) < 3:
        return (s[0] if s else 0), (s[-1] if s else 0)
    lo = s[len(s) // 3]
    hi = s[2 * len(s) // 3]
    return lo, hi


def compute_rows(data, filtered_prices, filtered_seizures, country, substances):
    if not country:
        return None
    neigh = neighbours_of(data, country)
    if not neigh:
        return "no_neigh"

    subs = [s for s in substances if s != "Other"]
    rows = []
    for n in neigh:
        for s in subs:
            c_retail = mean_price(filtered_prices, country, s, "Retail")
            c_whole = mean_price(filtered_prices, country, s, "Wholesale")
            n_retail = mean_price(filtered_prices, n, s, "Retail")
            n_whole = mean_price(filtered_prices, n, s, "Wholesale")

            import_margin = (c_retail - n_whole
                             if c_retail is not None and n_whole is not None else None)
            export_margin = (n_retail - c_whole
                             if n_retail is not None and c_whole is not None else None)
            if import_margin is None and export_margin is None:
                continue

            best_import = (import_margin if import_margin is not None else float("-inf"))
            best_export = (export_margin if export_margin is not None else float("-inf"))
            if best_import >= best_export:
                direction, margin = "import", import_margin
                buy = f"buy wholesale in {n} (${n_whole:,.1f})"
                sell = f"sell retail in {country} (${c_retail:,.1f})"
                signed = -margin  # import -> left
            else:
                direction, margin = "export", export_margin
                buy = f"buy wholesale in {country} (${c_whole:,.1f})"
                sell = f"sell retail in {n} (${n_retail:,.1f})"
                signed = margin  # export -> right
            if margin is None:
                continue

            corridor_t = (seized_tons(filtered_seizures, country, s)
                          + seized_tons(filtered_seizures, n, s))
            rows.append({"label": f"{n} + {s}", "signed": signed, "margin": margin,
                         "substance": s, "direction": direction,
                         "buy": buy, "sell": sell, "corridor_t": corridor_t,
                         "neighbour": n})

    if not rows:
        return rows

    # priority = top-tercile margin and bottom-tercile seizures
    pressures = [r["corridor_t"] for r in rows]
    _, margin_hi = tercile_thresholds([r["margin"] for r in rows])
    seiz_lo, _ = tercile_thresholds(pressures)
    for r in rows:
        r["priority"] = r["margin"] >= margin_hi and r["corridor_t"] <= seiz_lo
        r["hover"] = (
            f"<b>{r['label']}</b><br>{r['direction'].title()} play: "
            f"{r['buy']} → {r['sell']}<br>Margin: ${r['margin']:,.2f}/g"
            + ("<br><b>⚑ Priority gap: high margin, low seizures</b>"
               if r["priority"] else "")
            + "<extra></extra>")
    return rows


@memoize_figure()
def border_arbitrage(data, filtered_prices, filtered_seizures, country, substances):
    rows = compute_rows(data, filtered_prices, filtered_seizures,
                        country, substances)
    if rows is None:
        return helpers.empty_fig(
            "Select a single country (click it on the map) to see its "
            "cross-border arbitrage opportunities.", 420)
    if rows == "no_neigh":
        return helpers.empty_fig(f"No bordering countries with price data for "
                                 f"{country}.", 420)
    if not rows:
        return helpers.empty_fig(
            f"No matched wholesale/retail price pairs across {country}'s borders "
            "for the current filters.", 420)

    # sort so the strongest borders stand out
    rows.sort(key=lambda r: r["margin"])
    marker_colors = [
        data.substance_color_map.get(r["substance"], theme.TOL_MUTED[0])
        for r in rows]

    fig = go.Figure(go.Bar(
        x=[r["signed"] for r in rows],
        y=[r["label"] for r in rows],
        orientation="h", marker_color=marker_colors,
        marker_line_color=["#111" if r["priority"] else "rgba(0,0,0,0)"
                           for r in rows],
        marker_line_width=[2 if r["priority"] else 0 for r in rows],
        customdata=[r["hover"] for r in rows],
        hovertemplate="%{customdata}",
        text=[f"${r['margin']:,.1f}" + (" ⚑" if r["priority"] else "")
              for r in rows], textposition="auto"))
    fig.add_vline(x=0, line_color="black", line_width=1)

    n_priority = sum(r["priority"] for r in rows)
    height = max(360, len(rows) * 22 + 130)
    fig.update_layout(
        title=dict(text=(
            f"Best cross-border arbitrage at {country}'s land borders "
            f"(wholesale → retail)"), y=0.97, yanchor="top"),
        xaxis_title=f"◀ Import into {country}   (best margin, USD/g)   "
                    f"Export from {country} ▶",
        height=height + 28, margin=dict(l=180, r=40, t=104, b=50),
        xaxis=dict(gridcolor=theme.GRID, zeroline=True),
        yaxis=dict(gridcolor=theme.GRID, tickfont=dict(size=10)),
        plot_bgcolor=theme.PLOT_BG, showlegend=False)
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=1.07, showarrow=False,
        font=dict(size=11, color="#555"), xanchor="left", yanchor="top",
        align="left",
        text="⚑ outlined = high-margin priority gap. Hue = substance.")
    return fig


@memoize_figure()
def priority_gap_list(data, filtered_prices, filtered_seizures, country, substances):
    from dash import html

    rows = compute_rows(data, filtered_prices, filtered_seizures,
                        country, substances)
    if not rows or rows in (None, "no_neigh"):
        return html.Small(
            "Select a single country to list its priority border gaps.",
            className="text-muted")

    gaps = sorted((r for r in rows if r["priority"]),
                  key=lambda r: r["margin"], reverse=True)
    if not gaps:
        return html.Small(
            "No priority gaps for the current filters - every high-margin "
            "corridor here already carries comparatively high seizures.",
            className="text-muted")

    items = []
    for r in gaps:
        arrow = ("→ into " + country if r["direction"] == "import"
                 else "→ out to " + r["neighbour"])
        swatch = data.substance_color_map.get(r["substance"], "#888")
        items.append(html.Li([
            html.Span(style={"display": "inline-block", "width": "10px",
                             "height": "10px", "borderRadius": "50%",
                             "backgroundColor": swatch, "marginRight": "6px"}),
            html.Strong(f"{r['neighbour']} + {r['substance']} "),
            html.Span(f"({r['direction']} {arrow})  ",
                      className="text-muted small"),
            html.Span(f"${r['margin']:,.1f}/g margin, "
                      f"{r['corridor_t']:,.1f} t seized",
                      className="small"),
        ], className="mb-1"))

    return html.Div([
        html.Strong(f"⚑ {len(gaps)} priority border gap(s) for {country} "
                    "(high margin, low seizures):"),
        html.Ul(items, className="mt-2 mb-0"),
    ], className="small")


_MARKET_TOP_N = 25


def market_rows(filtered_prices, filtered_seizures, pool, substances, cap=None):
    priced = set(filtered_prices["Country"].unique())
    countries = sorted(set(pool) & priced) if pool else sorted(priced)
    subs = [s for s in substances if s != "Other"]
    rows = []
    for s in subs:
        retail = {c: mean_price(filtered_prices, c, s, "Retail") for c in countries}
        whole = {c: mean_price(filtered_prices, c, s, "Wholesale") for c in countries}
        retail = {c: v for c, v in retail.items() if v is not None}
        whole = {c: v for c, v in whole.items() if v is not None}
        if not retail or not whole:
            continue
        buy_c = min(whole, key=whole.get)
        wh = whole[buy_c]
        # one corridor per retail destination that clears the origin wholesale
        sub_rows = []
        for sell_c, rt in retail.items():
            if sell_c == buy_c:
                continue
            margin = rt - wh
            if margin <= 0:
                continue
            corridor_t = (seized_tons(filtered_seizures, buy_c, s)
                          + seized_tons(filtered_seizures, sell_c, s))
            sub_rows.append({"substance": s, "margin": margin, "buy_c": buy_c,
                             "sell_c": sell_c, "rt": rt, "wh": wh,
                             "corridor_t": corridor_t})
        if sub_rows:
            best = max(sub_rows, key=lambda r: r["margin"])
            best["is_best"] = True
            rows.extend(sub_rows)
    if not rows:
        return rows
    for r in rows:
        r.setdefault("is_best", False)

    # opacity inverse to seizure pressure; priority = high margin, low seizures
    pressures = [r["corridor_t"] for r in rows]
    p_min, p_span = min(pressures), (max(pressures) - min(pressures)) or 1.0
    _, margin_hi = tercile_thresholds([r["margin"] for r in rows])
    seiz_lo, _ = tercile_thresholds(pressures)
    for r in rows:
        norm = (r["corridor_t"] - p_min) / p_span
        r["alpha"] = 1.0 - 0.7 * norm
        r["priority"] = r["margin"] >= margin_hi and r["corridor_t"] <= seiz_lo
        r["label"] = f"{r['substance']}: {r['buy_c']} → {r['sell_c']}"
        r["hover"] = (
            f"<b>{r['substance']}</b><br>"
            f"Buy wholesale in {r['buy_c']} (${r['wh']:,.1f})<br>"
            f"Sell retail in {r['sell_c']} (${r['rt']:,.1f})<br>"
            f"Spread: ${r['margin']:,.2f}/g"
            f"<br>Corridor seizures: {r['corridor_t']:,.1f} t"
            + ("<br><b>⚑ Priority gap: high margin, low seizures</b>"
               if r["priority"] else "")
            + "<extra></extra>")

    rows.sort(key=lambda r: r["margin"], reverse=True)
    return rows[:cap] if cap else rows


@memoize_figure()
def market_flow_map(data, filtered_prices, filtered_seizures, pool, substances,
                    height=620):
    rows = market_rows(filtered_prices, filtered_seizures, pool, substances,
                       cap=None)
    arrows = [r for r in rows if r["is_best"]]
    if not arrows:
        return helpers.base_geo_layout(
            helpers.empty_fig("No cross-market arbitrage for the current "
                              "selection.", height), right_margin=10)

    priced = set(filtered_prices["Country"].unique())
    countries = sorted(set(pool) & priced) if pool else sorted(priced)
    gdf = data.europe_gdf
    pts = {n: (rp.x, rp.y) for n, rp in
           zip(gdf["NAME"], gdf.geometry.representative_point())}

    # faint base so arrows read against a map
    base = gdf[gdf["NAME"].isin(countries)]
    fig = go.Figure(go.Choropleth(
        geojson=base.geometry.__geo_interface__, locations=base.index,
        z=[0] * len(base), showscale=False, hoverinfo="skip",
        colorscale=[[0, "#eef0f2"], [1, "#eef0f2"]],
        marker_line_color="white", marker_line_width=0.5))

    for r in arrows:
        o, dst = pts.get(r["buy_c"]), pts.get(r["sell_c"])
        if not o or not dst:
            continue
        color = data.substance_color_map.get(r["substance"], theme.TOL_MUTED[0])
        fig.add_trace(go.Scattergeo(
            lon=[o[0], dst[0]], lat=[o[1], dst[1]], mode="lines",
            line=dict(width=3, color=color), opacity=0.85,
            hoverinfo="skip", showlegend=False))
        # origin dot
        fig.add_trace(go.Scattergeo(
            lon=[o[0]], lat=[o[1]], mode="markers",
            marker=dict(size=6, color=color, opacity=0.6,
                        line=dict(width=1, color="white")),
            hoverinfo="skip", showlegend=False))
        # destination arrowhead
        fig.add_trace(go.Scattergeo(
            lon=[dst[0]], lat=[dst[1]], mode="markers",
            marker=dict(size=13, color=color, symbol="triangle-up",
                        angle=bearing(o, dst),
                        line=dict(width=1, color="white")),
            name=r["substance"], customdata=[r["hover"]],
            hovertemplate="%{customdata}", showlegend=True))

    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=40, b=0),
        title=f"Best arbitrage corridor per substance ({len(arrows)} flows)",
        legend=dict(title="Substance", orientation="h", yanchor="bottom",
                    y=-0.05, xanchor="center", x=0.5))
    fig.update_geos(scope="europe", projection_type="mercator",
                    showcountries=True, countrycolor="#d0d0d0",
                    showcoastlines=False, fitbounds="locations", visible=True,
                    bgcolor="rgba(0,0,0,0)")
    return fig


@memoize_figure()
def market_arbitrage(data, filtered_prices, filtered_seizures, pool, substances,
                     cap=_MARKET_TOP_N):
    rows = market_rows(filtered_prices, filtered_seizures, pool, substances,
                       cap=cap)
    if not rows:
        return helpers.empty_fig(
            "No matched wholesale/retail price pairs for the current "
            "selection.", 420)

    priced = set(filtered_prices["Country"].unique())
    n_countries = len(set(pool) & priced) if pool else len(priced)

    marker_colors = [hex_to_rgba(
        data.substance_color_map.get(r["substance"], theme.TOL_MUTED[0]),
        r["alpha"]) for r in rows]
    # bars drawn bottom-up, reverse so strongest is on top
    rows = rows[::-1]

    fig = go.Figure(go.Bar(
        x=[r["margin"] for r in rows],
        y=[r["label"] for r in rows],
        orientation="h", marker_color=marker_colors[::-1],
        marker_line_color=["#111" if r["priority"] else "rgba(0,0,0,0)"
                           for r in rows],
        marker_line_width=[2 if r["priority"] else 0 for r in rows],
        customdata=[r["hover"] for r in rows],
        hovertemplate="%{customdata}",
        text=[f"${r['margin']:,.1f}"
              + (" ▸" if r["is_best"] else "")
              + (" ⚑" if r["priority"] else "")
              for r in rows], textposition="auto"))

    n_priority = sum(r["priority"] for r in rows)
    height = max(360, len(rows) * 26 + 130)
    fig.update_layout(
        title=dict(text=(
            f"Top {len(rows)} cross-market arbitrage corridors across "
            f"{n_countries} selected countries | {n_priority} priority gap(s) ⚑"),
            y=0.97, yanchor="top"),
        xaxis_title="Arbitrage spread (USD/g)",
        height=height + 40, margin=dict(l=220, r=40, t=116, b=50),
        xaxis=dict(gridcolor=theme.GRID, zeroline=True),
        yaxis=dict(gridcolor=theme.GRID, tickfont=dict(size=10)),
        plot_bgcolor=theme.PLOT_BG, showlegend=False)
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=1.07, showarrow=False,
        font=dict(size=11, color="#555"), xanchor="left", yanchor="top",
        align="left",
        text="Each corridor: buy wholesale at the origin, sell retail at the "
             "destination. ▸ = drawn on the map above (best per substance).<br>"
             "Opacity = corridor seizure pressure (bold = lightly policed); "
             "⚑ = high-margin priority gap. Hue = substance.")
    return fig


@memoize_figure()
def market_gap_list(data, filtered_prices, filtered_seizures, pool, substances,
                    cap=_MARKET_TOP_N):
    import dash_bootstrap_components as dbc
    from dash import html

    rows = market_rows(filtered_prices, filtered_seizures, pool, substances,
                       cap=cap)
    if not rows:
        return html.Small(
            "Select countries to list cross-market arbitrage spreads.",
            className="text-muted")

    gaps = [r for r in rows if r["priority"]]
    if not gaps:
        return html.Small(
            "No priority gaps for the current selection - every high-margin "
            "spread here already carries comparatively high seizures.",
            className="text-muted")

    items = []
    for r in gaps:
        swatch = data.substance_color_map.get(r["substance"], "#888")
        items.append(html.Li([
            html.Span(style={"display": "inline-block", "width": "10px",
                             "height": "10px", "borderRadius": "50%",
                             "backgroundColor": swatch, "marginRight": "6px"}),
            html.Strong(f"{r['substance']} "),
            html.Span(f"(buy {r['buy_c']} → sell {r['sell_c']})  ",
                      className="text-muted small"),
            html.Span(f"${r['margin']:,.1f}/g spread, "
                      f"{r['corridor_t']:,.1f} t seized",
                      className="small"),
        ], className="mb-1"))

    return html.Div([
        html.Strong(f"⚑ {len(gaps)} priority market gap(s) "
                    "(high margin, low seizures): "),
        html.I(className="bi bi-info-circle text-muted",
               id="q3-gaps-info", style={"cursor": "help"}),
        dbc.Tooltip(
            "A corridor is flagged when its arbitrage spread is in the top "
            "third of all shown corridors AND its combined seizures (origin + "
            "destination) are in the bottom third - i.e. high profit, low "
            "enforcement. Thresholds are recomputed for the current selection.",
            target="q3-gaps-info", placement="bottom"),
        html.Ul(items, className="mt-2 mb-0"),
    ], className="small")


@memoize_figure()
def neighbour_map(data, country):
    if not country:
        return helpers.base_geo_layout(
            helpers.empty_fig("Select a single country", 420), right_margin=10)
    neigh = neighbours_of(data, country)
    gdf = data.europe_gdf[data.europe_gdf["NAME"].isin([country] + neigh)].copy()
    if len(gdf) == 0:
        return helpers.base_geo_layout(
            helpers.empty_fig("No map data", 420), right_margin=10)
    gdf["Role"] = gdf["NAME"].apply(
        lambda n: "Selected" if n == country else "Neighbour")
    import plotly.express as px
    fig = px.choropleth(
        gdf, geojson=gdf.geometry.__geo_interface__, locations=gdf.index,
        color="Role", hover_name="NAME",
        color_discrete_map={"Selected": theme.ACCENT, "Neighbour": theme.ACCENT_ALT},
        title=f"{country} and its land neighbours",
    )
    fig.update_layout(legend=dict(title="", orientation="h", yanchor="bottom",
                      y=-0.05, xanchor="center", x=0.5))
    return helpers.base_geo_layout(fig, height=420, right_margin=10)
