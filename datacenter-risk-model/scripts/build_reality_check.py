"""Build reports/reality_check.md: how close are the distributions to real-world behaviour? Numbers read from models/*.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = lambda p: json.load(open(ROOT / p))
RC, V, HT = J("models/reality_check.json"), J("models/validation.json"), J("models/heat_trend_abilene.json")
FE, BC, CP, GS = J("models/frequency_event_model.json"), J("models/battery_capacity_params.json"), J("models/capacitor_degradation_params.json"), J("site/abilene/gpu_sync_site.json")
f = lambda x, n=2: f"{x:.{n}f}"
L = []; A = L.append
A("# How close are the distributions to the real world?\n")
A("Method: (1) backtests on data the model never saw, where such data exists; (2) transfer-gap checks where the data come from a different system than the target; (3) the spread of the output across plausible values of each unobservable assumption. The last is the honest measure for the factors no data can validate. Nothing here is a measurement of any real campus; the reference campus is built from public information: no site data (power traces, protection records, UPS/battery specs) was obtainable from public sources.\n")
A("## 1. Backtests against held-out real data\n")
a, b = RC["kabi_dry_bulb_holdout_2016_2026"], RC["kabi_annual_max_holdout"]
A(f"- **Abilene dry-bulb (fit 1996-2015, test 2016-2026, {a['n_test']:,} hours):** the 5-95% band covered {f(a['cov_5_95'])} of hours (nominal 0.90), the 25-75% band {f(a['cov_25_75'])} (0.50); the test decade was {f(a['mean_shift_c'],1)} C warmer and {f(a['frac_above_p95']*100,1)}% of hours exceeded the old 95th percentile (nominal 5%). **Typical hours: good. Warming: not captured by a stationary window.**")
A(f"- **Abilene extreme heat:** a stationary extreme-value fit on 1949-2015 gave a 10-year level of {f(b['fitted_10y_level_c'],1)} C; {b['test_years_exceeding_10y_level']} of the next {b['test_years']} years exceeded it (expected {f(b['expected_in_test'],1)}); the test-period maximum was {f(b['test_max_c'],1)} C vs {f(b['train_max_c'],1)} C before. **The stationary model failed on extremes.** The site model now uses a trend (location +{HT['trend']['mu1_per_year']:.3f} C/yr, AIC {HT['trend']['aic']:.0f} vs {HT['stationary']['aic']:.0f}) and a 2011-2025 body window.")
fe = RC["frequency_events_vs_recent_years"]
A(f"- **ERCOT frequency events vs 2024 and Jan-Sep 2025 (model at the current response level):** events per year model {f(fe['2024']['events_per_year']['model'],1)} vs observed {f(fe['2024']['events_per_year']['observed'],1)} (2024) and {f(fe['2025_Jan_Sep']['events_per_year']['observed'],1)} (2025); nadir below 59.9 Hz per year: model {f(fe['2024']['59.9']['model'],1)} vs observed {f(fe['2024']['59.9']['observed'],1)} (2024) and {f(fe['2025_Jan_Sep']['59.9']['observed'],1)} (2025); below 59.85 Hz: model {f(fe['2024']['59.85']['model'])} vs {f(fe['2024']['59.85']['observed'])} / {f(fe['2025_Jan_Sep']['59.85']['observed'])}. **Within about a factor of 2 of 2024 and conservative against 2025, as the grid keeps improving.** A model trained on 2018-2022 over-predicted later years 3-10x, so the response level must be re-estimated yearly.")
A(f"- **Frequency body:** pooled RMS {f(V['frequency_body']['pooled_rms_mhz'],1)} mHz vs ERCOT's published 2023 monthly range 12.5-18.2 mHz (inside); only 5 days of 1 s data, so shape beyond the central range is unchecked.")
A(f"- **Battery fade, capacitor loss, AI-swing repeats:** leave-one-cell-out {f(V['battery_capacity_leave_one_cell_out']['frac_in_5_95'])} inside the 5-95% band (nominal 0.90, n=10); capacitor leave-one-out {f(V['capacitor_leave_one_out_5000h']['frac_within_2sd'])} within 2 sd (0.95); AI swing even-vs-odd repeat KS median {f(V['ai_swing_even_vs_odd_repeats']['median_ks'])}. These show the fits describe the data they came from. They say nothing about whether the cells, capacitors and research-cluster runs resemble the target.\n")
A("## 2. Transfer gaps (proxy vs target)\n")
u = RC["utilization_transfer_gap"]
A(f"- **Utilization:** the Alibaba fleet (median SM utilization {f(u['alibaba_median_sm_util'])}, mixed light inference) implies node power at {f(u['implied_node_power_fraction_of_peak']*100,0)}% of peak; measured training nodes (NLR) run at {f(u['nlr_training_median_over_p95_power']*100,0)}% of their 95th-percentile power: a factor of {f(u['ratio_training_to_alibaba'],1)}. A dedicated training campus should use the training-like value, not the Alibaba fleet number.")
A(f"- **Voltage dips:** EPRI transmission median {RC['voltage_dips_plausibility']['epri_transmission_median_below_0_8pu']}/yr below 0.8 pu vs {RC['voltage_dips_plausibility']['ercot_west_far_west_load_affecting_fault_events_12mo']} ERCOT-counted load-affecting fault events in West/Far West in 12 months (ratio {f(RC['voltage_dips_plausibility']['ratio'],1)}): the same order of magnitude, but these are different quantities and say nothing about whether this campus rides through them.")
A("- **Battery:** the NASA cells age over 100-250 cycles; a facility UPS/BESS is specified for thousands of cycles and years of calendar aging. The fade model is a method template; absolute lifetimes do not transfer. The CALCE NMC cell gives a real fresh-cell DC resistance by temperature and SOC, but its aging growth was not measured.")
A("- **Capacitor:** electrolytic parts at 10-14 V overstress; the film DC-link part at the campus is not public. Absolute loss does not transfer.")
A("- **AI load shape:** normalized H100 training runs of 2-16 nodes are applied to GB200 NVL72 clusters of thousands of nodes. Lockstep inside a job is measured up to 16 nodes only.\n")
A("## 3. Spread of the output across plausible assumptions (what no data can validate)\n")
gs = GS["results"]
A("| unobservable input | plausible range | effect on output |\n|---|---|---|")
A(f"| cross-job phase sharing rho | 0 to 1 | campus training swing at 200 MW: {gs['load200MW_kwgpu1.75_rho0.0']['swing_p99_p1_mw']:.0f} to {gs['load200MW_kwgpu1.75_rho1.0']['swing_p99_p1_mw']:.0f} MW (x{gs['load200MW_kwgpu1.75_rho1.0']['swing_p99_p1_mw']/gs['load200MW_kwgpu1.75_rho0.0']['swing_p99_p1_mw']:.0f}); 1 s ramp p99.9 {gs['load200MW_kwgpu1.75_rho0.0']['ramp_1s_p999_mw_per_s']:.1f} to {gs['load200MW_kwgpu1.75_rho1.0']['ramp_1s_p999_mw_per_s']:.0f} MW/s |")
A(f"| kW per GPU (hardware) | 1.25 to 2.25 | swing changes only {gs['load200MW_kwgpu1.25_rho1.0']['swing_p99_p1_mw']:.0f} to {gs['load200MW_kwgpu2.25_rho1.0']['swing_p99_p1_mw']:.0f} MW at rho=1 (normalized shapes) |")
sy = FE["systemic_stress_regime"]
A(f"| systemic grid-stress regime rate | {sy['rate_ci95'][0]} to {sy['rate_ci95'][1]} per year (95%) | annual probability of nadir below 59.5 Hz from {sy['sensitivity_annual_probability_by_rate']['0.02']['P(year min nadir<59.5)']} (rate 0.02) to {sy['sensitivity_annual_probability_by_rate']['0.30']['P(year min nadir<59.5)']} (rate 0.30): x{sy['sensitivity_annual_probability_by_rate']['0.30']['P(year min nadir<59.5)']/sy['sensitivity_annual_probability_by_rate']['0.02']['P(year min nadir<59.5)']:.0f} |")
c10, c14 = CP["groups"]["10V"]["loss_5000h_mean"], CP["groups"]["14V"]["loss_5000h_mean"]
A(f"| capacitor stress/transfer | 10 V to 14 V equivalent | 5000 h loss {f(c10*100,1)}% to {f(c14*100,1)}% (x{c14/c10:.1f}), before any film-vs-electrolytic transfer |")
A(f"| battery cycle-life basis | 94 to 256 cycles to 70% SOH (NASA cells) | not comparable to a UPS design life; template only |")
A("| West Texas dip-rate multiplier | 1 to 2 | dips per year scale proportionally |")
A("| Utilization transfer | Alibaba vs training campus | mean power fraction x2.2 |\n")
A("## 4. Scorecard\n")
A("Closeness to real-world behaviour for the reference campus (Abilene, public-information proxy), from the evidence above. 'Close' = validated on held-out real data at or near the target; 'Moderate' = real data from a similar system, factor-of-2-level confidence; 'Far' = assumption- or transfer-dominated, output spans an order of magnitude or more across plausible inputs.\n")
A("| Factor | Verdict | Basis | Main residual error |\n|---|---|---|---|")
A("| Outdoor temperature, typical hours | **Close** | hold-out coverage 0.88/0.49 vs 0.90/0.50 | airport vs campus microclimate (not measured) |")
A("| Extreme heat | **Moderate** | stationary model failed backtest (5/10 vs 1); trend model fitted, not yet backtested forward | trend extrapolation; coincident grid stress |")
A("| Wet-bulb | **Close but not needed** | derived from observed data | irrelevant to air-cooled chillers |")
A("| Grid frequency, typical (body + events) | **Moderate-Close** | within ~2x of 2024, conservative for 2025; RMS in published range | response keeps improving; 5 days of 1 s data |")
A("| Grid frequency, deep tail / systemic | **Far** | 2 documented events; regime rate spans 0.03-0.44/yr | rate and in-regime depth are scenario-grade |")
A("| Over-frequency from campus trip | **Moderate** | fit reproduces ERCOT's 1,560 MW / 60.235 Hz event (60.22); n=12 | ride-through design and partial trips unknown |")
A("| AI load swing, per node | **Moderate** | measured, repeat-consistent (KS 0.08) | H100 research runs vs GB200 production |")
A("| AI load swing, whole campus / sync | **Far** | rho unobservable: 25x spread at 200 MW | needs scheduler/PDU telemetry |")
A("| Utilization / mean power | **Moderate after correction** | transfer gap x2.2 identified; use training-like fraction | no campus data |")
A("| Voltage dips (rate) | **Moderate** | EPRI vs ERCOT West count same order | old survey, not ERCOT; Texas not isolated |")
A("| Voltage dips (impact: depth/duration/phases/ride-through) | **Far** | durations from ERCOT deck, phases and ride-through assumed | campus ride-through unknown |")
A("| Battery internal resistance, fresh | **Close** | measured NMC cell at 0/25/45 C and by SOC | one cell type; pulse vs system |")
A("| Battery aging (capacity, resistance growth) | **Far** | proxy cells, 100-250 cycle lives, LOO coverage 0.80 | not the facility chemistry/duty |")
A("| DC-link capacitor degradation | **Far** | electrolytic overstress proxy, strong stress dependence | film vs electrolytic; no operating-condition data |\n")
A("## 5. Bottom line\n")
A("- Of the 14 scored items, 3 are close to observed real-world behaviour (typical temperature, wet-bulb, fresh NMC resistance), 6 are moderate (within roughly a factor of 2 on transferable evidence), and 5 are far: dominated by assumptions or transfer gaps that public data cannot resolve, with outputs that swing 3x to 25x across plausible inputs.")
A("- The backtests already caught two real errors (stationary extremes understating heat; a utilization source unrepresentative of a training campus) plus the frequency-response trend earlier. More such errors are likely in the factors with no held-out data.")
A("- The quickest ways to tighten the picture, in order of leverage: scheduler/PDU power traces to pin down rho; UPS/BESS and capacitor specifications with vendor life data; protection and fault records at the point of interconnection; refreshing the frequency response estimate annually; continued monitoring of the heat trend.")
(ROOT / "reports/reality_check.md").write_text("\n".join(L))
print("written", sum(map(len, L)))
