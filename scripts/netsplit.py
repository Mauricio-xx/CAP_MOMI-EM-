"""Split a cap_cmomi GDS into per-net, per-layer polygon sets."""
import klayout.db as db

# name -> (gds layer, datatype, zmin, zmax)  from the PDK stackup
STACK = {
    "Metal1": (8, 0, 1.0400, 1.4600),
    "Via1":   (19, 0, 1.4600, 2.0000),
    "Metal2": (10, 0, 2.0000, 2.4900),
    "Via2":   (29, 0, 2.4900, 3.0300),
    "Metal3": (30, 0, 3.0300, 3.5200),
    "Via3":   (49, 0, 3.5200, 4.0600),
    "Metal4": (50, 0, 4.0600, 4.5500),
}
ORDER = ["Metal1", "Via1", "Metal2", "Via2", "Metal3", "Via3", "Metal4"]


def extract_nets(gds):
    ly = db.Layout(); ly.read(gds); top = ly.top_cell()
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
    l2n.include_floating_subcircuits = True
    regions = {}
    for nm in ORDER:
        lnum, dt, _, _ = STACK[nm]
        li = ly.layer(lnum, dt)
        r = l2n.make_polygon_layer(li, nm)
        regions[nm] = r
    # connectivity: metal - via - metal up the stack
    for i in range(0, len(ORDER) - 1):
        l2n.connect(regions[ORDER[i]], regions[ORDER[i + 1]])
    for nm in ORDER:
        l2n.connect(regions[nm])
    l2n.extract_netlist()

    nets = []
    circuit = l2n.netlist().circuit_by_name(top.name) or list(l2n.netlist().each_circuit())[0]
    for net in circuit.each_net():
        per_layer = {}
        total = 0.0
        for nm in ORDER:
            reg = l2n.shapes_of_net(net, regions[nm], True)
            if reg is None:
                continue
            polys = [p for p in reg.each()]
            if polys:
                per_layer[nm] = polys
                total += sum(p.area() for p in polys) * ly.dbu * ly.dbu
        if per_layer:
            nets.append((net.expanded_name(), total, per_layer))
    nets.sort(key=lambda t: -t[1])
    return ly, nets


if __name__ == "__main__":
    import sys
    for gds in sys.argv[1:]:
        ly, nets = extract_nets(gds)
        print(f"\n{gds}: {len(nets)} nets with geometry")
        for nm, area, per_layer in nets[:6]:
            desc = " ".join(f"{k}={len(v)}" for k, v in per_layer.items())
            print(f"   net {nm:>6}  metal+via area {area:8.3f} um2   {desc}")
