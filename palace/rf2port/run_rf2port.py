#!/usr/bin/env python3
"""Reference-matched 2-port full-wave campaign driver (cap_mom, IHP sg13cmos5l).

Mirrors KrzysztofHerman/IHP__TEST9203 testbenches/em: each capacitor is wrapped
in a 2-port RF testbench (Metal4 feeds + 201/202 markers + Metal1 guard ring),
solved with Palace (driven full-wave, order 2, refined_cellsize 0.5, ABC, 2 lumped
50 ohm ports Metal1->Metal4 in Z), converted to Touchstone .s2p, and the
differential capacitance extracted at ~60 MHz (Cdiff = Im(-(Y12+Y21)/2)/(2 pi f)).

Uses our proven gds2palace integration (as scripts/gds2palace_density.py), the
SG13CMOS5L.xml stackup (devices are sg13cmos5l), Palace 0.16 via apptainer.
Serial, RAM-gated, resumable. Only 'double' (opposite-side feed) devices: the
2-port wrapper shorts on 'same'/'none'.

Usage:
  run_rf2port.py [--build-only] [--min-free-gb N] [device_name ...]
Default device set = the starter double-feed sizes. device_name = basename in
campaign/gds_fixed/ (without .gds), e.g. cap_mom_double_07p8um.
"""
import os
import sys
import csv
import json
import time
import shutil
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/montanares/git/slim-pdk/issue92_em"
GDS_FIXED = f"{ROOT}/campaign/gds_fixed"
WF = os.path.expanduser("~/personal_exp/gds2palace_ihp_sg13g2/workflow")
SIF = os.path.expanduser("~/palace.sif")
COMBINE = os.path.expanduser("~/personal_exp/gds2palace_ihp_sg13g2/scripts/combine_extend_snp.py")
VENV_PY = os.path.expanduser("~/venv/palace/bin/python")
XML = f"{HERE}/SG13CMOS5L.xml"
BASE_GDS = f"{HERE}/TE_10.gds"
TB_DIR = f"{HERE}/tb"
RESULTS_DIR = f"{HERE}/results"
OUTCSV = f"{RESULTS_DIR}/rf2port_results.csv"
NP = 8

STARTER_DOUBLE = [
    "cap_mom_double_02p0um", "cap_mom_double_04p9um", "cap_mom_double_07p8um",
    "cap_mom_double_10p7um", "cap_mom_double_13p6um",
]

sys.path.insert(0, HERE)
import build_cap_rf_tb as tb            # noqa: E402  (gdstk, system python3 OK)
# evaluate_C needs scikit-rf -> run it via the venv python as a subprocess.

MODEL_TMPL = '''import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'gds2palace')))
from gds2palace import *
gds_filename = "{gds}"
XML_filename = "{xml}"
script_path = utilities.get_script_path(__file__)
model_basename = utilities.get_basename(__file__)
sim_path = utilities.create_sim_path(script_path, model_basename)
print('Simulation data directory: ', sim_path)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
settings = {{}}
settings['unit'] = 1e-6
settings['margin'] = 20
settings['air_around'] = 20
settings['fstart'] = 0e9
settings['fstop'] = 20e9
settings['fstep'] = 0.1e9
settings['refined_cellsize'] = 0.5
settings['cells_per_wavelength'] = 10
settings['meshsize_max'] = 100
settings['order'] = 2
settings['adaptive_mesh_iterations'] = 0
settings['boundary'] = ["ABC", "ABC", "ABC", "ABC", "ABC", "ABC"]
settings['no_gui'] = True
simulation_ports = simulation_setup.all_simulation_ports()
simulation_ports.add_port(simulation_setup.simulation_port(
    portnumber=1, voltage=1, port_Z0=50,
    source_layernum=201, from_layername='Metal1', to_layername='Metal4', direction='Z'))
simulation_ports.add_port(simulation_setup.simulation_port(
    portnumber=2, voltage=1, port_Z0=50,
    source_layernum=202, from_layername='Metal1', to_layername='Metal4', direction='Z'))
materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate(XML_filename)
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)
allpolygons = gds_reader.read_gds(gds_filename, layernumbers, purposelist=[0],
    metals_list=metals_list, preprocess=True, merge_polygon_size=0)
settings['simulation_ports'] = simulation_ports
settings['materials_list'] = materials_list
settings['dielectrics_list'] = dielectrics_list
settings['metals_list'] = metals_list
settings['layernumbers'] = layernumbers
settings['allpolygons'] = allpolygons
settings['sim_path'] = sim_path
settings['model_basename'] = model_basename
excite_ports = simulation_ports.all_active_excitations()
simulation_setup.create_palace(excite_ports, settings)
utilities.create_run_script(sim_path)
print('BUILD_OK', sim_path)
'''


def free_gb():
    out = subprocess.check_output(["free", "-g"]).decode()
    for line in out.splitlines():
        if line.startswith("Mem:"):
            return int(line.split()[6])
    return 0


def load_done():
    done = set()
    if os.path.exists(OUTCSV):
        for r in csv.DictReader(open(OUTCSV)):
            done.add(r["device"])
    return done


def append_row(row):
    new = not os.path.exists(OUTCSV)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTCSV, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["device", "basename", "nports", "Cdiff_fF", "s2p",
                        "peak_rss_mb", "build_s", "solve_s"])
        w.writerow(row)


def wrap_device(name):
    """Wrap campaign/gds_fixed/<name>.gds into a 2-port testbench GDS."""
    os.makedirs(TB_DIR, exist_ok=True)
    template = tb.extract_template(__import__("pathlib").Path(BASE_GDS))
    cap_path = __import__("pathlib").Path(f"{GDS_FIXED}/{name}.gds")
    out_path, top = tb.build_testbench(template, cap_path, __import__("pathlib").Path(TB_DIR))
    return str(out_path)


def build_model(name, tb_gds):
    basename = f"{name}_rf_tb"
    shutil.copy(tb_gds, f"{WF}/{basename}.gds")
    model_py = f"{WF}/{basename}.py"
    with open(model_py, "w") as f:
        f.write(MODEL_TMPL.format(gds=f"{basename}.gds", xml=XML))
    t0 = time.time()
    r = subprocess.run([VENV_PY, f"{basename}.py"], cwd=WF, capture_output=True, text=True)
    if r.returncode != 0 or "BUILD_OK" not in r.stdout:
        print(f"[BUILD FAIL] {basename}\n{r.stdout[-1500:]}\n{r.stderr[-800:]}")
        return None, None
    sim_path = f"{WF}/palace_model/{basename}_data"
    return sim_path, time.time() - t0


def check_ports(sim_path):
    pj = f"{sim_path}/port_information.json"
    if not os.path.exists(pj):
        return None
    return len(json.load(open(pj))["ports"])


def solve(sim_path, min_free_gb):
    fg = free_gb()
    if fg < min_free_gb:
        print(f"[SKIP] only {fg} GB free (< {min_free_gb})")
        return None, None
    t0 = time.time()
    r = subprocess.run(
        ["/usr/bin/time", "-v", "apptainer", "exec", SIF, "palace", "-np", str(NP), "config.json"],
        cwd=sim_path, capture_output=True, text=True)
    solve_s = time.time() - t0
    log = r.stderr
    open(f"{sim_path}/solve.log", "w").write(r.stdout + "\n---TIME---\n" + log)
    if r.returncode != 0 or "MPI_Abort" in r.stdout or "Verification failed" in r.stdout:
        print(f"[SOLVE FAIL] {sim_path}\n{r.stdout[-1200:]}")
        return None, solve_s
    peak_mb = None
    for line in log.splitlines():
        if "Maximum resident set size" in line:
            peak_mb = int(line.split()[-1]) // 1024
    return peak_mb, solve_s


def combine_and_eval(name, sim_path):
    """port-S.csv -> Touchstone (combine) -> differential Cdiff @~60 MHz (evaluate_C).

    Both steps run under the venv python (scikit-rf). Uses the BASE (non
    de-embedded) .s2p, matching the reference. Archives the .s2p into results/.
    """
    import pathlib
    import shutil as _sh
    basename = f"{name}_rf_tb"
    r = subprocess.run([VENV_PY, COMBINE], cwd=sim_path, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[COMBINE FAIL] {basename}\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
        return None, None
    s2ps = sorted(pathlib.Path(sim_path).rglob("*.s2p"))
    if not s2ps:
        print(f"[NO S2P] {basename}")
        return None, None
    s2p = str(next((p for p in s2ps if p.stem == basename), s2ps[0]))
    ev = subprocess.run([VENV_PY, f"{HERE}/evaluate_C.py", s2p,
                         "--gds-name", name, "--results-dir", RESULTS_DIR],
                        capture_output=True, text=True)
    cdiff = None
    for line in ev.stdout.splitlines():
        if "Extracted differential capacitance" in line:
            cdiff = float(line.split(":")[1].strip().split()[0])
    if cdiff is None:
        print(f"[EVAL FAIL] {basename}\n{ev.stdout[-600:]}\n{ev.stderr[-400:]}")
        return None, None
    # archive the base .s2p into the repo results dir
    archive = f"{RESULTS_DIR}/{name}.s2p"
    try:
        _sh.copy(s2p, archive)
    except OSError:
        archive = s2p
    return archive, cdiff


def process(name, build_only, min_free_gb):
    print(f"\n==== {name} ====", flush=True)
    basename = f"{name}_rf_tb"
    sim_path = f"{WF}/palace_model/{basename}_data"
    port_s = f"{sim_path}/output/{basename}/port-S.csv"
    # solve-level resume: if this device already produced port-S.csv, skip the
    # (expensive) wrap/build/solve and go straight to extraction.
    if os.path.exists(port_s) and not build_only:
        print("  [reuse existing solve]")
        nports = check_ports(sim_path) or 2
        peak_mb, solve_s, build_s = "", "", ""
    else:
        tb_gds = wrap_device(name)
        sim_path, build_s = build_model(name, tb_gds)
        if sim_path is None:
            return
        nports = check_ports(sim_path)
        print(f"  built ({build_s:.0f}s), ports={nports}")
        if nports != 2:
            print(f"  [ABORT] expected 2 ports, got {nports}")
            return
        if build_only:
            return
        peak_mb, solve_s = solve(sim_path, min_free_gb)
        if solve_s is None:
            return
    s2p, cdiff = combine_and_eval(name, sim_path)
    if cdiff is None:
        return
    # drop the big mesh to save disk
    for msh in __import__("pathlib").Path(sim_path).glob("*.msh"):
        try:
            os.remove(msh)
        except OSError:
            pass
    def fmt(x):
        return f"{x:.0f}" if isinstance(x, (int, float)) else (x or "")
    append_row([name, f"{name}_rf_tb", nports, f"{cdiff:.4f}", s2p,
                peak_mb or "", fmt(build_s), fmt(solve_s)])
    print(f"  [OK] Cdiff = {cdiff:.3f} fF  (solve {fmt(solve_s)}s, peak {peak_mb} MB)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("devices", nargs="*", help="device basenames in campaign/gds_fixed/")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--min-free-gb", type=int, default=25)
    args = ap.parse_args()
    devs = args.devices or STARTER_DOUBLE
    done = load_done()
    for name in devs:
        if name in done and not args.build_only:
            print(f"[skip done] {name}")
            continue
        process(name, args.build_only, args.min_free_gb)
    print("\nDone. Results:", OUTCSV)


if __name__ == "__main__":
    main()
