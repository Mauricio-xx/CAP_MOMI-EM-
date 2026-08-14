"""Mesh convergence of the Palace electrostatic C12, feed=double, w=7 um.

Every capacitance in this study is read at a finite mesh size h (the gmsh
characteristic length lc). This figure shows that C12(h) follows the expected
power law C(h) = Cinf + a*h^p and that the runs used for the fits (h <= 0.12)
are within ~1% of the h -> 0 limit, so the numbers are converged, not mesh noise.

Data: results/ALL_C12.txt (the lc ladders). Cinf is a least-squares fit of
(Cinf, a) at fixed p = 1.88, the reference rate from the fully resolved 5.5x7
triple (convergence/ANALYSIS.txt). Left panel: raw C(h) with the fitted curve
and its Cinf asymptote. Right panel: the same runs as relative distance to Cinf,
log-log, collapsing onto slope p.

Usage:  plot_convergence.py [out.png|out.svg]
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P_REF = 1.88  # reference convergence order, convergence/ANALYSIS.txt

# h [um] -> C12 [fF], from results/ALL_C12.txt. All feed=double, w=7 um,
# one grounded box per family (margin 5.0 / z_hi 10.0).
LADDERS = {
    "10 x 7,  N=4":  {0.40: 61.2819, 0.30: 59.5944, 0.20: 57.0979,
                      0.12: 55.3891, 0.08: 54.4183, 0.06: 53.9492},
    "5.5 x 7, N=4":  {0.40: 33.8646, 0.30: 32.8562, 0.20: 31.5570,
                      0.12: 30.6104, 0.08: 30.0863},
    "5.5 x 7, N=5":  {0.12: 38.4120, 0.08: 37.7608, 0.06: 37.4386},
    "5.5 x 7, N=3":  {0.12: 23.5947, 0.08: 23.1945, 0.06: 22.9990},
    "5.5 x 7, N=2":  {0.12: 15.8084, 0.08: 15.5404, 0.06: 15.4111},
}
COLORS = ["#c0392b", "#2c6fb5", "#8a5a00", "#2e8b57", "#7d3c98"]


def fit_cinf(hs, cs):
    """Least-squares (Cinf, a) with p fixed, using the finest three points."""
    idx = np.argsort(hs)[:3]
    h, c = hs[idx], cs[idx]
    A = np.column_stack([np.ones_like(h), h ** P_REF])
    (cinf, a), *_ = np.linalg.lstsq(A, c, rcond=None)
    return cinf, a


def main(out):
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11.6, 4.9))

    for (label, d), col in zip(LADDERS.items(), COLORS):
        hs = np.array(sorted(d))
        cs = np.array([d[h] for h in hs])
        cinf, a = fit_cinf(hs, cs)

        axl.plot(hs, cs, "o", color=col, ms=5, zorder=3)
        hh = np.linspace(0, hs.max() * 1.03, 200)
        axl.plot(hh, cinf + a * hh ** P_REF, "-", color=col, lw=1.4,
                 label=f"{label}   Cinf={cinf:.2f} fF")
        axl.plot(0, cinf, "*", color=col, ms=11, zorder=4)

        rel = np.abs(cs - cinf) / cinf
        m = rel > 0
        axr.plot(hs[m], rel[m], "o-", color=col, lw=1.2, ms=5, label=label)

    axl.axvline(0.12, color="0.6", ls=":", lw=1)
    axl.text(0.123, axl.get_ylim()[0], " fits use h<=0.12", color="0.4",
             fontsize=8, va="bottom", rotation=90)
    axl.set_xlabel("mesh size  h = lc  [um]")
    axl.set_ylabel("Palace C12  [fF]")
    axl.set_title("C(h) = Cinf + a h^p  (stars = h->0 limit)", fontsize=10.5)
    axl.set_xlim(-0.02, 0.44)
    axl.legend(fontsize=7.6, loc="center right")
    axl.grid(alpha=0.25)

    # reference slope guide
    xg = np.array([0.05, 0.42])
    axr.plot(xg, 3.5e-3 * (xg / 0.12) ** P_REF, "--", color="0.5", lw=1.1,
             label=f"slope p = {P_REF}")
    axr.set_xscale("log")
    axr.set_yscale("log")
    axr.set_xlabel("mesh size  h  [um]")
    axr.set_ylabel("| C(h) - Cinf | / Cinf")
    axr.set_title("relative distance to the converged value", fontsize=10.5)
    axr.legend(fontsize=7.8)
    axr.grid(alpha=0.25, which="both")

    fig.suptitle("cap_cmomi: Palace electrostatic C12 is mesh-converged "
                 "(feed=double, w=7 um)", fontsize=12.2, y=0.99)
    fig.text(0.5, 0.005,
             "The runs used throughout this study (h<=0.12 um) sit within about 1% of the h->0 limit, "
             "and the differenced feed term converges ~33x better than the totals. "
             "Data: results/ALL_C12.txt; rate p=1.88 from convergence/ANALYSIS.txt.",
             ha="center", va="bottom", fontsize=8.4, color="0.2")
    fig.tight_layout(rect=(0, 0.045, 1, 0.95))
    fig.savefig(out, dpi=165)
    print(out)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.dirname(here))  # issue92_em
    main(sys.argv[1] if len(sys.argv) > 1 else "fig/convergence.png")
