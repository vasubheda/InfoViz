"""Enforcement-priority Cleveland dot plot (Q4/Q5).

Each country's top-scoring substance, ranked by the composite priority index
(high markup + high street price + comparatively low current seizure pressure).
Re-aggregates under the active filters so brushing affects it.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers


def priority_dotplot(data, selection, substances, year_range):
    df = data.enforcement_metrics
    df = df[df["Substance"].isin(substances) & (df["Substance"] != "Other")]
    if selection.get("substance"):
        df = df[df["Substance"] == selection["substance"]]
    if selection.get("countries"):
        df = df[df["Country"].isin(selection["countries"])]
    if selection.get("country"):
        df = df[df["Country"] == selection["country"]]
    if len(df) == 0:
        return helpers.empty_fig("No data for selected filters", 300)

    # Top substance per country, ascending so the highest priority is on top.
    top = df.loc[df.groupby("Country")["priority_score"].idxmax()]
    top = top.sort_values("priority_score", ascending=True)
    colors = [data.substance_color_map.get(s, theme.TOL_MUTED[0])
              for s in top["Substance"]]

    fig = go.Figure()
    for i, row in enumerate(top.itertuples()):
        fig.add_shape(type="line", x0=0, x1=row.priority_score, y0=i, y1=i,
                      line=dict(color="rgba(128,128,128,0.4)", width=1))
    fig.add_trace(go.Scatter(
        x=top["priority_score"], y=top["Country"], mode="markers",
        marker=dict(color=colors, size=11, line=dict(width=1, color="white")),
        text=top["Substance"],
        customdata=top[["Substance", "RelativeMargin", "Typical_USD_Retail"]],
        hovertemplate=("<b>%{y}</b><br>Priority: %{x:.3f}"
                       "<br>Top substance: %{customdata[0]}"
                       "<br>Markup: %{customdata[1]:.0f}%"
                       "<br>Retail: $%{customdata[2]:.1f}/g<extra></extra>")))
    fig.update_layout(
        title="Enforcement-priority index (top substance per country)",
        xaxis_title="Priority score", height=max(320, len(top) * 20),
        margin=dict(l=140, r=30, t=50, b=40),
        xaxis=dict(range=[0, 1.05], gridcolor=theme.GRID),
        yaxis=dict(gridcolor=theme.GRID, tickfont=dict(size=10)),
        plot_bgcolor=theme.PLOT_BG, showlegend=False)
    return fig
