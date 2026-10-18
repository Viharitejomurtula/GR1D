# Product performance and failure drivers: grid_friendly

Unit: one grid event hitting one site. 100,000 events, seed 0.

> **Scope: results cover only grid dips that retain 0.70-0.90 pu of nominal voltage (about 69% of sags).** Every figure below is conditional on such a dip. Deeper sags (below 0.70 pu) are out of scope: they are unassessed, counted neither as pass nor as fail. The simulator's deep-sag voltage-collapse problem is still open (validation/CROSSCHECK.md).

## Performance

- Probability an event fails: **93.3%** (Monte Carlo 95% interval 93.2% to 93.4%).
- By ensemble member: 91.4%, 92.8%, 94.7%, 94.8%, 92.6% (surrogate disagreement).
- Surrogate model: v1 (torch-ensemble, surrogate/models/v1, trained_rows 10000, simulator_commit c929a84661ead35c8b9b2b13c779550894697f0f).
- Events that almost surely fail (P>0.9): 79.6%; almost surely pass (P<0.1): 0.0%.

How events fail (share of all events):

- below power floor: 70.7%
- storage hand-back too slow: 10.6%
- exceeded 150% current cap: 9.7%
- PSU shutdown and restart delay: 0.9%
- cooling tripped: 0.9%
- voltage collapse: 0.0%
- missed 2.0 s recovery: 0.0%

| measure | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| min_power | 0.155 | 0.222 | 0.264 | 0.292 | 0.365 |
| peak_current_pu | 1.14 | 1.18 | 1.24 | 1.34 | 1.49 |
| floor_violation_s | 0.0308 | 0.0698 | 0.116 | 0.183 | 0.33 |
| recovery_margin_s | -0.131 | 0.361 | 0.802 | 1.22 | 1.61 |

## Group A: conditions (what the grid and weather do)

Ranked on **p_fail**:

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Sag depth | 0.0991 | 56% | 0.699 to 0.74 (1) | 1-1 |
| 2 | Workload type (power-swing size and rate) | 0.0226 | 13% | no clear difference | 2-2 |
| 3 | Reclosing (second dip and gap) | 0.0176 | 10% | no clear difference | 3-3 |
| 4 | Fault type (phases involved) | 0.0156 | 9% | no clear difference | 4-5 |
| 5 | Site load level | 0.0146 | 8% | no clear difference | 4-5 |
| 6 | Season and outdoor temperature | 0.0050 | 3% | no clear difference | 6-6 |
| 7 | Protection clearing (normal / breaker problem) | 0.0033 | 2% | no clear difference | 7-7 |

Strongest pairwise interactions: dip_depth+workload_type (0.0335); dip_depth+reclose (0.0269); fault_type+dip_depth (0.0235).

## Group B: site state (what the equipment is like)

Ranked on **p_fail**:

| # | driver | importance | share | worst level (mean outcome) | rank 90% range |
|---|---|---|---|---|---|
| 1 | Cooling plant makeup (compressor vs fan share) | 0.0086 | 40% | no clear difference | 1-1 |
| 2 | Equipment age | 0.0046 | 21% | no clear difference | 2-2 |
| 3 | Battery state of charge | 0.0034 | 16% | no clear difference | 3-3 |
| 4 | Battery hall temperature | 0.0029 | 13% | no clear difference | 4-4 |
| 5 | Compressor restart time | 0.0019 | 9% | no clear difference | 5-5 |

Strongest pairwise interactions: battery_soc+cooling_makeup (0.0014); battery_age+battery_temp (0.0009); battery_temp+cooling_makeup (0.0007).

## Conditions versus site state

- p_fail: conditions 90%, site state 10%

## Caveats

- Scope: Results cover only grid dips retaining 0.70-0.90 pu (about 69% of sags, Eaton/EPRI); every figure is conditional on that. Deeper sags are out of scope: unassessed, neither pass nor fail (the simulator's deep-sag voltage-collapse problem is open; validation/CROSSCHECK.md).
- Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.
- The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).
- Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.
- Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.
- Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.
- Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.
