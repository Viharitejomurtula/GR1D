# Evidence grade per factor  (M = measured, S = published spec, G = general practice, A = assumed)
Results are CONDITIONAL on a disturbance occurring and on the event class stated (loss-causing public events / general EPRI sags / ride-through test). No annual rate yet.
Sensitivity = total-order Sobol ST, every assumed value a wide interval (sim/run_final2.py).

| # | Factor | Grade | Source / note |
|---|---|---|---|
| 1-3 | dip shape, count, gaps | M (2024 Table 1); M/A (2025, 2026: sag times+depths assumed) | NERC; PJM decks. Events are public BECAUSE load was lost (outcome-selected) |
| 1 | dip depth | M range 0.25-0.40 (NERC); EPRI bins (M, other agent) | now drives PSU (172 VAC UVLO vs residual x Vnom) and VFD (rectifier conducts if sqrt2*400*res >= 540 V) |
| 4 | phase jump | A | physics sweep, no measured angles |
| 5 | post-dip overvoltage | M (3 events, n=3) | interval, not distribution |
| 6 | AI crash/restart | A; surge range G (ERCOT/AionTracks deck, vendor) | Llama 3: 466 interruptions/54 d verified |
| 7 | SOC at dip | A | derived: ms dips drain ~0.3 Wh of ~1 kWh; ST ~0 |
| 8 | units offline | A (design) | reported as two separate scenarios |
| 9 | equipment age | M-unconfirmed | NASA EOS conflicts with other agent's fit; ST ~0 so unneeded |
| 10-12,15 | converter overload | S for ORv3 PSU class (AE: >115%/10 s, >120%/100 ms, CC 155% 10 ms) ; A that the BBU converter shares these | replaced Vertiv UPS tiers |
| 13-14 | bypass | S (1/4 cycle transfer, Vertiv); A (detection delay) | |
| 16 | SOC-estimation error | A (bias+noise) | ST ~0 |
| 17-18 | ultracap | S | not in output chain |
| 19-22 | PSU | S | AE ORv3 3 kW |
| 23 | rack buffer | G (4 min, 15 kW, 2 ms takeover, 48.5 V trigger: Analog Devices, secondary) | OCP spec still blocked |
| 24 | board UV | S tolerance (TPS2663) + G (40 V server floor) + A (droop) | |
| 25-28 | cooling | S (ATV320 manual NVE41295: UV timeout 0.2 s, DC-Maintain off by default, Atr off by default) ; G (chiller 100-600 s) ; A (DC-bus UV behavior, operator time) | |
| 29-30 | transformer | G/A | not in chain; +-7.5% unverified |
| 31 | relay | S | |
| 32 | breaker | merged into dip duration (3-5 cycles) | |
| PSU loading | G (servers 20-85% of nameplate, mean ~31%; vendor-commissioned older study) | interval 0.2-0.85 |
