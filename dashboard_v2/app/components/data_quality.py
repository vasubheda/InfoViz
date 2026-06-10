import dash_bootstrap_components as dbc
from dash import html

# friendly labels for the imputed columns the manifest reports on
_COL_LABELS = {
    "Typical_USD": "Typical price (USD/g)",
    "Minimum_USD": "Minimum price (USD/g)",
    "Maximum_USD": "Maximum price (USD/g)",
    "Typical": "Typical purity (%)",
    "Minimum": "Minimum purity (%)",
    "Maximum": "Maximum purity (%)",
    "Kilograms": "Seizures (kg)",
}

_TABLE_LABELS = {"prices": "Prices", "purity": "Purity", "seizures": "Seizures"}


def imputation_summary(manifest):
    """Per-column imputation counts pulled straight from the build manifest."""
    imp = manifest.get("imputation", {})

    header = html.Thead(html.Tr([
        html.Th("Source"), html.Th("Field"),
        html.Th("Missing", className="text-end"),
        html.Th("Interpolated", className="text-end"),
        html.Th("Median-filled", className="text-end"),
        html.Th("Still missing", className="text-end"),
    ]))

    rows = []
    for table, cols in imp.items():
        for col, stats in cols.items():
            median_filled = (stats.get("median_country_substance", 0)
                             + stats.get("median_subregion_substance", 0))
            rows.append(html.Tr([
                html.Td(_TABLE_LABELS.get(table, table.title())),
                html.Td(_COL_LABELS.get(col, col)),
                html.Td(f"{stats.get('originally_missing', 0):,}",
                        className="text-end"),
                html.Td(f"{stats.get('interpolated', 0):,}",
                        className="text-end"),
                html.Td(f"{median_filled:,}", className="text-end"),
                html.Td(f"{stats.get('left_missing', 0):,}",
                        className="text-end"),
            ]))

    table = dbc.Table([header, html.Tbody(rows)],
                      size="sm", bordered=False, hover=True, striped=True,
                      className="small mb-0")

    method = html.P([
        "Missing price and purity values are estimated in two steps: first by ",
        "temporal interpolation",
        " across years within each country, substance and sale level, then by "
        "filling any remaining gaps with the ",
        "median",
        " of the same substance in that country (falling back to the "
        "sub-region). ",
        "Seizures are never imputed",
        " - a missing seizure figure does not mean zero seizures, so those "
        "cells are left blank.",
    ], className="small text-muted")

    return html.Div([method, table])


def data_quality_modal(data):
    """Modal explaining how missing data is handled, plus the marker legend."""
    legend = html.P([
        html.Span("○", style={"fontSize": "1.1rem", "marginRight": "6px"}),
        "Open / hollow markers mark ",
        html.Strong("estimated (imputed)"),
        " values.  ",
        html.Span("●", style={"fontSize": "1.1rem",
                                   "margin": "0 6px 0 12px"}),
        "Solid markers are ",
        html.Strong("reported measurements"),
        ".",
    ], className="small mt-3 mb-0")

    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("How is missing data handled?")),
        dbc.ModalBody([
            imputation_summary(data.manifest),
            legend,
        ]),
    ], id="data-quality-modal", size="lg", scrollable=True, is_open=False)
