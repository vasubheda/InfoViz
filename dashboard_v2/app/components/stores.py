from dash import dcc


def make_stores():
    return [
        dcc.Store(id="selection-store", data={
            "country": None, "countries": None, "substance": None,
            "year": None, "subregion": None,
        }),
        # country selection from the map, [] = all of Europe
        dcc.Store(id="country-store", data=[]),
        # active substances from the legend, [] = all active
        dcc.Store(id="substance-select-store", data=[]),
    ]
