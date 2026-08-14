#!/bin/bash
# Third convergence point for nar_l20_w2 (lc 0.05, 4.96M tets). Palace runs under a
# watchdog that kills it if free memory drops below 14 GB, so the box never goes
# under the 10 GB floor.
set -u
cd "$(dirname "$0")"
tag=nar20_lc0p050
if [ ! -f "$tag.msh" ]; then
  source /home/montanares/venv/palace/bin/activate
  python /home/montanares/git/slim-pdk/issue92_em/scripts/build_model.py \
    /home/montanares/git/slim-pdk/issue92_em/gds/nar_l20_w2.json "$tag" 0.050 5.0 10.0 \
    > $tag.build.log 2>&1 || { echo "BUILD FAILED"; exit 1; }
  echo "rebuilt mesh: $(grep -o 'tets=[0-9]*' $tag.build.log | head -1)"
fi

apptainer exec /opt/palace/current/palace_016.sif palace -np 8 "$tag.json" > $tag.solve.log 2>&1 &
PID=$!

while kill -0 $PID 2>/dev/null; do
  avail=$(free -g | awk '/^Mem:/{print $7}')
  if [ "$avail" -lt 14 ]; then
    echo "ABORT: available memory ${avail}GB below floor, killing palace"
    pkill -P $PID 2>/dev/null
    kill -9 $PID 2>/dev/null
    pkill -9 -f "palace .*$tag.json" 2>/dev/null
    rm -f $tag.msh
    exit 2
  fi
  sleep 5
done
wait $PID; rc=$?
if [ $rc -ne 0 ]; then echo "$tag SOLVE FAILED rc=$rc"; rm -f $tag.msh; exit $rc; fi

python3 -c "
import csv
r=list(csv.reader(open('${tag}_out/terminal-C.csv')))
print('RESULT $tag lc=0.050 tets=4957453 C12=%.4f fF' % (-float(r[1][2])*1e15))"
rm -f $tag.msh
