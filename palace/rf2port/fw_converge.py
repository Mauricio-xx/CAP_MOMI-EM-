#!/usr/bin/env python3
"""Full-wave mesh convergence on the 04p9 double DUT.

The +14.6% FW-Cdiff-over-ES gap is not dielectric (-0.6% controlled re-solve),
not fixture (open dummy 0.05 fF, ES comb+feeds +0.06 fF). The remaining suspect
is FW discretization: the campaign runs refined_cellsize=0.5 um, coarser than the
0.84 um tooth pitch, so the mesh under-resolves the inter-tooth gap that sets C.
The ES uses lc=0.10 um and lands at 20.79.

This re-solves the SAME DUT testbench GDS changing ONLY refined_cellsize, so the
delta is pure mesh. If Cdiff falls toward ~20.8 as the cell drops below the gap,
the +14% is a mesh artifact; if it holds ~23.8, it is not mesh and we look at the
port / surface-impedance instead.

Run (system python3; build_model shells to the venv):
  python3 fw_converge.py [--min-free-gb 20] [rc ...]   # default rc = 0.35 0.25
"""
import os
import sys
import csv
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_rf2port as R  # noqa: E402

DUT = "cap_mom_double_04p9um"
DUT_TB = f"{R.TB_DIR}/{DUT}_rf_tb.gds"
BASE_TMPL = R.MODEL_TMPL
# Optional fstart override (e.g. "0.01e9") to dodge the DC (f=0) SuperLU singular
# that kills the ROM build on some meshes. Cdiff is frequency-flat, so moving the
# band start off DC does not change the extracted value.
FSTART = os.environ.get("FW_FSTART")
ES_REF = 20.791
FW_05 = 23.820
OUTCSV = f"{R.RESULTS_DIR}/fw_converge_04p9.csv"


def solve_rc(rc, min_free_gb):
    name = f"{DUT}_rc{int(round(rc*100)):03d}"
    # change ONLY refined_cellsize; leave freq sweep, order, ports, stackup intact
    R.MODEL_TMPL = BASE_TMPL.replace(
        "settings['refined_cellsize'] = 0.5",
        f"settings['refined_cellsize'] = {rc}")
    assert f"refined_cellsize'] = {rc}" in R.MODEL_TMPL, "template patch failed"
    if FSTART:
        R.MODEL_TMPL = R.MODEL_TMPL.replace(
            "settings['fstart'] = 0e9", f"settings['fstart'] = {FSTART}")
        assert f"fstart'] = {FSTART}" in R.MODEL_TMPL, "fstart patch failed"
        print(f"  (fstart overridden to {FSTART} to avoid DC singular)")

    print(f"\n==== refined_cellsize = {rc} ({name}) ====", flush=True)
    t0 = time.time()
    sim_path, build_s = R.build_model(name, DUT_TB)
    if sim_path is None:
        return None
    nports = R.check_ports(sim_path)
    print(f"  built ({build_s:.0f}s), ports={nports}", flush=True)
    if nports != 2:
        print(f"  [ABORT] ports={nports}")
        return None
    peak_mb, solve_s = R.solve(sim_path, min_free_gb)
    if solve_s is None:
        print("  [SKIP] not enough free RAM")
        return None
    s2p, cdiff = R.combine_and_eval(name, sim_path)
    if cdiff is None:
        print("  [EVAL FAIL]")
        return None
    off = 100 * (cdiff - ES_REF) / ES_REF
    print(f"  [OK] rc={rc}: Cdiff={cdiff:.3f} fF  ({off:+.1f}% vs ES)  "
          f"peak={peak_mb}MB build={build_s:.0f}s solve={solve_s:.0f}s", flush=True)
    new = not os.path.exists(OUTCSV)
    with open(OUTCSV, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["refined_cellsize", "Cdiff_fF", "off_vs_ES_pct",
                        "peak_mb", "build_s", "solve_s"])
        w.writerow([rc, f"{cdiff:.4f}", f"{off:.2f}", peak_mb or "",
                    f"{build_s:.0f}", f"{solve_s:.0f}"])
    return cdiff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rc", nargs="*", type=float, default=[0.35, 0.25])
    ap.add_argument("--min-free-gb", type=int, default=20)
    args = ap.parse_args()
    print(f"ES ref = {ES_REF} fF ; FW@0.5 = {FW_05} fF (+{100*(FW_05-ES_REF)/ES_REF:.1f}%)")
    res = {0.5: FW_05}
    for rc in args.rc:                      # strictly serial
        c = solve_rc(rc, args.min_free_gb)
        if c is not None:
            res[rc] = c
    print("\n---- FW mesh convergence (04p9) ----")
    for rc in sorted(res, reverse=True):
        print(f"  rc={rc:>5}: Cdiff={res[rc]:.3f} fF  ({100*(res[rc]-ES_REF)/ES_REF:+.1f}% vs ES {ES_REF})")


if __name__ == "__main__":
    main()
