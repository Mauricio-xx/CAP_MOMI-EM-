#!/bin/bash
set -u
source /home/montanares/venv/palace/bin/activate
cd "$(dirname "$0")"
run_one () {  # tag net lc margin zhi
  tag=$1; net=$2; lc=$3; mg=$4; zh=$5
  [ -f "$tag.json" ] || python ../build_model.py "$net" "$tag" "$lc" "$mg" "$zh" > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
  [ -f "${tag}_out/terminal-C.csv" ] || apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 || { echo "$tag SOLVE FAILED"; return; }
  c=$(python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('%.4f' % (-float(r[1][2])*1e15))")
  echo "RESULT $tag margin=$mg zhi=$zh C12=${c} fF"
}
run_one m8_l5p5_w7  ../gds/pcell_l5p5_w7_n4.json   0.12 8.0 14.0
run_one m8_l5p5_w15 ../gds/pcell_l5p5_w15_dbl.json 0.12 8.0 14.0
run_one m8_l10_w7   ../gds/pcell_l10_w7_n4.json    0.12 8.0 14.0
run_one m8_l10_w15  ../gds/pcell_l10_w15_dbl.json  0.12 8.0 14.0
echo "SWEEP5 DONE"
