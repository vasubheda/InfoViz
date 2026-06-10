import pandas as pd

# columns we impute per table
IMPUTE_PLAN = {
    "prices": {
        "cols": ["Typical_USD", "Minimum_USD", "Maximum_USD"],
        "group": ["Country", "Substance", "LevelOfSale"],
        "interpolate": True,
    },
    "purity": {
        "cols": ["Typical", "Minimum", "Maximum"],
        "group": ["Country", "Substance", "LevelOfSale"],
        "interpolate": True,
    },
    "seizures": {
        "cols": ["Kilograms"],
        "group": ["Country", "Substance"],
        "interpolate": False,  # missing != zero, flag only
        "median_fill": False,  # never fabricate a seizure volume
    },
}


def interpolate_within_groups(df: pd.DataFrame, cols: list[str],
                              group: list[str]) -> pd.DataFrame:
    # linear interpolate over Year within each group, internal gaps only
    df = df.sort_values(group + ["Year"]).reset_index(drop=True)
    for c in cols:
        df[c] = df.groupby(group, sort=False)[c].transform(
            lambda s: s.interpolate(method="linear", limit_area="inside"))
    return df


def fill_with_median(df: pd.DataFrame, col: str, keys: list[str]) -> pd.Series:
    return df.groupby(keys)[col].transform("median")


def impute_table(df: pd.DataFrame, name: str) -> tuple[pd.DataFrame, dict]:
    plan = IMPUTE_PLAN[name]
    cols, group = plan["cols"], plan["group"]
    df = df.copy()
    stats: dict[str, dict] = {}

    for col in cols:
        if col not in df.columns:
            continue
        orig_missing = df[col].isna()
        stats[col] = {
            "originally_missing": int(orig_missing.sum()),
            "interpolated": 0,
            "median_country_substance": 0,
            "median_subregion_substance": 0,
            "left_missing": 0,
        }

    # method A: temporal interpolation within group (price/purity only)
    if plan["interpolate"]:
        df = interpolate_within_groups(df, cols, group)
        for col in cols:
            if col not in df.columns:
                continue
            filled = df[col].notna() & was_missing(df, col, stats)
            stats[col]["interpolated"] = int(filled.sum())

    # method B: group-median fallback (skipped for seizures)
    median_fill = plan.get("median_fill", True)
    for col in (cols if median_fill else []):
        if col not in df.columns:
            continue
        # (Country, Substance) median
        before = df[col].isna()
        cs = fill_with_median(df, col, ["Country", "Substance"])
        df.loc[before, col] = cs[before]
        stats[col]["median_country_substance"] = int((before & df[col].notna()).sum())
        # (SubRegion, Substance) median for whatever remains
        before2 = df[col].isna()
        srs = fill_with_median(df, col, ["SubRegion", "Substance"])
        df.loc[before2, col] = srs[before2]
        stats[col]["median_subregion_substance"] = int((before2 & df[col].notna()).sum())

    # residual missingness per column
    for col in cols:
        if col in df.columns:
            stats[col]["left_missing"] = int(df[col].isna().sum())

    # per-column imputed flag: True where originally missing but now present
    for col in cols:
        if col not in df.columns:
            continue
        df[f"{col}_is_imputed"] = imputed_flag(df, col, stats)

    return df, stats


# we stash original missingness the first time we see the column
_ORIG_KEY = "__orig_missing__"


def was_missing(df, col, stats):
    key = f"{_ORIG_KEY}{col}"
    if key not in df.columns:
        return pd.Series(False, index=df.index)
    return df[key]


def imputed_flag(df, col, stats):
    key = f"{_ORIG_KEY}{col}"
    if key in df.columns:
        flag = df[key] & df[col].notna()
        return flag
    return pd.Series(False, index=df.index)


def impute_all(tables: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    out, all_stats = {}, {}
    for name in ("prices", "purity", "seizures"):
        df = tables[name].copy()
        # snapshot original missingness before any fill
        for col in IMPUTE_PLAN[name]["cols"]:
            if col in df.columns:
                df[f"{_ORIG_KEY}{col}"] = df[col].isna()
        imp, stats = impute_table(df, name)
        # drop the snapshot helper columns
        imp = imp[[c for c in imp.columns if not c.startswith(_ORIG_KEY)]]
        out[name] = imp
        all_stats[name] = stats
    return out, all_stats
