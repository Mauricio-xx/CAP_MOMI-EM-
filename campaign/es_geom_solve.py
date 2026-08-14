#!/usr/bin/env python3
"""ES geometry discriminator solve (venv python: gmsh + palace).

Part of the FW-vs-ES investigation (see results/FW_MESH_INVESTIGATION.md). Meshes
the bare comb and the comb+feeds in the SAME domain, uniform eps=4.1, and extracts
the A-B mutual C12 = -C[1][2]*1e15. If comb+feeds ~ comb, the rf2port feed/port
geometry does not explain the FW-over-ES gap. Run es_geom_prep.py first.

  ~/venv/palace/bin/python campaign/es_geom_solve.py
"""
import os
import sys
import csv
import json
import time
import subprocess

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
sys.path.insert(0, f"{ROOT}/scripts")
import build_model as B  # noqa: E402

SIF = os.path.expanduser("~/palace.sif")
LC, Z_LO, Z_HI, NP = 0.10, -1.0, 10.0, 8
P = json.load(open(f"{ROOT}/campaign/es_geom/params.json"))
DOM, OUT = P["domain"], P["outdir"]
ES_BARE, FW_05 = 20.791, 23.820


def c12(prefix):
    rows = list(csv.reader(open(f"{prefix}_out/terminal-C.csv")))
    body = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return -float(body[0][2]) * 1e15


def run(tag, netjson):
    prefix = f"{OUT}/sol_{tag}"           # sol_* so we never clobber the *_net.json inputs
    t0 = time.time()
    ntet = B.build(netjson, prefix, lc_fine=LC, z_lo=Z_LO, z_hi=Z_HI, domain=DOM)
    r = subprocess.run(["apptainer", "exec", SIF, "palace", "-np", str(NP), f"sol_{tag}.json"],
                       cwd=OUT, capture_output=True, text=True)
    dt = time.time() - t0
    if r.returncode != 0 or "MPI_Abort" in r.stdout:
        print(f"[SOLVE FAIL] {tag}\n{r.stdout[-1500:]}")
        return None
    C = c12(prefix)
    print(f"[OK] {tag}: C12 = {C:.3f} fF  (tets={ntet}, {dt:.0f}s)", flush=True)
    return C


c_comb = run("comb", P["comb"])
c_feeds = run("combfeeds", P["combfeeds"])
print("\n---- ES geometry discriminator (uniform eps=4.1) ----")
print(f"ES comb-only (shared domain) : {c_comb:.3f} fF")
print(f"ES comb+feeds (shared domain): {c_feeds:.3f} fF")
print(f"ES campaign bare comb        : {ES_BARE:.3f} fF")
print(f"FW Cdiff @0.5 (DUT)          : {FW_05:.3f} fF")
if c_comb and c_feeds:
    print(f"feed geometry adds           : {c_feeds - c_comb:+.3f} fF ({100*(c_feeds-c_comb)/c_comb:+.1f}%)")
