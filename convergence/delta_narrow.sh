#!/bin/bash
# Mesh-matched delta-length on the narrow geometry: nar_l50_w2 at the same lc as
# nar_l20_w2 (0.10, and 0.07 if it fits). The per-column capacitance from the
# difference cancels the end structures and most of the mesh bias, which is the
# quantity the model's area-only law has to reproduce.
set -u
cd "$(dirname "$0")"
BM=/home/montanares/git/slim-pdk/issue92_em/scripts/build_model.py
GDS=/home/montanares/git/slim-pdk/issue92_em/gds

run_one () {
  tag=$1; net=$2; lc=$3
  if [ ! -f "$tag.msh" ] && [ ! -f "${tag}_out/terminal-C.csv" ]; then
    source /home/montanares/venv/palace/bin/activate
    python $BM "$net" "$tag" "$lc" 5.0 10.0 > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
  fi
  tets=$(grep -o 'tets=[0-9]*' $tag.build.log | head -1 | cut -d= -f2)
  echo "BUILT $tag lc=$lc tets=$tets"
  if [ ! -f "${tag}_out/terminal-C.csv" ]; then
    apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 &
    PID=$!
    while kill -0 $PID 2>/dev/null; do
      avail=$(free -g | awk '/^Mem:/{print $7}')
      if [ "$avail" -lt 14 ]; then
        echo "ABORT $tag: available ${avail}GB below floor"
        pkill -P $PID 2>/dev/null; kill -9 $PID 2>/dev/null
        pkill -9 -f "palace .*$tag.json" 2>/dev/null
        rm -f $tag.msh; return
      fi
      sleep 5
    done
    wait $PID || { echo "$tag SOLVE FAILED"; rm -f $tag.msh; return; }
  fi
  c=$(python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('%.4f' % (-float(r[1][2])*1e15))")
  echo "RESULT $tag lc=$lc tets=$tets C12=${c} fF"
  rm -f $tag.msh
}

run_one nar50_lc0p100 $GDS/nar_l50_w2.json 0.100
run_one nar50_lc0p070 $GDS/nar_l50_w2.json 0.070
echo "DELTA DONE"
