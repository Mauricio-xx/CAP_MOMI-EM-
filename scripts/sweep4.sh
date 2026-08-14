#!/bin/bash
set -u
source /home/montanares/venv/palace/bin/activate
cd "$(dirname "$0")"
tag=w15_l10_dbl
[ -f "$tag.json" ] || python ../build_model.py ../gds/pcell_l10_w15_dbl.json $tag 0.12 > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; exit; }
[ -f "${tag}_out/terminal-C.csv" ] || apptainer exec /opt/palace/current/palace_016.sif palace -np 8 $tag.json > $tag.solve.log 2>&1 || { echo "$tag SOLVE FAILED"; exit; }
c=$(python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('%.4f' % (-float(r[1][2])*1e15))")
echo "RESULT $tag C12=${c} fF"
echo "SWEEP4 DONE"
