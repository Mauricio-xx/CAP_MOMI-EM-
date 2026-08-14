# FW-vs-ES gap on cap_mom: it is mesh, not a physical correction

Handoff note for the cmos5l / g2 model reviewer. Device: `cap_mom_double_04p9um`
(cap_cmomi, IHP sg13cmos5l), fixed-via, branch `fix/cap-cmomi-row-count` @ `356ff2d`.
All work under `/home/montanares/git/slim-pdk/issue92_em`.

## TL;DR

The +14.6% by which the 2-port full-wave `Cdiff` (23.82 fF) sat above the
electrostatic `C12` (20.79 fF) is **mostly a full-wave mesh artifact**, not a
physical correction and not evidence against the model. The campaign FW ran at
`refined_cellsize = 0.5 um`, coarser than the 0.84 um tooth pitch, so it did not
resolve the inter-tooth gap that sets the capacitance. Refining the mesh (only
that knob, same geometry) drives `Cdiff` monotonically toward the ES value:

| refined_cellsize (um) | Cdiff (fF) | vs ES 20.791 | peak | build/solve |
| --- | --- | --- | --- | --- |
| 0.50 | 23.82 | +14.6% | - | - |
| 0.35 | 22.35 | +7.5% | 998 MB | 75 s / 628 s |
| 0.25 | 22.15 | +6.5% | 1243 MB | 81 s / 789 s |
| 0.20 | 21.68 | +4.3% | 1571 MB | 85 s / 883 s |
| 0.18 | 21.63 | +4.0% | 1782 MB | 92 s / 1066 s |

It flattens near **+4%** by 0.18 um (step 0.20->0.18 = -0.05 fF): the FW does not
converge all the way to ES but to a small genuine full-wave fringe residual of
~+4% (~0.8 fF), well inside model tolerance and consistent with the ~+5% a clean
gds2palace comb flow shows. Below 0.18 um the mesh could not be pushed: rc=0.15
(and a retry with fstart=0.01e9 off the DC point) both died on an MFEM/SuperLU
singular matrix at a fixed DOF (64604) - an isolated-DOF mesh degeneracy that
gds2palace produces at that cell size, not RAM and not the DC excitation. rc=0.18
sits on a clean mesh and already pins the limit.

**The model is good at device level.** The trustworthy number is the fine-mesh ES
(lc = 0.10 um, resolves the gap): 20.79 fF vs model 21.11 fF = **+1.6%**. Across
2 to 13.6 um the error is +0.5% to +1.6%, density[N] fits R^2 ~ 1 at 1.09/0.82/0.55.
The FW at 0.5 must not be read as a "+14% physical correction" nor as the silicon
twin; it was an under-resolved cross-check.

## What was ruled out (and how)

The +14% is not the dielectric, not the test fixture, not the feed geometry:

| hypothesis | test | result |
| --- | --- | --- |
| layered stackup (6.6/11.9) vs uniform 4.1 | ES re-solve in layers (prior session) | **-0.6%** (moves C down) |
| stackup, by geometry | comb sits in 8.9 um SiO2 block, ~4.3 um of 4.1 above M4, EPI below z=0 | near-field all 4.1 |
| un-de-embedded fixture (feeds+ports+guard) | FW open dummy (comb removed) | **0.05 fF** trans-coupling |
| feed/port geometry adds to A-B C | ES on comb+feeds, uniform 4.1, shared domain | **+0.06 fF (+0.3%)** |
| FW mesh under-resolves the tooth gap | FW convergence sweep (table above) | **confirmed**, dominant |

Differential 2-port cancels common-mode loading (guard, substrate act to ground),
which is why the open removes essentially nothing: at 60 MHz the substrate is a
conductor (sigma/omega*eps ~ 250), not eps=11.9.

## Model validation (the real deliverable)

From the fixed-via ES campaign (`results/es_campaign.csv`) vs the branch `.va`
(reproduced in `campaign/analyze.py`):

- Full-stack N4 double, |err| = +0.5% to +1.6% over W = 2 to 13.6 um.
- density[N] re-extracted: N4 1.0947 (R^2 1.000), N3 0.8080 (0.997), N2 0.5289
  (1.000) vs model 1.09 / 0.82 / 0.55.
- Row-count fix (`ay = floor(w/0.89)`, no -1) closes a pre-fix 6-44% gap.
- Reduced-stack (m1m3/m2m4/m3m4) run +1 to +7% (documented simplifications:
  single density[N] ignores vertical position; double-feed coeff fit on 4-metal
  pads over-counts ~1 fF on 2-3 metal stacks).

Status: EM-validated at device level, **uncalibrated** (no silicon yet, Phase 4).

## Open items

- FW residual pinned: `Cdiff` flattens near +4% by rc=0.18 (21.63 fF), a small
  genuine full-wave fringe, well inside model tolerance. Finer meshes (rc<=0.15)
  hit an isolated-DOF SuperLU singular (mesh degeneracy from gds2palace at that
  cell size, unaffected by fstart), so 0.18 is the practical floor; it suffices.
- `results/PHASE3_REPORT.md` "Full-wave vs electrostatic" section and Verdict:
  rewritten to the mesh finding (convergence table parametrized from the sweep CSV,
  dielectric and fixture as ruled out, ES as reference). Done by the peer session
  (em-issues-momcapi) plus the generator fix here; regenerated. Not committed.

## Files (all under issue92_em/)

FW mesh convergence:
- `palace/rf2port/fw_converge.py` (driver; changes only refined_cellsize)
- `palace/rf2port/results/fw_converge_04p9.csv` (0.35/0.25/0.20 rows)
- `palace/rf2port/results/fw_converge_04p9.log`, `..._rc020.log`

Open-dummy de-embed:
- `palace/rf2port/deembed_open.py` (driver)
- `palace/rf2port/results/deembed_04p9.log`
- `palace/rf2port/results/cap_mom_open_04p9um.s2p` (open .s2p)
- `palace/rf2port/tb/cap_mom_open_04p9um_rf_tb.gds` (open fixture; tb/ is gitignored)

ES geometry discriminator:
- `campaign/es_geom_prep.py` (system python3: gdstk+klayout.db)
- `campaign/es_geom_solve.py` (venv python: gmsh+palace)
- `campaign/es_geom/` (comb_net.json, combfeeds_net.json, combfeeds.gds, params.json,
  es_geom_solve.summary.txt)

Baseline campaign / model:
- `results/es_campaign.csv`, `results/campaign_results.csv`
- `palace/rf2port/results/rf2port_results.csv` (FW @0.5: 02p0/04p9/10p7)
- `results/PHASE3_REPORT.md` (needs the FW-section rewrite noted above)
- `campaign/analyze.py` (model function, reproduces branch goldens)

## Reproduce

FW convergence: `cd palace/rf2port && python3 fw_converge.py 0.35 0.25 0.20`
Open de-embed:  `cd palace/rf2port && python3 deembed_open.py cap_mom_double_04p9um`
ES discriminator: `python3 campaign/es_geom_prep.py && ~/venv/palace/bin/python campaign/es_geom_solve.py`

Interpreter split: gmsh only in `~/venv/palace/bin/python`; klayout.db + gdstk only
in system `python3`. Palace 0.16 via `apptainer exec ~/palace.sif`, `-np 8`. Serial,
RAM-gated. Only `refined_cellsize` changes across the FW sweep; freq/order/ports/stackup fixed.
