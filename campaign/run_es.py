#!/usr/bin/env python3
"""Phase 2 electrostatic starter batch (cap_mom, fixed-via, IHP sg13cmos5l).

The high-accuracy comb-to-comb capacitance path that validates the model's
density[N] / row-count / Cfeed. Palace Electrostatic, uniform eps=4.1, C12 from
the Maxwell matrix (C12 = -C[1][2]*1e15). Reuses scripts/build_model.py and the
netdump -> mesh -> solve flow. Serial, RAM-gated, resumable.

Device set (starter):
  * full-stack N4 double + same at 2.0/4.9/7.8/10.7/13.6 um; each size's
    double+same pair solved in a COMMON domain so Cfeed=C(same)-C(double) is
    boundary-clean (solve_feed_fix.py pattern).
  * per-N ladder (purpose-built small cells): m1m3/m2m4 (N3), m3m4 (N2) at
    w7, l=5.5 & l=10 (delta-L density).  Generate first: campaign/gen_ladder.py.

Writes results/es_campaign.csv.
"""
import os
import sys
import csv
import json
import time
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/montanares/git/slim-pdk/issue92_em"
sys.path.insert(0, f"{ROOT}/scripts")
import build_model as B  # noqa: E402

GDS_FIXED = f"{HERE}/gds_fixed"
ESDIR = f"{HERE}/es"
NETDUMP = f"{ROOT}/scripts/netdump.py"
SIF = os.path.expanduser("~/palace.sif")
OUTCSV = f"{ROOT}/results/es_campaign.csv"
NP = 8
LC = 0.10
Z_HI = 10.0
Z_LO = -1.0
MARGIN = 5.0

# starter full-stack sizes: (wl_um, suffix)
SIZES = [(2.0, "02p0um"), (4.9, "04p9um"), (7.8, "07p8um"),
         (10.7, "10p7um"), (13.6, "13p6um")]

# ladder cells: (name, l_um, w_um, mmin, mmax, N)
LADDER = [
    ("n3_m1m3_w7_l5p5", 5.5, 7, 1, 3, 3), ("n3_m1m3_w7_l10", 10.0, 7, 1, 3, 3),
    ("n3_m2m4_w7_l5p5", 5.5, 7, 2, 4, 3), ("n3_m2m4_w7_l10", 10.0, 7, 2, 4, 3),
    ("n2_m3m4_w7_l5p5", 5.5, 7, 3, 4, 2), ("n2_m3m4_w7_l10", 10.0, 7, 3, 4, 2),
]


def free_gb():
    out = subprocess.check_output(["free", "-g"]).decode()
    for line in out.splitlines():
        if line.startswith("Mem:"):
            return int(line.split()[6])
    return 0


def netjson(name):
    j = f"{ESDIR}/{name}.json"
    if not os.path.exists(j):
        subprocess.run([sys.executable, NETDUMP, f"{GDS_FIXED}/{name}.gds", j], check=True)
    return j


def common_domain(jsons):
    xs, ys = [], []
    for p in jsons:
        d = json.load(open(p))
        for e in d["nets"]:
            for polys in e["layers"].values():
                for poly in polys:
                    xs += [x for x, _ in poly]
                    ys += [y for _, y in poly]
    return [round(min(xs) - MARGIN, 6), round(min(ys) - MARGIN, 6),
            round(max(xs) + MARGIN, 6), round(max(ys) + MARGIN, 6)]


def c12(prefix):
    rows = list(csv.reader(open(f"{prefix}_out/terminal-C.csv")))
    body = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return -float(body[0][2]) * 1e15


def solve(name, domain, min_free_gb):
    j = netjson(name)
    prefix = f"{ESDIR}/{name}"
    if os.path.exists(f"{prefix}_out/terminal-C.csv"):
        return c12(prefix), None, None
    fg = free_gb()
    if fg < min_free_gb:
        print(f"[SKIP] {name}: only {fg} GB free (< {min_free_gb})")
        return None, None, None
    t0 = time.time()
    ntet = B.build(j, prefix, lc_fine=LC, z_lo=Z_LO, z_hi=Z_HI, domain=domain)
    r = subprocess.run(["apptainer", "exec", SIF, "palace", "-np", str(NP), f"{name}.json"],
                       cwd=ESDIR, capture_output=True, text=True)
    solve_s = time.time() - t0
    if r.returncode != 0 or "MPI_Abort" in r.stdout or "Verification failed" in r.stdout:
        print(f"[SOLVE FAIL] {name}\n{r.stdout[-1200:]}")
        return None, ntet, solve_s
    C = c12(prefix)
    try:
        os.remove(f"{prefix}.msh")
    except OSError:
        pass
    return C, ntet, solve_s


def load_done():
    done = set()
    if os.path.exists(OUTCSV):
        for r in csv.DictReader(open(OUTCSV)):
            done.add(r["name"])
    return done


def append_row(row):
    new = not os.path.exists(OUTCSV)
    os.makedirs(os.path.dirname(OUTCSV), exist_ok=True)
    with open(OUTCSV, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["name", "feed", "N", "mmin", "mmax", "w_um", "l_um",
                        "C12_fF", "tets", "solve_s", "lc"])
        w.writerow(row)


def run(name, feed, N, mmin, mmax, w, l, domain, done, min_free_gb):
    if name in done:
        print(f"[skip done] {name}")
        return
    print(f"\n==== {name}  feed={feed} N={N} w={w} l={l} ====", flush=True)
    C, ntet, ss = solve(name, domain, min_free_gb)
    if C is None:
        return
    append_row([name, feed, N, mmin, mmax, w, l, f"{C:.4f}", ntet or "",
                f"{ss:.0f}" if ss else "", LC])
    print(f"[OK] {name} C12 = {C:.3f} fF  (tets={ntet}, {ss:.0f}s)" if ss
          else f"[cached] {name} C12 = {C:.3f} fF", flush=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-free-gb", type=int, default=25)
    ap.add_argument("--only", choices=["pairs", "ladder"], help="run only one group")
    args = ap.parse_args()
    os.makedirs(ESDIR, exist_ok=True)
    done = load_done()

    if args.only != "ladder":
        for wl, sfx in SIZES:
            dbl = f"cap_mom_double_{sfx}"
            sam = f"cap_mom_same_{sfx}"
            dom = common_domain([netjson(dbl), netjson(sam)])
            print(f"=== size {wl}um  common domain {dom}", flush=True)
            run(dbl, "double", 4, 1, 4, wl, wl, dom, done, args.min_free_gb)
            run(sam, "same", 4, 1, 4, wl, wl, dom, done, args.min_free_gb)

    if args.only != "pairs":
        for name, l, w, mmin, mmax, N in LADDER:
            j = netjson(name)
            dom = common_domain([j])
            run(name, "double", N, mmin, mmax, w, l, dom, done, args.min_free_gb)

    print("\nES starter done. Results:", OUTCSV)


if __name__ == "__main__":
    main()
