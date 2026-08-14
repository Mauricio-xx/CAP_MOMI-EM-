#!/usr/bin/env python3
"""Re-run the density series with FIXED (densified) vias, to quantify the effect.

For each density-series cell: densify the vias to the reference pitch (fix_vias),
materialise the GDS (json_to_gds), add the port, and solve in gds2palace (sub
stackup). Writes palace/gds2palace/density_runs_fixvia.csv, to be compared
against the sparse-via density_runs.csv.
"""
import os, sys, csv, subprocess, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gds2palace_par as P
import gds2palace_density as G

ROOT = G.ROOT
FIXCSV = f"{ROOT}/palace/gds2palace/density_runs_fixvia.csv"
K = 4

# (orig_base, N_metal, l_um, w_um, rows)
CELLS = [
    ("fd_l5p5_w2_dbl",   4, 5.5, 2,  2),
    ("fd_l5p5_w5_dbl",   4, 5.5, 5,  5),
    ("fd_l5p5_w7_dbl",   4, 5.5, 7,  7),
    ("fd_l5p5_w15_dbl",  4, 5.5, 15, 16),
    ("n2_l5p5_w7",       2, 5.5, 7,  7),
    ("n2_l10_w7",        2, 10.0, 7, 7),
    ("pcell_l5p5_w7_n3", 3, 5.5, 7,  7),
    ("pcell_l10_w7_n3",  3, 10.0, 7, 7),
    ("g2n5_l5p5_w7",     5, 5.5, 7,  7),
    ("g2n5_l10_w7",      5, 10.0, 7, 7),
]
META = {c[0]: c for c in CELLS}
lock = threading.Lock()


def done_set():
    d = set()
    if os.path.exists(FIXCSV):
        for r in csv.DictReader(open(FIXCSV)):
            d.add(r["cell"])
    return d


def prep(base):
    """densify vias, write fixvia json + gds; return the fixvia base name."""
    fj = f"{ROOT}/gds/{base}_fixvia.json"
    if not os.path.exists(fj):
        subprocess.run([sys.executable, f"{ROOT}/scripts/fix_vias.py",
                        f"{ROOT}/gds/{base}.json"], check=True)
    if not os.path.exists(f"{ROOT}/gds/{base}_fixvia.gds"):
        subprocess.run([sys.executable, f"{ROOT}/scripts/json_to_gds.py", fj], check=True)
    return base + "_fixvia"


def append(base, N, l, w, rows, C):
    with lock:
        new = not os.path.exists(FIXCSV)
        with open(FIXCSV, "a", newline="") as f:
            wr = csv.writer(f)
            if new:
                wr.writerow(["cell", "N_metal", "l_um", "w_um", "rows", "stackup", "C_fF"])
            wr.writerow([base, N, l, w, rows, "sub_fixvia", f"{C:.4f}"])


def main():
    done = done_set()
    todo = [c for c in CELLS if c[0] not in done]
    print(f"prep {len(todo)} fixvia cells ...", flush=True)
    fixbases = {}
    for base, *_ in todo:
        fixbases[base] = prep(base)
    layer = P.pregen_ports([fixbases[b] for b, *_ in todo])
    print(f"launching {len(todo)} fixvia solves, K={K}", flush=True)
    with ThreadPoolExecutor(max_workers=K) as ex:
        futs = {}
        for base, N, l, w, rows in todo:
            fb = fixbases[base]
            futs[ex.submit(P.run_task, fb, "sub", layer[fb])] = (base, N, l, w, rows)
        for fut in as_completed(futs):
            base, N, l, w, rows = futs[fut]
            fb, s, C, msg = fut.result()
            if C is None:
                print(f"[FAIL] {base}: {msg[:200]}", flush=True)
            else:
                append(base, N, l, w, rows, C)
                print(f"[OK] {base} fixvia  C = {C:.3f} fF", flush=True)
    print("FIXVIA BATCH DONE", flush=True)


if __name__ == "__main__":
    main()
