#!/bin/bash
# One Palace run of our shipped cell (bar-terminated, l=5.5 w=7, feed=double, M1..M4)
# WITH the electrostatic field written for visualization. Run at -np 1 on purpose:
# single rank means one mesh partition, so the ParaView field is not split across
# subdomains (the missing-field-in-subdomains artifact Palace shows under MPI). The
# volume field is saved, so any cut plane can be taken in post; no dummy plane needed.
set -u
cd "$(dirname "$0")/.."
RUN="$(pwd)/palace/field_run"; mkdir -p "$RUN"
TAG=pcell_w7_field
if ls "$RUN/${TAG}_out"/paraview*/*.pvd >/dev/null 2>&1; then echo "already done"; else
  source /home/montanares/venv/palace/bin/activate
  python3 - <<EOF
import sys, json
sys.path.insert(0, "scripts")
from build_model import build
build("gds/fd_l5p5_w7_dbl.json", "$RUN/$TAG", lc_fine=0.10, z_lo=-1.0, z_hi=10.0,
      domain=(-6.2, -5.32, 10.94, 11.55))
cfg = json.load(open("$RUN/$TAG.json"))
cfg["Solver"]["Electrostatic"] = {"Save": 2}   # write the terminal field solutions
json.dump(cfg, open("$RUN/$TAG.json", "w"), indent=2)
print("patched config with Solver.Electrostatic.Save=2")
EOF
  deactivate 2>/dev/null || true
  ( cd "$RUN" && apptainer exec /opt/palace/current/palace_016.sif palace -np 1 "$TAG.json" \
      > "$TAG.solve.log" 2>&1 )
fi
echo "=== field output tree ==="
find "$RUN/${TAG}_out" -maxdepth 2 -type f 2>/dev/null | head -30
echo "FIELD RUN DONE"
