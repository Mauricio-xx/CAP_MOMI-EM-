#!/usr/bin/env python3
"""Behavioural diff of two cap_cmomi OSDI objects.

The PDK ships a checked-in libs.tech/ngspice/osdi/cap_cmomi.osdi.  Nothing in
CI rebuilds it, so before touching the Verilog-A we have to know that the
binary in the tree still corresponds to the source in the tree.  A byte
compare is useless (the build embeds the output path), so compare behaviour:
run the same grid of geometries through both objects in one batched ngspice AC
sweep each and diff the extracted low-frequency capacitance.

Usage:  osdi_compare.py <osdi_a> <osdi_b> [--tol-ppm N]
"""
import argparse, math, os, re, subprocess, sys, tempfile

FMEAS = 1e6          # low enough that L and R are negligible against 1/(wC)
TWO_PI = 2.0 * math.pi


def cases():
    """(l, w, mmin, mmax, feed).  feed 0=none 1=same 2=double."""
    out = []
    for mmin, mmax in [(3, 4), (2, 4), (1, 4), (1, 3), (1, 2)]:
        for l, w in [(2e-6, 2e-6), (5e-6, 5e-6), (5.5e-6, 7e-6),
                     (10e-6, 7e-6), (10e-6, 70e-6), (15e-6, 15e-6),
                     # knife edges: exact pitch multiples of 0.84 / 0.89
                     (21e-6, 8.9e-6), (3.36e-6, 6.23e-6), (42e-6, 3.56e-6),
                     # sub-minimum widths the .va accepts and the clamp touches
                     (5e-6, 1.5e-6), (5e-6, 0.8e-6)]:
            for feed in (0, 1, 2):
                out.append((l, w, mmin, mmax, feed))
    return out


def run(osdi, cs):
    lines = ["* cap_cmomi OSDI behavioural grid", ".model cmom cap_cmomi"]
    for i, (l, w, mmin, mmax, feed) in enumerate(cs):
        lines.append(f"N{i} p{i} 0 0 cmom w={w} l={l} mmin={mmin} "
                     f"mmax={mmax} feed={feed}")
        lines.append(f"V{i} p{i} 0 dc 0 ac 1")
    lines.append(".end")
    tb = os.path.join(tempfile.gettempdir(), "tb_cmomi_grid.sp")
    with open(tb, "w") as f:
        f.write("\n".join(lines) + "\n")

    cmds = [f"osdi {osdi}", f"source {tb}", f"ac lin 1 {FMEAS} {FMEAS}"]
    for i in range(len(cs)):
        cmds.append(f"let c{i} = -imag(v{i}#branch)/({TWO_PI}*{FMEAS})*1e15")
        cmds.append(f"print c{i}")
    cmds.append("quit")
    p = subprocess.run(["ngspice", "-p"], input="\n".join(cmds) + "\n",
                       capture_output=True, text=True, timeout=300)
    vals = {}
    for ln in p.stdout.splitlines():
        m = re.match(r"\s*c(\d+)\s*=\s*([-\d.eE+]+)", ln)
        if m:
            vals[int(m.group(1))] = float(m.group(2))
    if len(vals) != len(cs):
        sys.stderr.write(p.stdout[-3000:] + "\n" + p.stderr[-2000:] + "\n")
        raise SystemExit(f"{osdi}: got {len(vals)}/{len(cs)} points")
    return [vals[i] for i in range(len(cs))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("osdi_a")
    ap.add_argument("osdi_b")
    ap.add_argument("--tol-ppm", type=float, default=1.0)
    a = ap.parse_args()

    cs = cases()
    va, vb = run(a.osdi_a, cs), run(a.osdi_b, cs)

    worst, worst_case = 0.0, None
    for c, x, y in zip(cs, va, vb):
        d = abs(x - y) / max(abs(x), 1e-30) * 1e6
        if d > worst:
            worst, worst_case = d, (c, x, y)
    print(f"{len(cs)} points, worst deviation {worst:.4g} ppm")
    if worst_case and worst > a.tol_ppm:
        (l, w, mmin, mmax, feed), x, y = worst_case
        print(f"  at l={l*1e6}u w={w*1e6}u m{mmin}..{mmax} feed={feed}: "
              f"{x:.6f} vs {y:.6f} fF")
    ok = worst <= a.tol_ppm
    print("MATCH" if ok else "DIFFER")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
