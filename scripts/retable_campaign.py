"""Recompute the nominal capacitance column of the characterisation README.

The layouts do not change: the row-count correction is a model change, and the
XOR against the shipped PCell is empty on every conductor layer.  Only the
predicted value moves, and it has to move BEFORE the measurements arrive.  A
nominal table built on the old counting law makes the data look size-dependent,
and the natural reaction to that is to absorb the shape error into the fitted
density, which is exactly the mistake the correction removes.

Densities are unchanged (they are per coupled unit cell and transfer directly).
The single-side feed term is not: it is now fitted on the cell as drawn, so the
'same' column moves for a second reason.

Usage:  retable_campaign.py <README.md>   [rewrites in place, keeps a .bak]
"""
import math
import re
import shutil
import sys

DENSITY = {2: 0.55, 3: 0.82, 4: 1.09}
CFEED_SLOPE, CFEED_END = 0.1625, 0.0916      # no layer keying, see cap_cmomi.va
CFEED2_SLOPE = 0.152                          # opposite-side (double) feed, see cap_cmomi.va
UC_X, UC_Y = 0.84, 0.89
T_BAR = 0.21


def nlayers(row):
    if "_m3m4_" in row:
        return 2
    if "_m1m3_" in row or "_m2m4_" in row:
        return 3
    return 4


def values(w, n):
    ax = max(1, math.floor(w / UC_X + 1e-6))
    ay = max(2, math.floor(w / UC_Y + 1e-6))
    pad_len = ay * UC_Y + 2 * T_BAR
    c_area = DENSITY[n] * ax * UC_X * ay * UC_Y
    c_dbl = c_area + CFEED2_SLOPE * pad_len            # opposite-side (double) feed
    c_same = c_area + CFEED_SLOPE * pad_len + CFEED_END
    return ax, ay, c_dbl, c_same


def fix_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    # both table shapes end in: <XxY> <gds double> <C double> <gds same> <C same>
    if len(cells) < 6 or "gds/" not in line:
        return line
    try:
        w = float(cells[-6])
    except ValueError:
        return line
    n = nlayers(line)
    ax, ay, c_dbl, c_same = values(w, n)
    cells[-5] = f"{ax} x {ay}"
    cells[-3] = f"{c_dbl:.2f}"
    cells[-1] = f"{c_same:.2f}"
    return "| " + " | ".join(cells) + " |\n"


NOTE_MARK = "> **Model corrections"
NOTE = """
> **Model corrections (layouts unchanged).** Two things moved since these
> structures were drawn, and neither touches the layout: the fabricated cells XOR
> to zero against the current PCell on every conductor layer.
>
> The nominal values below count the coupled rows the cell actually draws,
> `floor(W/0.89)`. The earlier model subtracted one row, describing a structure that
> ends in single fingers with no counter electrode; this cell has none, so the
> subtraction did not describe it and every size was under-counted by one row. That
> correction is geometric and needs no field solver.
>
> The `same` column moved a second time. The single-side feed term is no longer the
> earlier `cfeed_per_um * feed_width`, which describes a via-tied fan-in this cell
> does not draw, but `0.1625 * pad_len + 0.0916` fF fitted on the drawn pads from an
> electrostatic field solve. The `double` column also moved: it now carries the
> opposite-side feed `0.152 * pad_len` (+3.6% at w=l=5, cmos5l N=4).
>
> The densities are unchanged and remain the transferred, uncalibrated values this
> campaign is meant to measure.

"""


def main(path):
    shutil.copy(path, path + ".bak")
    src = open(path).read()
    # Idempotent: drop any note this script (or an earlier version of it) left
    # behind before writing the current one, so re-running does not stack them.
    src = re.sub(r"\n?> \*\*(Model corrections|Row-count correction)[^\n]*\n(> [^\n]*\n|>\n)*",
                 "", src)
    out, done_note = [], False
    for line in src.splitlines(keepends=True):
        if not done_note and line.startswith("## Configurations"):
            out.append(NOTE)
            done_note = True
        out.append(fix_row(line) if line.lstrip().startswith("|") else line)
    open(path, "w").write("".join(out))
    print(f"{path} rewritten ({path}.bak kept)")


if __name__ == "__main__":
    main(sys.argv[1])
