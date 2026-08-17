#!/usr/bin/env python3
"""Collapse of all cap_cmomi fd via-fixed (cmos5l, N=4 double) EM results onto
one residual axis. Because the model is area-based, every (w, l) geometry should
fall in the same band regardless of size or aspect ratio: electrostatic ~+1%,
full-wave ~+5% fringe. Pools the square W=L sweep, the l=5.5 width sweep, and the
w=7 length sweep. Writes fig/collapse_wl.png."""
import csv, os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def model(w, l):
    ax = int(l / 0.84 + 1e-6); ay = int(w / 0.89 + 1e-6)
    return 1.09 * ax * ay * 0.84 * 0.89 + 0.152 * (ay * 0.89 + 0.42)

BLUE, RED = "#1f77b4", "#d62728"

# (path, C column, solver, series label, marker, row-filter)
def dbl_n4(r):
    return r.get("feed", "double") == "double" and r.get("N", "4") == "4" \
        and r.get("mmin", "1") == "1" and r.get("mmax", "4") == "4"

SERIES = [
    (f"{ROOT}/results/es_campaign.csv",              "C12_fF", "ES", "square W=L",   "o", dbl_n4),
    (f"{ROOT}/palace/es_viacorner/es_viafix_sweep.csv","C12_fF","ES", "width @l5.5",  "s", None),
    (f"{ROOT}/palace/es_viacorner/es_viafix_lsweep.csv","C12_fF","ES","length @w7",  "^", None),
    (f"{ROOT}/palace/gds2palace/viafix_fw_sweep.csv", "C_fF",   "FW", "width @l5.5",  "s", None),
    (f"{ROOT}/palace/gds2palace/viafix_fw_lsweep.csv","C_fF",   "FW", "length @w7",   "^", None),
]

fig, ax = plt.subplots(figsize=(8.2, 5.2))
ax.axhline(0, color="#444", lw=1.2)
seen_series, seen_solver = {}, {}
for path, ck, solver, slabel, marker, filt in SERIES:
    if not os.path.exists(path):
        continue
    xs, ys = [], []
    for r in csv.DictReader(open(path)):
        if filt and not filt(r):
            continue
        try:
            w, l, C = float(r["w_um"]), float(r["l_um"]), float(r[ck])
        except (KeyError, ValueError):
            continue
        m = model(w, l)
        xs.append(m); ys.append((C / m - 1) * 100)
    if not xs:
        continue
    color = BLUE if solver == "ES" else RED
    ax.scatter(xs, ys, marker=marker, s=90, facecolor=color, edgecolor="white",
               linewidth=1.0, zorder=3)
    seen_series[slabel] = marker
    seen_solver[solver] = color

# reference bands
ax.axhspan(-1, 1, color=BLUE, alpha=0.06)
ax.axhspan(4, 7, color=RED, alpha=0.06)
ax.text(0.985, 0.135, "electrostatic: matches model  (±1%)",
        transform=ax.transAxes, ha="right", color=BLUE, fontsize=9.5)
ax.text(0.985, 0.75, "full-wave: +5% from edge fields",
        transform=ax.transAxes, ha="right", color=RED, fontsize=9.5)

# legends: solver by color, series by marker
from matplotlib.lines import Line2D
h_solver = [Line2D([], [], marker="o", ls="", mfc=c, mec="white", ms=10, label=s)
            for s, c in seen_solver.items()]
h_series = [Line2D([], [], marker=m, ls="", mfc="#888", mec="white", ms=10, label=s)
            for s, m in seen_series.items()]
leg1 = ax.legend(handles=h_solver, loc="upper left", fontsize=9, title="solver")
ax.add_artist(leg1)
ax.legend(handles=h_series, loc="lower left", fontsize=9, title="geometry series")

ax.set_xscale("log")
ax.set_xlabel("model C  (fF, log)")
ax.set_ylabel("(EM - model) / model  (%)")
ax.set_title("cap_cmomi fd via-fixed (cmos5l, N=4 double): EM vs model, all W/L pooled")
ax.set_ylim(-4, 10)
ax.grid(alpha=0.3, which="both")
fig.tight_layout()
out = f"{ROOT}/fig/collapse_wl.png"
fig.savefig(out, dpi=140)
print("wrote", out)
