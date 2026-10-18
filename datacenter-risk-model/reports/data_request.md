# What data to ask the operator for, ranked by effect on the results

The tool tells operators which data to share: each request below names the model input it pins down and, where our sensitivity results exist, how much output spread it would remove. Items marked JUDGMENT are not in the model yet, so no sensitivity number exists for them; they are ranked by their role in turning grid events into failures, and become quantifiable once provided.

| Rank | Data | Pins down | Spread today (our results) | Basis |
|---|---|---|---|---|
| 1 | **PSU / IT loading: scheduler logs and PDU or rack power traces** (1 s or finer, at least 2 weeks, including job starts/stops and checkpoints; job sizes) | cross-job phase sharing (rho); mean power fraction; PSU load distribution | campus training swing at 200 MW 9 to 201 MW (x23); 1 s ramp p99.9 1.7 to 96 MW/s; mean power x2.2 utilization transfer gap | MEASURED sensitivity (largest operator-side spread) |
| 2 | **UPS / BBU converter limits**: maximum power ramp rate, overload rating and duration, battery discharge power limit, bypass/transfer windows | whether a load swing or grid event is absorbed or becomes a trip | not in the model | JUDGMENT |
| 3 | **Restart surge**: inrush and restart ramp after a trip or dip, staggering/sequencing | size and timing of the load re-pick (a second event after a dip) | not in the model | JUDGMENT |
| 4 | **Rail droop and board undervoltage settings**: DC-bus droop per load step, undervoltage trip thresholds and delays, PSU hold-up time, ride-through test curves | which voltage dips (depth, duration, phases) cause load loss | dip rate known to within about 1-2x; impact (depth, duration, phases, ride-through) unconstrained | JUDGMENT (rate is from data) |
| 5 | **Fault and protection records at the point of interconnection**: clearing times (normal vs delayed), 12 months of recorded dips or fault history | dip rate multiplier, duration mixture | rate multiplier 1 to 2 (scenario); durations 3-5 cycles normal, 10-20 delayed | MEASURED range |
| 6 | **DC-link capacitor specifications** (type, rated and operating voltage, temperature, ripple current, vendor life curves) | capacitor degradation transfer | 5000 h loss 6.8% to 23.0% across stress levels before any film transfer; but the capacitor sits at its mid value in the headline results because its propagation to failures was not tested | LOWER priority (operator judgment); effect on outcomes untested |
| 7 | UPS/BESS battery chemistry, capacity and cycling duty; chiller capacity vs ambient (derating curve at 40-44 C) | battery aging basis; cooling margin as hours above 40 C rise | battery lifetimes proxy-based (100-250 cycles); hours above 40 C rising | lower |

## How the ranking was made

- Items 1 and 5 have measured spreads from the sensitivity analysis. Items 2-4 are the equipment-level limits that decide whether an event becomes a failure; they are not modelled yet, so the ranking is judgment, not a sensitivity result. Item 6 is placed low on the operator's guidance; our own result shows a 3.4x stress spread, and how it propagates to outcomes has not been tested.
- Grid-side uncertainties that no operator can supply (systemic grid-stress event rate 0.028 to 0.435 per year) are reported as low/mid/high scenarios, never fixed to a default.