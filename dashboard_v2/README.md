# European Drug-Market Intelligence — Dashboard v2

An interactive Dash/Plotly dashboard over the UNODC World Drug Report
(2019–2023, European subset) built to answer the five research questions in the
project proposal, oriented toward **law-enforcement / policy prioritisation**.

This is a clean rewrite of the earlier `src/` prototype. It separates a
documented, reproducible **data-cleaning pipeline** (which writes versioned
artifacts) from a **modular app** that only ever reads those artifacts.

## Research questions → views

| RQ | View |
|----|------|
| Q1 Do seizures move the market? | Within-country, 1-year-lagged seizure→price/purity correlation + per-substance regression facets |
| Q2 Which markets have the highest markup? | Retail/wholesale heatmaps + highest retail–wholesale markup choropleth |
| Q3 How do localised seizures affect neighbours? | Cross-border price-arbitrage exposure map (spillover-risk indicator) |
| Q4 Which markets are most profitable? | Enforcement-priority composite index (Cleveland dot plot) |
| Q5 Which drugs to focus on per country? | Semantic-zoom seizure map + priority index |

## Note on the framework

The proposal names **Streamlit**. We build in **Dash/Plotly** instead, because
the project leans heavily on cross-chart brushing & linking, semantic zoom, and
a year animation — interaction patterns Dash supports natively and robustly. The
analysis, data, and questions are unchanged; only the rendering framework
differs.

## Data handling highlights

- **Standalone pipeline** (`pipeline/`) → versioned parquet artifacts under
  `data/clean/v1/` + a `manifest.json` recording row counts, imputation counts,
  source hashes, and unmatched countries.
- **Imputation with provenance flags**: sporadic missing prices/purity are filled
  by within-series temporal interpolation, then group-median fallback, each
  filled cell flagged `*_is_imputed`. Seizure volumes are *never* imputed
  (a missing year is not a zero). Imputed points render with **hollow / dotted
  markers** in the app.
- **Colourblind-safe throughout**: one `app/theme.py` palette source — Paul Tol
  Muted (categorical), Viridis (sequential), RdBu (diverging). No red-green.
- **Rigorous Q1**: the lagged correlation is computed *within each country*
  then aggregated across countries via a Fisher-z, sample-weighted mean with a
  95% CI — not pooled across heterogeneous markets. Limitations are stated in-app.

## Running

```bash
# 1. install
pip install -r requirements.txt

# 2. build cleaned artifacts (idempotent; never mutates raw)
python -m pipeline.build_artifacts --version 1

# 3. run the app
python -m app.server          # dev server at http://localhost:8050
# or, production:
gunicorn app.server:server
```

The app fails fast with a clear message if the artifacts are missing.

## Tests

```bash
python -m pytest pipeline/tests -q
```

Covers unit conversion, the substance taxonomy, imputation flagging (incl. the
seizures-never-imputed rule), the lag-correlation minimum-n guard, and artifact
presence/sanity.

## Layout

```
pipeline/   load → normalize → impute → features → correlate → build_artifacts
data/       raw/ (xlsx, input only) · europe.geojson · clean/v1/ (artifacts)
app/        theme · data_access · figures/ (pure builders) · components ·
            layout · callbacks/ (selection store, figures, animation, zoom) · server
```
