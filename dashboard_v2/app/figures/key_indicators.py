import plotly.graph_objects as go

from .. import theme
from . import helpers
from .cache import memoize_figure

_DIM_OPACITY = 0.22


def active_set(all_substances, active):
    # empty active list means all substances are active
    return set(active) if active else set(all_substances)


def bar(substances, values, colors, title, hover_unit,
        fmt, tickprefix="", height=260):
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
        xaxis=dict(showticklabels=True, tickangle=-40,
                   tickfont=dict(size=9), gridcolor=theme.GRID),
        yaxis=dict(gridcolor=theme.GRID, tickprefix=tickprefix,
                   rangemode="tozero",
                   range=[0, (max(present) * 1.18) if present and max(present) > 0
                          else 1]))
    return fig


@memoize_figure()
def substance_bars(data, all_substances, active, seiz, prices, comb, height=260):
    active_subs = list(active_set(all_substances, active) & set(all_substances))
    # keep canonical ordering
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

    fig_seiz = bar(active_subs, col(seiz_by), colors,
                   "Seizures (t)", "Seizures: %{y:,.1f} t",
                   fmt=lambda v: f"{v:,.1f}", height=height)
    fig_price = bar(active_subs, col(price_by), colors,
                    "Avg Price (USD/g)", "Avg price: $%{y:,.2f}/g",
                    fmt=lambda v: f"${v:,.0f}", tickprefix="$", height=height)
    fig_purity = bar(active_subs, col(purity_by), colors,
                     "Avg Purity (%)", "Avg purity: %{y:.1f}%",
                     fmt=lambda v: f"{v:.0f}%", height=height)
    return fig_seiz, fig_price, fig_purity


def substance_cards(data, all_substances, active):
    import dash_bootstrap_components as dbc
    from dash import html

    active_set_ = active_set(all_substances, active)

    cards = []
    for s in all_substances:
        on = s in active_set_
        color = data.substance_color_map.get(s, theme.TOL_MUTED[0])
        # outer Div holds the click since dbc.Card has no n_clicks
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
