# ngspice cross-check of the PSU hold-up model

Method: the real RideThroughCore model is run on a controlled one-group dip; an ngspice power stage (bulk cap, input-current-limited PFC,
constant-power DC-DC) is driven by the model's own service-voltage, lockout and demand traces; hold-up energy traces are compared.
Reproduce: `.venv/bin/python validation/crosscheck/run_psu_crosscheck.py` (needs ngspice, Docker and the built model).
Capacitor sized from the spec (20 ms at 3 kW out, eta 0.965), not from the model's 60 J.

## Findings
1. **Default PSU mode (`psu_cap_datasheet=True`) assumes no hold-up use before lockout; the circuit disagrees unless the PFC can draw
   about 2x the datasheet current.** In a 12 ms sag (below the 16.7 ms debounce) at 0.5 pu the model keeps hold-up at 1.00. The circuit
   drops to 0.78 with I_lim = 3000/(0.965*180) = 17.3 A, 0.86 at 1.25x, 0.94 at 1.5x, 0.99 at 2x. The model's old per-unit mode
   (`psu_cap_datasheet=False`) tracks the 1.0x circuit to within 0.01-0.05 at every depth tested (0.45-0.75 pu).
   Physical basis: at 95 V (0.415 pu at the SDP) the model delivers 2.55 kW per PSU, which needs 27.8 A input, 1.6x the 17.3 A that
   the 180 V rating implies.
2. **It matters for the validated quantity.** Peak facility current: datasheet mode 1.70/1.49/1.16 pu (A/B/0.844) vs per-unit mode
   1.26/1.32/1.15, against reported 1.60/1.50. Failure modes are identical in both modes. The 1-cycle debounce was fitted with datasheet
   mode on, so it may be compensating for the missing current limit (FINDINGS already says it is an inference, not independent evidence).
3. **Recharge:** the model's fixed 50 ms time constant is 1.4-6x slower than PFC headroom allows (load 0.85: 78 vs 16 ms to 95%).
   Not consequential for sampled scenarios: reclose gaps are >= 0.25 s (sim/scenario.py:347-348).
4. **Consistent:** the 1/P hold-up law and 20 ms at 3 kW (13.3 ms at 150% load = 60/4500 is the spec's own data point).

## Unresolved
The PSU input-current limit is not in the public AE ORv3 page (only the 180-305 V range). Findings 1-2 hold for any limit below ~2x the
180 V rating and vanish above it. Getting that number (full AE datasheet, or the PFC peak-current limit) settles it.
Not covered: unbalanced/single-phase input, PFC loop dynamics, 48 V droop and BBU handoff (the model triggers the BBU on voltage).
Model runs below ~0.45 pu retained collapse the voltage solution and end early, so those depths are untested.

# PyBaMM cross-check of the BBU temperature derating (`pybamm_bbu.py`)
Delivered energy vs 25 C, constant-current discharge, isothermal SPMe, to each set's own cut-off.

| | -10 C | 0 C | 10 C | 25 C | 35 C |
|---|---|---|---|---|---|
| **model (Sandia LFP table)** | 0.64 | 0.74 | 0.84 | 1.00 | 1.06 |
| Ecker2015 NMC, 1C | 0.75 | 0.93 | 0.97 | 1.00 | 1.01 |
| Ecker2015 NMC, 3C | 0.16 | 0.70 | 0.88 | 1.00 | 1.03 |
| Marquis2019, 1C / 2C | 0.23 / 0.06 | 0.94 / 0.13 | 0.97 / 0.96 | 1.00 | 1.01 / 1.02 |
| NCA_Kim2011, 1C / 2C | 0.97 / 0.15 | 0.99 / 0.95 | 0.99 / 0.98 | 1.00 | 1.00 |

1. **In the sampled range (battery 18-27 C, stress 32-35 C) the model's factor is within about 7% of PyBaMM** (model 0.93 at 18 C and 1.06 at 35 C;
   PyBaMM 0.97-1.03). Agreement is adequate there, not strong: the model's >1 at 35 C is not reproduced (+1-3%).
2. **Below ~10 C the model's single factor is not a rate-independent quantity.** PyBaMM at 1C gives 0.93-0.99 at 0 C, but 0.07-0.70 at 2-3C
   (cells fall off a cliff), so 0.74 is right only by coincidence at one rate. The BBU runs ~8-9 /h (3 kW from 333 Wh), well past the 3C limit
   where these sets solve, so cold-hall behaviour at BBU rates is UNTESTED, not validated.
3. **Not answered:** the open 200 vs 333 Wh item. A constant-power 9 /h discharge failed to solve on Chen2020 (stiff at cut-off), and none of the
   public sets is a 1.5 Ah power cell. It needs the BBU cell datasheet's discharge curve at the actual rate, or a power-cell parameter set.
4. Ageing (2.5%/yr fade) is not covered: PyBaMM lifetime runs need thousands of cycles and the BBU is float-held (calendar ageing). Chen2020 and
   Prada2013 show no temperature response at all (<=3% across -10..35 C), so they are not usable for this check.

# PSU input-current limit: source search (done 2026-10-18)
The Advanced Energy 50 V 3 kW ORv3 PSU datasheet (rev 02-03-26, 18 pp) was read in full. It gives input range 180-305 VAC, start-up 178 V,
lockout 172 V, hold-up 20 ms at 200-277 VAC/100% load, PF >= 0.98 at 30-100% load, 30 A inrush, and primary fusing (size unstated), but
**no input current rating and no low-line derating**. The 5.5 kW HPR datasheet and the AE product pages are equally silent. The input-current
limit needed by finding 1 is therefore not public; it needs AE (or the OCP ORv3 PSU spec's protection section, which the search returned only as a table of contents).
What the datasheet does confirm: 10 ms of hold-up before the 3 V droop at 100% load (30 J), matching the model's E_FRAC_BBU logic, and the 20/18.2/16.7/.../13.3 ms
load table (= 60 J / P).

# DPsim + plain-Python cross-check of the grid voltage-drop network (`network_check.py`)
The model computes the service-delivery-point voltage from a SCALAR quadratic (series impedance collapsed to one real drop factor, Z_EFF_FACTOR at
pf 0.9, X/R 10). The exact network is a constant-power load (P + jQ) behind the complex impedance |Z| = z_total * chain_loading = 0.148 pu at X/R 10,
tap-set so rated load sees 1.0 pu. Same Z and load in all three solvers; 36 cases (dip 0.4-0.9 pu, load 0.5-1.0 pu, load pf 0.9 and 0.98).
1. **DPsim and an independent plain-Python complex solve agree to 1.4e-9 pu on all 25 solvable cases**, and both find no solution on the other 11,
   so the exact reference is solid.
2. **The model's voltage during a dip is too high: mean +0.040 pu, up to +0.165 pu** (positive = model optimistic). Examples (pf 0.9, load 0.85 pu):
   dip 0.7 -> model 0.687, exact 0.625; dip 0.6 -> model 0.578, exact 0.413; dip 0.8 -> 0.796 vs 0.767. The error is largest in the 0.5-0.7 pu band
   that dominates the ERCOT events, and it shrinks to < 0.01 above 0.9 pu.
3. **The model finds an operating point in all 11/11 cases where none physically exists** (e.g. dip 0.5, load 0.85; dip 0.6, load 1.0). The real
   network voltage-collapses there; the model's collapse guard (v_disc) trips later than it should, and its collapse boundary is too deep.
4. **Consequences.** (a) PSU lockout is decided on this voltage: at 277 V supply the lockout is 0.62 pu, and a 0.7 pu dip at load 0.85 gives the
   model 0.687 (rides through comfortably) but the exact network 0.625 (marginal). (b) Grid current i = p/v is understated by the same ratio, e.g.
   1.24 vs 1.36 pu at dip 0.7: the model's peak current, the quantity checked against facilities A/B, is biased low from this source, opposite in sign to
   the PSU current-limit effect found with ngspice (which biases it high), so the two errors may be offsetting in the fitted debounce.
5. Not covered: the Z itself (z_total_pct and chain loading are model inputs, unverified here), unbalanced faults (the model scales by faulted
   phase fraction; DPsim runs here are balanced), and voltage-dependent Q. Network settling time is not a concern by estimate: tau ~ X_tot /
   (omega * R_tot) ~ 2 ms for this network, short next to the 1 ms sense filter and 16.7 ms debounce (analytic, not simulated).

# Exact network solve in the model, and the A/B re-run (model/RideThroughCore.mo, 2026-10-18)
`v_sdp_pu` is now the exact constant-power solve (x = |V|^2 root of x^2 - b x + |Z|^2 (p^2+q^2) = 0, tap-set source), replacing the scalar drop. The
scalar reference in `network_check.py` (`model_v`) is kept as the "old model" column. `v_disc`/`v_branch_margin` still gate invalid runs.
Before/after: `validation_before_network_fix.json`, `validation_after_network_fix.json`, `network_refit.json` (all at the committed defaults unless noted).

| case (target) | before | after exact network |
|---|---|---|
| A loss 0.46 / peak 1.60 | 0.445 / 1.70, cooling tripped | **voltage collapse (run invalid)**; 0.545 / 2.43 |
| B loss 0.24 / peak 1.50 | 0.245 / 1.49 | 0.26 / 1.79, cooling tripped |
| 0.844 loss 0.19 | 0.245 | 0.245 (unchanged) |
| 70-sag product: median / worst recovery (target 0.41 / 0.49 s) | 0.371 / 4.00 s | **0.386 / 1.35 s**; never disconnected, 100% inside rule |

1. **The old A/B agreement was partly a compensating error.** The 1-cycle debounce and the legacy share were fitted under a network that read too
   high in voltage. With the exact network at the same defaults, B's peak current is 19% high and A is no longer a valid run.
2. **The 70-sag benchmark improved**: worst recovery 4.0 -> 1.35 s (target 0.49) and median 0.371 -> 0.386 s (target 0.41). That is independent evidence
   the exact solve moves the model toward real behaviour.
3. **Refit sweep** (debounce 0-33 ms x PSU mode, `network_refit.json`): B is reproduced within about 8% on peak by either mode (datasheet mode at 0 ms: 1.57,
   loss 0.26; input-limited/per-unit mode at 17-33 ms: 1.38-1.39, loss 0.26), so B does not discriminate between them. **A cannot be reproduced at
   all**: datasheet mode collapses the voltage at every debounce; per-unit mode never trips the PSUs (loss 0.08, "no disturbance").
4. **Why A fails, and the new gating limitation:** A is a 2-of-3-phase fault at 0.535 pu. The model applies the dip to the whole facility's network voltage
   and uses the faulted-phase fraction only for PSU tripping, so it is a balanced equivalent that is harsher than reality (the healthy phase carries
   load without the dip). The old optimistic voltage was masking this. Resolving it needs an unbalanced three-phase network (DPsim SP/EMT Ph3), not a
   different PSU setting.
5. The 4 pre-existing test failures (test_adapter x2, test_scenario_distributions x2) are unchanged; no new failures (71 pass / 22 skipped).
6. Defaults (`psu_uv_delay_s` = 1/60, `psu_cap_datasheet=True`) were NOT changed: the data above do not pick a pair, and the PSU input-current limit that would
   decide it is not public (see above).

# Facility A/B were mis-specified, not unreproducible (`caseA_depth.py`, defaults unchanged)
The validation cases enter the retained voltage OBSERVED at the facility (A: "PSU sees 148 V at 277 V" = 0.535 pu; B: 0.670) as `dip_depth_pu`, but the model
treats `dip_depth_pu` as the SOURCE voltage behind the transformer chain. The old, too-optimistic network made the two nearly equal; the exact network does not.
Setting the source depth so the voltage at the PSUs equals the observed value (no other change, no refit):

| case | source depth | min v at PSUs (observed) | peak current (target) | loss (target) |
|---|---|---|---|---|
| A | 0.67 | 0.534 (0.535) | 1.55 (1.60), -3% | 0.417 (0.46) |
| B | 0.74 | 0.656 (0.670) | 1.45 (1.50), -3% | 0.245 (0.24) |

Peak current is within 3% for both at the committed defaults (psu_uv_delay_s = 1/60, psu_cap_datasheet = True), where the old-network fit had needed the
debounce tuned. A's loss is 4 points low (the legacy share was fitted under the old network and should be re-fitted).
Unbalanced three-phase network: NOT built. In a grounded-wye 277/480 V system with single-phase PSUs the phases decouple, so each phase sees the balanced
single-phase result; coupling would only matter for delta/ungrounded paths (a transformer-connection question that needs the facility one-line diagram).
Next: change `validation/cases.py` to convert observed voltage to source depth (inverse of the exact solve), re-fit the legacy share, re-run.

# Final validation state after the network fix and case re-specification (`validation_final.json`, `calibrate_cases.py`)
Case inputs converted from observed to source voltage by bisection on the model (A 0.535 -> 0.671, B 0.670 -> 0.749, 0.844 -> 0.875). Defaults unchanged.

| check | target | model | status |
|---|---|---|---|
| A peak current (unfitted) | 1.60 | 1.54 | -4% |
| B peak current (unfitted) | 1.50 | 1.42 | -5% |
| A sustained loss | 0.46 | 0.46 | FITTED (legacy share 0.46 -> 0.50; loss slope vs share ~1.07, so not evidence) |
| B sustained loss | 0.24 | 0.245 | legacy 0.30 from earlier fit; a discrete cliff sits between 0.28 (0.73 loss) and 0.32 (0.27), so this is fragile |
| 0.844 loss (out of sample) | 0.19 | 0.245 | +5.5 points high, unchanged from before |
| 70-sag median / worst recovery | 0.41 / 0.49 s | 0.386 / 1.35 s | median -6%; worst-case 2.7x too slow |
| 70-sag never disconnected | yes | yes | pass |

Independent evidence for the physics: ngspice (hold-up law, PSU shortfall), DPsim + plain-Python (network, agree to 1e-9), PyBaMM (battery temperature, 18-35 C within ~7%).
Open: PSU input-current limit (not public), 200 vs 333 Wh and cold-rate battery behaviour (no suitable cell model), unbalanced/delta paths (needs one-line diagram),
the B legacy-share cliff, and the worst-case recovery tail. ANDES and Julia were not run.
