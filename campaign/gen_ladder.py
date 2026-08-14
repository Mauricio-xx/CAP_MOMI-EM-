#!/usr/bin/env python3
"""Generate the small per-N density ladder cells (fixed pcell) for Phase 2 ES.

These are purpose-built (NOT fab devices): small w7 cells at two lengths so the
per-N density comes out of a length pair (delta-L) at fixed width, isolating N
= mmax-mmin+1 (count, not vertical position: m1m3 vs m2m4 both N=3).

Run under KLayout:  klayout -z -nc -r campaign/gen_ladder.py
"""
import os
import pya

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "gds_fixed")
os.makedirs(OUTDIR, exist_ok=True)

LADDER = [
    ("n3_m1m3_w7_l5p5", "5.5u", 1, 3),
    ("n3_m1m3_w7_l10",  "10u",  1, 3),
    ("n3_m2m4_w7_l5p5", "5.5u", 2, 4),
    ("n3_m2m4_w7_l10",  "10u",  2, 4),
    ("n2_m3m4_w7_l5p5", "5.5u", 3, 4),
    ("n2_m3m4_w7_l10",  "10u",  3, 4),
]

for name, l, mmin, mmax in LADDER:
    params = {"w": "7u", "l": l, "mmin": mmin, "mmax": mmax,
              "feed": "double", "subblock": 0}
    layout = pya.Layout()
    layout.technology_name = "sg13cmos5l"
    cell = layout.create_cell("cap_cmomi", "SG13_dev", params)
    if cell is None:
        print("FAIL", name)
        continue
    top = layout.create_cell(name)
    top.insert(pya.DCellInstArray(cell, pya.DTrans()))
    top.flatten(-1, True)
    layout.write(os.path.join(OUTDIR, name + ".gds"))
    print("WROTE", name)

print("LADDER done")
