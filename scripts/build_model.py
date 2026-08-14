"""Build a Palace electrostatic capacitance model from a cap_cmomi GDS.

Conductors become PEC Terminal boundaries; the FEM domain is the surrounding
uniform SiO2 (the PDK stackup has one SiO2 block spanning the whole thin-metal
region, so no dielectric layering is needed between M1 and M5).
"""
import json, os, sys
import gmsh

EPS_SIO2 = 4.1


def build(netjson, out_prefix, lc_fine=0.15, lc_far=2.0, margin_xy=3.0, z_lo=-1.0, z_hi=8.0,
          domain=None):
    data = json.load(open(netjson))
    STACK = data["stack"]
    ORDER = list(STACK.keys())
    nets = data["nets"]

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("Geometry.OCCParallel", 1)
    occ = gmsh.model.occ

    def is_rect(pts):
        if len(pts) != 4:
            return False
        xs = sorted({round(p[0], 6) for p in pts}); ys = sorted({round(p[1], 6) for p in pts})
        return len(xs) == 2 and len(ys) == 2

    net_vols = [[], []]
    for idx, entry in enumerate(nets):
        for lname in ORDER:
            polys = entry["layers"].get(lname)
            if not polys:
                continue
            zmin, zmax = STACK[lname]
            for pts in polys:
                if is_rect(pts):
                    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                    v = occ.addBox(min(xs), min(ys), zmin,
                                   max(xs)-min(xs), max(ys)-min(ys), zmax-zmin)
                    net_vols[idx].append((3, v))
                else:
                    ptags = [occ.addPoint(x, y, zmin) for x, y in pts]
                    ltags = [occ.addLine(ptags[i], ptags[(i+1) % len(ptags)]) for i in range(len(ptags))]
                    loop = occ.addCurveLoop(ltags)
                    surf = occ.addPlaneSurface([loop])
                    ext = occ.extrude([(2, surf)], 0, 0, zmax - zmin)
                    net_vols[idx] += [e for e in ext if e[0] == 3]
    occ.synchronize()

    if domain is not None:
        # Explicit outer box. Two geometries that differ only in a small feature
        # must sit in the SAME domain, or the boundary shifts between them and
        # the difference picks up ~0.25% of the total, which can be the size of
        # the feature being measured.
        x0, y0, x1, y1 = domain
    else:
        bb = gmsh.model.getBoundingBox(-1, -1)
        x0, y0 = bb[0] - margin_xy, bb[1] - margin_xy
        x1, y1 = bb[3] + margin_xy, bb[4] + margin_xy
    dom = occ.addBox(x0, y0, z_lo, x1-x0, y1-y0, z_hi-z_lo)

    cond = net_vols[0] + net_vols[1]
    out, omap = occ.fragment([(3, dom)], cond)
    occ.synchronize()

    # omap[0] -> pieces of the domain box; omap[1:] -> pieces of each conductor
    cond_pieces = [set(), set()]
    for i, dt in enumerate(cond):
        pieces = {t for (d, t) in omap[1 + i] if d == 3}
        which = 0 if i < len(net_vols[0]) else 1
        cond_pieces[which] |= pieces
    dom_pieces = {t for (d, t) in omap[0] if d == 3}
    diel = sorted(dom_pieces - cond_pieces[0] - cond_pieces[1])

    term_surfs = []
    for k in (0, 1):
        vols = [(3, t) for t in sorted(cond_pieces[k])]
        bnd = gmsh.model.getBoundary(vols, combined=True, oriented=False)
        term_surfs.append(sorted({t for (d, t) in bnd if d == 2}))

    # far boundary = outer faces of the domain box
    all_diel_bnd = gmsh.model.getBoundary([(3, t) for t in diel], combined=True, oriented=False)
    far = []
    tol = 1e-6
    for d, t in all_diel_bnd:
        if d != 2:
            continue
        sb = gmsh.model.getBoundingBox(2, t)
        on_face = (abs(sb[0]-x0) < tol and abs(sb[3]-x0) < tol) or (abs(sb[0]-x1) < tol and abs(sb[3]-x1) < tol) \
               or (abs(sb[1]-y0) < tol and abs(sb[4]-y0) < tol) or (abs(sb[1]-y1) < tol and abs(sb[4]-y1) < tol) \
               or (abs(sb[2]-z_lo) < tol and abs(sb[5]-z_lo) < tol) or (abs(sb[2]-z_hi) < tol and abs(sb[5]-z_hi) < tol)
        if on_face:
            far.append(t)

    # drop conductor volumes from the mesh, keep their bounding surfaces
    occ.remove([(3, t) for t in sorted(cond_pieces[0] | cond_pieces[1])], recursive=False)
    occ.synchronize()

    ATTR = dict(diel=1, term1=2, term2=3, far=4)
    gmsh.model.addPhysicalGroup(3, diel, ATTR["diel"], name="dielectric")
    gmsh.model.addPhysicalGroup(2, term_surfs[0], ATTR["term1"], name="terminal1")
    gmsh.model.addPhysicalGroup(2, term_surfs[1], ATTR["term2"], name="terminal2")
    gmsh.model.addPhysicalGroup(2, far, ATTR["far"], name="farfield")

    # mesh sizing: fine on the conductor surfaces, coarse away from them
    gmsh.model.mesh.field.add("Distance", 1)
    gmsh.model.mesh.field.setNumbers(1, "SurfacesList", term_surfs[0] + term_surfs[1])
    gmsh.model.mesh.field.setNumber(1, "Sampling", 200)
    gmsh.model.mesh.field.add("Threshold", 2)
    gmsh.model.mesh.field.setNumber(2, "InField", 1)
    gmsh.model.mesh.field.setNumber(2, "SizeMin", lc_fine)
    gmsh.model.mesh.field.setNumber(2, "SizeMax", lc_far)
    gmsh.model.mesh.field.setNumber(2, "DistMin", 0.2)
    gmsh.model.mesh.field.setNumber(2, "DistMax", 4.0)
    gmsh.model.mesh.field.setAsBackgroundMesh(2)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)   # HXT, threaded
    gmsh.option.setNumber("General.NumThreads", 8)
    gmsh.model.mesh.generate(3)

    mshfile = out_prefix + ".msh"
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.write(mshfile)
    ntet = len(gmsh.model.mesh.getElementsByType(4)[0])
    gmsh.finalize()

    cfg = {
        "Problem": {"Type": "Electrostatic", "Verbose": 2, "Output": out_prefix + "_out"},
        "Model": {"Mesh": os.path.basename(mshfile), "L0": 1.0e-6},
        "Domains": {"Materials": [{"Attributes": [ATTR["diel"]], "Permittivity": EPS_SIO2}]},
        "Boundaries": {
            "Ground": {"Attributes": [ATTR["far"]]},
            "Terminal": [{"Index": 1, "Attributes": [ATTR["term1"]]},
                         {"Index": 2, "Attributes": [ATTR["term2"]]}],
        },
        "Solver": {"Order": 2, "Device": "CPU",
                   "Linear": {"Type": "BoomerAMG", "KSPType": "CG", "Tol": 1.0e-10, "MaxIts": 500}},
    }
    with open(out_prefix + ".json", "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"{out_prefix}: tets={ntet}  diel_vols={len(diel)} term1_surfs={len(term_surfs[0])} "
          f"term2_surfs={len(term_surfs[1])} far={len(far)}")
    return ntet


if __name__ == "__main__":
    netjson = sys.argv[1]
    pre = sys.argv[2]
    kw = {}
    if len(sys.argv) > 3: kw["lc_fine"] = float(sys.argv[3])
    if len(sys.argv) > 4: kw["margin_xy"] = float(sys.argv[4])
    if len(sys.argv) > 5: kw["z_hi"] = float(sys.argv[5])
    build(netjson, pre, **kw)
