"""Time-series line chart with a metric selector and imputation-aware markers."""
import plotly.express as px
import plotly.graph_objects as go

from .. import theme
from . import helpers

METRICS = {
    "seizures": ("Kilograms", lambda x: x / 1000, "Seizures (Tons)", "seizure_imputed"),
    "price":    ("Typical_USD", lambda x: x, "Average Price (USD/g)", "price_imputed"),
    "purity":   ("Typical", lambda x: x, "Average Purity (%)", "purity_imputed"),
}


def timeseries(data, filtered_combined, metric, selection, year_range,
               height=400, title_prefix=""):
    if metric not in METRICS or len(filtered_combined) == 0:
        return helpers.empty_fig("No data for selected filters", height)
    col, transform, y_label, imp_col = METRICS[metric]

    agg = "sum" if metric == "seizures" else "mean"
    grouped = (filtered_combined.groupby(["Year", "Substance"])
               .agg(val=(col, agg), imp=(imp_col, "max")).reset_index())
    grouped["Value"] = transform(grouped["val"])
    grouped["Year"] = grouped["Year"].astype(int)

    cmap = {s: data.substance_color_map[s] for s in grouped["Substance"].unique()
            if s in data.substance_color_map}
    fig = px.line(grouped, x="Year", y="Value", color="Substance", markers=True,
                  title=f"{title_prefix}{y_label} over time",
                  labels={"Value": y_label}, color_discrete_map=cmap)
    fig.update_traces(line=dict(width=3),
                      marker=dict(size=9, line=dict(width=2, color="white")))

    # Overlay hollow markers on imputed points (per substance trace).
    for substance, g in grouped.groupby("Substance"):
        imp = g[g["imp"]]
        if len(imp):
            fig.add_trace(go.Scatter(
                x=imp["Year"], y=imp["Value"], mode="markers",
                marker=dict(symbol="circle-open", size=13,
                            line=dict(width=2, color="#000000"),
                            color=cmap.get(substance, "#000")),
                showlegend=False, hoverinfo="skip"))

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
        xaxis=dict(type="linear", tickmode="linear", dtick=1, tickformat="d",
                   gridcolor=theme.GRID),
        yaxis=dict(gridcolor=theme.GRID), plot_bgcolor=theme.PLOT_BG)
    return fig
