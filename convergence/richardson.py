"""Fit C(h) = Cinf + a*h^p to three mesh points and report the extrapolated value."""
import sys
from math import log, exp


def fit(hs, cs):
    h1, h2, h3 = hs
    c1, c2, c3 = cs
    tgt = (c1 - c2) / (c2 - c3)
    lo, hi = 0.05, 6.0
    for _ in range(200):
        p = 0.5 * (lo + hi)
        f = (h1**p - h2**p) / (h2**p - h3**p)
        if f < tgt:
            lo = p
        else:
            hi = p
    p = 0.5 * (lo + hi)
    a = (c2 - c3) / (h2**p - h3**p)
    cinf = c3 - a * h3**p
    return p, a, cinf


CASES = {
    # name: (mesh sizes, C12 in fF), coarsest first
}

if __name__ == "__main__":
    import json
    cases = json.load(open(sys.argv[1]))
    print(f"{'case':<16}{'p':>7}{'C(finest)':>12}{'C_inf':>10}{'resid%':>9}")
    for name, (hs, cs) in cases.items():
        if len(hs) < 3:
            print(f"{name:<16}{'--':>7}{cs[-1]:>12.3f}{'--':>10}{'--':>9}")
            continue
        p, a, cinf = fit(hs, cs)
        resid = 100.0 * (cs[-1] - cinf) / cinf
        print(f"{name:<16}{p:>7.2f}{cs[-1]:>12.3f}{cinf:>10.3f}{resid:>9.1f}")
