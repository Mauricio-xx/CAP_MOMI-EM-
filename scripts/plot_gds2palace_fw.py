#!/usr/bin/env python3
"""cap_cmomi fd (base+tip vias, _viafix), l=5.5 um width sweep, cmos5l stack:
Palace full-wave (gds2palace in-plane port) and electrostatic vs the Verilog-A
model. One clean full-wave flow, no rf2port mesh artifact.

Two panels: absolute C vs w (top), and EM/model residual in % (bottom) where the
small full-wave fringe and the electrostatic agreement are read off cleanly.
Writes fig/model_vs_gds2palace_fw.png."""
import csv, os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = 5.5

def model(w, l=L):
    ax = int(l / 0.84 + 1e-6); ay = int(w / 0.89 + 1e-6)
    return 1.09 * ax * ay * 0.84 * 0.89 + 0.152 * (ay * 0.89 + 0.42)

def load(path, wkey, ckey):
    out = {}
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            out[float(r[wkey])] = float(r[ckey])
    return out

# gds2palace full-wave sweep (base+tip vias)
fw = load(f"{ROOT}/palace/gds2palace/viafix_fw_sweep.csv", "w_um", "C_fF")
# electrostatic sweep (base+tip vias); fall back to the single canonical w7 point
es = load(f"{ROOT}/palace/es_viacorner/es_viafix_sweep.csv", "w_um", "C12_fF")
if not es:
    es = {7.0: 35.5074}

fw_w = sorted(fw); es_w = sorted(es)
fw_pct = [(fw[w] / model(w) - 1) * 100 for w in fw_w]
es_pct = [(es[w] / model(w) - 1) * 100 for w in es_w]

GREEN, RED, BLUE = "#2ca02c", "#d62728", "#1f77b4"
BOX = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.8, 6.8), sharex=True,
                               gridspec_kw={"height_ratios": [3, 1.5]})

# --- top: absolute C vs w ---
wgrid = np.linspace(1.8, 15.3, 500)
ax1.plot(wgrid, [model(w) for w in wgrid], "-", color=GREEN, lw=1.8,
         label="Verilog-A model (cmos5l, feed=double)")
ax1.plot(fw_w, [fw[w] for w in fw_w], "s", color=RED, ms=10, mec="white", mew=1.2,
         label="Palace full-wave (base+tip vias)")
ax1.plot(es_w, [es[w] for w in es_w], "o", color=BLUE, ms=10, mec="white", mew=1.2,
         label="Palace electrostatic (base+tip vias)")
ax1.set_ylabel("C  (fF)")
ax1.set_title("cap_cmomi fd via-fixed, cmos5l: Palace EM vs Verilog-A model")
ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)
ax1.grid(alpha=0.3)

# --- bottom: EM / model residual in % ---
ax2.axhline(0, color="#444", lw=1.2)
ax2.plot(fw_w, fw_pct, "s-", color=RED, ms=9, mec="white", mew=1.0, lw=1.6,
         label="full-wave / model")
ax2.plot(es_w, es_pct, "o-", color=BLUE, ms=9, mec="white", mew=1.0, lw=1.6,
         label="electrostatic / model")
for w, p in zip(fw_w, fw_pct):
    ax2.annotate(f"+{p:.1f}%", (w, p), textcoords="offset points", xytext=(0, 9),
                 ha="center", fontsize=9, color=RED, bbox=BOX, zorder=5)
ax2.set_ylabel("(EM - model) / model  (%)")
ax2.set_xlabel("width  w  (um)     [length l = 5.5 um]")
ax2.set_ylim(-3, 9)
ax2.text(10.5, 4.3, "full-wave", ha="center", va="top", color=RED, fontsize=9.5)
ax2.text(10.5, 1.9, "electrostatic", ha="center", va="bottom", color=BLUE, fontsize=9.5)
ax2.grid(alpha=0.3)

fig.tight_layout()
out = f"{ROOT}/fig/model_vs_gds2palace_fw.png"
fig.savefig(out, dpi=140)
print("wrote", out)
print("FW w:", fw_w, "%:", [round(p, 1) for p in fw_pct])
print("ES w:", es_w, "%:", [round(p, 1) for p in es_pct])
