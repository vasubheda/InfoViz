"""Key-indicators substance bars: three compact bar charts (seizures, avg price,
avg purity) that replace the old per-substance DataTable.

Selection moved from table rows to a shared clickable legend (rendered as HTML
swatches, see callbacks/selection.py): bars for deselected substances stay
visible but dimmed, so every substance's value is still comparable while only
the active ones drive the rest of the dashboard.
"""
import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

# Opacity for a bar whose substance is currently deselected (dimmed-but-visible).
_DIM_OPACITY = 0.22


def _active_set(all_substances, active):
    """Empty / None active list means 'all substances active' (the default)."""
    return set(active) if active else set(all_substances)


def _bar(substances, values, colors, title, hover_unit,
         fmt, tickprefix="", height=260):
    """One vertical bar chart for the given substances.

    ``values`` carry ``None`` for substances with no data under the current
    filters (distinct from a genuine 0): Plotly draws no bar there and we label
    it "n/a", so a real zero (a drawn zero-height bar) stays distinguishable.
    """
    text = ["n/a" if v is None else fmt(v) for v in values]
    present = [v for v in values if v is not None]
    fig = go.Figure(go.Bar(
        x=substances, y=values,
        marker_color=colors,
        text=text, textposition="outside",
        textfont=dict(size=10), cliponaxis=False,
        hovertemplate=f"%{{x}}<br>{hover_unit}<extra></extra>"))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13)),
        height=height, plot_bgcolor=theme.PLOT_BG, showlegend=False,

        margin=dict(l=45, r=12, t=40, b=95),
        # Substance names along the x-axis (angled so the long ones - e.g.
        # "Tranquillizers and Sedatives" - fit the narrow md=4 columns).
        xaxis=dict(showticklabels=True, tickangle=-40,
                   tickfont=dict(size=9), gridcolor=theme.GRID),
        # Headroom so the outside value labels are not clipped at the top.
        yaxis=dict(gridcolor=theme.GRID, tickprefix=tickprefix,
                   rangemode="tozero",
                   range=[0, (max(present) * 1.18) if present and max(present) > 0
                          else 1]))
    return fig


@memoize_figure()
def substance_bars(data, all_substances, active, seiz, prices, comb, height=260):
    """Return (seizures, avg-price, avg-purity) bar figures for active substances only."""
    active_subs = list(_active_set(all_substances, active) & set(all_substances))
    # Preserve canonical ordering
    active_subs = [s for s in all_substances if s in active_subs]
    colors = [data.substance_color_map.get(s, theme.TOL_MUTED[0]) for s in active_subs]

    seiz_by = (seiz.groupby("Substance")["Kilograms"].sum() / 1000
               if len(seiz) else None)
    price_by = (prices.groupby("Substance")["Typical_USD"].mean()
                if len(prices) else None)
    purity_by = (comb.groupby("Substance")["Typical"].mean()
                 if len(comb) else None)

    def col(series):
        if series is None:
            return [None] * len(active_subs)
        return [float(series[s]) if s in series.index and series[s] == series[s]
                else None for s in active_subs]

    fig_seiz = _bar(active_subs, col(seiz_by), colors,
                    "Seizures (t)", "Seizures: %{y:,.1f} t",
                    fmt=lambda v: f"{v:,.1f}", height=height)
    fig_price = _bar(active_subs, col(price_by), colors,
                     "Avg Price (USD/g)", "Avg price: $%{y:,.2f}/g",
                     fmt=lambda v: f"${v:,.0f}", tickprefix="$", height=height)
    fig_purity = _bar(active_subs, col(purity_by), colors,
                      "Avg Purity (%)", "Avg purity: %{y:.1f}%",
                      fmt=lambda v: f"{v:.0f}%", height=height)
    return fig_seiz, fig_price, fig_purity


def substance_cards(data, all_substances, active):
    """Clickable substance selection cards that act as the substance filter.

    One card per substance: a colour dot and the substance name. Deselected
    cards render dimmed but stay visible/clickable. Each carries the same
    pattern-matching id the toggle callback already listens on, so the wiring is
    unchanged from the old legend swatches.
    """
    import dash_bootstrap_components as dbc
    from dash import html

    active_set = _active_set(all_substances, active)

    cards = []
    for s in all_substances:
        on = s in active_set
        color = data.substance_color_map.get(s, theme.TOL_MUTED[0])
        # The clickable affordance lives on an outer Div (dbc.Card has no
        # n_clicks); the Card inside is purely visual. The Div keeps the
        # pattern-matching id the toggle callback already listens on.
        cards.append(html.Div(dbc.Card(dbc.CardBody([
            html.Div([
                html.Span(style={
                    "display": "inline-block", "width": "11px", "height": "11px",
                    "borderRadius": "2px", "marginRight": "6px",
                    "backgroundColor": color,
                    "opacity": 1.0 if on else _DIM_OPACITY}),
                html.Span(s, className="fw-bold" if on else None,
                          style={"fontSize": "0.8rem"}),
            ], className="d-flex align-items-center"),
        ], className="p-2"),
            style={
                "borderColor": color if on else "#dee2e6",
                "borderWidth": "2px" if on else "1px",
                "opacity": 1.0 if on else 0.6}),
            id={"type": "subst-legend", "index": s},
            n_clicks=0,
            style={"cursor": "pointer", "userSelect": "none",
                   "marginRight": "8px", "marginBottom": "8px",
                   "minWidth": "92px"},
        ))
    return cards
