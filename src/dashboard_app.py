# dashboard_app.py
import os
import json
import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import geopandas as gpd
import requests
from datetime import datetime
from scipy import stats

# ============================================================================
# COLORBLIND-FRIENDLY COLOR CONFIGURATION
# ============================================================================

PAUL_TOL_BRIGHT = [
    '#4477AA', '#EE6677', '#228833', '#CCBB44',
    '#66CCEE', '#AA3377', '#BBBBBB'
]

PAUL_TOL_MUTED = [
    '#332288', '#88CCEE', '#44AA99', '#117733',
    '#999933', '#DDCC77', '#CC6677', '#882255',
    '#AA4499', '#DDDDDD'
]

IBM_COLORBLIND_SAFE = [
    '#648FFF', '#785EF0', '#DC267F', '#FE6100',
    '#FFB000', '#06D6A0', '#118AB2', '#073B4C'
]

WONG_PALETTE = [
    '#E69F00', '#56B4E9', '#009E73', '#F0E442',
    '#0072B2', '#D55E00', '#CC79A7', '#000000'
]

OKABE_ITO_PALETTE = [
    '#E69F00', '#56B4E9', '#009E73', '#F0E442',
    '#0072B2', '#D55E00', '#CC79A7', '#999999'
]

PRIMARY_PALETTE = PAUL_TOL_MUTED

COLORBLIND_CONTINUOUS = 'Viridis'

COLORBLIND_DIVERGING_SCALES = {
    'RdYlBu': 'RdYlBu',
    'BrBG': 'BrBG',
    'PiYG': 'PiYG',
}

# ============================================================================
# COLOR UTILITY FUNCTIONS
# ============================================================================


def get_contrasting_text_color(background_hex):
    hex_color = background_hex.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def lum(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b)
    return '#FFFFFF' if luminance < 0.5 else '#000000'


def create_accessible_color_mapping(substances):
    unique_substances = sorted(substances)
    return {s: PRIMARY_PALETTE[i % len(PRIMARY_PALETTE)] for i, s in enumerate(unique_substances)}


# ============================================================================
# DATA LOADING AND PREPROCESSING
# ============================================================================

def load_and_preprocess_data():
    price_and_purity_excel_file = './data/raw/8.1_Prices_and_purities_of_drugs.xlsx'
    seizures_excel_file = './data/raw/7.1_Drug_seizures_2019-2023.xlsx'

    drug_prices_df = pd.read_excel(price_and_purity_excel_file, sheet_name='Prices in USD')
    drug_purity_df = pd.read_excel(price_and_purity_excel_file, sheet_name='Purities')
    drug_seizures_df = pd.read_excel(seizures_excel_file, sheet_name='Seizures')

    drug_prices_df = drug_prices_df.rename(columns={'Country/Territory': 'Country'})
    drug_purity_df = drug_purity_df.rename(columns={'Country/Territory': 'Country'})
    drug_seizures_df = drug_seizures_df.rename(columns={'Reference year': 'Year'})

    region = 'Europe'
    drug_seizures_df = drug_seizures_df[drug_seizures_df['Region'] == region].reset_index(drop=True)
    drug_prices_df = drug_prices_df[drug_prices_df['Region'] == region].reset_index(drop=True)
    drug_purity_df = drug_purity_df[drug_purity_df['Region'] == region].reset_index(drop=True)

    def rename_countries(x):
        mapping = {
            'Russian Federation': 'Russia',
            'North Macedonia': 'The former Yugoslav Republic of Macedonia',
            'Czechia': 'Czech Republic',
            'Türkiye': 'Turkey'
        }
        return mapping.get(x, x)

    for df in [drug_seizures_df, drug_prices_df, drug_purity_df]:
        df['Country'] = df['Country'].apply(rename_countries)

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

    drug_seizures_df['Substance'] = drug_seizures_df['DrugGroup'].apply(classify_substances)
    drug_prices_df['Substance'] = drug_prices_df['DrugGroup'].apply(classify_substances)
    drug_purity_df['Substance'] = drug_purity_df['DrugGroup'].apply(classify_substances)

    for df_ref in [drug_prices_df, drug_purity_df, drug_seizures_df]:
        df_ref.drop(df_ref[df_ref['Substance'] == 'Other'].index, inplace=True)
        df_ref.reset_index(drop=True, inplace=True)

    drug_prices_df = unify_prices(drug_prices_df)
    drug_prices_df = unify_unit_names(drug_prices_df)

    drug_prices_df['Spread_USD'] = drug_prices_df['Maximum_USD'] - drug_prices_df['Minimum_USD']
    drug_prices_df['Spread_rel'] = drug_prices_df['Spread_USD'] / drug_prices_df['Typical_USD']

    retail_df = drug_prices_df[drug_prices_df['LevelOfSale'] == 'Retail']
    wholesale_df = drug_prices_df[drug_prices_df['LevelOfSale'] == 'Wholesale']

    retail_prices = retail_df.groupby(['Country', 'Substance'])['Typical_USD'].mean().reset_index()
    wholesale_prices = wholesale_df.groupby(['Country', 'Substance'])['Typical_USD'].mean().reset_index()

    inland_margin = pd.merge(retail_prices, wholesale_prices, on=['Country', 'Substance'],
                             how='inner', suffixes=('_Retail', '_Wholesale'))
    inland_margin['Margin'] = inland_margin['Typical_USD_Retail'] - inland_margin['Typical_USD_Wholesale']
    inland_margin['RelativeMargin'] = (inland_margin['Margin'] / inland_margin['Typical_USD_Wholesale']) * 100
    inland_margin = inland_margin.dropna(subset=['RelativeMargin'])

    # Load GeoJSON - cache locally for reliability
    geojson_cache = './data/europe.geojson'
    if os.path.exists(geojson_cache):
        europe_gdf = gpd.read_file(geojson_cache)
    else:
        url = "https://raw.githubusercontent.com/leakyMirror/map-of-europe/master/GeoJSON/europe.geojson"
        response = requests.get(url)
        os.makedirs('./data', exist_ok=True)
        with open(geojson_cache, 'wb') as f:
            f.write(response.content)
        europe_gdf = gpd.read_file(response.content)

    return drug_prices_df, drug_purity_df, drug_seizures_df, inland_margin, europe_gdf


def unify_prices(df):
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
    res['conversion_multiplier'] = res['Unit'].map(lambda x: unit_conversion.get(str(x), 1))
    total_multiplier = res['unit_multiplier'] * res['conversion_multiplier']
    for col in price_cols:
        if col in res.columns:
            res[col] = res[col] / total_multiplier
    res = res.drop(['unit_multiplier', 'conversion_multiplier'], axis=1)
    return res


def unify_unit_names(df):
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
# INITIALIZE APP - PRE-COMPUTE ALL EXPENSIVE JOINS AT STARTUP
# ============================================================================

drug_prices_df, drug_purity_df, drug_seizures_df, inland_margin, europe_gdf = load_and_preprocess_data()

all_substances = (set(drug_prices_df['Substance'].unique()) |
                  set(drug_purity_df['Substance'].unique()) |
                  set(drug_seizures_df['Substance'].unique())) - {'Other'}
SUBSTANCE_COLOR_MAP = create_accessible_color_mapping(all_substances)

# Pre-compute full 3-way join (price + purity + seizures) once at startup
_price_avg_full = drug_prices_df.groupby(['Country', 'Substance', 'Year'])['Typical_USD'].mean().reset_index()
_purity_avg_full = drug_purity_df.groupby(['Country', 'Substance', 'Year'])['Typical'].mean().reset_index()
_seizures_sum_full = drug_seizures_df.groupby(['Country', 'Substance', 'Year'])['Kilograms'].sum().reset_index()
COMBINED_DF = _price_avg_full.merge(_purity_avg_full, on=['Country', 'Substance', 'Year'], how='inner')
COMBINED_DF = COMBINED_DF.merge(_seizures_sum_full, on=['Country', 'Substance', 'Year'], how='inner')
COMBINED_DF = COMBINED_DF.dropna()

# Pre-compute subregion lookup
_country_subregion = drug_prices_df[['Country', 'SubRegion']].drop_duplicates()
COMBINED_DF = COMBINED_DF.merge(_country_subregion, on='Country', how='left')

# Pre-compute 1-year lag correlation: seizures in year Y vs price/purity in year Y+1
_seizures_lagged = drug_seizures_df.groupby(['Country', 'Substance', 'Year'])['Kilograms'].sum().reset_index()
_seizures_lagged['Year'] = _seizures_lagged['Year'] + 1  # shift by 1 year
_prices_next = drug_prices_df.groupby(['Country', 'Substance', 'Year'])['Typical_USD'].mean().reset_index()
LAG_DF = _seizures_lagged.merge(_prices_next, on=['Country', 'Substance', 'Year'], how='inner').dropna()

# Compute Pearson r per substance with lag
LAG_CORRELATIONS = []
for substance in LAG_DF['Substance'].unique():
    sub = LAG_DF[LAG_DF['Substance'] == substance]
    if len(sub) >= 5:
        r, p = stats.pearsonr(sub['Kilograms'], sub['Typical_USD'])
        LAG_CORRELATIONS.append({'Substance': substance, 'r': r, 'p': p, 'n': len(sub)})
LAG_CORR_DF = pd.DataFrame(LAG_CORRELATIONS).sort_values('r')

# Pre-compute drug market attractiveness composite index
def _norm(s):
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)

_seizures_by_country_substance = drug_seizures_df.groupby(['Country', 'Substance'])['Kilograms'].sum().reset_index()
_attractiveness = inland_margin.merge(_seizures_by_country_substance, on=['Country', 'Substance'], how='left')
_attractiveness['Kilograms'] = _attractiveness['Kilograms'].fillna(0)
_attractiveness['score'] = (
    _norm(_attractiveness['RelativeMargin']) * 0.4 +
    _norm(_attractiveness['Typical_USD_Retail']) * 0.3 +
    (1 - _norm(np.log1p(_attractiveness['Kilograms']))) * 0.3
)
# Keep top substance per country
ATTRACTIVENESS_DF = _attractiveness.loc[
    _attractiveness.groupby('Country')['score'].idxmax()
].reset_index(drop=True).sort_values('score', ascending=True)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "European Drug Analytics Dashboard"

# ============================================================================
# LAYOUT
# ============================================================================

app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("European Drug Analytics Dashboard",
                    className="text-center text-primary mb-2"),
            html.H5("Interactive Analysis of Drug Prices, Purity, and Seizures (2019-2023)",
                    className="text-center text-muted mb-4"),
            html.Hr()
        ])
    ]),

    # Accessibility notice
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.Strong("Accessibility: "),
                "Colorblind-friendly palettes (Paul Tol's Muted scheme) throughout."
            ], color="success", className="mb-3", dismissable=True)
        ])
    ]),

    # Global Filters
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Global Filters", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Substances:", className="fw-bold"),
                            dcc.Dropdown(
                                id='substance-filter',
                                options=[{'label': s, 'value': s} for s in sorted(drug_prices_df['Substance'].unique())],
                                value=list(drug_prices_df['Substance'].unique()),
                                multi=True,
                                placeholder="Select substances..."
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Select Year Range:", className="fw-bold"),
                            dcc.RangeSlider(
                                id='year-slider',
                                min=int(drug_prices_df['Year'].min()),
                                max=int(drug_prices_df['Year'].max()),
                                value=[int(drug_prices_df['Year'].min()), int(drug_prices_df['Year'].max())],
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

    # Brushing & Linking info
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.Strong("Brushing & Linking Active: "),
                html.Span(id='brushing-info',
                          children="Click on any chart to filter all others."),
                html.Br(),
                dbc.Button("Reset Selection", id='reset-button',
                           color="danger", size="sm", className="mt-2")
            ], color="info", className="mb-3")
        ])
    ]),

    # ========================================================================
    # ROW 1: SUBREGION MAP + TIME SERIES
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("European Subregions (click to drill down)", className="mb-0")),
                dbc.CardBody([
                    html.Small("Click a subregion to zoom in; click a country for detail panel", className="text-muted d-block mb-1"),
                    dcc.Graph(id='subregion-map', config={'displayModeBar': True})
                ])
            ])
        ], md=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col(html.H5("Time Series Analysis", className="mb-0"), md=5),
                        dbc.Col([
                            dcc.Dropdown(
                                id='timeseries-metric-selector',
                                options=[
                                    {'label': 'Seizures (Tons)', 'value': 'seizures'},
                                    {'label': 'Average Price (USD)', 'value': 'price'},
                                    {'label': 'Average Purity (%)', 'value': 'purity'}
                                ],
                                value='seizures',
                                clearable=False,
                                className="small"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Button("Play", id='play-button', color="success",
                                       size="sm", className="mt-1")
                        ], md=3)
                    ])
                ]),
                dbc.CardBody([
                    html.Small("Click a data point to filter by year", className="text-muted d-block mb-1"),
                    dcc.Graph(id='timeseries-chart', config={'displayModeBar': True})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 2: RETAIL AND WHOLESALE HEATMAPS
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Retail Prices by Region & Substance", className="mb-0")),
                dbc.CardBody([
                    html.Small("Click a cell to filter by region and substance", className="text-muted d-block mb-1"),
                    dcc.Graph(id='price-heatmap-retail', config={'displayModeBar': True})
                ])
            ])
        ], md=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Wholesale Prices by Region & Substance", className="mb-0")),
                dbc.CardBody([
                    html.Small("Click a cell to filter by region and substance", className="text-muted d-block mb-1"),
                    dcc.Graph(id='price-heatmap-wholesale', config={'displayModeBar': True})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 3: MARGIN MAP + OPTIMAL SEIZURE MAP
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Highest Profit Margins by Country", className="mb-0")),
                dbc.CardBody([
                    html.Small("Shows substance with highest margin per country", className="text-muted d-block mb-1"),
                    dcc.Graph(id='margin-map', config={'displayModeBar': True})
                ])
            ])
        ], md=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Optimal Seizure Locations", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Country:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='optimal-country-selector',
                                options=[{'label': c, 'value': c} for c in sorted(drug_prices_df['Country'].unique())],
                                value=sorted(drug_prices_df['Country'].unique())[0],
                                clearable=False, className="small mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Substance:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='optimal-substance-selector',
                                options=[{'label': s, 'value': s} for s in sorted(drug_seizures_df['Substance'].unique())],
                                value=sorted(drug_seizures_df['Substance'].unique())[0],
                                clearable=False, className="small mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Price Type:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='optimal-price-type-selector',
                                options=[
                                    {'label': 'Retail', 'value': 'Retail'},
                                    {'label': 'Wholesale', 'value': 'Wholesale'}
                                ],
                                value='Retail',
                                clearable=False, className="small mb-2"
                            )
                        ], md=4)
                    ]),
                    html.Small("Gradient shows seizure value potential vs selected country price", className="text-muted d-block mb-1"),
                    dcc.Graph(id='optimal-selling-map', config={'displayModeBar': True})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 4: PARALLEL COORDINATES (NEW - non-standard multi-variate encoding)
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Parallel Coordinates: Multi-Variate Drug Market Profile", className="mb-0")),
                dbc.CardBody([
                    html.Small(
                        "Drag axis ranges to create multi-variate filters. Each line is a (Country, Substance, Year) observation.",
                        className="text-muted d-block mb-1"
                    ),
                    dcc.Graph(id='parcoords-plot', config={'displayModeBar': True})
                ])
            ])
        ], md=12)
    ], className="mb-4"),

    # ========================================================================
    # ROW 5: LAG CORRELATION + CLEVELAND DOT PLOT (NEW)
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Seizure-to-Price Lag Correlation (1 Year)", className="mb-0")),
                dbc.CardBody([
                    html.Small(
                        "Pearson r: correlation between seizure volume in year Y and street price in year Y+1. "
                        "Positive r = more seizures preceded higher prices.",
                        className="text-muted d-block mb-2"
                    ),
                    dcc.Graph(id='lag-correlation-chart', config={'displayModeBar': False})
                ])
            ])
        ], md=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Drug Market Attractiveness Index by Country", className="mb-0")),
                dbc.CardBody([
                    html.Small(
                        "Composite score: 40% relative margin + 30% retail price + 30% inverse seizure risk. "
                        "Color = substance with highest score per country.",
                        className="text-muted d-block mb-2"
                    ),
                    dcc.Graph(id='attractiveness-chart', config={'displayModeBar': False})
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    # ========================================================================
    # ROW 6: CORRELATION REGRESSION
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Correlation Analysis with Regression", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("X-Axis:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='x-axis-dropdown',
                                options=[
                                    {'label': 'Price (USD)', 'value': 'Typical_USD'},
                                    {'label': 'Purity (%)', 'value': 'Typical'},
                                    {'label': 'Kilograms Seized', 'value': 'Kilograms'}
                                ],
                                value='Typical_USD', clearable=False
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Y-Axis:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='y-axis-dropdown',
                                options=[
                                    {'label': 'Price (USD)', 'value': 'Typical_USD'},
                                    {'label': 'Purity (%)', 'value': 'Typical'},
                                    {'label': 'Kilograms Seized', 'value': 'Kilograms'}
                                ],
                                value='Typical', clearable=False
                            )
                        ], md=6)
                    ], className="mb-3"),
                    dcc.Graph(id='correlation-regression', config={'displayModeBar': True}),
                    html.Div(id='correlation-stats', className="mt-2 small text-muted")
                ])
            ])
        ], md=12)
    ], className="mb-4"),

    # ========================================================================
    # ROW 7: SCATTER PLOT MATRIX
    # ========================================================================
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Multi-Variable Scatter Plot", className="mb-0")),
                dbc.CardBody([
                    html.Small("Click and drag to select points (lasso) and filter all views", className="text-muted d-block mb-1"),
                    dcc.Graph(id='correlation-scatter', config={'displayModeBar': True})
                ])
            ])
        ], md=12)
    ], className="mb-4"),

    # Statistics Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Key Statistics", className="mb-0")),
                dbc.CardBody([html.Div(id='statistics-panel')])
            ])
        ])
    ], className="mb-4"),

    # Country detail offcanvas (semantic zoom level 2)
    dbc.Offcanvas(
        id='country-detail-panel',
        title="Country Detail",
        is_open=False,
        placement="end",
        style={"width": "420px"},
        children=[html.Div(id='country-detail-content')]
    ),

    # Hidden state stores
    dcc.Store(id='zoom-level', data=0),
    dcc.Store(id='zoom-subregion', data=None),
    dcc.Store(id='animation-year', data=int(drug_prices_df['Year'].min())),
    dcc.Interval(id='animation-tick', interval=900, disabled=True, n_intervals=0),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P([
                f"Data: UNODC 2019-2023 | Color palette: Paul Tol's Muted (colorblind-safe)"
            ], className="text-center text-muted small")
        ])
    ])

], fluid=True, style={'backgroundColor': '#f8f9fa'})


# ============================================================================
# ANIMATION CALLBACKS
# ============================================================================

@app.callback(
    Output('animation-tick', 'disabled'),
    Input('play-button', 'n_clicks'),
    State('animation-tick', 'disabled'),
    prevent_initial_call=True
)
def toggle_animation(n_clicks, is_disabled):
    return not is_disabled


@app.callback(
    Output('animation-year', 'data'),
    Input('animation-tick', 'n_intervals'),
    State('animation-year', 'data'),
    prevent_initial_call=True
)
def advance_animation_year(n_intervals, current_year):
    year_max = int(drug_prices_df['Year'].max())
    year_min = int(drug_prices_df['Year'].min())
    next_year = current_year + 1
    if next_year > year_max:
        next_year = year_min
    return next_year


# ============================================================================
# SEMANTIC ZOOM CALLBACKS
# ============================================================================

@app.callback(
    Output('zoom-level', 'data'),
    Output('zoom-subregion', 'data'),
    Output('country-detail-panel', 'is_open'),
    Output('country-detail-content', 'children'),
    Input('subregion-map', 'clickData'),
    State('zoom-level', 'data'),
    State('zoom-subregion', 'data'),
    prevent_initial_call=True
)
def handle_map_zoom(click_data, zoom_level, zoom_subregion):
    if not click_data:
        return zoom_level, zoom_subregion, False, []

    point = click_data['points'][0]

    if zoom_level == 0:
        # Clicked a subregion — zoom in to level 1
        subregion = point.get('customdata', [None])[0] if 'customdata' in point else None
        if subregion:
            return 1, subregion, False, []
        return 0, None, False, []

    elif zoom_level == 1:
        # Clicked a country inside a subregion — open detail panel (level 2)
        country = point.get('hovertext') or point.get('text')
        if not country:
            return 0, None, False, []

        # Build mini detail content
        country_prices = drug_prices_df[drug_prices_df['Country'] == country]
        country_seizures = drug_seizures_df[drug_seizures_df['Country'] == country]

        if len(country_prices) == 0 and len(country_seizures) == 0:
            content = html.P(f"No data available for {country}.")
            return 1, zoom_subregion, True, content

        # Mini trend chart
        if len(country_seizures) > 0:
            ts = country_seizures.groupby(['Year', 'Substance'])['Kilograms'].sum().reset_index()
            ts['Value'] = ts['Kilograms'] / 1000
            mini_fig = px.line(
                ts, x='Year', y='Value', color='Substance',
                title=f"{country}: Seizures (Tons)",
                labels={'Value': 'Tons'},
                color_discrete_map={s: SUBSTANCE_COLOR_MAP.get(s, '#888') for s in ts['Substance'].unique()}
            )
            mini_fig.update_layout(height=250, margin=dict(l=30, r=10, t=40, b=30),
                                   showlegend=True, legend=dict(font=dict(size=9)))
        else:
            mini_fig = go.Figure()

        # KPI stats
        avg_price = country_prices['Typical_USD'].mean() if len(country_prices) > 0 else None
        total_kg = country_seizures['Kilograms'].sum() if len(country_seizures) > 0 else None
        top_substance = (country_prices.groupby('Substance')['Typical_USD'].mean().idxmax()
                         if len(country_prices) > 0 else "N/A")

        content = html.Div([
            html.H5(country, className="text-primary"),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6(f"${avg_price:,.0f}" if avg_price else "N/A"),
                    html.Small("Avg Price (USD)", className="text-muted")
                ])), md=6),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6(f"{total_kg/1000:,.1f}t" if total_kg else "N/A"),
                    html.Small("Total Seizures", className="text-muted")
                ])), md=6),
            ], className="mb-3"),
            html.P([html.Strong("Top substance: "), top_substance]),
            dcc.Graph(figure=mini_fig, config={'displayModeBar': False}),
            dbc.Button("Back to subregion view", id='zoom-back-button',
                       color="secondary", size="sm", className="mt-2")
        ])

        return 1, zoom_subregion, True, content

    return 0, None, False, []


@app.callback(
    Output('zoom-level', 'data', allow_duplicate=True),
    Output('zoom-subregion', 'data', allow_duplicate=True),
    Output('country-detail-panel', 'is_open', allow_duplicate=True),
    Input('zoom-back-button', 'n_clicks'),
    prevent_initial_call=True
)
def zoom_back(_):
    return 0, None, False


# ============================================================================
# MAIN DASHBOARD CALLBACK
# ============================================================================

@app.callback(
    [Output('subregion-map', 'figure'),
     Output('timeseries-chart', 'figure'),
     Output('price-heatmap-retail', 'figure'),
     Output('price-heatmap-wholesale', 'figure'),
     Output('margin-map', 'figure'),
     Output('optimal-selling-map', 'figure'),
     Output('parcoords-plot', 'figure'),
     Output('lag-correlation-chart', 'figure'),
     Output('attractiveness-chart', 'figure'),
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
     Input('reset-button', 'n_clicks'),
     Input('zoom-level', 'data'),
     Input('zoom-subregion', 'data'),
     Input('animation-year', 'data')]
)
def update_dashboard(selected_substances, year_range, timeseries_metric,
                     optimal_country, optimal_substance, optimal_price_type, x_axis, y_axis,
                     subregion_click, timeseries_click, heatmap_retail_click,
                     heatmap_wholesale_click, margin_click, scatter_selection, reset_clicks,
                     zoom_level, zoom_subregion, animation_year):

    triggered_id = ctx.triggered_id

    # Initialize brushing state
    selected_country = None
    selected_year = None
    selected_substance_brush = None
    selected_region = None
    selected_subregion = None
    selected_countries_scatter = None
    brushing_info_text = "No selection active. Click on any visualization to filter others."

    if triggered_id == 'reset-button':
        subregion_click = timeseries_click = heatmap_retail_click = None
        heatmap_wholesale_click = margin_click = scatter_selection = None
        brushing_info_text = "Selection cleared."

    elif subregion_click and triggered_id == 'subregion-map':
        try:
            if 'customdata' in subregion_click['points'][0]:
                selected_subregion = subregion_click['points'][0]['customdata'][0]
                brushing_info_text = f"Subregion selected: {selected_subregion}"
        except (KeyError, IndexError, TypeError):
            pass

    elif margin_click and triggered_id == 'margin-map':
        try:
            selected_country = margin_click['points'][0].get('hovertext') or \
                               europe_gdf.iloc[margin_click['points'][0].get('location', 0)]['NAME']
            if selected_country:
                brushing_info_text = f"Country from margin map: {selected_country}"
        except (KeyError, IndexError, TypeError):
            pass

    elif timeseries_click and triggered_id == 'timeseries-chart':
        try:
            selected_year = timeseries_click['points'][0].get('x')
            selected_substance_brush = timeseries_click['points'][0].get('legendgroup')
            brushing_info_text = f"Year {selected_year} selected"
            if selected_substance_brush:
                brushing_info_text += f" — {selected_substance_brush}"
        except (KeyError, IndexError, TypeError):
            pass

    elif triggered_id in ('price-heatmap-retail', 'price-heatmap-wholesale'):
        click_data = heatmap_retail_click if triggered_id == 'price-heatmap-retail' else heatmap_wholesale_click
        if click_data:
            try:
                selected_region = click_data['points'][0].get('y')
                selected_substance_brush = click_data['points'][0].get('x')
                price_type = "Retail" if triggered_id == 'price-heatmap-retail' else "Wholesale"
                brushing_info_text = f"{price_type} — {selected_region}, {selected_substance_brush}"
            except (KeyError, IndexError, TypeError):
                pass

    elif scatter_selection and triggered_id == 'correlation-scatter':
        try:
            if scatter_selection.get('points'):
                selected_countries_scatter = list(set(
                    p['customdata'][0] for p in scatter_selection['points']
                    if 'customdata' in p and p['customdata']
                ))
                brushing_info_text = f"{len(selected_countries_scatter)} countries selected from scatter."
        except (KeyError, IndexError, TypeError):
            pass

    # Apply animation year as an additional year filter when animation runs
    effective_year_range = list(year_range)
    if triggered_id == 'animation-year':
        effective_year_range = [animation_year, animation_year]
        brushing_info_text = f"Animating year: {animation_year}"

    # ========================================================================
    # APPLY GLOBAL FILTERS
    # ========================================================================
    def filter_df(df, year_col='Year', substance_col='Substance'):
        return df[
            (df[substance_col].isin(selected_substances)) &
            (df[substance_col] != 'Other') &
            (df[year_col] >= effective_year_range[0]) &
            (df[year_col] <= effective_year_range[1])
        ].copy()

    filtered_prices = filter_df(drug_prices_df)
    filtered_purity = filter_df(drug_purity_df)
    filtered_seizures = filter_df(drug_seizures_df)

    # Apply brushing filters
    def apply_brush(df):
        d = df
        if selected_subregion:
            d = d[d['SubRegion'] == selected_subregion]
        if selected_country:
            d = d[d['Country'] == selected_country]
        if selected_year:
            d = d[d['Year'] == selected_year]
        if selected_substance_brush:
            d = d[d['Substance'] == selected_substance_brush]
        if selected_region:
            region_filter = selected_region if ' Europe' in selected_region else f"{selected_region} Europe"
            d = d[d['SubRegion'] == region_filter]
        if selected_countries_scatter:
            d = d[d['Country'].isin(selected_countries_scatter)]
        return d

    filtered_prices = apply_brush(filtered_prices)
    filtered_purity = apply_brush(filtered_purity)
    filtered_seizures = apply_brush(filtered_seizures)

    # ========================================================================
    # 1. SUBREGION / SEMANTIC ZOOM MAP
    # ========================================================================
    country_subregion = drug_prices_df[['Country', 'SubRegion']].drop_duplicates()

    if zoom_level == 0:
        # Default: subregion-colored full Europe
        subregions = drug_prices_df['SubRegion'].unique()
        subregion_colors = {sr: PRIMARY_PALETTE[i % len(PRIMARY_PALETTE)]
                            for i, sr in enumerate(sorted(subregions))}
        map_subregion_df = europe_gdf.merge(country_subregion, how='left',
                                            left_on='NAME', right_on='Country')
        valid = map_subregion_df.dropna(subset=['SubRegion'])
        if len(valid) > 0:
            subregion_fig = px.choropleth(
                valid,
                geojson=valid.geometry.__geo_interface__,
                locations=valid.index,
                color='SubRegion',
                hover_name='NAME',
                custom_data=['SubRegion'],
                color_discrete_map=subregion_colors,
                title="Click a subregion to zoom in"
            )
        else:
            subregion_fig = go.Figure()

        subregion_fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
        subregion_fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0), height=400, clickmode='event+select',
            legend=dict(title="Subregion", orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.02, bgcolor="rgba(255,255,255,0.9)",
                        bordercolor="#333", borderwidth=1)
        )

    else:
        # Zoom level 1: show countries within the zoomed subregion, colored by seizures
        countries_in_subregion = country_subregion[country_subregion['SubRegion'] == zoom_subregion]['Country'].tolist()
        zoom_gdf = europe_gdf[europe_gdf['NAME'].isin(countries_in_subregion)].copy()

        seizures_by_country = (filtered_seizures.groupby('Country')['Kilograms'].sum() / 1000).reset_index()
        seizures_by_country.columns = ['Country', 'Tons']
        zoom_gdf = zoom_gdf.merge(seizures_by_country, how='left', left_on='NAME', right_on='Country')
        zoom_gdf['Tons'] = zoom_gdf['Tons'].fillna(0)

        valid_zoom = zoom_gdf
        if len(valid_zoom) > 0:
            subregion_fig = px.choropleth(
                valid_zoom,
                geojson=valid_zoom.geometry.__geo_interface__,
                locations=valid_zoom.index,
                color='Tons',
                hover_name='NAME',
                color_continuous_scale=COLORBLIND_CONTINUOUS,
                title=f"{zoom_subregion} — click a country for detail"
            )
        else:
            subregion_fig = go.Figure()

        subregion_fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
        subregion_fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0), height=400, clickmode='event+select',
            coloraxis_colorbar=dict(title="Seizures<br>(Tons)", thickness=12, len=0.6)
        )

    # ========================================================================
    # 2. TIME SERIES
    # ========================================================================
    if timeseries_metric == 'seizures':
        ts_src = filtered_seizures
        ts_col, ts_transform = 'Kilograms', lambda x: x / 1000
        y_label, title_suffix = 'Seizures (Tons)', 'Seizures'
    elif timeseries_metric == 'price':
        ts_src = filtered_prices
        ts_col, ts_transform = 'Typical_USD', lambda x: x
        y_label, title_suffix = 'Average Price (USD)', 'Prices'
    else:
        ts_src = filtered_purity
        ts_col, ts_transform = 'Typical', lambda x: x
        y_label, title_suffix = 'Average Purity (%)', 'Purity'

    if len(ts_src) > 0:
        if timeseries_metric == 'seizures':
            ts_grouped = ts_src.groupby(['Year', 'Substance'])[ts_col].sum().reset_index()
        else:
            ts_grouped = ts_src.groupby(['Year', 'Substance'])[ts_col].mean().reset_index()
        ts_grouped['Value'] = ts_transform(ts_grouped[ts_col])
        ts_grouped['Year'] = ts_grouped['Year'].astype(int)

        ts_color_map = {s: SUBSTANCE_COLOR_MAP[s] for s in ts_grouped['Substance'].unique() if s in SUBSTANCE_COLOR_MAP}
        timeseries_fig = px.line(
            ts_grouped, x='Year', y='Value', color='Substance', markers=True,
            title=f"{title_suffix} Over Time ({effective_year_range[0]}-{effective_year_range[1]})",
            labels={'Value': y_label, 'Year': 'Year'},
            color_discrete_map=ts_color_map
        )
        timeseries_fig.update_traces(marker=dict(size=10, line=dict(width=2, color='white')), line=dict(width=3))

        if selected_year:
            timeseries_fig.add_vline(x=selected_year, line_dash="dash", line_color="#D55E00", line_width=3,
                                     annotation_text=f"Selected: {selected_year}", annotation_position="top")
        if triggered_id == 'animation-year':
            timeseries_fig.add_vline(x=animation_year, line_dash="dot", line_color="#0072B2", line_width=2)

        timeseries_fig.update_layout(
            hovermode='x unified', height=400,
            legend=dict(title="Substance", orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.02, bgcolor="rgba(255,255,255,0.9)",
                        bordercolor="#333", borderwidth=1),
            margin=dict(l=50, r=150, t=50, b=80),
            xaxis=dict(type='linear', tickmode='linear', tick0=year_range[0],
                       dtick=1, tickformat='d', gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
    else:
        timeseries_fig = _empty_fig("No data for selected filters")

    # ========================================================================
    # 3. PRICE HEATMAPS
    # ========================================================================
    def create_price_heatmap(price_level):
        if len(filtered_prices) == 0:
            return _empty_fig("No data available")
        latest_year = filtered_prices['Year'].max()
        data = filtered_prices[
            (filtered_prices['Year'] == latest_year) &
            (filtered_prices['LevelOfSale'] == price_level)
        ].copy()
        if len(data) == 0:
            return _empty_fig("No data available")
        data['SubRegion'] = data['SubRegion'].str.replace(' Europe', '')
        hm = data.pivot_table(values='Typical_USD', index='SubRegion', columns='Substance', aggfunc='mean')
        fig = go.Figure(data=go.Heatmap(
            z=hm.values, x=hm.columns, y=hm.index,
            colorscale=COLORBLIND_CONTINUOUS, hoverongaps=False,
            colorbar=dict(title="Price<br>(USD)", titleside="right", thickness=15, len=0.7, x=1.15),
            hovertemplate='Region: %{y}<br>Substance: %{x}<br>Price: $%{z:.2f}<extra></extra>'
        ))
        if selected_region and selected_substance_brush:
            region_short = selected_region.replace(' Europe', '')
            if region_short in hm.index and selected_substance_brush in hm.columns:
                ri = list(hm.index).index(region_short)
                ci = list(hm.columns).index(selected_substance_brush)
                fig.add_shape(type="rect", x0=ci-0.5, x1=ci+0.5, y0=ri-0.5, y1=ri+0.5,
                              line=dict(color="#D55E00", width=4))
        fig.update_layout(
            title=f"{price_level} Prices ({latest_year})",
            xaxis_title="Substance", yaxis_title="European Region",
            height=400, xaxis=dict(side='bottom'), plot_bgcolor='white',
            margin=dict(l=100, r=150, t=50, b=50)
        )
        return fig

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
        filtered_margin = filtered_margin[filtered_margin['Substance'] == selected_substance_brush]
    if selected_countries_scatter:
        filtered_margin = filtered_margin[filtered_margin['Country'].isin(selected_countries_scatter)]

    if len(filtered_margin) > 0:
        best = filtered_margin.loc[filtered_margin.groupby('Country')['RelativeMargin'].idxmax()].reset_index(drop=True)
        map_margin_df = europe_gdf.merge(best, how='left', left_on='NAME', right_on='Country')
        valid_margin = map_margin_df.dropna(subset=['Substance'])
        current_color_map = {s: SUBSTANCE_COLOR_MAP[s] for s in valid_margin['Substance'].unique() if s in SUBSTANCE_COLOR_MAP}
        if len(valid_margin) > 0:
            margin_fig = px.choropleth(
                valid_margin, geojson=valid_margin.geometry.__geo_interface__,
                locations=valid_margin.index, color='Substance',
                hover_name='NAME', hover_data={'RelativeMargin': ':.2f'},
                color_discrete_map=current_color_map,
                title="Substance with Highest Profit Margin"
            )
        else:
            margin_fig = _empty_fig("No data available")
    else:
        margin_fig = _empty_fig("No data available")

    margin_fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    margin_fig.update_layout(
        margin=dict(l=0, r=150, t=30, b=0), height=400, clickmode='event+select',
        legend=dict(title="Substance", orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.02, bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#333", borderwidth=1)
    )

    # ========================================================================
    # 5. OPTIMAL SEIZURE MAP
    # ========================================================================
    if optimal_country and optimal_substance and len(filtered_prices) > 0:
        source_data = filtered_prices[
            (filtered_prices['Country'] == optimal_country) &
            (filtered_prices['Substance'] == optimal_substance) &
            (filtered_prices['LevelOfSale'] == optimal_price_type)
        ]
        if len(source_data) > 0:
            source_avg = source_data['Typical_USD'].mean()
            target = filtered_prices[
                (filtered_prices['LevelOfSale'] == optimal_price_type) &
                (filtered_prices['Substance'] == optimal_substance)
            ].groupby('Country')['Typical_USD'].mean().reset_index()
            target['PriceDifference'] = target['Typical_USD'] - source_avg
            map_opt = europe_gdf.merge(target, how='left', left_on='NAME', right_on='Country')
            valid_opt = map_opt.dropna(subset=['PriceDifference'])
            if len(valid_opt) > 0:
                optimal_fig = px.choropleth(
                    valid_opt, geojson=valid_opt.geometry.__geo_interface__,
                    locations=valid_opt.index, color='PriceDifference',
                    hover_name='NAME', hover_data={'PriceDifference': ':.2f', 'Typical_USD': ':.2f'},
                    color_continuous_scale='RdYlGn',
                    title=f"Seizure Value Potential: {optimal_substance} from {optimal_country}",
                    labels={'PriceDifference': 'Value Diff (USD)'}
                )
                optimal_fig.update_layout(
                    coloraxis_colorbar=dict(title="Seizure<br>Value", thickness=15, len=0.7, x=1.15)
                )
            else:
                optimal_fig = _empty_fig("No data available")
        else:
            optimal_fig = _empty_fig(f"No {optimal_price_type.lower()} data for {optimal_substance} in {optimal_country}")
    else:
        optimal_fig = _empty_fig("Select a country and substance")

    optimal_fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    optimal_fig.update_layout(margin=dict(l=0, r=150, t=30, b=0), height=400)

    # ========================================================================
    # 6. PARALLEL COORDINATES (new non-standard encoding)
    # ========================================================================
    # Use COMBINED_DF filtered by current selections
    cdf = COMBINED_DF.copy()
    cdf = cdf[
        (cdf['Substance'].isin(selected_substances)) &
        (cdf['Year'] >= effective_year_range[0]) &
        (cdf['Year'] <= effective_year_range[1])
    ]
    if selected_subregion and 'SubRegion' in cdf.columns:
        cdf = cdf[cdf['SubRegion'] == selected_subregion]
    if selected_country:
        cdf = cdf[cdf['Country'] == selected_country]
    if selected_year:
        cdf = cdf[cdf['Year'] == selected_year]
    if selected_substance_brush:
        cdf = cdf[cdf['Substance'] == selected_substance_brush]
    if selected_countries_scatter:
        cdf = cdf[cdf['Country'].isin(selected_countries_scatter)]

    # Merge with inland_margin for RelativeMargin
    margin_lookup = inland_margin[['Country', 'Substance', 'RelativeMargin']].copy()
    cdf = cdf.merge(margin_lookup, on=['Country', 'Substance'], how='left')

    if len(cdf) > 0:
        substance_list = sorted(cdf['Substance'].unique())
        substance_idx = {s: i for i, s in enumerate(substance_list)}
        cdf['substance_num'] = cdf['Substance'].map(substance_idx)

        colorscale_vals = [i / max(len(substance_list) - 1, 1) for i in range(len(substance_list))]
        palette_hex = [PRIMARY_PALETTE[i % len(PRIMARY_PALETTE)] for i in range(len(substance_list))]

        def hex_to_rgb_str(h):
            h = h.lstrip('#')
            return f"rgb({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)})"

        colorscale = [[v, hex_to_rgb_str(c)] for v, c in zip(colorscale_vals, palette_hex)]
        if len(colorscale) == 1:
            colorscale = [[0, colorscale[0][1]], [1, colorscale[0][1]]]

        parcoords_fig = go.Figure(data=go.Parcoords(
            line=dict(
                color=cdf['substance_num'],
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(
                    title="Substance",
                    tickvals=list(substance_idx.values()),
                    ticktext=list(substance_idx.keys()),
                    thickness=12, len=0.8
                )
            ),
            dimensions=[
                dict(label='Price (USD)', values=cdf['Typical_USD'],
                     range=[cdf['Typical_USD'].quantile(0.01), cdf['Typical_USD'].quantile(0.99)]),
                dict(label='Purity (%)', values=cdf['Typical'],
                     range=[0, 100]),
                dict(label='Seizures (kg)', values=cdf['Kilograms'],
                     range=[0, cdf['Kilograms'].quantile(0.95)]),
                dict(label='Rel. Margin (%)', values=cdf['RelativeMargin'].fillna(0),
                     range=[cdf['RelativeMargin'].quantile(0.01) if cdf['RelativeMargin'].notna().any() else 0,
                            cdf['RelativeMargin'].quantile(0.99) if cdf['RelativeMargin'].notna().any() else 100]),
                dict(label='Year', values=cdf['Year'],
                     tickvals=sorted(cdf['Year'].unique()),
                     range=[cdf['Year'].min(), cdf['Year'].max()])
            ]
        ))
        parcoords_fig.update_layout(
            height=350,
            margin=dict(l=80, r=120, t=30, b=30),
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
    else:
        parcoords_fig = _empty_fig("No data for selected filters")

    # ========================================================================
    # 7. LAG CORRELATION BAR CHART (new statistical model)
    # ========================================================================
    if len(LAG_CORR_DF) > 0:
        bar_colors = [SUBSTANCE_COLOR_MAP.get(s, PRIMARY_PALETTE[0]) for s in LAG_CORR_DF['Substance']]
        lag_fig = go.Figure()
        lag_fig.add_trace(go.Bar(
            x=LAG_CORR_DF['r'],
            y=LAG_CORR_DF['Substance'],
            orientation='h',
            marker_color=bar_colors,
            text=[f"r={r:.2f}, p={p:.3f}, n={n}" for r, p, n in
                  zip(LAG_CORR_DF['r'], LAG_CORR_DF['p'], LAG_CORR_DF['n'])],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>r = %{x:.3f}<extra></extra>'
        ))
        lag_fig.add_vline(x=0, line_color='black', line_width=1)
        # Mark significant bars
        for _, row in LAG_CORR_DF.iterrows():
            if row['p'] < 0.05:
                lag_fig.add_annotation(
                    x=row['r'] + (0.02 if row['r'] >= 0 else -0.02),
                    y=row['Substance'],
                    text="*",
                    showarrow=False,
                    font=dict(size=14, color='red')
                )
        lag_fig.update_layout(
            title="* = p < 0.05",
            xaxis_title="Pearson r (seizures Y → price Y+1)",
            height=300,
            margin=dict(l=140, r=40, t=40, b=40),
            xaxis=dict(range=[-1, 1], gridcolor='rgba(128,128,128,0.2)', zeroline=True),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
    else:
        lag_fig = _empty_fig("Insufficient data for lag correlation")

    # ========================================================================
    # 8. ATTRACTIVENESS CLEVELAND DOT PLOT (new non-standard chart)
    # ========================================================================
    if len(ATTRACTIVENESS_DF) > 0:
        dot_colors = [SUBSTANCE_COLOR_MAP.get(s, PRIMARY_PALETTE[0]) for s in ATTRACTIVENESS_DF['Substance']]
        attract_fig = go.Figure()
        # Horizontal lines from 0 to dot
        for i, row in enumerate(ATTRACTIVENESS_DF.itertuples()):
            attract_fig.add_shape(
                type='line',
                x0=0, x1=row.score, y0=i, y1=i,
                line=dict(color='rgba(128,128,128,0.4)', width=1)
            )
        attract_fig.add_trace(go.Scatter(
            x=ATTRACTIVENESS_DF['score'],
            y=ATTRACTIVENESS_DF['Country'],
            mode='markers',
            marker=dict(
                color=dot_colors,
                size=10,
                line=dict(width=1, color='white')
            ),
            text=ATTRACTIVENESS_DF['Substance'],
            hovertemplate='<b>%{y}</b><br>Score: %{x:.3f}<br>Top substance: %{text}<extra></extra>'
        ))
        attract_fig.update_layout(
            xaxis_title="Attractiveness Score",
            height=max(300, len(ATTRACTIVENESS_DF) * 20),
            margin=dict(l=130, r=30, t=20, b=40),
            xaxis=dict(range=[0, 1.05], gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)', tickfont=dict(size=10)),
            plot_bgcolor='rgba(240,240,240,0.5)',
            showlegend=False
        )
    else:
        attract_fig = _empty_fig("No data available")

    # ========================================================================
    # 9. CORRELATION REGRESSION
    # ========================================================================
    filtered_cdf = COMBINED_DF[
        (COMBINED_DF['Substance'].isin(selected_substances)) &
        (COMBINED_DF['Year'] >= effective_year_range[0]) &
        (COMBINED_DF['Year'] <= effective_year_range[1])
    ].copy()
    if selected_subregion and 'SubRegion' in filtered_cdf.columns:
        filtered_cdf = filtered_cdf[filtered_cdf['SubRegion'] == selected_subregion]
    if selected_country:
        filtered_cdf = filtered_cdf[filtered_cdf['Country'] == selected_country]
    if selected_year:
        filtered_cdf = filtered_cdf[filtered_cdf['Year'] == selected_year]
    if selected_substance_brush:
        filtered_cdf = filtered_cdf[filtered_cdf['Substance'] == selected_substance_brush]
    if selected_countries_scatter:
        filtered_cdf = filtered_cdf[filtered_cdf['Country'].isin(selected_countries_scatter)]

    label_mapping = {'Typical_USD': 'Price (USD)', 'Typical': 'Purity (%)', 'Kilograms': 'Kilograms Seized'}
    substances_to_plot = sorted([s for s in selected_substances if s in filtered_cdf['Substance'].values]) \
        if len(filtered_cdf) > 0 else []

    if len(substances_to_plot) == 0 or len(filtered_cdf) == 0:
        regression_fig = _empty_fig("No data for selected filters")
        correlation_stats_text = "No correlation data available"
        num_rows = 1
    else:
        num_cols = min(3, len(substances_to_plot))
        num_rows = int(np.ceil(len(substances_to_plot) / num_cols))
        regression_fig = make_subplots(
            rows=num_rows, cols=num_cols,
            subplot_titles=substances_to_plot,
            horizontal_spacing=0.1, vertical_spacing=0.15
        )
        correlation_results = []
        for idx, substance in enumerate(substances_to_plot):
            row, col = (idx // num_cols) + 1, (idx % num_cols) + 1
            subset = filtered_cdf[filtered_cdf['Substance'] == substance]
            if len(subset) >= 2:
                regression_fig.add_trace(
                    go.Scatter(
                        x=subset[x_axis], y=subset[y_axis], mode='markers',
                        name=substance,
                        marker=dict(color=SUBSTANCE_COLOR_MAP.get(substance, PRIMARY_PALETTE[0]),
                                    size=10, opacity=0.7, line=dict(width=1, color='white')),
                        hovertemplate=f'<b>{substance}</b><br>{label_mapping[x_axis]}: %{{x:.2f}}<br>'
                                      f'{label_mapping[y_axis]}: %{{y:.2f}}<extra></extra>',
                        showlegend=False
                    ), row=row, col=col
                )
                if subset[x_axis].std() > 0 and subset[y_axis].std() > 0:
                    z = np.polyfit(subset[x_axis], subset[y_axis], 1)
                    x_line = np.linspace(subset[x_axis].min(), subset[x_axis].max(), 100)
                    regression_fig.add_trace(
                        go.Scatter(x=x_line, y=np.poly1d(z)(x_line), mode='lines',
                                   line=dict(color='#D55E00', width=3, dash='dash'),
                                   showlegend=False, hoverinfo='skip'),
                        row=row, col=col
                    )
                    corr = subset[x_axis].corr(subset[y_axis])
                    correlation_results.append(f"{substance}: r={corr:.3f}")
                else:
                    correlation_results.append(f"{substance}: N/A (insufficient variance)")
            else:
                correlation_results.append(f"{substance}: N/A (insufficient data)")
            regression_fig.update_xaxes(title_text=label_mapping[x_axis], row=row, col=col,
                                         gridcolor='rgba(128,128,128,0.2)')
            regression_fig.update_yaxes(title_text=label_mapping[y_axis], row=row, col=col,
                                         gridcolor='rgba(128,128,128,0.2)')
        correlation_stats_text = html.Div([
            html.Strong("Correlation Coefficients: "),
            html.Br(),
            *[html.Div(r) for r in correlation_results]
        ])

    regression_fig.update_layout(
        height=max(400, 300 * num_rows), showlegend=False,
        title_text=f"{label_mapping[y_axis]} vs {label_mapping[x_axis]} by Substance",
        plot_bgcolor='rgba(240,240,240,0.5)'
    )

    # ========================================================================
    # 10. SCATTER PLOT
    # ========================================================================
    scatter_data = filtered_cdf if len(filtered_cdf) > 0 else pd.DataFrame()
    if len(scatter_data) > 0:
        scatter_color_map = {s: SUBSTANCE_COLOR_MAP[s] for s in scatter_data['Substance'].unique()
                             if s in SUBSTANCE_COLOR_MAP}
        scatter_fig = px.scatter(
            scatter_data, x='Typical_USD', y='Typical', size='Kilograms',
            color='Substance', hover_data=['Country', 'Year'],
            title="Price vs Purity (size = Seizures) — drag to select",
            labels={'Typical_USD': 'Price (USD)', 'Typical': 'Purity (%)'},
            opacity=0.7, color_discrete_map=scatter_color_map,
            custom_data=['Country']
        )
        scatter_fig.update_traces(marker=dict(
            line=dict(width=1, color='white'), sizemode='diameter',
            sizeref=2.*max(scatter_data['Kilograms'])/(40.**2), sizemin=4
        ))
        scatter_fig.update_layout(
            height=500, dragmode='lasso',
            legend=dict(title="Substance", orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.02, bgcolor="rgba(255,255,255,0.9)",
                        bordercolor="#333", borderwidth=1),
            margin=dict(l=50, r=150, t=50, b=50),
            xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
    else:
        scatter_fig = _empty_fig("No data for selected filters")

    # ========================================================================
    # 11. STATISTICS PANEL
    # ========================================================================
    total_seizures = filtered_seizures['Kilograms'].sum() / 1000 if len(filtered_seizures) > 0 else 0
    avg_price = filtered_prices['Typical_USD'].mean() if len(filtered_prices) > 0 else 0
    avg_purity = filtered_purity['Typical'].mean() if len(filtered_purity) > 0 else 0
    num_countries = filtered_prices['Country'].nunique() if len(filtered_prices) > 0 else 0

    stats_panel = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(f"{total_seizures:,.1f}", style={'color': '#0072B2'}),
            html.P("Total Seizures (Tons)", className="text-muted mb-0")
        ]), className="text-center", style={'border-left': '4px solid #0072B2'}), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(f"${avg_price:,.2f}", style={'color': '#009E73'}),
            html.P("Average Price (USD)", className="text-muted mb-0")
        ]), className="text-center", style={'border-left': '4px solid #009E73'}), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(f"{avg_purity:.1f}%", style={'color': '#E69F00'}),
            html.P("Average Purity", className="text-muted mb-0")
        ]), className="text-center", style={'border-left': '4px solid #E69F00'}), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(f"{num_countries}", style={'color': '#CC79A7'}),
            html.P("Countries Analyzed", className="text-muted mb-0")
        ]), className="text-center", style={'border-left': '4px solid #CC79A7'}), md=3)
    ])

    return (subregion_fig, timeseries_fig, heatmap_retail_fig, heatmap_wholesale_fig,
            margin_fig, optimal_fig, parcoords_fig, lag_fig, attract_fig,
            regression_fig, correlation_stats_text, scatter_fig, stats_panel, brushing_info_text)


def _empty_fig(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_layout(height=300)
    return fig


# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
