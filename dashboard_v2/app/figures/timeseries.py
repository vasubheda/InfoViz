"""Time-series line charts (seizures, price, purity) stacked as facets that
share one legend, with imputation-aware markers."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .. import theme
from . import helpers

# (column, transform, y-axis label, imputed-flag column, aggregation)
METRICS = [
    ("Kilograms", lambda x: x / 1000, "Seizures (Tons)", "seizure_imputed", "sum"),
    ("Typical_USD", lambda x: x, "Average Price (USD/g)", "price_imputed", "mean"),
    ("Typical", lambda x: x, "Average Purity (%)", "purity_imputed", "mean"),
]


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
        legend=dict(title="Substance", orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.02, bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#333", borderwidth=1),
        margin=dict(l=50, r=150, t=50, b=60),
        plot_bgcolor=theme.PLOT_BG)
    return fig
