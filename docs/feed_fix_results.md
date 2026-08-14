# Feed campaign on the via-fixed cell

Electrostatic Palace (robust flow), N=4 (M1..M4), l=5.5 um, widths {5,7,10,15},
feeds {none, same, double}. Each width solves its three feeds in one common
outer domain (lc=0.10, z_hi=10.0), so the feed delta is boundary-clean. Cells
generated from the branch PCell (row-count + via fix). Data:
`palace/feed_fix/feed_fix.csv`, figure `fig/feed_fix.png`.

## Measured C12 (fF)

| w | ny | pad_len | none | same | double |
|---|----|---------|------|------|--------|
| 5 | 5 | 4.87 | 24.124 | 25.015 | 24.851 |
| 7 | 7 | 6.65 | 33.807 | 34.990 | 34.802 |
| 10 | 11 | 10.21 | 53.176 | 54.941 | 54.696 |
| 15 | 16 | 14.66 | 77.381 | 79.874 | 79.643 |

## Single-side feed: model validated

`C(same) - C(none)` vs `pad_len` fits slope 0.1636, intercept 0.0945, against the
model's CFEED_SLOPE=0.1625 / CFEED_END=0.0916. Agreement within ~1% at every
width. The via fix (tip via in the core) is common to same/none and cancels in
the difference, as expected. No change to CFEED.

## Double feed: real residual, previously dropped

The model billed feed=double as `c_active` only (no feed term), justified by an
"the two errors cancel" argument. That is false: `C(double) - C(none)` is a real,
systematic residual, ~0.152·pad_len (through-origin, intercept ~0), max fit
residual 0.033 fF. On the SHIPPED default (feed=double) this makes the old model
under-predict by a consistent +1.7%:

| w | c_active (1.09·area) | C(double) | error |
|---|----------------------|-----------|-------|
| 5 | 24.45 | 24.85 | +1.66% |
| 7 | 34.23 | 34.80 | +1.68% |
| 10 | 53.78 | 54.70 | +1.70% |
| 15 | 78.23 | 79.64 | +1.81% |

## Decision (Option A)

Add a double-feed term to the model, both PDKs:

    feed == 'double' :  C = c_active + CFEED2_SLOPE * pad_len,  CFEED2_SLOPE = 0.152

with `pad_len = ny*UC_Y + 2*T_BAR` (same pad_len as the single-side branch).
Propagate to the PCell C-label, xschem tcleval, qucs-s equation (g2), and
regenerate osdi + electrical goldens in both PDKs. Retire the "errors cancel"
prose. CFEED (single-side) and the N=4 area density are unchanged.

## Implementation (both PDKs, done)

CFEED2_SLOPE = 0.152 added; `feed=='double'` now bills `c_active +
CFEED2_SLOPE*pad_len`. Edited in each PDK: `cap_cmomi.va` (constant, `isdbl`
selector, `cfeed_fF`, header/SCALE prose), PCell C-label (`cap_cmomi_code.py` /
`cmomi_code.py`), xschem `cap_cmomi.sym` tcleval. g2 also: qucs-s symbol
`cap_cmomi.xml` + example `ac_mom_cap.sch` equation (and its annotation, now the
correct 929.83 fF for 10x70 M1..M5), and the consistency test's qucs comparison
(qucs has no string branch, so its equation tracks the default feed=double and is
compared on double cases only). osdi rebuilt (openvaf) and gnucap plugin rebuilt
in both; the two electrical goldens per PDK regenerated:

| PDK | typ device | old C | new C |
|-----|-----------|-------|-------|
| cmos5l | 5x5 M1..M4 double | 20.37 fF | 21.12 fF |
| g2 | 5x5 M1..M5 double | 25.42 fF | 26.17 fF |

`cap_cmomi_consistency_test.py` PASSes in both PDKs: veriloga / PCell / xschem /
qucs and the two stored golden .out refs all agree.
