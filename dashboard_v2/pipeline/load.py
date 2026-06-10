import pandas as pd

from . import config as cfg


def read(path, sheet) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)


def load_raw() -> dict[str, pd.DataFrame]:
    prices = read(cfg.PRICES_XLSX, cfg.PRICES_SHEET).rename(
        columns={"Country/Territory": "Country"}
    )
    purity = read(cfg.PRICES_XLSX, cfg.PURITY_SHEET).rename(
        columns={"Country/Territory": "Country"}
    )
    seizures = read(cfg.SEIZURES_XLSX, cfg.SEIZURES_SHEET).rename(
        columns={"Reference year": "Year"}
    )

    out = {}
    for name, df in [("prices", prices), ("purity", purity), ("seizures", seizures)]:
        df = df[df["Region"] == cfg.REGION].reset_index(drop=True)
        out[name] = df
    return out
