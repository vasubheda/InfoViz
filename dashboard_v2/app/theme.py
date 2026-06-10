# paul tol muted palette
TOL_MUTED = [
    "#332288", "#88CCEE", "#44AA99", "#117733",
    "#999933", "#DDCC77", "#CC6677", "#882255",
    "#AA4499", "#DDDDDD",
]

SEQUENTIAL = "Viridis"

# accent colours for selection markers / regression lines
ACCENT = "#D55E00"        # orange highlight
ACCENT_ALT = "#0072B2"    # blue

PLOT_BG = "rgba(240,240,240,0.5)"
GRID = "rgba(128,128,128,0.2)"


def substance_color_map(substances) -> dict:
    # skip 'Other', it is never shown
    displayed = sorted(s for s in substances if s != "Other")
    return {s: TOL_MUTED[i % len(TOL_MUTED)] for i, s in enumerate(displayed)}


def subregion_color_map(subregions) -> dict:
    # use the tail of the palette so these never clash with substance colours
    # drop pale grey since it reads like 'no data'
    tail = [c for c in reversed(TOL_MUTED) if c != "#DDDDDD"]
    return {sr: tail[i % len(tail)] for i, sr in enumerate(sorted(subregions))}
