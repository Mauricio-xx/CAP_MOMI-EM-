#!/usr/bin/env python3
"""cap_cmomi Verilog-A model vs Palace EM, feed=double, l=5.5, N=4 (M1..M4),
via-fixed cell. The model reproduces the ELECTROSTATIC solve to ~1%; the single
full-wave point we have (w=7) sits ~5% higher, the fringing the ES solve omits.
Writes fig/model_vs_em.png."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

w = np.array([5, 7, 10, 15])

# Verilog-A model, feed=double: c_active(1.09) + 0.152*pad_len
def model(wi):
    nx = 6                      # floor(5.5/0.84)
    ny = int(wi / 0.89 + 1e-6)
    area = nx * 0.84 * ny * 0.89
    pad = ny * 0.89 + 0.42
    return 1.09 * area + 0.152 * pad

m = np.array([model(wi) for wi in w])
es = np.array([24.8512, 34.8017, 54.6960, 79.6425])   # Palace electrostatic, feed campaign
fw_w = 7
fw = 37.1176                                           # Palace full-wave, via_matrix (fd)
es_vm = 35.5074                                        # ES at w7, via_matrix setup (setup spread)

ww = np.linspace(4.5, 15.5, 60)
mm = np.array([model(x) for x in ww])

fig, ax = plt.subplots(figsize=(7.4, 5.0))
ax.plot(ww, mm, "-", color="#1f77b4", lw=1.8, label="Verilog-A model (feed=double)")
ax.plot(w, es, "o", color="#1f77b4", ms=8, label="Palace electrostatic")
ax.plot([fw_w], [fw], "s", color="#d62728", ms=11, label="Palace full-wave (single geometry)")
ax.plot([fw_w], [es_vm], "o", mfc="none", mec="#1f77b4", ms=11,
        label="ES, alt. setup (spread)")

# gap annotation at w=7
ax.annotate("", xy=(fw_w, fw), xytext=(fw_w, model(7)),
            arrowprops=dict(arrowstyle="<->", color="#d62728", lw=1.2))
ax.annotate(f"full-wave  +{100*(fw/model(7)-1):.0f}%\nabove model",
            xy=(fw_w, (fw + model(7)) / 2), xytext=(7.5, 40),
            fontsize=9, color="#d62728",
            arrowprops=dict(arrowstyle="-", color="#d62728", lw=0.6))
ax.text(11.2, 58, "model tracks electrostatic\nto ~1% across width",
        fontsize=9, color="#1f77b4")

ax.set_xlabel("width w  (um)")
ax.set_ylabel("C  (fF)  [feed=double, l=5.5, M1..M4]")
ax.set_title("cap_cmomi: Verilog-A model vs Palace EM (via-fixed cell)")
ax.legend(fontsize=8.5, loc="upper left")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("fig/model_vs_em.png", dpi=140)
print("wrote fig/model_vs_em.png")
print("model:", np.round(m, 2))
print("es   :", es, "  model/ES:", np.round(m / es, 3))
print(f"w7 full-wave {fw}  model {model(7):.2f}  model/FW {model(7)/fw:.3f}")
