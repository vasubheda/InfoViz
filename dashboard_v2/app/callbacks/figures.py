"""The single figures callback: global filters + selection + map-driven country
-> every figure. Each figure is produced by a pure builder; the Q1 lag and Q4
priority charts re-aggregate under the active selection (fixing the old app's
frozen-panel bug).
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html, no_update

from ..figures import (border_arbitrage, helpers, key_indicators, lag_corr,
                       maps, margin_trend, multivariate, price_ladder, priority,
                       priority_heatmap, quality_price, timeseries)
from ..figures.filtering import Filters, apply_filters
from .. import theme


def register(app, data):
    @app.callback(
        Output("enforcement-map", "figure"),
        Output("ts-seizures", "figure"),
        Output("ts-price", "figure"),
        Output("ts-purity", "figure"),
        Output("lag-correlation-chart", "figure"),
        Output("lag-limitations", "children"),
        Output("regression-chart", "figure"),
        Output("regression-stats", "children"),
        Output("price-ladder", "figure"),
        Output("margin-trend", "figure"),
        Output("quality-price", "figure"),
        Output("priority-heatmap", "figure"),
        Output("margin-map", "figure"),
        Output("arbitrage-map", "figure"),
        Output("priority-chart", "figure"),
        Output("border-arbitrage-chart", "figure"),
        Output("border-arbitrage-gaps", "children"),
        Output("neighbour-map", "figure"),
        Output("kpi-panel", "children"),
        Output("ki-seizures-bar", "figure"),
        Output("ki-price-bar", "figure"),
        Output("ki-purity-bar", "figure"),
        Output("substance-legend", "children"),
        Output("q2-insight-banner", "children"),
        Input("substance-select-store", "data"),
        Input("country-store", "data"),
        Input("year-slider", "value"),
        Input("x-axis", "value"),
        Input("y-axis", "value"),
        Input("arb-country", "value"),
        Input("arb-substance", "value"),
        Input("arb-level", "value"),
        Input("selection-store", "data"),
        Input("detail-tabs", "active_tab"),
    )
    def update(active_store, countries, year_range, x_axis, y_axis,
               arb_country, arb_substance, arb_level, selection, active_tab):
        selection = dict(selection or {})

        # Active substances come from the Key-indicators legend store.
        # Empty list -> treat as "all substances".
        all_substances = data.substances
        active_store = active_store or []
        substances = active_store or all_substances

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
        
        # MASTER PANEL: Always update
        enf_map = maps.enforcement_map(data, f_seiz, selection)
        kpi = _kpi(f_seiz, f_prices)
        subst_cards = key_indicators.substance_cards(data, all_substances, active_store)

        # Output Defaults (lazy loading - don't update if not active tab)
        ts_seiz = ts_price_fig = ts_purity_fig = lag_fig = lag_note = \
        reg_fig = reg_stats = ladder = \
        m_trend = qprice = prio_hm = margin = arb = prio = border_arb = \
        border_gaps = neigh_map = ki_seiz = ki_price = ki_purity = q2_insight = no_update

        # OVERVIEW TAB
        if active_tab == "tab-overview":
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

        # TAB Q1
        elif active_tab == "tab-q1":
            f_comb = apply_filters(data.combined, filters, selection)
            lag_fig = lag_corr.lag_correlation(data, selection,
                                               target=("Typical_USD" if y_axis != "Typical"
                                                       else "Typical"))
            lag_note = _lag_limitations(data)
            reg_fig, reg_stats = multivariate.regression_facets(data, f_comb, x_axis, y_axis)

        # TAB Q2
        elif active_tab == "tab-q2":
            f_comb = apply_filters(data.combined, filters, selection)
            if country_filter_active:
                ladder = m_trend = helpers.filter_note_fig(400)
                margin = helpers.filter_note_fig(400)
                q2_insight = html.Div()
            else:
                ladder = price_ladder.price_ladder(data, f_prices, selection)
                m_trend = margin_trend.margin_trend(data, f_prices, selection)
                margin = maps.margin_map(data, selection)

                # Insight generation
                q2_insight = _generate_q2_insight(data.inland_margin, f_prices)

            qprice = quality_price.quality_adjusted_price(data, f_comb, selection)

        # TAB Q3
        elif active_tab == "tab-q3":
            if country_filter_active:
                arb = helpers.filter_note_fig(400)
            else:
                arb = maps.arbitrage_map(data, f_prices, arb_country, arb_substance, arb_level)
                
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

        # TAB Q45
        elif active_tab == "tab-q45":
            prio = priority.priority_dotplot(data, selection, substances, year_range)
            prio_hm = priority_heatmap.priority_heatmap(
                data, selection, substances, year_range)

        return (enf_map, ts_seiz, ts_price_fig, ts_purity_fig,
                lag_fig, lag_note, reg_fig, reg_stats, ladder,
                m_trend, qprice, prio_hm,
                margin, arb, prio, border_arb, border_gaps, neigh_map,
                kpi, ki_seiz, ki_price, ki_purity, subst_cards, q2_insight)


def _lag_limitations(data):
    p = data.manifest["lag_params"]
    return [html.Strong("Limitations: "),
            f"only {p['min_pairs']}+ paired years per country are correlated; "
            "5-year window (2019–2023) gives small n; prices are USD-normalised "
            "per gram; correlation is not causation."]


def _kpi(seiz, prices):
    # A single compact total-seizures indicator, shown in the master panel.
    # (The old two-card KPI row — total seizures + countries — was dropped from
    # the Overview tab; the country count is already surfaced beside the map.)
    total_t = seiz["Kilograms"].sum() / 1000 if len(seiz) else 0
    color = theme.ACCENT_ALT
    return dbc.Card(dbc.CardBody([
        html.H4(f"{total_t:,.1f}", className="mb-0", style={"color": color}),
        html.P("Total seizures (t), current selection",
               className="text-muted small mb-0"),
    ]), className="text-center",
        style={"borderLeft": f"4px solid {color}"})
        
def _generate_q2_insight(inland_margin, f_prices):
    if len(inland_margin) == 0:
        return html.Div()
        
    margin = inland_margin.copy()
    valid = margin.dropna(subset=["Margin"])
    if len(valid) == 0:
        return html.Div()
        
    # Get the country with the absolute highest markup in the current selection
    max_idx = valid["Margin"].idxmax()
    top_row = valid.loc[max_idx]
    
    country = top_row["Country"]
    substance = top_row["Substance"]
    markup = top_row["Margin"]
    
    return dbc.Alert(
        [
            html.I(className="bi bi-info-circle-fill me-2"),
            html.Strong("Key Insight: "),
            f"Within the current selection, the highest absolute markup is observed in ",
            html.Strong(f"{country}"),
            f" for ",
            html.Strong(f"{substance}"),
            f" (${markup:,.0f}/g retail-wholesale spread)."
        ],
        color="info",
        className="d-flex align-items-center mb-0"
    )

