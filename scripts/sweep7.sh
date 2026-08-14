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
run_one nar_l20_w2 ../gds/nar_l20_w2.json 0.10
run_one nar_l50_w2 ../gds/nar_l50_w2.json 0.12
echo "SWEEP7 DONE"
