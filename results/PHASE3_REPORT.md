# cap_mom EM campaign, Phase 3: model validation

Palace electrostatic EM (plus a gds2palace full-wave cross-check) against the updated cap_cmomi Verilog-A model (branch `fix/cap-cmomi-row-count`, commit `1e93ffc`). All layouts regenerated from that branch PCell (via fix + `floor(w/0.89)` rows), geometry XOR-verified against the simulated GDS. Model function imported from `campaign/analyze.py`, which reproduces the branch `.va` goldens (5x5 N4: double 21.12 / same 21.26 / none 20.37 fF).

## Verdict

The updated model matches EM within **+-1.6%** across the full drawn size range for the fab-relevant full-stack double devices (fine-mesh ES sweep; the viafix ES sweep behind the collapse figure agrees to ~+-1%). The row-count fix (`ay=floor(w/0.89)`, no -1) is what closes the gap: the pre-fix billing under-predicted by 6-44%. Density[N] and both feed terms are consistent with the model. The clean gds2palace full-wave sits a small consistent ~+5% edge-field fringe above the electrostatic solve.

## Full-stack (N=4) double: C vs size

![C vs size](../fig/phase3_c_vs_size.png)

| W=L (um) | ES C12 (fF) | model (fF) | err % | pre-fix err % |
| --- | --- | --- | --- | --- |
| 2.0 | 3.54 | 3.59 | +1.62 | -44.5 |
| 4.9 | 20.79 | 21.11 | +1.55 | -18.1 |
| 7.8 | 59.37 | 59.82 | +0.76 | -11.6 |
| 10.7 | 118.33 | 119.03 | +0.59 | -7.7 |
| 13.6 | 196.67 | 197.67 | +0.51 | -6.1 |

**Full-wave (gds2palace).** The full-wave is the in-plane-port gds2palace flow at `refined_cellsize = 0.2 um`: it sits a consistent ~+5% over the electrostatic solve across width and length (+5.9% @w2, +5.0% @w5, +4.5% @w7, +3.9% @w15 at l=5.5; +7.3% @l2.5, +3.9% @l10, +3.7% @l14 at w7), a physical edge-field fringe. Data: `palace/gds2palace/viafix_fw_sweep.csv` + `viafix_fw_lsweep.csv` vs `palace/es_viacorner/es_viafix_sweep.csv` + `es_viafix_lsweep.csv`. See `fig/model_vs_gds2palace_fw.png` and `fig/collapse_wl.png`.

![error vs size](../fig/phase3_error_vs_size.png)

## Density[N] re-extracted from the fixed-via ES sweep

![density ladder](../fig/phase3_density_ladder.png)

| N | density fit (fF/um^2) | model | intercept (fF) | R2 | n pts |
| --- | --- | --- | --- | --- | --- |
| 4 | 1.0947 | 1.09 | +0.36 | 1.00000 | 5 |
| 3 | 0.8080 | 0.82 | +0.59 | 0.99705 | 4 |
| 2 | 0.5289 | 0.55 | +0.54 | 1.00000 | 2 |

N=3 comes from `m1m3` and `m2m4` (count, not vertical position); N=2 from `m3m4`. The small positive intercept is the fringe/feed offset the pure area law omits.

## C(same) - C(double) feed delta

| W=L (um) | EM delta (fF) | model[same-double] (fF) | pad_len (um) |
| --- | --- | --- | --- |
| 2.0 | +0.040 | +0.115 | 2.20 |
| 4.9 | +0.167 | +0.143 | 4.87 |
| 7.8 | +0.127 | +0.171 | 7.54 |
| 10.7 | +0.176 | +0.208 | 11.10 |
| 13.6 | +0.305 | +0.236 | 13.77 |

Both feeds add cap to `Cmain` (double `0.152*pad_len`, same `0.1625*pad_len+0.0916`), so the same-minus-double delta is small; EM and model agree at the ~0.1 fF ES noise floor.

## Reduced-stack ladder (m1m3 / m2m4 / m3m4)

| cell | N | W (um) | L (um) | EM C12 (fF) | model (fF) | err % |
| --- | --- | --- | --- | --- | --- | --- |
| n2_m3m4_w7_l10 | 2 | 7 | 10.0 | 30.98 | 32.67 | +5.4 |
| n2_m3m4_w7_l5p5 | 2 | 7 | 5.5 | 17.14 | 18.28 | +6.6 |
| n3_m1m3_w7_l10 | 3 | 7 | 10.0 | 46.39 | 48.21 | +3.9 |
| n3_m1m3_w7_l5p5 | 3 | 7 | 5.5 | 25.57 | 26.76 | +4.7 |
| n3_m2m4_w7_l10 | 3 | 7 | 10.0 | 47.81 | 48.21 | +0.8 |
| n3_m2m4_w7_l5p5 | 3 | 7 | 5.5 | 26.35 | 26.76 | +1.5 |

Reduced-stack cells run +1 to +7% high. Two documented model simplifications, not bugs: a single `density[N]` ignores vertical position (`m2m4` reads ~3% above `m1m3` at identical N), and the double-feed coefficient (0.152, fit on 4-metal pads) over-counts ~1 fF on 2-3 metal stacks.

## Notes

- Large reduced-stack fab devices (65-80 um) exceed the fine-mesh RAM floor and are model-projected (Phase 4); density is intensive and set by the small cells here.

