#!/usr/bin/env python3
"""Phase 3: verify the updated cap_cmomi Verilog-A model against the EM campaign.

Loads the ES (comb-to-comb C12) starter results, computes the model prediction
with the UPDATED (rowfix branch) formula and, for contrast, the PRE-FIX row
count, and reports:
  * density[N] re-extracted from the fixed-via ES sweep (slope of C12 vs area);
  * the row-count fix (EM vs fixed-ay model vs prefix-(ay-1) model, %err);
  * C(same)-C(double) delta vs the model Cfeed(same)-Cfeed(double).
Writes results/campaign_results.csv (unified) and prints a summary. Runs on
whatever subset of results exists (safe to run while the batch is still going).

Model (updated / rowfix, matches .va at branch fix/cap-cmomi-row-count 1e93ffc):
  C = density[N]*ax*ay*0.84*0.89 + Cfeed
  ax = floor(l/0.84+1e-6), ay = floor(w/0.89+1e-6)
  density = {<=2:0.55, 3:0.82, 4:1.09, 5:1.36};  pad_len = ay*0.89 + 0.42
  Cfeed: none=0;  double = 0.152*pad_len;  same = 0.1625*pad_len + 0.0916
"""
import os
import csv
import math
import numpy as np

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
ES_CSV = f"{ROOT}/results/es_campaign.csv"
OUT_CSV = f"{ROOT}/results/campaign_results.csv"
UC_X, UC_Y = 0.84, 0.89
DENSITY = {2: 0.55, 3: 0.82, 4: 1.09, 5: 1.36}
# Feed terms from the .va (both feeds add cap to Cmain, keyed on pad_len):
CFEED_SLOPE, CFEED_END = 0.1625, 0.0916   # feed == 'same'  (single-side)
CFEED2_SLOPE = 0.152                        # feed == 'double' (opposite-side)


def geom(w, l):
    ax = math.floor(l / UC_X + 1e-6)
    ay = math.floor(w / UC_Y + 1e-6)
    return ax, ay, ax * ay * UC_X * UC_Y


def pad_len_of(w, l):
    _, ay, _ = geom(w, l)           # drawn (true) row count; physical pad height
    return ay * UC_Y + 0.42


def feed_C(feed, pad_len):
    if feed == "same":
        return CFEED_SLOPE * pad_len + CFEED_END
    if feed == "double":
        return CFEED2_SLOPE * pad_len
    return 0.0


def model_C(w, l, N, feed, rowfix=True):
    ax, ay, area = geom(w, l)
    if not rowfix:
        ay = ay - 1
        area = ax * ay * UC_X * UC_Y
    d = DENSITY[min(5, max(2, N))]
    # pad_len uses the DRAWN ay (physical), so the row-fix contrast isolates area.
    return d * area + feed_C(feed, pad_len_of(w, l))


def load(path, key):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path)))


def main():
    es = {r["name"]: r for r in load(ES_CSV, "name")}
    print(f"loaded ES={len(es)}")

    rows = []
    for name, r in sorted(es.items()):
        w, l, N, feed = float(r["w_um"]), float(r["l_um"]), int(r["N"]), r["feed"]
        ax, ay, area = geom(w, l)
        c_em = float(r["C12_fF"])
        c_fix = model_C(w, l, N, feed, rowfix=True)
        c_pre = model_C(w, l, N, feed, rowfix=False)
        rows.append(dict(name=name, feed=feed, N=N, w=w, l=l, ax=ax, ay=ay,
                         area=round(area, 3), C12_es=round(c_em, 3),
                         model_fix=round(c_fix, 3),
                         model_pre=round(c_pre, 3),
                         err_fix_pct=round(100 * (c_fix - c_em) / c_em, 2),
                         err_pre_pct=round(100 * (c_pre - c_em) / c_em, 2)))

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    if rows:
        with open(OUT_CSV, "w", newline="") as f:
            wtr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wtr.writeheader()
            wtr.writerows(rows)

    # ---- density[N] re-extraction from fixed-via ES (double / feed=none area law) ----
    print("\n== density[N] from fixed-via ES ==")
    for N in (4, 3, 2):
        pts = [(r["area"], r["C12_es"]) for r in rows
               if r["N"] == N and r["feed"] == "double"]
        if len(pts) >= 2:
            a = np.array([p[0] for p in pts]); c = np.array([p[1] for p in pts])
            slope, inter = np.polyfit(a, c, 1)
            ss = 1 - np.sum((c - (slope * a + inter))**2) / np.sum((c - c.mean())**2)
            print(f"  N={N}: density_fit={slope:.4f} fF/um^2 (model {DENSITY[N]}), "
                  f"intercept={inter:.2f} fF, R2={ss:.5f}, npts={len(pts)}")
        else:
            print(f"  N={N}: need >=2 double points, have {len(pts)}")

    # ---- Cfeed delta = C(same) - C(double) per size ----
    # EM measures the SAME-minus-DOUBLE differential-C delta, so it must be
    # compared to the model's Cfeed(same) - Cfeed(double), not Cfeed(same) alone
    # (the double device already carries its own 0.152*pad_len feed cap).
    print("\n== C(same)-C(double) delta: EM vs model[same-double] ==")
    for r in rows:
        if r["feed"] != "double":
            continue
        sname = r["name"].replace("_double_", "_same_")
        if sname == r["name"]:
            continue                      # ladder cells have no 'same' twin
        s = next((x for x in rows if x["name"] == sname), None)
        if not s:
            continue
        cfeed_em = s["C12_es"] - r["C12_es"]
        pad_len = r["ay"] * UC_Y + 0.42
        cfeed_mod = feed_C("same", pad_len) - feed_C("double", pad_len)
        print(f"  {r['name'][8:]:20} EM d={cfeed_em:+.3f} fF  model d={cfeed_mod:+.3f} fF  "
              f"(pad_len={pad_len:.2f})")

    # ---- row-count summary (double devices) ----
    print("\n== C(size): EM vs updated model vs pre-fix (double) ==")
    print(f"  {'device':22} {'C12_EM':>8} {'model_fix':>9} {'err%':>6} {'model_pre':>9} {'err%':>6}")
    for r in rows:
        if r["feed"] == "double":
            print(f"  {r['name'][9:]:22} {r['C12_es']:8.2f} {r['model_fix']:9.2f} "
                  f"{r['err_fix_pct']:6.1f} {r['model_pre']:9.2f} {r['err_pre_pct']:6.1f}")

    print(f"\nUnified table -> {OUT_CSV}")


if __name__ == "__main__":
    main()
