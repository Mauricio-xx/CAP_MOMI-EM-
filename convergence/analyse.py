"""Mesh-convergence analysis for the cap_cmomi Palace runs.

Fits C(h) = Cinf + a*h^p to each mesh sequence, then rebuilds the per-column
capacitance by the delta-length method at matched mesh density.
"""
UC_X, UC_Y = 0.84, 0.89
CELL = UC_X * UC_Y
DENS = 1.09


def fit3(hs, cs):
    h1, h2, h3 = hs
    c1, c2, c3 = cs
    tgt = (c1 - c2) / (c2 - c3)
    lo, hi = 0.05, 8.0
    for _ in range(300):
        p = 0.5 * (lo + hi)
        f = (h1**p - h2**p) / (h2**p - h3**p)
        if f < tgt:
            lo = p
        else:
            hi = p
    p = 0.5 * (lo + hi)
    a = (c2 - c3) / (h2**p - h3**p)
    return p, c3 - a * h3**p


def fit2(hs, cs, p):
    """Two points, convergence rate assumed from a well-resolved case."""
    (h1, h2), (c1, c2) = hs, cs
    a = (c1 - c2) / (h1**p - h2**p)
    return c2 - a * h2**p


SEQ = {
    # name: (mesh sizes coarse->fine, C12 fF)
    "5.5x7  N=4": ([0.12, 0.08, 0.06], [30.5377, 30.0212, 29.8324]),
    "2x2    N=4": ([0.080, 0.050, 0.035], [3.1382, 3.1045, 3.0915]),
    "20x2   N=4": ([0.100, 0.070, 0.050], [32.4214, 32.0951, 31.8452]),
    "50x2   N=4": ([0.120, 0.100, 0.070], [83.5932, 82.5953, 81.7551]),
}

print("Mesh convergence, C(h) = Cinf + a*h^p")
print(f"{'case':<12}{'meshes':>22}{'p':>7}{'C_finest':>11}{'C_inf':>9}{'left%':>7}")
res = {}
for k, (hs, cs) in SEQ.items():
    p, cinf = fit3(hs, cs)
    res[k] = cinf
    print(f"{k:<12}{'/'.join(f'{h:g}' for h in hs):>22}{p:>7.2f}{cs[-1]:>11.3f}{cinf:>9.3f}"
          f"{100*(cs[-1]-cinf)/cinf:>7.1f}")

# the 20x2 and 50x2 sequences have their coarsest point outside the asymptotic
# range, which distorts the three-point rate. Re-extrapolate the two finest with
# the rate measured on the well-resolved 5.5x7 case.
P_REF = fit3(*SEQ["5.5x7  N=4"])[0]
print(f"\nreference convergence rate p = {P_REF:.2f} (from the fully resolved 5.5x7 triple)")
alt = {
    "20x2   N=4": fit2([0.070, 0.050], [32.0951, 31.8452], P_REF),
    "50x2   N=4": fit2([0.100, 0.070], [82.5953, 81.7551], P_REF),
    "2x2    N=4": fit2([0.050, 0.035], [3.1045, 3.0915], P_REF),
}
for k, v in alt.items():
    print(f"  {k}: C_inf = {v:.3f} fF   (three-point fit gave {res[k]:.3f})")

print("\nModel vs Palace, using the p-consistent extrapolation")
print(f"{'l x w':<10}{'nx':>4}{'ny':>4}{'model fF':>10}{'Palace fF':>11}{'ratio':>8}")
CASES = [("2 x 2", 2, 1, alt["2x2    N=4"]),
         ("20 x 2", 23, 1, alt["20x2   N=4"]),
         ("50 x 2", 59, 1, alt["50x2   N=4"]),
         ("5.5 x 7", 6, 6, res["5.5x7  N=4"])]
for name, nx, ny, cp in CASES:
    m = DENS * nx * ny * CELL
    print(f"{name:<10}{nx:>4}{ny:>4}{m:>10.3f}{cp:>11.3f}{cp/m:>8.3f}")

print("\nDelta-length, per column, at MATCHED mesh density")
print("(cancels the end structures and most of the mesh bias)")
pairs = [
    ("w=2  lc 0.10", 0.10, 82.5953, 32.4214, 59, 23, 1),
    ("w=2  lc 0.07", 0.07, 81.7551, 32.0951, 59, 23, 1),
    ("w=7  lc 0.12", 0.12, 55.2795, 30.5377, 11, 6, 6),
    ("w=7  lc 0.08", 0.08, 54.3234, 30.0212, 11, 6, 6),
]
per = {}
for name, h, clong, cshort, nlong, nshort, ny in pairs:
    pc = (clong - cshort) / (nlong - nshort)
    dens = pc / (ny * CELL)
    per.setdefault(ny, []).append((h, pc))
    print(f"  {name}: {pc:8.4f} fF/col   effective density {dens:6.4f} fF/um2")

print("\n  extrapolated to h -> 0 with p = %.2f:" % P_REF)
conv = {}
for ny, pts in per.items():
    pts.sort(reverse=True)
    (h1, c1), (h2, c2) = pts
    cinf = fit2([h1, h2], [c1, c2], P_REF)
    conv[ny] = cinf
    print(f"    ny={ny:<3} {cinf:8.4f} fF/col   effective density {cinf/(ny*CELL):6.4f} fF/um2"
          f"   vs model {DENS}  ->  {cinf/(ny*CELL)/DENS:.3f}x")

A = (conv[6] - conv[1]) / ((6 - 1) * CELL)
B = conv[1] - A * CELL
print(f"\nBilinear law from the two converged widths:")
print(f"  C_per_column = {A:.4f} * (ny * {CELL:.4f}) + {B:.4f}")
print(f"  i.e.  C = {A:.4f} * active_area + {B:.4f} * nx  (+ a small end term)")
print(f"\nEffective density the shipped constant 1.09 should have been:")
for ny, w in ((1, 2), (2, 3), (6, 7), (15, 15)):
    d = (A * ny * CELL + B) / (ny * CELL)
    print(f"  ny={ny:<3} (w~{w:>2} um): {d:6.4f} fF/um2   model/actual = {DENS/d:.3f}")
