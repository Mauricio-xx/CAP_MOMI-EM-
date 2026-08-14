# cap_cmomi model changes — cross-session reference

State as of 2026-08-14. These changes are **committed on branch worktrees** but
NOT merged and NOT pushed. The INSTALLED PDKs (`~/.klayout`, `$PDK_ROOT`) do NOT
have them — point at the worktree to use the updated model.

## Worktrees (per PDK)

- **cmos5l**: `/home/montanares/git/slim-pdk/IHP-Open-PDK/ihp-sg13cmos5l-worktrees/cap-cmomi-rowfix`
  branch `fix/cap-cmomi-row-count`, tip commit `356ff2d` ("via the tooth tips and bill the double-side feed")
- **g2**: `/home/montanares/git/IHP-Open-PDK-worktrees/cap-cmomi-g2-fixes/ihp-sg13g2`
  branch `fix/cap-cmomi-row-and-feed`, tip commit `3bfaa650` (same subject)

## Model changes (both PDKs)

1. Row count: active rows = `floor(w/0.89)` (was `floor(w/0.89) - 1`).
2. Vias: each interdigitated tooth is via'd at base AND tip (`TOOTH_VIA_OFF = 0.41`),
   ~doubling per-tier via counts. Affects drawn geometry only.
3. Feed model, `pad_len = active_y*0.89 + 0.42`:
   - `feed=none`   -> `C = c_active`
   - `feed=same`   -> `C = c_active + 0.1625*pad_len + 0.0916`
   - `feed=double` -> `C = c_active + 0.152*pad_len`   (NEW; was 0)
   - `c_active = density[N] * active_area`, `active_area = floor(l/0.84)*0.84 * floor(w/0.89)*0.89`
   - density UNCHANGED: cmos5l {N<=2:0.55, N=3:0.82, N>=4:1.09}; g2 adds {N>=5:1.36}.

The via fix VALIDATES the density (it closed the old sparse-via deficit); it did NOT
change the density coefficients. The only coefficient added this session is the
double-feed slope `CFEED2_SLOPE = 0.152` (through-origin fit of the EM-measured
`C(feed=double) - C(feed=none)`).

## Current model files on each branch

`libs.tech/verilog-a/cap_cmomi/cap_cmomi.va`; the PCell
(`.../sg13cmos5l_pycell_lib/ihp/cap_cmomi_code.py` on cmos5l,
`.../sg13g2_pycell_lib/ihp/cmomi_code.py` on g2);
`libs.tech/xschem/<pr>/cap_cmomi.sym`; `libs.tech/ngspice/models/cap_cmomi.lib`;
g2 also `libs.tech/qucs-s/symbols/cap_cmomi.xml`.
cmos5l tracks `libs.tech/ngspice/osdi/cap_cmomi.osdi` (rebuilt); g2 gitignores osdi.

## Using / verifying the updated model (cmos5l)

- Layout from the branch PCell:
  `KLAYOUT_HOME=<empty dir> KLAYOUT_PATH=<cmos5l worktree>/libs.tech/klayout klayout -zz -r <script>`,
  tech `sg13cmos5l`, PCell name `cap_cmomi`. Empty KLAYOUT_HOME avoids the installed
  cmos5l; SET (never prepend) KLAYOUT_PATH because both PDKs register `SG13_dev`.
- Simulation: rebuild osdi from the branch `.va` (`libs.tech/verilog-a/openvaf-compile-va.sh`)
  and run ngspice with `PDK_ROOT=/home/montanares/git/slim-pdk/IHP-Open-PDK/ihp-sg13cmos5l-worktrees PDK=cap-cmomi-rowfix`
  so `$PDK_ROOT/$PDK` resolves to the worktree (the installed osdi is stale).
- Numeric check (cmos5l, N=4): `5x5 double = 21.11 fF`, `5x5 same = 21.26 fF`,
  `5x5 none = 20.37 fF`. `libs.tech/klayout/sg13cmos5l_tests/cap_cmomi_consistency_test.py`
  cross-checks PCell / xschem / osdi / goldens and prints PASS.
