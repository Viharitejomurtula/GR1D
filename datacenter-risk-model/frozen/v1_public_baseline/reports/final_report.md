# Data-center risk model: fitted distributions from public data (Categories 1 and 2)

Reference scenario: ERCOT (Texas), Li-ion NMC, film DC-link capacitors (`config.yaml`). **None of the models is site-calibrated.** Every number below is read from `models/*.json`; every factor is labelled OBSERVED (fitted to data) or ASSUMED (modeling choice). Samplers: `models/samplers.py`; scenario generator: `sample_scenarios.py`; source register: `sources.csv`.

## 1. Summary and confidence


| # | Factor | Cat. | Source | Model | Confidence | Main limitation |
|---|---|---|---|---|---|---|
| 1 | Outdoor temperature | 1 | NOAA GHCNh (KAUS, KDFW) | month x hour empirical quantiles + GEV annual max | High (observed) | airport, dry-bulb only |
| 2 | Frequency deviation and RoCoF (body) | 1 | Open Frequency DB US_TX01/02 | empirical + block resampling | Medium | 5.1 days, one May window |
| 3 | Frequency events and extremes | 1 | ERCOT monthly Operations Reports (311 events, 2018-2025) | Poisson x GPD(MW) x nadir regression with year trend + documented systemic regime (2011, 2021) | Medium for typical events; Low-Medium for deep tail (2 documented collapse events) | collapse events (Uri) absent from data; response improving |
| 4 | AI load swing magnitude and speed | 1 | NLR GenAI power profiles | empirical quantiles by workload and nodes | High (measured) | research cluster, <=16 nodes |
| 5 | Voltage dips (depth, rate; duration/phases) | 2 | EPRI DPQ II (aggregate) | Poisson x lognormal site rate by depth bin | Low-Medium; duration and phases ASSUMED | no raw events, old data |
| 6 | GPU synchronization | 2 | NLR (lockstep) + Alibaba (group sizes) | facility Monte Carlo vs cross-job phase sharing rho | Low (rho ASSUMED) | cross-job sync unobservable |
| 7 | Data-center capacity utilization | 2 | Alibaba ASI v2026 (6 sampled days) | hourly utilization + ASSUMED linear power map | Medium-Low | 6 sampled days of 185, power map assumed |
| 8 | Battery capacity degradation | 2 | NASA PCoE (10 cells) | per-cell exponential fade, lognormal rate | Low-Medium | small cells, no temperature effect resolved |
| 9 | Battery internal resistance | 2 | CALCE INR NMC (DC, by T and SOC) + NASA PCoE EIS (aging growth, 7 cells) | fresh DC table x lognormal growth | Medium (fresh NMC level); Low (growth transfer) | growth not measured on the NMC cell |
| 10 | DC-link capacitance degradation | 2 | NASA PCoE capacitors (24) | saturating + linear loss by stress voltage | Low | electrolytic proxy; film transfer ASSUMED |

(The plan lists nine factors; frequency magnitude and rate of change appears as rows 2-3.)

## 2. Category 1

### 2.1 Outdoor temperature (OBSERVED)
- Units degC. Stations KAUS (650,528 valid hourly values, 1949-2026) and KDFW (638,096). Quantiles (1/5/25/50/75/95/99%) per month and CST hour, years 1996-2025; stored in `models/temperature_params.json`.
- KAUS August 15:00: 23.5 / 27.8 / 33.9 / 36.1 / 37.2 / 39.4 / 41.1. KAUS January 06:00: -7.2 / -3.9 / 1.0 / 5.6 / 10.6 / 18.2 / 20.7.
- KAUS annual-maximum GEV (shape c=0.19, 76 years): 10/50/100-year hot hour 41.6/43.0/43.5 C (100-y 95% CI 42.5-44.6); observed max 43.3 C. Annual mean trend 0.1 C/decade (p=0.019).
- KDFW annual-maximum GEV (shape c=0.22, 73 years): 10/50/100-year hot hour 42.2/43.6/44.0 C (100-y 95% CI 43.0-45.0); observed max 44.4 C. Annual mean trend 0.31 C/decade (p=<0.001).
- Validation (fit 1996-2015, test 2016-2025): 5-95% band covers 0.89 of held-out hours (nominal 0.90); 25-75% band 0.49 (nominal 0.50); test decade 0.80 C warmer.
- Wet-bulb (cooling-relevant; derived from dry-bulb and dew point, Stull 2011; `models/wetbulb_params.json`): KAUS August 15:00 quantiles 21.0 / 22.4 / 23.8 / 24.5 / 25.2 / 26.2 / 27.1 C; annual-maximum GEV 10/50/100-year 28.7/30.0/30.6 C (observed max 30.6); KDFW 100-year 29.1 C. In Jul-Aug, 17% of KAUS hours have wet-bulb above 25 C. An isolated 32.9 C dew-point spike (2000-08-01) was removed by a spike filter.
- Assumptions/limits: QC codes 2/3/6/7 dropped (ISD convention assumed); airport stations, not the site; pooled years ignore warming; 100-year level is an extrapolation.

### 2.2 Grid frequency deviation and RoCoF: body (OBSERVED)
- Units mHz from 60 Hz (RoCoF mHz/s), 1 s resolution. US_TX01 1.44 d and US_TX02 3.69 d (May 2019), quality-flag-0 samples only. Joint trajectories preserved by resampling 1346 contiguous 5-min blocks (`data/processed/frequency_blocks.parquet`).
- Deviation quantiles (0.1/1/5/25/50/75/95/99/99.9%), US_TX02: -60.5 / -42.1 / -28.4 / -14.9 / 5.2 / 14.2 / 22.0 / 32.0 / 40.1. RoCoF (1 s) quantiles: -5.68 / -3.42 / -2.09 / -0.78 / -0.02 / 0.75 / 2.16 / 3.73 / 6.26. Lag-60 s autocorrelation 0.632.
- Validation: pooled RMS 16.6 mHz vs ERCOT-published 2023 monthly RMS1 range 12.48-18.21 mHz (inside). The two files differ statistically (KS 0.054), as expected for different days: no seasonal, load-level or diurnal coverage.

### 2.3 Frequency events and extremes (OBSERVED events; extrapolation MODELED; systemic stress ASSUMED)
- Data: ERCOT monthly Operations Reports (86 monthly docx from ROS meeting pages, Nov 2018 - Sep 2025): 311 frequency events with date, delta-frequency, **nadir/peak frequency**, MW loss, load, wind share and system inertia (`data/processed/ercot_frequency_events.csv`). ERCOT reports events with dF >= 60 mHz, loss >= 350 MW or RRS deployment. This replaces the 55-event BAL-003 table (settling frequency only, 3 years), kept as a cross-check (`models/frequency_tail_params.json`).
- Under-frequency events: n=299, 43.4/yr; observed minimum nadir 59.7 Hz, largest loss 2519 MW (4 Jun 2022). Stage 1: MW loss above 820 MW is GPD (shape 0.15, scale 235), return levels 1/10/100 y: 1196/1994/3116 MW. Stage 2: log(depth) = -4.07 + 0.64 log(MW) -0.35 log(inertia) -0.113 x years_since_2018 + eps (sigma 0.24, R2 ~0.6).
- **Structural change:** for the same MW loss, nadir depth fell ~11% per year (t = -16.7): faster frequency response has made the grid markedly more robust to trips. In 2025 no event went below 59.9 Hz. The model evaluates at the latest response level; a 2019-level 'legacy response' sensitivity is provided. A model trained on 2018-2022 and tested on 2022-2025 over-predicted rates 3-10x (validation), so older data would overstate current risk.

| nadir below (Hz) | observed events/yr (whole window) | model, current response | model 95% CI | model, legacy 2019 response | direct GPD cross-check |
|---|---|---|---|---|---|
| 59.9 | 18.742 | 3.7820 | 2.6491-4.9965 | 34.8410 | 18.7419 |
| 59.8 | 1.017 | 0.0525 | 0.002-0.1977 | 4.3930 | 1.2164 |
| 59.7 | 0.000 | 0.0020 | 0.0-0.0691 | 0.4060 | 0.0344 |
| 59.6 | 0.000 | 0.0000 | 0.0-0.0457 | 0.0525 | 0.0001 |
| 59.5 | 0.000 | 0.0000 | 0.0-0.034 | 0.0095 | 0.0000 |
| 59.4 | 0.000 | 0.0000 | 0.0-0.0246 | 0.0030 | 0.0000 |
| 59.3 | 0.000 | 0.0000 | 0.0-0.02 | 0.0005 | 0.0000 |
- Reading: ordinary generation-trip events do not reach 59.7 Hz or below at today's response levels (upper 95% bound at 59.3 Hz is ~0.02/yr, i.e. once per ~50 years); under the legacy response 59.7 Hz would occur about every 2.5 years. Rates at or below 59.7 Hz are extrapolation.
- **What the event table cannot show, and how it is handled:** the table lists unit-trip/load-loss events; system-scarcity collapses are absent (its Feb 2021 entries are ordinary trips, nadir >= 59.775 Hz). These are modeled as a separate systemic regime built from primary documents (ERCOT House E&C slides 2021-03-24; FERC-NERC joint report 2021-11, `data/raw/uri_docs/`):

| | Feb 2011 | Feb 2021 (Uri) |
|---|---|---|
| lowest frequency | 59.58 Hz | 59.302 Hz (0.002 Hz above the first load-shed stage, 59.3 Hz) |
| time below 59.4 Hz | n/a | 4 min 23 s (ERCOT: more units would have tripped after 9 min) |
| max firm load shed | 4,000 MW for 7.5 h | 20,000 MW for 70.5 h (orders of 1,000/5,000/8,500/10,500 MW in the first minutes) |
| cumulative generation outages | 14,702 MW | 52,277 MW |
- Regime rate: 2 documented events in 14.75 years (Jan 2011 - Sep 2025): MLE 0.136/yr, posterior median 0.15/yr, 95% interval 0.028-0.435/yr. In-regime nadir ~ Uniform(59.302, 59.58) Hz (two events: scenario-grade; the 2021 event nearly reached load shedding, so deeper outcomes are plausible; use `systemic_nadir_hz=59.3` for the load-shed stress case).
- Sensitivity of the annual probability that the year's minimum nadir falls below each level, by assumed regime rate (the rate is the main uncertainty; the downstream decision should be checked at several values):

| regime rate /yr | P(<59.7 Hz) | P(<59.5 Hz) | P(<59.4 Hz) |
|---|---|---|---|
| 0.02 | 0.0198 | 0.0141 | 0.007 |
| 0.07 | 0.0676 | 0.0482 | 0.0238 |
| 0.15 | 0.1372 | 0.0977 | 0.0484 |
| 0.30 | 0.2592 | 0.1846 | 0.0914 |
- Design anchors from ERCOT documents (scenarios, not probabilities): most severe single contingency 1,430 MW; responsive reserves sized to keep frequency >= 59.7 Hz for it and above 59.3 Hz (first load-shed stage) for the two largest units; lowest observed inertia 115 GW*s (Mar 2022).
- Over-frequency (load loss, e.g. data-center ride-through): 12 events, 1.74/yr, peak up to 60.24 Hz for 1400 MW; excess = exp(-6.30) x MW^0.65 (sigma 0.15). ERCOT's Nov-2024 deck adds large-load cases (60.086 Hz / 415 MW; 60.132 Hz / 500 MW; 60.235 Hz / 1,560 MW; the loads were crypto). Very few events; scale with care.
- Limits: Poisson independence; reporting thresholds truncate small events; inertia is a system estimate; trend not extrapolated; nadir levels < 59.7 Hz are model-based; the regime rate is weakly constrained.

### 2.4 AI load swing magnitude and speed (OBSERVED)
- NLR GenAI power profiles (CC BY 4.0), 0.2 s, 4 GPUs per node. Per-node results (W per node); full empirical quantiles by workload/nodes in `models/ai_load_swing_params.json` and `ai_inference_swing_params.json`.
- Training llama2_70b_lora (41 runs pooled over 2-16 nodes): median 2506 W/node, p5 722, p95 3011; 99th-pct 1 s ramp up +552 W/s, down -671 W/s; 99th-pct 5 s swing 1313 W; largest 0.2 s-lag ramp 2266 W/s.
- Training stable_diffusion (41 runs pooled over 2-16 nodes): median 2511 W/node, p5 739, p95 2971; 99th-pct 1 s ramp up +1704 W/s, down -1606 W/s; 99th-pct 5 s swing 2059 W; largest 0.2 s-lag ramp 2340 W/s.
- Inference offline (722 runs, 1 node): median 99th-pct 1 s ramp 1007 W/s (range 538-1230); median power 2772 W.
- Inference online_finite (706 runs, 1 node): median 99th-pct 1 s ramp 625 W/s (range 121-948); median power 2643 W.
- Inference online_rate (200 runs, 1 node): median 99th-pct 1 s ramp 3 W/s (range 0-10); median power 2785 W.
- Structure: two regimes (near-flat vs large steps), capped by idle-to-peak (~2.5 kW/node), so a single parametric family fits poorly; kept empirical. Steady-rate inference is nearly flat; bursty/batch inference and training swing by up to ~1-2.4 kW per node within a second.
- Repeat consistency (even vs odd repeats): median KS 0.08. Limits: research cluster/benchmark jobs, 2-16 nodes, runs of minutes to hours, GPU+CPU aggregate; checkpoints and failures under-sampled.

## 3. Category 2

### 3.1 Voltage dips: depth and rate OBSERVED (aggregate); duration and phases ASSUMED
- Source: EPRI DPQ II report 1002199, Tables 2-1/2-2 (site-median annual sag counts by threshold and monitoring location, events <= 1 min); depth bins by differencing cumulative thresholds.

| Location | 0.70-0.80 pu | 0.50-0.70 pu | <0.50 pu | site-rate lognormal sigma |
|---|---|---|---|---|
| transmission | 3.2 | 2.5 | 3.3 | 0.828 |
| substation | 10.5 | 6.5 | 3.8 | 0.77 |
| feeder | 10.4 | 9.5 | 10.9 | 0.677 |
- Rates are events per year at the median site; site-to-site variation is lognormal (sigma from the quartiles). Sampler: Poisson count per depth bin x site multiplier, depth uniform within bin (assumed).
- NOT in the data (user must set): duration distribution and phase count (sampler defaults: 90% normal clearing 3-5 cycles, 10% delayed clearing 10-20 cycles per ERCOT's large-load deck evidence, with the weights assumed; 20% three-phase, assumed). EPRI sites are 1990s-2000s US distribution sites, not ERCOT; Texas not isolated. ERCOT's 2024 deck says single-line-to-ground faults cause larger load reductions than models predict, so phase count matters.

### 3.2 GPU synchronization (OBSERVED lockstep + group sizes; cross-job sync ASSUMED)
- Observed (NLR raw per-node logs): within a job, node 1 s power changes correlate 0.95-0.99 (mean pairwise, per job; lowest single pair 0.91) with median best lag 0.0 s; variability ratio 0.99 vs 1/sqrt(N)=0.25 for 16 independent nodes. Holds up to 16 nodes (41 jobs); extrapolated beyond.
- Observed (Alibaba, concurrent GPUs per training workload_id, quantiles 0/1/5/10/25/50/75/90/95/99/99.9%): 0.0 / 0.1 / 0.3 / 1.0 / 2.0 / 8.0 / 26.0 / 64.0 / 128.0 / 176.0 / 256.0. Median 8 GPUs, 90th pct 64, 99.9th pct 256.
- Facility Monte Carlo (10,000 GPUs placeholder, 20% training = 500 nodes; scale linearly): p99-p1 aggregate training swing vs rho (fraction of jobs sharing phase; ASSUMED, unobservable):

| rho | p99-p1 swing MW (mean; 5-95% across draws) | std MW |
|---|---|---|
| 0.0 | 0.35 (0.22-0.51) | 0.09 |
| 0.25 | 0.51 (0.31-0.72) | 0.15 |
| 0.5 | 0.73 (0.53-0.94) | 0.24 |
| 1.0 | 1.16 (1.0-1.3) | 0.46 |
- Mean training power 0.96 MW: swing is 35% (independent) to 120% (aligned) of mean training power. Treat rho as a scenario knob.

### 3.3 Data-center capacity utilization (OBSERVED utilization; power map ASSUMED)
- Alibaba ASI GPU trace v2026 (OSDI'26), 144 sampled hours over days [15, 30, 60, 100, 140, 165] of 185 (HTTP-range extraction of the 352 GB hourly table; job summary of 40.5M GPU pods fully read). ~150k GPUs in the sampled hours.
- Fleet GPU allocation fraction 5/50/95%: 0.958 / 0.969 / 1.028 (fully allocated). SM utilization fraction 5/50/95%: 0.176 / 0.219 / 0.246 (hourly, little diurnal variation). Allocation vs utilization differ by ~4x: capacity reserved is not capacity used.
- ASSUMED power map: P_node = 0.6 kW + (3.0 - 0.6) x SM util per 4-GPU node (endpoints from NLR H100 training low/high states). Alibaba GPUs are mixed (H20, L20, A10, XPU), so use fractions, not absolute watts. Implied mean node power ~1.1 kW at median utilization.
- Limits: 6 of 185 days; hourly averages; SM utilization is not power; one Chinese hyperscaler fleet mix.

### 3.4 Battery capacity degradation (OBSERVED proxy; transfer ASSUMED)
- NASA PCoE Li-ion 18650 cells (~2 Ah), 10 clean cells at 22-43 C, 1.5 A charge / 2 A discharge. Model SOH(n)=exp(-k n), k lognormal: mu=-6.07 (CI -6.25 to -5.91), sigma=0.30 (CI 0.17 to 0.37); median k=0.0023/cycle.
- Cycles to 70% SOH (5/50/95%): [94.0, 155.0, 256.0]. Temperature effect rho=0.59, p=0.07 (not significant). Cells excluded: 23 of 34 (cold-cell reversible capacity loss, anomalous starts, poor fits).
- Leave-one-cell-out: 0.80 of held-out fade rates inside the 5-95% predictive band (nominal 0.90, n=10). Limits: lives of 100-250 cycles; no calendar aging, DoD or SOC effects; not NMC-specific; CALCE data not obtained.

### 3.5 Battery internal resistance (OBSERVED: NMC DC level by temperature/SOC + aging growth from other cells; combining ASSUMED)
- **Fresh-cell DC resistance, NMC (CALCE INR 18650-20R, LiNiMnCo/graphite, 2.0 Ah; DST dynamic tests at 0/25/45 C, start SOC 50% and 80%):** pulse resistance from dV/dI on current steps (<=1.5 s, >=1 A), in mOhm per cell (median, IQR across steps; `models/battery_dc_resistance_params.json`):

| temperature | SOC 0-10% | 10-20% | 20-30% | 30-40% | 40-50% | 50-60% |
|---|---|---|---|---|---|---|
| 0 C | 118 | 107 | 103 | 101 | 98 | 103 |
| 25 C | 76 | 72 | 71 | 71 | 71 | 72 |
| 45 C | 82 | 83 | 78 | 77 | 77 | 78 |
- Reading: resistance is ~72 mOhm at 25 C, ~100-120 mOhm at 0 C and ~77-83 mOhm at 45 C, nearly flat in SOC between 10% and 60% and rising at low SOC (<10%). SOC above ~60% is sparsely covered. The 45 C value being above 25 C is in the data (one test per condition; not explained).
- **Aging growth (NASA cells, EIS Re+Rct):** 7 cells with good log-linear fit: R(n)=R0 exp(g n); growth g median 0.0025/cycle (log-sigma 1.09), about 28% growth over 100 cycles at the median, heavy upper tail. NASA EIS R0 median 0.153 ohm vs CALCE pulse ~0.072 ohm: EIS (down to 0.1 Hz) includes slower processes, so the two are different quantities. The sampler multiplies the CALCE fresh level by the NASA growth ratio, which ASSUMES the growth ratio transfers across cell types.
- Invalid EIS fits (Re/Rct outside 0-1 ohm, complex values) dropped; the EIS table logs 24 C for cold-aged cells so the aging ambient from the discharge table is used. Not available: aging growth for the NMC cell itself, temperature dependence of growth, pack-level scaling.

### 3.6 DC-link capacitance degradation (OBSERVED electrolytic proxy; film transfer ASSUMED)
- NASA PCoE capacitor electrical-stress aging (ELECTROLYTIC, ~2200 uF, stressed at 10, 12, 14 V; 8 capacitors each; 5,105 h; capacitance from EIS at 100 Hz). Model L(t)=L_inf(1-exp(-t/tau))+k t.

| Stress | loss at 5000 h mean +/- sd | L_inf | k per 1000 h | reached 20% loss |
|---|---|---|---|---|
| 10V | 6.8% +/- 1.0 | 0.082 | 0.0000 | 0/8 |
| 12V | 13.7% +/- 1.5 | 0.151 | 0.0000 | 0/8 |
| 14V | 23.0% +/- 5.8 | 0.182 | 0.0091 | 6/8 |
- Loss at 5000 h rises ~4.1 percentage points per volt over 10-14 V (r=0.89). At 10-12 V loss is a fast step then plateau (tau of a few hours, with partial recovery); at 14 V it keeps growing and 6/8 pass 20%.
- Leave-one-out within stress group: 0.92 of capacitors inside mean +/- 2 sd (n=24).
- ASSUMED: transfer to film DC-link capacitors (film ages far more slowly by different mechanisms): sampler exposes `scale_to_target` (default 1.0 = no transfer, a pessimistic bound). Accelerated overvoltage conditions, no temperature or ripple-current dependence; early-time first-crossing times (<300 h) are conditioning artifacts.

## 4. Validation summary

- Held-out or external checks exist for: temperature (decade hold-out), AI swing (repeat split), battery capacity (leave-one-cell-out), capacitor (leave-one-out), frequency body (ERCOT published RMS), frequency events (time split: predictions failed because response improved over time, see 2.3). None exists for: voltage dips, GPU synchronization across jobs, utilization power mapping, battery resistance, or any transfer to the target hardware. Full numbers: `models/validation.json`.

## 5. Where data are too sparse, and what is assumed

- Rare events: frequency deep tail (collapse regime from 2 documented events; rate interval 0.03-0.44/yr), voltage dips (aggregate rates only), heat extremes (GEV on ~75 annual maxima).
- Pure assumptions (no data): voltage-dip phase count and clearing-time mixture weights; cross-job synchronization rho; utilization-to-power map; battery/capacitor transfer to the target technology; facility size and training share.
- Sample sizes: 10 / 7 / 24 cells or capacitors, 5 days of frequency, 6 days of utilization.

## 6. Reproduce

`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt h5py python-pptx pypdf`; downloads in `scripts/download_*.py` (run from `scripts/`); fits `scripts/fit_*.py`, `extract_*.py`, `validate.py`; `python sample_scenarios.py 2000 1`; this report: `scripts/build_report.py`. Data in `data/raw` (untouched), `data/interim` (unpacked archives, git-ignored), `data/processed`.

## 7. Next steps to improve the evidence

- Obtain ERCOT FME zips/NP12-261-M or FNET data (frequency tails); more Alibaba days and cluster-specific power telemetry; CALCE (NMC-relevant) battery data; EPRI raw sag records or site-specific monitoring; film-capacitor aging data; a site decision (location, equipment) to calibrate every factor.
