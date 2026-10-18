# Structural-fix findings (branch sim-structure-fixes)

Image: openmodelica/openmodelica:v1.27.1-ompython (the pinned one). Earlier numbers in baseline.json were produced under v1.25.0-minimal.

## Validation, original model -> now
| case | sustained loss (real) | peak current pu (real) |
|---|---|---|
| facility A | 50.3% -> 44.5% (46%) | 1.48 -> 1.70 (1.60) |
| facility B | 28.1% -> 24.5% (24%) | 1.33 -> 1.49 (1.50) |
| 0.844 pu | 28.1% -> 24.5% (19%) | n/a |
| 70-sag product | median 0.383 -> 0.387 s (0.41), worst 1.34 -> 1.37 s (0.49), never disconnected: yes | |

## Item 7: the legacy-share fit is not a validation (validation/calibrate.py)
- Facility A: sustained loss = -0.03 + 1.03 x legacy_load_frac. Slope ~1: matching the loss only recovers the number you fitted. Only the
  UNFITTED observables (peak current, recovery) carry information: A +6.0%, B -0.9% on peak current.
- Facility B is NOT monotone: legacy share 0.0 -> 63% loss, 0.2 -> 70%, 0.3 -> 24.5%, 0.4 -> 35%. Below ~0.25 the BBU never hands back inside the
  15 s window (a second takeover at 4.46 s when the tripped PSUs restart) -- a discrete cliff, and the documented match sits ~0.05 above it.
- Leave-one-out loss predictions are poor (A's fraction predicts B 19.6 points high); the shallow 0.844 case is 5.5 points high.

## Other things found while doing this
- OpenModelica 1.27.1 ignores `-override stopTime/stepSize` ("override variable name not found"); 1.25 honoured it. They are runtime flags
  (`-stopTime`, `-stepSize`). On the pinned image every run therefore used the baked 15 s window and a 3.75 ms output step.
- The grader's peak current was an instantaneous maximum including a one-sample event-instant spike; it is now the one-cycle average.
- The relay opened the load instantly; breaker opening time (2-5 cycles) was missing. Added `legacy_open_delay_s` (default 50 ms).
- `psu_uv_delay_s` (lockout debounce, G) is the dominant unsourced quantity for peak current: 1 cycle reproduces BOTH facilities, which
  is an inference from the validation data, not independent evidence.
- PSU capability scaled with per-unit voltage (0.8 pu -> 80% power). The AE datasheet rates 3 kW over 180-305 VAC with lockout at 172 VAC.
  Now full power until lockout (ablation switch psu_cap_datasheet).
- Transformer %Z were summed on each unit's own base. Added chain_loading_frac (G, 0.5-1.0, default 0.75).
- Voltage solution: `v_disc` / `v_branch_margin` signals; the runner marks a run invalid on a collapsed root or no operating point. A plain-Python
  closed-form solution of the constant-power quadratic matches the Modelica trace within 2e-3 at four dip depths.

## Items 1-3 (priority list)
1. Invariants: hold-up energy is clamped at zero; the runner marks a run INVALID (numerics_ok False, mode "invalid: ...") on non-finite values,
   negative hold-up, state of charge outside [0,1], voltage outside [0,2] pu or negative grid power. 60 random scenarios: 0 invalid (was 1).
2. Grader now follows the primary text (PUCT report 2026-07-09, 282NOGRR-45): current <= 150% of the facility's own pre-event maximum and
   overcurrent <= 0.5 s (was 125%, nameplate-normalised, no duration); cooling that trips below 0.35 pu is removed from the reference;
   a load-transfer scheme below 0.8 pu is held to 0.5 s recovery (2.0 s otherwise). NOT implemented: "begins returning within 0.25 s".
   Table A (voltage envelope) was not re-checked against this text.
3. PSU debounce now 4.5 ms (AE ORv3 HPR datasheet: AC_LOSS_L validation delay 4-5 ms); the 1-cycle value was inferred from the validation data and is
   withdrawn. Breaker opening 3-5 cycles. Result: peak current is UNDER-predicted for the ERCOT crypto facilities (A 1.08 vs 1.60, B 1.26 vs 1.50) and
   reaching the real values needs >= ~16 ms. The ORv3 value may simply not apply to those facilities' (crypto) power supplies. Breaker opening time
   has no effect on current in these cases (PSUs lock out first).
