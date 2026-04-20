# dashboard_app.py
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import geopandas as gpd
import requests
from datetime import datetime

# ============================================================================
# STATE-OF-THE-ART COLORBLIND-FRIENDLY COLOR CONFIGURATION
# ============================================================================

# Paul Tol's colorblind-friendly palette (scientifically designed)
PAUL_TOL_BRIGHT = [
    '#4477AA',  # Blue
    '#EE6677',  # Red
    '#228833',  # Green
    '#CCBB44',  # Yellow
    '#66CCEE',  # Cyan
    '#AA3377',  # Purple
    '#BBBBBB'   # Grey
]

PAUL_TOL_MUTED = [
    '#332288',  # Indigo
    '#88CCEE',  # Cyan
    '#44AA99',  # Teal
    '#117733',  # Green
    '#999933',  # Olive
    '#DDCC77',  # Sand
    '#CC6677',  # Rose
    '#882255',  # Wine
    '#AA4499',  # Purple
    '#DDDDDD'   # Grey
]

IBM_COLORBLIND_SAFE = [
    '#648FFF',  # Blue
    '#785EF0',  # Purple
    '#DC267F',  # Magenta
    '#FE6100',  # Orange
    '#FFB000',  # Gold
    '#06D6A0',  # Teal
    '#118AB2',  # Blue-green
    '#073B4C'   # Dark blue
]

WONG_PALETTE = [
    '#E69F00',  # Orange
    '#56B4E9',  # Sky Blue
    '#009E73',  # Bluish Green
    '#F0E442',  # Yellow
    '#0072B2',  # Blue
    '#D55E00',  # Vermillion
    '#CC79A7',  # Reddish Purple
    '#000000'   # Black
]

OKABE_ITO_PALETTE = [
    '#E69F00',  # Orange
    '#56B4E9',  # Sky Blue
    '#009E73',  # Bluish Green
    '#F0E442',  # Yellow
    '#0072B2',  # Blue
    '#D55E00',  # Vermillion
    '#CC79A7',  # Reddish Purple
    '#999999'   # Grey
]

PRIMARY_PALETTE = PAUL_TOL_MUTED

COLORBLIND_SEQUENTIAL_SCALES = {
    'viridis': 'Viridis',
    'plasma': 'Plasma',
    'cividis': 'Cividis',
    'blues': 'Blues',
    'greens': 'Greens',
    'oranges': 'Oranges',
    'purples': 'Purples',
    'teal': 'Teal',
}

COLORBLIND_CONTINUOUS = 'Viridis'

COLORBLIND_DIVERGING_SCALES = {
    'RdYlBu': 'RdYlBu',
    'BrBG': 'BrBG',
    'PiYG': 'PiYG',
}

# ============================================================================
# CUSTOM COLOR FUNCTIONS
# ============================================================================


def get_contrasting_text_color(background_hex):
    """Calculate contrasting text color (black or white) based on background"""
    hex_color = background_hex.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def get_luminance_component(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lum = get_luminance_component(r)
    g_lum = get_luminance_component(g)
    b_lum = get_luminance_component(b)

    luminance = 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum
    return '#FFFFFF' if luminance < 0.5 else '#000000'


def create_accessible_color_mapping(substances):
    """Create colorblind-friendly color mapping with maximum contrast"""
    unique_substances = sorted(substances)
    color_mapping = {}
    for i, substance in enumerate(unique_substances):
        color_mapping[substance] = PRIMARY_PALETTE[i % len(PRIMARY_PALETTE)]
    return color_mapping


def add_pattern_to_trace(fig, trace_index, pattern_shape=''):
    """Add patterns to traces for additional differentiation"""
    patterns = ['', '/', '\\', 'x', '-', '|', '+', '.']
    if pattern_shape == '':
        pattern_shape = patterns[trace_index % len(patterns)]
    return pattern_shape

# ============================================================================
# DATA LOADING AND PREPROCESSING
# ============================================================================


def load_and_preprocess_data():
    """Load and preprocess all datasets"""

    price_and_purity_excel_file = './data/raw/8.1_Prices_and_purities_of_drugs.xlsx'
    seizures_excel_file = './data/raw/7.1_Drug_seizures_2019-2023.xlsx'

    drug_prices_df = pd.read_excel(
        price_and_purity_excel_file, sheet_name='Prices in USD')
    drug_purity_df = pd.read_excel(
        price_and_purity_excel_file, sheet_name='Purities')
    drug_seizures_df = pd.read_excel(
        seizures_excel_file, sheet_name='Seizures')

    drug_prices_df = drug_prices_df.rename(
        columns={'Country/Territory': 'Country'})
    drug_purity_df = drug_purity_df.rename(
        columns={'Country/Territory': 'Country'})
    drug_seizures_df = drug_seizures_df.rename(
        columns={'Reference year': 'Year'})

    region = 'Europe'
    print(f"Filtering datasets for region: {drug_seizures_df.columns}")
    drug_seizures_df = drug_seizures_df[drug_seizures_df['Region'] == region].reset_index(
        drop=True)
    drug_prices_df = drug_prices_df[drug_prices_df['Region'] == region].reset_index(
        drop=True)
    drug_purity_df = drug_purity_df[drug_purity_df['Region'] == region].reset_index(
        drop=True)

    def rename_countries(x):
        mapping = {
            'Russian Federation': 'Russia',
            'North Macedonia': 'The former Yugoslav Republic of Macedonia',
            'Czechia': 'Czech Republic',
            'Türkiye': 'Turkey'
        }
        return mapping.get(x, x)

    drug_seizures_df['Country'] = drug_seizures_df['Country'].apply(
        rename_countries)
    drug_prices_df['Country'] = drug_prices_df['Country'].apply(
        rename_countries)
    drug_purity_df['Country'] = drug_purity_df['Country'].apply(
        rename_countries)

    def classify_substances(x):
        if x in ['Amphetamine-type stimulants', 'Amphetamine-type stimulants (excluding "ecstasy")', 'ATS']:
            return 'Amphetamines'
        elif x in ['Cannabis-type', 'Cannabis-type drugs', 'Cannabis-type drugs (excluding synthetic cannabinoids)']:
            return 'Cannabis'
        elif x in ['Cocaine-type', 'Cocaine-type drugs']:
            return 'Cocaine'
        elif x in ['Sedatives and Tranquillizers', 'Sedatives and tranquilizers (please specify)', 'Sedatives and tranquillizers']:
            return 'Tranquillizers and Sedatives'
        elif x == '"Ecstasy"-type substances':
            return 'Ecstasy'
        elif x == 'Opioids':
            return 'Opioids'
        elif x == 'Hallucinogens':
            return 'Hallucinogens'
        else:
            return 'Other'

    drug_seizures_df['Substance'] = drug_seizures_df['DrugGroup'].apply(
        classify_substances)
    drug_prices_df['Substance'] = drug_prices_df['DrugGroup'].apply(
        classify_substances)
    drug_purity_df['Substance'] = drug_purity_df['DrugGroup'].apply(
        classify_substances)

    drug_prices_df = drug_prices_df[drug_prices_df['Substance'] != 'Other'].reset_index(
        drop=True)
    drug_purity_df = drug_purity_df[drug_purity_df['Substance'] != 'Other'].reset_index(
        drop=True)
    drug_seizures_df = drug_seizures_df[drug_seizures_df['Substance'] != 'Other'].reset_index(
        drop=True)

    drug_prices_df = unify_prices(drug_prices_df)
    drug_prices_df = unify_unit_names(drug_prices_df)

    drug_prices_df['Spread_USD'] = drug_prices_df['Maximum_USD'] - \
        drug_prices_df['Minimum_USD']
    drug_prices_df['Spread_rel'] = drug_prices_df['Spread_USD'] / \
        drug_prices_df['Typical_USD']

    retail_df = drug_prices_df[drug_prices_df['LevelOfSale'] == 'Retail']
    wholesale_df = drug_prices_df[drug_prices_df['LevelOfSale'] == 'Wholesale']

    retail_prices = retail_df.groupby(['Country', 'Substance'])[
        'Typical_USD'].mean().reset_index()
    wholesale_prices = wholesale_df.groupby(['Country', 'Substance'])[
        'Typical_USD'].mean().reset_index()

    inland_margin = pd.merge(retail_prices, wholesale_prices, on=['Country', 'Substance'],
                             how='inner', suffixes=('_Retail', '_Wholesale'))
    inland_margin['Margin'] = inland_margin['Typical_USD_Retail'] - \
        inland_margin['Typical_USD_Wholesale']
    inland_margin['RelativeMargin'] = (
        inland_margin['Margin'] / inland_margin['Typical_USD_Wholesale']) * 100
    inland_margin = inland_margin.dropna(subset='RelativeMargin')

    url = "https://raw.githubusercontent.com/leakyMirror/map-of-europe/master/GeoJSON/europe.geojson"
    response = requests.get(url)
    europe_gdf = gpd.read_file(response.content)

    return drug_prices_df, drug_purity_df, drug_seizures_df, inland_margin, europe_gdf


def unify_prices(df):
    """Unify price units to standard measurements"""
    import re

    def extract_number_from_unit(unit_str):
        if pd.isna(unit_str):
            return 1
        match = re.search(r'(\d+)', str(unit_str))
        return int(match.group(1)) if match else 1

    res = df.copy()
    price_cols = ['Typical_USD', 'Minimum_USD', 'Maximum_USD']

    res['unit_multiplier'] = res['Unit'].apply(extract_number_from_unit)

    unit_conversion = {
        'Kilograms': 1000, 'Kilogram': 1000,
        'Litres': 1000, 'Litre': 1000,
        'milligram': 1/1000, 'Ounce': 29.5735
    }

    res['conversion_multiplier'] = res['Unit'].map(
        lambda x: unit_conversion.get(str(x), 1))
    total_multiplier = res['unit_multiplier'] * res['conversion_multiplier']

    for col in price_cols:
        if col in res.columns:
            res[col] = res[col] / total_multiplier

    res = res.drop(['unit_multiplier', 'conversion_multiplier'], axis=1)
    return res


def unify_unit_names(df):
    """Standardize unit names"""
    res = df.copy()
    unit_mapping = {
        'Grams': 'Gram', 'Gram': 'Gram', 'Kilograms': 'Gram', 'Kilogram': 'Gram',
        '5 gram': 'Gram', '10 gram': 'Gram', '100 gram': 'Gram', '100 milligram': 'Gram',
        'Millilitres': 'Millilitre', 'Litres': 'Millilitre', 'Millilitre': 'Millilitre',
        'Litre': 'Millilitre', 'Ounce': 'Millilitre',
        'Tablets': 'Piece', 'Tablet': 'Piece', 'Units': 'Piece', 'Unit': 'Piece',
        '1000 tablets': 'Piece', '1000 units': 'Piece', 'Pill': 'Piece', 'Dose': 'Piece',
        '10000 tablets': 'Piece', '100 unit': 'Piece', '10 units': 'Piece',
        'Plasters': 'Piece', 'Mark': 'Piece', 'Stamp': 'Piece',
        'Blotting paper': 'Piece', 'Trip': 'Piece'
    }
    res['Unit'] = res['Unit'].replace(unit_mapping)
    return res

# ============================================================================
# INITIALIZE APP
# ============================================================================


drug_prices_df, drug_purity_df, drug_seizures_df, inland_margin, europe_gdf = load_and_preprocess_data()

all_substances = set(drug_prices_df['Substance'].unique()) | set(
    drug_purity_df['Substance'].unique()) | set(drug_seizures_df['Substance'].unique())
all_substances = all_substances - {'Other'}
SUBSTANCE_COLOR_MAP = create_accessible_color_mapping(all_substances)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "European Drug Analytics Dashboard"

# ============================================================================
# LAYOUT - RESTRUCTURED
# ============================================================================

app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🌍 European Drug Analytics Dashboard",
                    className="text-center text-primary mb-2"),
            html.H5("Interactive Analysis of Drug Prices, Purity, and Seizures (2019-2023)",
                    className="text-center text-muted mb-4"),
            html.Hr()
        ])
    ]),

    # Accessibility Notice
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.I(className="bi bi-universal-access me-2"),
                html.Strong("Accessibility: "),
                "This dashboard uses colorblind-friendly palettes (Paul Tol's Muted scheme) ensuring accessibility for all users."
            ], color="success", className="mb-3", dismissable=True)
        ])
    ]),

    # Filters Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("🎛️ Global Filters", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Substances:",
                                       className="fw-bold"),
                            dcc.Dropdown(
                                id='substance-filter',
                                options=[{'label': s, 'value': s} for s in sorted(
                                    drug_prices_df['Substance'].unique())],
                                value=list(
                                    drug_prices_df['Substance'].unique()),
                                multi=True,
                                placeholder="Select substances..."
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Select Year Range:",
                                       className="fw-bold"),
                            dcc.RangeSlider(
                                id='year-slider',
                                min=int(drug_prices_df['Year'].min()),
                                max=int(drug_prices_df['Year'].max()),
                                value=[int(drug_prices_df['Year'].min()), int(
                                    drug_prices_df['Year'].max())],
                                marks={year: str(year) for year in range(
                                    int(drug_prices_df['Year'].min()),
                                    int(drug_prices_df['Year'].max()) + 1
                                )},
                                step=1
                            )
                        ], md=6)
                    ])
                ])
            ], className="mb-4")
        ])
    ]),

    # Brushing & Linking Info Panel
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.Strong("🔗 Brushing & Linking Active: "),
                html.Span(
                    id='brushing-info', children="Click on a subregion in the map or a point in the time series to filter other views."),
                html.Br(),
                dbc.Button("Reset Selection", id='reset-button',
                           color="danger", size="sm", className="mt-2")
            ], color="info", className="mb-3")
        ])
    ]),

    # ========================================================================
    # ROW 1: SUBREGION MAP + TIME SERIES WITH METRIC SELECTOR
    # ========================================================================
    dbc.Row([
        # Subregion Map (colored by subregion)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H5("🗺️ European Subregions", className="mb-0")),
                dbc.CardBody([
                    html.Div([
                        html.Small(
                            "💡 Click on a subregion to filter all other visualizations", className="text-muted")
                    ]),
                    dcc.Graph(id='subregion-map',
                              config={'displayModeBar': True})
                ])
            ])
        ], md=6),

        # Time Series with Metric Selector
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col(html.H5("📈 Time Series Analysis",
                                className="mb-0"), md=6),
                        dbc.Col([
                            dcc.Dropdown(
                                id='timeseries-metric-selector',
                                options=[
                                    {'label': 'Seizures (Tons)',
                                     'value': 'seizures'},
                                    {'label': 'Average Price (USD)',
                                     'value': 'price'},
                                    {'label': 'Average Purity (%)',
                                     'value': 'purity'}
                                ],
                                value='seizures',
                                clearable=False,
                                className="small"
                            )
                        ], md=6)
                    ])
                ]),
                dbc.CardBody([
                    html.Div([
                        html.Small(
                            "💡 Click on a data point to filter by year", className="text-muted")
                    ]),
                    dcc.Graph(id='timeseries-chart',
                              config={'displayModeBar': True})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 2: RETAIL AND WHOLESALE PRICE HEATMAPS
    # ========================================================================
    dbc.Row([
        # Retail Price Heatmap
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H5("💰 Retail Prices by Region & Substance", className="mb-0")),
                dbc.CardBody([
                    html.Div([
                        html.Small(
                            "💡 Click on a cell to filter by region and substance", className="text-muted")
                    ]),
                    dcc.Graph(id='price-heatmap-retail',
                              config={'displayModeBar': True})
                ])
            ])
        ], md=6),

        # Wholesale Price Heatmap
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H5("💰 Wholesale Prices by Region & Substance", className="mb-0")),
                dbc.CardBody([
                    html.Div([
                        html.Small(
                            "💡 Click on a cell to filter by region and substance", className="text-muted")
                    ]),
                    dcc.Graph(id='price-heatmap-wholesale',
                              config={'displayModeBar': True})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 3: MARGIN MAP + OPTIMAL SEIZURE LOCATION MAP
    # ========================================================================
    dbc.Row([
        # Margin Map (original from row 1)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H5("📊 Highest Profit Margins by Country", className="mb-0")),
                dbc.CardBody([
                    html.Div([
                        html.Small(
                            "💡 Shows substance with highest margin per country", className="text-muted")
                    ]),
                    dcc.Graph(id='margin-map', config={'displayModeBar': True})
                ])
            ])
        ], md=6),

        # Optimal Seizure Location Map (NEW)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col(html.H5("🎯 Optimal Seizure Locations",
                                className="mb-0"), md=12),
                    ])
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Country:",
                                       className="fw-bold small"),
                            dcc.Dropdown(
                                id='optimal-country-selector',
                                options=[{'label': c, 'value': c} for c in sorted(
                                    drug_prices_df['Country'].unique())],
                                value=sorted(drug_prices_df['Country'].unique())[
                                    0] if len(drug_prices_df) > 0 else None,
                                clearable=False,
                                className="small mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Select Substance:",
                                       className="fw-bold small"),
                            dcc.Dropdown(
                                id='optimal-substance-selector',
                                options=[{'label': s, 'value': s} for s in sorted(
                                    drug_seizures_df['Substance'].unique())],
                                value=sorted(drug_seizures_df['Substance'].unique())[
                                    0] if len(drug_seizures_df) > 0 else None,
                                clearable=False,
                                className="small mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Price Type:",
                                       className="fw-bold small"),
                            dcc.Dropdown(
                                id='optimal-price-type-selector',
                                options=[
                                    {'label': 'Retail', 'value': 'Retail'},
                                    {'label': 'Wholesale', 'value': 'Wholesale'}
                                ],
                                value='Retail',
                                clearable=False,
                                className="small mb-2"
                            )
                        ], md=4)
                    ]),
                    html.Div([
                        html.Small(
                            "💡 Gradient shows where seizures would have highest value based on price differences", className="text-muted")
                    ]),
                    dcc.Graph(id='optimal-selling-map',
                              config={'displayModeBar': True})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 4: CORRELATION ANALYSIS
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("🔗 Correlation Analysis with Regression",
                            className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("X-Axis:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='x-axis-dropdown',
                                options=[
                                    {'label': 'Price (USD)',
                                     'value': 'Typical_USD'},
                                    {'label': 'Purity (%)',
                                     'value': 'Typical'},
                                    {'label': 'Kilograms Seized',
                                        'value': 'Kilograms'}
                                ],
                                value='Typical_USD',
                                clearable=False
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Y-Axis:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='y-axis-dropdown',
                                options=[
                                    {'label': 'Price (USD)',
                                     'value': 'Typical_USD'},
                                    {'label': 'Purity (%)',
                                     'value': 'Typical'},
                                    {'label': 'Kilograms Seized',
                                        'value': 'Kilograms'}
                                ],
                                value='Typical',
                                clearable=False
                            )
                        ], md=6)
                    ], className="mb-3"),
                    dcc.Graph(id='correlation-regression',
                              config={'displayModeBar': True}),
                    html.Div(id='correlation-stats',
                             className="mt-2 small text-muted")
                ])
            ])
        ], md=12)
    ], className="mb-4"),

    # ========================================================================
    # ROW 5: SCATTER PLOT MATRIX
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H5("🔍 Multi-Variable Scatter Plot Matrix", className="mb-0")),
                dbc.CardBody([
                    html.Div([
                        html.Small(
                            "💡 Click and drag to select points and filter other views", className="text-muted")
                    ]),
                    dcc.Graph(id='correlation-scatter',
                              config={'displayModeBar': True})
                ])
            ])
        ], md=12)
    ], className="mb-4"),

    # Statistics Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("📊 Key Statistics", className="mb-0")),
                dbc.CardBody([
                    html.Div(id='statistics-panel')
                ])
            ])
        ])
    ], className="mb-4"),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P([
                f"Dashboard generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ",
                html.Strong("Color Palette: "),
                "Paul Tol's Muted (Colorblind-Safe)"
            ], className="text-center text-muted small")
        ])
    ])

], fluid=True, style={'backgroundColor': '#f8f9fa'})

# ============================================================================
# CALLBACKS FOR INTERACTIVITY WITH BRUSHING & LINKING
# ============================================================================


@app.callback(
    [Output('subregion-map', 'figure'),
     Output('timeseries-chart', 'figure'),
     Output('price-heatmap-retail', 'figure'),
     Output('price-heatmap-wholesale', 'figure'),
     Output('margin-map', 'figure'),
     Output('optimal-selling-map', 'figure'),
     Output('correlation-regression', 'figure'),
     Output('correlation-stats', 'children'),
     Output('correlation-scatter', 'figure'),
     Output('statistics-panel', 'children'),
     Output('brushing-info', 'children')],
    [Input('substance-filter', 'value'),
     Input('year-slider', 'value'),
     Input('timeseries-metric-selector', 'value'),
     Input('optimal-country-selector', 'value'),
     Input('optimal-substance-selector', 'value'),
     Input('optimal-price-type-selector', 'value'),
     Input('x-axis-dropdown', 'value'),
     Input('y-axis-dropdown', 'value'),
     Input('subregion-map', 'clickData'),
     Input('timeseries-chart', 'clickData'),
     Input('price-heatmap-retail', 'clickData'),
     Input('price-heatmap-wholesale', 'clickData'),
     Input('margin-map', 'clickData'),
     Input('correlation-scatter', 'selectedData'),
     Input('reset-button', 'n_clicks')]
)
def update_dashboard(selected_substances, year_range, timeseries_metric,
                     optimal_country, optimal_substance, optimal_price_type, x_axis, y_axis,
                     subregion_click, timeseries_click, heatmap_retail_click,
                     heatmap_wholesale_click, margin_click, scatter_selection, reset_clicks):
    """Main callback for brushing & linking between all visualizations"""

    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split(
        '.')[0] if ctx.triggered else None

    # Initialize brushing state
    selected_country = None
    selected_year = None
    selected_substance_brush = None
    selected_region = None
    selected_subregion = None
    selected_countries_scatter = None
    brushing_info_text = "No selection active. Click on any visualization to filter others."

    # Reset button clicked
    if triggered_id == 'reset-button':
        subregion_click = None
        timeseries_click = None
        heatmap_retail_click = None
        heatmap_wholesale_click = None
        margin_click = None
        scatter_selection = None
        brushing_info_text = "Selection cleared. Click on any visualization to filter others."

    # Handle subregion map click - FILTER BY SUBREGION ONLY
    elif subregion_click and triggered_id == 'subregion-map':
        try:
            if 'customdata' in subregion_click['points'][0]:
                selected_subregion = subregion_click['points'][0]['customdata'][0]
                brushing_info_text = f"🗺️ Subregion selected: {selected_subregion}. All views filtered by this subregion."
        except (KeyError, IndexError, TypeError):
            pass

    # Handle margin map click
    elif margin_click and triggered_id == 'margin-map':
        try:
            if 'hovertext' in margin_click['points'][0]:
                selected_country = margin_click['points'][0]['hovertext']
            elif 'location' in margin_click['points'][0]:
                location_idx = margin_click['points'][0]['location']
                selected_country = europe_gdf.iloc[location_idx]['NAME']

            if selected_country:
                brushing_info_text = f"📊 Country selected from margin map: {selected_country}. All views filtered."
        except (KeyError, IndexError, TypeError):
            pass

    # Handle time series click
    elif timeseries_click and triggered_id == 'timeseries-chart':
        try:
            selected_year = timeseries_click['points'][0].get('x')
            if 'legendgroup' in timeseries_click['points'][0]:
                selected_substance_brush = timeseries_click['points'][0]['legendgroup']

            brushing_info_text = f"📈 Year {selected_year} selected"
            if selected_substance_brush:
                brushing_info_text += f" for {selected_substance_brush}"
            brushing_info_text += ". All views filtered accordingly."
        except (KeyError, IndexError, TypeError):
            pass

    # Handle heatmap click
    elif (heatmap_retail_click and triggered_id == 'price-heatmap-retail') or \
         (heatmap_wholesale_click and triggered_id == 'price-heatmap-wholesale'):
        try:
            click_data = heatmap_retail_click if triggered_id == 'price-heatmap-retail' else heatmap_wholesale_click
            selected_region = click_data['points'][0].get('y')
            selected_substance_brush = click_data['points'][0].get('x')
            if selected_region and selected_substance_brush:
                price_type = "Retail" if triggered_id == 'price-heatmap-retail' else "Wholesale"
                brushing_info_text = f"💰 {price_type} - Region: {selected_region}, Substance: {selected_substance_brush} selected."
        except (KeyError, IndexError, TypeError):
            pass

    # Handle scatter plot selection
    elif scatter_selection and triggered_id == 'correlation-scatter':
        try:
            if 'points' in scatter_selection and len(scatter_selection['points']) > 0:
                selected_countries_scatter = []
                for point in scatter_selection['points']:
                    if 'customdata' in point and len(point['customdata']) > 0:
                        selected_countries_scatter.append(
                            point['customdata'][0])

                if selected_countries_scatter:
                    selected_countries_scatter = list(
                        set(selected_countries_scatter))
                    brushing_info_text = f"🔍 {len(selected_countries_scatter)} countries selected from scatter plot."
        except (KeyError, IndexError, TypeError):
            pass

    # ========================================================================
    # APPLY GLOBAL FILTERS
    # ========================================================================
    filtered_prices = drug_prices_df[
        (drug_prices_df['Substance'].isin(selected_substances)) &
        (drug_prices_df['Substance'] != 'Other') &
        (drug_prices_df['Year'] >= year_range[0]) &
        (drug_prices_df['Year'] <= year_range[1])
    ].copy()

    filtered_purity = drug_purity_df[
        (drug_purity_df['Substance'].isin(selected_substances)) &
        (drug_purity_df['Substance'] != 'Other') &
        (drug_purity_df['Year'] >= year_range[0]) &
        (drug_purity_df['Year'] <= year_range[1])
    ].copy()

    filtered_seizures = drug_seizures_df[
        (drug_seizures_df['Substance'].isin(selected_substances)) &
        (drug_seizures_df['Substance'] != 'Other') &
        (drug_seizures_df['Year'] >= year_range[0]) &
        (drug_seizures_df['Year'] <= year_range[1])
    ].copy()

    # ========================================================================
    # APPLY BRUSHING FILTERS (LINKING)
    # ========================================================================

    # Filter by subregion if selected
    if selected_subregion:
        filtered_prices = filtered_prices[filtered_prices['SubRegion']
                                          == selected_subregion]
        filtered_purity = filtered_purity[filtered_purity['SubRegion']
                                          == selected_subregion]
        filtered_seizures = filtered_seizures[filtered_seizures['SubRegion']
                                              == selected_subregion]

    if selected_country:
        filtered_prices = filtered_prices[filtered_prices['Country']
                                          == selected_country]
        filtered_purity = filtered_purity[filtered_purity['Country']
                                          == selected_country]
        filtered_seizures = filtered_seizures[filtered_seizures['Country']
                                              == selected_country]

    if selected_year:
        filtered_prices = filtered_prices[filtered_prices['Year']
                                          == selected_year]
        filtered_purity = filtered_purity[filtered_purity['Year']
                                          == selected_year]
        filtered_seizures = filtered_seizures[filtered_seizures['Year']
                                              == selected_year]

    if selected_substance_brush:
        filtered_prices = filtered_prices[filtered_prices['Substance']
                                          == selected_substance_brush]
        filtered_purity = filtered_purity[filtered_purity['Substance']
                                          == selected_substance_brush]
        filtered_seizures = filtered_seizures[filtered_seizures['Substance']
                                              == selected_substance_brush]

    if selected_region:
        region_filter = selected_region if ' Europe' in selected_region else f"{selected_region} Europe"
        filtered_prices = filtered_prices[filtered_prices['SubRegion']
                                          == region_filter]
        filtered_purity = filtered_purity[filtered_purity['SubRegion']
                                          == region_filter]
        filtered_seizures = filtered_seizures[filtered_seizures['SubRegion']
                                              == region_filter]

    if selected_countries_scatter:
        filtered_prices = filtered_prices[filtered_prices['Country'].isin(
            selected_countries_scatter)]
        filtered_purity = filtered_purity[filtered_purity['Country'].isin(
            selected_countries_scatter)]
        filtered_seizures = filtered_seizures[filtered_seizures['Country'].isin(
            selected_countries_scatter)]

    # ========================================================================
    # 1. SUBREGION MAP (UPDATED - only filters by subregion)
    # ========================================================================

    # Create subregion color mapping
    subregions = drug_prices_df['SubRegion'].unique()
    subregion_colors = {}
    for i, subregion in enumerate(sorted(subregions)):
        subregion_colors[subregion] = PRIMARY_PALETTE[i % len(PRIMARY_PALETTE)]

    # Map countries to their subregions
    country_subregion = drug_prices_df[[
        'Country', 'SubRegion']].drop_duplicates()
    map_subregion_df = europe_gdf.merge(country_subregion, how='left',
                                        left_on='NAME', right_on='Country')

    if len(map_subregion_df.dropna(subset=['SubRegion'])) > 0:
        subregion_fig = px.choropleth(
            map_subregion_df.dropna(subset=['SubRegion']),
            geojson=map_subregion_df.geometry.__geo_interface__,
            locations=map_subregion_df.dropna(subset=['SubRegion']).index,
            color='SubRegion',
            hover_name='NAME',
            custom_data=['SubRegion'],
            color_discrete_map=subregion_colors,
            title="European Subregions"
        )

        if selected_subregion:
            subregion_fig.add_annotation(
                text=f"Selected: {selected_subregion}",
                xref="paper", yref="paper",
                x=0.5, y=0.95,
                showarrow=False,
                font=dict(size=12, color="red"),
                bgcolor="rgba(255,255,255,0.8)"
            )
    else:
        subregion_fig = go.Figure()
        subregion_fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )

    subregion_fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator"
    )

    subregion_fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        clickmode='event+select',
        legend=dict(
            title="Subregion",
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#333",
            borderwidth=1
        )
    )

    # ========================================================================
    # 2. TIME SERIES WITH METRIC SELECTOR
    # ========================================================================

    if timeseries_metric == 'seizures':
        if len(filtered_seizures) > 0:
            ts_grouped = filtered_seizures.groupby(['Year', 'Substance'])[
                'Kilograms'].sum().reset_index()
            ts_grouped['Value'] = ts_grouped['Kilograms'] / 1000
            y_label = 'Seizures (Tons)'
            title_suffix = "Seizures"
        else:
            ts_grouped = pd.DataFrame()
            y_label = 'Seizures (Tons)'
            title_suffix = "Seizures"

    elif timeseries_metric == 'price':
        if len(filtered_prices) > 0:
            ts_grouped = filtered_prices.groupby(['Year', 'Substance'])[
                'Typical_USD'].mean().reset_index()
            ts_grouped['Value'] = ts_grouped['Typical_USD']
            y_label = 'Average Price (USD)'
            title_suffix = "Prices"
        else:
            ts_grouped = pd.DataFrame()
            y_label = 'Average Price (USD)'
            title_suffix = "Prices"

    else:  # purity
        if len(filtered_purity) > 0:
            ts_grouped = filtered_purity.groupby(['Year', 'Substance'])[
                'Typical'].mean().reset_index()
            ts_grouped['Value'] = ts_grouped['Typical']
            y_label = 'Average Purity (%)'
            title_suffix = "Purity"
        else:
            ts_grouped = pd.DataFrame()
            y_label = 'Average Purity (%)'
            title_suffix = "Purity"

    if len(ts_grouped) > 0:
        ts_grouped['Year'] = ts_grouped['Year'].astype(int)

        ts_substances = ts_grouped['Substance'].unique()
        ts_color_map = {
            substance: SUBSTANCE_COLOR_MAP[substance] for substance in ts_substances}

        timeseries_fig = px.line(
            ts_grouped,
            x='Year',
            y='Value',
            color='Substance',
            markers=True,
            title=f"{title_suffix} Over Time ({year_range[0]}-{year_range[1]})",
            labels={'Value': y_label, 'Year': 'Year'},
            color_discrete_map=ts_color_map
        )

        timeseries_fig.update_traces(
            marker=dict(size=10, line=dict(width=2, color='white')),
            line=dict(width=3)
        )

        if selected_year:
            timeseries_fig.add_vline(
                x=selected_year,
                line_dash="dash",
                line_color="#D55E00",
                line_width=3,
                annotation_text=f"Selected: {selected_year}",
                annotation_position="top"
            )

        timeseries_fig.update_layout(
            hovermode='x unified',
            height=400,
            legend=dict(
                title="Substance",
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="#333",
                borderwidth=1
            ),
            margin=dict(l=50, r=150, t=50, b=80),
            xaxis=dict(
                type='linear',
                tickmode='linear',
                tick0=year_range[0],
                dtick=1,
                tickformat='d',
                gridcolor='rgba(128,128,128,0.2)'
            ),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
    else:
        timeseries_fig = go.Figure()
        timeseries_fig.add_annotation(
            text="No data available for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        timeseries_fig.update_layout(height=400)

    # ========================================================================
    # 3. PRICE HEATMAPS - RETAIL AND WHOLESALE (FIXED LEGEND)
    # ========================================================================

    def create_price_heatmap(price_level_filter):
        """Helper function to create heatmap with fixed legend"""
        if len(filtered_prices) > 0:
            latest_year = filtered_prices['Year'].max()
            latest_data = filtered_prices[
                (filtered_prices['Year'] == latest_year) &
                (filtered_prices['LevelOfSale'] == price_level_filter)
            ].copy()

            if len(latest_data) > 0:
                latest_data['SubRegion'] = latest_data['SubRegion'].str.replace(
                    ' Europe', '')

                heatmap_data = latest_data.pivot_table(
                    values='Typical_USD',
                    index='SubRegion',
                    columns='Substance',
                    aggfunc='mean'
                )

                heatmap_fig = go.Figure(data=go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale=COLORBLIND_CONTINUOUS,
                    hoverongaps=False,
                    colorbar=dict(
                        title="Price<br>(USD)",
                        titleside="right",
                        tickmode="linear",
                        thickness=15,
                        len=0.7,
                        x=1.15  # Position to the right
                    ),
                    hovertemplate='Region: %{y}<br>Substance: %{x}<br>Price: $%{z:.2f}<extra></extra>'
                ))

                if selected_region and selected_substance_brush:
                    region_short = selected_region.replace(' Europe', '')
                    if region_short in heatmap_data.index and selected_substance_brush in heatmap_data.columns:
                        row_idx = list(heatmap_data.index).index(region_short)
                        col_idx = list(heatmap_data.columns).index(
                            selected_substance_brush)
                        heatmap_fig.add_shape(
                            type="rect",
                            x0=col_idx - 0.5, x1=col_idx + 0.5,
                            y0=row_idx - 0.5, y1=row_idx + 0.5,
                            line=dict(color="#D55E00", width=4)
                        )

                heatmap_fig.update_layout(
                    title=f"{price_level_filter} Prices ({latest_year})",
                    xaxis_title="Substance",
                    yaxis_title="European Region",
                    height=400,
                    xaxis=dict(side='bottom'),
                    plot_bgcolor='white',
                    # Extra right margin for colorbar
                    margin=dict(l=100, r=150, t=50, b=50)
                )
            else:
                heatmap_fig = go.Figure()
                heatmap_fig.add_annotation(
                    text="No data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16)
                )
                heatmap_fig.update_layout(height=400)
        else:
            heatmap_fig = go.Figure()
            heatmap_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            heatmap_fig.update_layout(height=400)

        return heatmap_fig

    heatmap_retail_fig = create_price_heatmap('Retail')
    heatmap_wholesale_fig = create_price_heatmap('Wholesale')

    # ========================================================================
    # 4. MARGIN MAP
    # ========================================================================

    filtered_margin = inland_margin[
        (inland_margin['Substance'].isin(selected_substances)) &
        (inland_margin['Substance'] != 'Other')
    ].copy()

    if selected_substance_brush:
        filtered_margin = filtered_margin[filtered_margin['Substance']
                                          == selected_substance_brush]
    if selected_countries_scatter:
        filtered_margin = filtered_margin[filtered_margin['Country'].isin(
            selected_countries_scatter)]

    if len(filtered_margin) > 0:
        inland_best_margin = filtered_margin.loc[
            filtered_margin.groupby('Country')['RelativeMargin'].idxmax()
        ].reset_index(drop=True)
    else:
        inland_best_margin = pd.DataFrame()

    map_margin_df = europe_gdf.merge(inland_best_margin, how='left',
                                     left_on='NAME', right_on='Country')

    current_substances = map_margin_df['Substance'].dropna().unique()
    current_color_map = {
        substance: SUBSTANCE_COLOR_MAP[substance] for substance in current_substances}

    if len(map_margin_df.dropna(subset=['Substance'])) > 0:
        margin_fig = px.choropleth(
            map_margin_df.dropna(subset=['Substance']),
            geojson=map_margin_df.geometry.__geo_interface__,
            locations=map_margin_df.dropna(subset=['Substance']).index,
            color='Substance',
            hover_name='NAME',
            hover_data={'RelativeMargin': ':.2f'},
            color_discrete_map=current_color_map,
            title="Substance with Highest Profit Margin"
        )

        if selected_country:
            margin_fig.add_annotation(
                text=f"Selected: {selected_country}",
                xref="paper", yref="paper",
                x=0.5, y=0.95,
                showarrow=False,
                font=dict(size=12, color="red"),
                bgcolor="rgba(255,255,255,0.8)"
            )
    else:
        margin_fig = go.Figure()
        margin_fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )

    margin_fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator"
    )

    margin_fig.update_layout(
        margin=dict(l=0, r=150, t=30, b=0),
        height=400,
        clickmode='event+select',
        legend=dict(
            title="Substance",
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#333",
            borderwidth=1
        )
    )

    # ========================================================================
    # 5. OPTIMAL SEIZURE LOCATION MAP (UPDATED WITH SUBSTANCE SELECTOR)
    # ========================================================================

    if optimal_country and optimal_substance and len(filtered_prices) > 0:
        # Get price for selected country and substance
        source_price_data = filtered_prices[
            (filtered_prices['Country'] == optimal_country) &
            (filtered_prices['Substance'] == optimal_substance) &
            (filtered_prices['LevelOfSale'] == optimal_price_type)
        ]

        if len(source_price_data) > 0:
            source_avg_price = source_price_data['Typical_USD'].mean()

            # Calculate price differences for all countries for the selected substance
            target_prices = filtered_prices[
                (filtered_prices['LevelOfSale'] == optimal_price_type) &
                (filtered_prices['Substance'] == optimal_substance)
            ].groupby('Country')['Typical_USD'].mean().reset_index()

            target_prices['PriceDifference'] = target_prices['Typical_USD'] - \
                source_avg_price
            target_prices['SeizureValue'] = target_prices['PriceDifference']

            map_optimal_df = europe_gdf.merge(target_prices, how='left',
                                              left_on='NAME', right_on='Country')

            if len(map_optimal_df.dropna(subset=['SeizureValue'])) > 0:
                optimal_fig = px.choropleth(
                    map_optimal_df.dropna(subset=['SeizureValue']),
                    geojson=map_optimal_df.geometry.__geo_interface__,
                    locations=map_optimal_df.dropna(
                        subset=['SeizureValue']).index,
                    color='SeizureValue',
                    hover_name='NAME',
                    hover_data={'SeizureValue': ':.2f', 'Typical_USD': ':.2f'},
                    color_continuous_scale='RdYlGn',
                    title=f"Seizure Value Potential: {optimal_substance} from {optimal_country} ({optimal_price_type})",
                    labels={'SeizureValue': 'Value Difference (USD)'}
                )

                optimal_fig.update_layout(
                    coloraxis_colorbar=dict(
                        title="Seizure<br>Value",
                        titleside="right",
                        thickness=15,
                        len=0.7,
                        x=1.15
                    )
                )
            else:
                optimal_fig = go.Figure()
                optimal_fig.add_annotation(
                    text="No data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16)
                )
        else:
            optimal_fig = go.Figure()
            optimal_fig.add_annotation(
                text=f"No {optimal_price_type.lower()} price data for {optimal_substance} in {optimal_country}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14)
            )
    else:
        optimal_fig = go.Figure()
        optimal_fig.add_annotation(
            text="Select a country and substance to see optimal seizure locations",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )

    optimal_fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator"
    )

    optimal_fig.update_layout(
        margin=dict(l=0, r=150, t=30, b=0),
        height=400
    )

    # ========================================================================
    # 6. CORRELATION REGRESSION PLOT
    # ========================================================================

    if len(filtered_prices) > 0 and len(filtered_purity) > 0 and len(filtered_seizures) > 0:
        price_avg = filtered_prices.groupby(['Country', 'Substance', 'Year'])[
            'Typical_USD'].mean().reset_index()
        purity_avg = filtered_purity.groupby(['Country', 'Substance', 'Year'])[
            'Typical'].mean().reset_index()
        seizures_sum = filtered_seizures.groupby(['Country', 'Substance', 'Year'])[
            'Kilograms'].sum().reset_index()

        combined = price_avg.merge(
            purity_avg, on=['Country', 'Substance', 'Year'], how='inner')
        combined = combined.merge(
            seizures_sum, on=['Country', 'Substance', 'Year'], how='inner')
        combined = combined.dropna()
    else:
        combined = pd.DataFrame()

    label_mapping = {
        'Typical_USD': 'Price (USD)',
        'Typical': 'Purity (%)',
        'Kilograms': 'Kilograms Seized'
    }

    substances_to_plot = sorted(
        [s for s in selected_substances if s in combined['Substance'].values]) if len(combined) > 0 else []

    if len(substances_to_plot) == 0 or len(combined) == 0:
        regression_fig = go.Figure()
        regression_fig.add_annotation(
            text="No data available for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        correlation_stats_text = "No correlation data available"
        num_rows = 1
    else:
        num_cols = min(3, len(substances_to_plot))
        num_rows = int(np.ceil(len(substances_to_plot) / num_cols))

        regression_fig = make_subplots(
            rows=num_rows, cols=num_cols,
            subplot_titles=[
                f"{substance}" for substance in substances_to_plot],
            horizontal_spacing=0.1,
            vertical_spacing=0.15
        )

        correlation_results = []

        for idx, substance in enumerate(substances_to_plot):
            row = (idx // num_cols) + 1
            col = (idx % num_cols) + 1

            subset = combined[combined['Substance'] == substance]

            if len(subset) >= 2:
                regression_fig.add_trace(
                    go.Scatter(
                        x=subset[x_axis],
                        y=subset[y_axis],
                        mode='markers',
                        name=substance,
                        marker=dict(
                            color=SUBSTANCE_COLOR_MAP.get(
                                substance, PRIMARY_PALETTE[0]),
                            size=10,
                            opacity=0.7,
                            line=dict(width=1, color='white')
                        ),
                        hovertemplate=f'<b>{substance}</b><br>' +
                        f'{label_mapping[x_axis]}: %{{x:.2f}}<br>' +
                        f'{label_mapping[y_axis]}: %{{y:.2f}}<br>' +
                        '<extra></extra>',
                        showlegend=False
                    ),
                    row=row, col=col
                )

                if subset[x_axis].std() > 0 and subset[y_axis].std() > 0:
                    z = np.polyfit(subset[x_axis], subset[y_axis], 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(
                        subset[x_axis].min(), subset[x_axis].max(), 100)
                    y_line = p(x_line)

                    regression_fig.add_trace(
                        go.Scatter(
                            x=x_line,
                            y=y_line,
                            mode='lines',
                            name=f'{substance} Regression',
                            line=dict(color='#D55E00', width=3, dash='dash'),
                            showlegend=False,
                            hoverinfo='skip'
                        ),
                        row=row, col=col
                    )

                    corr = subset[x_axis].corr(subset[y_axis])
                    correlation_results.append(f"{substance}: {corr:.3f}")
                else:
                    correlation_results.append(
                        f"{substance}: N/A (insufficient variance)")
            else:
                correlation_results.append(
                    f"{substance}: N/A (insufficient data)")

            regression_fig.update_xaxes(
                title_text=label_mapping[x_axis],
                row=row, col=col,
                gridcolor='rgba(128,128,128,0.2)'
            )
            regression_fig.update_yaxes(
                title_text=label_mapping[y_axis],
                row=row, col=col,
                gridcolor='rgba(128,128,128,0.2)'
            )

        correlation_stats_text = html.Div([
            html.Strong("Correlation Coefficients: "),
            html.Br(),
            *[html.Div(result) for result in correlation_results]
        ])

    regression_fig.update_layout(
        height=max(400, 300 * num_rows),
        showlegend=False,
        title_text=f"{label_mapping[y_axis]} vs {label_mapping[x_axis]} by Substance",
        plot_bgcolor='rgba(240,240,240,0.5)'
    )

    # ========================================================================
    # 7. SCATTER PLOT MATRIX
    # ========================================================================

    scatter_substances = [s for s in combined['Substance'].unique()] if len(
        combined) > 0 else []
    scatter_color_map = {
        substance: SUBSTANCE_COLOR_MAP[substance] for substance in scatter_substances}

    if len(combined) > 0:
        scatter_fig = px.scatter(
            combined,
            x='Typical_USD',
            y='Typical',
            size='Kilograms',
            color='Substance',
            hover_data=['Country', 'Year'],
            title="Price vs Purity (size = Seizures) - Click and drag to select points",
            labels={'Typical_USD': 'Price (USD)', 'Typical': 'Purity (%)'},
            opacity=0.7,
            color_discrete_map=scatter_color_map,
            custom_data=['Country']
        )

        scatter_fig.update_traces(
            marker=dict(
                line=dict(width=1, color='white'),
                sizemode='diameter',
                sizeref=2.*max(combined['Kilograms'])/(40.**2),
                sizemin=4
            )
        )

        scatter_fig.update_layout(
            height=500,
            dragmode='lasso',
            legend=dict(
                title="Substance",
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="#333",
                borderwidth=1
            ),
            margin=dict(l=50, r=150, t=50, b=50),
            xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
    else:
        scatter_fig = go.Figure()
        scatter_fig.add_annotation(
            text="No data available for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )

    # ========================================================================
    # 8. STATISTICS PANEL
    # ========================================================================

    total_seizures = filtered_seizures['Kilograms'].sum(
    ) / 1000 if len(filtered_seizures) > 0 else 0
    avg_price = filtered_prices['Typical_USD'].mean() if len(
        filtered_prices) > 0 else 0
    avg_purity = filtered_purity['Typical'].mean() if len(
        filtered_purity) > 0 else 0
    num_countries = filtered_prices['Country'].nunique() if len(
        filtered_prices) > 0 else 0

    stats_panel = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(f"{total_seizures:,.1f}",
                            style={'color': '#0072B2'}),
                    html.P("Total Seizures (Tons)",
                           className="text-muted mb-0")
                ])
            ], className="text-center", style={'border-left': '4px solid #0072B2'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(f"${avg_price:,.2f}", style={'color': '#009E73'}),
                    html.P("Average Price (USD)", className="text-muted mb-0")
                ])
            ], className="text-center", style={'border-left': '4px solid #009E73'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(f"{avg_purity:.1f}%", style={'color': '#E69F00'}),
                    html.P("Average Purity", className="text-muted mb-0")
                ])
            ], className="text-center", style={'border-left': '4px solid #E69F00'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(f"{num_countries}", style={'color': '#CC79A7'}),
                    html.P("Countries Analyzed", className="text-muted mb-0")
                ])
            ], className="text-center", style={'border-left': '4px solid #CC79A7'})
        ], md=3)
    ])

    return (subregion_fig, timeseries_fig, heatmap_retail_fig, heatmap_wholesale_fig,
            margin_fig, optimal_fig, regression_fig, correlation_stats_text,
            scatter_fig, stats_panel, brushing_info_text)

# ============================================================================
# RUN APP
# ============================================================================


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
