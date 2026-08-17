#!/usr/bin/env python3
"""Serial electrostatic sweep on the base+tip (_viafix) fd cells at l=5.5.

Mirrors solve_es_viacorner.py (build_model + Palace Electrostatic, mutual C12
from terminal-C.csv, lc_fine=0.15, per-cell domain box). One solve at a time,
RAM-gated. w=7 first, validated against the canonical 35.5074 fF; aborts if it
drifts >2%.

Run with: ~/venv/palace/bin/python scripts/run_viafix_es_sweep.py
Writes palace/es_viacorner/es_viafix_sweep.csv (resumable).
"""
import os, sys, csv, json, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_model as B

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
GDS = f"{ROOT}/gds"
RUN = f"{ROOT}/palace/es_viacorner"
SIF = os.path.expanduser("~/palace.sif")
NP, LC, MARGIN = 6, 0.15, 5.0
W7_REF, W7_TOL = 35.5074, 0.02
OUT = f"{RUN}/es_viafix_sweep.csv"

CELLS = [
    ("fd_l5p5_w7_dbl_viafix",  7,  7),
    ("fd_l5p5_w2_dbl_viafix",  2,  2),
    ("fd_l5p5_w5_dbl_viafix",  5,  5),
    ("fd_l5p5_w15_dbl_viafix", 15, 16),
]


def free_gb():
    for line in subprocess.check_output(["free", "-g"]).decode().splitlines():
        if line.startswith("Mem:"):
            return int(line.split()[6])
    return 0


def bbox_domain(j):
    d = json.load(open(j)); xs, ys = [], []
    for e in d["nets"]:
        for polys in e["layers"].values():
            for poly in polys:
                xs += [x for x, _ in poly]; ys += [y for _, y in poly]
    return [round(min(xs) - MARGIN, 6), round(min(ys) - MARGIN, 6),
            round(max(xs) + MARGIN, 6), round(max(ys) + MARGIN, 6)]


def c12(prefix):
    rows = list(csv.reader(open(f"{RUN}/{prefix}_out/terminal-C.csv")))
    body = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return -float(body[0][2]) * 1e15


def solve(prefix):
    j = f"{GDS}/{prefix}.json"
    B.build(j, f"{RUN}/{prefix}", lc_fine=LC, domain=bbox_domain(j))
    r = subprocess.run(["apptainer", "exec", SIF, "palace", "-np", str(NP), f"{prefix}.json"],
                       cwd=RUN, capture_output=True, text=True)
    if r.returncode != 0 or "MPI_Abort" in r.stdout:
        return None, r.stdout[-800:]
    C = c12(prefix)
    try: os.remove(f"{RUN}/{prefix}.msh")
    except OSError: pass
    return C, "ok"


def done_set():
    d = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            d.add(r["cell"])
    return d


def main():
    os.makedirs(RUN, exist_ok=True)
    done = done_set()
    todo = [c for c in CELLS if c[0] not in done]
    print(f"[{time.strftime('%H:%M:%S')}] serial viafix ES sweep; todo={[c[0] for c in todo]}", flush=True)
    new = not os.path.exists(OUT)
    for base, w, rows in todo:
        while free_gb() < 14:
            time.sleep(5)
        t0 = time.time()
        print(f"\n[{time.strftime('%H:%M:%S')}] ES SOLVE {base}  (w={w}, free={free_gb()} GB)", flush=True)
        C, msg = solve(base)
        if C is None:
            print(f"[FAIL] {base}: {msg}", flush=True)
            if w == 7:
                print("ABORT: w7 validation failed.", flush=True); return
            continue
        with open(OUT, "a", newline="") as f:
            wr = csv.writer(f)
            if new:
                wr.writerow(["cell", "N_metal", "l_um", "w_um", "rows", "solver", "C12_fF"]); new = False
            wr.writerow([base, 4, 5.5, w, rows, "electrostatic_viafix", f"{C:.4f}"])
        print(f"[OK] {base}  C12 = {C:.4f} fF  ({time.time()-t0:.0f}s, free={free_gb()} GB)", flush=True)
        if w == 7:
            off = abs(C - W7_REF) / W7_REF
            print(f"[VALIDATION] w7 {C:.4f} vs ref {W7_REF} -> {off*100:.2f}%", flush=True)
            if off > W7_TOL:
                print(f"ABORT: w7 drifted >{W7_TOL*100:.0f}%.", flush=True); return
            print("w7 validated; continuing.", flush=True)
    print(f"\n[{time.strftime('%H:%M:%S')}] VIAFIX ES SWEEP DONE", flush=True)


if __name__ == "__main__":
    main()
