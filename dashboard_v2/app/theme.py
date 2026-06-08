"""Single source of truth for colour.

Everything visual draws from here so the colourblind-safe claim is enforced in
one place (the original app advertised accessibility yet used a red-green
diverging scale). Categorical = Paul Tol Muted; sequential = Viridis;
diverging = RdBu (colourblind-safe, replaces the old RdYlGn).
"""

# Paul Tol's Muted qualitative palette (colourblind-safe).
TOL_MUTED = [
    "#332288", "#88CCEE", "#44AA99", "#117733",
    "#999933", "#DDCC77", "#CC6677", "#882255",
    "#AA4499", "#DDDDDD",
]

SEQUENTIAL = "Viridis"
DIVERGING = "RdBu"        # colourblind-safe diverging (was RdYlGn)

# Accent colours used for selection markers / regression lines (Wong-safe).
ACCENT = "#D55E00"        # selection highlight (orange)
ACCENT_ALT = "#0072B2"    # secondary accent (blue)

PLOT_BG = "rgba(240,240,240,0.5)"
GRID = "rgba(128,128,128,0.2)"

# Marker styling for imputed observations (hollow + dashed outline).
IMPUTED_MARKER = dict(symbol="circle-open", line=dict(width=2, dash="dot"))


def substance_color_map(substances) -> dict:
    """Deterministic substance -> hex assignment, cycling the Tol palette."""
    return {s: TOL_MUTED[i % len(TOL_MUTED)] for i, s in enumerate(sorted(substances))}


def subregion_color_map(subregions) -> dict:
    """Deterministic subregion -> hex, drawn from the TAIL of the Tol palette so
    subregion colours never collide with substance colours (which use the head;
    see substance_color_map). With our data substances claim the first 7 slots
    (incl. the never-displayed 'Other'), leaving exactly the last three
    (#DDDDDD/#AA4499/#882255) free — so the tail is the only disjoint band."""
    tail = list(reversed(TOL_MUTED))
    return {sr: tail[i % len(tail)] for i, sr in enumerate(sorted(subregions))}
