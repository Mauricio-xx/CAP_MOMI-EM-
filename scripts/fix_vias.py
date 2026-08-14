#!/usr/bin/env python3
"""Densify the vias of a cap_cmomi net JSON to the foundry reference, ON GRID.

Our PCell only vias the horizontal rails (via rows at the 0.89 um unit pitch in y);
the reference MOM layout vias every finger cell, on a regular 0.42 x 0.445 um grid
(0.19 um cuts) aligned to the fingers. This rewrites each net's via layers with
that aligned grid: build the grid from the cell's own via phase (so vias land
centred on the fingers exactly like the reference), and drop a 0.19 um via at
every grid node where it fits inside the metal below.

Writes <base>_fixvia.json. Pair with json_to_gds.py for the GDS.

Usage: python fix_vias.py gds/fd_l5p5_w7_dbl.json
"""
import sys, os, json
import numpy as np
from matplotlib.path import Path

VIA_BELOW = {"Via1": "Metal1", "Via2": "Metal2", "Via3": "Metal3", "Via4": "Metal4"}
VIA = 0.19
HALF = VIA / 2
TEST = HALF - 0.01          # half-extent for the "via fits inside metal" corner test
UC_X, UC_Y = 0.84, 0.89     # unit cell -> via grid pitch is half of each
XP, YP = UC_X / 2, UC_Y / 2  # 0.42, 0.445


def phase(vias, pitch):
    """Most-common grid phase of a set of coordinates modulo pitch."""
    if not vias:
        return 0.0
    r = np.mod(np.round(vias, 3), pitch)
    vals, cnt = np.unique(np.round(r, 3), return_counts=True)
    return float(vals[cnt.argmax()])


def fill(metal_polys, xs_grid, ys_grid):
    paths = [Path(np.array(p)) for p in metal_polys]
    GX, GY = np.meshgrid(xs_grid, ys_grid)
    C = np.column_stack([GX.ravel(), GY.ravel()])
    ok = np.ones(len(C), bool)
    for dx, dy in [(0, 0), (TEST, TEST), (-TEST, TEST), (TEST, -TEST), (-TEST, -TEST)]:
        probe = C + [dx, dy]
        hit = np.zeros(len(C), bool)
        for pa in paths:
            hit |= pa.contains_points(probe)
        ok &= hit
    return [[[x - HALF, y - HALF], [x + HALF, y - HALF],
             [x + HALF, y + HALF], [x - HALF, y + HALF]] for x, y in C[ok]]


def main():
    jp = sys.argv[1]
    base = jp[:-5] if jp.endswith(".json") else jp
    out = base + "_fixvia.json"
    d = json.load(open(jp))

    # grid phase from the cell's existing (correctly-placed) vias
    ovx, ovy = [], []
    for net in d["nets"]:
        for via in VIA_BELOW:
            for p in net["layers"].get(via, []):
                a = np.array(p); ovx.append(a[:, 0].mean()); ovy.append(a[:, 1].mean())
    xph, yph = phase(ovx, XP), phase(ovy, YP)

    # metal bbox for the grid extent (use Metal below the lowest via present)
    allpts = np.vstack([np.array(p) for net in d["nets"]
                        for m in VIA_BELOW.values() if m in net["layers"]
                        for p in net["layers"][m]])
    x0, x1 = allpts[:, 0].min(), allpts[:, 0].max()
    y0, y1 = allpts[:, 1].min(), allpts[:, 1].max()
    xs_grid = np.arange(xph + XP * np.floor((x0 - xph) / XP), x1 + XP, XP)
    ys_grid = np.arange(yph + YP * np.floor((y0 - yph) / YP), y1 + YP, YP)

    tot_old = tot_new = 0
    for net in d["nets"]:
        L = net["layers"]
        for via, metal in VIA_BELOW.items():
            if via in L and metal in L:
                tot_old += len(L[via])
                L[via] = fill(L[metal], xs_grid, ys_grid)
                tot_new += len(L[via])
    json.dump(d, open(out, "w"))
    print(f"{out}: grid phase x={xph:.3f} y={yph:.3f} pitch {XP}x{YP}; vias {tot_old} -> {tot_new}")


if __name__ == "__main__":
    main()
