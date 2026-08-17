#!/usr/bin/env python3
"""Add the base+tip via lattice to a cap_cmomi net JSON (the drawn PCell fix).

The as-drawn cell vias each tooth only at its base (one via per finger on the
0.89 um y-pitch). The branch PCell fix (TOOTH_VIA_OFF = 0.41) adds a second via
0.41 um along each tooth toward its tip. This reproduces that: for every existing
via it drops a copy offset +-0.41 um in y, in the direction the tooth metal
continues (so the tip via lands on the finger, never past the base onto the bar
or into the gap). Same x, same via size; nothing is removed.

This is the '_viafix' lattice used for the canonical electrostatic/full-wave
numbers. Validated to reproduce gds/fd_l5p5_w7_dbl_viafix.json exactly (0 missing,
0 extra vias on every net x via layer). Writes <base>_viafix.json.

Usage: python add_tip_vias.py gds/fd_l5p5_w7_dbl.json
"""
import sys, json
import numpy as np
from matplotlib.path import Path

VIA_BELOW = {"Via1": "Metal1", "Via2": "Metal2", "Via3": "Metal3", "Via4": "Metal4"}
OFF = 0.41          # tooth-via offset toward the tip (PCell TOOTH_VIA_OFF)
DUP = 0.05          # dedup tolerance vs an existing via
STEP = 0.05         # extra reach past the tip via to confirm it is on the finger


def centers(polys):
    return [(round(float(np.mean([q[0] for q in p])), 3),
             round(float(np.mean([q[1] for q in p])), 3)) for p in polys]


def add_tips(d):
    tot_old = tot_new = 0
    for net in d["nets"]:
        L = net["layers"]
        for via, metal in VIA_BELOW.items():
            if via not in L or metal not in L:
                continue
            paths = [Path(np.array(p)) for p in L[metal]]
            cen = centers(L[via])
            cs = set(cen)
            half = None
            # infer via half-size from an existing via to draw the new squares
            p0 = L[via][0]
            hx = (max(q[0] for q in p0) - min(q[0] for q in p0)) / 2.0
            hy = (max(q[1] for q in p0) - min(q[1] for q in p0)) / 2.0
            added = []
            for (x, y) in cen:
                for dy in (OFF, -OFF):
                    px, py = round(x, 3), round(y + dy, 3)
                    if any(abs(px - ex) < DUP and abs(py - ey) < DUP for ex, ey in cs):
                        continue
                    on = any(pa.contains_point((px, py)) for pa in paths)
                    reach = any(pa.contains_point((px, py + (STEP if dy > 0 else -STEP)))
                                for pa in paths)
                    if on and reach:
                        added.append((px, py))
            for (px, py) in added:
                L[via].append([[px - hx, py - hy], [px + hx, py - hy],
                               [px + hx, py + hy], [px - hx, py + hy]])
            tot_old += len(cen)
            tot_new += len(cen) + len(added)
    return tot_old, tot_new


def main():
    jp = sys.argv[1]
    base = jp[:-5] if jp.endswith(".json") else jp
    out = base + "_viafix.json"
    d = json.load(open(jp))
    old, new = add_tips(d)
    json.dump(d, open(out, "w"))
    print(f"{out}: vias {old} -> {new} (base+tip, +-{OFF} um)")


if __name__ == "__main__":
    main()
