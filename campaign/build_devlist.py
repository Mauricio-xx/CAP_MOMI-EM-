#!/usr/bin/env python3
"""Build the canonical campaign device manifest from the fab summaries.

Reads the fabricated-device inventories and emits campaign/devices.json with,
per device, the cap_cmomi pcell params needed to regenerate it with the fixed
pcell, plus campaign bookkeeping (group/N/feed/wl, starter flag).

Full-stack devices  <- cap_mom_characterization/_summary.json        (56, M1-M4)
Reduced-stack       <- cap_mom_characterization/_summary_metal.json   (32)
"""
import json
from pathlib import Path

FAB = Path("/home/montanares/git/slim-pdk/cap_mom_characterization")
OUT = Path(__file__).resolve().parent / "devices.json"

# Starter batch: full-stack square sizes (um) that mesh under the RAM floor.
STARTER_WL = [2.0, 4.9, 7.8, 10.7, 13.6]


def params_for(w_l_um, mmin, mmax, feed):
    return {
        "w": f"{w_l_um}u",
        "l": f"{w_l_um}u",
        "mmin": int(mmin),
        "mmax": int(mmax),
        "feed": feed,
        "subblock": 0,
    }


def main():
    devices = []

    full = json.loads((FAB / "_summary.json").read_text())
    for d in full:
        wl = d["wl"]
        devices.append({
            "name": d["cell"],
            "file": d["file"],
            "fab_gds": str(FAB / "gds" / d["file"]),
            "group": "full",
            "mmin": 1, "mmax": 4, "N": 4,
            "feed": d["feed"],
            "wl": wl,
            "params": params_for(wl, 1, 4, d["feed"]),
            "starter": (wl in STARTER_WL),
        })

    red = json.loads((FAB / "_summary_metal.json").read_text())
    for d in red:
        wl = d["wl"]
        devices.append({
            "name": d["cell"],
            "file": d["file"],
            "fab_gds": str(FAB / "gds" / d["file"]),
            "group": d["group"],
            "mmin": d["mmin"], "mmax": d["mmax"], "N": d["N"],
            "feed": d["feed"],
            "wl": wl,
            "params": params_for(wl, d["mmin"], d["mmax"], d["feed"]),
            "starter": False,  # reduced-stack fab cells are all 65-80um (not meshable)
        })

    OUT.write_text(json.dumps(devices, indent=2))
    n_full = sum(1 for d in devices if d["group"] == "full")
    n_red = len(devices) - n_full
    n_start = sum(1 for d in devices if d["starter"])
    print(f"wrote {OUT}: {len(devices)} devices ({n_full} full-stack, {n_red} reduced), "
          f"{n_start} starter")
    for d in devices:
        if d["starter"]:
            print(f"  starter: {d['name']:28} feed={d['feed']:6} wl={d['wl']}")


if __name__ == "__main__":
    main()
