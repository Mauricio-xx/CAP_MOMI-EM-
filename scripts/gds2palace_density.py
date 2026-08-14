#!/usr/bin/env python3
"""Recompute the cap_cmomi density series in gds2palace (full-wave), two stackups.

For each cell: add the in-plane port (add_port_cap_cmomi.py), template a gds2palace
model, build headless, solve Palace, read the low-frequency capacitance from the
1-port S-parameter (C = Im(Y11)/2*pi*f). Serial, memory-guarded.

Two stackups per cell:
  sub   = SG13G2_200um.xml   (real g2 substrate, matches the reference substrate notes)
  nosub = SG13G2_nosub.xml   (substrate pushed away, ~ comb-to-comb only)

Cells:
  N=4 (M1-M4, our cap): fd width sweep w=2,5,7,15 at l=5.5 -> slope -> density
  N=2 (M1-M2):          n2 length pair l=5.5,10 at w=7   -> delta-L -> density

Writes palace/gds2palace/density_runs.csv (one row per cell x stackup).
Resumable: skips a (cell,stackup) already in the CSV.
"""
import os, sys, csv, json, subprocess, time
import numpy as np

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
WF = os.path.expanduser("~/personal_exp/gds2palace_ihp_sg13g2/workflow")
SIF = os.path.expanduser("~/palace.sif")
ADD_PORT = f"{ROOT}/scripts/add_port_cap_cmomi.py"
OUTDIR = f"{ROOT}/palace/gds2palace"
OUTCSV = f"{OUTDIR}/density_runs.csv"
MIN_FREE_GB = 14          # abort a run if available RAM would drop below this
NP = 8

STACKS = {"sub": "SG13G2_200um.xml", "nosub": "SG13G2_nosub.xml"}

# (json_base, N_metal, l_um, w_um, coupled_rows)
# N=4 (M1-M4, our cap): width sweep -> slope -> density
# N=2/3/5: length pair at w=7 (l=5.5 vs l=10) -> delta-L -> density
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

MODEL_TMPL = '''import os, sys, subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'gds2palace')))
from gds2palace import *
start_simulation = False
gds_filename = "{gds}"
XML_filename = "{xml}"
preprocess_gds = True
merge_polygon_size = 0
script_path = utilities.get_script_path(__file__)
model_basename = utilities.get_basename(__file__)
sim_path = utilities.create_sim_path(script_path, model_basename)
print('Simulation data directory: ', sim_path)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
settings = {{}}
settings['unit'] = 1e-6
settings['margin'] = 20
settings['fstart'] = 0e9
settings['fstop'] = 20e9
settings['fstep'] = 2e9
settings['refined_cellsize'] = 0.2
settings['cells_per_wavelength'] = 10
settings['meshsize_max'] = 10
settings['order'] = 2
settings['adaptive_mesh_iterations'] = 0
settings['no_gui'] = True
simulation_ports = simulation_setup.all_simulation_ports()
simulation_ports.add_port(simulation_setup.simulation_port(
    portnumber=1, voltage=1, port_Z0=50,
    source_layernum=201, target_layername='{layer}', direction='x'))
materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate(XML_filename)
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)
allpolygons = gds_reader.read_gds(gds_filename, layernumbers, purposelist=[0],
    metals_list=metals_list, preprocess=preprocess_gds, merge_polygon_size=merge_polygon_size)
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
'''


def free_gb():
    out = subprocess.check_output(["free", "-g"]).decode()
    for line in out.splitlines():
        if line.startswith("Mem:"):
            return int(line.split()[6])
    return 0


def load_done():
    done = {}
    if os.path.exists(OUTCSV):
        for r in csv.DictReader(open(OUTCSV)):
            done[(r["cell"], r["stackup"])] = r
    return done


def append_row(row):
    new = not os.path.exists(OUTCSV)
    with open(OUTCSV, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["cell", "N_metal", "l_um", "w_um", "rows", "stackup", "C_fF"])
        w.writerow(row)


def extract_C(basename):
    sdir = f"{WF}/palace_model/{basename}_data/output/{basename}"
    rows = list(csv.reader(open(f"{sdir}/port-S.csv")))
    Z0 = 50.0
    best = None  # lowest-frequency point
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        f = float(r[0]) * 1e9
        S = 10 ** (float(r[1]) / 20) * np.exp(1j * np.deg2rad(float(r[2])))
        Y = (1 / Z0) * (1 - S) / (1 + S)
        C = Y.imag / (2 * np.pi * f) * 1e15
        if best is None or f < best[0]:
            best = (f, C)
    return best[1]


def run_one(base, stk_key):
    xml = STACKS[stk_key]
    basename = f"capd_{base}_{stk_key}"
    # 1) add port (auto-detects the bottom metal layer, prints PORT_LAYER=...)
    ap = subprocess.run([sys.executable, ADD_PORT, f"{ROOT}/gds/{base}.json"],
                        capture_output=True, text=True, check=True)
    layer = "Metal1"
    for line in ap.stdout.splitlines():
        if line.startswith("PORT_LAYER="):
            layer = line.split("=", 1)[1].strip()
    gds_ported = f"{ROOT}/gds/{base}_port.gds"
    gds_wf = f"{basename}.gds"
    subprocess.run(["cp", gds_ported, f"{WF}/{gds_wf}"], check=True)
    # 2) template model
    model_py = f"{WF}/{basename}.py"
    with open(model_py, "w") as f:
        f.write(MODEL_TMPL.format(gds=gds_wf, xml=xml, layer=layer))
    # 3) build headless
    env = dict(os.environ)
    r = subprocess.run([sys.executable, basename + ".py"], cwd=WF, env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[BUILD FAIL] {basename}\n{r.stdout[-1500:]}\n{r.stderr[-800:]}")
        return None
    # 4) solve (memory guard)
    fg = free_gb()
    if fg < MIN_FREE_GB:
        print(f"[SKIP] {basename}: only {fg} GB free (< {MIN_FREE_GB})")
        return None
    sdir = f"{WF}/palace_model/{basename}_data"
    r = subprocess.run(["apptainer", "exec", SIF, "palace", "-np", str(NP), "config.json"],
                       cwd=sdir, capture_output=True, text=True)
    if "Verification failed" in r.stdout or "MPI_Abort" in r.stdout or r.returncode != 0:
        tail = r.stdout[-1200:]
        print(f"[SOLVE FAIL] {basename}\n{tail}")
        return None
    # 5) extract C
    try:
        C = extract_C(basename)
    except Exception as e:
        print(f"[EXTRACT FAIL] {basename}: {e}")
        return None
    # cleanup big mesh to save disk
    try:
        os.remove(f"{sdir}/{basename}.msh")
    except OSError:
        pass
    return C


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    done = load_done()
    for base, N, l, w, rows in CELLS:
        for stk in STACKS:
            if (base, stk) in done:
                print(f"[skip done] {base} {stk} = {done[(base,stk)]['C_fF']} fF")
                continue
            t0 = time.time()
            print(f"\n==== {base}  {stk}  (N={N}, l={l}, w={w}, rows={rows}) ====", flush=True)
            C = run_one(base, stk)
            if C is None:
                print(f"[no result] {base} {stk}")
                continue
            append_row([base, N, l, w, rows, stk, f"{C:.4f}"])
            print(f"[OK] {base} {stk}  C = {C:.3f} fF  ({time.time()-t0:.0f}s)", flush=True)
    print("\nAll done. Results in", OUTCSV)


if __name__ == "__main__":
    main()
