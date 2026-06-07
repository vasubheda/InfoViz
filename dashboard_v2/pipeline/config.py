"""Central configuration for the data-cleaning pipeline.

All paths, the artifact version, and the lookup tables used to normalise the raw
UNODC data live here so the rest of the pipeline contains logic only.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & versioning
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
GEOJSON_PATH = DATA_DIR / "europe.geojson"
CLEAN_DIR = DATA_DIR / "clean"

# Bump when the cleaning logic changes in a way that invalidates old artifacts.
ARTIFACT_VERSION = 1

PRICES_XLSX = RAW_DIR / "8.1_Prices_and_purities_of_drugs.xlsx"
SEIZURES_XLSX = RAW_DIR / "7.1_Drug_seizures_2019-2023.xlsx"

PRICES_SHEET = "Prices in USD"
PURITY_SHEET = "Purities"
SEIZURES_SHEET = "Seizures"

REGION = "Europe"

# ---------------------------------------------------------------------------
# Substance taxonomy: ~15 raw UNODC DrugGroup labels -> 8 canonical categories.
# 'Other' is kept as a real category in the artifacts (the app filters it),
# so the cleaned dataset stays a faithful representation of the source.
# ---------------------------------------------------------------------------
SUBSTANCE_MAP = {
    "Amphetamine-type stimulants": "Amphetamines",
    'Amphetamine-type stimulants (excluding "ecstasy")': "Amphetamines",
    "ATS": "Amphetamines",
    "Cannabis-type": "Cannabis",
    "Cannabis-type drugs": "Cannabis",
    "Cannabis-type drugs (excluding synthetic cannabinoids)": "Cannabis",
    "Cocaine-type": "Cocaine",
    "Cocaine-type drugs": "Cocaine",
    "Sedatives and Tranquillizers": "Tranquillizers and Sedatives",
    "Sedatives and tranquilizers (please specify)": "Tranquillizers and Sedatives",
    "Sedatives and tranquillizers": "Tranquillizers and Sedatives",
    '"Ecstasy"-type substances': "Ecstasy",
    "Opioids": "Opioids",
    "Hallucinogens": "Hallucinogens",
}
# Canonical analytic substances (everything else collapses to 'Other').
SUBSTANCES = [
    "Amphetamines", "Cannabis", "Cocaine", "Ecstasy",
    "Hallucinogens", "Opioids", "Tranquillizers and Sedatives",
]
OTHER = "Other"
ALL_SUBSTANCE_CATEGORIES = SUBSTANCES + [OTHER]

# ---------------------------------------------------------------------------
# Country name normalisation to match the geojson `NAME` property.
# ---------------------------------------------------------------------------
COUNTRY_MAP = {
    "Russian Federation": "Russia",
    "North Macedonia": "The former Yugoslav Republic of Macedonia",
    "Czechia": "Czech Republic",
    "Türkiye": "Turkey",
}

# ---------------------------------------------------------------------------
# Unit normalisation: prices are converted to a per-canonical-unit basis.
# `UNIT_CONVERSION` rescales the *price* so it expresses cost of one base unit
# (gram / millilitre / piece). `UNIT_NAME_MAP` collapses 30+ raw unit strings
# into the three canonical units.
# ---------------------------------------------------------------------------
UNIT_CONVERSION = {
    "Kilograms": 1000, "Kilogram": 1000,
    "Litres": 1000, "Litre": 1000,
    "milligram": 1 / 1000, "Ounce": 29.5735,
}

UNIT_NAME_MAP = {
    "Grams": "Gram", "Gram": "Gram", "Kilograms": "Gram", "Kilogram": "Gram",
    "5 gram": "Gram", "10 gram": "Gram", "100 gram": "Gram", "100 milligram": "Gram",
    "Millilitres": "Millilitre", "Litres": "Millilitre", "Millilitre": "Millilitre",
    "Litre": "Millilitre", "Ounce": "Millilitre",
    "Tablets": "Piece", "Tablet": "Piece", "Units": "Piece", "Unit": "Piece",
    "1000 tablets": "Piece", "1000 units": "Piece", "Pill": "Piece", "Dose": "Piece",
    "10000 tablets": "Piece", "100 unit": "Piece", "10 units": "Piece",
    "Plasters": "Piece", "Mark": "Piece", "Stamp": "Piece",
    "Blotting paper": "Piece", "Trip": "Piece",
}

# ---------------------------------------------------------------------------
# Analysis parameters
# ---------------------------------------------------------------------------
MIN_LAG_PAIRS = 3          # min paired years for a within-country lag correlation
SIGNIFICANCE_ALPHA = 0.05  # p-value threshold for the significance marker

# Composite enforcement-priority index weights (must sum to 1.0).
PRIORITY_WEIGHTS = {"margin": 0.4, "retail": 0.3, "inverse_seizure": 0.3}


def clean_version_dir(version: int = ARTIFACT_VERSION) -> Path:
    return CLEAN_DIR / f"v{version}"
