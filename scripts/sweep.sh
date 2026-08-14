#!/bin/bash
# Serial Palace sweep. Never run these in parallel: the box is shared.
set -u
source /home/montanares/venv/palace/bin/activate
cd "$(dirname "$0")"
run_one () {  # tag netjson lc
  tag=$1; net=$2; lc=$3
  if [ ! -f "$tag.json" ]; then
    python ../build_model.py "$net" "$tag" "$lc" > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
  fi
  if [ ! -f "${tag}_out/terminal-C.csv" ]; then
    apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 || { echo "$tag SOLVE FAILED"; return; }
  fi
  c=$(python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('%.4f' % (-float(r[1][2])*1e15))")
  tets=$(grep -o 'tets=[0-9]*' $tag.build.log | head -1)
  echo "RESULT $tag lc=$lc $tets C12=${c} fF"
}
run_one l5p5_n4_lc0p08 ../gds/pcell_l5p5_w7_n4.json 0.08
run_one l10_n4_lc0p12  ../gds/pcell_l10_w7_n4.json  0.12
run_one l10_n4_lc0p08  ../gds/pcell_l10_w7_n4.json  0.08
run_one l5p5_n3_lc0p12 ../gds/pcell_l5p5_w7_n3.json 0.12
run_one l10_n3_lc0p12  ../gds/pcell_l10_w7_n3.json  0.12
echo "SWEEP DONE"
