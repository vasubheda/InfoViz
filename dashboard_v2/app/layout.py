"""App layout assembly. Reframed throughout to a law-enforcement / policy voice
(research questions from the proposal drive each panel).
"""
import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html

from .components.stores import make_stores
from .figures.helpers import imputed_legend_note


def _loading(component):
    """Wrap a component in a Dash loading overlay for recompute feedback."""
    return dcc.Loading(component, type="default", color="#0d6efd")


def _graph(graph_id, hint=None, displaymodebar=True):
    children = []
    if hint:
        children.append(html.Small(hint, className="text-muted d-block mb-1"))
    children.append(_loading(
        dcc.Graph(id=graph_id, config={"displayModeBar": displaymodebar})))
    return children


def _card(title, body, md=6):
    return dbc.Col(dbc.Card([
        dbc.CardHeader(html.H5(title, className="mb-0")),
        dbc.CardBody(body),
    ]), md=md)


def build_layout(data):
    substances = data.substances
    years = list(range(data.year_min, data.year_max + 1))
    imp = data.manifest["imputation"]
    total_imputed = sum(
        s.get("interpolated", 0) + s.get("median_country_substance", 0)
        + s.get("median_subregion_substance", 0)
        for table in imp.values() for s in table.values())

    return dbc.Container([
        # Header
        dbc.Row(dbc.Col([
            html.H1("European Drug-Market Intelligence",
                    className="text-center text-primary mb-2"),
            html.H5("An evidence base for enforcement prioritisation using "
                    "prices, purity & seizures, 2019–2023 (UNODC)",
                    className="text-center text-muted mb-3"),
            html.Hr(),
        ])),

        # Methodology / accessibility banner
        dbc.Row(dbc.Col(dbc.Alert([
            html.Strong("Reading this dashboard. "),
            "All palettes are colourblind-safe (Paul Tol Muted; Viridis; RdBu "
            "diverging). ", html.Em(imputed_legend_note()), ". ",
            f"{total_imputed} sporadically-missing values were imputed and flagged; "
            "seizure volumes are never imputed (a missing year is not a zero).",
        ], color="info", dismissable=True, className="mb-3"))),

        # KPI panel (with merged linked-selection controls in the header)
        dbc.Row(dbc.Col(dbc.Card([
            dbc.CardHeader(dbc.Row([
                dbc.Col(html.H5("Key indicators", className="mb-0"),
                        width="auto", className="d-flex align-items-center"),
                dbc.Col([
                    html.Strong("Linked selection: ", className="me-1"),
                    html.Span(id="brushing-info",
                              children="Click any chart to filter the rest."),
                ], className="d-flex align-items-center text-muted small"),
                dbc.Col(dbc.Button("Reset selection", id="reset-button",
                                   color="danger", size="sm"),
                        width="auto", className="d-flex align-items-center"),
            ], className="g-2 justify-content-between flex-nowrap")),
            dbc.CardBody([
                html.Label("Year range:", className="fw-bold"),
                dcc.RangeSlider(id="year-slider", min=data.year_min,
                                max=data.year_max,
                                value=[data.year_min, data.year_max],
                                marks={y: str(y) for y in years}, step=1,
                                className="mb-3"),
                _loading(html.Div(id="kpi-panel")),
                html.H6("Where & what: regions and countries", className="mb-1"),
                *_graph("enforcement-map"),
                html.Small("Select rows to filter every chart by substance "
                           "(none selected = all substances).",
                           className="text-muted d-block mb-1 mt-3"),
                dash_table.DataTable(
                    id="substance-table",
                    columns=[
                        {"name": "Substance", "id": "Substance"},
                        {"name": "Seizures (t)", "id": "Seizures"},
                        {"name": "Avg price (USD/g)", "id": "Price"},
                        {"name": "Avg purity", "id": "Purity"},
                    ],
                    data=[{"Substance": s} for s in substances],
                    row_selectable="multi",
                    selected_rows=[],
                    cell_selectable=False,
                    style_as_list_view=True,
                    style_cell={"fontSize": "0.85rem", "padding": "4px 8px",
                                "fontFamily": "inherit"},
                    style_header={"fontWeight": "bold"},
                    style_data_conditional=[
                        {"if": {"state": "selected"},
                         "backgroundColor": "rgba(13,110,253,0.12)",
                         "border": "1px solid rgba(13,110,253,0.4)"},
                    ],
                    style_cell_conditional=[
                        {"if": {"column_id": c}, "textAlign": "right"}
                        for c in ("Seizures", "Price", "Purity")
                    ],
                ),
            ]),
        ])), className="mb-4"),

        # Row: time series (Q5 / overview) + price vs purity
        dbc.Row([
            _card("Trends over time",
                  [dcc.Dropdown(id="timeseries-metric", clearable=False,
                                value="seizures", className="small mb-2",
                                options=[{"label": "Seizures (Tons)", "value": "seizures"},
                                         {"label": "Price (USD/g)", "value": "price"},
                                         {"label": "Purity (%)", "value": "purity"}]),
                   *_graph("timeseries-chart", "Click a point to filter by year")]),
            _card("Price vs purity",
                  _graph("scatter-plot")),
        ], className="mb-4"),

        # Row: Q1 lag correlation + regression
        dbc.Row([
            _card("Q1 · Do seizures move the market? (within-country, +1yr lag)",
                  [html.Small("Pearson r between seizures in year Y and street price "
                              "in Y+1, computed per country then aggregated "
                              "(Fisher-z, sample-weighted). Select a country to see "
                              "its own correlations.",
                              className="text-muted d-block mb-2"),
                   _loading(dcc.Graph(id="lag-correlation-chart",
                             config={"displayModeBar": False})),
                   html.Div(id="lag-limitations", className="small text-muted mt-2")]),
            _card("Q1 · Correlation detail by substance",
                  [dbc.Row([
                      dbc.Col(dcc.Dropdown(id="x-axis", clearable=False,
                              value="Kilograms", className="small",
                              options=[{"label": "Kilograms seized", "value": "Kilograms"},
                                       {"label": "Price (USD/g)", "value": "Typical_USD"},
                                       {"label": "Purity (%)", "value": "Typical"}]), md=6),
                      dbc.Col(dcc.Dropdown(id="y-axis", clearable=False,
                              value="Typical_USD", className="small",
                              options=[{"label": "Price (USD/g)", "value": "Typical_USD"},
                                       {"label": "Purity (%)", "value": "Typical"},
                                       {"label": "Kilograms seized", "value": "Kilograms"}]), md=6),
                  ], className="mb-2"),
                   _loading(dcc.Graph(id="regression-chart")),
                   html.Div(id="regression-stats", className="mt-2 small text-muted")]),
        ], className="mb-4"),

        # Row: Q2 heatmaps
        dbc.Row([
            _card("Q2 · Retail prices by region & substance",
                  _graph("heatmap-retail", "Click a cell to filter by region & substance")),
            _card("Q2 · Wholesale prices by region & substance",
                  _graph("heatmap-wholesale", "Click a cell to filter by region & substance")),
        ], className="mb-4"),

        # Row: Q2 margin map + Q3 arbitrage map
        dbc.Row([
            _card("Q2 · Highest retail–wholesale markup by country",
                  _graph("margin-map", "Click a country to filter")),
            _card("Q3 · Cross-border price-arbitrage exposure",
                  [dbc.Row([
                      dbc.Col([html.Label("Reference country:", className="fw-bold small"),
                               dcc.Dropdown(id="arb-country", clearable=False,
                                   className="small mb-2",
                                   options=[{"label": c, "value": c} for c in data.countries],
                                   value=data.countries[0])], md=4),
                      dbc.Col([html.Label("Substance:", className="fw-bold small"),
                               dcc.Dropdown(id="arb-substance", clearable=False,
                                   className="small mb-2",
                                   options=[{"label": s, "value": s} for s in substances],
                                   value=substances[0])], md=4),
                      dbc.Col([html.Label("Level:", className="fw-bold small"),
                               dcc.Dropdown(id="arb-level", clearable=False,
                                   className="small mb-2",
                                   options=[{"label": "Retail", "value": "Retail"},
                                            {"label": "Wholesale", "value": "Wholesale"}],
                                   value="Retail")], md=4),
                  ]),
                   html.Small("Δ price vs the reference country signals where a "
                              "displaced market could be more profitable — a "
                              "spillover-risk indicator, not a selling guide.",
                              className="text-muted d-block mb-1"),
                   _loading(dcc.Graph(id="arbitrage-map"))]),
        ], className="mb-4"),

        # Row: single-country border arbitrage (appears when one country picked)
        dbc.Row([
            _card("Q3 · Where to focus border control: best cross-border "
                  "wholesale→retail arbitrage",
                  [html.Small("Select a single country on the map. For each land "
                              "neighbour and substance this shows the more "
                              "profitable smuggling play — import (buy wholesale "
                              "next door, sell retail here) or export (vice "
                              "versa). Longer bars = stronger smuggling incentive "
                              "at that border.",
                              className="text-muted d-block mb-1"),
                   _loading(dcc.Graph(id="border-arbitrage-chart")),
                   html.Div(id="border-arbitrage-gaps", className="mt-2")], md=8),
            _card("Selected country & neighbours",
                  _graph("neighbour-map", displaymodebar=False), md=4),
        ], className="mb-4"),

        # Row: Q4 priority dotplot + scatter
        dbc.Row([
            _card("Q4 · Market profitability / enforcement-priority index",
                  [html.Small("Composite: 40% retail–wholesale markup + 30% retail "
                              "price + 30% inverse seizure pressure. Top substance "
                              "shown per country.", className="text-muted d-block mb-1"),
                   _loading(dcc.Graph(id="priority-chart", config={"displayModeBar": False}))],
                  md=12),
        ], className="mb-4"),

        *make_stores(),

        dbc.Row(dbc.Col([
            html.Hr(),
            html.P("Data: UNODC World Drug Report 2019–2023 · "
                   "Built with Dash/Plotly · Colourblind-safe palettes throughout",
                   className="text-center text-muted small"),
        ])),
    ], fluid=True, style={"backgroundColor": "#f8f9fa"})
