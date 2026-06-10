# European Drug-Market Intelligence - Dashboard v2

An interactive Dash/Plotly dashboard over the UNODC World Drug Report
(2019-2023, European subset) built to answer the five research questions in the
project proposal, oriented toward **law-enforcement / policy prioritisation**.

This is a clean rewrite of the earlier `src/` prototype. It separates a
documented, reproducible **data-cleaning pipeline** (which writes versioned
artifacts) from a **modular app** that only ever reads those artifacts.

## Research questions -> views

The app has four tabs. The master panel (region/subregion choropleth, year-range
slider, substance toggles) brushes every view via cross-chart linking.

| Tab | Research question | Views |
|-----|-------------------|-------|
| Overview | Cross-cutting market snapshot | Per-substance bars (seizures, price, purity) + animated time-series trends + the same three metrics broken out by subregion |
| National | Q2 Which markets have the highest markup? | Animated metric-by-country choropleth (price/purity split retail vs wholesale, seizures as one panel) + animated highest retail-wholesale markup map (relative % and absolute $/g) |
| Cross-Border | Q3 How do localised seizures affect neighbours? | Cross-border wholesale→retail price-arbitrage. Single country: per-neighbour arbitrage bars + a neighbours map. Multiple/all countries: best-corridor flow map + ranked top-25 arbitrage corridors. (Spillover-*risk* indicator - see *Deviation from the proposal* below) |
| Seizure Impact | Q1 Do seizures move the market? | Within-country, 1-year-lagged seizure→price correlation (aggregated across countries via Fisher-z, or per-country when one is selected) + a per-substance scatter with selectable x/y axes and fit line |
| Cross-Border | Q4 Which markets are most profitable? | Priority-gap flagging on the arbitrage views: high-margin, low-seizure corridors are outlined and listed as the markets where enforcement pays off most |
| Cross-Border | Q5 Which drugs to focus on per country? | Per-neighbour / per-corridor arbitrage broken out by substance, so the highest-margin drug to target is visible per country |

## Note on the framework

The proposal names **Streamlit**. We build in **Dash/Plotly** instead, because
the project leans heavily on cross-chart brushing & linking, semantic zoom, and
a year animation - interaction patterns Dash supports natively and robustly. The
analysis, data, and questions are unchanged; only the rendering framework
differs.

## Deviation from the proposal: Q3

Our proposal asked for Q3 as *"how do localised seizure events impact
neighbouring countries' drug markets?"*, which is basically asking for a cause
and effect over time. The problem is we only have five years of data (2019-2023),
so there aren't enough paired years per border to actually measure a
seizure→neighbour-price lag in a reliable way.

So instead we answer Q3 with a **cross-border price-arbitrage** view. Using the
geojson land borders to find which countries touch, we show where the price gap
between two neighbours makes smuggling across that border more profitable. It's
more of a "where is the risk" view looking forward, rather than proving a cause
after the fact. We still cover the same idea (cross-border market effects), we
just framed it to fit what 5 years of data can realistically show.

## Data handling highlights

Most of the messy bits of the raw UNODC data get cleaned up in the pipeline, and
the lookup tables that drive those transformations all live in one place
(`pipeline/config.py`) so they're easy to find and tweak.

- **Substance grouping**: the raw data uses a bunch of different labels for the
  same drug (e.g. "Cocaine-type", "Cocaine-type drugs"). We map all of those down
  to a fixed set of categories with `SUBSTANCE_MAP`, and anything that doesn't
  match becomes `"Other"`. This is what lets us compare the same substances across
  countries and years.
- **Country names**: the price/seizure spreadsheets and the geojson map don't
  always spell countries the same way, so `COUNTRY_MAP` renames a few of them
  (e.g. "Russian Federation" -> "Russia", "Czechia" -> "Czech Republic") so the
  data actually joins onto the map.
- **Unit conversion**: prices come in all sorts of units (per kilogram, per ounce,
  "10 gram", per litre, etc.). To make them comparable we convert everything to a
  single base unit using two tables: `UNIT_CONVERSION` rescales the amount (e.g.
  kilogram = 1000, ounce ≈ 29.57) and `UNIT_NAME_MAP` collapses all the unit
  labels into Gram / Millilitre / Piece. We also pull the leading number out of
  labels like "10 gram" so the price is divided by the right amount.
- **Imputation with flags**: sporadic missing prices/purity get filled in (first
  by interpolating over time within a series, then a group-median fallback), and
  every filled cell is flagged `*_is_imputed` so views can tell real values from
  filled ones. Seizure volumes are never filled in - a missing year isn't a zero.
- **Versioned output**: the pipeline writes parquet artifacts under
  `data/clean/v1/` plus a `manifest.json` with row counts, imputation counts,
  source hashes and any countries that didn't match the map. Bump
  `ARTIFACT_VERSION` in the config when the cleaning logic changes.

## Running

```bash
# 1. install
pip install -r requirements.txt

# 2. build cleaned artifacts
python -m pipeline.build_artifacts --version 1

# 3. run the app
python -m app.server          # dev server at http://localhost:8050
```

The app fails fast with a clear message if the artifacts are missing.

## Layout

```
pipeline/   transform data for dashboard
data/       raw/ (xlsx, input only), europe.geojson, clean/v1/ (artifacts)
app/        dashboard
```
