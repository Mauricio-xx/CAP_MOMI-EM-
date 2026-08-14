#!/usr/bin/env python3
"""Regenerate every campaign device from the CURRENT branch cap_cmomi PCell.

Provenance-clean regen: the first batch (2026-08-13) ran ~12 h before the model
edit 356ff2d was committed, so those GDS carry a stale cosmetic C= text label
(layer 63/0) from the old analytic formula. The DRAWN GEOMETRY was already the
current branch geometry (via fix + floor(w/0.89) rows, XOR-verified), so nothing
needs re-simulating; this only refreshes the label so the on-disk layouts match
the branch head exactly.

Run forcing the worktree PCell (empty KLAYOUT_HOME avoids the installed cmos5l;
KLAYOUT_PATH SET, not prepended, because tech/lib name SG13_dev collides between
the two PDKs):
  KLAYOUT_HOME=<empty> KLAYOUT_PATH=<worktree>/libs.tech/klayout \
  REGEN_OUT=campaign/gds_fixed_branch klayout -zz -r campaign/regen_clean.py
"""
import os
import json
import pya

HERE = os.path.dirname(os.path.abspath(__file__))
DEVS = json.load(open(os.path.join(HERE, "devices.json")))
OUTDIR = os.environ.get("REGEN_OUT", os.path.join(HERE, "gds_fixed_branch"))
OUTDIR = OUTDIR if os.path.isabs(OUTDIR) else os.path.join(os.getcwd(), OUTDIR)
os.makedirs(OUTDIR, exist_ok=True)

# ladder cells (purpose-built, not in devices.json): name -> params
LADDER = [
    ("n3_m1m3_w7_l5p5", {"w": "7u", "l": "5.5u", "mmin": 1, "mmax": 3, "feed": "double", "subblock": 0}),
    ("n3_m1m3_w7_l10",  {"w": "7u", "l": "10u",  "mmin": 1, "mmax": 3, "feed": "double", "subblock": 0}),
    ("n3_m2m4_w7_l5p5", {"w": "7u", "l": "5.5u", "mmin": 2, "mmax": 4, "feed": "double", "subblock": 0}),
    ("n3_m2m4_w7_l10",  {"w": "7u", "l": "10u",  "mmin": 2, "mmax": 4, "feed": "double", "subblock": 0}),
    ("n2_m3m4_w7_l5p5", {"w": "7u", "l": "5.5u", "mmin": 3, "mmax": 4, "feed": "double", "subblock": 0}),
    ("n2_m3m4_w7_l10",  {"w": "7u", "l": "10u",  "mmin": 3, "mmax": 4, "feed": "double", "subblock": 0}),
]

WORK = [(d["name"], d["file"], d["params"]) for d in DEVS]
WORK += [(name, name + ".gds", params) for name, params in LADDER]


def read_label(layout, top):
    """Return the C= annotation text (layer 63/0) if present, else ''."""
    li = layout.layer(63, 0)
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        sh = it.shape()
        if sh.is_text():
            try:
                return sh.text.string
            except Exception:
                return "<text>"
        it.next()
    return ""


n_ok = n_fail = 0
labels = {}
for name, fname, params in WORK:
    layout = pya.Layout()
    layout.technology_name = "sg13cmos5l"
    cell = layout.create_cell("cap_cmomi", "SG13_dev", params)
    if cell is None:
        print("FAIL (pcell None):", name, params)
        n_fail += 1
        continue
    top = layout.create_cell(name)
    top.insert(pya.DCellInstArray(cell, pya.DTrans()))
    top.flatten(-1, True)
    labels[name] = read_label(layout, top)
    layout.write(os.path.join(OUTDIR, fname))
    n_ok += 1

# spot-print the golden-device labels so provenance is visible in the log
for k in ("cap_mom_double_04p9um", "cap_mom_same_04p9um", "cap_mom_double_07p8um"):
    if k in labels:
        print(f"LABEL {k}: {labels[k]}")
print(f"REGEN done: {n_ok} ok, {n_fail} failed -> {OUTDIR}")
