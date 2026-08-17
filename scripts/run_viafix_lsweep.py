#!/usr/bin/env python3
"""Serial length (L) sweep at fixed w=7 on the base+tip (_viafix) fd cells.
Both solvers: gds2palace full-wave and Palace electrostatic. One solve at a
time, RAM-gated. l=5.5,w=7 already lives in the width-sweep CSVs.

Run with ~/venv/palace/bin/python. Writes:
  palace/gds2palace/viafix_fw_lsweep.csv     (full-wave)
  palace/es_viacorner/es_viafix_lsweep.csv   (electrostatic)
Resumable.
"""
import os, sys, csv, json, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gds2palace_par as P
import gds2palace_density as G
import build_model as B

ROOT = G.ROOT
GDS = f"{ROOT}/gds"
FWOUT = f"{ROOT}/palace/gds2palace/viafix_fw_lsweep.csv"
ESRUN = f"{ROOT}/palace/es_viacorner"
ESOUT = f"{ESRUN}/es_viafix_lsweep.csv"
SIF = os.path.expanduser("~/palace.sif")
NP, LC, MARGIN = 6, 0.15, 5.0

# (base, l_um, w_um, rows)  rows = floor(7/0.89) = 7
CELLS = [
    ("fd_l2p5_w7_dbl_viafix", 2.5, 7, 7),
    ("fd_l10_w7_dbl_viafix", 10.0, 7, 7),
    ("fd_l14_w7_dbl_viafix", 14.0, 7, 7),
]


def free_gb():
    for line in subprocess.check_output(["free", "-g"]).decode().splitlines():
        if line.startswith("Mem:"):
            return int(line.split()[6])
    return 0


def wait_ram(floor=16):
    while free_gb() < floor:
        time.sleep(5)


def done_set(path):
    d = set()
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            d.add(r["cell"])
    return d


def append(path, header, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


# ---- electrostatic (mirror run_viafix_es_sweep) ----
def bbox_domain(j):
    d = json.load(open(j)); xs, ys = [], []
    for e in d["nets"]:
        for polys in e["layers"].values():
            for poly in polys:
                xs += [x for x, _ in poly]; ys += [y for _, y in poly]
    return [round(min(xs) - MARGIN, 6), round(min(ys) - MARGIN, 6),
            round(max(xs) + MARGIN, 6), round(max(ys) + MARGIN, 6)]


def es_c12(prefix):
    rows = list(csv.reader(open(f"{ESRUN}/{prefix}_out/terminal-C.csv")))
    body = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return -float(body[0][2]) * 1e15


def solve_es(prefix):
    j = f"{GDS}/{prefix}.json"
    B.build(j, f"{ESRUN}/{prefix}", lc_fine=LC, domain=bbox_domain(j))
    r = subprocess.run(["apptainer", "exec", SIF, "palace", "-np", str(NP), f"{prefix}.json"],
                       cwd=ESRUN, capture_output=True, text=True)
    if r.returncode != 0 or "MPI_Abort" in r.stdout:
        return None, r.stdout[-700:]
    C = es_c12(prefix)
    try: os.remove(f"{ESRUN}/{prefix}.msh")
    except OSError: pass
    return C, "ok"


def main():
    # ---------- FULL-WAVE ----------
    fw_done = done_set(FWOUT)
    fw_todo = [c for c in CELLS if c[0] not in fw_done]
    if fw_todo:
        bases = [c[0] for c in fw_todo]
        print(f"[{time.strftime('%H:%M:%S')}] FW pregen ports: {bases}", flush=True)
        layer = P.pregen_ports(bases)
        for base, l, w, rows in fw_todo:
            wait_ram(22)
            t0 = time.time()
            print(f"\n[{time.strftime('%H:%M:%S')}] FW SOLVE {base} (l={l}, free={free_gb()} GB)", flush=True)
            b, s, C, msg = P.run_task(base, "sub", layer[base])
            if C is None:
                print(f"[FW FAIL] {base}: {msg[:500]}", flush=True); continue
            append(FWOUT, ["cell", "N_metal", "l_um", "w_um", "rows", "stackup", "C_fF"],
                   [base, 4, l, w, rows, "sub_viafix", f"{C:.4f}"])
            print(f"[FW OK] {base} C={C:.4f} fF ({time.time()-t0:.0f}s)", flush=True)

    # ---------- ELECTROSTATIC ----------
    es_done = done_set(ESOUT)
    es_todo = [c for c in CELLS if c[0] not in es_done]
    for base, l, w, rows in es_todo:
        wait_ram(14)
        t0 = time.time()
        print(f"\n[{time.strftime('%H:%M:%S')}] ES SOLVE {base} (l={l}, free={free_gb()} GB)", flush=True)
        C, msg = solve_es(base)
        if C is None:
            print(f"[ES FAIL] {base}: {msg}", flush=True); continue
        append(ESOUT, ["cell", "N_metal", "l_um", "w_um", "rows", "solver", "C12_fF"],
               [base, 4, l, w, rows, "electrostatic_viafix", f"{C:.4f}"])
        print(f"[ES OK] {base} C12={C:.4f} fF ({time.time()-t0:.0f}s)", flush=True)

    print(f"\n[{time.strftime('%H:%M:%S')}] VIAFIX L-SWEEP DONE", flush=True)


if __name__ == "__main__":
    main()
