"""Detail-view tab switching. The four research-question panels stay mounted at
all times (so the single figures mega-callback can keep writing to every graph);
this callback just toggles each panel's visibility via its `style`.
"""
from dash import Input, Output

_PANELS = ["panel-q1", "panel-q2", "panel-q3", "panel-q45"]
_TAB_TO_PANEL = {"tab-q1": "panel-q1", "tab-q2": "panel-q2",
                 "tab-q3": "panel-q3", "tab-q45": "panel-q45"}


def register(app, data):
    @app.callback(
        [Output(p, "style") for p in _PANELS],
        Input("detail-tabs", "active_tab"),
    )
    def _toggle(active_tab):
        active = _TAB_TO_PANEL.get(active_tab, "panel-q1")
        return [{} if p == active else {"display": "none"} for p in _PANELS]
