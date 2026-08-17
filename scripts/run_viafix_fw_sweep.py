#!/usr/bin/env python3
"""Serial gds2palace full-wave sweep on the base+tip (_viafix) fd cells.

One solve at a time (never two Palace runs concurrently), RAM-gated. Runs w=7
first and checks it reproduces the known viafix full-wave value (37.1176 fF);
if it drifts >2% the sweep aborts before spending compute on the other widths.

Run with the venv that has gmsh+gdspy+skrf:
    ~/venv/palace/bin/python scripts/run_viafix_fw_sweep.py

Writes palace/gds2palace/viafix_fw_sweep.csv (resumable).
"""
import os, sys, csv, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gds2palace_par as P
import gds2palace_density as G

ROOT = G.ROOT
OUT = f"{ROOT}/palace/gds2palace/viafix_fw_sweep.csv"
W7_REF = 37.1176           # run_viafix_compare.py value, same pipeline
W7_TOL = 0.02

# w=7 first (validation), then the rest. (base, N, l, w, rows)
CELLS = [
    ("fd_l5p5_w7_dbl_viafix",  4, 5.5, 7,  7),
    ("fd_l5p5_w2_dbl_viafix",  4, 5.5, 2,  2),
    ("fd_l5p5_w5_dbl_viafix",  4, 5.5, 5,  5),
    ("fd_l5p5_w15_dbl_viafix", 4, 5.5, 15, 16),
]


def done_map():
    d = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            d[r["cell"]] = float(r["C_fF"])
    return d


def write_row(base, N, l, w, rows, C):
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        wr = csv.writer(f)
        if new:
            wr.writerow(["cell", "N_metal", "l_um", "w_um", "rows", "stackup", "C_fF"])
        wr.writerow([base, N, l, w, rows, "sub_viafix", f"{C:.4f}"])


def main():
    done = done_map()
    todo = [c for c in CELLS if c[0] not in done]
    bases = [c[0] for c in todo]
    print(f"[{time.strftime('%H:%M:%S')}] serial viafix FW sweep; todo={bases}", flush=True)
    if not bases:
        print("nothing to do (all in CSV).", flush=True); return
    print("pregen ports (serial) ...", flush=True)
    layer = P.pregen_ports(bases)
    print("port layers:", layer, flush=True)

    for base, N, l, w, rows in todo:
        P.wait_ram()
        t0 = time.time()
        print(f"\n[{time.strftime('%H:%M:%S')}] SOLVE {base}  (w={w}, free={G.free_gb()} GB)", flush=True)
        b, s, C, msg = P.run_task(base, "sub", layer[base])
        if C is None:
            print(f"[FAIL] {base}: {msg[:600]}", flush=True)
            if base.endswith("w7_dbl_viafix"):
                print("ABORT: w7 validation solve failed; not running the rest.", flush=True)
                return
            continue
        write_row(base, N, l, w, rows, C)
        dt = time.time() - t0
        print(f"[OK] {base}  C = {C:.4f} fF  ({dt:.0f}s, free={G.free_gb()} GB)", flush=True)
        if base.endswith("w7_dbl_viafix"):
            off = abs(C - W7_REF) / W7_REF
            print(f"[VALIDATION] w7 {C:.4f} vs ref {W7_REF} -> {off*100:.2f}%", flush=True)
            if off > W7_TOL:
                print(f"ABORT: w7 drifted >{W7_TOL*100:.0f}%; pipeline suspect, not running w2/5/15.", flush=True)
                return
            print("w7 validated; continuing to w2/5/15.", flush=True)
    print(f"\n[{time.strftime('%H:%M:%S')}] VIAFIX FW SWEEP DONE", flush=True)


if __name__ == "__main__":
    main()
