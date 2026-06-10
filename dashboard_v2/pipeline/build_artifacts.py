"""Pipeline orchestrator.

    python -m pipeline.build_artifacts [--version N]

Runs load -> normalise -> impute -> features -> correlate and writes versioned
parquet artifacts plus a manifest.json describing the build. Idempotent; never
mutates the raw inputs.
"""
import argparse
import hashlib
import json

import pandas as pd

from . import config as cfg
from . import correlate, features, geo, load, normalize


def _hash_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def run(version: int = cfg.ARTIFACT_VERSION) -> dict:
    # 1-3: load, region filter, rename countries, classify substances
    raw = load.load_raw()
    tables = {}
    for name, df in raw.items():
        df = normalize.rename_countries(df)
        df = normalize.classify_substances(df)
        tables[name] = df

    # 4: geo validation (explicit Country -> NAME lookup, recorded unmatched)
    geo_gdf = geo.load_geo()
    all_countries = set()
    for df in tables.values():
        all_countries |= set(df["Country"].dropna().unique())
    geo_join = geo.validate_country_join(all_countries, geo_gdf)

    # 5-6: unify prices then unit names (prices only)
    tables["prices"] = normalize.unify_unit_names(
        normalize.unify_prices(tables["prices"].dropna(subset=["Unit"]))
    )

    # 7: imputation + flagging (snapshot-based exact flags)
    from . import impute
    tables, impute_stats = impute.impute_all(tables)

    # 8: features
    prices = features.add_spreads(tables["prices"])
    purity = tables["purity"]
    seizures = tables["seizures"]
    margin = features.inland_margin(prices)
    combined = features.build_combined(prices, purity, seizures)
    enforcement = features.enforcement_metrics(margin, seizures)

    # 9: within-country lagged correlation ()
    lag = correlate.lag_correlation(prices, purity, seizures)

    # 10: write artifacts
    out_dir = cfg.clean_version_dir(version)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "prices": prices, "purity": purity, "seizures": seizures,
        "combined": combined, "inland_margin": margin,
        "enforcement_metrics": enforcement, "lag_correlation": lag,
    }
    for name, df in artifacts.items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)

    # persist the geo name lookup so the app never indexes positionally
    with open(out_dir / "geo_lookup.json", "w") as f:
        json.dump(geo_join, f, indent=2)

    manifest = {
        "artifact_version": version,
        "region": cfg.REGION,
        "substances": cfg.ALL_SUBSTANCE_CATEGORIES,
        "source_hashes": {
            "prices_xlsx": _hash_file(cfg.PRICES_XLSX),
            "seizures_xlsx": _hash_file(cfg.SEIZURES_XLSX),
            "geojson": _hash_file(cfg.GEOJSON_PATH),
        },
        "row_counts": {k: int(len(v)) for k, v in artifacts.items()},
        "imputation": impute_stats,
        "geo_unmatched_countries": geo_join["unmatched"],
        "lag_params": {
            "min_pairs": cfg.MIN_LAG_PAIRS,
            "alpha": cfg.SIGNIFICANCE_ALPHA,
            "method": "within-country seizures(Y) vs target(Y+1); "
                      "Fisher-z sample-weighted aggregate across countries",
        },
        "priority_weights": cfg.PRIORITY_WEIGHTS,
    }
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main():
    ap = argparse.ArgumentParser(description="Build cleaned drug-market artifacts")
    ap.add_argument("--version", type=int, default=cfg.ARTIFACT_VERSION)
    args = ap.parse_args()
    manifest = run(args.version)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
