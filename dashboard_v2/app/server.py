import os
import warnings

import dash

# silence a noisy plotly futurewarning
warnings.filterwarnings("ignore", category=FutureWarning, module="plotly")
import dash_bootstrap_components as dbc

from .callbacks import register_callbacks
from .data_access import load_artifacts
from .layout import build_layout

DATA = load_artifacts()

app = dash.Dash(__name__, external_stylesheets=[
                    dbc.themes.BOOTSTRAP,
                    # bootstrap icons for the info glyphs
                    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/"
                    "font/bootstrap-icons.min.css",
                ],
                suppress_callback_exceptions=True,
                title="European Drug-Market Intelligence")
server = app.server
app.layout = build_layout(DATA)
register_callbacks(app, DATA)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
