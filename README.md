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
- `campaign/`, `scripts/` the solve and analysis pipeline (gds to Palace to C), including the
  base+tip via generator (`add_tip_vias.py`) and the via-fixed width/length sweeps
  (`run_viafix_fw_sweep.py`, `run_viafix_es_sweep.py`, `run_viafix_lsweep.py`).
- `palace/` Palace run inputs and outputs: electrostatic `terminal-C`, and full-wave both the
  early 2-port (`rf2port`) and the clean in-plane-port `gds2palace` flow.
- `convergence/` mesh and size convergence data.
- `results/` extracted capacitance and the validation reports.
- `fig/`, `docs/` deliverable figures and notes.

## Key results

- The model is area-based: `C = density[N]*ax*ay*0.84*0.89 + Cfeed`, with
  `ax = floor(l/0.84)`, `ay = floor(w/0.89)`. Re-extracted density[N] is
  1.36 / 1.09 / 0.82 / 0.55 fF/um^2 for N=5 / N=4 / N=3 / N<=2, and the row-count fix
  (`ay = floor(w/0.89)`, no -1) closes a pre-fix 6 to 44% gap.
- The pycell now vias each tooth at base and tip, matching the foundry via lattice, and the
  opposite-side (double) feed is billed explicitly (`Cfeed = 0.152*pad_len` for feed=double),
  about +3.6% on the cmos5l default device and +2.9% on the g2 default. The area-density law
  is unchanged: it already assumed a fully-viaed cell.
- Clean gds2palace full-wave (in-plane port, `refined_cellsize = 0.2 um`) sits a consistent
  ~+5% above the electrostatic solve across width and length, and the electrostatic solve
  matches the model to ~+-1%. Pooling every W/L geometry onto a residual axis, both bands stay
  flat over ~2 decades of C: the +5% is a physical edge-field fringe, not a size- or
  aspect-dependent error. See `fig/collapse_wl.png` and `fig/model_vs_gds2palace_fw.png`.
- The earlier +14% by which the campaign 2-port full-wave (`rf2port`) sat above the
  electrostatic solve was a mesh artifact: that run used `refined_cellsize = 0.5 um`, coarser
  than the 0.84 um tooth pitch, so it under-resolved the inter-tooth gap that sets C. The
  gds2palace flow above resolves it and supersedes that number. See
  `results/FW_MESH_INVESTIGATION.md` and `results/PHASE3_REPORT.md`.

## Reproduce

The two model-vs-EM figures regenerate from the committed CSVs:

    python scripts/plot_gds2palace_fw.py     # fig/model_vs_gds2palace_fw.png
    python scripts/plot_collapse.py          # fig/collapse_wl.png

The solves themselves use Palace 0.16; gmsh and scikit-rf in a venv, klayout.db in system
python; runs are serial and RAM-gated. See the drivers in `scripts/` and `campaign/`.

Status: EM-validated at device level, uncalibrated (no silicon yet).
