"""Raw data intake: read the three UNODC sheets, apply defensive renames, and
filter to the European region. No feature engineering happens here.
"""
import pandas as pd

from . import config as cfg


def _read(path, sheet) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)


def load_raw() -> dict[str, pd.DataFrame]:
    """Return raw price / purity / seizure frames, region-filtered to Europe.

    Column renames are idempotent: the source sheets sometimes already use the
    canonical names (``Country`` / ``Year``), so ``rename`` is a no-op there.
    """
    prices = _read(cfg.PRICES_XLSX, cfg.PRICES_SHEET).rename(
        columns={"Country/Territory": "Country"}
    )
    purity = _read(cfg.PRICES_XLSX, cfg.PURITY_SHEET).rename(
        columns={"Country/Territory": "Country"}
    )
    seizures = _read(cfg.SEIZURES_XLSX, cfg.SEIZURES_SHEET).rename(
        columns={"Reference year": "Year"}
    )

    out = {}
    for name, df in [("prices", prices), ("purity", purity), ("seizures", seizures)]:
        df = df[df["Region"] == cfg.REGION].reset_index(drop=True)
        out[name] = df
    return out
