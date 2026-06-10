"""Single source of truth for colour.

Everything visual draws from here so the colourblind-safe claim is enforced in
one place (the original app advertised accessibility yet used a red-green
diverging scale). Categorical = Paul Tol Muted; sequential = Viridis.
"""

# Paul Tol's Muted qualitative palette (colourblind-safe).
TOL_MUTED = [
    "#332288", "#88CCEE", "#44AA99", "#117733",
    "#999933", "#DDCC77", "#CC6677", "#882255",
    "#AA4499", "#DDDDDD",
]

SEQUENTIAL = "Viridis"

# Accent colours used for selection markers / regression lines (Wong-safe).
ACCENT = "#D55E00"        # selection highlight (orange)
ACCENT_ALT = "#0072B2"    # secondary accent (blue)

PLOT_BG = "rgba(240,240,240,0.5)"
GRID = "rgba(128,128,128,0.2)"


def substance_color_map(substances) -> dict:
    """Deterministic substance -> hex assignment, cycling the Tol palette.

    'Other' is excluded from the assignment: it is never displayed, and giving
    it a slot would push the displayed substances onto 7 head colours, leaving
    too few free for the disjoint subregion band (see subregion_color_map)."""
    displayed = sorted(s for s in substances if s != "Other")
    return {s: TOL_MUTED[i % len(TOL_MUTED)] for i, s in enumerate(displayed)}


def subregion_color_map(subregions) -> dict:
    """Deterministic subregion -> hex, drawn from the TAIL of the Tol palette so
    subregion colours never collide with substance colours (which use the head;
    see substance_color_map). The 6 displayed substances claim slots 0-5,
    leaving #CC6677/#882255/#AA4499/#DDDDDD free. #DDDDDD (pale grey) is dropped
    - as a region fill it reads like 'no data' - so subregions take the rose /
    maroon / purple, all distinct from every substance."""
    tail = [c for c in reversed(TOL_MUTED) if c != "#DDDDDD"]
    return {sr: tail[i % len(tail)] for i, sr in enumerate(sorted(subregions))}
