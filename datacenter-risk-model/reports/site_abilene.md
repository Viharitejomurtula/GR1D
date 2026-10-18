# Reference campus (Abilene, TX, ERCOT West): site calibration vs frozen public baseline

**This is a reference campus built from public information. It is not the operator's actual equipment or design, and nothing here is a claim about any real facility's hardware, protection or performance.**

Baseline = `frozen/v1_public_baseline` (unchanged). Everything here is labelled OBSERVED, DERIVED (from observed data), SCENARIO (an input the operator must confirm) or UNCHANGED (no site data yet).

## 1. Reference-campus definition (verification status)

Verified by reading the company/contractor pages directly (Verified 2026-10-17 by reading the company/contractor pages directly (not independent confirmation).):
- **campus:** 1.2 GW total power capacity; eight buildings; up to 50,000 NVIDIA GB200 NVL72 per building; phase 1 two buildings, >200 MW; phase 2 six buildings expected mid-2026; 1.2 GW grid interconnection (source: Crusoe newsroom: expands Abilene AI campus to 1.2 GW)
- **cooling:** Direct-to-chip liquid cooling, 'zero-water evaporation', closed water loop chilled by air-cooled chillers; ~1 million gallons of water per building (source: Crusoe newsroom; Madrona interview)
- **electrical:** Original 200 MW, 138 kV substation (2022-2024); 12.5-acre 1 GW, 345 kV greenfield substation with five main power transformers (three temporary units while permanent ones are procured; fully energized 2026-03-10; swap expected Oct 2026); work done 'in coordination with AEP'. Medium-voltage distribution to low-voltage transformers, switchgear, low-voltage UPS, RPPs as modular units (source: Mortenson project page; Madrona interview)
- **on site resources:** Natural-gas turbines for backup power; large-scale behind-the-meter battery storage and solar (source: Crusoe newsroom (capacities not stated))

Not verified, so not used or not to be presented on slides:
- **coordinates:** exact location not confirmed (Crusoe names the Lancium Clean Campus in Abilene; county not explicitly stated); the KABI weather station is ~8 km from city centre only
- **transmission owner:** contractor says work was 'in coordination with AEP'; ownership of the line is not stated
- **onsite gas capacity mw:** ~360 MW appeared only in a secondary report (Cleanview); Crusoe gives no capacity
- **load ramp:** 421 MW rising to 843 MW (Epoch AI) appeared in a secondary source only
- **Not available from public sources at all:** UPS/BBU converter limits, battery chemistry/capacity, DC-link capacitor part, restart surge, rail droop or board undervoltage settings, ride-through design, protection settings, scheduler or PDU power behaviour.
- Scenario inputs: weather station USW00013962 Abilene Regional Airport (KABI); voltage class transmission (138/345 kV), stated by the contractor; load {'phase1_verified': 200, 'illustrative_mid': 600, 'full_verified': 1200} MW (200 and 1,200 MW are stated phase/total capacities; 600 MW is an illustrative midpoint, not a site claim); training share 0.8 (assumed).

## 2. Weather (DERIVED from observed KABI data, 1930-2026)

| | Austin (baseline) | Abilene (site) |
|---|---|---|
| August 15:00 dry-bulb quantiles 1/5/25/50/75/95/99% (C) | 23.5 / 27.8 / 33.9 / 36.1 / 37.2 / 39.4 / 41.1 | 23.7 / 27.2 / 33.3 / 36.1 / 37.8 / 40.6 / 42.3 |
| January 06:00 dry-bulb quantiles (C) | -7.2 / -3.9 / 1.0 / 5.6 / 10.6 / 18.2 / 20.7 | -11.7 / -6.7 / -0.8 / 2.5 / 7.0 / 12.8 / 15.4 |
| hot-hour return levels 10/50/100 y, stationary fit (C) | 41.6/43.0/43.5 | 41.9/43.1/43.5 (100-y CI 42.7-44.2) |
| August 15:00 wet-bulb quantiles (C) | 21.0 / 22.4 / 23.8 / 24.5 / 25.2 / 26.2 / 27.1 | 19.0 / 20.1 / 21.8 / 22.6 / 23.4 / 24.6 / 25.3 |
| wet-bulb return levels 10/50/100 y (C) | 28.7/30.0/30.6 | 27.3/28.2/28.5 |
| Jul-Aug hours with wet-bulb > 25 C | 16.8% | 1.9% |
| annual-mean trend (C/decade) | 0.1 | 0.28 |
- Site body distribution uses 2011-2025 (the warming trend and backtest below show older windows understate present heat). Non-stationary extremes (KABI annual maxima, location trend 0.020 C/yr, 95% CI 0.009-0.034; AIC 358 vs 366 stationary): hot-hour return levels in 2026 for 10/50/100 years = 42.7/43.6/43.8 C; 2040 projection (trend extrapolation) 43.0/43.9/44.1 C.
- **Cooling-relevant exposure (dry-bulb hours per year; the campus uses air-cooled chillers on a closed liquid loop, so dry-bulb, not wet-bulb, sets heat-rejection limits):**
| threshold | mean 2000-2025 | first decade mean | last decade mean | fitted 2026 | worst year |
|---|---|---|---|---|---|
| > 35 C | 259 h | 224 h | 315 h | 370 h | 723 h |
| > 38 C | 60 h | 39 h | 94 h | 122 h | 304 h |
| > 40 C | 12 h | 5 h | 24 h | 31 h | 104 h |
| > 42 C | 2 h | 0 h | 4 h | 5 h | 16 h |
- Reading: Abilene's dry-bulb extremes match Austin's but are rising: hours above 40 C roughly quadrupled between the first and last decade. Wet-bulb is much lower than Austin (above 25 C in ~2% of summer hours vs 17%), but because Crusoe states it uses air-cooled chillers rather than evaporative cooling, wet-bulb is not the limiting variable; chiller capacity at 40-44 C ambient is. A spike filter (>6 C from the 5-hour median) removed 0.4% of KABI hours (including impossible 45-47 C readings in April 2022) and a 27 C dew-point cap removed 8 hours; neither affects the frozen Austin/Dallas-Fort Worth results. KABI is an airport station; the campus microclimate and on-site heat sources are not represented.

## 3. Grid frequency (UNCHANGED system-wide; site as a source of events)

- ERCOT frequency is one interconnection-wide quantity: the baseline body, event, trend and systemic-regime models apply unchanged to the site. No site-specific frequency measurement was found.
- **The campus as a load-loss source** (DERIVED from ERCOT's own over-frequency events, n=12; excess = exp(-6.30) x MW^0.65, sigma 0.15 in log): if the whole campus trips off at once, the expected peak frequency is
| load lost | expected peak (Hz) | +/-1 sigma |
|---|---|---|
| 200 MW | 60.058 | 60.050-60.067 |
| 600 MW | 60.119 | 60.103-60.138 |
| 1200 MW | 60.187 | 60.162-60.216 |
- Check: ERCOT's observed 1,560 MW loss produced 60.235 Hz; the fit gives 60.22. These are single-instant total losses; partial ride-through reduces them, and the campus's behind-the-meter battery storage and gas backup (capacities not public) could change this and are not modelled.

## 4. Voltage dips (CLASS from EPRI; West Texas evidence SCENARIO-level)

- Class: transmission (138/345 kV). EPRI median rates per year: 3.2 (0.7-0.8 pu), 2.5 (0.5-0.7 pu), 3.3 (<0.5 pu); site-to-site lognormal sigma 0.828.
- West Texas evidence (ERCOT PDCWG Nov 2024 large-load deck): documented fault events that cut large loads: Oct 2022 West Texas (3LG, 138 kV, delayed ~10-cycle clearing, 415-500 MW), Dec 2022 Far West (19-cycle clearing, ~1,560 MW), Jan and Oct 2023 West Texas (single-line-to-ground, 3-4 cycle clearing), plus 19 power-electronics ride-through events Nov 2023 - Oct 2024 (7 West/McCamey, 4 Far West, 8 Central). ERCOT also reports SLG faults cutting loads at dips as shallow as 0.85 pu and warns of >1,000 MW reductions for 345 kV faults in Far West Texas.
- Reading: ERCOT counted 11 fault events (7 West, 4 Far West) that cut large power-electronics loads in the ~12 months from Nov 2023 (regional, not at this site), comparable to or above the EPRI transmission median of 9.0 sags/yr below 0.8 pu. This supports using the EPRI transmission class with an elevated-rate scenario (multiplier 1.0-2.0, SCENARIO) instead of a fitted site rate. Duration evidence from the same deck (3-4 cycles normal, 10-19 delayed) is already in the sampler defaults. Whether a given dip drops the campus load depends on its own ride-through design (NOT KNOWN; ERCOT notes large unit-to-unit variance at similar dips).

## 5. AI load swing at site scale (OBSERVED shapes and job sizes; scale, kW/GPU and rho are SCENARIO)

- Hardware (public statements): GB200 NVL72 racks, ~120-132 kW per 72 GPUs, i.e. ~1.7-1.8 kW/GPU rack-level; scenarios use 1.25 / 1.75 / 2.25 kW per GPU. Method: facility Monte Carlo (`scripts/site_gpu_sync.py`): job sizes from Alibaba, normalized H100 training power shapes from NLR, training share 0.8 (assumed). Hardware statement and kW/GPU come from public pages (GB200 NVL72); the shapes remain H100-based. Corrects the baseline's rule of thumb: swing scales ~linearly with size only when jobs are aligned.
| IT load | kW/GPU | rho (fraction of jobs sharing phase) | training mean (MW) | swing p99-p1 (MW) | 1 s ramp p99 / p99.9 (MW/s) |
|---|---|---|---|---|---|
| 200 MW | 1.75 | 0.0 | 160.0 | 8.6 | 1.2 / 1.7 |
| 200 MW | 1.75 | 0.25 | 160.0 | 51.8 | 9.4 / 24.1 |
| 200 MW | 1.75 | 1.0 | 160.0 | 201.1 | 48.0 / 95.9 |
| 600 MW | 1.75 | 0.0 | 480.0 | 18.0 | 2.1 / 2.7 |
| 600 MW | 1.75 | 0.25 | 480.0 | 146.9 | 25.1 / 66.7 |
| 600 MW | 1.75 | 1.0 | 480.0 | 601.0 | 138.1 / 297.6 |
| 1200 MW | 1.75 | 0.0 | 960.0 | 21.9 | 3.0 / 4.0 |
| 1200 MW | 1.75 | 0.25 | 960.0 | 312.0 | 74.6 / 164.8 |
| 1200 MW | 1.75 | 1.0 | 960.0 | 1234.2 | 269.8 / 597.4 |
- Reading: the result is dominated by rho, which no public data constrains. At the 200 MW phase (1.75 kW/GPU, GB200 NVL72 class) the aggregate training swing is ~9 MW if jobs are independent, ~52 MW if a quarter share phase and ~201 MW (about 1.3x mean training power) if all align; kW per GPU (hardware generation) matters far less (compare the 1.25 and 2.25 kW/GPU runs in `site/abilene/gpu_sync_site.json`). Real scheduler/PDU telemetry from the operator is the only way to narrow this. Ramps are the numbers that stress UPS/BESS and grid-interconnection limits.

## 6. Factors still on proxies (UNCHANGED until site/vendor data arrive)

- Battery capacity/resistance (NASA small cells, CALCE NMC DC level), DC-link capacitor (NASA electrolytic). UPS/BESS and capacitor hardware at the campus are not public in the sources found.
- Utilization: the Alibaba fleet (22% SM utilization, mixed light-inference workloads) is NOT representative of a dedicated training campus. Transfer check: it implies mean node power at 38% of peak, while measured training nodes (NLR) run at 84% of their 95th-percentile power, a factor of 2.2. For this site use the training-like fraction.

## 7. Needed from the operator/TSP to finish calibration

1. Confirmed coordinates and point of interconnection (voltage, short-circuit strength, protection clearing times, fault history at the bus).
2. Facility one-line diagram: UPS/BESS chemistry, ratings and cycling duty; DC-link capacitor part and temperature.
3. GPU generation and per-GPU all-in power; scheduler logs or PDU-level 1 s power traces to estimate rho.
4. Ride-through/voltage-dip tolerance of power supplies and UPS (test curves).
5. On-site gas generation operating mode (islandable? ramp rates).
6. Cooling design (dry vs evaporative; setpoints) to convert the wet-bulb results into limits.
