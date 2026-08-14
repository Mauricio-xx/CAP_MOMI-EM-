"""The single-side feed term: drawn (Palace) vs the old model, and the new fit.

This is the one EM-calibrated change in the fix. The drawn feed capacitance is
measured as C(feed='same') - C(feed='none') in one shared domain per width, so
the uniform-dielectric absolute systematic and the common-mode mesh bias cancel.
The four points fall on a straight line in pad_len, and the shipped model uses
F_same = 0.1625*pad_len + 0.0916 fF. The old model billed cfeed_per_um*feed_width,
about 6.5x more at w=7 and growing the wrong way with width.

Left: F_same drawn vs pad_len, the fit line, and the noise band (+/- 3.5 aF, the
differenced floor from 8 exact-repeat runs). Right: the fit residuals in aF against
that band; and, on a log axis, the old model's cfeed over the drawn value.

Data: palace/index.json (same/none C12 per width, l=5.5, lc 0.10).

Usage:  plot_feed_fit.py [out.png|out.svg]
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SLOPE, END = 0.1625, 0.0916          # shipped CFEED_SLOPE, CFEED_END [fF/um, fF]
NOISE_AF = 3.5                        # differenced noise floor [aF]
DENS_N4_CFEED_PER_UM = 1.28          # old model coefficient at N=4

# width -> (C_same, C_none) [fF], palace/index.json, l=5.5, lc 0.10.
FEED = {2: (8.7748, 8.3275), 5: (21.783, 20.8974),
        7: (30.4514, 29.2801), 15: (69.4653, 66.9922)}


def rows(w):        # drawn coupled rows = floor(w/0.89)
    return int(np.floor(w / 0.89 + 1e-6))


def pad_len(w):     # new regressor: array height + two half-bars
    return rows(w) * 0.89 + 0.42


def feed_width_old(w):   # old model: (floor(w/0.89)-1)*0.89 + 0.64
    return (rows(w) - 1) * 0.89 + 0.64


def main(out):
    ws = np.array(sorted(FEED))
    pl = np.array([pad_len(w) for w in ws])
    Fdrawn = np.array([FEED[w][0] - FEED[w][1] for w in ws])
    Ffit = SLOPE * pl + END
    resid_af = (Fdrawn - Ffit) * 1e3
    cfeed_old = DENS_N4_CFEED_PER_UM * np.array([feed_width_old(w) for w in ws])

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11.8, 4.9),
                                   gridspec_kw={"width_ratios": [1.15, 1.0]})

    # left: the fit
    xx = np.linspace(0, pl.max() * 1.05, 100)
    band = NOISE_AF * 1e-3
    axl.fill_between(xx, SLOPE * xx + END - band, SLOPE * xx + END + band,
                     color="#2c6fb5", alpha=0.15, lw=0,
                     label=f"+/- {NOISE_AF:.1f} aF noise floor")
    axl.plot(xx, SLOPE * xx + END, "-", color="#2c6fb5", lw=1.6,
             label=f"F_same = {SLOPE}*pad_len + {END} fF")
    axl.plot(pl, Fdrawn, "o", color="#c0392b", ms=7, zorder=4,
             label="drawn (Palace, same - none)")
    for w, x, y in zip(ws, pl, Fdrawn):
        axl.annotate(f"w={w}", (x, y), textcoords="offset points",
                     xytext=(6, -12), fontsize=8.2, color="0.3")
    axl.set_xlabel("pad_len = floor(w/0.89)*0.89 + 0.42  [um]")
    axl.set_ylabel("single-side feed capacitance  [fF]")
    axl.set_title("Palace supports the feed fit to the last digit", fontsize=10.5)
    axl.set_xlim(0, pl.max() * 1.05)
    axl.set_ylim(0, Fdrawn.max() * 1.15)
    axl.legend(fontsize=8.2, loc="upper left")
    axl.grid(alpha=0.25)

    # right top: residuals in aF
    axr.axhspan(-NOISE_AF, NOISE_AF, color="0.75", alpha=0.4,
                label=f"+/- {NOISE_AF:.1f} aF floor")
    axr.axhline(0, color="0.4", lw=0.8)
    axr.plot(ws, resid_af, "o-", color="#2c6fb5", ms=6)
    for w, r in zip(ws, resid_af):
        axr.annotate(f"{r:+.1f}", (w, r), textcoords="offset points",
                     xytext=(6, 4), fontsize=8, color="#2c6fb5")
    axr.set_xscale("log")
    axr.set_xticks(ws)
    axr.set_xticklabels([str(w) for w in ws])
    axr.set_xlabel("device width w  [um]")
    axr.set_ylabel("fit residual  [aF]")
    axr.set_ylim(-6, 6)
    axr.set_title("residuals sit at the noise floor", fontsize=10.5)
    axr.legend(fontsize=8, loc="lower right")
    axr.grid(alpha=0.25)

    fig.suptitle("cap_cmomi single-side feed: measured, fitted, and 6.5x below "
                 "what the old model billed", fontsize=12.0, y=0.99)
    ratio = cfeed_old[ws.tolist().index(7)] / Fdrawn[ws.tolist().index(7)]
    fig.text(0.5, 0.005,
             "Old model at w=7, N=4: cfeed = 1.28*5.98 = 7.65 fF against a drawn 1.17 fF "
             f"({ratio:.1f}x over), and it grew 2.3x from w=7 to w=15 while the drawn feed grew 2.1x. "
             "The new term is fitted to the drawn value; feed=double is untouched.",
             ha="center", va="bottom", fontsize=8.4, color="0.2")
    fig.tight_layout(rect=(0, 0.045, 1, 0.95))
    fig.savefig(out, dpi=165)
    print(out)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.dirname(here))
    main(sys.argv[1] if len(sys.argv) > 1 else "fig/feed_fit.png")
