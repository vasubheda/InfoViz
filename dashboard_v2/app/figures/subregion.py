import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# west to east reading order
_SUBREGION_ORDER = [
    "Western and Central Europe",
    "South-Eastern Europe",
    "Eastern Europe",
]

# shorter labels for the single-year bars
_SHORT = {
    "Western and Central Europe": "West &<br>Central",
    "South-Eastern Europe": "South-<br>Eastern",
    "Eastern Europe": "Eastern",
}


def present_subregions(*frames):
    seen = set()
    for f in frames:
        if f is not None and len(f) and "SubRegion" in f.columns:
            seen |= set(f["SubRegion"].dropna().unique())
    return [sr for sr in _SUBREGION_ORDER if sr in seen]


def make_layout(fig, title, height, single_year, **yaxis):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13)),
        height=height, plot_bgcolor=theme.PLOT_BG,
        margin=dict(l=45, r=12, t=40, b=55),
        legend=dict(orientation="h", yanchor="top", y=-0.18,
                    x=0, font=dict(size=8)),
        showlegend=not single_year,
        hovermode="x unified" if not single_year else "closest",
        xaxis=dict(gridcolor=theme.GRID, tickfont=dict(size=9),
                   **({} if single_year else
                      dict(title="Year", type="linear", tickmode="linear",
                           dtick=1, tickformat="d"))),
        yaxis=dict(gridcolor=theme.GRID, rangemode="tozero", **yaxis))
    return fig


@memoize_figure()
def subregion_trends(data, seiz, comb_outer, single_year, height=260):
    subregions = present_subregions(seiz, comb_outer)
    if not subregions:
        empty = helpers.empty_fig("No subregion data", height)
        return empty, empty, empty

    fig_seiz = seizures(data, seiz, subregions, single_year, height)
    fig_price = level(data, comb_outer, "Typical_USD", subregions, single_year,
                      height, "Avg Price by Subregion (USD/g)",
                      "$%{y:,.2f}/g", tickprefix="$")
    fig_purity = level(data, comb_outer, "Typical", subregions, single_year,
                       height, "Avg Purity by Subregion (%)",
                       "%{y:.1f}%", ticksuffix="%")
    return fig_seiz, fig_price, fig_purity


def color(data, sr):
    return data.subregion_color_map.get(sr, theme.TOL_MUTED[0])


def seizures(data, seiz, subregions, single_year, height):
    grp = (seiz.groupby(["SubRegion", "Year"])["Kilograms"].sum() / 1000)
    if single_year:
        fig = go.Figure(go.Bar(
            x=[_SHORT[s] for s in subregions],
            y=[float(grp.loc[s].sum()) if s in grp.index.get_level_values(0)
               else 0.0 for s in subregions],
            marker_color=[color(data, s) for s in subregions],
            hovertemplate="%{x}: %{y:,.1f} t<extra></extra>"))
        return make_layout(fig, "Seizures by Subregion (t)", height, True)

    fig = go.Figure()
    for sr in subregions:
        if sr not in grp.index.get_level_values(0):
            continue
        s = grp.loc[sr].sort_index()
        fig.add_scatter(x=s.index, y=s.cumsum(), mode="lines+markers", name=sr,
                        line=dict(width=2, color=color(data, sr)),
                        marker=dict(size=7, line=dict(width=2, color="white"),
                                    color=color(data, sr)),
                        hovertemplate=f"%{{y:,.1f}} t<extra>{sr}</extra>")
    return make_layout(fig, "Cumulative Seizures by Subregion (t)", height, False)


def level(data, comb, col, subregions, single_year, height, title, hover,
          **yaxis):
    present = comb.dropna(subset=[col]) if col in comb.columns else comb.iloc[:0]
    grp = present.groupby(["SubRegion", "Year"])[col].mean()
    if single_year:
        fig = go.Figure(go.Bar(
            x=[_SHORT[s] for s in subregions],
            y=[float(grp.loc[s].mean()) if s in grp.index.get_level_values(0)
               else None for s in subregions],
            marker_color=[color(data, s) for s in subregions],
            hovertemplate="%{x}: " + hover + "<extra></extra>"))
        return make_layout(fig, title, height, True, **yaxis)

    fig = go.Figure()
    for sr in subregions:
        if sr not in grp.index.get_level_values(0):
            continue
        s = grp.loc[sr].sort_index()
        fig.add_scatter(x=s.index, y=s.values, mode="lines+markers", name=sr,
                        line=dict(width=2, color=color(data, sr)),
                        marker=dict(size=7, line=dict(width=2, color="white"),
                                    color=color(data, sr)),
                        hovertemplate=hover + f"<extra>{sr}</extra>")
    return make_layout(fig, title, height, False, **yaxis)
