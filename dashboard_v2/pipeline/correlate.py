import numpy as np
import pandas as pd
from scipy import stats

from . import config as cfg


def per_country_corr(seizures, target_df, target_col):
    seiz = (
        seizures.groupby(["Country", "Substance", "Year"])["Kilograms"]
        .sum().reset_index()
    )
    seiz_lag = seiz.copy()
    seiz_lag["Year"] = seiz_lag["Year"] + 1  # seizures(Y) aligns to year Y+1

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


def aggregate(per_country: pd.DataFrame) -> pd.DataFrame:
    # fisher-z, sample-weighted mean of per-country r
    out = []
    valid = per_country.dropna(subset=["r"])
    for (substance, target), g in valid.groupby(["Substance", "target"]):
        z = np.arctanh(g["r"].clip(-0.999, 0.999))
        w = (g["n"] - 3).clip(lower=1)
        z_mean = np.average(z, weights=w)
        r_agg = np.tanh(z_mean)
        # 95% CI on the weighted z-mean, back-transformed
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
    frames = []
    for tdf, tcol in [(prices, "Typical_USD"), (purity, "Typical")]:
        pc = per_country_corr(seizures, tdf, tcol)
        frames.append(pc)
        frames.append(aggregate(pc))
    result = pd.concat(frames, ignore_index=True)
    # make sure aggregate-only columns exist on country rows too
    for col in ("n_countries", "n_significant", "ci_low", "ci_high"):
        if col not in result.columns:
            result[col] = np.nan
    return result
