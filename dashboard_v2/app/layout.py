"""App layout assembly. Reframed throughout to a law-enforcement / policy voice
(research questions from the proposal drive each panel).
"""
import dash_bootstrap_components as dbc
from dash import dcc, html

from .components.stores import make_stores


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


def _card(title, body, md=6, className="detail-card"):
    return dbc.Col(dbc.Card([
        dbc.CardHeader(html.H5(title, className="mb-0")),
        dbc.CardBody(body),
    ], className=className), md=md)


def build_layout(data):
    substances = data.substances
    years = list(range(data.year_min, data.year_max + 1))

    return dbc.Container([
        # Master–detail body: a sticky selection hub on the left, the
        # research-question-tabbed analytical charts on the right.
        dbc.Row([
            # ---- MASTER (left, sticky): the selection hub ----
            dbc.Col(dbc.Card([
                dbc.CardHeader(dbc.Row([
                    dbc.Col([
                        html.H5("European Drug-Market Intelligence",
                                className="mb-0 d-inline-block me-2"),
                        html.Span("ⓘ", id="title-info",
                                  className="text-muted",
                                  style={"cursor": "help"}),
                        dbc.Tooltip(
                            "An evidence base for enforcement prioritisation "
                            "using prices, purity & seizures, 2019–2023 (UNODC)",
                            target="title-info"),
                    ], width="auto", className="d-flex align-items-center"),
                    dbc.Col(dbc.Button("Reset selection", id="reset-button",
                                       color="danger", size="sm"),
                            width="auto", className="d-flex align-items-center"),
                ], className="g-2 justify-content-between flex-nowrap")),
                dbc.CardBody([
                    html.Div([
                        html.Strong("Linked selection: ", className="me-1"),
                        html.Span(id="brushing-info",
                                  children="Click any chart to filter the rest."),
                    ], className="text-muted small mb-3"),
                    html.H6("Year range", className="master-heading"),
                    dcc.RangeSlider(id="year-slider", min=data.year_min,
                                    max=data.year_max,
                                    value=[data.year_min, data.year_max],
                                    marks={y: str(y) for y in years}, step=1,
                                    className="mb-3"),
                    html.Div([
                        html.H6("Regions & countries",
                                className="master-heading mb-0"),
                        html.Span(id="country-count",
                                  className="text-muted small"),
                    ], className="d-flex justify-content-between "
                                 "align-items-baseline mt-3 mb-1"),
                    *_graph("enforcement-map"),
                    html.H6("Substances", className="master-heading mt-3"),
                    html.Div(id="substance-legend",
                             className="d-flex flex-wrap mb-2"),
                    # Total-seizures indicator (relocated from the Overview tab).
                    _loading(html.Div(id="kpi-panel", className="mt-3")),
                ]),
            ]), md=4,
                style={"position": "sticky", "top": "1rem",
                       "alignSelf": "flex-start"}),

            # ---- DETAIL (right): research-question tabs ----
            # The tab bar is only a selector; every panel below stays mounted so
            # the single figures mega-callback (writes all graphs at once) and
            # the brushing callbacks keep working. Visibility is toggled in
            # callbacks/tabs.py via each panel's `style`.
            dbc.Col([
                html.Div(
                    dbc.Tabs(id="detail-tabs", active_tab="tab-overview",
                             className="detail-tabs", children=[
                        dbc.Tab(label="Overview", tab_id="tab-overview"),
                        dbc.Tab(label="Seizure Impact", tab_id="tab-q1"),
                        dbc.Tab(label="Profitability", tab_id="tab-q2"),
                        dbc.Tab(label="Cross-Border", tab_id="tab-q3"),
                        dbc.Tab(label="Enforcement Priority", tab_id="tab-q45"),
                    ]),
                    className="mb-3",
                    # Keep the tab bar in view while the panel content scrolls.
                    # Stick flush to the viewport top (top:0) with an opaque
                    # background and top padding, so no panel content can scroll
                    # into view above the tabs. The 1rem padding visually keeps
                    # the tabs aligned with the sticky master panel's top.
                    style={"position": "sticky", "top": 0, "zIndex": 1020,
                           "backgroundColor": "#f8f9fa",
                           "paddingTop": "1rem"}),

                # --- Panel Overview: KPI chips, substance bars, time series ---
                html.Div(id="panel-overview", children=[
                    dbc.Row([
                        dbc.Col(_graph("ki-seizures-bar", displaymodebar=False),
                                md=4),
                        dbc.Col(_graph("ki-price-bar", displaymodebar=False),
                                md=4),
                        dbc.Col(_graph("ki-purity-bar", displaymodebar=False),
                                md=4),
                    ], className="g-2 mb-4"),
                    dbc.Row([
                        _card("Trends over time",
                              _graph("timeseries-chart"),
                              md=12),
                    ], className="mb-4"),
                ]),

                # --- Panel Q1: seizures -> market ---
                html.Div(id="panel-q1", children=[
                    dbc.Row([
                        _card("Q1 · Do seizures move the market? "
                              "(within-country, +1yr lag)",
                              [html.Small("Pearson r between seizures in year Y "
                                          "and street price in Y+1, computed per "
                                          "country then aggregated (Fisher-z, "
                                          "sample-weighted). Select a country to "
                                          "see its own correlations.",
                                          className="text-muted d-block mb-2"),
                               _loading(dcc.Graph(id="lag-correlation-chart",
                                         config={"displayModeBar": False})),
                               html.Div(id="lag-limitations",
                                        className="small text-muted mt-2")]),
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
                               html.Div(id="regression-stats",
                                        className="mt-2 small text-muted")]),
                    ], className="mb-4"),
                ]),

                # --- Panel Q2: profitability & markup ---
                html.Div(id="panel-q2", children=[
                    dbc.Row([
                        _card("Q2 · Retail vs wholesale price ladder by region "
                              "& substance",
                              _graph("price-ladder",
                                     "Each rung links wholesale (●) to retail "
                                     "(○); bar length = markup. Click a rung to "
                                     "filter by region & substance."),
                              md=12),
                    ], className="mb-4"),
                    dbc.Row([
                        _card("Q2 · Retail–wholesale markup over time",
                              _graph("margin-trend",
                                     "Relative markup (%) by substance, "
                                     "2019–2023 — is the gap widening or "
                                     "narrowing?"),
                              md=6),
                        _card("§5 · Quality-adjusted price (price ÷ purity) by "
                              "substance",
                              _graph("quality-price",
                                     "Raw $/g vs purity-normalised cost — the "
                                     "'true' price once potency is accounted "
                                     "for."),
                              md=6),
                    ], className="mb-4"),
                    dbc.Row([
                        _card("Q2 · Highest retail–wholesale markup by country",
                              _graph("margin-map", "Click a country to filter"),
                              md=12),
                    ], className="mb-4"),
                ]),

                # --- Panel Q3: cross-border spillover ---
                html.Div(id="panel-q3", children=[
                    dbc.Row([
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
                               html.Small("Δ price vs the reference country "
                                          "signals where a displaced market "
                                          "could be more profitable — a "
                                          "spillover-risk indicator, not a "
                                          "selling guide.",
                                          className="text-muted d-block mb-1"),
                               _loading(dcc.Graph(id="arbitrage-map"))], md=12),
                    ], className="mb-4"),
                    dbc.Row([
                        _card("Q3 · Where to focus border control: best "
                              "cross-border wholesale→retail arbitrage",
                              [html.Small("Select a single country on the map. "
                                          "For each land neighbour and substance "
                                          "this shows the more profitable "
                                          "smuggling play — import (buy wholesale "
                                          "next door, sell retail here) or export "
                                          "(vice versa). Longer bars = stronger "
                                          "smuggling incentive at that border.",
                                          className="text-muted d-block mb-1"),
                               _loading(dcc.Graph(id="border-arbitrage-chart")),
                               html.Div(id="border-arbitrage-gaps",
                                        className="mt-2")], md=8),
                        _card("Selected country & neighbours",
                              _graph("neighbour-map", displaymodebar=False),
                              md=4),
                    ], className="mb-4"),
                ]),

                # --- Panel Q4/Q5: enforcement priority ---
                html.Div(id="panel-q45", children=[
                    dbc.Row([
                        _card("Q4 · Market profitability / enforcement-priority "
                              "index",
                              [html.Small("Composite: 40% retail–wholesale "
                                          "markup + 30% retail price + 30% "
                                          "inverse seizure pressure. Top "
                                          "substance shown per country.",
                                          className="text-muted d-block mb-1"),
                               _loading(dcc.Graph(id="priority-chart",
                                         config={"displayModeBar": False}))]),
                        _card("Q5 · Enforcement priority by country & substance",
                              _graph("priority-heatmap",
                                     "Darker = higher priority. Click a cell to "
                                     "filter by country & substance.")),
                    ], className="mb-4"),
                ]),
            ], md=8),
        ], className="g-3 mb-4"),

        *make_stores(),

        # Fixed attribution bar, always visible; detail/master content scrolls
        # beneath it (the container's bottom padding keeps content from hiding
        # permanently behind it).
        html.Div(
            html.P("Data: UNODC World Drug Report 2019–2023 · "
                   "Built with Dash/Plotly · Palettes: Paul Tol Muted "
                   "(categorical), Viridis (sequential), RdBu (diverging)",
                   className="text-center text-muted small mb-0"),
            style={"position": "fixed", "bottom": 0, "left": 0, "right": 0,
                   "zIndex": 1030, "backgroundColor": "#f8f9fa",
                   "borderTop": "1px solid #dee2e6",
                   "padding": "0.4rem 1rem"}),
    ], fluid=True, style={"backgroundColor": "#f8f9fa",
                          "paddingBottom": "2.5rem"})
