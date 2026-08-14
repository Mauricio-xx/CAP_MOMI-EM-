#!/usr/bin/env python3
"""Write a GDS from a net JSON, mapping layer names to IHP g2 GDS layer numbers.

Used to materialise the N=5 cells (g2n5_*.json), which exist only as JSON from
make_g2_n5.py, into GDS so gds2palace can read them. All polygons of both nets go
on their layer's g2 number (nets stay galvanically separate by geometry).

Usage: python json_to_gds.py gds/g2n5_l5p5_w7.json [gds/g2n5_l5p5_w7.gds]
"""
import sys, os, json
import gdspy

LAYERNUM = {
    "Metal1": 8, "Metal2": 10, "Metal3": 30, "Metal4": 50, "Metal5": 67,
    "Via1": 19, "Via2": 29, "Via3": 49, "Via4": 66,
}


def main():
    jp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else jp[:-5] + ".gds"
    name = os.path.splitext(os.path.basename(out))[0]
    d = json.load(open(jp))
    gdspy.current_library = gdspy.GdsLibrary()
    lib = gdspy.GdsLibrary()
    cell = lib.new_cell(name)
    counts = {}
    for net in d["nets"]:
        for lname, polys in net["layers"].items():
            ln = LAYERNUM[lname]
            for p in polys:
                cell.add(gdspy.Polygon(p, layer=ln, datatype=0))
                counts[lname] = counts.get(lname, 0) + 1
    lib.write_gds(out)
    print("wrote", out, "layers:", {k: counts[k] for k in sorted(counts)})


if __name__ == "__main__":
    main()
