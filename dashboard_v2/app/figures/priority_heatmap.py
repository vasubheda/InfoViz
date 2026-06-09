"""Q5 country x substance enforcement-priority heatmap.

Answers "which drugs should law enforcement focus on, in which countries?" head
on: the full Country x Substance priority matrix, instead of the Q4 dot plot's
single top substance per country. Clicking a cell brushes the rest of the app.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure


@memoize_figure()
def priority_heatmap(data, selection, substances, year_range, height=520):
    df = data.enforcement_metrics
    df = df[df["Substance"].isin(substances) & (df["Substance"] != "Other")]
    if selection.get("countries"):
        df = df[df["Country"].isin(selection["countries"])]
    if len(df) == 0:
        return helpers.empty_fig("No data for selected filters", height)

    hm = df.pivot_table(values="priority_score", index="Country",
                        columns="Substance", aggfunc="mean")
    # Highest-priority markets at the top (row mean over available substances).
    hm = hm.loc[hm.mean(axis=1).sort_values().index]

    countries = list(hm.index)
    subs = list(hm.columns)
    customdata = [[[c, s] for s in subs] for c in countries]

    fig = go.Figure(go.Heatmap(
        z=hm.values, x=subs, y=countries,
        colorscale=theme.SEQUENTIAL, hoverongaps=False,
        customdata=customdata,
        colorbar=dict(title="Priority", thickness=15, len=0.7, x=1.02),
        hovertemplate=("Country: %{customdata[0]}<br>"
                       "Substance: %{customdata[1]}<br>"
                       "Priority: %{z:.3f}<extra></extra>")))

    # Highlight the brushed cell.
    sel_country = selection.get("country")
    sel_sub = selection.get("substance")
    if sel_country in countries and sel_sub in subs:
        ri = countries.index(sel_country)
        ci = subs.index(sel_sub)
        fig.add_shape(type="rect", x0=ci - 0.5, x1=ci + 0.5,
                      y0=ri - 0.5, y1=ri + 0.5,
                      line=dict(color=theme.ACCENT, width=4))

    fig.update_layout(
        title="Enforcement-priority index (country x substance)",
        xaxis_title="Substance", yaxis_title="Country",
        height=height, plot_bgcolor="white",
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=140, r=80, t=50, b=60))
    return fig
