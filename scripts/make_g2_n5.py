"""Build the g2 N=5 (Metal1..Metal5) net JSON from the cmos5l N=4 geometry.

The PCell draws one identical comb on every metal except the topmost, which also
carries the feed pads. Verified on the N=4 JSON: Metal1 == Metal2 == Metal3 and
Via1 == Via2 == Via3, with only Metal4 (the top) different. So the N=5 device is
the same comb on Metal1..Metal4, the top pattern on Metal5, and one more via tier.
This is an exact reconstruction, not an approximation, for feed='double'.

g2 stackup from libs.tech/klayout/tech/xsect/sg13g2_for_EM.xs:
  t_metal4 0.49, t_via4 0.54, t_metal5 0.49, continuing the same z ladder.
"""
import json, sys

G2_STACK = {
    "Metal1": [1.04, 1.46], "Via1": [1.46, 2.00],
    "Metal2": [2.00, 2.49], "Via2": [2.49, 3.03],
    "Metal3": [3.03, 3.52], "Via3": [3.52, 4.06],
    "Metal4": [4.06, 4.55], "Via4": [4.55, 5.09],
    "Metal5": [5.09, 5.58],
}
ORDER = ["Metal1", "Via1", "Metal2", "Via2", "Metal3", "Via3",
         "Metal4", "Via4", "Metal5"]


def build(src, out):
    d = json.load(open(src))
    # sanity: the pattern really is uniform below the top metal
    def norm(e, l):
        return sorted(tuple(sorted(tuple(round(v, 4) for v in pt) for pt in p))
                      for p in e["layers"].get(l, []))
    for e in d["nets"]:
        assert norm(e, "Metal1") == norm(e, "Metal2") == norm(e, "Metal3"), "middle metals differ"
        assert norm(e, "Via1") == norm(e, "Via2") == norm(e, "Via3"), "via tiers differ"

    nets = []
    for e in d["nets"]:
        mid = e["layers"]["Metal1"]
        via = e["layers"]["Via1"]
        top = e["layers"]["Metal4"]
        nets.append({"name": e["name"], "layers": {
            "Metal1": mid, "Via1": via,
            "Metal2": mid, "Via2": via,
            "Metal3": mid, "Via3": via,
            "Metal4": mid, "Via4": via,
            "Metal5": top,
        }})
    json.dump({"stack": G2_STACK, "nets": nets, "bbox": d.get("bbox")}, open(out, "w"))
    n = sum(len(v) for e in nets for v in e["layers"].values())
    print(f"{out}: 5 metals, 4 via tiers, {n} polygons, z 1.04 to 5.58 um")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
