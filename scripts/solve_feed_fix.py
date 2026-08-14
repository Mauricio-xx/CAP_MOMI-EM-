#!/usr/bin/env python3
"""Feed campaign on the via-FIXED cell (branch rowfix+viafix PCell).

Re-measure the two feed terms on the corrected layout, since the via fix
removed the sparse-via density deficit that the feed decomposition leaned on:
  * single-side feed  Cfeed_same = C(feed=same) - C(feed=none)   -> refit vs
    pad_len = ny*UC_Y + 2*T_BAR against the model CFEED_SLOPE/CFEED_END.
  * opposite-side feed residual  C(feed=double) - C(feed=none)   -> currently
    dropped to 0 in the model; decide add vs keep-zero.

Electrostatic (robust flow). Each width solves its three feeds in the SAME
outer domain so the feed delta is not contaminated by the boundary. lc/z match
the original feed fit (feed_sweep.sh: lc=0.10, z_hi=10.0).

Writes palace/feed_fix/feed_fix.csv
"""
import os, sys, csv, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_model as B

ROOT = "/home/montanares/git/slim-pdk/issue92_em"
GDS = "/tmp/claude-30044/-home-montanares-git-slim-pdk-issue92-em/0db4471c-c8fa-4ac0-b598-9524aad92b53/scratchpad/feedfix/gds"
RUN = f"{ROOT}/palace/feed_fix"
SIF = os.path.expanduser("~/palace.sif")
NP = 8
LC = 0.10
Z_HI = 10.0
MARGIN = 5.0
UC_Y = 0.89
T_BAR = 0.21

WIDTHS = [5, 7, 10, 15]
FEEDS = ["none", "same", "dbl"]


def common_domain(jsons):
    xs, ys = [], []
    for p in jsons:
        d = json.load(open(p))
        for e in d["nets"]:
            for polys in e["layers"].values():
                for poly in polys:
                    xs += [x for x, _ in poly]; ys += [y for _, y in poly]
    return [round(min(xs) - MARGIN, 6), round(min(ys) - MARGIN, 6),
            round(max(xs) + MARGIN, 6), round(max(ys) + MARGIN, 6)]


def c12(prefix):
    rows = list(csv.reader(open(f"{RUN}/{prefix}_out/terminal-C.csv")))
    body = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return -float(body[0][2]) * 1e15


def solve(prefix, domain):
    j = f"{GDS}/{prefix}.json"
    pre = f"{RUN}/{prefix}"
    if not os.path.exists(f"{pre}_out/terminal-C.csv"):
        B.build(j, pre, lc_fine=LC, z_hi=Z_HI, domain=domain)
        r = subprocess.run(["apptainer", "exec", SIF, "palace", "-np", str(NP),
                            f"{prefix}.json"], cwd=RUN, capture_output=True, text=True)
        if r.returncode != 0 or "MPI_Abort" in r.stdout:
            print(f"[SOLVE FAIL] {prefix}\n{r.stdout[-1500:]}", flush=True)
            return None
    C = c12(prefix)
    try: os.remove(f"{pre}.msh")
    except OSError: pass
    return C


def main():
    os.makedirs(RUN, exist_ok=True)
    res = {}
    for w in WIDTHS:
        pres = [f"fd_l5p5_w{w}_{fe}" for fe in FEEDS]
        dom = common_domain([f"{GDS}/{p}.json" for p in pres])
        ny = int(w / UC_Y + 1e-6)
        pad_len = ny * UC_Y + 2 * T_BAR
        print(f"=== w{w}  ny={ny}  pad_len={pad_len:.4f}  domain {dom}", flush=True)
        for p in pres:
            C = solve(p, dom)
            res[p] = C
            print(f"[w{w}] {p:24s} C12 = {C} fF", flush=True)
        cn, cs, cd = (res[pres[0]], res[pres[1]], res[pres[2]])
        if None not in (cn, cs, cd):
            print(f"[w{w}] Cfeed_same = C(same)-C(none) = {cs-cn:+.4f} fF   "
                  f"(model {0.1625*pad_len+0.0916:.4f})", flush=True)
            print(f"[w{w}] resid_dbl  = C(dbl)-C(none)  = {cd-cn:+.4f} fF   "
                  f"(model 0)", flush=True)

    with open(f"{RUN}/feed_fix.csv", "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["width", "ny", "pad_len", "feed", "C12_fF"])
        for w in WIDTHS:
            ny = int(w / UC_Y + 1e-6); pad_len = ny * UC_Y + 2 * T_BAR
            for fe in FEEDS:
                v = res[f"fd_l5p5_w{w}_{fe}"]
                wtr.writerow([w, ny, f"{pad_len:.4f}", fe,
                              f"{v:.4f}" if v is not None else "FAIL"])
    print("FEED FIX DONE", flush=True)


if __name__ == "__main__":
    main()
