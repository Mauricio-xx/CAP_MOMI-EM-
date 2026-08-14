#!/usr/bin/env python3
"""Add one in-plane lumped port to a cap_cmomi GDS, for gds2palace.

cap_cmomi is a lateral interdigitated MoM cap: net A (left feed) and net B
(right feed) never touch, and their feeds sit on opposite sides. gds2palace
excites a device with a lumped port drawn on a special GDS layer. For a
2-terminal cap the right choice is ONE in-plane port on Metal1 placed in the
coupling gap between a finger of net A and the adjacent finger of net B.

The port rectangle must fill that gap EXACTLY: its two edges coincide with the
two facing metal walls (touch, zero overlap), its interior is clean oxide. If it
overlaps metal by even a fraction, Palace aborts with "a non-periodic face
cannot have multiple boundary elements" (the port surface and the metal
conductivity surface land on the same face). So we read the exact vertical wall
coordinates from the polygons, not from a scan.

Writes <input>_port.gds and a verification PNG. The port direction is x (current
crosses the finger gap), so the model script must use direction='x'.

Usage: python add_port_cap_cmomi.py gds/fd_l5p5_w5_dbl.json
"""
import sys, os, json
import numpy as np
from matplotlib.path import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Rectangle
import gdspy

PORTLAYER = 201          # special layer gds2palace reads as a port
Y_INSET = 0.02           # um pulled in from the finger overlap top/bottom (stay off corners)
MAX_GAP = 0.6            # um, largest finger-to-finger gap we accept as a coupling gap
MIN_OVERLAP = 0.12       # um, minimum shared finger height for a usable port
METAL_Z = {"Metal1": 1, "Metal2": 2, "Metal3": 3, "Metal4": 4, "Metal5": 5}


def bottom_metal(nets):
    """Lowest metal layer name present across the nets (where we place the port)."""
    present = set()
    for net in nets:
        present |= {k for k in net["layers"] if k in METAL_Z}
    return min(present, key=lambda m: METAL_Z[m])


def net_paths(nets, layer):
    return [[Path(np.array(p)) for p in net["layers"][layer]] for net in nets]


def inside(paths, x, y):
    return any(pa.contains_points([[x, y]])[0] for pa in paths)


def vwalls(nets_layer):
    """Vertical edges (x const) of a net's polygons: list of (x, ylo, yhi)."""
    E = []
    for p in nets_layer:
        a = np.array(p); n = len(a)
        for i in range(n):
            x1, y1 = a[i]; x2, y2 = a[(i + 1) % n]
            if abs(x1 - x2) < 1e-9:
                ylo, yhi = sorted([y1, y2])
                if yhi - ylo > 1e-6:
                    E.append((round(x1, 4), round(ylo, 4), round(yhi, 4)))
    return E


def find_interdigit_port(nets, pA, pB, bbox, layer):
    """Return (xR, xL, y0, y1): the exact coupling gap between a B wall at xR and
    an A wall at xL>xR, with clean oxide between and a shared finger height."""
    (x0b, y0b), (x1b, y1b) = bbox
    xc, yc = (x0b + x1b) / 2, (y0b + y1b) / 2
    wA = vwalls(nets[0]["layers"][layer])
    wB = vwalls(nets[1]["layers"][layer])
    best = None
    for (xR, bl, bh) in wB:
        for (xL, al, ah) in wA:
            gap = xL - xR
            if not (0.05 < gap < MAX_GAP):
                continue
            ov0, ov1 = max(bl, al), min(bh, ah)
            if ov1 - ov0 < MIN_OVERLAP:
                continue
            my = (ov0 + ov1) / 2
            # true facing gap: oxide between, B just left of xR, A just right of xL
            if inside(pA, (xR + xL) / 2, my) or inside(pB, (xR + xL) / 2, my):
                continue
            if not (inside(pB, xR - 0.01, my) and inside(pA, xL + 0.01, my)):
                continue
            score = -(abs((xR + xL) / 2 - xc) + abs(my - yc))   # prefer cap centre
            if best is None or score > best[0]:
                best = (score, xR, xL, ov0 + Y_INSET, ov1 - Y_INSET)
    if best is None:
        raise SystemExit("no clean interdigit A/B gap found")
    return best[1:]


def main():
    jpath = sys.argv[1]
    base = jpath[:-5] if jpath.endswith(".json") else jpath
    gds_in, gds_out = base + ".gds", base + "_port.gds"
    d = json.load(open(jpath))
    nets = d["nets"]
    layer = sys.argv[2] if len(sys.argv) > 2 else bottom_metal(nets)
    print(f"PORT_LAYER={layer}")
    pA, pB = net_paths(nets, layer)
    allpts = [pt for net in nets for p in net["layers"][layer] for pt in p]
    xs = [p[0] for p in allpts]; ys = [p[1] for p in allpts]
    bbox = ((min(xs), min(ys)), (max(xs), max(ys)))

    xR, xL, y0, y1 = find_interdigit_port(nets, pA, pB, bbox, layer)
    print(f"coupling gap: B wall x={xR:.3f}  A wall x={xL:.3f}  gap={xL - xR:.3f} um  "
          f"port y[{y0:.3f},{y1:.3f}]")
    print(f"port rect: x[{xR:.3f},{xL:.3f}] y[{y0:.3f},{y1:.3f}]  "
          f"(direction x, length={xL - xR:.3f}, width={y1 - y0:.3f})")

    # hard check: strict interior must be metal-free (no clipped finger)
    gx = np.arange(xR + 0.01, xL - 0.01, 0.005)
    gy = np.arange(y0 + 0.01, y1 - 0.01, 0.005)
    GX, GY = np.meshgrid(gx, gy); pts = np.column_stack([GX.ravel(), GY.ravel()])
    hit = sum(int(np.array([pa.contains_points(pts) for pa in ps]).any(0).sum())
              for ps in (pA, pB))
    assert hit == 0, f"port interior clips metal ({hit} pts) - refuse to write"
    print("interior metal-free: OK")

    gdspy.current_library = gdspy.GdsLibrary()
    lib = gdspy.GdsLibrary(infile=gds_in)
    top = lib.top_level()[0]
    top.add(gdspy.Rectangle((xR, y0), (xL, y1), layer=PORTLAYER, datatype=0))
    lib.write_gds(gds_out)
    print("wrote", gds_out)

    # verification render (full cell + zoom)
    fig, (ax, az) = plt.subplots(1, 2, figsize=(13, 6))
    cols = ["#2166ac", "#b2182b"]
    for target in (ax, az):
        for ni, net in enumerate(nets):
            for p in net["layers"][layer]:
                target.add_patch(MplPoly(p, closed=True, facecolor=cols[ni],
                                         edgecolor="k", lw=0.3, alpha=0.85))
        target.add_patch(Rectangle((xR, y0), xL - xR, y1 - y0, facecolor="#f1c40f",
                                   edgecolor="k", lw=1.4, alpha=0.97, zorder=5))
        target.set_aspect("equal")
    (x0b, y0b), (x1b, y1b) = bbox
    ax.set_xlim(x0b - 1.3, x1b + 0.6); ax.set_ylim(y0b - 0.6, y1b + 0.6)
    ax.set_title("full cell: A=blue B=red, port=yellow")
    az.set_xlim(xR - 1.0, xL + 1.0); az.set_ylim(y0 - 1.0, y1 + 1.0)
    az.set_title("zoom: port fills the A-B coupling gap (edges = metal walls)")
    fig.suptitle(f"{os.path.basename(base)}  in-plane port  x[{xR:.2f},{xL:.2f}] "
                 f"y[{y0:.2f},{y1:.2f}]  dir x")
    out_png = base + "_port.png"
    fig.savefig(out_png, dpi=110, bbox_inches="tight")
    print("wrote", out_png)


if __name__ == "__main__":
    main()
