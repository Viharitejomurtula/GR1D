# Product performance and failure drivers: grid_friendly

Unit: one grid event hitting one site. 100,000 events, seed 0.

## Performance

- Probability an event fails: **99.3%** (Monte Carlo 95% interval 99.3% to 99.3%).
- By ensemble member: 99.1%, 99.4%, 99.5%, 99.5%, 99.1% (surrogate disagreement).
- Events that almost surely fail (P>0.9): 98.2%; almost surely pass (P<0.1): 0.0%.

How events fail (share of all events):

- exceeded 125% current cap: 52.9%
- cooling tripped: 29.7%
- below power floor: 15.6%
- storage hand-back too slow: 1.0%
- PSU shutdown and restart delay: 0.0%
- missed 2.0 s recovery: 0.0%

| measure | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| min_power | 0.103 | 0.181 | 0.239 | 0.283 | 0.429 |
| peak_current_pu | 1.25 | 1.37 | 1.48 | 1.69 | 4.83 |
| floor_violation_s | 0.0364 | 0.0681 | 0.131 | 0.368 | 0.822 |
| recovery_margin_s | -2.09 | 0.738 | 1.34 | 1.52 | 1.78 |

## Group A: conditions (what the grid and weather do)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.2331 | 59% | -0.000998 to 0.459 (0.647) | 1-1 |
| 2 | Reclosing (second dip and gap) | 0.0680 | 17% | 5.0 (0.615) | 2-2 |
| 3 | Fault type (phases involved) | 0.0350 | 9% | 3LG (0.339) | 3-3 |
| 4 | Protection clearing (normal / breaker problem) | 0.0262 | 7% | breaker_failure (0.373) | 4-4 |
| 5 | Season and outdoor temperature | 0.0147 | 4% | -18.3 to 11.7 (0.272) | 5-5 |
| 6 | Site load level | 0.0095 | 2% | 0.437 to 0.496 (0.261) | 6-6 |
| 7 | Workload type (power-swing size and rate) | 0.0061 | 2% | training (0.256) | 7-7 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0116 | 48% | 0.459 to 0.727 (1) | 1-1 |
| 2 | Workload type (power-swing size and rate) | 0.0049 | 20% | training (0.997) | 2-2 |
| 3 | Reclosing (second dip and gap) | 0.0024 | 10% | 5.0 (1) | 3-4 |
| 4 | Site load level | 0.0022 | 9% | 0.204 to 0.39 (0.994) | 3-4 |
| 5 | Fault type (phases involved) | 0.0016 | 7% | 3LG (0.997) | 5-5 |
| 6 | Season and outdoor temperature | 0.0010 | 4% | 11.7 to 18.6 (0.994) | 6-6 |
| 7 | Protection clearing (normal / breaker problem) | 0.0006 | 3% | breaker_misoperation (0.996) | 7-7 |

Strongest pairwise interactions: dip_depth+reclose (0.0552); fault_type+dip_depth (0.0467); dip_depth+weather (0.0180).

## Group B: site state (what the equipment is like)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Battery state of charge | 0.0069 | 31% | 0.799 to 0.84 (0.262) | 1-1 |
| 2 | Equipment age | 0.0058 | 26% | -0.000654 to 3.02 (0.261) | 2-2 |
| 3 | Cooling plant makeup (compressor vs fan share) | 0.0053 | 24% | 0.574 to 0.602 (0.26) | 3-3 |
| 4 | Battery hall temperature | 0.0034 | 15% | 19.8 to 21.6 (0.257) | 4-4 |
| 5 | Compressor restart time | 0.0008 | 3% | 100 to 104 (0.256) | 5-5 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Battery hall temperature | 0.0009 | 33% | 18 to 19.8 (0.994) | 1-2 |
| 2 | Cooling plant makeup (compressor vs fan share) | 0.0008 | 29% | 0.518 to 0.547 (0.993) | 1-2 |
| 3 | Battery state of charge | 0.0006 | 20% | 0.799 to 0.84 (0.994) | 3-3 |
| 4 | Equipment age | 0.0003 | 11% | -0.000654 to 3.02 (0.993) | 4-4 |
| 5 | Compressor restart time | 0.0002 | 7% | 100 to 104 (0.994) | 5-5 |

Strongest pairwise interactions: battery_age+battery_temp (0.0020); battery_soc+cooling_makeup (0.0008); battery_temp+cooling_makeup (0.0008).

## Conditions versus site state

- p_fail: conditions 89%, site state 11%
- floor_violation_s: conditions 96%, site state 4%

## Caveats

- 34% of events have an input outside the surrogate's training range.
- Failure rate is 99.3%: P(fail) cannot be ranked meaningfully, so the headline ranking uses floor_violation_s.
- Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.
- The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).
- Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.
- Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.
- Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.
- Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.
