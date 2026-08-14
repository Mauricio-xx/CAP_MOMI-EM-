#!/usr/bin/env python3
"""Before/after of the via fix: Metal1 (grey) + Via1 (red) for our cell,
sparse (as-was, vias only at tooth bases) vs viafix (reference: base + tip).
Zoom to a few tooth cells so the extra tip vias are visible.
Writes fig/via_layout.{png,svg}.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
PAIR = [("gds/fd_l5p5_w7_dbl.json", "sin vias (as-was): solo base del diente"),
        ("gds/fd_l5p5_w7_dbl_viafix.json", "con vias (reference): base + punta")]
# zoom window (um): a few coupled rows near the cell centre
XLIM, YLIM = (0.0, 3.2), (1.6, 5.2)

fig, axes = plt.subplots(1, 2, figsize=(11, 6), sharex=True, sharey=True)
for ax, (jp, title) in zip(axes, PAIR):
    d = json.load(open(f"{ROOT}/{jp}"))
    nv = 0
    for net in d["nets"]:
        for p in net["layers"].get("Metal1", []):
            ax.add_patch(MplPoly(p, closed=True, facecolor="#cfcfcf",
                                 edgecolor="#888", lw=0.4, zorder=1))
        for p in net["layers"].get("Via1", []):
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            cx, cy = np.mean(xs), np.mean(ys)
            if XLIM[0] <= cx <= XLIM[1] and YLIM[0] <= cy <= YLIM[1]:
                nv += 1
            ax.add_patch(MplPoly(p, closed=True, facecolor="#b2182b",
                                 edgecolor="k", lw=0.3, zorder=3))
    ax.set_xlim(*XLIM); ax.set_ylim(*YLIM); ax.set_aspect("equal")
    ax.set_title(f"{title}\n({nv} Via1 en esta ventana)", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("El fix del PCell: vias a lo largo del diente (nuestra celda, w=7)",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
for ext in ("png", "svg"):
    out = f"{ROOT}/fig/via_layout.{ext}"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("wrote", out)
