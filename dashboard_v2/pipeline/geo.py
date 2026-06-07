"""Geographic join helpers.

We never index the geodataframe positionally in the app. Instead we build an
explicit ``Country -> geojson NAME`` lookup at build time and validate that
every data country either matches a geojson feature or is recorded as unmatched
in the manifest.
"""
import geopandas as gpd

from . import config as cfg


def load_geo() -> gpd.GeoDataFrame:
    return gpd.read_file(cfg.GEOJSON_PATH)


def validate_country_join(countries: set[str], geo: gpd.GeoDataFrame) -> dict:
    """Return {'matched': {country: NAME}, 'unmatched': [country, ...]}.

    Because ``rename_countries`` already aligns data names to geojson ``NAME``,
    the lookup is identity for matched countries; the value of this step is the
    explicit, persisted record of which countries have no map geometry.
    """
    names = set(geo["NAME"])
    matched = {c: c for c in sorted(countries) if c in names}
    unmatched = sorted(c for c in countries if c not in names)
    return {"matched": matched, "unmatched": unmatched}
