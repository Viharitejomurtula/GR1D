# S matrix: factor responses to external drivers

The model is X = S·D + e, so Cov(X) = S · Σ_D · Sᵀ + diag(noise variances). This file covers S and the noise terms. Σ_D comes from the driver fit (temperature and load data).

## Grid (slope at the driver's typical value)

"Upper" is the slope if the battery or converter room drifts with outdoor temperature (see Thermal path).

| factor | outdoor_temp_c (per °C) | load_fraction | equipment_age_years (per year) | workload_type |
|---|---|---|---|---|
| storage_resistance_pu | 0 (upper −0.025) | none | +0.052 (up to +0.067) | none |
| capacity_age_factor | none | none | −0.0084 (−0.0060 to −0.0134) | none |
| usable_energy_factor | 0 (upper +0.0017) | none | −0.0084 (through capacity) | none |
| soc_estimate_error | none | none | none | none |
| converter_current_limit_pu | 0 below 25 °C; −0.006 above if outdoor | none | none | none |
| converter_overload_s | none | none | none | none |
| dclink_capacitance_factor | none | none | −0.0132 (bound) | none |
| relay_accuracy_pct | none | none | none | none |
| psu_holdup_ms | none | 20 ms / PSU load ratio | −0.26 ms (bound) | none |
| compressor_trip_pct | none | none | none | none |
| compressor_restart_s | none | none | none | none |
| osc_amp | none | none | none | training 0.375, inference 0.09 |
| osc_freq_hz | none | none | none | training 0.2–3 Hz |
| converter_loading | — | exact equation | — | — |

Coverage: temperature 3 of 13 factors, load 1 (plus the converter_loading equation), age 5, workload 2. Six factors respond to no driver and stay independent.

## What this means for the covariance

1. **Age is the main shared driver.** Battery resistance, battery capacity, usable energy, DC-link capacitance and PSU hold-up all move with equipment age. Old units have higher resistance, less capacity and less capacitance together. This is the strongest dependence in the network, and it comes from cited aging data.
2. **Outdoor temperature barely reaches indoor equipment.** Batteries, PSUs and relays sit in rooms held near ASHRAE's recommended 18–27 °C. Their nominal temperature slope is zero, and the "upper" values assume the room drifts across that whole band. Temperature matters for equipment outdoors: chillers (no sourced response yet) and the converter, if it is containerized like the SMA unit, but only on hours above 25 °C.
3. **Load has one sourced response,** PSU hold-up, plus the exact converter_loading equation.
4. **Implied correlations among the age-driven factors will be close to ±1.** The only noise found is the spread between new cells (0.28% capacity, 0.72% impedance). Spread that develops with aging was not found. This overstates the correlation, so sweep the noise (for example 1×, 5× and 10× the new-cell spread).

## Thermal path

- The upper attenuation is 0.284. It assumes the room spans 18–27 °C (9 °C) as DFW outdoor temperature goes from its 5th to 95th percentile (3.3 to 35.0 °C, 31.7 °C). That is an assumption, not a measured room response.
- The product's location is not decided. Indoor gives zero converter temperature response. Outdoor in a container uses SMA's derating: 1.0 at 25 °C, 0.91 at 40 °C, 0.85 at 50 °C.

## Assumptions to state in the demo

- Aging slopes are linear averages of power-law fits, from model predictions at 25 °C and 50% charge. The cells were tested at 40–55 °C. UPS batteries kept near full charge likely age faster.
- Capacitor drift is a bound (≤30% over ≥22.8 years at 40 °C), not a measured rate. Its direction and linearity are assumed.
- PSU hold-up below full load is extrapolated from the equation. PSU load is not site load, because redundant supplies share it, and the mapping is unknown.
- All responses come from proxy products: one LFP cell, one capacitor series, one inverter and one PSU.
- Age × temperature interaction (faster aging when hot) is not modeled.

## Not in S

These are factor-to-factor links. See direct_links.csv, where each is assigned to the simulator's pre-event step, the simulator itself, or a network equation.

## Files

- s_matrix_long.csv: all 53 cells with source, quote, calculation and evidence label.
- curve_points_s.csv: curves in the network's curve format.
- noise.csv
- direct_links.csv
- verification_log.csv
