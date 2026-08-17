#!/usr/bin/env python3
"""Phase 3 report: EM (Palace) vs updated cap_cmomi Verilog-A (branch 1e93ffc).

Builds the figures (fig/phase3_*.png) and the markdown report
results/PHASE3_REPORT.md from the campaign CSVs. Model functions are imported
from analyze.py so the report and the %err column cannot drift apart.

NOTE: results/PHASE3_REPORT.md is hand-maintained since the gds2palace full-wave
update. This generator emits the electrostatic campaign tables and figures only;
the gds2palace full-wave section in the report is hand-added. Re-apply that
section if you regenerate.
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

# ---- assemble per-device records -------------------------------------------
rec = []
for r in es:
    w, l, N, feed = float(r["w_um"]), float(r["l_um"]), int(r["N"]), r["feed"]
    ax, ay, area = A.geom(w, l)
    c_em = float(r["C12_fF"])
    mfix = A.model_C(w, l, N, feed, rowfix=True)
    mpre = A.model_C(w, l, N, feed, rowfix=False)
    rec.append(dict(name=r["name"], w=w, l=l, N=N, feed=feed, ax=ax, ay=ay,
                    area=area, c_em=c_em, mfix=mfix, mpre=mpre,
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

# ============================ MARKDOWN ======================================
def row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


L = []
L.append("# cap_mom EM campaign, Phase 3: model validation\n")
L.append("Palace electrostatic EM against the "
         "updated cap_cmomi Verilog-A model (branch "
         "`fix/cap-cmomi-row-count`, commit `1e93ffc`). All layouts regenerated from that "
         "branch PCell (via fix + `floor(w/0.89)` rows), geometry XOR-verified against the "
         "simulated GDS. Model function imported from `campaign/analyze.py`, which reproduces "
         "the branch `.va` goldens (5x5 N4: double 21.12 / same 21.26 / none 20.37 fF).\n")

L.append("## Verdict\n")
L.append("The updated model matches EM within **+-1.6%** across the full drawn size range for "
         "the fab-relevant full-stack double devices. The row-count fix (`ay=floor(w/0.89)`, no "
         "-1) is what closes the gap: the pre-fix billing under-predicted by 6-44%. Density[N] "
         "and both feed terms are consistent with the model.\n")

L.append("## Full-stack (N=4) double: C vs size\n")
L.append("![C vs size](../fig/phase3_c_vs_size.png)\n")
L.append(row(["W=L (um)", "ES C12 (fF)", "model (fF)", "err %", "pre-fix err %"]))
L.append(row(["---"] * 5))
for d in full_dbl:
    L.append(row([f"{d['w']:.1f}", f"{d['c_em']:.2f}",
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

L.append("## Notes\n")
L.append("- Large reduced-stack fab devices (65-80 um) exceed the fine-mesh RAM floor and are "
         "model-projected (Phase 4); density is intensive and set by the small cells here.\n")

open(REPORT, "w").write("\n".join(L) + "\n")
print("wrote", REPORT)
print("figures:", ", ".join(sorted(os.path.basename(p) for p in
      [f"{FIG}/phase3_c_vs_size.png", f"{FIG}/phase3_error_vs_size.png",
       f"{FIG}/phase3_density_ladder.png"])))
