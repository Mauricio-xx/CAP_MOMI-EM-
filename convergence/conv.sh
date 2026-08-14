#!/bin/bash
# Mesh-convergence check on the small/narrow geometries that the small-device
# finding rests on. Only lc_fine changes; margin (5.0) and z_hi (10.0) are the
# same as the original single-mesh runs, so the comparison is clean.
set -u
source /home/montanares/venv/palace/bin/activate
cd "$(dirname "$0")"
BM=/home/montanares/git/slim-pdk/issue92_em/scripts/build_model.py
GDS=/home/montanares/git/slim-pdk/issue92_em/gds
TETCAP=4500000

run_one () {
  tag=$1; net=$2; lc=$3
  if [ ! -f "$tag.json" ]; then
    python $BM "$net" "$tag" "$lc" 5.0 10.0 > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
  fi
  tets=$(grep -o 'tets=[0-9]*' $tag.build.log | head -1 | cut -d= -f2)
  echo "BUILT $tag lc=$lc tets=$tets"
  if [ "${tets:-0}" -gt "$TETCAP" ]; then
    echo "SKIP $tag: $tets tets over cap $TETCAP"
    rm -f $tag.msh
    return
  fi
  avail=$(free -g | awk '/^Mem:/{print $7}')
  if [ "$avail" -lt 25 ]; then echo "SKIP $tag: only ${avail}GB available"; rm -f $tag.msh; return; fi
  if [ ! -f "${tag}_out/terminal-C.csv" ]; then
    apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 \
      || { echo "$tag SOLVE FAILED"; rm -f $tag.msh; return; }
  fi
  c=$(python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('%.4f' % (-float(r[1][2])*1e15))")
  echo "RESULT $tag lc=$lc tets=$tets C12=${c} fF"
  rm -f $tag.msh
}

run_one sm2x2_lc0p050  $GDS/sm_2x2.json     0.050
run_one sm2x2_lc0p035  $GDS/sm_2x2.json     0.035
run_one nar20_lc0p070  $GDS/nar_l20_w2.json 0.070
run_one nar20_lc0p050  $GDS/nar_l20_w2.json 0.050
echo "CONV DONE"
