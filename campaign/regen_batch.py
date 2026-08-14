#!/usr/bin/env python3
"""Batch-regenerate every campaign device with the FIXED cap_cmomi pcell.

Runs under KLayout:  klayout -z -nc -r campaign/regen_batch.py
Reads campaign/devices.json, writes one flattened GDS per device into
campaign/gds_fixed/. One KLayout process for all devices (fast).

The tech `sg13cmos5l` (base-path -> the fixed working tree) supplies the
cap_cmomi PCell; the XOR gate (xor_all.py) proves the fix is present.
"""
import os
import json
import pya

HERE = os.path.dirname(os.path.abspath(__file__))
DEVS = json.load(open(os.path.join(HERE, "devices.json")))
OUTDIR = os.path.join(HERE, "gds_fixed")
os.makedirs(OUTDIR, exist_ok=True)

n_ok = 0
n_fail = 0
for d in DEVS:
    layout = pya.Layout()
    layout.technology_name = "sg13cmos5l"
    cell = layout.create_cell("cap_cmomi", "SG13_dev", d["params"])
    if cell is None:
        print("FAIL (pcell None):", d["name"], d["params"])
        n_fail += 1
        continue
    top = layout.create_cell(d["name"])
    top.insert(pya.DCellInstArray(cell, pya.DTrans()))
    top.flatten(-1, True)
    out = os.path.join(OUTDIR, d["file"])
    layout.write(out)
    n_ok += 1

print(f"REGEN done: {n_ok} ok, {n_fail} failed -> {OUTDIR}")
