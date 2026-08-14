#!/usr/bin/env python3
"""XOR gate over all regenerated devices vs their fab GDS.

For each device in devices.json: conductor layers (M1-M4) must XOR to empty
(geometry unchanged) and via layers must be densified (regen via area > fab).
Writes campaign/xor_report.csv and prints a summary. Non-zero exit if any
device fails the conductor-identity check.
"""
import json
import csv
from pathlib import Path
import klayout.db as db

HERE = Path(__file__).resolve().parent
DEVS = json.loads((HERE / "devices.json").read_text())
GDSDIR = HERE / "gds_fixed"
REPORT = HERE / "xor_report.csv"

CONDUCTORS = [("Metal1", 8, 0), ("Metal2", 10, 0), ("Metal3", 30, 0), ("Metal4", 50, 0)]
VIAS = [("Via1", 19, 0), ("Via2", 29, 0), ("Via3", 49, 0)]
EPS = 1e-6  # um^2


def regions(path):
    ly = db.Layout()
    ly.read(str(path))
    top = ly.top_cell()
    out = {}
    for name, lnum, dt in CONDUCTORS + VIAS:
        idx = ly.find_layer(lnum, dt)
        r = db.Region() if idx is None else db.Region(top.begin_shapes_rec(idx))
        r.merge()
        out[(lnum, dt)] = r
    return ly.dbu, out


def main():
    rows = []
    n_pass = n_fail = 0
    for d in DEVS:
        regen = GDSDIR / d["file"]
        fab = Path(d["fab_gds"])
        if not regen.exists():
            print("MISSING regen:", regen)
            n_fail += 1
            continue
        dbu_a, ra = regions(regen)
        _, rb = regions(fab)
        cond_xor = 0.0
        via_regen = via_fab = 0.0
        for name, lnum, dt in CONDUCTORS:
            cond_xor += (ra[(lnum, dt)] ^ rb[(lnum, dt)]).area() * dbu_a * dbu_a
        for name, lnum, dt in VIAS:
            via_regen += ra[(lnum, dt)].area() * dbu_a * dbu_a
            via_fab += rb[(lnum, dt)].area() * dbu_a * dbu_a
        cond_ok = cond_xor < EPS
        via_densified = via_regen > via_fab + EPS
        ok = cond_ok and via_densified
        n_pass += ok
        n_fail += (not ok)
        rows.append({
            "name": d["name"], "group": d["group"], "feed": d["feed"], "wl": d["wl"],
            "N": d["N"], "cond_xor_um2": round(cond_xor, 6),
            "via_regen_um2": round(via_regen, 4), "via_fab_um2": round(via_fab, 4),
            "via_delta_um2": round(via_regen - via_fab, 4),
            "verdict": "PASS" if ok else ("COND_MISMATCH" if not cond_ok else "VIA_NOT_DENSIFIED"),
        })
        if not ok:
            print(f"  FAIL {d['name']}: cond_xor={cond_xor:.4f} via_regen={via_regen:.3f} via_fab={via_fab:.3f}")

    with REPORT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"XOR gate: {n_pass} PASS, {n_fail} FAIL  ->  {REPORT}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
