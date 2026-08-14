"""Dump a feed='none' cap_cmomi as TWO terminals, grouped by row polarity.

The bare array has no feed rails, so every same-polarity column stack is an
electrically separate conductor and connectivity extraction returns one net per
stack.  For a capacitance reference that has to line up with the 'same' and
'double' pairs, the terminals must be defined the way the array means them:
bars sit at y = j*0.89, adjacent rows carry opposite polarity, so j even is one
plate and j odd is the other.  That is exactly what a feed rail does when it is
present, without adding any metal.

Usage:  netdump_none.py <gds> <out.json>
"""
import json
import sys

import klayout.db as db
from netsplit import extract_nets, STACK, ORDER

UC_Y = 0.89
BOT = "Metal1"


def parity_of(per_layer, dbu):
    """0 or 1 from the row index of this net's horizontal bars."""
    js = []
    for nm in ORDER:
        if not nm.startswith("Metal"):
            continue
        for p in per_layer.get(nm, []):
            b = p.bbox()
            if b.width() <= b.height():
                continue                      # a tooth, not a bar
            yc = (b.bottom + b.top) / 2.0 * dbu
            js.append(int(round(yc / UC_Y)))
    if not js:
        return None
    par = {j % 2 for j in js}
    if len(par) != 1:
        raise SystemExit(f"net spans both row parities: rows {sorted(set(js))}")
    return par.pop()


def main(gds, out):
    ly = db.Layout(); ly.read(gds)
    dbu = ly.dbu
    _, nets = extract_nets(gds)

    groups = {0: {}, 1: {}}
    for nm, _area, per_layer in nets:
        par = parity_of(per_layer, dbu)
        if par is None:
            raise SystemExit(f"net {nm} has no horizontal bar to key on")
        for lname in ORDER:
            if lname not in per_layer:
                continue
            groups[par].setdefault(lname, []).extend(per_layer[lname])

    data = {"stack": {k: STACK[k][2:] for k in ORDER}, "nets": []}
    for par in (0, 1):
        entry = {"name": f"parity{par}", "layers": {}}
        for lname in ORDER:
            polys = groups[par].get(lname, [])
            if not polys:
                continue
            reg = db.Region()
            for p in polys:
                reg.insert(p)
            entry["layers"][lname] = [
                [[pt.x * dbu, pt.y * dbu] for pt in poly.each_point_hull()]
                for poly in reg.merged().each()
            ]
        data["nets"].append(entry)

    b = ly.top_cell().dbbox()
    data["bbox"] = [b.left, b.bottom, b.right, b.top]
    json.dump(data, open(out, "w"))
    n = sum(len(v) for e in data["nets"] for v in e["layers"].values())
    print(f"{gds} -> {out}: {len(nets)} raw nets grouped into 2 by row parity, "
          f"{n} merged polygons, bbox {b.width():.2f} x {b.height():.2f} um")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
