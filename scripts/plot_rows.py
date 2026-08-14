"""Render the Metal1 comb of a cap_cmomi PCell and mark drawn vs billed rows."""
import json, math, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

UC_Y = 0.89
C1, C2 = "#2c6fb5", "#c0392b"


def bars_of(d):
    """One merged comb polygon per bar. Its y-centre is offset for the two outer
    bars (teeth on one side only), so snap the count to the 0.89 pitch instead."""
    n = 0
    for e in d["nets"]:
        for p in e["layers"]["Metal1"]:
            xs = [x for x, _ in p]; yy = [y for _, y in p]
            if max(xs) - min(xs) > max(yy) - min(yy):
                n += 1
    return n


def panel(ax, netjson, w_nom, title):
    d = json.load(open(netjson))
    for ni, e in enumerate(d["nets"]):
        for p in e["layers"]["Metal1"]:
            ax.add_patch(MplPoly(p, closed=True, facecolor=C1 if ni == 0 else C2,
                                 edgecolor="none", alpha=0.85))
    xs = [x for e in d["nets"] for p in e["layers"]["Metal1"] for x, _ in p]
    ys = [y for e in d["nets"] for p in e["layers"]["Metal1"] for _, y in p]
    x0, x1 = min(xs), max(xs)

    nb = bars_of(d)
    drawn = nb - 1
    billed = max(1, int(w_nom / UC_Y + 1e-6) - 1)

    for j in range(nb):
        ax.axhline(j * UC_Y, color="0.35", lw=0.6, ls=":", zorder=5)
    xr = x1 + 0.35
    for j in range(drawn):
        yc = (j + 0.5) * UC_Y
        paid = j < billed
        ax.annotate("", xy=(xr, j * UC_Y), xytext=(xr, (j + 1) * UC_Y),
                    arrowprops=dict(arrowstyle="<->", color="0.2", lw=1.1))
        ax.text(xr + 0.18, yc, f"fila {j+1}\n{'COBRADA' if paid else 'NO COBRADA'}",
                va="center", ha="left", fontsize=8,
                color="0.15" if paid else "#b8860b",
                weight="normal" if paid else "bold")
        if not paid:
            ax.add_patch(plt.Rectangle((x0, j * UC_Y), x1 - x0, UC_Y,
                                       facecolor="#f1c40f", alpha=0.22, zorder=1))

    ax.set_title(f"{title}\ndibuja {drawn} filas acopladas, el modelo cobra {billed}",
                 fontsize=10)
    ax.set_xlim(x0 - 0.3, xr + 1.9)
    ax.set_ylim(min(ys) - 0.3, max(ys) + 0.3)
    ax.set_aspect("equal")
    ax.set_xlabel("um"); ax.set_ylabel("um")


if __name__ == "__main__":
    cases = [("gds/sm_2x2.json", 2.0, "cap_cmomi  l=2 w=2"),
             ("gds/pcell_l5p5_w7_n4.json", 7.0, "cap_cmomi  l=5.5 w=7")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    for ax, (f, w, t) in zip(axes, cases):
        panel(ax, f, w, t)
    fig.suptitle("Metal1: cada par de barras adyacentes es una fila acoplada. "
                 "La amarilla la dibuja el PCell y no la cobra el modelo.", fontsize=11)
    fig.tight_layout()
    out = sys.argv[1] if len(sys.argv) > 1 else "rows.png"
    fig.savefig(out, dpi=150)
    print(out)
