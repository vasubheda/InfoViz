"""Missing-value imputation with provenance flagging.

The proposal commits to imputing sporadic missing values *while flagging them as
originally missing*. We honour that here:

  * Method A - temporal linear interpolation over ``Year`` within each
    (Country, Substance[, LevelOfSale]) group, internal gaps only. A missing
    2021 between an observed 2020 and 2022 is the most defensible fill.
  * Method B - group-median fallback for leading/trailing gaps that
    interpolation cannot reach: (Country, Substance) median, then
    (SubRegion, Substance) median.
  * Cells with no support even at SubRegion level are left NaN (never
    fabricated).

Every filled cell sets the column's ``<col>_is_imputed`` flag to True. Seizure
volumes are intentionally NOT interpolated - a missing seizure-year is not a
true zero - they are only flagged as originally missing.
"""
import pandas as pd

# Columns we impute per table.
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
        "interpolate": False,  # missing != zero; flag only
        "median_fill": False,  # never fabricate a seizure volume
    },
}


def _interpolate_within_groups(df: pd.DataFrame, cols: list[str],
                               group: list[str]) -> pd.DataFrame:
    """Linear-interpolate ``cols`` over Year within each ``group``, internal
    gaps only. Sorting the whole frame by (group, Year) up front lets us use a
    groupby ``transform`` (index-aligned, per-group, in Year order) instead of
    a ``groupby.apply`` - the latter's ``include_groups`` arg was removed in
    pandas 3.0.
    """
    df = df.sort_values(group + ["Year"]).reset_index(drop=True)
    for c in cols:
        df[c] = df.groupby(group, sort=False)[c].transform(
            lambda s: s.interpolate(method="linear", limit_area="inside"))
    return df


def _median_fill(df: pd.DataFrame, col: str, keys: list[str]) -> pd.Series:
    return df.groupby(keys)[col].transform("median")


def impute_table(df: pd.DataFrame, name: str) -> tuple[pd.DataFrame, dict]:
    """Return (imputed_df, stats). Adds one ``<col>_is_imputed`` flag per column."""
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

    # Method A: temporal interpolation within group (price/purity only).
    if plan["interpolate"]:
        df = _interpolate_within_groups(df, cols, group)
        for col in cols:
            if col not in df.columns:
                continue
            filled = df[col].notna() & _was_missing(df, col, stats)
            stats[col]["interpolated"] = int(filled.sum())

    # Method B: group-median fallback (skipped where median_fill is False, e.g.
    # seizures, where a fabricated volume would be misleading).
    median_fill = plan.get("median_fill", True)
    for col in (cols if median_fill else []):
        if col not in df.columns:
            continue
        # (Country, Substance) median
        before = df[col].isna()
        cs = _median_fill(df, col, ["Country", "Substance"])
        df.loc[before, col] = cs[before]
        stats[col]["median_country_substance"] = int((before & df[col].notna()).sum())
        # (SubRegion, Substance) median for whatever remains
        before2 = df[col].isna()
        srs = _median_fill(df, col, ["SubRegion", "Substance"])
        df.loc[before2, col] = srs[before2]
        stats[col]["median_subregion_substance"] = int((before2 & df[col].notna()).sum())

    # Record residual missingness for every column (covers median_fill=False).
    for col in cols:
        if col in df.columns:
            stats[col]["left_missing"] = int(df[col].isna().sum())

    # Build the per-column imputed flag: True where originally missing but now present.
    for col in cols:
        if col not in df.columns:
            continue
        # Recompute against the original frame passed in via stats bookkeeping.
        df[f"{col}_is_imputed"] = _imputed_flag(df, col, stats)

    return df, stats


# --- helpers that reconstruct "was missing" against the running state --------
# We track original missingness by stashing it the first time we see the column.
_ORIG_KEY = "__orig_missing__"


def _was_missing(df, col, stats):
    key = f"{_ORIG_KEY}{col}"
    if key not in df.columns:
        # original missingness already lost after interpolation; recompute from
        # the recorded count is not possible per-row, so we snapshot earlier.
        return pd.Series(False, index=df.index)
    return df[key]


def _imputed_flag(df, col, stats):
    key = f"{_ORIG_KEY}{col}"
    if key in df.columns:
        flag = df[key] & df[col].notna()
        return flag
    return pd.Series(False, index=df.index)


def impute_all(tables: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    """Impute price/purity/seizure tables; return (tables, per-table stats)."""
    out, all_stats = {}, {}
    for name in ("prices", "purity", "seizures"):
        df = tables[name].copy()
        # Snapshot original missingness BEFORE any fill so flags are exact.
        for col in IMPUTE_PLAN[name]["cols"]:
            if col in df.columns:
                df[f"{_ORIG_KEY}{col}"] = df[col].isna()
        imp, stats = impute_table(df, name)
        # Drop the snapshot helper columns.
        imp = imp[[c for c in imp.columns if not c.startswith(_ORIG_KEY)]]
        out[name] = imp
        all_stats[name] = stats
    return out, all_stats
