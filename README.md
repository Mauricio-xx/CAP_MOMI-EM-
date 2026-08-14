# CAP_MOMI-EM

Palace EM characterization campaign for the IHP `cap_cmomi` / `cap_mom`
interdigitated MOM capacitor. This repository is the simulated-data backup behind
the Verilog-A model shipped in the `ihp-sg13cmos5l` and `ihp-sg13g2` PDKs: the
electrostatic and full-wave solves, the extracted capacitances, and the analysis
that set and validated the model coefficients.

All layouts come from our own corrected pycell (fixed-via, `floor(w/0.89)` rows).
No third-party reference data is included.

## Contents

- `gds/` drawn layouts (our pycell) per length / width / metal stack, plus `_port` variants.
- `campaign/`, `scripts/` the solve and analysis pipeline (gds to Palace to C).
- `palace/` Palace run inputs and outputs (electrostatic `terminal-C`, full-wave 2-port).
- `convergence/` mesh and size convergence data.
- `results/` extracted capacitance and the validation reports.
- `fig/`, `docs/` deliverable figures and notes.

## Key results

- The model matches the fine-mesh electrostatic solve within +-1.6% across 2 to
  13.6 um (full-stack N=4 double). Re-extracted density[N] is 1.09 / 0.82 / 0.55
  fF/um^2 for N>=4 / N=3 / N<=2, and the row-count fix (`ay = floor(w/0.89)`, no -1)
  closes a pre-fix 6 to 44% gap.
- The +14% by which the campaign 2-port full-wave sat above the electrostatic solve
  is a mesh artifact: the run used `refined_cellsize = 0.5 um`, coarser than the
  0.84 um tooth pitch, so it under-resolved the inter-tooth gap that sets C.
  Refining converges to a small (~+4%) full-wave fringe, not a physical +14%
  correction. See `results/FW_MESH_INVESTIGATION.md` and `results/PHASE3_REPORT.md`.

## Reproduce

See the drivers in `scripts/` and `campaign/`. Palace 0.16; gmsh and scikit-rf in a
venv, klayout.db in system python; runs are serial and RAM-gated.

Status: EM-validated at device level, uncalibrated (no silicon yet).
