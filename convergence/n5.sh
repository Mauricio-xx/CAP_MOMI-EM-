#!/bin/bash
# Converged density for the remaining layer counts, same recipe as N=4:
# two lengths at w=7, three meshes each, one domain (5.0 / 10.0) throughout.
# N=3 is Metal2..Metal4, N=2 is Metal3..Metal4. Both are cheaper than N=4.
set -u
cd "$(dirname "$0")"
BM=/home/montanares/git/slim-pdk/issue92_em/scripts/build_model.py
GDS=/home/montanares/git/slim-pdk/issue92_em/gds

run_one () {
  tag=$1; net=$2; lc=$3
  if [ ! -f "${tag}_out/terminal-C.csv" ]; then
    if [ ! -f "$tag.msh" ]; then
      source /home/montanares/venv/palace/bin/activate
      python $BM "$net" "$tag" "$lc" 5.0 10.0 > $tag.build.log 2>&1 || { echo "$tag BUILD FAILED"; return; }
    fi
    apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 &
    PID=$!
    while kill -0 $PID 2>/dev/null; do
      avail=$(free -g | awk '/^Mem:/{print $7}')
      if [ "$avail" -lt 14 ]; then
        echo "ABORT $tag ${avail}GB"; pkill -P $PID 2>/dev/null; kill -9 $PID 2>/dev/null
        pkill -9 -f "palace .*$tag.json" 2>/dev/null; rm -f $tag.msh; return
      fi
      sleep 5
    done
    wait $PID || { echo "$tag SOLVE FAILED"; rm -f $tag.msh; return; }
  fi
  tets=$(grep -o 'tets=[0-9]*' $tag.build.log 2>/dev/null | head -1 | cut -d= -f2)
  python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('RESULT $tag lc=$lc tets=${tets:-?} C12=%.4f fF' % (-float(r[1][2])*1e15))"
  rm -f $tag.msh
}

for lc in 0.120 0.080 0.060; do
  t=${lc/./p}
  run_one n5_l5p5_m5_lc${t} $GDS/g2n5_l5p5_w7.json $lc
  run_one n5_l10_m5_lc${t}  $GDS/g2n5_l10_w7.json  $lc
done
echo "N5 DONE"
