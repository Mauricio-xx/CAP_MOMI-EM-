#!/bin/bash
# The 5.5x7 convergence triple mixed domain settings: lc 0.12 and 0.08 came from
# sweep.sh at the build_model.py defaults (margin 3.0, z_hi 8.0) while lc 0.06 was
# built at 5.0 / 10.0. A larger domain raises C12 by ~0.3%, which biases the fitted
# convergence rate. Re-run the two coarser points at 5.0 / 10.0 so the whole triple
# matches the rest of the dataset, which is all at 5.0 / 10.0.
set -u
cd "$(dirname "$0")"
BM=/home/montanares/git/slim-pdk/issue92_em/scripts/build_model.py
NET=/home/montanares/git/slim-pdk/issue92_em/gds/pcell_l5p5_w7_n4.json
run_one () {
  tag=$1; lc=$2
  if [ ! -f "${tag}_out/terminal-C.csv" ]; then
    source /home/montanares/venv/palace/bin/activate
    python $BM "$NET" "$tag" "$lc" 5.0 10.0 > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
    apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 &
    PID=$!
    while kill -0 $PID 2>/dev/null; do
      avail=$(free -g | awk '/^Mem:/{print $7}')
      if [ "$avail" -lt 14 ]; then echo "ABORT $tag ${avail}GB"; kill -9 $PID 2>/dev/null; rm -f $tag.msh; return; fi
      sleep 5
    done
    wait $PID || { echo "$tag SOLVE FAILED"; rm -f $tag.msh; return; }
  fi
  tets=$(grep -o 'tets=[0-9]*' $tag.build.log | head -1 | cut -d= -f2)
  python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('RESULT $tag lc=$lc tets=$tets C12=%.4f fF' % (-float(r[1][2])*1e15))"
  rm -f $tag.msh
}
run_one l5p5w7_m5_lc0p120 0.120
run_one l5p5w7_m5_lc0p080 0.080
echo "REMATCH DONE"
