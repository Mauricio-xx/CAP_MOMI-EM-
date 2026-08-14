import os, json
import pya
cfg = json.loads(os.environ["CFG"])
layout = pya.Layout()
layout.technology_name = "sg13cmos5l"
cell = layout.create_cell("cap_cmomi", "SG13_dev", cfg["params"])
if cell is None:
    raise SystemExit("cap_cmomi PCell not found in SG13_dev")
top = layout.create_cell(cfg["name"])
top.insert(pya.DCellInstArray(cell, pya.DTrans()))
top.flatten(-1, True)
layout.write(cfg["out"])
print("WROTE", cfg["out"])
