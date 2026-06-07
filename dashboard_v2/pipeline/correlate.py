"""Within-country 1-year lagged correlation (research question 1).

For each (Country, Substance) we pair seizure volume in year Y against street
price / purity in year Y+1, *within the same country*, then aggregate the
per-country Pearson r across countries with a Fisher-z weighted mean. This
avoids the ecological/confounded pooling of all countries into one correlation.
"""
import numpy as np
import pandas as pd
from scipy import stats

from . import config as cfg


def _per_country(seizures, target_df, target_col):
    """Yield per-(Country, Substance) lag correlations for one target column."""
    seiz = (
        seizures.groupby(["Country", "Substance", "Year"])["Kilograms"]
        .sum().reset_index()
    )
    seiz_lag = seiz.copy()
    seiz_lag["Year"] = seiz_lag["Year"] + 1  # seizures(Y) -> aligns to year Y+1

    tgt = (
        target_df.groupby(["Country", "Substance", "Year"])[target_col]
        .mean().reset_index()
    )
    paired = seiz_lag.merge(tgt, on=["Country", "Substance", "Year"], how="inner")

    rows = []
    for (country, substance), g in paired.groupby(["Country", "Substance"]):
        n = len(g)
        if n < cfg.MIN_LAG_PAIRS or g["Kilograms"].std() == 0 or g[target_col].std() == 0:
            rows.append({
                "level": "country", "Country": country, "Substance": substance,
                "target": target_col, "r": np.nan, "p": np.nan, "n": n,
                "reason": "insufficient_n" if n < cfg.MIN_LAG_PAIRS else "no_variance",
            })
            continue
        r, p = stats.pearsonr(g["Kilograms"], g[target_col])
        rows.append({
            "level": "country", "Country": country, "Substance": substance,
            "target": target_col, "r": r, "p": p, "n": n, "reason": "",
        })
    return pd.DataFrame(rows)


def _aggregate(per_country: pd.DataFrame) -> pd.DataFrame:
    """Fisher-z, sample-size-weighted mean of per-country r, per Substance/target."""
    out = []
    valid = per_country.dropna(subset=["r"])
    for (substance, target), g in valid.groupby(["Substance", "target"]):
        # Fisher z-transform; weight by (n - 3), the variance-stabilised weight.
        z = np.arctanh(g["r"].clip(-0.999, 0.999))
        w = (g["n"] - 3).clip(lower=1)
        z_mean = np.average(z, weights=w)
        r_agg = np.tanh(z_mean)
        # 95% CI on the weighted z-mean -> back-transform.
        se = 1.0 / np.sqrt(w.sum())
        lo, hi = np.tanh(z_mean - 1.96 * se), np.tanh(z_mean + 1.96 * se)
        n_sig = int((g["p"] < cfg.SIGNIFICANCE_ALPHA).sum())
        out.append({
            "level": "substance_aggregate", "Country": None, "Substance": substance,
            "target": target, "r": r_agg, "p": np.nan,
            "n": int(g["n"].sum()), "n_countries": int(len(g)),
            "n_significant": n_sig, "ci_low": lo, "ci_high": hi, "reason": "",
        })
    return pd.DataFrame(out)


def lag_correlation(prices, purity, seizures) -> pd.DataFrame:
    """Combined per-country + substance-aggregate table for price and purity."""
    frames = []
    for tdf, tcol in [(prices, "Typical_USD"), (purity, "Typical")]:
        pc = _per_country(seizures, tdf, tcol)
        frames.append(pc)
        frames.append(_aggregate(pc))
    result = pd.concat(frames, ignore_index=True)
    # Ensure aggregate-only columns exist on country rows too.
    for col in ("n_countries", "n_significant", "ci_low", "ci_high"):
        if col not in result.columns:
            result[col] = np.nan
    return result
