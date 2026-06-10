from dash import Input, Output, State, ctx, no_update

from ..figures.maps import subregion_order


def register(app, data):
    country_subregion = data.prices[["Country", "SubRegion"]].drop_duplicates()
    # map a clicked polygon back to its country name
    idx_to_country = data.europe_gdf["NAME"].to_dict()

    def clicked_country(click):
        pt = click["points"][0]
        # base trace carries hovertext, the overlay only has a location index
        name = pt.get("hovertext")
        if name:
            return name
        loc = pt.get("location")
        if loc is None:
            return None
        return idx_to_country.get(loc, loc)

    def region_of_trace(restyle):
        # map a legend restyle event to its subregion name
        try:
            idx = restyle[1][0]
        except (TypeError, IndexError):
            return None
        order = subregion_order(data)
        return order[idx] if 0 <= idx < len(order) else None

    @app.callback(
        Output("country-store", "data", allow_duplicate=True),
        Input("enforcement-map", "clickData"),
        Input("enforcement-map", "restyleData"),
        State("country-store", "data"),
        prevent_initial_call=True,
    )
    def map_select(click, restyle, current):
        selected = list(current or [])
        trigger_prop = (ctx.triggered[0]["prop_id"] if ctx.triggered else "")

        if trigger_prop.endswith("restyleData") and restyle:
            region = region_of_trace(restyle)
            if not region:
                return no_update
            members = country_subregion[
                country_subregion["SubRegion"] == region]["Country"].tolist()
            # toggle the whole region on/off
            if members and all(c in selected for c in members):
                selected = [c for c in selected if c not in members]
            else:
                selected = selected + [c for c in members if c not in selected]
            return selected

        if trigger_prop.endswith("clickData") and click:
            country = clicked_country(click)
            if not country:
                return no_update
            if country in selected:
                selected.remove(country)
            else:
                selected.append(country)
            return selected

        return no_update

    # show how many countries are selected
    @app.callback(
        Output("country-count", "children"),
        Input("country-store", "data"),
    )
    def country_count(selected):
        n = len(selected or [])
        return "All selected" if n == 0 else f"{n} selected"
