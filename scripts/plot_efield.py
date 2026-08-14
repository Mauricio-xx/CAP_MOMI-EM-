"""E-field visualization of the shipped cap_cmomi cell (PCell, l=5.5, w=7, feed=double).

Reads the Palace electrostatic field (single-partition run, so no subdomain gaps), cuts two
planes and colours |E| in the dielectric. Metal is a hole in the mesh (conductors are boundaries),
so the interdigitated fingers and the via towers read as blanks with the field between them.

  Left  : horizontal cut at z=2.25 um (through Metal2) -> finger-to-finger coupling in plane.
  Right : vertical cut at y=3.0 um (x-z) -> layer-to-layer coupling through the via towers.

Usage:  plot_efield.py [out.png|out.svg]
"""
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import LogNorm

VTU = ("/home/montanares/git/slim-pdk/issue92_em/palace/field_run/"
       "pcell_w7_field_out/paraview/electrostatic/Cycle000001/proc000000.vtu")


def read_grid():
    r = vtk.vtkXMLUnstructuredGridReader()
    r.SetFileName(VTU)
    r.Update()
    return r.GetOutput()


def cut(grid, origin, normal):
    pl = vtk.vtkPlane(); pl.SetOrigin(*origin); pl.SetNormal(*normal)
    c = vtk.vtkCutter(); c.SetInputData(grid); c.SetCutFunction(pl); c.Update()
    t = vtk.vtkTriangleFilter(); t.SetInputConnection(c.GetOutputPort()); t.Update()
    poly = t.GetOutput()
    pts = vtk_to_numpy(poly.GetPoints().GetData())
    Emag = np.linalg.norm(vtk_to_numpy(poly.GetPointData().GetArray("E")), axis=1)
    conn = vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    return pts, Emag, conn


def panel(ax, u, v, tris, mag, xlim, ylim, xlabel, ylabel, title):
    # keep triangles fully inside the view so tricontourf does not span the metal holes
    inb = (u >= xlim[0]) & (u <= xlim[1]) & (v >= ylim[0]) & (v <= ylim[1])
    keep = inb[tris].all(axis=1)
    tri = mtri.Triangulation(u, v, tris[keep])
    vmax = np.percentile(mag[inb], 99.0)
    vmin = max(vmax / 1e3, np.percentile(mag[inb], 20.0))
    lev = np.logspace(np.log10(vmin), np.log10(vmax), 24)
    cf = ax.tricontourf(tri, np.clip(mag, vmin, vmax), levels=lev,
                        norm=LogNorm(vmin=vmin, vmax=vmax), cmap="turbo", extend="both")
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal")
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title, fontsize=10.5)
    cb = plt.colorbar(cf, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("|E|  [V/um]", fontsize=8.5); cb.ax.tick_params(labelsize=7.5)


def main(out):
    g = read_grid()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.2, 5.2))

    p, m, c = cut(g, (0, 0, 2.25), (0, 0, 1))          # horizontal, through Metal2
    panel(axL, p[:, 0], p[:, 1], c, m, (-1.1, 6.3), (-0.4, 6.7),
          "x [um]", "y [um]", "Horizontal cut at z=2.25 um (Metal2): finger-to-finger field")

    p, m, c = cut(g, (0, 3.0, 0), (0, 1, 0))            # vertical x-z, through the array
    panel(axR, p[:, 0], p[:, 2], c, m, (-1.1, 6.3), (0.8, 4.8),
          "x [um]", "z [um]", "Vertical cut at y=3.0 um (x-z): layer and via coupling")

    fig.suptitle("cap_cmomi PCell (l=5.5, w=7, feed=double, M1..M4): Palace electrostatic |E|, "
                 "terminal 1 at 1 V", fontsize=12, y=0.99)
    fig.text(0.5, 0.005,
             "Metal is a hole in the mesh (conductors are PEC boundaries): the fingers and the "
             "metal/via stack read as blanks, the field lives in the oxide between opposite-polarity\n"
             "conductors. Single-rank run, so no subdomain gaps (no dummy plane needed).",
             ha="center", va="bottom", fontsize=8.0, color="0.2")
    fig.tight_layout(rect=(0, 0.045, 1, 0.96))
    fig.savefig(out, dpi=160)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fig/efield.png")
