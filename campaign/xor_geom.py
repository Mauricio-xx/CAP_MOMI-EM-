#!/usr/bin/env python3
"""XOR two GDS dirs on conductor+via layers only (geometry equality check).

Confirms a relabeled regen changed NOTHING the EM solve sees. Text/annotation
layers (e.g. 63/0) are intentionally ignored. Prints the max residual XOR area
(um^2) across all shared files; 0 means geometry is byte-for-byte equal.

  python3 campaign/xor_geom.py <dirA> <dirB>
"""
import os
import sys
import glob
import klayout.db as kdb

CONDUCT = [("Metal1", 8), ("Metal2", 10), ("Metal3", 30), ("Metal4", 50)]
VIAS = [("Via1", 19), ("Via2", 29), ("Via3", 49)]
LAYERS = CONDUCT + VIAS


def region(ly, top, lnum, dt=0):
    li = ly.find_layer(lnum, dt)
    if li is None:
        return kdb.Region()
    return kdb.Region(top.begin_shapes_rec(li))


def main():
    dirA, dirB = sys.argv[1], sys.argv[2]
    files = sorted(os.path.basename(p) for p in glob.glob(f"{dirB}/*.gds"))
    worst = 0.0
    worst_where = ""
    nchecked = 0
    nmissing = 0
    for f in files:
        pa, pb = f"{dirA}/{f}", f"{dirB}/{f}"
        if not os.path.exists(pa):
            nmissing += 1
            continue
        la, lb = kdb.Layout(), kdb.Layout()
        la.read(pa)
        lb.read(pb)
        ta, tb = la.top_cell(), lb.top_cell()
        dbu = la.dbu
        for lname, lnum in LAYERS:
            ra = region(la, ta, lnum)
            rb = region(lb, tb, lnum)
            area = (ra ^ rb).area() * dbu * dbu
            if area > worst:
                worst, worst_where = area, f"{f}:{lname}"
        nchecked += 1
    print(f"checked {nchecked} files ({nmissing} in B not in A)")
    print(f"max residual XOR area = {worst:.9f} um^2  ({worst_where or 'all zero'})")
    print("GEOMETRY IDENTICAL" if worst == 0.0 else "GEOMETRY DIFFERS")
    sys.exit(0 if worst == 0.0 else 1)


if __name__ == "__main__":
    main()
