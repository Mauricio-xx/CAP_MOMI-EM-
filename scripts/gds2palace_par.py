#!/usr/bin/env python3
"""Parallel version of the gds2palace density batch (deadline mode).

Runs the remaining (cell, stackup) tasks concurrently with a bounded worker pool,
reduced MPI ranks per solve, and a RAM guard, so we never drop below the free-RAM
floor. sub runs go first (they give the density-vs-notes headline); nosub after.

Resumable: skips (cell, stackup) already in density_runs.csv.
"""
import os, sys, csv, subprocess, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gds2palace_density as G   # reuse WF, SIF, ROOT, STACKS, MODEL_TMPL, ADD_PORT, extract_C, free_gb

K = 4                 # parallel solves
NP = 6                # MPI ranks each -> K*NP = 24 cores, 8 free
RAM_FLOOR_GB = 22     # do not start a new solve unless this much is free (keeps >10 with margin)
OUTCSV = G.OUTCSV

CELLS = {c[0]: c for c in G.CELLS}   # base -> (base, N, l, w, rows)

# task order: all sub first, then nosub
TASKS = ([(b, "sub") for b in CELLS] + [(b, "nosub") for b in CELLS])

lock = threading.Lock()
ram_gate = threading.Semaphore(K)


def done_set():
    d = set()
    if os.path.exists(OUTCSV):
        for r in csv.DictReader(open(OUTCSV)):
            d.add((r["cell"], r["stackup"]))
    return d


def pregen_ports(bases):
    """Serial: write gds/<base>_port.gds and capture the port layer per cell."""
    layer = {}
    for b in bases:
        ap = subprocess.run([sys.executable, G.ADD_PORT, f"{G.ROOT}/gds/{b}.json"],
                            capture_output=True, text=True)
        lay = "Metal1"
        for line in ap.stdout.splitlines():
            if line.startswith("PORT_LAYER="):
                lay = line.split("=", 1)[1].strip()
        if ap.returncode != 0:
            print(f"[PORT FAIL] {b}\n{ap.stdout[-400:]}\n{ap.stderr[-400:]}", flush=True)
        layer[b] = lay
    return layer


def wait_ram():
    while G.free_gb() < RAM_FLOOR_GB:
        time.sleep(5)


def run_task(base, stk, layer):
    xml = G.STACKS[stk]
    basename = f"capd_{base}_{stk}"
    gds_wf = f"{basename}.gds"
    subprocess.run(["cp", f"{G.ROOT}/gds/{base}_port.gds", f"{G.WF}/{gds_wf}"], check=True)
    with open(f"{G.WF}/{basename}.py", "w") as f:
        f.write(G.MODEL_TMPL.format(gds=gds_wf, xml=xml, layer=layer))
    # build headless
    r = subprocess.run([sys.executable, basename + ".py"], cwd=G.WF,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return base, stk, None, f"BUILD FAIL: {r.stdout[-500:]} {r.stderr[-300:]}"
    # solve (RAM-gated)
    wait_ram()
    sdir = f"{G.WF}/palace_model/{basename}_data"
    r = subprocess.run(["apptainer", "exec", G.SIF, "palace", "-np", str(NP), "config.json"],
                       cwd=sdir, capture_output=True, text=True)
    if "Verification failed" in r.stdout or "MPI_Abort" in r.stdout or r.returncode != 0:
        return base, stk, None, f"SOLVE FAIL rc={r.returncode}: {r.stdout[-500:]}"
    try:
        C = G.extract_C(basename)
    except Exception as e:
        return base, stk, None, f"EXTRACT FAIL: {e}"
    try:
        os.remove(f"{sdir}/{basename}.msh")
    except OSError:
        pass
    return base, stk, C, "ok"


def append(base, stk):
    _, N, l, w, rows = CELLS[base]

    def _w(C):
        with lock:
            new = not os.path.exists(OUTCSV)
            with open(OUTCSV, "a", newline="") as f:
                wr = csv.writer(f)
                if new:
                    wr.writerow(["cell", "N_metal", "l_um", "w_um", "rows", "stackup", "C_fF"])
                wr.writerow([base, N, l, w, rows, stk, f"{C:.4f}"])
    return _w


def main():
    todo = [(b, s) for (b, s) in TASKS if (b, s) not in done_set()]
    bases = sorted({b for (b, s) in todo})
    print(f"pre-generating {len(bases)} port GDS ...", flush=True)
    layer = pregen_ports(bases)
    print(f"launching {len(todo)} tasks, K={K}, np={NP}", flush=True)
    with ThreadPoolExecutor(max_workers=K) as ex:
        futs = {ex.submit(run_task, b, s, layer[b]): (b, s) for (b, s) in todo}
        for fut in as_completed(futs):
            b, s, C, msg = fut.result()
            if C is None:
                print(f"[FAIL] {b} {s}: {msg[:300]}", flush=True)
            else:
                append(b, s)(C)
                print(f"[OK] {b} {s}  C = {C:.3f} fF   (free {G.free_gb()} GB)", flush=True)
    print("PARALLEL BATCH DONE", flush=True)


if __name__ == "__main__":
    main()
