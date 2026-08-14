#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import gdstk
except ModuleNotFoundError as exc:
    raise SystemExit("This script requires the 'gdstk' package") from exc


METAL1 = (8, 0)
METAL4 = (50, 0)
PORT_LEFT = (201, 0)
PORT_RIGHT = (202, 0)
M1_CLEARANCE_UM = 1.0


def bbox_area(bbox):
    (xmin, ymin), (xmax, ymax) = bbox
    return (xmax - xmin) * (ymax - ymin)


def polygon_bbox(polygon):
    xs = polygon.points[:, 0]
    ys = polygon.points[:, 1]
    return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))


def rect_size(bbox):
    xmin, ymin, xmax, ymax = bbox
    return xmax - xmin, ymax - ymin


def rect_center(bbox):
    xmin, ymin, xmax, ymax = bbox
    return ((xmin + xmax) / 2, (ymin + ymax) / 2)


def load_caps_list(caps_path: Path):
    lines = [line.strip() for line in caps_path.read_text(encoding="ascii").splitlines()]
    entries = [line for line in lines if line and not line.startswith("#")]
    if len(entries) < 2:
        raise ValueError(f"{caps_path} must contain a source directory followed by GDS file names")

    source_dir = (caps_path.parent / entries[0]).resolve()
    cap_paths = [source_dir / entry for entry in entries[1:]]
    return source_dir, cap_paths


def load_caps_dirs(caps_dirs):
    cap_paths = []
    for caps_dir in caps_dirs:
        caps_dir = Path(caps_dir).resolve()
        if not caps_dir.is_dir():
            raise ValueError(f"Capacitor directory not found: {caps_dir}")
        cap_paths.extend(sorted(caps_dir.glob("*.gds")))

    if not cap_paths:
        raise ValueError("No capacitor GDS files found in the requested directories")

    return cap_paths


def pick_template_cells(base_lib: gdstk.Library):
    top_cells = list(base_lib.top_level())
    if len(top_cells) < 2:
        raise ValueError("Base GDS must contain the testbench top cell and one capacitor top cell")

    top_cells.sort(key=lambda cell: bbox_area(cell.bounding_box()), reverse=True)
    return top_cells[0], top_cells[1]


def layer_rectangles(cell: gdstk.Cell, spec):
    rects = []
    for polygon in cell.polygons:
        if (polygon.layer, polygon.datatype) != spec:
            continue
        rects.append(polygon_bbox(polygon))
    return rects


def extract_template(base_path: Path):
    base_lib = gdstk.read_gds(base_path)
    tb_cell, cap_cell = pick_template_cells(base_lib)

    cap_bbox = cap_cell.bounding_box()
    (cap_xmin, cap_ymin), (cap_xmax, cap_ymax) = cap_bbox
    cap_cx = (cap_xmin + cap_xmax) / 2
    cap_cy = (cap_ymin + cap_ymax) / 2
    base_cap_left = cap_xmin - cap_cx
    base_cap_right = cap_xmax - cap_cx
    base_cap_bottom = cap_ymin - cap_cy
    base_cap_top = cap_ymax - cap_cy

    feed_rects = sorted(layer_rectangles(tb_cell, METAL4), key=lambda bbox: rect_center(bbox)[0])
    left_port = layer_rectangles(tb_cell, PORT_LEFT)
    right_port = layer_rectangles(tb_cell, PORT_RIGHT)

    if len(feed_rects) != 2 or len(left_port) != 1 or len(right_port) != 1:
        raise ValueError("Base GDS must contain 2 Metal4 feed rectangles and 1 polygon on each RF port layer")

    left_feed, right_feed = feed_rects
    left_port = left_port[0]
    right_port = right_port[0]

    outer_bbox = tb_cell.bounding_box()
    (outer_xmin, outer_ymin), (outer_xmax, outer_ymax) = outer_bbox

    left_port_width = rect_size(left_port)[0]
    right_port_width = rect_size(right_port)[0]

    return {
        "unit": base_lib.unit,
        "precision": base_lib.precision,
        "feed_ymin": left_feed[1],
        "feed_ymax": left_feed[3],
        "left_feed_length": base_cap_left - left_feed[0],
        "right_feed_length": right_feed[2] - base_cap_right,
        "left_feed_inner_offset": left_feed[2] - base_cap_left,
        "right_feed_inner_offset": right_feed[0] - base_cap_right,
        "left_port_width": left_port_width,
        "right_port_width": right_port_width,
        "left_port_inset": left_port[0] - left_feed[0],
        "right_port_inset": right_feed[2] - right_port[2],
        "outer_left_margin": base_cap_left - outer_xmin,
        "outer_right_margin": outer_xmax - base_cap_right,
        "outer_bottom_margin": base_cap_bottom - outer_ymin,
        "outer_top_margin": outer_ymax - base_cap_top,
    }


def build_testbench(template, cap_path: Path, output_dir: Path):
    cap_lib = gdstk.read_gds(cap_path)
    cap_top = list(cap_lib.top_level())
    if not cap_top:
        raise ValueError(f"No top cell found in {cap_path}")

    cap_cell = cap_top[0]
    (cap_xmin, cap_ymin), (cap_xmax, cap_ymax) = cap_cell.bounding_box()
    cap_cx = (cap_xmin + cap_xmax) / 2
    cap_cy = (cap_ymin + cap_ymax) / 2
    cap_left = cap_xmin - cap_cx
    cap_right = cap_xmax - cap_cx
    cap_bottom = cap_ymin - cap_cy
    cap_top_y = cap_ymax - cap_cy

    stem = cap_path.stem
    top_name = f"{stem}_rf_tb.gds"
    output_path = output_dir / top_name

    out_lib = gdstk.Library(unit=template["unit"], precision=template["precision"])
    out_lib.add(*cap_lib.cells)

    top_cell = out_lib.new_cell(top_name)
    top_cell.add(gdstk.Reference(cap_cell, origin=(-cap_cx, -cap_cy)))

    feed_ymin = template["feed_ymin"]
    feed_ymax = template["feed_ymax"]

    left_feed_xmin = cap_left - template["left_feed_length"]
    left_feed_xmax = cap_left + template["left_feed_inner_offset"]
    right_feed_xmin = cap_right + template["right_feed_inner_offset"]
    right_feed_xmax = cap_right + template["right_feed_length"]

    top_cell.add(gdstk.rectangle((left_feed_xmin, feed_ymin), (left_feed_xmax, feed_ymax), layer=METAL4[0], datatype=METAL4[1]))
    top_cell.add(gdstk.rectangle((right_feed_xmin, feed_ymin), (right_feed_xmax, feed_ymax), layer=METAL4[0], datatype=METAL4[1]))

    left_port_xmin = left_feed_xmin + template["left_port_inset"]
    left_port_xmax = left_port_xmin + template["left_port_width"]
    right_port_xmax = right_feed_xmax - template["right_port_inset"]
    right_port_xmin = right_port_xmax - template["right_port_width"]

    top_cell.add(gdstk.rectangle((left_port_xmin, feed_ymin), (left_port_xmax, feed_ymax), layer=PORT_LEFT[0], datatype=PORT_LEFT[1]))
    top_cell.add(gdstk.rectangle((right_port_xmin, feed_ymin), (right_port_xmax, feed_ymax), layer=PORT_RIGHT[0], datatype=PORT_RIGHT[1]))

    outer_xmin = cap_left - template["outer_left_margin"]
    outer_xmax = cap_right + template["outer_right_margin"]
    outer_ymin = cap_bottom - template["outer_bottom_margin"]
    outer_ymax = cap_top_y + template["outer_top_margin"]
    inner_xmin = cap_left - M1_CLEARANCE_UM
    inner_xmax = cap_right + M1_CLEARANCE_UM
    inner_ymin = cap_bottom - M1_CLEARANCE_UM
    inner_ymax = cap_top_y + M1_CLEARANCE_UM

    m1_ring = gdstk.boolean(
        [gdstk.rectangle((outer_xmin, outer_ymin), (outer_xmax, outer_ymax))],
        [gdstk.rectangle((inner_xmin, inner_ymin), (inner_xmax, inner_ymax))],
        "not",
        precision=template["precision"],
        layer=METAL1[0],
        datatype=METAL1[1],
    )
    if not m1_ring:
        raise ValueError(f"Failed to build Metal1 surround for {cap_path}")
    top_cell.add(*m1_ring)

    out_lib.write_gds(output_path)
    return output_path, top_name


def main():
    parser = argparse.ArgumentParser(description="Build RF capacitor testbench GDS files from caps.txt")
    parser.add_argument("--base-gds", default="TE_10.gds", help="Base RF testbench GDS used as geometry template")
    parser.add_argument("--caps-file", default="caps.txt", help="List of capacitor GDS files to wrap")
    parser.add_argument(
        "--caps-dir",
        action="append",
        help="Capacitor directory to wrap directly; may be given multiple times instead of --caps-file",
    )
    parser.add_argument("--output-dir", default=".", help="Directory for generated *_rf_tb.gds files")
    args = parser.parse_args()

    base_path = Path(args.base_gds).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not base_path.exists():
        raise SystemExit(f"Base GDS not found: {base_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.caps_dir:
        cap_paths = load_caps_dirs(args.caps_dir)
    else:
        caps_path = Path(args.caps_file).resolve()
        if not caps_path.exists():
            raise SystemExit(f"Caps list not found: {caps_path}")
        _, cap_paths = load_caps_list(caps_path)

    template = extract_template(base_path)

    for cap_path in cap_paths:
        if not cap_path.exists():
            raise SystemExit(f"Capacitor GDS not found: {cap_path}")
        output_path, top_name = build_testbench(template, cap_path, output_dir)
        print(f"Wrote {output_path} (top cell {top_name})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
