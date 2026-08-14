#!/usr/bin/env python3
"""Feed campaign on the via-fixed cell: single-side feed validates the model
CFEED line; opposite-side (double) feed shows a real, previously-dropped
residual ~0.152*pad_len. Writes fig/feed_fix.png."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

pad = np.array([4.87, 6.65, 10.21, 14.66])
w   = [5, 7, 10, 15]
cs  = np.array([0.8905, 1.1834, 1.7647, 2.4930])   # C(same) - C(none)
rd  = np.array([0.7271, 0.9949, 1.5200, 2.2611])   # C(dbl)  - C(none)

xx = np.linspace(4, 15.5, 50)
same_model = 0.1625 * xx + 0.0916
dbl_model  = 0.152 * xx                            # new term, through origin

fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.plot(xx, same_model, "-", color="#1f77b4", lw=1.6,
        label="single-side model  0.1625·pad_len + 0.0916")
ax.plot(pad, cs, "o", color="#1f77b4", ms=8, label="single-side measured")
ax.plot(xx, dbl_model, "-", color="#d62728", lw=1.6,
        label="double-feed new term  0.152·pad_len")
ax.plot(pad, rd, "s", color="#d62728", ms=8, label="double-feed measured")
ax.axhline(0, color="#999", lw=0.8, ls=":")
for x, y, ww in zip(pad, rd, w):
    ax.annotate(f"w{ww}", (x, y), textcoords="offset points",
                xytext=(6, -12), fontsize=8, color="#d62728")

ax.set_xlabel("pad_len = ny·0.89 + 0.42  (um)")
ax.set_ylabel("feed capacitance vs bare array  (fF)")
ax.set_title("cap_cmomi feed terms on the via-fixed cell (electrostatic, N=4, l=5.5)")
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("fig/feed_fix.png", dpi=140)
print("wrote fig/feed_fix.png")
