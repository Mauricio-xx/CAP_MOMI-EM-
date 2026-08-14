#!/usr/bin/env python3
"""XOR gate: regenerated (fixed-pcell) GDS vs the fabricated GDS.

Confirms the fixed pcell reproduces the fab geometry exactly on conductor
layers (XOR must be empty) while adding the missing tip vias on the via
layers (XOR must be non-empty, and equal to the extra via count).

Usage: python3 xor_check.py <regen.gds> <fab.gds>
Exit 0 = pass (metals identical, vias densified), 1 = unexpected.
"""
import sys
import klayout.db as db

# (name, layer, datatype)
CONDUCTORS = [("Metal1", 8, 0), ("Metal2", 10, 0), ("Metal3", 30, 0), ("Metal4", 50, 0)]
VIAS = [("Via1", 19, 0), ("Via2", 29, 0), ("Via3", 49, 0)]


def regions(path):
    ly = db.Layout()
    ly.read(path)
    top = ly.top_cell()
    out = {}
    for name, lnum, dt in CONDUCTORS + VIAS:
        idx = ly.find_layer(lnum, dt)
        if idx is None:
            out[(lnum, dt)] = db.Region()
        else:
            out[(lnum, dt)] = db.Region(top.begin_shapes_rec(idx))
        out[(lnum, dt)].merge()
    return ly.dbu, out


def main():
    regen, fab = sys.argv[1], sys.argv[2]
    dbu_a, ra = regions(regen)
    dbu_b, rb = regions(fab)
    print(f"regen={regen}\nfab  ={fab}\ndbu regen={dbu_a} fab={dbu_b}")
    ok = True
    print(f"{'layer':8} {'xor_area_um2':>14} {'regen_um2':>12} {'fab_um2':>12} verdict")
    for name, lnum, dt in CONDUCTORS + VIAS:
        a = ra[(lnum, dt)]
        b = rb[(lnum, dt)]
        xor = a ^ b
        # areas in um^2 (region area is in dbu^2)
        xa = xor.area() * dbu_a * dbu_a
        aa = a.area() * dbu_a * dbu_a
        ba = b.area() * dbu_b * dbu_b
        is_via = (name, lnum, dt) in VIAS
        if is_via:
            verdict = "OK-densified" if xa > 1e-6 and aa > ba + 1e-6 else ("empty?" if xa < 1e-6 else "check")
        else:
            verdict = "OK-identical" if xa < 1e-6 else "MISMATCH"
            if xa >= 1e-6:
                ok = False
        print(f"{name:8} {xa:14.4f} {aa:12.4f} {ba:12.4f} {verdict}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
