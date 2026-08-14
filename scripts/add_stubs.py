"""Add the reference document's unpaired outer fingers to a cap_cmomi net JSON.

The characterised structure ends in teeth that have no counter-electrode (page 3 of
the reference document: "the outer rows with single fingers are not included here").
The PCell does not draw them. This adds them, so the two topologies can be compared
on the same stack with one variable changed.

Bottom bar carries up-teeth at X_UP and is missing its down-teeth at X_UP + 0.42;
the top bar is the mirror. Stub rectangles overlap the bar so the solid stays
connected; gmsh fragments the overlap and both pieces land on the same terminal.
"""
import json, sys

TOOTH_EXT = 0.575
ENDCAP = 0.155
X_OFF = 0.42          # X_DOWN - X_UP


def teeth_x_at(poly, y_extreme, tol=1e-6):
    """x intervals where the merged comb polygon touches its extreme y."""
    pts = [(x, y) for x, y in poly]
    n = len(pts)
    spans = []
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if abs(y0 - y_extreme) < tol and abs(y1 - y_extreme) < tol:
            spans.append((min(x0, x1), max(x0, x1)))
    return sorted(spans)


def add(netjson, out):
    d = json.load(open(netjson))
    metals = [k for k in d["stack"] if k.startswith("Metal")]

    # locate the outermost bar of each net by the extreme y of its comb polygons
    ref = metals[0]
    best_lo, best_hi = None, None
    for ni, e in enumerate(d["nets"]):
        for p in e["layers"].get(ref, []):
            lo = min(y for _, y in p); hi = max(y for _, y in p)
            if best_lo is None or lo < best_lo[1]:
                best_lo = (ni, lo, p)
            if best_hi is None or hi > best_hi[1]:
                best_hi = (ni, hi, p)
    net_bot, y_bot, poly_bot = best_lo
    net_top, y_top, poly_top = best_hi

    # bottom bar: has up-teeth reaching y_bot+... ; its own extreme low is the endcap
    bar_bot = y_bot + ENDCAP
    bar_top = y_top - ENDCAP
    up_x = teeth_x_at(poly_bot, max(y for _, y in poly_bot))
    dn_x = teeth_x_at(poly_top, min(y for _, y in poly_top))

    stubs_bot = [(x0 + X_OFF, x1 + X_OFF, bar_bot - TOOTH_EXT, bar_bot + ENDCAP) for x0, x1 in up_x]
    stubs_top = [(x0 - X_OFF, x1 - X_OFF, bar_top - ENDCAP, bar_top + TOOTH_EXT) for x0, x1 in dn_x]

    for m in metals:
        for x0, x1, ya, yb in stubs_bot:
            d["nets"][net_bot]["layers"].setdefault(m, []).append(
                [[x0, ya], [x1, ya], [x1, yb], [x0, yb]])
        for x0, x1, ya, yb in stubs_top:
            d["nets"][net_top]["layers"].setdefault(m, []).append(
                [[x0, ya], [x1, ya], [x1, yb], [x0, yb]])

    # keep the added rectangles so a figure can mark which fingers are unpaired
    d["stubs"] = [list(s) for s in stubs_bot + stubs_top]
    json.dump(d, open(out, "w"))
    print(f"{out}: bottom bar y={bar_bot:.3f} net{net_bot} +{len(stubs_bot)} stubs, "
          f"top bar y={bar_top:.3f} net{net_top} +{len(stubs_top)} stubs, "
          f"on {len(metals)} metal layers")


if __name__ == "__main__":
    add(sys.argv[1], sys.argv[2])
