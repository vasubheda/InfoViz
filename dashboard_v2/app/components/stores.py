"""All shared client-side state: the canonical selection store and the
map-driven country selection.
"""
from dash import dcc


def make_stores():
    return [
        dcc.Store(id="selection-store", data={
            "country": None, "countries": None, "substance": None,
            "year": None, "subregion": None,
        }),
        # Canonical country selection, driven entirely by the enforcement map
        # (replaces the old country dropdown). Empty list = all of Europe.
        dcc.Store(id="country-store", data=[]),
    ]
