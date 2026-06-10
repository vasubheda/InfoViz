import geopandas as gpd

from . import config as cfg


def load_geo() -> gpd.GeoDataFrame:
    return gpd.read_file(cfg.GEOJSON_PATH)


def validate_country_join(countries: set[str], geo: gpd.GeoDataFrame) -> dict:
    # rename_countries already aligns names, so matched is identity
    names = set(geo["NAME"])
    matched = {c: c for c in sorted(countries) if c in names}
    unmatched = sorted(c for c in countries if c not in names)
    return {"matched": matched, "unmatched": unmatched}
