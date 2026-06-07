"""Smoke tests for the cleaning pipeline.

Run from the dashboard_v2 directory:  python -m pytest pipeline/tests -q
"""
import json

import numpy as np
import pandas as pd
import pytest

from pipeline import config as cfg
from pipeline import correlate, impute, normalize


# --- (a) unit conversion ----------------------------------------------------
def test_unify_prices_kg_to_gram():
    df = pd.DataFrame({
        "Unit": ["Kilogram"], "Typical_USD": [1000.0],
        "Minimum_USD": [1000.0], "Maximum_USD": [2000.0],
    })
    out = normalize.unify_prices(df)
    # 1 kg = 1000 g, so a $1000/kg price is $1/g.
    assert out["Typical_USD"].iloc[0] == pytest.approx(1.0)
    assert out["Maximum_USD"].iloc[0] == pytest.approx(2.0)


def test_unify_prices_compound_unit_prefix():
    df = pd.DataFrame({"Unit": ["10 gram"], "Typical_USD": [100.0],
                       "Minimum_USD": [100.0], "Maximum_USD": [100.0]})
    out = normalize.unify_prices(df)
    assert out["Typical_USD"].iloc[0] == pytest.approx(10.0)


# --- (b) substance taxonomy -------------------------------------------------
def test_substances_in_canonical_set():
    df = pd.DataFrame({"DrugGroup": list(cfg.SUBSTANCE_MAP.keys()) + ["NPS junk"]})
    out = normalize.classify_substances(df)
    assert set(out["Substance"]).issubset(set(cfg.ALL_SUBSTANCE_CATEGORIES))
    assert (out["Substance"] == cfg.OTHER).sum() == 1  # the unknown group


# --- (c) imputation flagging ------------------------------------------------
def test_impute_flags_only_originally_missing():
    df = pd.DataFrame({
        "Country": ["A"] * 4, "Substance": ["Cocaine"] * 4,
        "LevelOfSale": ["Retail"] * 4, "SubRegion": ["X"] * 4,
        "Year": [2019, 2020, 2021, 2022],
        "Typical": [10.0, np.nan, 30.0, 40.0],
        "Minimum": [5.0, 5.0, 5.0, 5.0], "Maximum": [50.0, 50.0, 50.0, 50.0],
    })
    tables = {"prices": df.assign(**{c: 1.0 for c in
              ["Typical_USD", "Minimum_USD", "Maximum_USD"]}),
              "purity": df, "seizures": df.assign(Kilograms=[1.0, 2.0, 3.0, 4.0])}
    out, stats = impute.impute_all(tables)
    purity = out["purity"]
    # The 2020 gap is interpolated to 20 and flagged; the observed rows are not.
    row2020 = purity[purity["Year"] == 2020].iloc[0]
    assert row2020["Typical"] == pytest.approx(20.0)
    assert bool(row2020["Typical_is_imputed"]) is True
    assert purity["Typical_is_imputed"].sum() == 1
    # No imputed cell is left null.
    assert purity.loc[purity["Typical_is_imputed"], "Typical"].notna().all()


def test_seizures_not_median_filled():
    df = pd.DataFrame({
        "Country": ["A", "A"], "Substance": ["Cocaine", "Cocaine"],
        "SubRegion": ["X", "X"], "Year": [2019, 2020],
        "Kilograms": [np.nan, np.nan],
    })
    tables = {"prices": df.assign(LevelOfSale="Retail", Typical_USD=1.0,
              Minimum_USD=1.0, Maximum_USD=1.0),
              "purity": df.assign(LevelOfSale="Retail", Typical=1.0,
              Minimum=1.0, Maximum=1.0),
              "seizures": df}
    out, _ = impute.impute_all(tables)
    # Seizures stay missing (never fabricated) and thus are not flagged imputed.
    assert out["seizures"]["Kilograms"].isna().all()
    assert out["seizures"]["Kilograms_is_imputed"].sum() == 0


# --- (d) lag correlation respects min-n ------------------------------------
def test_lag_min_pairs_enforced():
    # Two paired years only -> below MIN_LAG_PAIRS -> insufficient_n.
    seiz = pd.DataFrame({"Country": ["A"] * 2, "Substance": ["Cocaine"] * 2,
                         "Year": [2019, 2020], "Kilograms": [10.0, 20.0]})
    price = pd.DataFrame({"Country": ["A"] * 2, "Substance": ["Cocaine"] * 2,
                          "Year": [2020, 2021], "Typical_USD": [5.0, 6.0]})
    purity = price.rename(columns={"Typical_USD": "Typical"})
    lag = correlate.lag_correlation(price, purity, seiz)
    country_rows = lag[lag["level"] == "country"]
    assert (country_rows["reason"] == "insufficient_n").all()
    assert country_rows["r"].isna().all()


# --- (e) artifacts exist & are determin, manifest sane ----------------------
def test_artifacts_present_and_valid():
    out_dir = cfg.clean_version_dir()
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        pytest.skip("run `python -m pipeline.build_artifacts` first")
    manifest = json.loads(manifest_path.read_text())
    for name in ["prices", "purity", "seizures", "combined",
                 "inland_margin", "enforcement_metrics", "lag_correlation"]:
        assert (out_dir / f"{name}.parquet").exists()
        assert manifest["row_counts"][name] > 0
    # imputation happened but did not swallow the whole dataset
    p = manifest["imputation"]["prices"]["Typical_USD"]
    assert 0 < p["originally_missing"] < manifest["row_counts"]["prices"]
