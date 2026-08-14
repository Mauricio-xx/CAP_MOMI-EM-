#!/bin/bash
set -u
source /home/montanares/venv/palace/bin/activate
cd "$(dirname "$0")"
run_one () {
  tag=$1; net=$2; lc=$3
  [ -f "$tag.json" ] || python ../build_model.py "$net" "$tag" "$lc" 5.0 10.0 > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
  [ -f "${tag}_out/terminal-C.csv" ] || apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 || { echo "$tag SOLVE FAILED"; return; }
  c=$(python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('%.4f' % (-float(r[1][2])*1e15))")
  echo "RESULT $tag C12=${c} fF"
  rm -f $tag.msh
}
run_one n2_l5p5 ../gds/n2_l5p5_w7.json 0.12
run_one n2_l10  ../gds/n2_l10_w7.json  0.12
run_one sm_2x2  ../gds/sm_2x2.json     0.08
run_one sm_3x3  ../gds/sm_3x3.json     0.08
run_one sm_2x2_same ../gds/sm_2x2_same.json 0.08
echo "SWEEP6 DONE"
