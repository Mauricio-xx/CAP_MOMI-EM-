"""Draw the array-boundary difference behind the cap_cmomi row-count defect.

The reference document's characterised structure ends in fingers that have no
counter electrode, and page 3 excludes them from the active area: "the outer
rows with single fingers are not included here".  That exclusion is the -1 in
active_y = floor(w/0.89) - 1.

The PCell terminates the array at the last coupled row instead, so it has no
unpaired fingers.  At the same drawn width it therefore fits one more coupled
row than the characterised structure, and the -1 no longer describes it.

Both panels show Metal1 of a cap_cmomi at l = 3 um.  The left one is a two-row
core with the document's outer fingers added; the right one is the PCell as it
draws today.  The two are the same drawn width to within 0.05 um.

Usage:  plot_termination.py [out.png|out.svg]
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Rectangle
import textwrap

UC_Y = 0.89
NET_A, NET_B = "#2c6fb5", "#c0392b"
EXCL = "#e8a33d"
LAYER = "Metal1"


def bars_of(d):
    """y interval of every horizontal comb bar, bottom-up."""
    out = []
    for e in d["nets"]:
        for p in e["layers"][LAYER]:
            xs = [x for x, _ in p]
            ys = [y for _, y in p]
            if max(xs) - min(xs) > max(ys) - min(ys):
                out.append((min(ys), max(ys)))
    return sorted(out)


def bracket(ax, x, ylo, yhi, color, tick=0.10):
    """A vertical span marker that stays legible at short heights."""
    ax.plot([x, x], [ylo, yhi], color=color, lw=1.3, zorder=6,
            solid_capstyle="butt")
    for y in (ylo, yhi):
        ax.plot([x - tick, x + tick], [y, y], color=color, lw=1.3, zorder=6)


def panel(ax, path, title, subtitle, mark_stubs):
    d = json.load(open(path))
    stubs = d.get("stubs", []) if mark_stubs else []

    for ni, e in enumerate(d["nets"]):
        for p in e["layers"][LAYER]:
            ax.add_patch(MplPoly(p, closed=True, lw=0,
                                 facecolor=NET_A if ni == 0 else NET_B,
                                 alpha=0.9, zorder=3))
    for x0, x1, ya, yb in stubs:
        ax.add_patch(Rectangle((x0, ya), x1 - x0, yb - ya, lw=1.1,
                               facecolor=EXCL, edgecolor="#8a5a00",
                               hatch="////", alpha=0.95, zorder=4))

    xs = [x for e in d["nets"] for p in e["layers"][LAYER] for x, _ in p]
    ys = [y for e in d["nets"] for p in e["layers"][LAYER] for _, y in p]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    bars = bars_of(d)
    xr = x1 + 0.30
    for i in range(len(bars) - 1):
        lo = (bars[i][0] + bars[i][1]) / 2
        hi = (bars[i + 1][0] + bars[i + 1][1]) / 2
        bracket(ax, xr, lo, hi, "0.15")
        ax.text(xr + 0.20, (lo + hi) / 2, f"coupled row {i + 1}",
                va="center", ha="left", fontsize=8.5, color="0.1")
    if stubs:
        for lo, hi, lbl in ((y0, bars[0][0], "single fingers"),
                            (bars[-1][1], y1, "single fingers")):
            ax.add_patch(Rectangle((x0 - 0.12, lo), x1 - x0 + 0.24, hi - lo,
                                   facecolor=EXCL, alpha=0.16, lw=0, zorder=1))
            bracket(ax, xr, lo, hi, "#8a5a00")
            ax.text(xr + 0.20, (lo + hi) / 2, lbl + "\nno counter electrode",
                    va="center", ha="left", fontsize=8, color="#8a5a00")

    bracket(ax, x0 - 0.45, y0, y1, "0.35")
    ax.text(x0 - 0.62, (y0 + y1) / 2, f"w = {y1 - y0:.2f} um", rotation=90,
            va="center", ha="right", fontsize=8.5, color="0.25")

    ax.set_title(title, fontsize=11, pad=13)
    ax.text(0.5, 1.005, subtitle, transform=ax.transAxes, ha="center",
            va="bottom", fontsize=8.8, color="0.3")
    ax.set_xlim(x0 - 1.05, xr + 2.35)
    ax.set_ylim(y0 - 0.28, y1 + 0.28)
    ax.set_aspect("equal")
    ax.axis("off")
    return len(bars) - 1


def main(out):
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))
    n_doc = panel(axes[0], "gds/fig_l3_w2_doc.json",
                  "Characterised structure (reference document)",
                  "the array ends in fingers with nothing facing them",
                  mark_stubs=True)
    n_pc = panel(axes[1], "gds/fig_l3_w3.json",
                 "cap_cmomi PCell, as drawn",
                 "the array ends at the last coupled row",
                 mark_stubs=False)

    fig.suptitle("cap_cmomi: the two structures terminate differently, "
                 "and only one of them is what the model counts", fontsize=12.5)
    caption = (
        f"At the same drawn width the characterised structure fits {n_doc} "
        f"coupled rows and the PCell fits {n_pc}. One pitch of the reference "
        f"structure is spent on unpaired fingers, which page 3 of the document "
        f"correctly excludes from the active area, and that exclusion is the "
        f"-1 in active_y = floor(w/0.89) - 1. It describes the reference "
        f"boundary, not the drawn one, so on this layout the model bills one "
        f"coupled row too few: negligible on a large device, a factor of two "
        f"on the smallest.")
    fig.text(0.5, 0.03, "\n".join(textwrap.wrap(caption, 118)),
             ha="center", va="bottom", fontsize=9.2, color="0.15")
    fig.tight_layout(rect=(0, 0.13, 1, 0.94))
    fig.savefig(out, dpi=170)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "termination.png")
