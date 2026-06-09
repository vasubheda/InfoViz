"""Time-series line charts (seizures, price, purity) stacked as facets that
share one legend, with imputation-aware markers."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .. import theme
from . import helpers

# (column, transform, y-axis label, imputed-flag column, aggregation)
METRICS = [
    ("Kilograms", lambda x: x / 1000, "Seizures (t)", "seizure_imputed", "sum"),
    ("Typical_USD", lambda x: x, "Average Price (USD/g)", "price_imputed", "mean"),
    ("Typical", lambda x: x, "Average Purity (%)", "purity_imputed", "mean"),
]


def timeseries_single(data, filtered_combined, selection, metric_index, height=260):
    """Animated line chart for one metric — lines draw left-to-right year by year.

    Each Plotly frame reveals one additional year so the built-in Play button
    progressively draws the lines. The final frame (all years visible) is also
    the initial data, so the chart renders fully on load and replays on demand.
    """
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
        """One Scatter trace per substance showing data up to the given year set."""
        traces = []
        for substance in substances:
            color = cmap.get(substance, theme.TOL_MUTED[0])
            g = grouped[(grouped["Substance"] == substance)
                        & (grouped["Year"].isin(up_to_years))].sort_values("Year")
            traces.append(go.Scatter(
                x=g["Year"], y=g["Value"], mode="lines+markers", name=substance,
                legendgroup=substance,
                line=dict(width=2, color=color),
                marker=dict(size=7, line=dict(width=2, color="white"), color=color),
                hovertemplate=f"{y_label}: %{{y:.2f}}<extra>{substance}</extra>"))
        return traces

    # Initial state: all years visible (so the chart looks complete on load)
    initial_traces = traces_for_years(years)

    # One frame per year — each reveals one more year cumulatively
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

def timeseries(data, filtered_combined, selection, year_range, height=560):
    """Three stacked line charts — one per metric — sharing a single legend."""
    if len(filtered_combined) == 0:
        return helpers.empty_fig("No data for selected filters", height)

    cmap = {s: data.substance_color_map[s]
            for s in filtered_combined["Substance"].unique()
            if s in data.substance_color_map}

    fig = make_subplots(rows=len(METRICS), cols=1, shared_xaxes=True,
                        vertical_spacing=0.06,
                        subplot_titles=[m[2] for m in METRICS])

    legend_seen = set()
    for row, (col, transform, y_label, imp_col, agg) in enumerate(METRICS, start=1):
        # Drop rows where this metric is absent (the outer-joined frame carries
        # NaN there) BEFORE aggregating, so a substance with no data for this
        # metric (e.g. Amphetamines seizures) draws a gap, not a flat-zero line
        # from summing all-NaN.
        present = filtered_combined.dropna(subset=[col])
        grouped = (present.groupby(["Year", "Substance"])
                   .agg(val=(col, agg), imp=(imp_col, "max")).reset_index())
        grouped["Value"] = transform(grouped["val"])
        grouped["Year"] = grouped["Year"].astype(int)

        for substance, g in grouped.sort_values("Year").groupby("Substance"):
            color = cmap.get(substance, theme.TOL_MUTED[0])
            # One legend entry per substance, shown only the first time it
            # appears; legendgroup ties all three rows together and feeds the
            # click cross-filter (selection.py reads point.legendgroup).
            show = substance not in legend_seen
            legend_seen.add(substance)
            fig.add_trace(go.Scatter(
                x=g["Year"], y=g["Value"], mode="lines+markers", name=substance,
                legendgroup=substance, showlegend=show,
                line=dict(width=3, color=color),
                marker=dict(size=9, line=dict(width=2, color="white"), color=color),
                hovertemplate=f"{y_label}: %{{y:.2f}}<extra>{substance}</extra>"),
                row=row, col=1)

            # Overlay hollow markers on imputed points.
            imp = g[g["imp"]]
            if len(imp):
                fig.add_trace(go.Scatter(
                    x=imp["Year"], y=imp["Value"], mode="markers",
                    marker=dict(symbol="circle-open", size=13,
                                line=dict(width=2, color="#000000"), color=color),
                    legendgroup=substance, showlegend=False, hoverinfo="skip"),
                    row=row, col=1)

        fig.update_yaxes(title_text=y_label, gridcolor=theme.GRID, rangemode="tozero",
                         row=row, col=1)
        fig.update_xaxes(type="linear", tickmode="linear", dtick=1, tickformat="d",
                         gridcolor=theme.GRID, row=row, col=1)

    if selection.get("year"):
        fig.add_vline(x=selection["year"], line_dash="dash",
                      line_color=theme.ACCENT, line_width=3,
                      annotation_text=f"Selected: {selection['year']}",
                      annotation_position="top")

    fig.update_layout(
        hovermode="x unified", height=height,
        legend=dict(title="Substance", orientation="h", yanchor="top", y=-0.08,
                    xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#333", borderwidth=1),
        margin=dict(l=50, r=30, t=50, b=90),
        plot_bgcolor=theme.PLOT_BG)
    return fig
