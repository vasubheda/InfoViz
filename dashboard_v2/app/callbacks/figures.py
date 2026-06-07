"""The single figures callback: global filters + selection + map-driven country
-> every figure. Each figure is produced by a pure builder; the Q1 lag and Q4
priority charts re-aggregate under the active selection (fixing the old app's
frozen-panel bug).
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html

from ..figures import (border_arbitrage, heatmaps, helpers, lag_corr, maps,
                       multivariate, priority, timeseries)
from ..figures.filtering import Filters, apply_filters
from .. import theme


def register(app, data):
    @app.callback(
        Output("enforcement-map", "figure"),
        Output("timeseries-chart", "figure"),
        Output("lag-correlation-chart", "figure"),
        Output("lag-limitations", "children"),
        Output("regression-chart", "figure"),
        Output("regression-stats", "children"),
        Output("heatmap-retail", "figure"),
        Output("heatmap-wholesale", "figure"),
        Output("margin-map", "figure"),
        Output("arbitrage-map", "figure"),
        Output("priority-chart", "figure"),
        Output("scatter-plot", "figure"),
        Output("border-arbitrage-chart", "figure"),
        Output("border-arbitrage-gaps", "children"),
        Output("neighbour-map", "figure"),
        Output("kpi-panel", "children"),
        Output("substance-table", "data"),
        Input("substance-table", "selected_rows"),
        Input("country-store", "data"),
        Input("year-slider", "value"),
        Input("timeseries-metric", "value"),
        Input("x-axis", "value"),
        Input("y-axis", "value"),
        Input("arb-country", "value"),
        Input("arb-substance", "value"),
        Input("arb-level", "value"),
        Input("selection-store", "data"),
        State("substance-table", "data"),
    )
    def update(selected_rows, countries, year_range, metric, x_axis, y_axis,
               arb_country, arb_substance, arb_level, selection,
               table_rows):
        selection = dict(selection or {})

        # Substances come from the selected rows of the Key-indicators table.
        # No rows selected -> treat as "all substances".
        all_substances = [r["Substance"] for r in (table_rows or [])]
        selected_rows = selected_rows or []
        picked = [all_substances[i] for i in selected_rows
                  if 0 <= i < len(all_substances)]
        substances = picked or all_substances

        # The country selection (driven by the map) folds into the selection
        # dict the figure builders already understand: exactly one -> a
        # single-country context (drives per-country views like the Q1 lag
        # bars); several -> a multi-country subset.
        countries = countries or []
        country_filter_active = len(countries) > 0
        if len(countries) == 1:
            selection["country"] = countries[0]
            selection["countries"] = None
        elif len(countries) > 1:
            selection["country"] = None
            selection["countries"] = countries

        filters = Filters(substances=substances, year_range=list(year_range))
        f_prices = apply_filters(data.prices, filters, selection)
        f_seiz = apply_filters(data.seizures, filters, selection)
        f_comb = apply_filters(data.combined, filters, selection)

        enf_map = maps.enforcement_map(data, f_seiz, selection)
        ts = timeseries.timeseries(data, f_comb, metric, selection, year_range)
        lag_fig = lag_corr.lag_correlation(data, selection,
                                           target=("Typical_USD" if y_axis != "Typical"
                                                   else "Typical"))
        lag_note = _lag_limitations(data)
        reg_fig, reg_stats = multivariate.regression_facets(data, f_comb, x_axis, y_axis)

        # Cross-country views (regional heatmaps + choropleths) only carry meaning
        # across all of Europe. With a country filter active they would render a
        # single region row / a handful of coloured polygons, which misleads, so
        # we swap in an instruction note instead.
        if country_filter_active:
            hm_r = hm_w = helpers.filter_note_fig(400)
            margin = arb = helpers.filter_note_fig(400)
        else:
            hm_r = heatmaps.price_heatmap(data, f_prices, "Retail", selection)
            hm_w = heatmaps.price_heatmap(data, f_prices, "Wholesale", selection)
            margin = maps.margin_map(data, selection)
            arb = maps.arbitrage_map(data, f_prices, arb_country, arb_substance, arb_level)
        prio = priority.priority_dotplot(data, selection, substances, year_range)
        scat = multivariate.scatter(data, f_comb, selection)

        # Border arbitrage needs prices for the selected country AND its
        # neighbours, so it cannot use the country-brushed frame. Filter by
        # year + substance only, then let the builder pick out the neighbours.
        single_country = countries[0] if len(countries) == 1 else None
        geo_unfiltered = {"country": None, "countries": None,
                          "substance": selection.get("substance"),
                          "year": selection.get("year"), "subregion": None}
        arb_prices = apply_filters(data.prices, filters, geo_unfiltered)
        arb_seiz = apply_filters(data.seizures, filters, geo_unfiltered)
        border_arb = border_arbitrage.border_arbitrage(
            data, arb_prices, arb_seiz, single_country, substances)
        border_gaps = border_arbitrage.priority_gap_list(
            data, arb_prices, arb_seiz, single_country, substances)
        neigh_map = border_arbitrage.neighbour_map(data, single_country)

        kpi = _kpi(f_seiz, f_prices)

        # The table always lists every substance (so any can be picked); its
        # values reflect the year + map selection but NOT the substance pick.
        tbl_filters = Filters(substances=all_substances, year_range=list(year_range))
        t_seiz = apply_filters(data.seizures, tbl_filters, selection)
        t_prices = apply_filters(data.prices, tbl_filters, selection)
        t_comb = apply_filters(data.combined, tbl_filters, selection)
        table_data = _substance_rows(all_substances, t_seiz, t_prices, t_comb)

        return (enf_map, ts, lag_fig, lag_note, reg_fig, reg_stats, hm_r, hm_w,
                margin, arb, prio, scat, border_arb, border_gaps, neigh_map,
                kpi, table_data)


def _lag_limitations(data):
    p = data.manifest["lag_params"]
    return [html.Strong("Limitations: "),
            f"only {p['min_pairs']}+ paired years per country are correlated; "
            "5-year window (2019–2023) gives small n; prices are USD-normalised "
            "per gram; correlation is not causation."]


def _kpi(seiz, prices):
    total_t = seiz["Kilograms"].sum() / 1000 if len(seiz) else 0
    n_countries = prices["Country"].nunique() if len(prices) else 0
    scalar_cards = [
        ("Total seizures (t)", f"{total_t:,.1f}", theme.ACCENT_ALT),
        ("Countries", f"{n_countries}", "#CC79A7"),
    ]
    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(val, style={"color": color}),
            html.P(label, className="text-muted mb-0"),
        ]), className="text-center",
            style={"borderLeft": f"4px solid {color}"}), md=6)
        for label, val, color in scalar_cards], className="mb-3")


def _substance_rows(all_substances, seiz, prices, comb):
    """Per-substance seizures / avg price / avg purity as DataTable row dicts.

    Always returns one row per substance in ``all_substances`` (fixed order, so
    the table's selected-row indices stay meaningful), with "—" where a metric
    has no data under the current year + map selection.
    """
    seiz_by = (seiz.groupby("Substance")["Kilograms"].sum() / 1000
               if len(seiz) else None)
    price_by = (prices.groupby("Substance")["Typical_USD"].mean()
                if len(prices) else None)
    purity_by = (comb.groupby("Substance")["Typical"].mean()
                 if len(comb) else None)

    def fmt(series, s, pattern):
        if series is None or s not in series.index:
            return "—"
        v = series[s]
        return pattern.format(v) if v == v else "—"

    return [{
        "Substance": s,
        "Seizures": fmt(seiz_by, s, "{:,.1f}"),
        "Price": fmt(price_by, s, "${:,.2f}"),
        "Purity": fmt(purity_by, s, "{:.1f}%"),
    } for s in all_substances]
