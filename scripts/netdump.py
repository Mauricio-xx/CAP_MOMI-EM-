"""Dump per-net, per-layer merged polygons of a cap_cmomi GDS to JSON."""
import json, sys
import klayout.db as db
from netsplit import extract_nets, STACK, ORDER

gds, out = sys.argv[1], sys.argv[2]
ly, nets = extract_nets(gds)
assert len(nets) == 2, f"expected 2 nets, got {len(nets)}"
dbu = ly.dbu
data = {"stack": {k: STACK[k][2:] for k in ORDER}, "nets": []}
for nm, area, per_layer in nets:
    entry = {"name": nm, "area_um2": area, "layers": {}}
    for lname in ORDER:
        if lname not in per_layer:
            continue
        reg = db.Region()
        for p in per_layer[lname]:
            reg.insert(p)
        polys = []
        for poly in reg.merged().each():
            polys.append([[pt.x * dbu, pt.y * dbu] for pt in poly.each_point_hull()])
        entry["layers"][lname] = polys
    data["nets"].append(entry)
b = ly.top_cell().dbbox()
data["bbox"] = [b.left, b.bottom, b.right, b.top]
json.dump(data, open(out, "w"))
n = sum(len(v) for e in data["nets"] for v in e["layers"].values())
print(f"{gds} -> {out}: 2 nets, {n} merged polygons, bbox {b.width():.2f} x {b.height():.2f} um")
