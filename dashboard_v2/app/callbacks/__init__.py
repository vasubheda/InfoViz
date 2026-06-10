from . import figures, selection, tabs, zoom, sidebar


def register_callbacks(app, data):
    selection.register(app, data)
    zoom.register(app, data)
    tabs.register(app, data)
    figures.register(app, data)
    sidebar.register(app, data)
