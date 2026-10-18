"""Build reports/data_request.md: operator data requests ranked by how much each would tighten the outputs (uses the sensitivity results where they exist)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = lambda p: json.load(open(ROOT / p))
gs = J("site/abilene/gpu_sync_site.json")["results"]; RC = J("models/reality_check.json"); FE = J("models/frequency_event_model.json")["systemic_stress_regime"]; CP = J("models/capacitor_degradation_params.json")["groups"]
r0, r1 = gs["load200MW_kwgpu1.75_rho0.0"], gs["load200MW_kwgpu1.75_rho1.0"]
u = RC["utilization_transfer_gap"]
L = []; A = L.append
A("# What data to ask the operator for, ranked by effect on the results\n")
A("The tool tells operators which data to share: each request below names the model input it pins down and, where our sensitivity results exist, how much output spread it would remove. Items marked JUDGMENT are not in the model yet, so no sensitivity number exists for them; they are ranked by their role in turning grid events into failures, and become quantifiable once provided.\n")
A("| Rank | Data | Pins down | Spread today (our results) | Basis |\n|---|---|---|---|---|")
A(f"| 1 | **PSU / IT loading: scheduler logs and PDU or rack power traces** (1 s or finer, at least 2 weeks, including job starts/stops and checkpoints; job sizes) | cross-job phase sharing (rho); mean power fraction; PSU load distribution | campus training swing at 200 MW {r0['swing_p99_p1_mw']:.0f} to {r1['swing_p99_p1_mw']:.0f} MW (x{r1['swing_p99_p1_mw']/r0['swing_p99_p1_mw']:.0f}); 1 s ramp p99.9 {r0['ramp_1s_p999_mw_per_s']:.1f} to {r1['ramp_1s_p999_mw_per_s']:.0f} MW/s; mean power x{u['ratio_training_to_alibaba']:.1f} utilization transfer gap | MEASURED sensitivity (largest operator-side spread) |")
A("| 2 | **UPS / BBU converter limits**: maximum power ramp rate, overload rating and duration, battery discharge power limit, bypass/transfer windows | whether a load swing or grid event is absorbed or becomes a trip | not in the model | JUDGMENT |")
A("| 3 | **Restart surge**: inrush and restart ramp after a trip or dip, staggering/sequencing | size and timing of the load re-pick (a second event after a dip) | not in the model | JUDGMENT |")
A("| 4 | **Rail droop and board undervoltage settings**: DC-bus droop per load step, undervoltage trip thresholds and delays, PSU hold-up time, ride-through test curves | which voltage dips (depth, duration, phases) cause load loss | dip rate known to within about 1-2x; impact (depth, duration, phases, ride-through) unconstrained | JUDGMENT (rate is from data) |")
A("| 5 | **Fault and protection records at the point of interconnection**: clearing times (normal vs delayed), 12 months of recorded dips or fault history | dip rate multiplier, duration mixture | rate multiplier 1 to 2 (scenario); durations 3-5 cycles normal, 10-20 delayed | MEASURED range |")
A(f"| 6 | **DC-link capacitor specifications** (type, rated and operating voltage, temperature, ripple current, vendor life curves) | capacitor degradation transfer | 5000 h loss {CP['10V']['loss_5000h_mean']*100:.1f}% to {CP['14V']['loss_5000h_mean']*100:.1f}% across stress levels before any film transfer; but the capacitor sits at its mid value in the headline results because its propagation to failures was not tested | LOWER priority (operator judgment); effect on outcomes untested |")
A("| 7 | UPS/BESS battery chemistry, capacity and cycling duty; chiller capacity vs ambient (derating curve at 40-44 C) | battery aging basis; cooling margin as hours above 40 C rise | battery lifetimes proxy-based (100-250 cycles); hours above 40 C rising | lower |\n")
A("## How the ranking was made\n")
A("- Items 1 and 5 have measured spreads from the sensitivity analysis. Items 2-4 are the equipment-level limits that decide whether an event becomes a failure; they are not modelled yet, so the ranking is judgment, not a sensitivity result. Item 6 is placed low on the operator's guidance; our own result shows a 3.4x stress spread, and how it propagates to outcomes has not been tested.")
A(f"- Grid-side uncertainties that no operator can supply (systemic grid-stress event rate {FE['rate_ci95'][0]} to {FE['rate_ci95'][1]} per year) are reported as low/mid/high scenarios, never fixed to a default.")
(ROOT / "reports/data_request.md").write_text("\n".join(L)); print("written")
