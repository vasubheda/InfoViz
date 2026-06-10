import dash_bootstrap_components as dbc
from dash import Input, Output, Patch, State, html, no_update

from ..figures import (border_arbitrage, key_indicators, lag_corr,
                       maps, multivariate, subregion, temporal_maps, timeseries)
from ..figures.filtering import Filters, apply_filters
from .. import theme


def register(app, data):
    def context(active_store, countries, year_from, year_to, selection):
        # normalise the shared filter/selection inputs
        selection = fold_countries(selection, countries)
        year_range = sorted([year_from, year_to])
        all_substances = data.substances
        active_store = active_store or []
        substances = active_store or all_substances
        filters = Filters(substances=substances, year_range=list(year_range))
        return (selection, substances, all_substances, year_range,
                list(countries or []), filters)

    def fold_countries(selection, countries):
        # one country -> single context, several -> a subset
        selection = dict(selection or {})
        countries = countries or []
        if len(countries) == 1:
            selection["country"], selection["countries"] = countries[0], None
        elif len(countries) > 1:
            selection["country"], selection["countries"] = None, countries
        return selection

    # master panel split into three callbacks so each only rebuilds on what it needs

    # the map just patches the outline overlay instead of redrawing everything
    _outline_idx = maps.enforcement_outline_index(data)

    @app.callback(
        Output("enforcement-map", "figure"),
        Input("country-store", "data"),
        Input("selection-store", "data"),
    )
    def update_map(countries, selection):
        selected = maps.selected_countries(fold_countries(selection, countries))
        patch = Patch()
        patch["data"][_outline_idx]["locations"] = selected
        patch["data"][_outline_idx]["z"] = [1] * len(selected)
        return patch

    # substance legend, driven only by the active substance set
    @app.callback(
        Output("substance-legend", "children"),
        Input("substance-select-store", "data"),
    )
    def update_legend(active_store):
        return key_indicators.substance_cards(data, data.substances,
                                              active_store or [])

    # kpi total, depends on every global filter
    @app.callback(
        Output("kpi-panel", "children"),
        Input("substance-select-store", "data"),
        Input("country-store", "data"),
        Input("year-from", "value"),
        Input("year-to", "value"),
        Input("selection-store", "data"),
    )
    def update_kpi(active_store, countries, year_from, year_to, selection):
        selection, _substances, _all, year_range, _co, filters = \
            context(active_store, countries, year_from, year_to, selection)
        f_prices = apply_filters(data.prices, filters, selection)
        f_seiz = apply_filters(data.seizures, filters, selection)
        return kpi(f_seiz, f_prices, year_range)

    @app.callback(
        Output("temporal-maps", "figure"),
        Output("temporal-highlights", "children"),
        Output("ts-seizures", "figure"),
        Output("ts-price", "figure"),
        Output("ts-purity", "figure"),
        Output("lag-correlation-chart", "figure"),
        Output("lag-limitations", "children"),
        Output("regression-chart", "figure"),
        Output("regression-stats", "children"),
        Output("margin-map", "figure"),
        Output("margin-highlights", "children"),
        Output("border-arbitrage-chart", "figure"),
        Output("border-arbitrage-gaps", "children"),
        Output("market-flow-map", "figure"),
        Output("neighbour-map", "figure"),
        Output("ki-seizures-bar", "figure"),
        Output("ki-price-bar", "figure"),
        Output("ki-purity-bar", "figure"),
        Output("sr-seizures", "figure"),
        Output("sr-price", "figure"),
        Output("sr-purity", "figure"),
        Input("substance-select-store", "data"),
        Input("country-store", "data"),
        Input("year-from", "value"),
        Input("year-to", "value"),
        Input("x-axis", "value"),
        Input("y-axis", "value"),
        Input("selection-store", "data"),
        Input("detail-tabs", "active_tab"),
        Input("temporal-metric", "value"),
        Input("temporal-substance", "value"),
        Input("q3-year", "value"),
    )
    def update(active_store, countries, year_from, year_to, x_axis, y_axis,
               selection, active_tab, temporal_metric, temporal_substance,
               q3_year):
        selection, substances, all_substances, year_range, countries, filters = \
            context(active_store, countries, year_from, year_to, selection)

        # defaults - skip outputs for tabs that aren't active
        temp_maps = temp_hi = no_update
        ts_seiz = ts_price_fig = ts_purity_fig = lag_fig = lag_note = \
        reg_fig = reg_stats = margin = margin_hi = border_arb = \
        border_gaps = flow_map = neigh_map = ki_seiz = ki_price = ki_purity = \
        sr_seiz = sr_price = sr_purity = no_update

        # overview tab
        if active_tab == "tab-overview":
            # only build the time series when there's an actual range
            if year_range[0] != year_range[1]:
                f_comb_outer = apply_filters(data.combined_outer, filters, selection)
                ts_seiz = timeseries.timeseries_single(data, f_comb_outer, selection, 0)
                ts_price_fig = timeseries.timeseries_single(data, f_comb_outer, selection, 1)
                ts_purity_fig = timeseries.timeseries_single(data, f_comb_outer, selection, 2)

            tbl_filters = Filters(substances=all_substances, year_range=list(year_range))
            t_seiz = apply_filters(data.seizures, tbl_filters, selection)
            t_prices = apply_filters(data.prices, tbl_filters, selection)
            t_comb = apply_filters(data.combined, tbl_filters, selection)
            ki_seiz, ki_price, ki_purity = key_indicators.substance_bars(
                data, all_substances, active_store, t_seiz, t_prices, t_comb)
            # subregion trends ignore the country selection, only year/substance apply
            sr_selection = {"country": None, "countries": None,
                            "subregion": None,
                            "substance": selection.get("substance"),
                            "year": selection.get("year")}
            f_seiz = apply_filters(data.seizures, filters, sr_selection)
            sr_comb_outer = apply_filters(data.combined_outer, filters,
                                          sr_selection)
            sr_seiz, sr_price, sr_purity = subregion.subregion_trends(
                data, f_seiz, sr_comb_outer, year_range[0] == year_range[1])

        # national tab - metric-over-time map plus the markup map
        elif active_tab == "tab-national":
            temp_maps = temporal_maps.temporal_maps(
                data, temporal_metric, temporal_substance, year_range,
                countries=countries)
            temp_hi = temporal_maps.temporal_highlights(
                data, temporal_metric, temporal_substance, year_range,
                countries=countries)
            margin = maps.margin_map(data, selection, substances,
                                     year_range=list(year_range))
            margin_hi = maps.margin_highlights(data, selection, substances,
                                               year_range=list(year_range))

        # seizure impact tab
        elif active_tab == "tab-q1":
            f_comb = apply_filters(data.combined, filters, selection)
            lag_fig = lag_corr.lag_correlation(data, selection,
                                               target=("Typical_USD" if y_axis != "Typical"
                                                       else "Typical"))
            lag_note = lag_limitations(data)
            reg_fig, reg_stats = multivariate.regression_facets(data, f_comb, x_axis, y_axis)

        # cross-border tab
        elif active_tab == "tab-q3":
            # single-year snapshot, clamp the slider into range, default to latest
            q3_yr = q3_year if (q3_year is not None
                                and year_range[0] <= q3_year <= year_range[1]) \
                else year_range[1]
            q3_filters = Filters(substances=substances,
                                 year_range=[q3_yr, q3_yr])
            geo_unfiltered = {"country": None, "countries": None,
                              "substance": selection.get("substance"),
                              "year": selection.get("year"), "subregion": None}
            arb_prices = apply_filters(data.prices, q3_filters, geo_unfiltered)
            arb_seiz = apply_filters(data.seizures, q3_filters, geo_unfiltered)
            if len(countries) == 1:
                # single-country land-border arbitrage plus neighbour map
                single_country = countries[0]
                border_arb = border_arbitrage.border_arbitrage(
                    data, arb_prices, arb_seiz, single_country, substances)
                border_gaps = border_arbitrage.priority_gap_list(
                    data, arb_prices, arb_seiz, single_country, substances)
                neigh_map = border_arbitrage.neighbour_map(data, single_country)
            else:
                # multi/all-country market arbitrage: flow map + ranked corridor bars
                flow_map = border_arbitrage.market_flow_map(
                    data, arb_prices, arb_seiz, countries, substances)
                border_arb = border_arbitrage.market_arbitrage(
                    data, arb_prices, arb_seiz, countries, substances)
                border_gaps = border_arbitrage.market_gap_list(
                    data, arb_prices, arb_seiz, countries, substances)

        return (temp_maps, temp_hi, ts_seiz, ts_price_fig, ts_purity_fig,
                lag_fig, lag_note, reg_fig, reg_stats,
                margin, margin_hi, border_arb, border_gaps, flow_map, neigh_map,
                ki_seiz, ki_price, ki_purity,
                sr_seiz, sr_price, sr_purity)

    # hide the overview time-series row for a single year
    @app.callback(
        Output("ts-row", "style"),
        Input("year-from", "value"),
        Input("year-to", "value"),
    )
    def toggle_ts_row(year_from, year_to):
        return {"display": "none"} if year_from == year_to else {}

    # one country -> chart + neighbour map, otherwise full-width market spread
    @app.callback(
        Output("q3-chart-col", "md"),
        Output("q3-neighbour-col", "style"),
        Output("q3-flow-wrap", "style"),
        Input("country-store", "data"),
    )
    def toggle_q3_layout(countries):
        single = len(countries or []) == 1
        hide = {"display": "none"}
        return ((8 if single else 12), ({} if single else hide),
                (hide if single else {}))

    # keep the year slider in sync with the global range
    @app.callback(
        Output("q3-year", "min"),
        Output("q3-year", "max"),
        Output("q3-year", "marks"),
        Output("q3-year", "value"),
        Input("year-from", "value"),
        Input("year-to", "value"),
        State("q3-year", "value"),
    )
    def q3_year_bounds(year_from, year_to, current):
        lo, hi = sorted([year_from, year_to])
        marks = {y: str(y) for y in range(lo, hi + 1)}
        value = current if (current is not None and lo <= current <= hi) else hi
        return lo, hi, marks, value


def lag_limitations(data):
    p = data.manifest["lag_params"]
    return [html.Strong("Limitations: "),
            f"only {p['min_pairs']}+ paired years per country are correlated; "
            "5-year window (2019-2023) gives small n; prices are USD-normalised "
            "per gram; correlation is not causation."]


def kpi(seiz, prices, year_range):
    # compact total-seizures indicator for the master panel
    total_t = seiz["Kilograms"].sum() / 1000 if len(seiz) else 0
    lo, hi = year_range
    year_label = str(lo) if lo == hi else f"{lo}-{hi}"
    color = "#495057"
    return dbc.Card(dbc.CardBody([
        html.H4(f"{total_t:,.1f}", className="mb-0", style={"color": color}),
        html.P(f"Total seizures (t), in {year_label}",
               className="text-muted small mb-0"),
    ]), className="text-center",
        style={"borderLeft": f"4px solid {color}"})
