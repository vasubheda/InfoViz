"""Artifact loading. The app reads ONLY the cleaned parquet artifacts produced
by the pipeline - it never touches raw Excel or recomputes joins at import.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd

from . import theme

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
GEOJSON_PATH = DATA_DIR / "europe.geojson"
ARTIFACT_VERSION = 1
CLEAN_DIR = DATA_DIR / "clean" / f"v{ARTIFACT_VERSION}"

_ARTIFACTS = [
    "prices", "purity", "seizures", "combined",
    "inland_margin", "enforcement_metrics", "lag_correlation",
]


@dataclass
class AppData:
    prices: pd.DataFrame
    purity: pd.DataFrame
    seizures: pd.DataFrame
    combined: pd.DataFrame
    inland_margin: pd.DataFrame
    enforcement_metrics: pd.DataFrame
    lag_correlation: pd.DataFrame
    europe_gdf: gpd.GeoDataFrame
    geo_lookup: dict
    manifest: dict
    substance_color_map: dict = field(default_factory=dict)

    # --- convenience accessors ---------------------------------------------
    @property
    def substances(self):
        # Union across the analytic tables (not just the inner-joined combined),
        # so substances present in prices/margins but missing seizure coverage
        # (e.g. Amphetamines) remain selectable for the charts that have them.
        present = (set(self.combined["Substance"])
                   | set(self.prices["Substance"])
                   | set(self.inland_margin["Substance"]))
        return sorted(s for s in present if s != "Other")

    @property
    def year_min(self):
        return int(self.combined["Year"].min())

    @property
    def year_max(self):
        return int(self.combined["Year"].max())

    @property
    def countries(self):
        return sorted(self.prices["Country"].unique())

    @property
    def subregions(self):
        return sorted(self.prices["SubRegion"].dropna().unique())


def load_artifacts(version: int = ARTIFACT_VERSION) -> AppData:
    clean = DATA_DIR / "clean" / f"v{version}"
    manifest_path = clean / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No artifacts at {clean}. Run the pipeline first:\n"
            f"    python -m pipeline.build_artifacts --version {version}"
        )
    frames = {name: pd.read_parquet(clean / f"{name}.parquet") for name in _ARTIFACTS}
    geo_lookup = json.loads((clean / "geo_lookup.json").read_text())
    manifest = json.loads(manifest_path.read_text())
    europe_gdf = gpd.read_file(GEOJSON_PATH)

    data = AppData(
        europe_gdf=europe_gdf, geo_lookup=geo_lookup, manifest=manifest, **frames,
    )
    data.substance_color_map = theme.substance_color_map(
        set(data.combined["Substance"]) | set(data.prices["Substance"])
    )
    return data
