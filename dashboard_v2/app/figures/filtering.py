from dataclasses import dataclass


@dataclass
class Filters:
    substances: list
    year_range: tuple


def empty_selection() -> dict:
    return {"country": None, "countries": None, "substance": None,
            "year": None, "subregion": None}


def apply_filters(df, filters: Filters, selection: dict | None,
                  year_col="Year", substance_col="Substance"):
    selection = selection or empty_selection()
    out = df[
        df[substance_col].isin(filters.substances)
        & (df[substance_col] != "Other")
        & (df[year_col] >= filters.year_range[0])
        & (df[year_col] <= filters.year_range[1])
    ].copy()

    if selection.get("subregion") and "SubRegion" in out.columns:
        out = out[out["SubRegion"] == selection["subregion"]]
    if selection.get("country") and "Country" in out.columns:
        out = out[out["Country"] == selection["country"]]
    if selection.get("countries") and "Country" in out.columns:
        out = out[out["Country"].isin(selection["countries"])]
    if selection.get("year") and year_col in out.columns:
        out = out[out[year_col] == selection["year"]]
    if selection.get("substance") and substance_col in out.columns:
        out = out[out[substance_col] == selection["substance"]]
    return out
