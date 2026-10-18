# Product performance and failure drivers: legacy_ups

Unit: one grid event hitting one site. 100,000 events, seed 0.

> **Scope: results cover only grid dips that retain 0.70-0.90 pu of nominal voltage (about 69% of sags).** Every figure below is conditional on such a dip. Deeper sags (below 0.70 pu) are out of scope: they are unassessed, counted neither as pass nor as fail. The simulator's deep-sag voltage-collapse problem is still open (validation/CROSSCHECK.md).

## Performance

- Probability an event fails: **98.7%** (Monte Carlo 95% interval 98.6% to 98.7%).
- By ensemble member: 97.6%, 99.0%, 98.9%, 99.0%, 98.9% (surrogate disagreement).
- Surrogate model: v1 (torch-ensemble, surrogate/models/v1, trained_rows 20000, simulator_commit 15c9426a7544420f1aab74e9dac0e14bad5ba52e).
- Events that almost surely fail (P>0.9): 96.2%; almost surely pass (P<0.1): 0.0%.

How events fail (share of all events):

- exceeded 125% current cap: 70.3%
- below power floor: 24.7%
- storage hand-back too slow: 3.0%
- PSU shutdown and restart delay: 0.3%
- cooling tripped: 0.2%
- missed 2.0 s recovery: 0.0%

| measure | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| min_power | 0.147 | 0.216 | 0.256 | 0.287 | 0.383 |
| peak_current_pu | 1.22 | 1.32 | 1.39 | 1.45 | 1.53 |
| floor_violation_s | 0.0416 | 0.0701 | 0.104 | 0.176 | 0.378 |
| recovery_margin_s | 0.126 | 0.964 | 1.25 | 1.4 | 1.58 |

## Group A: conditions (what the grid and weather do)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0781 | 42% | 0.699 to 0.74 (0.221) | 1-1 |
| 2 | Reclosing (second dip and gap) | 0.0481 | 26% | 3.0 (0.233) | 2-2 |
| 3 | Protection clearing (normal / breaker problem) | 0.0369 | 20% | breaker_failure (0.308) | 3-3 |
| 4 | Season and outdoor temperature | 0.0085 | 5% | -18.3 to 11.7 (0.154) | 4-4 |
| 5 | Fault type (phases involved) | 0.0064 | 3% | 3LG (0.181) | 5-5 |
| 6 | Site load level | 0.0052 | 3% | 0.204 to 0.39 (0.149) | 6-6 |
| 7 | Workload type (power-swing size and rate) | 0.0042 | 2% | no clear difference | 7-7 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0201 | 43% | no clear difference | 1-1 |
| 2 | Site load level | 0.0076 | 16% | no clear difference | 2-3 |
| 3 | Workload type (power-swing size and rate) | 0.0072 | 15% | no clear difference | 2-3 |
| 4 | Reclosing (second dip and gap) | 0.0058 | 12% | no clear difference | 4-4 |
| 5 | Fault type (phases involved) | 0.0023 | 5% | no clear difference | 5-5 |
| 6 | Season and outdoor temperature | 0.0018 | 4% | no clear difference | 6-7 |
| 7 | Protection clearing (normal / breaker problem) | 0.0018 | 4% | no clear difference | 6-7 |

Strongest pairwise interactions: dip_depth+reclose (0.0300); protection+dip_depth (0.0112); dip_depth+weather (0.0104).

## Group B: site state (what the equipment is like)

Ranked on **floor_violation_s** (P(fail) is saturated):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Equipment age | 0.0053 | 33% | no clear difference | 1-2 |
| 2 | Cooling plant makeup (compressor vs fan share) | 0.0052 | 32% | no clear difference | 1-2 |
| 3 | Battery state of charge | 0.0034 | 21% | no clear difference | 3-3 |
| 4 | Battery hall temperature | 0.0016 | 10% | no clear difference | 4-4 |
| 5 | Compressor restart time | 0.0007 | 4% | no clear difference | 5-5 |

Ranked on P(fail):

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Cooling plant makeup (compressor vs fan share) | 0.0018 | 31% | no clear difference | 1-1 |
| 2 | Equipment age | 0.0015 | 26% | no clear difference | 2-2 |
| 3 | Battery state of charge | 0.0011 | 19% | no clear difference | 3-3 |
| 4 | Battery hall temperature | 0.0008 | 13% | no clear difference | 4-4 |
| 5 | Compressor restart time | 0.0006 | 10% | no clear difference | 5-5 |

Strongest pairwise interactions: battery_age+battery_temp (0.0010); battery_soc+cooling_makeup (0.0007); battery_age+cooling_makeup (0.0006).

## Conditions versus site state

- p_fail: conditions 88%, site state 12%
- floor_violation_s: conditions 93%, site state 7%

## Caveats

- 100% of events have an input outside the surrogate's training range.
- Failure rate is 98.7%: P(fail) cannot be ranked meaningfully, so the headline ranking uses floor_violation_s.
- Scope: Results cover only grid dips retaining 0.70-0.90 pu (about 69% of sags, Eaton/EPRI); every figure is conditional on that. Deeper sags are out of scope: unassessed, neither pass nor fail (the simulator's deep-sag voltage-collapse problem is open; validation/CROSSCHECK.md).
- Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.
- The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).
- Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.
- Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.
- Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.
- Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.
