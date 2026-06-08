"""The cross-filter brain: one callback that merges every brushing source into
the canonical selection-store. ctx.triggered_id decides which dimension to set.

This replaces the old 18-input monolith's if/elif reconstruction and the
fragile ' Europe' string surgery / positional geodataframe indexing.
"""
from dash import ALL, Input, Output, State, ctx


def _empty():
    return {"country": None, "countries": None, "substance": None,
            "year": None, "subregion": None}


def register(app, data):
    @app.callback(
        Output("selection-store", "data"),
        Output("brushing-info", "children"),
        Input("timeseries-chart", "clickData"),
        Input("price-ladder", "clickData"),
        Input("priority-heatmap", "clickData"),
        Input("margin-map", "clickData"),
        Input("reset-button", "n_clicks"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection(ts_click, ladder_click, prio_hm_click, margin_click,
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

            if trigger == "priority-heatmap" and prio_hm_click:
                pt = prio_hm_click["points"][0]
                # customdata = [country, substance]
                cd = pt.get("customdata") or []
                if len(cd) >= 2:
                    sel["country"] = cd[0]
                    sel["substance"] = cd[1]
                    return sel, f"Priority: {cd[0]}, {cd[1]}"
        except (KeyError, IndexError, TypeError):
            pass

        return sel, "Click any chart to filter the rest."

    # Reset also clears the map-driven country selection and the substance
    # legend selection, so one button returns the whole app to "all".
    @app.callback(
        Output("country-store", "data", allow_duplicate=True),
        Output("substance-select-store", "data", allow_duplicate=True),
        Input("reset-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_external_selections(_n):
        return [], []

    # Clicking a substance in the shared Key-indicators legend toggles it in the
    # active set. The store uses [] = "all active", so the first click on a
    # full-active legend deselects one by materialising all-minus-that.
    all_substances = data.substances

    @app.callback(
        Output("substance-select-store", "data"),
        Input({"type": "subst-legend", "index": ALL}, "n_clicks"),
        State("substance-select-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_substance(_clicks, current):
        clicked = ctx.triggered_id and ctx.triggered_id.get("index")
        if not clicked:
            return current or []
        active = list(current) if current else list(all_substances)
        if clicked in active:
            active = [s for s in active if s != clicked]
        else:
            # keep canonical (data.substances) order
            active = [s for s in all_substances if s in active or s == clicked]
        # Falling back to all-active when nothing is left keeps "[] = all" tidy.
        return [] if set(active) == set(all_substances) or not active else active
