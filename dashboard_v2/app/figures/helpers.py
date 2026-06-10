import plotly.graph_objects as go


def empty_fig(msg: str, height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_layout(height=height, plot_bgcolor="white",
                      margin=dict(l=20, r=20, t=20, b=20))
    return fig


def filter_note_fig(height: int = 400) -> go.Figure:
    return empty_fig(
        "Clear the country filter (select all countries) to compare across markets.",
        height,
    )


def base_geo_layout(fig: go.Figure, height: int = 400, right_margin: int = 0,
                    clickmode: str = "event+select"):
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(margin=dict(l=0, r=right_margin, t=30, b=0),
                      height=height, clickmode=clickmode)
    return fig
