# How the simulator was cross-checked, and why it is "robust enough for now"

Status: hackathon-grade. **Partially cross-checked against independent engines; not validated.** Scope and pass criteria are in `SCOPE.md`; numbers and
raw outputs are in `crosscheck/RESULTS.md` and `crosscheck/*.json`. Date of work: 2026-10-18.

## 1. What was checked, with which engine

| Sub-model | Independent reference | How | Verdict |
|---|---|---|---|
| PSU hold-up energy (60 J, 20 ms at 3 kW) | ngspice 42 | Bulk capacitor sized from the AE spec (20 ms at 3 kW out, eta 0.965), not from the model's 60 J. Constant-power DC-DC stage, input-current-limited PFC. The circuit is driven by the real model's own voltage, lockout and demand traces (`ngspice_psu.py`, `run_psu_crosscheck.py`) | Hold-up law and spec point agree. **Model was optimistic before lockout** (assumed full PSU power down to 0.4 pu, needing ~2x the datasheet-implied input current) |
| Grid voltage network at the PSUs | Plain-Python exact complex solve + DPsim SP power flow (Newton-Raphson) | Same Z, same constant-power load, 36 cases (`network_check.py`) | The two references agree to 1.4e-9 pu. **Model's scalar shortcut read up to 0.165 pu too high** and found a voltage where none exists in 11/11 cases. Fixed |
| Battery usable energy vs temperature | PyBaMM 26.10 (Ecker2015, Marquis2019, NCA_Kim2011; Chen2020/Prada2013 run but show no temperature response) | Constant-current discharge, isothermal SPMe, ratio vs 25 C (`pybamm_bbu.py`) | Within ~7% over the sampled 18-35 C. Not meaningful below ~10 C or at the BBU's real rate |
| Whole simulator vs real events | NERC/ERCOT facilities A, B, 0.844 case; 70-sag benchmark | `validation/run_validation.py` | See section 3 |

Not run: ANDES (only used earlier to generate the dip library), Julia, DPsim EMT. ngspice's PSU circuit uses an input-current limit of 17.3 A (the current implied
by "3 kW down to 180 V"); the real number is not in the AE datasheet (read in full) or product pages.

## 2. What the cross-checks changed in the simulator

1. **Exact network solve replaced the scalar voltage drop** (`model/RideThroughCore.mo`, `v_sdp_pu`). Evidence it was right, beyond DPsim agreement: the 70-sag
   benchmark worst recovery moved 4.0 s -> 1.35 s and median 0.371 -> 0.386 s (target 0.41 / 0.49 s).
2. **Facility A/B inputs were mis-specified.** The observed facility voltage (0.535, 0.670) had been entered as the source depth. With the exact network they differ;
   they were converted by bisection on the model (`calibrate_cases.py`): A 0.671, B 0.749, 0.844 case 0.875. Peak current then landed within 4-5% with no tuning.
3. **PSU input-current limit became an explicit parameter** (`psu_ilim_x`, default 0 = no limit, so results are unchanged). Its value is an assumption; a
   sensitivity sweep (`ilim_sensitivity.py`) was started and was still running when this was written.
4. Facility A's legacy-load share was re-fitted 0.46 -> 0.50 after the network change. This is a fit, not evidence.

## 3. Where it stands (final run, `crosscheck/validation_final.json`)

| check | real | model | note |
|---|---|---|---|
| Facility A peak current | 1.60 | 1.54 | unfitted, -4% |
| Facility B peak current | 1.50 | 1.42 | unfitted, -5% |
| Facility A loss | 0.46 | 0.46 | FITTED (loss slope vs legacy share ~1.07) |
| Facility B loss | 0.24 | 0.245 | a discrete cliff sits at legacy share 0.28-0.32, so fragile |
| 0.844 case loss (out of sample) | 0.19 | 0.245 | +5.5 points |
| 70-sag median / worst recovery | 0.41 / 0.49 s | 0.386 / 1.35 s | worst 2.7x slow; 17 of 70 runs are flagged invalid voltage collapses |
| 70-sag never disconnected | yes | yes | |
Tests: 71 pass, 22 skipped, 4 fail (`test_adapter` x2, `test_scenario_distributions` x2); these failed before this work and were not investigated.

## 4. Why "robust enough for now" (and what that does and does not mean)

Reasons it is defensible for a hackathon:
- **The references are independent of the model and of each other.** ngspice solves circuit equations, DPsim and the plain-Python solve are two separate
  implementations of the same network equations that agree to 1e-9, PyBaMM is an electrochemical model. None share code with the Modelica.
- **Each check was run against the real model's own traces**, not a re-typed copy, so a mismatch in either direction shows up (and two did).
- **The checks were able to fail, and did**: they found the optimistic PSU assumption and the 0.165 pu network error. A check that cannot disagree proves nothing; the
  first ngspice attempt was circular (capacitor sized from the 60 J) and was discarded and rebuilt.
- **Fixes were confirmed by a measurement the fix was not tuned on** (the 70-sag benchmark, and A/B peak current, which was never fitted).
- **The claim is scoped** (`SCOPE.md`), with every unmet or blocked criterion listed there, so nothing is silently over-claimed.

What "robust enough" does NOT mean:
- Not validated: several `SCOPE.md` criteria are NOT MET or BLOCKED (PSU behaviour before lockout, battery at the real rate, 5+ unfitted real events, composite
  verdict agreement, worst-case recovery).
- Real data is 2 events plus one benchmark; one of the two losses is a fit.
- Out of scope and untested: cold battery halls, delta/ungrounded or phase-coupled paths (needs the facility one-line diagram), unbalanced three-phase, ANDES time
  domain, Julia re-implementation.
- No independent human review; `SCOPE.md` is a stand-in for pre-registration.

Suggested wording: "Sub-models cross-checked against ngspice, DPsim and PyBaMM within a stated scope. The cross-check found and fixed a grid-voltage error; PSU
current-limit and cold/high-rate battery behaviour remain open." Do not say "validated".

## 5. Reproduce
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pybamm dpsim andes   # plus: apt install ngspice; Docker for OpenModelica
.venv/bin/python validation/crosscheck/run_psu_crosscheck.py        # ngspice vs model
.venv/bin/python validation/crosscheck/network_check.py             # DPsim + plain Python vs model network
.venv/bin/python validation/crosscheck/pybamm_bbu.py                # PyBaMM battery temperature
.venv/bin/python -m validation.run_validation out.json              # A/B/0.844 + 70-sag benchmark
.venv/bin/python -m validation.crosscheck.calibrate_cases           # observed -> source voltage, legacy sweep
```
