"""App layout assembly. Reframed throughout to a law-enforcement / policy voice
(research questions from the proposal drive each panel).
"""
import dash_bootstrap_components as dbc
from dash import dcc, html

from .components.stores import make_stores
from .figures.maps import enforcement_map


def _loading(component):
    """Wrap a component in a Dash loading overlay for recompute feedback."""
    return dcc.Loading(component, type="default", color="#495057")


def _graph(graph_id, hint=None, displaymodebar=True, figure=None, loading=True):
    children = []
    if hint:
        children.append(html.Small(hint, className="text-muted d-block mb-1"))
    graph_kwargs = {"id": graph_id, "config": {"displayModeBar": displaymodebar}}
    # Seed an initial figure so a Patch callback has a figure to patch into
    # (the map is drawn once here; clicks only patch its outline trace).
    if figure is not None:
        graph_kwargs["figure"] = figure
    graph = dcc.Graph(**graph_kwargs)
    # loading=False skips the dcc.Loading overlay - used for the enforcement map,
    # whose clicks only Patch the outline trace; the overlay would otherwise
    # flash a spinner over the whole map on every selection.
    children.append(_loading(graph) if loading else graph)
    return children


def _card(title, body, md=6, className="detail-card", id=None):
    col_kwargs = {"md": md}
    if id is not None:
        col_kwargs["id"] = id
    return dbc.Col(dbc.Card([
        dbc.CardHeader(html.H5(title, className="mb-0")),
        dbc.CardBody(body),
    ], className=className), **col_kwargs)


def build_layout(data):
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
                    dbc.Col([
                        dbc.Button("Reset selection", id="reset-button",
                                   color="danger", size="sm", className="me-2"),
                        dbc.Button("❮", id="sidebar-toggle-btn",
                                   color="secondary", size="sm", outline=True, title="Toggle Sidebar")
                    ], width="auto", className="d-flex align-items-center"),
                ], className="g-2 justify-content-between flex-nowrap")),
                dbc.CardBody([
                    # The brushing-info span is still written to by the selection
                    # callback, so it stays in the DOM but is hidden (the visible
                    # "Linked selection: …" hint was removed).
                    html.Span(id="brushing-info", style={"display": "none"}),
                    html.H6("Year range", className="master-heading"),
                    # Two dropdowns (From / To) instead of a RangeSlider: every
                    # combination - including a single year (From == To) - is
                    # selectable, with none of the Dash-4 Radix-slider
                    # thumb-overlap quirks. The figures callback normalises the
                    # pair so order never matters.
                    dbc.Row([
                        dbc.Col([
                            html.Label("From", className="small text-muted mb-1"),
                            dcc.Dropdown(
                                id="year-from", clearable=False,
                                searchable=False,
                                value=data.year_min,
                                options=[{"label": str(y), "value": y}
                                         for y in years]),
                        ], width=6),
                        dbc.Col([
                            html.Label("To", className="small text-muted mb-1"),
                            dcc.Dropdown(
                                id="year-to", clearable=False,
                                searchable=False,
                                value=data.year_max,
                                options=[{"label": str(y), "value": y}
                                         for y in years]),
                        ], width=6),
                    ], className="g-2 mb-3"),
                    html.Div([
                        html.H6("Regions & countries",
                                className="master-heading mb-0"),
                        html.Span(id="country-count",
                                  className="text-muted small"),
                    ], className="d-flex justify-content-between "
                                 "align-items-baseline mt-3 mb-1"),
                    *_graph("enforcement-map",
                            figure=enforcement_map(data, {}), loading=False),
                    html.H6("Substances", className="master-heading mt-3"),
                    html.Div(id="substance-legend",
                             className="d-flex flex-wrap mb-2"),
                    # Total-seizures indicator (relocated from the Overview tab).
                    _loading(html.Div(id="kpi-panel", className="mt-3")),
                ]),
            ], id="master-card"), id="master-col", md=4,
                style={"position": "sticky", "top": "1rem",
                       "alignSelf": "flex-start", "transition": "all 0.3s ease",
                       # Match the detail tab bar's 1rem top padding so the
                       # master card aligns with the detail section's tabs.
                       "paddingTop": "1rem"}),

            # ---- DETAIL (right): research-question tabs ----
            # The tab bar is only a selector; every panel below stays mounted so
            # the single figures mega-callback (writes all graphs at once) and
            # the brushing callbacks keep working. Visibility is toggled in
            # callbacks/tabs.py via each panel's `style`.
            dbc.Col(id="detail-col", md=8, style={"transition": "all 0.3s ease"}, children=[
                html.Div([
                    dbc.Button("❯", id="sidebar-show-btn", color="secondary", size="sm", 
                               outline=True, className="me-3 align-self-start mt-2", style={"display": "none"}),
                    html.Div(
                        dbc.Tabs(id="detail-tabs", active_tab="tab-overview",
                                 className="detail-tabs", children=[
                            dbc.Tab(label="Overview", tab_id="tab-overview"),
                            dbc.Tab(label="Temporal", tab_id="tab-temporal"),
                            dbc.Tab(label="Profitability", tab_id="tab-q2"),
                            dbc.Tab(label="Cross-Border", tab_id="tab-q3"),
                            dbc.Tab(label="Seizure Impact", tab_id="tab-q1"),
                        ]), style={"flexGrow": 1}
                    )
                ], className="mb-3 d-flex align-items-center",
                   # Keep the tab bar in view while the panel content scrolls.
                   # Stick flush to the viewport top (top:0) with an opaque
                   # background and top padding, so no panel content can scroll
                   # into view above the tabs. The 1rem padding visually keeps
                   # the tabs aligned with the sticky master panel's top.
                   style={"position": "sticky", "top": 0, "zIndex": 1020,
                          "backgroundColor": "#f8f9fa",
                          "paddingTop": "1rem"}),

                # --- Panel Overview: substance bars + per-metric time series ---
                html.Div(id="panel-overview", children=[
                    dbc.Row([
                        dbc.Col(_graph("ki-seizures-bar", displaymodebar=False),
                                md=4),
                        dbc.Col(_graph("ki-price-bar", displaymodebar=False),
                                md=4),
                        dbc.Col(_graph("ki-purity-bar", displaymodebar=False),
                                md=4),
                    ], className="g-2 mb-2"),
                    # Hidden when a single year is selected (no trend to draw);
                    # visibility is toggled in callbacks/figures.py.
                    html.Div(id="ts-row", children=dbc.Row([
                        dbc.Col(_graph("ts-seizures", displaymodebar=False), md=4),
                        dbc.Col(_graph("ts-price",    displaymodebar=False), md=4),
                        dbc.Col(_graph("ts-purity",   displaymodebar=False), md=4),
                    ], className="g-2 mb-2")),
                    # Subregion breakdown: the bars/series above aggregate across
                    # all of Europe; these split the same metrics by subregion.
                    # Always shown (they work for a single year too).
                    dbc.Row([
                        dbc.Col(_graph("sr-seizures", displaymodebar=False),
                                md=4),
                        dbc.Col(_graph("sr-price", displaymodebar=False),
                                md=4),
                        dbc.Col(_graph("sr-purity", displaymodebar=False),
                                md=4),
                    ], className="g-2 mb-2"),
                ]),

                # --- Panel Temporal: a metric for one substance, mapped & animated ---
                html.Div(id="panel-temporal", children=[
                    dbc.Row([
                        _card(["Metric by country, over time",
                               html.I(className="bi bi-info-circle text-muted "
                                      "ms-1", id="temporal-info",
                                      style={"cursor": "help"}),
                               dbc.Tooltip(
                                   "A chosen metric per country. Price and "
                                   "purity split into retail (left) vs "
                                   "wholesale (right); seizures show a single "
                                   "total. ▶ animates the selected year range "
                                   "(latest year shown by default). Grey = no "
                                   "data for the metric/substance/year. Purity "
                                   "is %-measured only (mg/tablet excluded).",
                                   target="temporal-info", placement="bottom")],
                              [dbc.Row([
                                   dbc.Col([
                                       html.Label("Metric", className="small "
                                                  "text-muted mb-1"),
                                       dcc.Dropdown(id="temporal-metric",
                                                    clearable=False,
                                                    searchable=False,
                                                    value="purity",
                                                    options=[
                                                        {"label": "Price (USD/g)",
                                                         "value": "price"},
                                                        {"label": "Purity (%)",
                                                         "value": "purity"},
                                                        {"label": "Seizures (t)",
                                                         "value": "seizures"}],
                                                    className="small"),
                                   ], md=6),
                                   dbc.Col([
                                       html.Label("Substance", className="small "
                                                  "text-muted mb-1"),
                                       dcc.Dropdown(id="temporal-substance",
                                                    clearable=False,
                                                    searchable=False,
                                                    className="small"),
                                   ], md=6),
                               ], className="mb-2"),
                               html.Div(id="temporal-highlights",
                                        className="mb-3"),
                               _loading(dcc.Graph(id="temporal-maps"))],
                              md=12),
                    ], className="mb-4"),
                ]),

                # --- Panel Q1: seizures -> market ---
                # The two cards are stacked full-width (one above the other).
                html.Div(id="panel-q1", children=[
                    dbc.Row([
                        _card(["Q1 Do seizures move the market? "
                               "(within-country, +1yr lag) ",
                               html.I(className="bi bi-info-circle text-muted "
                                      "ms-1", id="q1-lag-info",
                                      style={"cursor": "help"}),
                               dbc.Tooltip(
                                   "Pearson r between seizures in year Y and "
                                   "street price in Y+1, computed per country "
                                   "then aggregated (Fisher-z, sample-weighted)."
                                   " Select a country to see its own "
                                   "correlations.",
                                   target="q1-lag-info", placement="bottom")],
                              [_loading(dcc.Graph(id="lag-correlation-chart",
                                         config={"displayModeBar": False})),
                               html.Div(id="lag-limitations",
                                        className="small text-muted mt-2")],
                              md=12),
                    ], className="mb-3"),
                    dbc.Row([
                        _card("Q1 Correlation detail by substance",
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
                                        className="mt-2 small text-muted")],
                              md=12),
                    ], className="mb-4"),
                ]),

                # --- Panel Q2: profitability & markup ---
                html.Div(id="panel-q2", children=[
                    dbc.Row([
                        _card(["Q2 Highest retail–wholesale markup by country ",
                               html.I(className="bi bi-info-circle text-muted "
                                      "ms-1", id="q2-info",
                                      style={"cursor": "help"}),
                               dbc.Tooltip(
                                   "Per country, the substance with the biggest "
                                   "markup - left ranks by relative %, right by "
                                   "absolute $/g. Colours match the master-panel "
                                   "substance legend; grey = no data. ▶ animates "
                                   "the selected year range; latest year shown "
                                   "by default. Click a country to filter.",
                                   target="q2-info", placement="bottom")],
                              [html.Div(id="margin-highlights",
                                        className="mb-3"),
                               *_graph("margin-map")],
                              md=12),
                    ], className="mb-4"),
                ]),

                # --- Panel Q3: cross-border spillover ---
                html.Div(id="panel-q3", children=[
                    dbc.Row([
                        _card([
                            "Q3 Where to focus border control: best "
                            "cross-border wholesale→retail arbitrage ",
                            html.I(className="bi bi-info-circle text-muted ms-1",
                                   id="q3-info", style={"cursor": "help"}),
                            dbc.Tooltip(
                                "Click a single country for its land-border "
                                "arbitrage - per neighbour and substance, the "
                                "more profitable smuggling play (import / "
                                "export). Or select multiple / all countries to "
                                "map the best arbitrage corridor per substance "
                                "(cheapest wholesale → priciest retail) and rank "
                                "the top 25 corridors below. Figures are a "
                                "snapshot of the selected year, not an "
                                "average across the range.",
                                target="q3-info", placement="bottom"),
                        ],
                              [# Priority gaps surfaced at the top of the body.
                               html.Div(id="border-arbitrage-gaps",
                                        className="mb-3"),
                               html.Div(_loading(dcc.Graph(id="market-flow-map")),
                                        id="q3-flow-wrap",
                                        style={"display": "none"}),
                               # Year picker: the arbitrage prices/seizures are
                               # a snapshot of this single year (not averaged
                               # across the range). Bounds track the global
                               # From/To range (see _q3_year_bounds in
                               # callbacks/figures.py). Shown in both modes,
                               # sat below the per-substance flow map.
                               html.Div([
                                   html.Label("Year", className="small "
                                              "text-muted mb-1"),
                                   dcc.Slider(id="q3-year", step=None,
                                              included=False,
                                              tooltip={"placement": "bottom"}),
                               ], id="q3-year-wrap", className="mb-3"),
                               _loading(dcc.Graph(id="border-arbitrage-chart"))],
                              md=8, id="q3-chart-col"),
                        _card("Selected country & neighbours",
                              _graph("neighbour-map", displaymodebar=False),
                              md=4, id="q3-neighbour-col"),
                    ], className="mb-4"),
                ]),
            ]),
        ], className="g-3 mb-4"),

        *make_stores(),

        # Fixed attribution bar, always visible; detail/master content scrolls
        # beneath it (the container's bottom padding keeps content from hiding
        # permanently behind it).
        html.Div(
            html.P("Data: UNODC World Drug Report 2019–2023 "
                   "Built with Dash/Plotly Palettes: Paul Tol Muted "
                   "(categorical), Viridis (sequential)",
                   className="text-center text-muted small mb-0"),
            style={"position": "fixed", "bottom": 0, "left": 0, "right": 0,
                   "zIndex": 1030, "backgroundColor": "#f8f9fa",
                   "borderTop": "1px solid #dee2e6",
                   "padding": "0.4rem 1rem"}),
    ], fluid=True, style={"backgroundColor": "#f8f9fa",
                          "paddingBottom": "2.5rem"})
