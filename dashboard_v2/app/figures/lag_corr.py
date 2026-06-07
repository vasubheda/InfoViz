"""Within-country lagged seizure->price correlation (Q1).

Default view: substance-level aggregated r̄ (Fisher-z weighted mean across
countries) with a 95% CI whisker and a significance marker. When a country is
selected, switch to that country's per-substance bars.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers


def lag_correlation(data, selection, target="Typical_USD"):
    lag = data.lag_correlation
    lag = lag[lag["target"] == target]
    country = selection.get("country")

    if country:
        rows = lag[(lag["level"] == "country") & (lag["Country"] == country)]
        rows = rows.dropna(subset=["r"]).sort_values("r")
        if len(rows) == 0:
            return helpers.empty_fig(f"No within-country lag data for {country}", 300)
        return _bar(data, rows, country, target, ci=False)

    rows = lag[lag["level"] == "substance_aggregate"].dropna(subset=["r"]).sort_values("r")
    if len(rows) == 0:
        return helpers.empty_fig("Insufficient data for lag correlation", 300)
    return _bar(data, rows, None, target, ci=True)


def _bar(data, rows, country, target, ci):
    colors = [data.substance_color_map.get(s, theme.TOL_MUTED[0])
              for s in rows["Substance"]]
    metric = "price" if target == "Typical_USD" else "purity"
    fig = go.Figure()
    if ci and {"ci_low", "ci_high"}.issubset(rows.columns):
        err_plus = (rows["ci_high"] - rows["r"]).clip(lower=0)
        err_minus = (rows["r"] - rows["ci_low"]).clip(lower=0)
        error_x = dict(type="data", symmetric=False,
                       array=err_plus, arrayminus=err_minus, thickness=1.5)
        text = [f"r̄={r:.2f} ({nc:.0f} countries)"
                for r, nc in zip(rows["r"], rows["n_countries"])]
    else:
        error_x = None
        text = [f"r={r:.2f}, p={p:.3f}, n={n}"
                for r, p, n in zip(rows["r"], rows["p"], rows["n"])]

    fig.add_trace(go.Bar(
        x=rows["r"], y=rows["Substance"], orientation="h", marker_color=colors,
        error_x=error_x, text=text, textposition="auto",
        hovertemplate="<b>%{y}</b><br>r = %{x:.3f}<extra></extra>"))
    fig.add_vline(x=0, line_color="black", line_width=1)

    # Significance markers.
    if ci and "n_significant" in rows.columns:
        for _, row in rows.iterrows():
            if row.get("n_significant", 0) and row["n_significant"] > 0:
                fig.add_annotation(x=row["r"] + (0.03 if row["r"] >= 0 else -0.03),
                                   y=row["Substance"], text="*", showarrow=False,
                                   font=dict(size=16, color="red"))
    else:
        for _, row in rows.iterrows():
            if row.get("p") is not None and row["p"] < 0.05:
                fig.add_annotation(x=row["r"] + (0.03 if row["r"] >= 0 else -0.03),
                                   y=row["Substance"], text="*", showarrow=False,
                                   font=dict(size=16, color="red"))

    scope = country if country else "across countries (Fisher-z weighted mean)"
    fig.update_layout(
        title=f"Seizures(Y) → {metric}(Y+1) · {scope} · * = significant",
        xaxis_title=f"Pearson r (seizures → {metric}, +1yr)", height=300,
        margin=dict(l=150, r=40, t=50, b=40),
        xaxis=dict(range=[-1, 1], gridcolor=theme.GRID, zeroline=True),
        yaxis=dict(gridcolor=theme.GRID), plot_bgcolor=theme.PLOT_BG)
    return fig
