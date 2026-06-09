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
        Input("priority-heatmap", "clickData"),
        Input("margin-map", "clickData"),
        Input("reset-button", "n_clicks"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection(prio_hm_click, margin_click,
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
        # Ignore spurious fires caused by the substance cards being re-rendered
        # (new components mount with n_clicks=0; Dash fires ALL-pattern callbacks
        # for them even though no real click occurred).
        triggered_value = ctx.triggered[0]["value"] if ctx.triggered else None
        if not triggered_value:
            return current or []
        active = list(current) if current else list(all_substances)
        if clicked in active:
            active = [s for s in active if s != clicked]
        else:
            # keep canonical (data.substances) order
            active = [s for s in all_substances if s in active or s == clicked]
        # Falling back to all-active when nothing is left keeps "[] = all" tidy.
        return [] if set(active) == set(all_substances) or not active else active

    # The Temporal-tab substance dropdown offers exactly the substances active in
    # the master legend ([] = all). It keeps the current pick when that pick is
    # still active, otherwise falls back to the first available substance.
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
