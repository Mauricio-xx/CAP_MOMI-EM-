#!/usr/bin/env python3
"""cap_cmomi released vs corrected model across finger length l and width w.

Default feed=double device, N=4 (valid on both PDKs; g2 also allows N=5).
One panel per l, sweeping w. Also writes a value table (released, corrected,
delta) over a realistic (l, w) grid.

  released :  rows = floor(w/0.89) - 1 (min 1) ,  double feed = 0
  corrected:  rows = floor(w/0.89)     (min 2) ,  double feed = 0.152*pad_len
  pad_len  =  rows*0.89 + 0.42 ,  active_area = floor(l/0.84)*0.84 * rows*0.89
  density[N] unchanged.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DENSITY = {2: 0.55, 3: 0.82, 4: 1.09, 5: 1.36}
CFEED2  = 0.152
UX, UY  = 0.84, 0.89

def teeth(l):        return np.floor(np.asarray(l) / UX + 1e-6)
def rows_old(w):     return np.maximum(np.floor(np.asarray(w) / UY + 1e-6) - 1.0, 1.0)
def rows_new(w):     return np.maximum(np.floor(np.asarray(w) / UY + 1e-6), 2.0)

def c_old(l, w, N):
    r = rows_old(w)
    return DENSITY[N] * teeth(l) * UX * r * UY
def c_new(l, w, N):
    r = rows_new(w)
    return DENSITY[N] * teeth(l) * UX * r * UY + CFEED2 * (r * UY + 0.42)

N = 4
L_LIST = [2, 5, 10, 20]
w = np.linspace(2.0, 30.0, 600)          # um, continuous sweep (staircase in rows)

fig, axes = plt.subplots(2, 2, figsize=(10.6, 7.2), sharex=True)
REF_W = [5, 10, 20]                       # reference widths marked on each panel
for ax, l in zip(axes.ravel(), L_LIST):
    co, cn = c_old(l, w, N), c_new(l, w, N)
    ax.fill_between(w, co, cn, color="#1f77b4", alpha=0.12)
    ax.plot(w, co, "--", color="#888", lw=1.5, label="released")
    ax.plot(w, cn, "-",  color="#1f77b4", lw=1.9, label="corrected (PR)")
    # reference-width dots on the corrected curve + a small value table
    tbl = ["w   old    new    +%"]
    for wv in REF_W:
        o, c = float(c_old(l, wv, N)), float(c_new(l, wv, N))
        ax.plot(wv, c, "o", color="#d62728", ms=5.5, zorder=5)
        tbl.append(f"{wv:>2}  {o:5.1f}  {c:5.1f}  {100*(c/o-1):3.0f}")
    ax.text(0.985, 0.05, "\n".join(tbl), transform=ax.transAxes,
            ha="right", va="bottom", fontsize=8, color="#d62728",
            family="monospace",
            bbox=dict(boxstyle="round", fc="white", ec="#d62728", alpha=0.75))
    ax.set_title(f"l = {l} um   ->   teeth = floor(l/0.84) = {int(teeth(l))}",
                 fontsize=9.5)
    ax.grid(alpha=0.3)
    if l == L_LIST[0]:
        ax.legend(fontsize=9, loc="upper left")
for ax in axes[-1]:
    ax.set_xlabel("width  w  (um)   ->   rows = floor(w/0.89)")
for ax in axes[:, 0]:
    ax.set_ylabel("capacitance  (fF)")

fig.suptitle("cap_cmomi model: released vs corrected  (default feed=double, N=4)",
             fontsize=12, y=0.990)
fig.text(0.5, 0.944,
         "C = density[N] * (teeth*0.84) * (rows*0.89) + Cfeed_double     "
         "red dots: w = 5, 10, 20 um",
         ha="center", va="top", fontsize=8.8)
fig.text(0.5, 0.920,
         "N = stacked metal layers M1..MN  ->  "
         "density {2:0.55, 3:0.82, 4:1.09, 5:1.36} fF/um^2   (N=5 g2 only)",
         ha="center", va="top", fontsize=8.2, color="#333")
fig.text(0.5, 0.898,
         "PR fixes rows (was floor(w/0.89)-1) and adds "
         "Cfeed_double = 0.152*pad_len (was 0)",
         ha="center", va="top", fontsize=8.2, color="#333")
fig.tight_layout(rect=(0, 0, 1, 0.878))
fig.savefig("fig/model_grid_l_w.png", dpi=140)
fig.savefig("fig/model_grid_l_w.svg")
print("wrote fig/model_grid_l_w.png")

# ---- value table over a realistic device grid ----------------------------
L_TAB = [2, 5, 10, 20, 50]
W_TAB = [2, 3, 5, 7, 10, 15, 20, 30, 50]
lines = ["l_um,w_um,N,rows_old,rows_new,released_fF,corrected_fF,delta_fF,delta_pct"]
for l in L_TAB:
    for wv in W_TAB:
        co, cn = float(c_old(l, wv, N)), float(c_new(l, wv, N))
        lines.append(f"{l},{wv},{N},{int(rows_old(wv))},{int(rows_new(wv))},"
                     f"{co:.3f},{cn:.3f},{cn-co:.3f},{100*(cn/co-1):.1f}")
with open("results/model_grid_l_w.csv", "w") as f:
    f.write("\n".join(lines) + "\n")
print("wrote results/model_grid_l_w.csv")
# compact console preview
print("\nl=5um default column:")
for wv in W_TAB:
    co, cn = float(c_old(5, wv, N)), float(c_new(5, wv, N))
    print(f"  w={wv:>2} um  n={int(rows_new(wv))}  released={co:6.2f}  "
          f"corrected={cn:6.2f}  +{100*(cn/co-1):5.1f}%")
