"""Feature engineering: price spreads, inland retail-wholesale margins, the
3-way combined table, and the composite enforcement-priority index.
"""
import numpy as np
import pandas as pd

from . import config as cfg


def add_spreads(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.copy()
    df["Spread_USD"] = df["Maximum_USD"] - df["Minimum_USD"]
    df["Spread_rel"] = df["Spread_USD"] / df["Typical_USD"]
    return df


def inland_margin(prices: pd.DataFrame) -> pd.DataFrame:
    """Retail-vs-wholesale price gap per (Country, Substance)."""
    retail = (
        prices[prices["LevelOfSale"] == "Retail"]
        .groupby(["Country", "Substance"])["Typical_USD"].mean().reset_index()
    )
    wholesale = (
        prices[prices["LevelOfSale"] == "Wholesale"]
        .groupby(["Country", "Substance"])["Typical_USD"].mean().reset_index()
    )
    m = retail.merge(
        wholesale, on=["Country", "Substance"], how="inner",
        suffixes=("_Retail", "_Wholesale"),
    )
    m["Margin"] = m["Typical_USD_Retail"] - m["Typical_USD_Wholesale"]
    m["RelativeMargin"] = (m["Margin"] / m["Typical_USD_Wholesale"]) * 100
    return m.dropna(subset=["RelativeMargin"]).reset_index(drop=True)


def build_combined(prices, purity, seizures) -> pd.DataFrame:
    """3-way inner join on [Country, Substance, Year] + attached SubRegion.

    Imputation flags from each source are carried so the app can mark which
    encoding (price / purity / seizure) of a point rests on imputed data.
    """
    price_avg = (
        prices.groupby(["Country", "Substance", "Year"])
        .agg(Typical_USD=("Typical_USD", "mean"),
             price_imputed=("Typical_USD_is_imputed", "max"))
        .reset_index()
    )
    purity_avg = (
        purity.groupby(["Country", "Substance", "Year"])
        .agg(Typical=("Typical", "mean"),
             purity_imputed=("Typical_is_imputed", "max"))
        .reset_index()
    )
    seiz_sum = (
        seizures.groupby(["Country", "Substance", "Year"])
        .agg(Kilograms=("Kilograms", "sum"),
             seizure_imputed=("Kilograms_is_imputed", "max"))
        .reset_index()
    )
    combined = price_avg.merge(purity_avg, on=["Country", "Substance", "Year"], how="inner")
    combined = combined.merge(seiz_sum, on=["Country", "Substance", "Year"], how="inner")
    combined = combined.dropna(subset=["Typical_USD", "Typical", "Kilograms"])

    subregion = prices[["Country", "SubRegion"]].drop_duplicates()
    combined = combined.merge(subregion, on="Country", how="left")
    for c in ("price_imputed", "purity_imputed", "seizure_imputed"):
        combined[c] = combined[c].fillna(False).astype(bool)
    combined["any_imputed"] = combined[
        ["price_imputed", "purity_imputed", "seizure_imputed"]
    ].any(axis=1)
    return combined.reset_index(drop=True)


def _norm(s: pd.Series) -> pd.Series:
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


def enforcement_metrics(margin: pd.DataFrame, seizures: pd.DataFrame) -> pd.DataFrame:
    """Composite enforcement-priority index per (Country, Substance).

    Reframed (not a trafficker guide): high score = a market where a high
    retail-vs-wholesale markup and high street price coincide with comparatively
    *low* current seizure pressure - i.e. a market that interdiction is not yet
    reaching. The full table is kept so the app can re-aggregate under filters.
    """
    seiz = (
        seizures.groupby(["Country", "Substance"])["Kilograms"].sum().reset_index()
    )
    m = margin.merge(seiz, on=["Country", "Substance"], how="left")
    m["Kilograms"] = m["Kilograms"].fillna(0)
    w = cfg.PRIORITY_WEIGHTS
    m["priority_score"] = (
        _norm(m["RelativeMargin"]) * w["margin"]
        + _norm(m["Typical_USD_Retail"]) * w["retail"]
        + (1 - _norm(np.log1p(m["Kilograms"]))) * w["inverse_seizure"]
    )
    return m.sort_values("priority_score", ascending=False).reset_index(drop=True)
