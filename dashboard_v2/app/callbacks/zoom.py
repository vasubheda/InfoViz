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
            country = click["points"][0].get("hovertext")
            if not country:
                return no_update
            if country in selected:
                selected.remove(country)
            else:
                selected.append(country)
            return selected

        return no_update
