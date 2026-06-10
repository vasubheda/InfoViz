"""Subregion trend charts for the Overview tab.

The KPI bars and the substance time-series above colour by *substance*; this row
recolours the same three core metrics (seizures, price, purity) by *subregion*,
so the three subregion colours (see theme.subregion_color_map) recur across the
whole row — which is what justifies having a dedicated subregion palette.

When a year *range* is selected each chart is a line per subregion; when a single
year is selected there is no trend to draw, so each falls back to a grouped bar
of that year's value per subregion. Seizures accumulate (a flow), so their line
is the cumulative total seized to date; price and purity are levels, so theirs is
the yearly average (not cumulative).

Like the other Overview builders these are pure, memoized functions consuming the
already-filtered frames, so they respect the global filters and brushing.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# West -> East reading order, independent of the alphabetical colour-map order.
_SUBREGION_ORDER = [
    "Western and Central Europe",
    "South-Eastern Europe",
    "Eastern Europe",
]

# Shorter labels for the single-year bar x-axis (narrow md=4 columns).
_SHORT = {
    "Western and Central Europe": "West &<br>Central",
    "South-Eastern Europe": "South-<br>Eastern",
    "Eastern Europe": "Eastern",
}


def _present_subregions(*frames):
    """Subregions (in reading order) appearing in any of the given frames."""
    seen = set()
    for f in frames:
        if f is not None and len(f) and "SubRegion" in f.columns:
            seen |= set(f["SubRegion"].dropna().unique())
    return [sr for sr in _SUBREGION_ORDER if sr in seen]


def _layout(fig, title, height, single_year, **yaxis):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13)),
        height=height, plot_bgcolor=theme.PLOT_BG,
        margin=dict(l=45, r=12, t=40, b=55),
        legend=dict(orientation="h", yanchor="top", y=-0.18,
                    x=0, font=dict(size=8)),
        showlegend=not single_year,  # bars are self-labelled by the x-axis
        hovermode="x unified" if not single_year else "closest",
        xaxis=dict(gridcolor=theme.GRID, tickfont=dict(size=9),
                   **({} if single_year else
                      dict(title="Year", type="linear", tickmode="linear",
                           dtick=1, tickformat="d"))),
        yaxis=dict(gridcolor=theme.GRID, rangemode="tozero", **yaxis))
    return fig


@memoize_figure()
def subregion_trends(data, seiz, comb_outer, single_year, height=260):
    """Return (cumulative-seizures, avg-price, avg-purity) figures by subregion.

    ``seiz`` is the filtered seizures frame; ``comb_outer`` the filtered outer
    time-series frame (price/purity per country-substance-year). ``single_year``
    switches every chart from a line to a grouped bar.
    """
    subregions = _present_subregions(seiz, comb_outer)
    if not subregions:
        empty = helpers.empty_fig("No subregion data", height)
        return empty, empty, empty

    fig_seiz = _seizures(data, seiz, subregions, single_year, height)
    fig_price = _level(data, comb_outer, "Typical_USD", subregions, single_year,
                       height, "Avg Price by Subregion (USD/g)",
                       "$%{y:,.2f}/g", tickprefix="$")
    fig_purity = _level(data, comb_outer, "Typical", subregions, single_year,
                        height, "Avg Purity by Subregion (%)",
                        "%{y:.1f}%", ticksuffix="%")
    return fig_seiz, fig_price, fig_purity


def _color(data, sr):
    return data.subregion_color_map.get(sr, theme.TOL_MUTED[0])


def _seizures(data, seiz, subregions, single_year, height):
    """Cumulative seizures (t) per subregion over time (bar of totals if 1 yr)."""
    grp = (seiz.groupby(["SubRegion", "Year"])["Kilograms"].sum() / 1000)
    if single_year:
        fig = go.Figure(go.Bar(
            x=[_SHORT[s] for s in subregions],
            y=[float(grp.loc[s].sum()) if s in grp.index.get_level_values(0)
               else 0.0 for s in subregions],
            marker_color=[_color(data, s) for s in subregions],
            hovertemplate="%{x}: %{y:,.1f} t<extra></extra>"))
        return _layout(fig, "Seizures by Subregion (t)", height, True)

    fig = go.Figure()
    for sr in subregions:
        if sr not in grp.index.get_level_values(0):
            continue
        s = grp.loc[sr].sort_index()
        fig.add_scatter(x=s.index, y=s.cumsum(), mode="lines+markers", name=sr,
                        line=dict(width=2, color=_color(data, sr)),
                        marker=dict(size=7, line=dict(width=2, color="white"),
                                    color=_color(data, sr)),
                        hovertemplate=f"%{{y:,.1f}} t<extra>{sr}</extra>")
    return _layout(fig, "Cumulative Seizures by Subregion (t)", height, False)


def _level(data, comb, col, subregions, single_year, height, title, hover,
           **yaxis):
    """Yearly mean of a level metric (price / purity) per subregion."""
    present = comb.dropna(subset=[col]) if col in comb.columns else comb.iloc[:0]
    grp = present.groupby(["SubRegion", "Year"])[col].mean()
    if single_year:
        fig = go.Figure(go.Bar(
            x=[_SHORT[s] for s in subregions],
            y=[float(grp.loc[s].mean()) if s in grp.index.get_level_values(0)
               else None for s in subregions],
            marker_color=[_color(data, s) for s in subregions],
            hovertemplate="%{x}: " + hover + "<extra></extra>"))
        return _layout(fig, title, height, True, **yaxis)

    fig = go.Figure()
    for sr in subregions:
        if sr not in grp.index.get_level_values(0):
            continue
        s = grp.loc[sr].sort_index()
        fig.add_scatter(x=s.index, y=s.values, mode="lines+markers", name=sr,
                        line=dict(width=2, color=_color(data, sr)),
                        marker=dict(size=7, line=dict(width=2, color="white"),
                                    color=_color(data, sr)),
                        hovertemplate=hover + f"<extra>{sr}</extra>")
    return _layout(fig, title, height, False, **yaxis)
