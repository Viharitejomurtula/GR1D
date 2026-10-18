# Scenario matrix: reference campus (Abilene, ERCOT West), low / mid / high

Unobservable inputs are reported at **low, mid and high** and never fixed to a default. Low/high are bounds (or 95% interval ends); mid is an illustrative midpoint or posterior median. They are not probabilities. This is a reference campus built from public information, not the operator's actual design.

## 1. Campus training-load swing and ramp (vs cross-job phase sharing rho; 1.75 kW/GPU, GB200 NVL72 class)

| IT load (mean MW) | rho | swing p99-p1 (MW) | 1 s ramp p99 (MW/s) | 1 s ramp p99.9 (MW/s) |
|---|---|---|---|---|
| 200 | low (rho=0.0) | 9 | 1.2 | 1.7 |
| 200 | mid (rho=0.25) | 52 | 9.4 | 24.1 |
| 200 | high (rho=1.0) | 201 | 48.0 | 95.9 |
| 600 | low (rho=0.0) | 18 | 2.1 | 2.7 |
| 600 | mid (rho=0.25) | 147 | 25.1 | 66.7 |
| 600 | high (rho=1.0) | 601 | 138.1 | 297.6 |
| 1200 | low (rho=0.0) | 22 | 3.0 | 4.0 |
| 1200 | mid (rho=0.25) | 312 | 74.6 | 164.8 |
| 1200 | high (rho=1.0) | 1234 | 269.8 | 597.4 |
- 200 and 1,200 MW are publicly stated phase/total capacities; 600 MW is an illustrative midpoint. The spread between low and high is x20 or more at every size; only operator power traces can narrow it.

## 2. Grid frequency stress (vs systemic-event rate; ERCOT-wide, from 2 documented events, 2011 and 2021)

| regime rate | per year | P(year min nadir < 59.7 Hz) | < 59.5 Hz | < 59.4 Hz | P(at least one in 10 years, < 59.5 Hz) | annual-min nadir p50 / p5 / p1 (Hz) incl. ordinary events |
|---|---|---|---|---|---|---|
| low | 0.028 | 0.028 | 0.020 | 0.010 | 0.18 | 59.87 / 59.78 / 59.41 |
| mid | 0.148 | 0.138 | 0.098 | 0.048 | 0.64 | 59.86 / 59.39 / 59.33 |
| high | 0.435 | 0.353 | 0.251 | 0.124 | 0.94 | 59.85 / 59.35 / 59.31 |
- In-regime nadir is Uniform(59.302, 59.58) Hz from the two documented events; the 2021 event came within 0.002 Hz of the first load-shed stage, so the low end is optimistic. Ordinary trip events at today's response level add only shallow dips (annual-min median ~59.86 Hz).

## 3. Voltage dips at the transmission class (EPRI rates x West Texas multiplier)

| multiplier | dips per year p5 / p50 / p95 | durations | phases |
|---|---|---|---|
| low (x1.0) | 1 / 9 / 37 | 90% 3-5 cycles, 10% 10-20 cycles (assumed weights) | 20% three-phase (assumed) |
| mid (x1.5) | 3 / 14 / 56 | 90% 3-5 cycles, 10% 10-20 cycles (assumed weights) | 20% three-phase (assumed) |
| high (x2.0) | 4 / 18 / 70 | 90% 3-5 cycles, 10% 10-20 cycles (assumed weights) | 20% three-phase (assumed) |
- Rate from EPRI (transmission class, site-to-site lognormal); multiplier is a scenario supported by ERCOT's count of 11 load-affecting West/Far-West fault events in 12 months. Whether any dip drops load depends on ride-through settings (data request items 2-4).

## 4. Items held at a stated middle value (spread reported, not driven into headlines)

- **Capacitor:** mid = the 12 V stress group, no film-vs-electrolytic scaling: 5000 h capacitance loss 15.1% (5-95%: 13.1-17.0%). The observed 12 V group mean at 5000 h is 13.7%; the fitted curve (plateau plus wear-out) ignores the partial recovery seen in the data and reads about 1.4 points high. Spread across stress levels 6.8%-23.0% and the film transfer are unresolved; propagation to failures not tested.
- **Mean power fraction:** training-like (NLR, 84% of peak) instead of the Alibaba fleet value (38%).
- **Heat (cooling margin):** 2026 hot-hour return levels 10/50/100 y = 42.7/43.6/43.8 C; hours above 40 C per year: 41 (last 5-year mean), trend-fitted 31.
- Battery aging remains proxy-based (template only); fresh NMC resistance by temperature and SOC is in `models/battery_dc_resistance_params.json`.