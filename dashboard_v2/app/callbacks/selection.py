"""The cross-filter brain: one callback that merges every brushing source into
the canonical selection-store. ctx.triggered_id decides which dimension to set.

This replaces the old 18-input monolith's if/elif reconstruction and the
fragile ' Europe' string surgery / positional geodataframe indexing.
"""
from dash import Input, Output, State, ctx


def _empty():
    return {"country": None, "countries": None, "substance": None,
            "year": None, "subregion": None}


def register(app, data):
    @app.callback(
        Output("selection-store", "data"),
        Output("brushing-info", "children"),
        Input("timeseries-chart", "clickData"),
        Input("price-ladder", "clickData"),
        Input("margin-map", "clickData"),
        Input("reset-button", "n_clicks"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection(ts_click, ladder_click, margin_click,
                         reset, current):
        trigger = ctx.triggered_id
        sel = dict(current or _empty())

        if trigger == "reset-button":
            return _empty(), "Selection cleared."

        try:
            if trigger == "margin-map" and margin_click:
                pt = margin_click["points"][0]
                country = pt.get("hovertext")
                if country:
                    sel["country"] = country
                    return sel, f"Country: {country}"

            if trigger == "timeseries-chart" and ts_click:
                pt = ts_click["points"][0]
                sel["year"] = pt.get("x")
                msg = f"Year {sel['year']}"
                grp = pt.get("legendgroup")
                if grp:
                    sel["substance"] = grp
                    msg += f" · {grp}"
                return sel, msg

            if trigger == "price-ladder" and ladder_click:
                pt = ladder_click["points"][0]
                # customdata = [substance, region, ws, rt, markup]
                cd = pt.get("customdata") or []
                substance = cd[0] if len(cd) > 0 else pt.get("y")
                region = cd[1] if len(cd) > 1 else None
                sel["substance"] = substance
                # store canonical SubRegion (append ' Europe' if needed)
                if region:
                    sel["subregion"] = (region if "Europe" in region
                                        else f"{region} Europe")
                return sel, f"Price ladder: {region}, {substance}"
        except (KeyError, IndexError, TypeError):
            pass

        return sel, "Click any chart to filter the rest."

    # Reset also clears the map-driven country selection and the substance
    # table's row selection, so one button returns the whole app to "all".
    @app.callback(
        Output("country-store", "data", allow_duplicate=True),
        Output("substance-table", "selected_rows"),
        Input("reset-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_external_selections(_n):
        return [], []
