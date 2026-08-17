#!/bin/bash
# How much can a coarse mesh inflate the EXTRACTED density?
#
# The ~19% by which the shipped 1.09 fF/um2 sat above converged Palace per drawn
# coupled row was the sparse-via drawn layout, not a mesh limit and not a density
# error; on the base+tip via-fixed cell the converged solve lands on 1.09.
# Test: extract the delta-length density from the same geometry pair at meshes from
# deliberately coarse down to the finest we can afford, and see how far it climbs.
#
# Both members of every pair must share the mesh AND the domain, so everything here
# runs at margin 5.0 / z_hi 10.0. l10_w7 has no runs at that domain yet, so it gets
# the full ladder; l5p5_w7 already has 0.12 / 0.08 / 0.06 there and only needs the
# coarse end.
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
        echo "ABORT $tag: ${avail}GB available"
        pkill -P $PID 2>/dev/null; kill -9 $PID 2>/dev/null
        pkill -9 -f "palace .*$tag.json" 2>/dev/null
        rm -f $tag.msh; return
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

# coarse end first: cheap, and it is where the hypothesis lives
for lc in 0.40 0.30 0.20; do
  t=${lc/./p}
  run_one l5p5w7_m5_lc${t} $GDS/pcell_l5p5_w7_n4.json $lc
  run_one l10w7_m5_lc${t}  $GDS/pcell_l10_w7_n4.json  $lc
done
# then the medium rungs so l10 matches the l5p5 ladder already on disk
run_one l10w7_m5_lc0p120 $GDS/pcell_l10_w7_n4.json 0.120
run_one l10w7_m5_lc0p080 $GDS/pcell_l10_w7_n4.json 0.080
echo "MESHTEST DONE"
