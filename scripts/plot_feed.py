"""Draw the two feed topologies of cap_cmomi, and what the model charges for each.

'double' puts one rail per net at opposite ends of the array, each stacked through
every metal and tied together by a via column. The two rails sit about six microns
apart, so their mutual capacitance is small, and the model calls it zero.

'same' puts both terminals at the same end as two plates that overlap completely,
one on the top metal and one on the metal below it, with no via between them. That
overlap is the single-side feed capacitance the model charges for.

The plan views cannot show the second topology, because the two plates lie exactly
on top of each other. The cross-section can, and it is the point of this figure.

Usage:  plot_feed.py [out.png|out.svg]
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Rectangle

NET_A, NET_B = "#2c6fb5", "#c0392b"
CORE = "#c8ccd0"
STACK = {"Metal1": (1.04, 1.46), "Via1": (1.46, 2.00), "Metal2": (2.00, 2.49),
         "Via2": (2.49, 3.03), "Metal3": (3.03, 3.52), "Via3": (3.52, 4.06),
         "Metal4": (4.06, 4.55)}
ARRAY_X = (-0.30, 5.09)      # the comb itself; anything outside is feed


def is_feed(p):
    xs = [x for x, _ in p]
    return min(xs) < ARRAY_X[0] - 1e-6 or max(xs) > ARRAY_X[1] + 1e-6


def plan(ax, path, title, note):
    d = json.load(open(path))
    for ni, e in enumerate(d["nets"]):
        for lay, polys in e["layers"].items():
            if not lay.startswith("Metal"):
                continue
            for p in polys:
                feed = is_feed(p)
                ax.add_patch(MplPoly(p, closed=True, lw=0, zorder=3 if feed else 2,
                                     facecolor=(NET_A if ni == 0 else NET_B) if feed else CORE,
                                     alpha=0.75 if feed else 0.55))
    ax.set_title(title, fontsize=11, pad=10)
    ax.text(0.5, 1.003, note, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=8.6, color="0.3")
    ax.set_xlim(-1.9, 6.7)
    ax.set_ylim(-0.9, 7.2)
    ax.set_aspect("equal")
    ax.axis("off")


def xsec(ax, path, ycut, title, note, annotate_gap=False, xlim=(-2.4, 6.7)):
    """Vertical slice at y = ycut, drawn in (x, z)."""
    d = json.load(open(path))
    for ni, e in enumerate(d["nets"]):
        for lay, polys in e["layers"].items():
            if lay not in STACK:
                continue
            z0, z1 = STACK[lay]
            for p in polys:
                ys = [y for _, y in p]
                if not (min(ys) <= ycut <= max(ys)):
                    continue
                # rectangles only, which is what this cell draws
                xs = sorted({x for x, _ in p})
                x0, x1 = xs[0], xs[-1]
                feed = is_feed(p)
                ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, lw=0.4,
                                       edgecolor="white", zorder=3 if feed else 2,
                                       facecolor=(NET_A if ni == 0 else NET_B) if feed else CORE,
                                       alpha=0.95 if feed else 0.55))
    for lay, (z0, z1) in STACK.items():
        if lay.startswith("Metal"):
            ax.text(ax.get_xlim()[0] if False else -1.95, (z0 + z1) / 2, lay,
                    fontsize=7.5, va="center", ha="right", color="0.35")
    ax.axvline(ARRAY_X[0], color="0.45", lw=0.9, ls=":", zorder=6)
    ax.text(ARRAY_X[0] + 0.06, 4.85, "array starts here", fontsize=7.6,
            color="0.45", va="top", ha="left")
    if annotate_gap:
        ax.annotate("", xy=(-0.75, 3.52), xytext=(-0.75, 4.06),
                    arrowprops=dict(arrowstyle="<->", color="0.1", lw=1.4))
        ax.text(-0.66, 3.79, "0.54 um of oxide, no via.\nThis overlap IS the\nsingle-side feed.",
                fontsize=8.6, va="center", ha="left", color="0.1")
    ax.set_title(title, fontsize=10.5, pad=8)
    ax.text(0.5, 1.004, note, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=8.4, color="0.3")
    ax.set_xlim(*xlim)
    ax.set_ylim(0.75, 5.0)
    ax.set_aspect(0.9)
    ax.set_xlabel("x [um]", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


def main(out):
    fig = plt.figure(figsize=(12.6, 8.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], hspace=0.30, wspace=0.06)

    plan(fig.add_subplot(gs[0, 0]), "gds/fd_l5p5_w7_dbl.json",
         "feed = 'double'   (the default configuration)",
         "one rail per terminal, at opposite ends, about 6 um apart")
    plan(fig.add_subplot(gs[0, 1]), "gds/fd_l5p5_w7_same.json",
         "feed = 'same'   (both terminals on the left)",
         "the two plates coincide in plan view; see the section below")

    xsec(fig.add_subplot(gs[1, 0]), "gds/fd_l5p5_w7_dbl.json", 0.0,
         "section through the left 'double' rail",
         "one terminal only, stacked Metal1..Metal4 and tied by a via column",
         xlim=(-2.0, 1.6))
    xsec(fig.add_subplot(gs[1, 1]), "gds/fd_l5p5_w7_same.json", 3.20,
         "section through the 'same' plates",
         "both terminals, one on Metal4 and one on Metal3, no via between them",
         annotate_gap=True, xlim=(-2.0, 1.6))

    fig.suptitle("cap_cmomi feed topologies, l = 5.5 um, w = 7 um, Metal1..Metal4",
                 fontsize=12.5, y=0.975)
    fig.text(0.5, 0.018,
             "The shipped model bills Cfeed(same)=0.1625*pad_len+0.0916 fF and "
             "Cfeed(double)=0.152*pad_len fF (pad_len=floor(w/0.89)*0.89+0.42), with no "
             "layer-count keying.\n"
             "The retired model charged cfeed_per_um[N] x feed_width for 'same' and nothing "
             "for 'double', scaling 0.70 to 1.28 fF/um with the layer count, while the drawn "
             "plates stay on the top two metals whatever the count is.",
             ha="center", va="bottom", fontsize=9.3, color="0.15")
    fig.subplots_adjust(top=0.90, bottom=0.115, left=0.055, right=0.985)
    fig.savefig(out, dpi=165)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "feed.png")
