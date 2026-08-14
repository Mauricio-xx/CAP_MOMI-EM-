"""Archive a reproducible record of the Palace runs behind the feed measurement.

A reviewer should be able to redo any run without this machine. What they need is
the input geometry (already tracked under gds/), the exact solver configuration,
the exact mesh parameters, and the raw capacitance matrix that came out.  The
mesh itself is deliberately not archived: it is large, and build_model.py
regenerates it deterministically from the tracked net JSON and the parameters
recorded here.

Usage:  collect_palace.py <run_dir> <out_dir> [tag_prefix ...]
"""
import csv
import json
import os
import re
import shutil
import sys


MARGIN_XY = 5.0          # feed_sweep.sh domain_of()
LC_FAR = 2.0             # build_model.py defaults, not overridden by the driver
DIST_MIN, DIST_MAX = 0.2, 4.0


def input_of(tag, gds_dir):
    """The net JSON this run was built from.

    The tag is not always the input's base name: the first width round wrote
    fd_w<W>_* while reading gds/fd_l5p5_w<W>_*.json, and the N=4 layer window is
    the w=7 width case reused rather than a separate fdn_m14 run.
    """
    base = re.sub(r"_lc\d+p\d+$", "", tag)
    m = re.match(r"fd_w(\d+)_(dbl|same|none)$", base)
    if m:
        base = f"fd_l5p5_w{m.group(1)}_{m.group(2)}"
    path = os.path.join(gds_dir, base + ".json")
    return path if os.path.isfile(path) else None


def domain_of(paths):
    """The outer box the driver handed gmsh: union bbox of the pair, plus margin.

    Every geometry that gets differenced against another is solved in the SAME
    box, so the box belongs to the pair, not to the run.  It is not recorded
    anywhere by gmsh or by Palace, so it is recomputed here from the inputs the
    same way feed_sweep.sh computes it.
    """
    xs, ys = [], []
    for p in paths:
        d = json.load(open(p))
        for e in d["nets"]:
            for polys in e["layers"].values():
                for poly in polys:
                    xs += [x for x, _ in poly]
                    ys += [y for _, y in poly]
    return [round(min(xs) - MARGIN_XY, 6), round(min(ys) - MARGIN_XY, 6),
            round(max(xs) + MARGIN_XY, 6), round(max(ys) + MARGIN_XY, 6)]


def pair_of(tag, gds_dir):
    """The dbl/same pair whose union bbox set this run's domain."""
    base = re.sub(r"_(dbl|same|none)_lc\d+p\d+$", "", tag)
    base = re.sub(r"^fd_w(\d+)$", r"fd_l5p5_w\1", base)
    out = []
    for variant in ("dbl", "same"):
        p = os.path.join(gds_dir, f"{base}_{variant}.json")
        if not os.path.isfile(p):
            return None
        out.append(p)
    return out


def mesh_params(build_log):
    """Recover the element count recorded in the build log."""
    if not os.path.isfile(build_log):
        return {}
    txt = open(build_log, errors="replace").read()
    m = re.search(r"tets=(\d+)", txt)
    return {"tets": int(m.group(1))} if m else {}


def matrix(csv_path):
    rows = list(csv.reader(open(csv_path)))
    hdr = [c.strip() for c in rows[0]]
    body = [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]
    return {"header": hdr, "rows": body,
            "C12_fF": -float(body[0][2]) * 1e15}


def main(run_dir, out_dir, prefixes):
    os.makedirs(os.path.join(out_dir, "configs"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "results"), exist_ok=True)
    gds_dir = os.path.join(os.path.dirname(os.path.abspath(out_dir)), "gds")
    index = []
    for name in sorted(os.listdir(run_dir)):
        if not name.endswith(".json"):
            continue
        tag = name[:-5]
        if prefixes and not any(tag.startswith(p) for p in prefixes):
            continue
        cfg_src = os.path.join(run_dir, name)
        res_src = os.path.join(run_dir, tag + "_out", "terminal-C.csv")
        if not os.path.isfile(res_src):
            continue

        cfg = json.load(open(cfg_src))
        # the absolute scratch paths are noise for a reviewer
        cfg["Problem"]["Output"] = f"{tag}_out"
        cfg["Model"]["Mesh"] = f"{tag}.msh"
        with open(os.path.join(out_dir, "configs", name), "w") as f:
            json.dump(cfg, f, indent=1)
        shutil.copy(res_src, os.path.join(out_dir, "results", tag + ".terminal-C.csv"))

        entry = {"tag": tag, "config": f"configs/{name}",
                 "result": f"results/{tag}.terminal-C.csv"}
        inp = input_of(tag, gds_dir)
        entry["input"] = os.path.relpath(inp, os.path.dirname(out_dir)) if inp else None
        pair = pair_of(tag, gds_dir)
        entry["domain_um"] = domain_of(pair) if pair else None
        m = re.search(r"_lc(\d+p\d+)$", tag)
        if m:
            entry["lc_fine"] = float(m.group(1).replace("p", "."))
        entry["lc_far"] = LC_FAR
        entry["dist_um"] = [DIST_MIN, DIST_MAX]
        entry["z_um"] = [-1.0, 10.0]
        entry["eps_r"] = 4.1
        entry.update(mesh_params(os.path.join(run_dir, tag + ".build.log")))
        entry["C12_fF"] = round(matrix(res_src)["C12_fF"], 4)
        index.append(entry)

    with open(os.path.join(out_dir, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    print(f"{len(index)} runs archived under {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
