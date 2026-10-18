# Product performance and failure drivers: legacy_ups

Unit: one grid event hitting one site. 100,000 events, seed 0.

> **Scope: results cover only grid dips that retain 0.70-0.90 pu of nominal voltage (about 69% of sags).** Every figure below is conditional on such a dip. Deeper sags (below 0.70 pu) are out of scope: they are unassessed, counted neither as pass nor as fail. The simulator's deep-sag voltage-collapse problem is still open (validation/CROSSCHECK.md).

## Performance

- Probability an event fails: **93.8%** (Monte Carlo 95% interval 93.8% to 93.9%).
- By ensemble member: 89.8%, 95.6%, 93.7%, 94.9%, 95.3% (surrogate disagreement).
- Surrogate model: v1 (torch-ensemble, surrogate/models/v1, trained_rows 10000, simulator_commit c929a84661ead35c8b9b2b13c779550894697f0f).
- Events that almost surely fail (P>0.9): 81.6%; almost surely pass (P<0.1): 0.0%.

How events fail (share of all events):

- below power floor: 73.4%
- storage hand-back too slow: 11.7%
- exceeded 150% current cap: 6.8%
- cooling tripped: 0.8%
- PSU shutdown and restart delay: 0.8%
- voltage collapse: 0.0%
- missed 2.0 s recovery: 0.0%

| measure | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| min_power | 0.123 | 0.192 | 0.234 | 0.263 | 0.295 |
| peak_current_pu | 1.09 | 1.13 | 1.19 | 1.32 | 1.5 |
| floor_violation_s | 0.041 | 0.0983 | 0.157 | 0.235 | 0.401 |
| recovery_margin_s | -2.28 | -0.427 | 0.566 | 1.34 | 1.85 |

## Group A: conditions (what the grid and weather do)

Ranked on **p_fail**:

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0936 | 57% | 0.699 to 0.74 (1) | 1-1 |
| 2 | Workload type (power-swing size and rate) | 0.0176 | 11% | no clear difference | 2-3 |
| 3 | Reclosing (second dip and gap) | 0.0170 | 10% | no clear difference | 2-3 |
| 4 | Season and outdoor temperature | 0.0141 | 9% | no clear difference | 4-4 |
| 5 | Site load level | 0.0099 | 6% | no clear difference | 5-5 |
| 6 | Fault type (phases involved) | 0.0090 | 5% | no clear difference | 6-6 |
| 7 | Protection clearing (normal / breaker problem) | 0.0037 | 2% | no clear difference | 7-7 |

Strongest pairwise interactions: dip_depth+workload_type (0.0275); dip_depth+reclose (0.0271); dip_depth+weather (0.0218).

## Group B: site state (what the equipment is like)

Ranked on **p_fail**:

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Cooling plant makeup (compressor vs fan share) | 0.0085 | 42% | no clear difference | 1-1 |
| 2 | Battery hall temperature | 0.0043 | 22% | no clear difference | 2-3 |
| 3 | Battery state of charge | 0.0040 | 20% | no clear difference | 2-3 |
| 4 | Equipment age | 0.0027 | 14% | no clear difference | 4-4 |
| 5 | Compressor restart time | 0.0005 | 2% | no clear difference | 5-5 |

Strongest pairwise interactions: battery_soc+cooling_makeup (0.0018); battery_age+battery_temp (0.0007); battery_temp+cooling_makeup (0.0006).

## Conditions versus site state

- p_fail: conditions 90%, site state 10%

## Caveats

- 100% of events have an input outside the surrogate's training range.
- Scope: Results cover only grid dips retaining 0.70-0.90 pu (about 69% of sags, Eaton/EPRI); every figure is conditional on that. Deeper sags are out of scope: unassessed, neither pass nor fail (the simulator's deep-sag voltage-collapse problem is open; validation/CROSSCHECK.md).
- Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.
- The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).
- Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.
- Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.
- Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.
- Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.
