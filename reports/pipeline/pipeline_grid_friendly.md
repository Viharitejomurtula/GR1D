# Product performance and failure drivers: grid_friendly

Unit: one grid event hitting one site. 100,000 events, seed 0.

> **Scope: results cover only grid dips that retain 0.70-0.90 pu of nominal voltage (about 69% of sags).** Every figure below is conditional on such a dip. Deeper sags (below 0.70 pu) are out of scope: they are unassessed, counted neither as pass nor as fail. The simulator's deep-sag voltage-collapse problem is still open (validation/CROSSCHECK.md).

## Performance

- Probability an event fails: **98.4%** (Monte Carlo 95% interval 98.4% to 98.4%).
- By ensemble member: 97.9%, 98.6%, 98.7%, 98.6%, 98.3% (surrogate disagreement).
- Surrogate model: v1 (torch-ensemble, surrogate/models/v1, trained_rows 20000, simulator_commit 15c9426a7544420f1aab74e9dac0e14bad5ba52e).
- Events that almost surely fail (P>0.9): 95.3%; almost surely pass (P<0.1): 0.0%.

How events fail (share of all events):

- exceeded 125% current cap: 72.9%
- below power floor: 22.8%
- storage hand-back too slow: 2.0%
- cooling tripped: 0.5%
- PSU shutdown and restart delay: 0.1%
- missed 2.0 s recovery: 0.0%

| measure | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| min_power | 0.147 | 0.221 | 0.261 | 0.322 | 0.539 |
| peak_current_pu | 1.2 | 1.33 | 1.41 | 1.47 | 1.56 |
| floor_violation_s | 0.0241 | 0.0583 | 0.0853 | 0.147 | 0.323 |
| recovery_margin_s | 0.912 | 1.29 | 1.42 | 1.56 | 1.8 |

## Group A: conditions (what the grid and weather do)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0702 | 42% | 0.699 to 0.74 (0.185) | 1-1 |
| 2 | Reclosing (second dip and gap) | 0.0408 | 25% | 3.0 (0.196) | 2-2 |
| 3 | Protection clearing (normal / breaker problem) | 0.0307 | 18% | breaker_failure (0.255) | 3-3 |
| 4 | Season and outdoor temperature | 0.0078 | 5% | -18.3 to 11.7 (0.128) | 4-4 |
| 5 | Site load level | 0.0061 | 4% | no clear difference | 5-6 |
| 6 | Fault type (phases involved) | 0.0058 | 3% | 3LG (0.152) | 5-6 |
| 7 | Workload type (power-swing size and rate) | 0.0050 | 3% | no clear difference | 7-7 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0247 | 45% | no clear difference | 1-1 |
| 2 | Workload type (power-swing size and rate) | 0.0104 | 19% | no clear difference | 2-2 |
| 3 | Site load level | 0.0059 | 11% | no clear difference | 3-4 |
| 4 | Reclosing (second dip and gap) | 0.0058 | 11% | no clear difference | 3-4 |
| 5 | Fault type (phases involved) | 0.0040 | 7% | no clear difference | 5-5 |
| 6 | Season and outdoor temperature | 0.0020 | 4% | no clear difference | 6-7 |
| 7 | Protection clearing (normal / breaker problem) | 0.0017 | 3% | no clear difference | 6-7 |

Strongest pairwise interactions: dip_depth+reclose (0.0269); protection+dip_depth (0.0112); dip_depth+weather (0.0104).

## Group B: site state (what the equipment is like)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Battery state of charge | 0.0040 | 31% | no clear difference | 1-1 |
| 2 | Cooling plant makeup (compressor vs fan share) | 0.0032 | 24% | no clear difference | 2-3 |
| 3 | Equipment age | 0.0031 | 24% | no clear difference | 2-3 |
| 4 | Battery hall temperature | 0.0025 | 19% | no clear difference | 4-4 |
| 5 | Compressor restart time | 0.0004 | 3% | no clear difference | 5-5 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Battery hall temperature | 0.0017 | 33% | no clear difference | 1-2 |
| 2 | Cooling plant makeup (compressor vs fan share) | 0.0016 | 31% | no clear difference | 1-2 |
| 3 | Equipment age | 0.0009 | 17% | no clear difference | 3-3 |
| 4 | Battery state of charge | 0.0007 | 14% | no clear difference | 4-4 |
| 5 | Compressor restart time | 0.0003 | 5% | no clear difference | 5-5 |

Strongest pairwise interactions: battery_age+battery_temp (0.0008); battery_age+cooling_makeup (0.0006); battery_temp+cooling_makeup (0.0006).

## Conditions versus site state

- p_fail: conditions 91%, site state 9%
- floor_violation_s: conditions 93%, site state 7%

## Caveats

- 33% of events have an input outside the surrogate's training range.
- Failure rate is 98.4%: P(fail) cannot be ranked meaningfully, so the headline ranking uses floor_violation_s.
- Scope: Results cover only grid dips retaining 0.70-0.90 pu (about 69% of sags, Eaton/EPRI); every figure is conditional on that. Deeper sags are out of scope: unassessed, neither pass nor fail (the simulator's deep-sag voltage-collapse problem is open; validation/CROSSCHECK.md).
- Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.
- The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).
- Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.
- Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.
- Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.
- Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.
