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
    "inland_margin", "lag_correlation",
]


@dataclass
class AppData:
    prices: pd.DataFrame
    purity: pd.DataFrame
    seizures: pd.DataFrame
    combined: pd.DataFrame
    inland_margin: pd.DataFrame
    lag_correlation: pd.DataFrame
    europe_gdf: gpd.GeoDataFrame
    geo_lookup: dict
    manifest: dict
    # Outer-joined counterpart to `combined`: built at load (see _build_combined_outer)
    # so the time-series can show substances with price/purity but no seizure
    # coverage (e.g. Amphetamines), which the inner-joined `combined` drops.
    combined_outer: pd.DataFrame = None
    substance_color_map: dict = field(default_factory=dict)
    subregion_color_map: dict = field(default_factory=dict)

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


def _build_combined_outer(prices, purity, seizures) -> pd.DataFrame:
    """Outer-joined [Country, Substance, Year] frame for the time-series.

    Mirrors the pipeline's inner-joined `build_combined` but joins with
    how='outer', so a substance present in only some sources (e.g. Amphetamines:
    price + purity, no seizures) keeps its rows. Metrics absent for a given
    (Country, Substance, Year) stay NaN - the time-series draws a gap there,
    not a misleading zero. Imputation flags default to False where missing.
    """
    price_avg = (prices.groupby(["Country", "Substance", "Year"])
                 .agg(Typical_USD=("Typical_USD", "mean"),
                      price_imputed=("Typical_USD_is_imputed", "max"))
                 .reset_index())
    purity_avg = (purity.groupby(["Country", "Substance", "Year"])
                  .agg(Typical=("Typical", "mean"),
                       purity_imputed=("Typical_is_imputed", "max"))
                  .reset_index())
    seiz_sum = (seizures.groupby(["Country", "Substance", "Year"])
                .agg(Kilograms=("Kilograms", "sum"),
                     seizure_imputed=("Kilograms_is_imputed", "max"))
                .reset_index())
    keys = ["Country", "Substance", "Year"]
    out = price_avg.merge(purity_avg, on=keys, how="outer")
    out = out.merge(seiz_sum, on=keys, how="outer")

    subregion = prices[["Country", "SubRegion"]].drop_duplicates()
    out = out.merge(subregion, on="Country", how="left")
    for c in ("price_imputed", "purity_imputed", "seizure_imputed"):
        out[c] = out[c].fillna(False).astype(bool)
    out["any_imputed"] = out[
        ["price_imputed", "purity_imputed", "seizure_imputed"]].any(axis=1)
    return out.reset_index(drop=True)


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
    data.combined_outer = _build_combined_outer(data.prices, data.purity,
                                                 data.seizures)
    data.substance_color_map = theme.substance_color_map(
        set(data.combined["Substance"]) | set(data.prices["Substance"])
    )
    data.subregion_color_map = theme.subregion_color_map(
        set(data.prices["SubRegion"].dropna())
    )
    return data
