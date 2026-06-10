import dash_bootstrap_components as dbc
from dash import dcc, html

from .components.stores import make_stores
from .figures.maps import enforcement_map


def loading(component):
    return dcc.Loading(component, type="default", color="#495057")


def make_graph(graph_id, hint=None, displaymodebar=True, figure=None, with_loading=True):
    children = []
    if hint:
        children.append(html.Small(hint, className="text-muted d-block mb-1"))
    graph_kwargs = {"id": graph_id, "config": {"displayModeBar": displaymodebar}}
    # seed an initial figure so a Patch callback has something to patch
    if figure is not None:
        graph_kwargs["figure"] = figure
    g = dcc.Graph(**graph_kwargs)
    # skip the spinner overlay for the map so it doesn't flash on every click
    children.append(loading(g) if with_loading else g)
    return children


def card(title, body, md=6, className="detail-card", id=None):
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
        # sticky selection hub on the left, tabbed charts on the right
        dbc.Row([
            # master panel (left, sticky)
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
                            "using prices, purity & seizures, 2019-2023 (UNODC)",
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
                    # hidden but the selection callback still writes to it
                    html.Span(id="brushing-info", style={"display": "none"}),
                    html.H6("Year range", className="master-heading"),
                    # two dropdowns instead of a range slider so single years work too
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
                    *make_graph("enforcement-map",
                                figure=enforcement_map(data, {}), with_loading=False),
                    html.H6("Substances", className="master-heading mt-3"),
                    html.Div(id="substance-legend",
                             className="d-flex flex-wrap mb-2"),
                    # total-seizures indicator
                    loading(html.Div(id="kpi-panel", className="mt-3")),
                ]),
            ], id="master-card"), id="master-col", md=4,
                style={"position": "sticky", "top": "1rem",
                       "alignSelf": "flex-start", "transition": "all 0.3s ease",
                       # Match the detail tab bar's 1rem top padding so the
                       # master card aligns with the detail section's tabs.
                       "paddingTop": "1rem"}),

            # detail panels (right) - all stay mounted, visibility toggled in callbacks/tabs.py
            dbc.Col(id="detail-col", md=8, style={"transition": "all 0.3s ease"}, children=[
                html.Div([
                    dbc.Button("❯", id="sidebar-show-btn", color="secondary", size="sm", 
                               outline=True, className="me-3 align-self-start mt-2", style={"display": "none"}),
                    html.Div(
                        dbc.Tabs(id="detail-tabs", active_tab="tab-overview",
                                 className="detail-tabs", children=[
                            dbc.Tab(label="Overview", tab_id="tab-overview"),
                            dbc.Tab(label="National", tab_id="tab-national"),
                            dbc.Tab(label="Cross-Border", tab_id="tab-q3"),
                            dbc.Tab(label="Seizure Impact", tab_id="tab-q1"),
                        ]), style={"flexGrow": 1}
                    )
                ], className="mb-3 d-flex align-items-center",
                   # keep the tab bar pinned to the top while content scrolls
                   style={"position": "sticky", "top": 0, "zIndex": 1020,
                          "backgroundColor": "#f8f9fa",
                          "paddingTop": "1rem"}),

                # overview panel: substance bars + time series
                html.Div(id="panel-overview", children=[
                    dbc.Row([
                        dbc.Col(make_graph("ki-seizures-bar", displaymodebar=False),
                                md=4),
                        dbc.Col(make_graph("ki-price-bar", displaymodebar=False),
                                md=4),
                        dbc.Col(make_graph("ki-purity-bar", displaymodebar=False),
                                md=4),
                    ], className="g-2 mb-2"),
                    # hidden for a single year (no trend), toggled in callbacks/figures.py
                    html.Div(id="ts-row", children=dbc.Row([
                        dbc.Col(make_graph("ts-seizures", displaymodebar=False), md=4),
                        dbc.Col(make_graph("ts-price",    displaymodebar=False), md=4),
                        dbc.Col(make_graph("ts-purity",   displaymodebar=False), md=4),
                    ], className="g-2 mb-2")),
                    # same metrics split by subregion
                    dbc.Row([
                        dbc.Col(make_graph("sr-seizures", displaymodebar=False),
                                md=4),
                        dbc.Col(make_graph("sr-price", displaymodebar=False),
                                md=4),
                        dbc.Col(make_graph("sr-purity", displaymodebar=False),
                                md=4),
                    ], className="g-2 mb-2"),
                ]),

                # national panel: metric-over-time map then the markup map
                html.Div(id="panel-national", children=[
                    dbc.Row([
                        card(["Metric by country over time",
                               html.I(className="bi bi-info-circle text-muted "
                                      "ms-1", id="temporal-info",
                                      style={"cursor": "help"}),
                               dbc.Tooltip(
                                   "A chosen metric per country. Price and "
                                   "purity are averaged per country within each "
                                   "year; seizures are summed. Price and purity "
                                   "split into retail (left) vs wholesale "
                                   "(right); seizures show a single total. Playbutton "
                                   "animates the selected year range (latest "
                                   "year shown by default). Grey = no data for "
                                   "the metric/substance/year. Purity is "
                                   "%-measured only (mg/tablet excluded).",
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
                               loading(dcc.Graph(id="temporal-maps"))],
                              md=12),
                    ], className="mb-4"),
                    # markup map below the over-time map
                    dbc.Row([
                        card([" Highest retail-wholesale markup by country ",
                               html.I(className="bi bi-info-circle text-muted "
                                      "ms-1", id="q2-info",
                                      style={"cursor": "help"}),
                               dbc.Tooltip(
                                   "Per country, the substance with the biggest "
                                   "markup - left ranks by relative %, right by "
                                   "absolute $/g. Retail and wholesale prices "
                                   "are averaged per country within each year, "
                                   "then the markup is their spread. Colours "
                                   "match the master-panel substance legend; "
                                   "grey = no data. Playbutton animates the selected "
                                   "year range; latest year shown by default. "
                                   "Click a country to filter.",
                                   target="q2-info", placement="bottom")],
                              [html.Div(id="margin-highlights",
                                        className="mb-3"),
                               *make_graph("margin-map")],
                              md=12),
                    ], className="mb-4"),
                ]),

                # seizures -> market panel, two stacked cards
                html.Div(id="panel-q1", children=[
                    dbc.Row([
                        card([" Do seizures move the market? "
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
                              [loading(dcc.Graph(id="lag-correlation-chart",
                                        config={"displayModeBar": False})),
                               html.Div(id="lag-limitations",
                                        className="small text-muted mt-2")],
                              md=12),
                    ], className="mb-3"),
                    dbc.Row([
                        card(" Correlation detail by substance",
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
                               loading(dcc.Graph(id="regression-chart")),
                               html.Div(id="regression-stats",
                                        className="mt-2 small text-muted")],
                              md=12),
                    ], className="mb-4"),
                ]),

                # cross-border spillover panel
                html.Div(id="panel-q3", children=[
                    dbc.Row([
                        card([
                            " Where to focus border control: best "
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
                              [# priority gaps at the top of the body
                               html.Div(id="border-arbitrage-gaps",
                                        className="mb-3"),
                               html.Div(loading(dcc.Graph(id="market-flow-map")),
                                        id="q3-flow-wrap",
                                        style={"display": "none"}),
                               # single-year snapshot picker, bounds track the global range
                               html.Div([
                                   html.Label("Year", className="small "
                                              "text-muted mb-1"),
                                   dcc.Slider(id="q3-year", step=None,
                                              included=False,
                                              tooltip={"placement": "bottom"}),
                               ], id="q3-year-wrap", className="mb-3"),
                               loading(dcc.Graph(id="border-arbitrage-chart"))],
                              md=8, id="q3-chart-col"),
                        card("Selected country & neighbours",
                             make_graph("neighbour-map", displaymodebar=False),
                             md=4, id="q3-neighbour-col"),
                    ], className="mb-4"),
                ]),
            ]),
        ], className="g-3 mb-4"),

        *make_stores(),

        # fixed attribution bar at the bottom
        html.Div(
            html.P("Data: UNODC World Drug Report 2019-2023 "
                   "Built with Dash/Plotly Palettes: Paul Tol Muted "
                   "(categorical), Viridis (sequential)",
                   className="text-center text-muted small mb-0"),
            style={"position": "fixed", "bottom": 0, "left": 0, "right": 0,
                   "zIndex": 1030, "backgroundColor": "#f8f9fa",
                   "borderTop": "1px solid #dee2e6",
                   "padding": "0.4rem 1rem"}),
    ], fluid=True, style={"backgroundColor": "#f8f9fa",
                          "paddingBottom": "2.5rem"})
