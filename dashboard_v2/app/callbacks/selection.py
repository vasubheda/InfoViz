from dash import ALL, Input, Output, State, ctx


def empty():
    return {"country": None, "countries": None, "substance": None,
            "year": None, "subregion": None}


def register(app, data):
    @app.callback(
        Output("selection-store", "data"),
        Output("brushing-info", "children"),
        Input("margin-map", "clickData"),
        Input("reset-button", "n_clicks"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection(margin_click, reset, current):
        trigger = ctx.triggered_id
        sel = dict(current or empty())

        if trigger == "reset-button":
            return empty(), "Selection cleared."

        try:
            if trigger == "margin-map" and margin_click:
                pt = margin_click["points"][0]
                country = pt.get("hovertext")
                if country:
                    sel["country"] = country
                    return sel, f"Country: {country}"
        except (KeyError, IndexError, TypeError):
            pass

        return sel, "Click any chart to filter the rest."

    # reset also clears the map and substance selections
    @app.callback(
        Output("country-store", "data", allow_duplicate=True),
        Output("substance-select-store", "data", allow_duplicate=True),
        Input("reset-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_external_selections(_n):
        return [], []

    # clicking a substance in the legend toggles it; [] means all active
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
        # ignore spurious fires from cards mounting with n_clicks=0
        triggered_value = ctx.triggered[0]["value"] if ctx.triggered else None
        if not triggered_value:
            return current or []
        active = list(current) if current else list(all_substances)
        if clicked in active:
            active = [s for s in active if s != clicked]
        else:
            # keep canonical (data.substances) order
            active = [s for s in all_substances if s in active or s == clicked]
        # fall back to all-active when nothing is left
        return [] if set(active) == set(all_substances) or not active else active

    # the temporal dropdown offers whatever substances are active in the legend
    @app.callback(
        Output("temporal-substance", "options"),
        Output("temporal-substance", "value"),
        Input("substance-select-store", "data"),
        State("temporal-substance", "value"),
    )
    def sync_temporal_substance(active, current):
        avail = active or all_substances
        avail = [s for s in all_substances if s in set(avail)]
        options = [{"label": s, "value": s} for s in avail]
        value = current if current in avail else (avail[0] if avail else None)
        return options, value
