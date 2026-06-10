from dash import Input, Output

_PANELS = ["panel-overview", "panel-national", "panel-q1", "panel-q3"]
_TAB_TO_PANEL = {"tab-overview": "panel-overview",
                 "tab-national": "panel-national",
                 "tab-q1": "panel-q1", "tab-q3": "panel-q3"}


def register(app, data):
    @app.callback(
        [Output(p, "style") for p in _PANELS],
        Input("detail-tabs", "active_tab"),
    )
    def toggle(active_tab):
        active = _TAB_TO_PANEL.get(active_tab, "panel-overview")
        return [{} if p == active else {"display": "none"} for p in _PANELS]
