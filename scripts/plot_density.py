"""The area density we did NOT change, and what the row-count fix does to it.

The fix corrects the row COUNT (pure geometry: billed rows now equal drawn rows).
It does not touch the area density, which stays at the flat 1.09 fF/um2 currently
shipped for N=4. This figure shows why the density is a separate, deferred question.

Left: the differenced, mesh-converged coupled-cell density is not constant. It is
~1.83 fF/um2 at the narrowest device and falls to ~0.98 at w=15, crossing the flat
model near w=7. Right: full feed=double devices, old model / Palace and new model /
Palace. Dropping the -1 lifts the badly under-predicted narrow devices toward 1. NOTE:
this figure is built on the superseded sparse-via, single-eps convergence data, where
the flat 1.09 reads high on the wider and near-square parts by 6 to 19%; on the base+tip
via-fixed cell the residual against flat 1.09 collapses to ~+-1%. The single-eps Palace
absolute here is not trustworthy, only its differences are.

Data: convergence/ANALYSIS.txt (converged densities and the model-vs-Palace table).
Model numbers recomputed from the shipped formulas; both agree with ANALYSIS.txt.

Usage:  plot_density.py [out.png|out.svg]
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODEL_DENS_N4 = 1.09

# converged coupled-cell density vs approx width, convergence/ANALYSIS.txt
#   (delta-length per column, extrapolated to h->0 at p=1.88)
DENS = [(2.0, 1.8252), (3.0, 1.3699), (7.0, 1.0664), (15.0, 0.9754)]

# full feed=double devices, convergence/ANALYSIS.txt "Model vs Palace" table.
# model_old uses ny=floor(w/0.89)-1 (as shipped before the fix); model_new drops
# the -1. Palace is the p=1.88 extrapolation. All N=4.
DEVICES = [
    # label     model_old  palace   model_new
    ("2x2",       1.630,    3.078,    3.259),
    ("20x2",     18.742,   31.562,   37.485),
    ("50x2",     48.078,   80.875,   96.156),
    ("5.5x7",    29.336,   29.569,   34.225),
]


def main(out):
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11.8, 4.9))

    # left: density vs width
    w = np.array([d[0] for d in DENS])
    dens = np.array([d[1] for d in DENS])
    axl.plot(w, dens, "o-", color="#c0392b", ms=7, lw=1.6,
             label="differenced Palace, h->0 (uniform eps)")
    axl.axhline(MODEL_DENS_N4, color="#2c6fb5", lw=1.6, ls="--",
                label=f"shipped model, flat {MODEL_DENS_N4} fF/um2 (unchanged)")
    for x, y in zip(w, dens):
        axl.annotate(f"{y:.2f}", (x, y), textcoords="offset points",
                     xytext=(6, 6), fontsize=8.2, color="0.3")
    axl.set_xlabel("device width w  [um]")
    axl.set_ylabel("coupled-cell area density  [fF/um2]")
    axl.set_title("the density is size-dependent; the model keeps it flat",
                  fontsize=10.3)
    axl.set_ylim(0.8, 2.0)
    axl.legend(fontsize=8.2, loc="upper right")
    axl.grid(alpha=0.25)

    # right: model/Palace ratio, old vs new
    labels = [d[0] for d in DEVICES]
    old = np.array([d[1] / d[2] for d in DEVICES])
    new = np.array([d[3] / d[2] for d in DEVICES])
    x = np.arange(len(labels))
    ww = 0.36
    axr.bar(x - ww / 2, old, ww, color="#b0b7bf", label="old model / Palace")
    axr.bar(x + ww / 2, new, ww, color="#2c6fb5", label="new model / Palace (row fix)")
    axr.axhline(1.0, color="0.3", lw=1.0)
    for xi, (o, n) in enumerate(zip(old, new)):
        axr.annotate(f"{o:.2f}", (xi - ww / 2, o), textcoords="offset points",
                     xytext=(0, 3), ha="center", fontsize=7.8, color="0.35")
        axr.annotate(f"{n:.2f}", (xi + ww / 2, n), textcoords="offset points",
                     xytext=(0, 3), ha="center", fontsize=7.8, color="#2c6fb5")
    axr.set_xticks(x)
    axr.set_xticklabels(labels)
    axr.set_ylabel("model C / Palace C   (feed=double)")
    axr.set_xlabel("device  l x w  [um]")
    axr.set_title("the row fix corrects the count, exposing the density",
                  fontsize=10.3)
    axr.set_ylim(0, 1.4)
    axr.legend(fontsize=8.2, loc="lower right")
    axr.grid(alpha=0.25, axis="y")

    fig.suptitle("cap_cmomi: the row-count fix is geometry; the area density is a "
                 "separate, deferred question", fontsize=11.8, y=0.99)
    fig.text(0.5, 0.005,
             "The row-count change (drop the -1) is pure geometry and settled. The area density stays at "
             "the shipped flat 1.09; on this superseded sparse-via single-eps data it reads ~6-19% high, "
             "but on the base+tip via-fixed cell the residual collapses to ~+-1%. "
             "Data: convergence/ANALYSIS.txt (superseded).",
             ha="center", va="bottom", fontsize=8.2, color="0.2")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(out, dpi=165)
    print(out)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.dirname(here))
    main(sys.argv[1] if len(sys.argv) > 1 else "fig/density_vs_size.png")
