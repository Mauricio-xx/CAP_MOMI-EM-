"""Build a Palace electrostatic capacitance model with a Z-LAYERED dielectric.

WHY THIS EXISTS (and the caveat that came with it)
---------------------------------------------------
This is the layered-eps variant of build_model.py, written to test whether the
constant 0.864x per-N area-density gap between our uniform-eps Palace (eps=4.1)
and the MOM model development reference notes is a dielectric/eps_eff
effect. The dielectric story needs eps_eff ~= 4.74 (since 4.1/0.864 = 4.745).

That inference was REFUTED before this script was run. The authoritative PDK
extraction
  /home/montanares/git/slim-pdk/IHP-Open-PDK/ihp-sg13cmos5l-worktrees/
      cap-cmomi-rowfix/libs.tech/magic/ihp-sg13cmos5l-extract.tech
gives eps_eff = 4.100 for EVERY inter-metal overlap, self-consistently:
  L245 defaultoverlap allm2 metal2 allm1 metal1 = 67.225 aF/um^2, gap 0.54 um
  L281 (M3/M2) = 67.225,  L322 (M4/M3) = 67.225   -> 67.225e-3 * 0.54 / 0.008854 = 4.100
  L368 (TopMetal/Metal4)  = 42.708 aF/um^2, gap 0.85 um  -> 42.708e-3 * 0.85 / 0.008854 = 4.100
The cmax/cmin corners (L447=73.947 -> 4.51, L649=60.502 -> 3.69) are pure +/-10%
margins; even the upper corner never reaches 4.74.

CONSEQUENCE: the "pdk-eps profile" is UNIFORM 4.100 in every IMD z-slab. So the
Z-layering below assigns eps=4.100 to every slab, and this model is numerically
DEGENERATE with build_model.py (uniform 4.1). Running it will reproduce ~4.10 and
~1.16 fF/um^2 at N=5; it CANNOT climb toward the reference 1.36, because the PDK has no
higher permittivity anywhere and this solver cannot reproduce his via/solver
setup artifacts. The reconciliation therefore graded a layered run NOT_WORTH_IT.
This file is kept as a best-effort artifact: if you want to vary the per-slab eps
by hand (a hypothesis test the PDK does not support), edit EPS_PROFILE below.

Everything else (mesh sizing, solver, PEC Terminal conductors, farfield Ground)
is identical to build_model.py.

Z-LAYERING (um), boundaries taken from the PDK stackup in netsplit.py / the N=5
stack stored in the input JSON. Each band is one Material with its own eps. The
metal/via z-ranges align to these band boundaries, so every conductor sits inside
a single band. eps values are the PDK-authoritative 4.100 (SiO2) throughout:

  band            z_bottom  z_top   eps     note
  sub_below       z_lo      1.04    4.100   fill below Metal1
  M1              1.04      1.46    4.100   Metal1 level
  IMD_V1 (M1-M2)  1.46      2.00    4.100   Via1 gap
  M2              2.00      2.49    4.100   Metal2 level
  IMD_V2 (M2-M3)  2.49      3.03    4.100   Via2 gap
  M3              3.03      3.52    4.100   Metal3 level
  IMD_V3 (M3-M4)  3.52      4.06    4.100   Via3 gap
  M4              4.06      4.55    4.100   Metal4 level
  IMD_V4 (M4-M5)  4.55      5.09    4.100   Via4 gap
  M5              5.09      5.58    4.100   Metal5 level
  top_above       5.58      z_hi    4.100   fill above Metal5
"""
import json, os, sys
import gmsh

# (z_bottom, z_top, eps, name). z_lo / z_hi are patched in at build time for the
# open bottom and top bands (sentinels None). All eps = 4.100 per the authoritative
# PDK extraction (see module docstring); edit here only for a hand hypothesis test.
EPS_PROFILE = [
    (None, 1.04, 4.100, "sub_below"),
    (1.04, 1.46, 4.100, "M1"),
    (1.46, 2.00, 4.100, "IMD_V1"),
    (2.00, 2.49, 4.100, "M2"),
    (2.49, 3.03, 4.100, "IMD_V2"),
    (3.03, 3.52, 4.100, "M3"),
    (3.52, 4.06, 4.100, "IMD_V3"),
    (4.06, 4.55, 4.100, "M4"),
    (4.55, 5.09, 4.100, "IMD_V4"),
    (5.09, 5.58, 4.100, "M5"),
    (5.58, None, 4.100, "top_above"),
]


def build(netjson, out_prefix, lc_fine=0.15, lc_far=2.0, margin_xy=3.0, z_lo=-1.0, z_hi=8.0,
          domain=None):
    data = json.load(open(netjson))
    STACK = data["stack"]
    ORDER = list(STACK.keys())
    nets = data["nets"]

    # resolve the open bottom/top bands against the domain z extent
    bands = []
    for zb, zt, eps, name in EPS_PROFILE:
        zb = z_lo if zb is None else zb
        zt = z_hi if zt is None else zt
        assert zt > zb, f"band {name} has non-positive thickness ({zb},{zt})"
        bands.append((zb, zt, eps, name))
    assert abs(bands[0][0] - z_lo) < 1e-9 and abs(bands[-1][1] - z_hi) < 1e-9, \
        "band stack must span z_lo..z_hi exactly"
    for a, b in zip(bands, bands[1:]):
        assert abs(a[1] - b[0]) < 1e-9, "bands must be contiguous in z (no gaps/overlaps)"

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

    # ONE domain box in build_model.py -> here, one slab box per Z band.
    slab_tags = []
    for zb, zt, eps, name in bands:
        slab_tags.append(occ.addBox(x0, y0, zb, x1-x0, y1-y0, zt-zb))
    occ.synchronize()

    cond = net_vols[0] + net_vols[1]
    slabs_dimtags = [(3, t) for t in slab_tags]
    out, omap = occ.fragment(slabs_dimtags, cond)
    occ.synchronize()

    # omap layout: first len(slabs) entries map the slab boxes, the rest map the
    # conductors (fragment preserves input order).
    nslab = len(slabs_dimtags)
    slab_pieces = []
    for i in range(nslab):
        slab_pieces.append({t for (d, t) in omap[i] if d == 3})

    cond_pieces = [set(), set()]
    for i, dt in enumerate(cond):
        pieces = {t for (d, t) in omap[nslab + i] if d == 3}
        which = 0 if i < len(net_vols[0]) else 1
        cond_pieces[which] |= pieces
    all_cond = cond_pieces[0] | cond_pieces[1]

    # per-band dielectric = that band's pieces minus every conductor piece
    band_diel = []
    for i in range(nslab):
        band_diel.append(sorted(slab_pieces[i] - all_cond))
    diel_all = sorted({t for bd in band_diel for t in bd})

    term_surfs = []
    for k in (0, 1):
        vols = [(3, t) for t in sorted(cond_pieces[k])]
        bnd = gmsh.model.getBoundary(vols, combined=True, oriented=False)
        term_surfs.append(sorted({t for (d, t) in bnd if d == 2}))

    # far boundary = outer faces of the whole dielectric block (union of all bands)
    all_diel_bnd = gmsh.model.getBoundary([(3, t) for t in diel_all], combined=True, oriented=False)
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
    occ.remove([(3, t) for t in sorted(all_cond)], recursive=False)
    occ.synchronize()

    # attributes: bands 1..nslab, then terminals and far after them
    band_attr = [i + 1 for i in range(nslab)]
    ATTR = dict(term1=nslab + 1, term2=nslab + 2, far=nslab + 3)
    for i in range(nslab):
        if band_diel[i]:
            gmsh.model.addPhysicalGroup(3, band_diel[i], band_attr[i], name="diel_" + bands[i][3])
    gmsh.model.addPhysicalGroup(2, term_surfs[0], ATTR["term1"], name="terminal1")
    gmsh.model.addPhysicalGroup(2, term_surfs[1], ATTR["term2"], name="terminal2")
    gmsh.model.addPhysicalGroup(2, far, ATTR["far"], name="farfield")

    # mesh sizing: fine on the conductor surfaces, coarse away from them (identical
    # to build_model.py)
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

    # one Material per non-empty band, each with its band eps
    materials = []
    for i in range(nslab):
        if band_diel[i]:
            materials.append({"Attributes": [band_attr[i]], "Permittivity": bands[i][2]})

    cfg = {
        "Problem": {"Type": "Electrostatic", "Verbose": 2, "Output": out_prefix + "_out"},
        "Model": {"Mesh": os.path.basename(mshfile), "L0": 1.0e-6},
        "Domains": {"Materials": materials},
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
    nb = sum(1 for i in range(nslab) if band_diel[i])
    print(f"{out_prefix}: tets={ntet}  bands={nb} diel_vols={len(diel_all)} "
          f"term1_surfs={len(term_surfs[0])} term2_surfs={len(term_surfs[1])} far={len(far)}")
    return ntet


if __name__ == "__main__":
    netjson = sys.argv[1]
    pre = sys.argv[2]
    kw = {}
    if len(sys.argv) > 3: kw["lc_fine"] = float(sys.argv[3])
    if len(sys.argv) > 4: kw["margin_xy"] = float(sys.argv[4])
    if len(sys.argv) > 5: kw["z_hi"] = float(sys.argv[5])
    build(netjson, pre, **kw)
