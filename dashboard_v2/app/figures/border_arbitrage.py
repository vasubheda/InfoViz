"""Cross-border wholesale->retail arbitrage for a single selected country.

For the selected country C and each bordering neighbour N, two smuggling plays
exist per substance:

  * IMPORT into C : buy wholesale in N, sell retail in C   margin = C_retail - N_wholesale
  * EXPORT from C : buy wholesale in C, sell retail in N   margin = N_retail - C_wholesale

We surface, per (neighbour, substance), the more profitable of the two
directions as a signed diverging bar (left = import incentive into C, right =
export incentive out of C). This shows border patrol which shared borders carry
the strongest smuggling pull and in which direction - the kind of cross-market
gap a purely domestic retail-wholesale markup misses.

Land-border adjacency is a hard-coded lookup (``_LAND_BORDERS``) using the
geojson ``NAME`` spelling. It was generated once from the geojson geometry (a
2 km buffer absorbed coastline/topology gaps); baking it in avoids running a
CRS reprojection + buffer + spatial-intersection over all of Europe on every
Q3 interaction. Names that carry no smuggling-relevant land border (islands:
Cyprus, Iceland, Malta; enclaves with none in-dataset: Gibraltar) map to [].
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# Symmetric land-border adjacency, geojson NAME spelling. See module docstring.
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
    """Land neighbours of ``country`` that also appear in the price data.

    Adjacency is the baked-in ``_LAND_BORDERS`` table; the price-data filter is
    applied at call time so the result still tracks whatever countries are
    actually priced (identical behaviour to the old geometry-derived version).
    """
    priced = set(data.prices["Country"].unique())
    return sorted(n for n in _LAND_BORDERS.get(country, []) if n in priced)


def _mean_price(prices, country, substance, level):
    sel = prices[(prices["Country"] == country)
                 & (prices["Substance"] == substance)
                 & (prices["LevelOfSale"] == level)]
    return sel["Typical_USD"].mean() if len(sel) else None


def _seized_tons(seizures, country, substance):
    sel = seizures[(seizures["Country"] == country)
                   & (seizures["Substance"] == substance)]
    return sel["Kilograms"].sum() / 1000 if len(sel) else 0.0


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _tercile_thresholds(values):
    s = sorted(values)
    if len(s) < 3:
        return (s[0] if s else 0), (s[-1] if s else 0)
    lo = s[len(s) // 3]
    hi = s[2 * len(s) // 3]
    return lo, hi


def _compute_rows(data, filtered_prices, filtered_seizures, country, substances):
    """Build enriched arbitrage rows for ``country``.

    Returns ``None`` (no country selected), ``"no_neigh"`` (no priced
    neighbours), or a list of row dicts each carrying the best margin, signed
    x-position, corridor seizure tonnage, opacity (inverse to pressure),
    priority flag, and a hover string. Shared by the chart and the gap list so
    both apply identical thresholds.
    """
    if not country:
        return None
    neigh = neighbours_of(data, country)
    if not neigh:
        return "no_neigh"

    subs = [s for s in substances if s != "Other"]
    rows = []
    for n in neigh:
        for s in subs:
            c_retail = _mean_price(filtered_prices, country, s, "Retail")
            c_whole = _mean_price(filtered_prices, country, s, "Wholesale")
            n_retail = _mean_price(filtered_prices, n, s, "Retail")
            n_whole = _mean_price(filtered_prices, n, s, "Wholesale")

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

            corridor_t = (_seized_tons(filtered_seizures, country, s)
                          + _seized_tons(filtered_seizures, n, s))
            rows.append({"label": f"{n} · {s}", "signed": signed, "margin": margin,
                         "substance": s, "direction": direction,
                         "buy": buy, "sell": sell, "corridor_t": corridor_t,
                         "neighbour": n})

    if not rows:
        return rows

    # Opacity inverse to corridor seizure pressure; priority = high margin
    # (top tercile) AND low seizures (bottom tercile).
    pressures = [r["corridor_t"] for r in rows]
    p_min, p_span = min(pressures), (max(pressures) - min(pressures)) or 1.0
    _, margin_hi = _tercile_thresholds([r["margin"] for r in rows])
    seiz_lo, _ = _tercile_thresholds(pressures)
    for r in rows:
        norm = (r["corridor_t"] - p_min) / p_span     # 0 = lightly policed
        r["alpha"] = 1.0 - 0.7 * norm                 # 1.0 .. 0.3
        r["priority"] = r["margin"] >= margin_hi and r["corridor_t"] <= seiz_lo
        r["hover"] = (
            f"<b>{r['label']}</b><br>{r['direction'].title()} play: "
            f"{r['buy']} → {r['sell']}<br>Margin: ${r['margin']:,.2f}/g"
            f"<br>Corridor seizures: {r['corridor_t']:,.1f} t"
            + ("<br><b>⚑ Priority gap: high margin, low seizures</b>"
               if r["priority"] else "")
            + "<extra></extra>")
    return rows


@memoize_figure()
def border_arbitrage(data, filtered_prices, filtered_seizures, country, substances):
    """Diverging per-(neighbour, substance) best-arbitrage bars for ``country``.

    Bar length = best smuggling margin; direction = import (left) / export
    (right). Bar opacity is inverse to *corridor seizure pressure* (the tonnage
    seized across the two countries for that substance): bold bars are high
    margin AND lightly policed - the priority gaps for border control.
    """
    rows = _compute_rows(data, filtered_prices, filtered_seizures,
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

    # Sort by absolute opportunity so the strongest borders are most prominent.
    rows.sort(key=lambda r: r["margin"])
    marker_colors = [_hex_to_rgba(
        data.substance_color_map.get(r["substance"], theme.TOL_MUTED[0]),
        r["alpha"]) for r in rows]

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
        title=(f"Best cross-border arbitrage at {country}'s land borders "
               f"(wholesale → retail) · {n_priority} priority gap(s) ⚑"),
        xaxis_title=f"◀ Import into {country}   (best margin, USD/g)   "
                    f"Export from {country} ▶",
        height=height, margin=dict(l=180, r=40, t=70, b=50),
        xaxis=dict(gridcolor=theme.GRID, zeroline=True),
        yaxis=dict(gridcolor=theme.GRID, tickfont=dict(size=10)),
        plot_bgcolor=theme.PLOT_BG, showlegend=False)
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=1.02, showarrow=False,
        font=dict(size=11, color="#555"), xanchor="left",
        text="Opacity (not hue) carries seizure pressure: bold = "
             "lightly-policed corridor (low seizures), faded = already under "
             "interdiction. ⚑ outlined = high-margin priority gap. "
             "Hue = substance.")
    return fig


@memoize_figure()
def priority_gap_list(data, filtered_prices, filtered_seizures, country, substances):
    """Ranked HTML list of the flagged priority-gap corridors (for the report).

    Returns Dash html components mirroring the ⚑ bars: high-margin,
    low-seizure (neighbour, substance) corridors, ordered by margin.
    """
    from dash import html

    rows = _compute_rows(data, filtered_prices, filtered_seizures,
                         country, substances)
    if not rows or rows in (None, "no_neigh"):
        return html.Small(
            "Select a single country to list its priority border gaps.",
            className="text-muted")

    gaps = sorted((r for r in rows if r["priority"]),
                  key=lambda r: r["margin"], reverse=True)
    if not gaps:
        return html.Small(
            "No priority gaps for the current filters — every high-margin "
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
            html.Strong(f"{r['neighbour']} · {r['substance']} "),
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


@memoize_figure()
def neighbour_map(data, country):
    """Small choropleth highlighting the selected country and its neighbours."""
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
