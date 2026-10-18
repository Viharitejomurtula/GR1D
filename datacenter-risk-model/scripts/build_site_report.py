"""Build reports/site_abilene.md and site/abilene/site_params.json: site calibration vs the frozen public baseline (frozen/v1_public_baseline)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
J = lambda p: json.load(open(ROOT / p))
prof = J("site/abilene/site_profile.json"); gs = J("site/abilene/gpu_sync_site.json"); HT = J("models/heat_trend_abilene.json"); RC = J("models/reality_check.json")
Tb, Ts = J("frozen/v1_public_baseline/models/temperature_params.json")["stations"], J("models/temperature_params_abilene.json")["stations"]["USW00013962"]
Wb, Ws = J("frozen/v1_public_baseline/models/wetbulb_params.json")["stations"], J("models/wetbulb_params_abilene.json")["stations"]["USW00013962"]
ov = J("models/frequency_event_model.json")["over_frequency"]; vd = J("models/voltage_dip_params.json")["locations"]["transmission"]
f = lambda x, n=1: f"{x:.{n}f}"
q = lambda a: " / ".join(f"{v:.1f}" for v in a)
L = []; A = L.append
A("# Reference campus (Abilene, TX, ERCOT West): site calibration vs frozen public baseline\n")
A("**This is a reference campus built from public information. It is not the operator's actual equipment or design, and nothing here is a claim about any real facility's hardware, protection or performance.**\n")
A("Baseline = `frozen/v1_public_baseline` (unchanged). Everything here is labelled OBSERVED, DERIVED (from observed data), SCENARIO (an input the operator must confirm) or UNCHANGED (no site data yet).\n")
A("## 1. Reference-campus definition (verification status)\n")
V = prof["verified_from_primary_pages"]
A(f"Verified by reading the company/contractor pages directly ({V['note']}):")
for k_, v_ in V.items():
    if k_ != "note":
        A(f"- **{k_.replace('_', ' ')}:** {v_['statement']} (source: {v_['source']})")
NV = prof["not_verified_do_not_present"]
A("\nNot verified, so not used or not to be presented on slides:")
for k_, v_ in NV.items():
    if k_ != "not_found_publicly":
        A(f"- **{k_.replace('_', ' ')}:** {v_}")
A(f"- **Not available from public sources at all:** {', '.join(NV['not_found_publicly'])}.")
SI = prof["scenario_inputs"]
A(f"- Scenario inputs: weather station {SI['weather_station']}; voltage class {SI['voltage_dip_class']}; load {SI['load_scenarios_mw']} MW (200 and 1,200 MW are stated phase/total capacities; 600 MW is an illustrative midpoint, not a site claim); training share {SI['training_share_of_load']} (assumed).\n")
A("## 2. Weather (DERIVED from observed KABI data, 1930-2026)\n")
b = Tb["USW00013904"]
rs, rb = Ts["annual_max"]["return_levels_c"], b["annual_max"]["return_levels_c"]
A("| | Austin (baseline) | Abilene (site) |\n|---|---|---|")
A(f"| August 15:00 dry-bulb quantiles 1/5/25/50/75/95/99% (C) | {q(b['body_month_hour']['08-15']['q'])} | {q(Ts['body_month_hour']['08-15']['q'])} |")
A(f"| January 06:00 dry-bulb quantiles (C) | {q(b['body_month_hour']['01-06']['q'])} | {q(Ts['body_month_hour']['01-06']['q'])} |")
A(f"| hot-hour return levels 10/50/100 y, stationary fit (C) | {rb['10y']['est']}/{rb['50y']['est']}/{rb['100y']['est']} | {rs['10y']['est']}/{rs['50y']['est']}/{rs['100y']['est']} (100-y CI {rs['100y']['ci95'][0]}-{rs['100y']['ci95'][1]}) |")
wb, ws = Wb["USW00013904"], Ws
A(f"| August 15:00 wet-bulb quantiles (C) | {q(wb['body_month_hour']['08-15']['q'])} | {q(ws['body_month_hour']['08-15']['q'])} |")
A(f"| wet-bulb return levels 10/50/100 y (C) | {wb['annual_max']['return_levels_c']['10y']['est']}/{wb['annual_max']['return_levels_c']['50y']['est']}/{wb['annual_max']['return_levels_c']['100y']['est']} | {ws['annual_max']['return_levels_c']['10y']['est']}/{ws['annual_max']['return_levels_c']['50y']['est']}/{ws['annual_max']['return_levels_c']['100y']['est']} |")
A(f"| Jul-Aug hours with wet-bulb > 25 C | {f(wb['jul_aug_frac_hours_tw_gt_25']*100)}% | {f(ws['jul_aug_frac_hours_tw_gt_25']*100)}% |")
A(f"| annual-mean trend (C/decade) | {b['annual_mean_trend_c_per_decade']} | {Ts['annual_mean_trend_c_per_decade']} |")
A(f"- Site body distribution uses 2011-2025 (the warming trend and backtest below show older windows understate present heat). Non-stationary extremes (KABI annual maxima, location trend {HT['trend']['mu1_per_year']:.3f} C/yr, 95% CI {HT['trend']['mu1_ci95'][0]}-{HT['trend']['mu1_ci95'][1]}; AIC {HT['trend']['aic']:.0f} vs {HT['stationary']['aic']:.0f} stationary): hot-hour return levels in 2026 for 10/50/100 years = {HT['return_levels_c']['10y_in_2026']['est']}/{HT['return_levels_c']['50y_in_2026']['est']}/{HT['return_levels_c']['100y_in_2026']['est']} C; 2040 projection (trend extrapolation) {HT['return_levels_c']['10y_in_2040']['est']}/{HT['return_levels_c']['50y_in_2040']['est']}/{HT['return_levels_c']['100y_in_2040']['est']} C.")
A("- **Cooling-relevant exposure (dry-bulb hours per year; the campus uses air-cooled chillers on a closed liquid loop, so dry-bulb, not wet-bulb, sets heat-rejection limits):**")
A("| threshold | mean 2000-2025 | first decade mean | last decade mean | fitted 2026 | worst year |\n|---|---|---|---|---|---|")
for t_, v_ in RC["kabi_hours_per_year_above_dry_bulb"].items():
    A(f"| > {t_} C | {v_['mean']:.0f} h | {v_['first10_mean']:.0f} h | {v_['last10_mean']:.0f} h | {HT['hours_above_dry_bulb'][t_]['fitted_2026']:.0f} h | {v_['max']} h |")
A("- Reading: Abilene's dry-bulb extremes match Austin's but are rising: hours above 40 C roughly quadrupled between the first and last decade. Wet-bulb is much lower than Austin (above 25 C in ~2% of summer hours vs 17%), but because Crusoe states it uses air-cooled chillers rather than evaporative cooling, wet-bulb is not the limiting variable; chiller capacity at 40-44 C ambient is. A spike filter (>6 C from the 5-hour median) removed 0.4% of KABI hours (including impossible 45-47 C readings in April 2022) and a 27 C dew-point cap removed 8 hours; neither affects the frozen Austin/Dallas-Fort Worth results. KABI is an airport station; the campus microclimate and on-site heat sources are not represented.\n")
A("## 3. Grid frequency (UNCHANGED system-wide; site as a source of events)\n")
A("- ERCOT frequency is one interconnection-wide quantity: the baseline body, event, trend and systemic-regime models apply unchanged to the site. No site-specific frequency measurement was found.")
A(f"- **The campus as a load-loss source** (DERIVED from ERCOT's own over-frequency events, n={ov['n']}; excess = exp({f(ov['log_excess_intercept'],2)}) x MW^{f(ov['log_excess_slope'],2)}, sigma {f(ov['resid_sigma'],2)} in log): if the whole campus trips off at once, the expected peak frequency is")
A("| load lost | expected peak (Hz) | +/-1 sigma |\n|---|---|---|")
for mw in (200, 600, 1200):
    e = float(np.exp(ov["log_excess_intercept"]) * mw ** ov["log_excess_slope"]); s = ov["resid_sigma"]
    A(f"| {mw} MW | {60 + e:.3f} | {60 + e * np.exp(-s):.3f}-{60 + e * np.exp(s):.3f} |")
A("- Check: ERCOT's observed 1,560 MW loss produced 60.235 Hz; the fit gives 60.22. These are single-instant total losses; partial ride-through reduces them, and the campus's behind-the-meter battery storage and gas backup (capacities not public) could change this and are not modelled.\n")
A("## 4. Voltage dips (CLASS from EPRI; West Texas evidence SCENARIO-level)\n")
d = vd["depth_bins_rate_per_year"]
A(f"- Class: transmission (138/345 kV). EPRI median rates per year: {d['0.70-0.80pu']} (0.7-0.8 pu), {d['0.50-0.70pu']} (0.5-0.7 pu), {d['<0.50pu']} (<0.5 pu); site-to-site lognormal sigma {vd['site_rate_lognormal_sigma']}.")
A("- West Texas evidence (ERCOT PDCWG Nov 2024 large-load deck): documented fault events that cut large loads: Oct 2022 West Texas (3LG, 138 kV, delayed ~10-cycle clearing, 415-500 MW), Dec 2022 Far West (19-cycle clearing, ~1,560 MW), Jan and Oct 2023 West Texas (single-line-to-ground, 3-4 cycle clearing), plus 19 power-electronics ride-through events Nov 2023 - Oct 2024 (7 West/McCamey, 4 Far West, 8 Central). ERCOT also reports SLG faults cutting loads at dips as shallow as 0.85 pu and warns of >1,000 MW reductions for 345 kV faults in Far West Texas.")
A("- Reading: ERCOT counted 11 fault events (7 West, 4 Far West) that cut large power-electronics loads in the ~12 months from Nov 2023 (regional, not at this site), comparable to or above the EPRI transmission median of 9.0 sags/yr below 0.8 pu. This supports using the EPRI transmission class with an elevated-rate scenario (multiplier 1.0-2.0, SCENARIO) instead of a fitted site rate. Duration evidence from the same deck (3-4 cycles normal, 10-19 delayed) is already in the sampler defaults. Whether a given dip drops the campus load depends on its own ride-through design (NOT KNOWN; ERCOT notes large unit-to-unit variance at similar dips).\n")
A("## 5. AI load swing at site scale (OBSERVED shapes and job sizes; scale, kW/GPU and rho are SCENARIO)\n")
A(f"- Hardware (public statements): GB200 NVL72 racks, ~120-132 kW per 72 GPUs, i.e. ~1.7-1.8 kW/GPU rack-level; scenarios use 1.25 / 1.75 / 2.25 kW per GPU. Method: facility Monte Carlo (`scripts/site_gpu_sync.py`): job sizes from Alibaba, normalized H100 training power shapes from NLR, training share {gs['training_share']} (assumed). Hardware statement and kW/GPU come from public pages (GB200 NVL72); the shapes remain H100-based. Corrects the baseline's rule of thumb: swing scales ~linearly with size only when jobs are aligned.")
A("| IT load | kW/GPU | rho (fraction of jobs sharing phase) | training mean (MW) | swing p99-p1 (MW) | 1 s ramp p99 / p99.9 (MW/s) |\n|---|---|---|---|---|---|")
for load in (200, 600, 1200):
    for kw in (1.75,):
        for rho in (0.0, 0.25, 1.0):
            r = gs["results"].get(f"load{load}MW_kwgpu{kw}_rho{rho}")
            if r:
                A(f"| {load} MW | {kw} | {rho} | {r['mean_training_mw']} | {r['swing_p99_p1_mw']} | {r['ramp_1s_p99_mw_per_s']} / {r['ramp_1s_p999_mw_per_s']} |")
r0, r25, r1 = (gs["results"][f"load200MW_kwgpu1.75_rho{x}"] for x in (0.0, 0.25, 1.0))
A(f"- Reading: the result is dominated by rho, which no public data constrains. At the 200 MW phase (1.75 kW/GPU, GB200 NVL72 class) the aggregate training swing is ~{r0['swing_p99_p1_mw']:.0f} MW if jobs are independent, ~{r25['swing_p99_p1_mw']:.0f} MW if a quarter share phase and ~{r1['swing_p99_p1_mw']:.0f} MW (about {r1['swing_p99_p1_mw']/r1['mean_training_mw']:.1f}x mean training power) if all align; kW per GPU (hardware generation) matters far less (compare the 1.25 and 2.25 kW/GPU runs in `site/abilene/gpu_sync_site.json`). Real scheduler/PDU telemetry from the operator is the only way to narrow this. Ramps are the numbers that stress UPS/BESS and grid-interconnection limits.\n")
A("## 6. Factors still on proxies (UNCHANGED until site/vendor data arrive)\n")
A("- Battery capacity/resistance (NASA small cells, CALCE NMC DC level), DC-link capacitor (NASA electrolytic). UPS/BESS and capacitor hardware at the campus are not public in the sources found.\n- Utilization: the Alibaba fleet (22% SM utilization, mixed light-inference workloads) is NOT representative of a dedicated training campus. Transfer check: it implies mean node power at 38% of peak, while measured training nodes (NLR) run at 84% of their 95th-percentile power, a factor of 2.2. For this site use the training-like fraction.\n")
A("## 7. Needed from the operator/TSP to finish calibration\n")
A("1. Confirmed coordinates and point of interconnection (voltage, short-circuit strength, protection clearing times, fault history at the bus).\n2. Facility one-line diagram: UPS/BESS chemistry, ratings and cycling duty; DC-link capacitor part and temperature.\n3. GPU generation and per-GPU all-in power; scheduler logs or PDU-level 1 s power traces to estimate rho.\n4. Ride-through/voltage-dip tolerance of power supplies and UPS (test curves).\n5. On-site gas generation operating mode (islandable? ramp rates).\n6. Cooling design (dry vs evaporative; setpoints) to convert the wet-bulb results into limits.\n")
(ROOT / "reports/site_abilene.md").write_text("\n".join(L))
json.dump(dict(site=prof["name"], baseline="frozen/v1_public_baseline", weather_params="models/temperature_params_abilene.json, models/wetbulb_params_abilene.json",
               gpu_sync_site="site/abilene/gpu_sync_site.json", voltage_dip_rate_multiplier_scenario=[1.0, 2.0]), open(ROOT / "site/abilene/site_params.json", "w"), indent=1)
print("written", sum(map(len, L)))
