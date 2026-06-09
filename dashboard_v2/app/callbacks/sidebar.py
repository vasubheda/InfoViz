"""Sidebar toggle callback.

Provides the 'Collapse'/'Expand' behaviour for the Master filter panel.
"""
from dash import Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc

def register(app, data):
    @app.callback(
        Output("master-col", "style"),
        Output("detail-col", "md"),
        Output("sidebar-show-btn", "style"),
        Input("sidebar-toggle-btn", "n_clicks"),
        Input("sidebar-show-btn", "n_clicks"),
        State("master-col", "style"),
        prevent_initial_call=True
    )
    def toggle_sidebar(hide_clicks, show_clicks, master_style):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # We start with it shown.
        # Hide action: master-col -> display none. Detail-col -> md 12. Show btn -> display inline-block.
        if button_id == "sidebar-toggle-btn":
            new_style = dict(master_style) if master_style else {}
            new_style["display"] = "none"
            return new_style, 12, {"display": "inline-block"}
            
        # Show action: master-col -> display None removed. Detail-col -> md 8. Show btn -> display none.
        if button_id == "sidebar-show-btn":
            new_style = dict(master_style) if master_style else {}
            if "display" in new_style:
                del new_style["display"]
            return new_style, 8, {"display": "none"}
            
        return no_update, no_update, no_update
