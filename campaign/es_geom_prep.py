#!/usr/bin/env python3
"""Prep for the ES geometry discriminator (system python3: gdstk + klayout.db).

Part of the FW-vs-ES investigation (see results/FW_MESH_INVESTIGATION.md). Builds
the comb+feeds geometry for the 04p9 double device and dumps net JSONs for the
bare comb and comb+Metal4-feeds, to test whether the rf2port feed/port geometry
adds to the A-B capacitance. Run this, then es_geom_solve.py (venv python).

  python3 campaign/es_geom_prep.py
"""
import os
import sys
import json

import gdstk
import klayout.db as db

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
sys.path.insert(0, f"{ROOT}/scripts")
from netsplit import extract_nets, STACK, ORDER  # noqa: E402

OUT = f"{ROOT}/campaign/es_geom"
os.makedirs(OUT, exist_ok=True)
TB = f"{ROOT}/palace/rf2port/tb/cap_mom_double_04p9um_rf_tb.gds"
COMB_SRC = f"{ROOT}/campaign/gds_fixed/cap_mom_double_04p9um.gds"
MARGIN = 5.0
METAL4 = (50, 0)


def build_combfeeds(dst):
    tb = gdstk.read_gds(TB)
    top = tb.top_level()[0]
    out = gdstk.Library(unit=tb.unit, precision=tb.precision)
    cell = out.new_cell("cap_mom_double_04p9um_feeds")
    for ref in top.references:                 # the comb (referenced cap cell)
        for p in ref.get_polygons():
            cell.add(p)
    for p in top.polygons:                     # the two Metal4 feed bars
        if (p.layer, p.datatype) == METAL4:
            cell.add(p.copy())
    out.write_gds(dst)


def dump_net(gds, out):
    ly, nets = extract_nets(gds)
    assert len(nets) == 2, f"expected 2 nets in {gds}, got {len(nets)}"
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
    return data["bbox"]


feeds_gds = f"{OUT}/combfeeds.gds"
build_combfeeds(feeds_gds)
comb_json = f"{OUT}/comb_net.json"
feeds_json = f"{OUT}/combfeeds_net.json"
bb_comb = dump_net(COMB_SRC, comb_json)
bb_feeds = dump_net(feeds_gds, feeds_json)

dom = [round(bb_feeds[0] - MARGIN, 6), round(bb_feeds[1] - MARGIN, 6),
       round(bb_feeds[2] + MARGIN, 6), round(bb_feeds[3] + MARGIN, 6)]
json.dump({"domain": dom, "comb": comb_json, "combfeeds": feeds_json, "outdir": OUT},
          open(f"{OUT}/params.json", "w"), indent=2)
print("comb bbox  :", bb_comb)
print("feeds bbox :", bb_feeds)
print("shared dom :", dom)
print("wrote", f"{OUT}/params.json")
