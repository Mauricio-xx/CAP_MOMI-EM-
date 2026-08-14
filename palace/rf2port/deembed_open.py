#!/usr/bin/env python3
"""Open-dummy de-embed for the rf2port 2-port full-wave testbench.

Tests whether the +14.6% FW-Cdiff-over-ES offset on the double devices is the
un-de-embedded fixture (Metal4 feeds + 201/202 port strips + Metal1 guard ring),
not a dielectric or model effect. The controlled substrate re-solve already
showed the layered stackup moves C by only -0.6%, so the offset should be the
fixture; the standard test is an OPEN dummy: same fixture with the DUT comb
removed, feeds left open across the former DUT gap.

Method: the open GDS is the DUT testbench with the cap reference deleted (feeds,
ports and guard frame kept at identical absolute coordinates -> byte-identical
fixture). Solve it in the SAME Palace 2-port flow. Because Cdiff is linear in Y,
  Cdiff_deemb = Cdiff_dut - Cdiff_open,
so one open solve settles it. No short dummy: at ~60 MHz the fixture parasitic is
capacitive (feed-to-feed + feed-to-guard shunt); lead L/R is negligible for C.

Run (system python3; build_model shells out to the venv):
  python3 deembed_open.py cap_mom_double_04p9um [--min-free-gb 20]
"""
import os
import sys
import csv
import time
import argparse
from pathlib import Path

import gdstk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_rf2port as R  # noqa: E402


def build_open_tb(dut_name, open_name):
    """Strip the cap reference from the DUT testbench -> open-fixture GDS."""
    src = Path(f"{R.TB_DIR}/{dut_name}_rf_tb.gds")
    if not src.exists():
        # wrap the DUT first so the fixture exists
        R.wrap_device(dut_name)
    lib = gdstk.read_gds(src)
    top = lib.top_level()[0]
    out = gdstk.Library(unit=lib.unit, precision=lib.precision)
    ocell = out.new_cell(f"{open_name}_rf_tb.gds")
    for p in top.polygons:            # feeds (50), ports (201/202), guard (8)
        ocell.add(p.copy())
    dst = Path(f"{R.TB_DIR}/{open_name}_rf_tb.gds")
    out.write_gds(dst)
    return str(dst)


def dut_cdiff(dut_name):
    for r in csv.DictReader(open(R.OUTCSV)):
        if r["device"] == dut_name:
            return float(r["Cdiff_fF"])
    return None


def es_c12(dut_name):
    es = f"{R.ROOT}/results/es_campaign.csv"
    for r in csv.DictReader(open(es)):
        if r["name"] == dut_name:
            return float(r["C12_fF"])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dut", help="DUT device basename, e.g. cap_mom_double_04p9um")
    ap.add_argument("--min-free-gb", type=int, default=20)
    args = ap.parse_args()

    dut = args.dut
    tag = dut.replace("cap_mom_double_", "").replace("cap_mom_", "")
    open_name = f"cap_mom_open_{tag}"

    print(f"== open de-embed for {dut} ==", flush=True)
    open_tb = build_open_tb(dut, open_name)
    print("open fixture GDS:", open_tb)

    sim_path, build_s = R.build_model(open_name, open_tb)
    if sim_path is None:
        sys.exit("build failed")
    nports = R.check_ports(sim_path)
    print(f"built ({build_s:.0f}s), ports={nports}")
    if nports != 2:
        sys.exit(f"expected 2 ports, got {nports} (open fixture lost a port)")

    peak_mb, solve_s = R.solve(sim_path, args.min_free_gb)
    if solve_s is None:
        sys.exit("skipped: not enough free RAM")
    s2p, cdiff_open = R.combine_and_eval(open_name, sim_path)
    if cdiff_open is None:
        sys.exit("open extraction failed")

    c_dut = dut_cdiff(dut)
    c_es = es_c12(dut)
    print("\n---- de-embed result ----")
    print(f"ES C12            : {c_es:.3f} fF" if c_es else "ES C12            : n/a")
    print(f"FW Cdiff (DUT)    : {c_dut:.3f} fF" if c_dut else "FW Cdiff (DUT)    : n/a")
    print(f"FW Cdiff (open)   : {cdiff_open:.3f} fF")
    if c_dut is not None:
        c_deemb = c_dut - cdiff_open
        print(f"FW Cdiff (deemb)  : {c_deemb:.3f} fF")
        if c_es:
            print(f"offset raw   vs ES: {100*(c_dut - c_es)/c_es:+.1f}%")
            print(f"offset deemb vs ES: {100*(c_deemb - c_es)/c_es:+.1f}%")
    print(f"(open solve {solve_s:.0f}s, peak {peak_mb} MB)")


if __name__ == "__main__":
    main()
