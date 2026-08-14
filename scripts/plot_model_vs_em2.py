#!/usr/bin/env python3
"""cap_cmomi model vs all EM we have, as C_EM / C_model (feed=double, N=4).
Electrostatic (5 square sizes) hugs the model to ~1%. The rf2port 2-port Cdiff
sits ~+14%, but that is a full-wave MESH artifact: the campaign ran
refined_cellsize=0.5um, coarser than the 0.84um tooth pitch, so it under-resolved
the inter-tooth gap; refining drives Cdiff down from +14% to a ~+4% floor
(23.82->21.63 over 0.5->0.18um, flattens by 0.18; see FW_MESH_INVESTIGATION.md).
That converged ~+4% matches the gds2palace in-plane port ~+5%: both are the genuine
small full-wave fringe, well inside model tolerance. Writes fig/model_vs_em_ratio.png."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def model(w, l):
    ax = int(l / 0.84 + 1e-6); ay = int(w / 0.89 + 1e-6)
    return 1.09 * ax * ay * 0.84 * 0.89 + 0.152 * (ay * 0.89 + 0.42)

# ES double N=4 (es_campaign.csv), square w=l
es = [(2.0, 3.5366), (4.9, 20.7907), (7.8, 59.3656), (10.7, 118.3299), (13.6, 196.6660)]
es_x = [model(w, w) for w, _ in es]
es_r = [c / model(w, w) for w, c in es]

# FW rf2port Cdiff (rf2port_results.csv), square w=l
fw = [(2.0, 4.13), (4.9, 23.82), (10.7, 134.52)]
fw_x = [model(w, w) for w, _ in fw]
fw_r = [c / model(w, w) for w, c in fw]

# FW gds2palace (via_matrix), fd cell l=5.5 w=7
g_model = model(7, 5.5)
g_x = [g_model]; g_r = [37.1176 / g_model]

fig, ax = plt.subplots(figsize=(7.6, 4.8))
ax.axhline(1.0, color="#444", lw=1.2, ls="-", label="Verilog-A model")
ax.plot(es_x, es_r, "o", color="#1f77b4", ms=8, label="Palace electrostatic (5 sizes)")
ax.plot(fw_x, fw_r, "s", color="#d62728", ms=9, label="Full-wave rf2port (2-port Cdiff)")
ax.plot(g_x, g_r, "^", color="#ff7f0e", ms=11, label="Full-wave gds2palace (in-plane port)")
ax.axhspan(0.99, 1.01, color="#1f77b4", alpha=0.08)

ax.text(4, 1.155, "rf2port ~+14%\n(FW mesh @0.5um, not physical)",
        fontsize=8.5, color="#d62728")
ax.text(40, 1.065, "gds2palace ~+5%", fontsize=8.5, color="#ff7f0e")
ax.text(6, 0.965, "electrostatic within ~1% of model", fontsize=8.5, color="#1f77b4")

ax.set_xscale("log")
ax.set_xlabel("model C  (fF, log)")
ax.set_ylabel("C(EM) / C(model)")
ax.set_ylim(0.94, 1.20)
ax.set_title("cap_cmomi: EM vs Verilog-A model (feed=double, N=4)")
ax.legend(fontsize=8, loc="upper right")
ax.grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig("fig/model_vs_em_ratio.png", dpi=140)
print("wrote fig/model_vs_em_ratio.png")
print("ES ratios :", [round(r, 3) for r in es_r])
print("FW rf2port:", [round(r, 3) for r in fw_r])
print("FW g2palace:", [round(r, 3) for r in g_r])
