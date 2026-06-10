"""Enforcement-map selection wiring.

The overview map is a flat choropleth (every country coloured by its subregion).
Two ways to select feed the same global country filter:

  * clicking a country polygon toggles that single country;
  * clicking a subregion in the legend toggles every country in that region.

Plotly does not emit a click event for legend items - it toggles trace
visibility instead - so legend interactions are read from the graph's
``restyleData`` (the visibility change + the trace index, which maps back to a
subregion via the deterministic ``subregion_order``).
"""
from dash import Input, Output, State, ctx, no_update

from ..figures.maps import subregion_order


def register(app, data):
    country_subregion = data.prices[["Country", "SubRegion"]].drop_duplicates()
    # Map a clicked polygon back to its country. Both the base choropleth and the
    # selection-outline overlay use the europe_gdf row index as `location`, so the
    # index resolves a click on either trace (the overlay carries no hovertext).
    idx_to_country = data.europe_gdf["NAME"].to_dict()

    def _clicked_country(click):
        pt = click["points"][0]
        # The base choropleth carries hovertext (country NAME) and is the normal
        # path. The selection-outline overlay carries none, so fall back to its
        # `location`: that overlay is keyed by country NAME, while the base trace
        # is keyed by the europe_gdf row index - so map an int index back to a
        # name and pass a NAME straight through.
        name = pt.get("hovertext")
        if name:
            return name
        loc = pt.get("location")
        if loc is None:
            return None
        return idx_to_country.get(loc, loc)

    def _region_of_trace(restyle):
        """Map a legend restyle event to its subregion name (or None)."""
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
            region = _region_of_trace(restyle)
            if not region:
                return no_update
            members = country_subregion[
                country_subregion["SubRegion"] == region]["Country"].tolist()
            # If every member is already selected, the click removes them;
            # otherwise it adds the whole region.
            if members and all(c in selected for c in members):
                selected = [c for c in selected if c not in members]
            else:
                selected = selected + [c for c in members if c not in selected]
            return selected

        if trigger_prop.endswith("clickData") and click:
            country = _clicked_country(click)
            if not country:
                return no_update
            if country in selected:
                selected.remove(country)
            else:
                selected.append(country)
            return selected

        return no_update

    # Show how many countries are currently selected next to the section
    # heading (no selection = the whole map / all countries).
    @app.callback(
        Output("country-count", "children"),
        Input("country-store", "data"),
    )
    def country_count(selected):
        n = len(selected or [])
        return "All selected" if n == 0 else f"{n} selected"
