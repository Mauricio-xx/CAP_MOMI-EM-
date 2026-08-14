#!/bin/bash
# Measure the DRAWN single-side feed capacitance.
#
# The model adds Cfeed = cfeed_per_um[N] * feed_width for feed='same' and
# nothing for feed='double', so its claim is exactly about the difference
# between the two layouts at the same size. That is what this measures.
#
# Both members of a pair are built in the SAME outer domain. Their bounding
# boxes differ by about 0.85 um in x, and a domain that tracked each bbox would
# shift the boundary between them; that is worth ~0.25% of the total, which is
# larger than the feature being measured.
set -u
cd "$(dirname "$0")/.."
BM=scripts/build_model.py
RUN=${RUN:-/tmp/claude-30044/-home-montanares-git-slim-pdk/66fa46d4-dc6b-456d-a8da-0ab6a4b47dc8/scratchpad/feed}
mkdir -p "$RUN"

domain_of () {   # union bbox of a pair, plus the margin, printed as x0 y0 x1 y1
  python3 - "$1" "$2" "$3" <<'EOF'
import json, sys
m = float(sys.argv[3])
xs, ys = [], []
for f in sys.argv[1:3]:
    d = json.load(open(f))
    for e in d["nets"]:
        for polys in e["layers"].values():
            for p in polys:
                xs += [x for x, _ in p]; ys += [y for _, y in p]
print(f"{min(xs)-m} {min(ys)-m} {max(xs)+m} {max(ys)+m}")
EOF
}

run_one () {     # tag netjson lc domain...
  tag=$1; net=$2; lc=$3; shift 3
  out="$RUN/${tag}_out/terminal-C.csv"
  if [ ! -f "$out" ]; then
    if [ ! -f "$RUN/$tag.msh" ]; then
      source /home/montanares/venv/palace/bin/activate
      python3 - "$net" "$RUN/$tag" "$lc" "$@" > "$RUN/$tag.build.log" 2>&1 <<'EOF' || { echo "$tag BUILD FAILED"; return; }
import sys
sys.path.insert(0, "scripts")
from build_model import build
net, pref, lc = sys.argv[1], sys.argv[2], float(sys.argv[3])
dom = tuple(float(v) for v in sys.argv[4:8])
build(net, pref, lc_fine=lc, z_lo=-1.0, z_hi=10.0, domain=dom)
EOF
      deactivate 2>/dev/null || true
    fi
    ( cd "$RUN" && apptainer exec /opt/palace/current/palace_016.sif \
        palace -np 8 "$tag.json" > "$tag.solve.log" 2>&1 ) &
    PID=$!
    while kill -0 $PID 2>/dev/null; do
      avail=$(free -g | awk '/^Mem:/{print $7}')
      if [ "$avail" -lt 14 ]; then
        echo "ABORT $tag ${avail}GB"; pkill -P $PID 2>/dev/null; kill -9 $PID 2>/dev/null
        pkill -9 -f "palace .*$tag.json" 2>/dev/null; rm -f "$RUN/$tag.msh"; return
      fi
      sleep 5
    done
    wait $PID || { echo "$tag SOLVE FAILED"; rm -f "$RUN/$tag.msh"; return; }
  fi
  python3 -c "
import csv
r=list(csv.reader(open('$out')))
print('RESULT $tag lc=$lc C12=%.4f fF' % (-float(r[1][2])*1e15))"
  rm -f "$RUN/$tag.msh"
}

LC=${LC:-0.10}
# PREFIX/TAGS let the same driver sweep layer windows instead of widths, with
# the pair-in-one-domain rule unchanged.
PREFIX=${PREFIX:-fd_l5p5_w}
for w in "${@:-2 5 7 15}"; do
  D=gds/${PREFIX}${w}_dbl.json
  S=gds/${PREFIX}${w}_same.json
  [ -f "$D" ] && [ -f "$S" ] || { echo "missing pair for w=$w"; continue; }
  DOM=$(domain_of "$D" "$S" 5.0)
  t=${LC/./p}
  run_one "${PREFIX}${w}_dbl_lc${t}"  "$D" "$LC" $DOM
  run_one "${PREFIX}${w}_same_lc${t}" "$S" "$LC" $DOM
  # the PCell's own no-feed branch, in the SAME domain: it is the reference the
  # model's feed=0 describes, so C(same)-C(none) and C(dbl)-C(none) are the two
  # feed terms with nothing hand-made in between.
  N=gds/${PREFIX}${w}_none.json
  [ -f "$N" ] && run_one "${PREFIX}${w}_none_lc${t}" "$N" "$LC" $DOM
done
echo "FEED SWEEP DONE"
