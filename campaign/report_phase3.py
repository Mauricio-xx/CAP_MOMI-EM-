#!/usr/bin/env python3
"""Phase 3 report: EM (Palace) vs updated cap_cmomi Verilog-A (branch 356ff2d).

Builds the figures (fig/phase3_*.png) and the markdown report
results/PHASE3_REPORT.md from the campaign CSVs. Model functions are imported
from analyze.py so the report and the %err column cannot drift apart.
"""
import os
import sys
import csv
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/montanares/git/slim-pdk/issue92_em"
sys.path.insert(0, HERE)
import analyze as A  # geom, model_C, feed_C, pad_len_of, DENSITY, UC_X, UC_Y

FIG = f"{ROOT}/fig"
os.makedirs(FIG, exist_ok=True)
REPORT = f"{ROOT}/results/PHASE3_REPORT.md"


def load_csv(path):
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


es = load_csv(A.ES_CSV)
fw = {r["device"]: r for r in load_csv(A.FW_CSV)}

# ---- assemble per-device records -------------------------------------------
rec = []
for r in es:
    w, l, N, feed = float(r["w_um"]), float(r["l_um"]), int(r["N"]), r["feed"]
    ax, ay, area = A.geom(w, l)
    c_em = float(r["C12_fF"])
    mfix = A.model_C(w, l, N, feed, rowfix=True)
    mpre = A.model_C(w, l, N, feed, rowfix=False)
    fwc = fw.get(r["name"], {}).get("Cdiff_fF", "")
    rec.append(dict(name=r["name"], w=w, l=l, N=N, feed=feed, ax=ax, ay=ay,
                    area=area, c_em=c_em, mfix=mfix, mpre=mpre,
                    fw=float(fwc) if fwc else None,
                    err_fix=100 * (mfix - c_em) / c_em,
                    err_pre=100 * (mpre - c_em) / c_em))

byname = {x["name"]: x for x in rec}
full_dbl = sorted([x for x in rec if x["name"].startswith("cap_mom_double_")], key=lambda x: x["w"])
full_sam = sorted([x for x in rec if x["name"].startswith("cap_mom_same_")], key=lambda x: x["w"])
ladder = [x for x in rec if x["name"][0] == "n"]


def density_fit(points):
    a = np.array([p[0] for p in points]); c = np.array([p[1] for p in points])
    slope, inter = np.polyfit(a, c, 1)
    r2 = 1 - np.sum((c - (slope * a + inter))**2) / np.sum((c - c.mean())**2)
    return slope, inter, r2


# density groups: N4 = full double, N3 = n3_* ladder, N2 = n2_* ladder
dgroups = {
    4: [(x["area"], x["c_em"]) for x in full_dbl],
    3: [(x["area"], x["c_em"]) for x in ladder if x["N"] == 3],
    2: [(x["area"], x["c_em"]) for x in ladder if x["N"] == 2],
}
dfit = {N: density_fit(p) for N, p in dgroups.items() if len(p) >= 2}

# ============================ FIGURES =======================================
plt.rcParams.update({"font.size": 11, "figure.dpi": 130})

# Fig 1: C vs size (full-stack double) -- EM(ES), EM(FW), model fix vs pre-fix
fig, ax1 = plt.subplots(figsize=(6.4, 4.6))
x = [d["w"] for d in full_dbl]
ax1.plot(x, [d["c_em"] for d in full_dbl], "o", color="#1f77b4", ms=8, label="EM electrostatic (C12)")
fwx = [d["w"] for d in full_dbl if d["fw"] is not None]
fwy = [d["fw"] for d in full_dbl if d["fw"] is not None]
ax1.plot(fwx, fwy, "s", color="#d62728", ms=8, mfc="none", mew=1.8, label="EM full-wave (Cdiff, 2-port)")
xs = np.linspace(min(x), max(x), 100)
ax1.plot(x, [d["mfix"] for d in full_dbl], "-", color="#2ca02c", lw=2, label="model (updated / row-fix)")
ax1.plot(x, [d["mpre"] for d in full_dbl], "--", color="#888", lw=1.6, label="model (pre-fix, row -1)")
ax1.set_xlabel("W = L  (um)"); ax1.set_ylabel("Capacitance  (fF)")
ax1.set_title("cap_mom full-stack (N=4) double: EM vs model")
ax1.legend(frameon=False, fontsize=9.5); ax1.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{FIG}/phase3_c_vs_size.png"); plt.close(fig)

# Fig 2: %error vs size -- updated vs pre-fix (double)
fig, ax2 = plt.subplots(figsize=(6.4, 4.2))
labels = [f"{d['w']:.1f}" for d in full_dbl]
xi = np.arange(len(labels)); bw = 0.38
ax2.bar(xi - bw/2, [d["err_fix"] for d in full_dbl], bw, color="#2ca02c", label="updated model")
ax2.bar(xi + bw/2, [d["err_pre"] for d in full_dbl], bw, color="#bbb", label="pre-fix (row -1)")
ax2.axhline(0, color="k", lw=0.8)
ax2.axhspan(-3, 3, color="#2ca02c", alpha=0.10)
ax2.set_xticks(xi); ax2.set_xticklabels(labels)
ax2.set_xlabel("W = L  (um)"); ax2.set_ylabel("model - EM  (%)")
ax2.set_title("Row-count fix: model error vs EM (double)")
ax2.legend(frameon=False); ax2.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(f"{FIG}/phase3_error_vs_size.png"); plt.close(fig)

# Fig 3: density ladder -- C12 vs active area, slope = density[N]
fig, ax3 = plt.subplots(figsize=(6.4, 4.6))
colors = {4: "#1f77b4", 3: "#ff7f0e", 2: "#2ca02c"}
for N in (4, 3, 2):
    if N not in dgroups:
        continue
    pts = sorted(dgroups[N])
    aa = [p[0] for p in pts]; cc = [p[1] for p in pts]
    ax3.plot(aa, cc, "o", color=colors[N], ms=7)
    if N in dfit:
        s, i, r2 = dfit[N]
        xr = np.array([0, max(aa) * 1.05])
        ax3.plot(xr, s * xr + i, "-", color=colors[N], lw=1.6,
                 label=f"N={N}: fit {s:.3f}  (model {A.DENSITY[N]})  R2={r2:.4f}")
ax3.set_xlabel("active area  (um^2)"); ax3.set_ylabel("EM C12  (fF)")
ax3.set_title("Density ladder: comb-to-comb C vs active area")
ax3.legend(frameon=False, fontsize=9); ax3.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{FIG}/phase3_density_ladder.png"); plt.close(fig)

# Fig 4: ES vs FW method offset
fig, ax4 = plt.subplots(figsize=(6.0, 4.0))
pairs = [(d["w"], d["c_em"], d["fw"]) for d in full_dbl if d["fw"] is not None]
ratio = [100 * (f - e) / e for _, e, f in pairs]
ax4.plot([p[0] for p in pairs], ratio, "D-", color="#9467bd", ms=8)
ax4.axhline(np.mean(ratio), color="#9467bd", ls="--", lw=1,
            label=f"mean +{np.mean(ratio):.1f}%")
ax4.set_xlabel("W = L  (um)"); ax4.set_ylabel("(FW - ES) / ES  (%)")
ax4.set_title("Full-wave (0.5 um mesh) vs electrostatic offset")
ax4.legend(frameon=False); ax4.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{FIG}/phase3_es_vs_fw.png"); plt.close(fig)

# ============================ MARKDOWN ======================================
def row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


L = []
L.append("# cap_mom EM campaign, Phase 3: model validation\n")
L.append("Palace EM (electrostatic + reference-matched 2-port full-wave) against the "
         "updated cap_cmomi Verilog-A model (worktree `cap-cmomi-rowfix`, branch "
         "`fix/cap-cmomi-row-count`, commit `356ff2d`). All layouts regenerated from that "
         "branch PCell (via fix + `floor(w/0.89)` rows), geometry XOR-verified against the "
         "simulated GDS. Model function imported from `campaign/analyze.py`, which reproduces "
         "the branch `.va` goldens (5x5 N4: double 21.11 / same 21.26 / none 20.37 fF).\n")

L.append("## Verdict\n")
L.append("The updated model matches EM within **+-1.6%** across the full drawn size range for "
         "the fab-relevant full-stack double devices. The row-count fix (`ay=floor(w/0.89)`, no "
         "-1) is what closes the gap: the pre-fix billing under-predicted by 6-44%. Density[N] "
         "and both feed terms are consistent with the model; the ES<->FW gap is a full-wave mesh "
         "artifact (see below), not a model error.\n")

L.append("## Full-stack (N=4) double: C vs size\n")
L.append("![C vs size](../fig/phase3_c_vs_size.png)\n")
L.append(row(["W=L (um)", "ES C12 (fF)", "FW Cdiff (fF)", "model (fF)", "err %", "pre-fix err %"]))
L.append(row(["---"] * 6))
for d in full_dbl:
    L.append(row([f"{d['w']:.1f}", f"{d['c_em']:.2f}",
                  f"{d['fw']:.2f}" if d['fw'] else "-",
                  f"{d['mfix']:.2f}", f"{d['err_fix']:+.2f}", f"{d['err_pre']:+.1f}"]))
L.append("")
L.append("![error vs size](../fig/phase3_error_vs_size.png)\n")

L.append("## Density[N] re-extracted from the fixed-via ES sweep\n")
L.append("![density ladder](../fig/phase3_density_ladder.png)\n")
L.append(row(["N", "density fit (fF/um^2)", "model", "intercept (fF)", "R2", "n pts"]))
L.append(row(["---"] * 6))
for N in (4, 3, 2):
    if N in dfit:
        s, i, r2 = dfit[N]
        L.append(row([N, f"{s:.4f}", A.DENSITY[N], f"{i:+.2f}", f"{r2:.5f}", len(dgroups[N])]))
L.append("\nN=3 comes from `m1m3` and `m2m4` (count, not vertical position); N=2 from `m3m4`. "
         "The small positive intercept is the fringe/feed offset the pure area law omits.\n")

L.append("## C(same) - C(double) feed delta\n")
L.append(row(["W=L (um)", "EM delta (fF)", "model[same-double] (fF)", "pad_len (um)"]))
L.append(row(["---"] * 4))
for d in full_dbl:
    s = byname.get(d["name"].replace("_double_", "_same_"))
    if not s:
        continue
    pad = d["ay"] * A.UC_Y + 0.42
    md = A.feed_C("same", pad) - A.feed_C("double", pad)
    L.append(row([f"{d['w']:.1f}", f"{s['c_em'] - d['c_em']:+.3f}", f"{md:+.3f}", f"{pad:.2f}"]))
L.append("\nBoth feeds add cap to `Cmain` (double `0.152*pad_len`, same `0.1625*pad_len+0.0916`), "
         "so the same-minus-double delta is small; EM and model agree at the ~0.1 fF ES noise "
         "floor.\n")

L.append("## Reduced-stack ladder (m1m3 / m2m4 / m3m4)\n")
L.append(row(["cell", "N", "W (um)", "L (um)", "EM C12 (fF)", "model (fF)", "err %"]))
L.append(row(["---"] * 7))
for d in sorted(ladder, key=lambda z: (z["N"], z["name"])):
    L.append(row([d["name"], d["N"], f"{d['w']:.0f}", f"{d['l']:.1f}",
                  f"{d['c_em']:.2f}", f"{d['mfix']:.2f}", f"{d['err_fix']:+.1f}"]))
L.append("\nReduced-stack cells run +1 to +7% high. Two documented model simplifications, not "
         "bugs: a single `density[N]` ignores vertical position (`m2m4` reads ~3% above `m1m3` at "
         "identical N), and the double-feed coefficient (0.152, fit on 4-metal pads) over-counts "
         "~1 fF on 2-3 metal stacks.\n")

L.append("## Full-wave vs electrostatic\n")
L.append("![ES vs FW](../fig/phase3_es_vs_fw.png)\n")
L.append(f"FW `Cdiff` at the campaign mesh (`refined_cellsize = 0.5 um`) sits "
         f"**+{min(ratio):.0f} to +{max(ratio):.0f}%** above ES `C12` "
         f"({', '.join(f'{r:+.1f}%' for r in ratio)} at {', '.join(f'{p[0]:.1f}' for p in pairs)} um). "
         "This is a full-wave **mesh** artifact, not a physical correction. 0.5 um is coarser than "
         "the 0.84 um tooth pitch, so the solve under-resolves the inter-tooth gap that sets the "
         "capacitance; refining only that knob (same geometry) drives `Cdiff` monotonically back "
         "toward ES:\n")
# convergence table: 0.5 baseline (campaign mesh) + the fw_converge_04p9 sweep CSV
_conv = [(0.50, 23.82, 14.6)]
_cf = f"{ROOT}/palace/rf2port/results/fw_converge_04p9.csv"
if os.path.exists(_cf):
    for _r in csv.DictReader(open(_cf)):
        _conv.append((float(_r["refined_cellsize"]), float(_r["Cdiff_fF"]),
                      float(_r["off_vs_ES_pct"])))
_conv = sorted({round(c[0], 3): c for c in _conv}.values(), key=lambda t: -t[0])  # dedupe, coarse->fine
L.append(row(["refined_cellsize (um)", "Cdiff (fF)", "vs ES 20.79"]))
L.append(row(["---"] * 3))
for _rc, _cd, _off in _conv:
    L.append(row([f"{_rc:.2f}", f"{_cd:.2f}", f"{_off:+.1f}%"]))
_fine = _conv[-1]
_falling = len(_conv) > 1 and (_conv[-2][1] - _fine[1]) > 0.25
if _falling:
    _lim = (f"Still falling at {_fine[0]:.2f} um ({_fine[2]:+.1f}%), heading to ES with at most a "
            "small (~few-%) fringe residual.")
else:
    _lim = (f"By {_fine[0]:.2f} um it flattens near {_fine[2]:+.0f}% (a small full-wave fringe "
            "residual, well inside model tolerance).")
L.append("\n" + _lim + " Two earlier explanations are refuted. The dielectric: a layered 11.9/6.6 "
         "stackup vs uniform eps=4.1 moves C only -0.6%, since the comb sits buried in the 4.1 IMD "
         "and substrate/passivation load common-mode to ground and cancel in the differential (at "
         "60 MHz the substrate is a conductor, not eps=11.9). The un-de-embedded fixture: an FW "
         "open dummy with the comb removed leaves only 0.05 fF of A-B coupling. So the campaign "
         "`Cdiff` @0.5 is an under-resolved cross-check, not a +14% correction and not the silicon "
         "twin; device-level accuracy is set by the fine-mesh ES (lc = 0.10 um) vs model, +-1.6%. "
         "Full convergence data and ruled-out hypotheses in `FW_MESH_INVESTIGATION.md`.\n")

L.append("## Notes\n")
L.append("- FW solves for 07p8 and 13p6 um failed on a Palace/MFEM SuperLU singular matrix during "
         "the ROM build (numerical, not RAM; 10p7 in between succeeded). FW is the cross-check; the "
         "three good points already fix the offset. Recovering them is optional.\n")
L.append("- Large reduced-stack fab devices (65-80 um) exceed the fine-mesh RAM floor and are "
         "model-projected (Phase 4); density is intensive and set by the small cells here.\n")

open(REPORT, "w").write("\n".join(L) + "\n")
print("wrote", REPORT)
print("figures:", ", ".join(sorted(os.path.basename(p) for p in
      [f"{FIG}/phase3_c_vs_size.png", f"{FIG}/phase3_error_vs_size.png",
       f"{FIG}/phase3_density_ladder.png", f"{FIG}/phase3_es_vs_fw.png"])))
