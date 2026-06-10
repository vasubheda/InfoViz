import re

import pandas as pd

from . import config as cfg


def rename_countries(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Country"] = df["Country"].map(lambda x: cfg.COUNTRY_MAP.get(x, x))
    return df


def classify_substances(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Substance"] = df["DrugGroup"].map(lambda x: cfg.SUBSTANCE_MAP.get(x, cfg.OTHER))
    return df


def extract_unit_multiplier(unit_str) -> int:
    # pull the leading number, e.g. '10 gram' -> 10
    if pd.isna(unit_str):
        return 1
    match = re.search(r"(\d+)", str(unit_str))
    return int(match.group(1)) if match else 1


def unify_prices(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    price_cols = ["Typical_USD", "Minimum_USD", "Maximum_USD"]
    unit_mult = res["Unit"].apply(extract_unit_multiplier)
    conv_mult = res["Unit"].map(lambda x: cfg.UNIT_CONVERSION.get(str(x), 1))
    total = unit_mult * conv_mult
    for col in price_cols:
        if col in res.columns:
            res[col] = res[col] / total
    return res


def unify_unit_names(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    res["Unit"] = res["Unit"].replace(cfg.UNIT_NAME_MAP)
    return res
