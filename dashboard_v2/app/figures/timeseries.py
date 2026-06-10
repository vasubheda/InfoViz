import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# column, transform, label, imputed-flag column, aggregation
METRICS = [
    ("Kilograms", lambda x: x / 1000, "Seizures (t)", "seizure_imputed", "sum"),
    ("Typical_USD", lambda x: x, "Average Price (USD/g)", "price_imputed", "mean"),
    ("Typical", lambda x: x, "Average Purity (%)", "purity_imputed", "mean"),
]


@memoize_figure()
def timeseries_single(data, filtered_combined, selection, metric_index, height=260):
    if len(filtered_combined) == 0:
        return helpers.empty_fig("No data for selected filters", height)

    col, transform, y_label, imp_col, agg = METRICS[metric_index]

    cmap = {s: data.substance_color_map[s]
            for s in filtered_combined["Substance"].unique()
            if s in data.substance_color_map}

    present = filtered_combined.dropna(subset=[col])
    grouped = (present.groupby(["Year", "Substance"])
               .agg(val=(col, agg), imp=(imp_col, "max")).reset_index())
    grouped["Value"] = transform(grouped["val"])
    grouped["Year"] = grouped["Year"].astype(int)

    years = sorted(grouped["Year"].unique())
    substances = list(grouped["Substance"].unique())

    def traces_for_years(up_to_years):
        traces = []
        for substance in substances:
            color = cmap.get(substance, theme.TOL_MUTED[0])
            g = grouped[(grouped["Substance"] == substance)
                        & (grouped["Year"].isin(up_to_years))].sort_values("Year")
            # hollow markers flag imputed (estimated) points; the outline keeps
            # the substance colour, the fill drops to white when imputed
            imp = g["imp"].tolist()
            fill = ["white" if i else color for i in imp]
            note = [" · imputed (estimated)" if i else "" for i in imp]
            traces.append(go.Scatter(
                x=g["Year"], y=g["Value"], mode="lines+markers", name=substance,
                legendgroup=substance,
                line=dict(width=2, color=color),
                marker=dict(size=7, line=dict(width=2, color=color), color=fill),
                customdata=note,
                hovertemplate=f"{y_label}: %{{y:.2f}}%{{customdata}}"
                              f"<extra>{substance}</extra>"))
        return traces

    # start with all years shown
    initial_traces = traces_for_years(years)

    # one frame per year, revealed cumulatively
    frames = [
        go.Frame(data=traces_for_years(years[:i + 1]), name=str(y))
        for i, y in enumerate(years)
    ]

    fig = go.Figure(data=initial_traces, frames=frames)

    if selection.get("year"):
        fig.add_vline(x=selection["year"], line_dash="dash",
                      line_color=theme.ACCENT, line_width=2)

    x_min, x_max = min(years), max(years)
    fig.update_layout(
        height=height, plot_bgcolor=theme.PLOT_BG,
        title=dict(text=y_label, font=dict(size=13)),
        margin=dict(l=45, r=12, t=40, b=40),
        xaxis=dict(title="Year", type="linear", tickmode="linear", dtick=1,
                   tickformat="d", gridcolor=theme.GRID,
                   range=[x_min - 0.5, x_max + 0.5]),
        yaxis=dict(gridcolor=theme.GRID, rangemode="tozero"),
        showlegend=False,
        hovermode="x unified",
        updatemenus=[dict(
            type="buttons", showactive=False,
            x=1.0, xanchor="right", y=1.25, yanchor="top",
            buttons=[dict(
                label="▶ ⏸",
                method="animate",
                args=[None, dict(frame=dict(duration=600, redraw=True),
                                 fromcurrent=True,
                                 transition=dict(duration=400, easing="sin-out"))],
                args2=[[None], dict(frame=dict(duration=0, redraw=False),
                                    mode="immediate",
                                    transition=dict(duration=0))],
            )],
        )],
    )
    return fig
