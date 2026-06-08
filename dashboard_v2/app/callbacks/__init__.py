"""Register all callback groups against the Dash app."""
from . import figures, selection, tabs, zoom


def register_callbacks(app, data):
    selection.register(app, data)
    zoom.register(app, data)
    tabs.register(app, data)
    figures.register(app, data)
