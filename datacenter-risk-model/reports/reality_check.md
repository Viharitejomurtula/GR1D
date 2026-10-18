# How close are the distributions to the real world?

Method: (1) backtests on data the model never saw, where such data exists; (2) transfer-gap checks where the data come from a different system than the target; (3) the spread of the output across plausible values of each unobservable assumption. The last is the honest measure for the factors no data can validate. Nothing here is a measurement of any real campus; the reference campus is built from public information: no site data (power traces, protection records, UPS/battery specs) was obtainable from public sources.

## 1. Backtests against held-out real data

- **Abilene dry-bulb (fit 1996-2015, test 2016-2026, 93,975 hours):** the 5-95% band covered 0.88 of hours (nominal 0.90), the 25-75% band 0.49 (0.50); the test decade was 1.1 C warmer and 8.5% of hours exceeded the old 95th percentile (nominal 5%). **Typical hours: good. Warming: not captured by a stationary window.**
- **Abilene extreme heat:** a stationary extreme-value fit on 1949-2015 gave a 10-year level of 41.5 C; 5 of the next 10 years exceeded it (expected 1.0); the test-period maximum was 44.0 C vs 42.8 C before. **The stationary model failed on extremes.** The site model now uses a trend (location +0.020 C/yr, AIC 358 vs 366) and a 2011-2025 body window.
- **ERCOT frequency events vs 2024 and Jan-Sep 2025 (model at the current response level):** events per year model 43.4 vs observed 34.9 (2024) and 49.5 (2025); nadir below 59.9 Hz per year: model 3.7 vs observed 6.0 (2024) and 0.0 (2025); below 59.85 Hz: model 0.32 vs 1.00 / 0.00. **Within about a factor of 2 of 2024 and conservative against 2025, as the grid keeps improving.** A model trained on 2018-2022 over-predicted later years 3-10x, so the response level must be re-estimated yearly.
- **Frequency body:** pooled RMS 16.6 mHz vs ERCOT's published 2023 monthly range 12.5-18.2 mHz (inside); only 5 days of 1 s data, so shape beyond the central range is unchecked.
- **Battery fade, capacitor loss, AI-swing repeats:** leave-one-cell-out 0.80 inside the 5-95% band (nominal 0.90, n=10); capacitor leave-one-out 0.92 within 2 sd (0.95); AI swing even-vs-odd repeat KS median 0.08. These show the fits describe the data they came from. They say nothing about whether the cells, capacitors and research-cluster runs resemble the target.

## 2. Transfer gaps (proxy vs target)

- **Utilization:** the Alibaba fleet (median SM utilization 0.22, mixed light inference) implies node power at 38% of peak; measured training nodes (NLR) run at 84% of their 95th-percentile power: a factor of 2.2. A dedicated training campus should use the training-like value, not the Alibaba fleet number.
- **Voltage dips:** EPRI transmission median 9.0/yr below 0.8 pu vs 11 ERCOT-counted load-affecting fault events in West/Far West in 12 months (ratio 1.2): the same order of magnitude, but these are different quantities and say nothing about whether this campus rides through them.
- **Battery:** the NASA cells age over 100-250 cycles; a facility UPS/BESS is specified for thousands of cycles and years of calendar aging. The fade model is a method template; absolute lifetimes do not transfer. The CALCE NMC cell gives a real fresh-cell DC resistance by temperature and SOC, but its aging growth was not measured.
- **Capacitor:** electrolytic parts at 10-14 V overstress; the film DC-link part at the campus is not public. Absolute loss does not transfer.
- **AI load shape:** normalized H100 training runs of 2-16 nodes are applied to GB200 NVL72 clusters of thousands of nodes. Lockstep inside a job is measured up to 16 nodes only.

## 3. Spread of the output across plausible assumptions (what no data can validate)

| unobservable input | plausible range | effect on output |
|---|---|---|
| cross-job phase sharing rho | 0 to 1 | campus training swing at 200 MW: 9 to 201 MW (x23); 1 s ramp p99.9 1.7 to 96 MW/s |
| kW per GPU (hardware) | 1.25 to 2.25 | swing changes only 189 to 190 MW at rho=1 (normalized shapes) |
| systemic grid-stress regime rate | 0.028 to 0.435 per year (95%) | annual probability of nadir below 59.5 Hz from 0.0141 (rate 0.02) to 0.1846 (rate 0.30): x13 |
| capacitor stress/transfer | 10 V to 14 V equivalent | 5000 h loss 6.8% to 23.0% (x3.4), before any film-vs-electrolytic transfer |
| battery cycle-life basis | 94 to 256 cycles to 70% SOH (NASA cells) | not comparable to a UPS design life; template only |
| West Texas dip-rate multiplier | 1 to 2 | dips per year scale proportionally |
| Utilization transfer | Alibaba vs training campus | mean power fraction x2.2 |

## 4. Scorecard

Closeness to real-world behaviour for the reference campus (Abilene, public-information proxy), from the evidence above. 'Close' = validated on held-out real data at or near the target; 'Moderate' = real data from a similar system, factor-of-2-level confidence; 'Far' = assumption- or transfer-dominated, output spans an order of magnitude or more across plausible inputs.

| Factor | Verdict | Basis | Main residual error |
|---|---|---|---|
| Outdoor temperature, typical hours | **Close** | hold-out coverage 0.88/0.49 vs 0.90/0.50 | airport vs campus microclimate (not measured) |
| Extreme heat | **Moderate** | stationary model failed backtest (5/10 vs 1); trend model fitted, not yet backtested forward | trend extrapolation; coincident grid stress |
| Wet-bulb | **Close but not needed** | derived from observed data | irrelevant to air-cooled chillers |
| Grid frequency, typical (body + events) | **Moderate-Close** | within ~2x of 2024, conservative for 2025; RMS in published range | response keeps improving; 5 days of 1 s data |
| Grid frequency, deep tail / systemic | **Far** | 2 documented events; regime rate spans 0.03-0.44/yr | rate and in-regime depth are scenario-grade |
| Over-frequency from campus trip | **Moderate** | fit reproduces ERCOT's 1,560 MW / 60.235 Hz event (60.22); n=12 | ride-through design and partial trips unknown |
| AI load swing, per node | **Moderate** | measured, repeat-consistent (KS 0.08) | H100 research runs vs GB200 production |
| AI load swing, whole campus / sync | **Far** | rho unobservable: 25x spread at 200 MW | needs scheduler/PDU telemetry |
| Utilization / mean power | **Moderate after correction** | transfer gap x2.2 identified; use training-like fraction | no campus data |
| Voltage dips (rate) | **Moderate** | EPRI vs ERCOT West count same order | old survey, not ERCOT; Texas not isolated |
| Voltage dips (impact: depth/duration/phases/ride-through) | **Far** | durations from ERCOT deck, phases and ride-through assumed | campus ride-through unknown |
| Battery internal resistance, fresh | **Close** | measured NMC cell at 0/25/45 C and by SOC | one cell type; pulse vs system |
| Battery aging (capacity, resistance growth) | **Far** | proxy cells, 100-250 cycle lives, LOO coverage 0.80 | not the facility chemistry/duty |
| DC-link capacitor degradation | **Far** | electrolytic overstress proxy, strong stress dependence | film vs electrolytic; no operating-condition data |

## 5. Bottom line

- Of the 14 scored items, 3 are close to observed real-world behaviour (typical temperature, wet-bulb, fresh NMC resistance), 6 are moderate (within roughly a factor of 2 on transferable evidence), and 5 are far: dominated by assumptions or transfer gaps that public data cannot resolve, with outputs that swing 3x to 25x across plausible inputs.
- The backtests already caught two real errors (stationary extremes understating heat; a utilization source unrepresentative of a training campus) plus the frequency-response trend earlier. More such errors are likely in the factors with no held-out data.
- The quickest ways to tighten the picture, in order of leverage: scheduler/PDU power traces to pin down rho; UPS/BESS and capacitor specifications with vendor life data; protection and fault records at the point of interconnection; refreshing the frequency response estimate annually; continued monitoring of the heat trend.