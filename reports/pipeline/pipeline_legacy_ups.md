# Product performance and failure drivers: legacy_ups

Unit: one grid event hitting one site. 100,000 events, seed 0.

## Performance

- Probability an event fails: **99.5%** (Monte Carlo 95% interval 99.5% to 99.5%).
- By ensemble member: 99.0%, 99.6%, 99.6%, 99.7%, 99.5% (surrogate disagreement).
- Events that almost surely fail (P>0.9): 98.9%; almost surely pass (P<0.1): 0.0%.

How events fail (share of all events):

- exceeded 125% current cap: 51.6%
- cooling tripped: 28.8%
- below power floor: 17.1%
- storage hand-back too slow: 1.9%
- PSU shutdown and restart delay: 0.2%
- missed 2.0 s recovery: 0.0%

| measure | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| min_power | 0.0815 | 0.17 | 0.232 | 0.275 | 0.343 |
| peak_current_pu | 1.25 | 1.37 | 1.46 | 1.73 | 5.22 |
| floor_violation_s | 0.0479 | 0.0809 | 0.155 | 0.412 | 0.924 |
| recovery_margin_s | -5.35 | -0.645 | 1.06 | 1.37 | 1.55 |

## Group A: conditions (what the grid and weather do)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.2574 | 59% | -0.000998 to 0.459 (0.723) | 1-1 |
| 2 | Reclosing (second dip and gap) | 0.0786 | 18% | 5.0 (0.688) | 2-2 |
| 3 | Fault type (phases involved) | 0.0398 | 9% | 3LG (0.382) | 3-3 |
| 4 | Protection clearing (normal / breaker problem) | 0.0308 | 7% | breaker_failure (0.429) | 4-4 |
| 5 | Season and outdoor temperature | 0.0144 | 3% | -18.3 to 11.7 (0.307) | 5-5 |
| 6 | Site load level | 0.0082 | 2% | 0.204 to 0.39 (0.295) | 6-6 |
| 7 | Workload type (power-swing size and rate) | 0.0064 | 1% | inference (0.291) | 7-7 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0089 | 47% | -0.000998 to 0.459 (1) | 1-1 |
| 2 | Workload type (power-swing size and rate) | 0.0029 | 15% | training (0.997) | 2-2 |
| 3 | Site load level | 0.0025 | 13% | 0.204 to 0.39 (0.997) | 3-4 |
| 4 | Reclosing (second dip and gap) | 0.0023 | 12% | 5.0 (1) | 3-4 |
| 5 | Fault type (phases involved) | 0.0010 | 5% | 3LG (0.997) | 5-5 |
| 6 | Season and outdoor temperature | 0.0008 | 4% | 11.7 to 18.6 (0.996) | 6-6 |
| 7 | Protection clearing (normal / breaker problem) | 0.0006 | 3% | breaker_misoperation (0.998) | 7-7 |

Strongest pairwise interactions: dip_depth+reclose (0.0634); fault_type+dip_depth (0.0526); protection+dip_depth (0.0162).

## Group B: site state (what the equipment is like)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Equipment age | 0.0102 | 37% | -0.000654 to 3.02 (0.302) | 1-1 |
| 2 | Cooling plant makeup (compressor vs fan share) | 0.0070 | 25% | 0.574 to 0.602 (0.297) | 2-3 |
| 3 | Battery state of charge | 0.0067 | 24% | 0.799 to 0.84 (0.297) | 2-3 |
| 4 | Battery hall temperature | 0.0028 | 10% | 25.2 to 27 (0.294) | 4-4 |
| 5 | Compressor restart time | 0.0012 | 4% | 100 to 104 (0.291) | 5-5 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Cooling plant makeup (compressor vs fan share) | 0.0008 | 27% | 0.459 to 0.518 (0.995) | 1-2 |
| 2 | Battery state of charge | 0.0007 | 26% | 0.799 to 0.84 (0.996) | 1-2 |
| 3 | Equipment age | 0.0006 | 20% | -0.000654 to 3.02 (0.995) | 3-3 |
| 4 | Battery hall temperature | 0.0004 | 14% | 18 to 19.8 (0.995) | 4-5 |
| 5 | Compressor restart time | 0.0004 | 13% | 100 to 104 (0.995) | 4-5 |

Strongest pairwise interactions: battery_age+battery_temp (0.0023); battery_soc+cooling_makeup (0.0009); battery_temp+cooling_makeup (0.0007).

## Conditions versus site state

- p_fail: conditions 86%, site state 14%
- floor_violation_s: conditions 95%, site state 5%

## Caveats

- 100% of events have an input outside the surrogate's training range.
- Failure rate is 99.5%: P(fail) cannot be ranked meaningfully, so the headline ranking uses floor_violation_s.
- Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.
- The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).
- Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.
- Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.
- Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.
- Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.
