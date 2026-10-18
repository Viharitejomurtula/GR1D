# Implied factor covariance (Part B)

Produced by `ridethrough/drivers/implied.py` on 2026-10-18. Cov(X) = S Sigma_D S^T + diag(noise^2), linearized at each driver's typical value.

Nominal case: attenuation nominal; coupling 1, grid-like (upper bound for a data center); noise multiplier 1; PSU mapping k 1; age sd 4.33 years (uniform 0-15); DC-link capacitors per bank n = 1.

Sweeps: attenuation ('nominal', 'upper'); coupling (0.0, 0.5, 1.0) (0 = flat load (independent of weather and time of day), 0.5 = half, 1 = grid-like (upper bound for a data center)); noise multiplier (1, 5, 10); PSU mapping k (0.5, 1.0); age sd (4.33, 2.5) years (fleet age distribution unknown: uniform 0-15 vs (high - low) / 6); DC-link n (1, 4, 16) (DC-link noise 0.115 / sqrt(n); capacitor count unknown). 216 cases x groups ('overall', 'DJF', 'MAM', 'JJA', 'SON').

## S used (nominal case; factor units per driver unit)

| factor | outdoor_temp_c | load_fraction | equipment_age_years |
|---|---|---|---|
| storage_resistance_pu | 0 | 0 | 0.052 |
| capacity_age_factor | 0 | 0 | -0.0084 |
| usable_energy_factor | 0 | 0 | -0.0084 |
| soc_estimate_error | 0 | 0 | 0 |
| converter_current_limit_pu | 0 | 0 | 0 |
| converter_overload_s | 0 | 0 | 0 |
| dclink_capacitance_factor | 0 | 0 | -0.0132 |
| relay_accuracy_pct | 0 | 0 | 0 |
| psu_holdup_ms | 0 | -20 | -0.263 |
| compressor_trip_pct | 0 | 0 | 0 |
| compressor_restart_s | 0 | 0 | 0 |
| osc_amp | 0 | 0 | 0 |
| osc_freq_hz | 0 | 0 | 0 |
| converter_loading | 0 | 1 | 0 |

Non-zero cells and their sources:

| factor | driver | slope | S column | conversion | evidence | source |
|---|---|---|---|---|---|---|
| storage_resistance_pu | equipment_age_years | 0.052 | slope_at_typical_nominal | - | model-default | https://pdfs.semanticscholar.org/86a4/fbda5951ce594c4707c34c6b27c83197ffa2.pdf |
| capacity_age_factor | equipment_age_years | -0.0084 | slope_at_typical_nominal | - | model-default | https://pdfs.semanticscholar.org/86a4/fbda5951ce594c4707c34c6b27c83197ffa2.pdf |
| usable_energy_factor | equipment_age_years | -0.0084 | slope_at_typical_nominal | - | assumed | - (equation row) |
| dclink_capacitance_factor | equipment_age_years | -0.0132 | slope_at_typical_nominal | - | datasheet-proxy | https://www.mouser.co.uk/datasheet/2/136/B41694__B41794-45962.pdf |
| psu_holdup_ms | load_fraction | -20 | slope_at_typical_nominal | x PSU mapping k 1 | datasheet-proxy | https://www.advancedenergy.com/getmedia/b530c4fb-6ef2-4d50-8296-24a02c9501fd/ENG-50V-3kW-OPEN-RACK-V3-PSU-235-01-04-27-22.pdf |
| psu_holdup_ms | equipment_age_years | -0.263 | slope_at_typical_nominal | - | assumed | https://www.mouser.co.uk/datasheet/2/136/B41694__B41794-45962.pdf |
| converter_loading | load_fraction | 1 | slope_at_typical_nominal | - | assumed | - (equation row) |

Cells that are non-zero only in the upper-attenuation case:

- storage_resistance_pu x outdoor_temp_c: -0.0057 (as in S)
- usable_energy_factor x outdoor_temp_c: 0.0017 (as in S)
- converter_current_limit_pu x outdoor_temp_c: -0.0093 (multiplier x typical 1.55)

## Noise used (multiplier 1, DC-link n = 1)

| factor | sd | basis | note |
|---|---|---|---|
| storage_resistance_pu | 0.0072 | sourced | noise.csv 0.0072 fraction (relative) x typical 1 x 1 |
| capacity_age_factor | 0.00238 | sourced | noise.csv 0.0028 fraction (relative) x typical 0.85 x 1 |
| usable_energy_factor | 0.0675 | assumed | master.csv (high - low) / 6 |
| soc_estimate_error | 2.167 | assumed | master.csv (high - low) / 6 |
| converter_current_limit_pu | 0.15 | assumed | master.csv (high - low) / 6 |
| converter_overload_s | 90 | assumed | master.csv (high - low) / 6 |
| dclink_capacitance_factor | 0.115 | sourced | noise.csv 0.115 fraction of nominal (per capacitor) / sqrt(1) x 1 |
| relay_accuracy_pct | 0.1667 | assumed | master.csv (high - low) / 6 |
| psu_holdup_ms | 1.667 | assumed | master.csv (high - low) / 6 |
| compressor_trip_pct | 3.333 | assumed | master.csv (high - low) / 6 |
| compressor_restart_s | 58.33 | assumed | master.csv (high - low) / 6 |
| osc_amp | 0.04617 | assumed | master.csv (high - low) / 6 |
| osc_freq_hz | 0.4667 | assumed | master.csv (high - low) / 6 |
| converter_loading | 0.1683 | assumed | master.csv (high - low) / 6 |

DC-link: noise.csv's 0.115 is a per-capacitor initial tolerance (kept as given). A bank of n independent capacitors has 0.115 / sqrt(n); the count is unknown, so n = 1, 4, 16 is swept. s_matrix/ is unchanged.

## Top 10 pairs by |correlation| (nominal case, overall)

Only pairs that share a driver are listed; every other pair has exactly zero implied correlation. Both age spreads are shown; the ranking uses age sd 4.33.

| factor pair | correlation (age sd 4.33) | correlation (age sd 2.5) | drivers | depends on |
|---|---|---|---|---|
| storage_resistance_pu - capacity_age_factor | -0.997 | -0.992 | equipment_age_years | noise = new-cell spread only (aging spread not found); correlation overstated |
| psu_holdup_ms - converter_loading | -0.502 | -0.522 | load_fraction | assumed noise;PSU mapping k |
| storage_resistance_pu - usable_energy_factor | -0.474 | -0.297 | equipment_age_years | assumed noise |
| capacity_age_factor - usable_energy_factor | 0.473 | 0.295 | equipment_age_years | assumed noise |
| storage_resistance_pu - dclink_capacitance_factor | -0.445 | -0.275 | equipment_age_years | bound slope |
| capacity_age_factor - dclink_capacitance_factor | 0.444 | 0.274 | equipment_age_years | bound slope |
| storage_resistance_pu - psu_holdup_ms | -0.337 | -0.202 | equipment_age_years | assumed noise;bound slope |
| capacity_age_factor - psu_holdup_ms | 0.337 | 0.201 | equipment_age_years | assumed noise;bound slope |
| usable_energy_factor - dclink_capacitance_factor | 0.211 | 0.082 | equipment_age_years | assumed noise;bound slope |
| usable_energy_factor - psu_holdup_ms | 0.160 | 0.060 | equipment_age_years | assumed noise;bound slope |

## Across the sweeps (overall)

Each column changes one setting from the nominal case; min and max are over all 216 cases.

| factor pair | nominal | min | max | attenuation (nom / upper) | coupling (0 / 0.5 / 1) | noise multiplier (1 / 5 / 10) | PSU k (0.5 / 1) | age sd (4.33 / 2.5) | DC-link n (1 / 4 / 16) |
|---|---|---|---|---|---|---|---|---|---|
| storage_resistance_pu - capacity_age_factor | -0.997 | -0.997 | -0.579 | -0.997 / -0.981 | -0.997 / -0.997 / -0.997 | -0.997 / -0.939 / -0.797 | -0.997 / -0.997 | -0.997 / -0.992 | -0.997 / -0.997 / -0.997 |
| psu_holdup_ms - converter_loading | -0.502 | -0.591 | -0.023 | -0.502 / -0.568 | -0.044 / -0.228 / -0.502 | -0.502 / -0.502 / -0.502 | -0.348 / -0.502 | -0.502 / -0.522 | -0.502 / -0.502 / -0.502 |
| storage_resistance_pu - usable_energy_factor | -0.474 | -0.663 | -0.260 | -0.474 / -0.663 | -0.474 / -0.474 / -0.474 | -0.474 / -0.468 / -0.452 | -0.474 / -0.474 | -0.474 / -0.297 | -0.474 / -0.474 / -0.474 |
| capacity_age_factor - usable_energy_factor | 0.473 | 0.197 | 0.641 | 0.473 / 0.641 | 0.473 / 0.473 / 0.473 | 0.473 / 0.451 / 0.397 | 0.473 / 0.473 | 0.473 / 0.295 | 0.473 / 0.473 / 0.473 |
| storage_resistance_pu - dclink_capacitance_factor | -0.445 | -0.893 | -0.025 | -0.445 / -0.437 | -0.445 / -0.445 / -0.445 | -0.445 / -0.098 / -0.047 | -0.445 / -0.445 | -0.445 / -0.275 | -0.445 / -0.705 / -0.893 |
| capacity_age_factor - dclink_capacitance_factor | 0.444 | 0.019 | 0.893 | 0.444 / 0.445 | 0.444 / 0.444 / 0.444 | 0.444 / 0.094 / 0.042 | 0.444 / 0.444 | 0.444 / 0.274 | 0.444 / 0.703 / 0.891 |
| storage_resistance_pu - psu_holdup_ms | -0.337 | -0.559 | -0.062 | -0.337 / -0.259 | -0.543 / -0.459 / -0.337 | -0.337 / -0.333 / -0.321 | -0.469 / -0.337 | -0.337 / -0.202 | -0.337 / -0.337 / -0.337 |
| capacity_age_factor - psu_holdup_ms | 0.337 | 0.134 | 0.558 | 0.337 / 0.337 | 0.542 / 0.459 / 0.337 | 0.337 / 0.321 / 0.282 | 0.468 / 0.337 | 0.337 / 0.201 | 0.337 / 0.337 / 0.337 |
| usable_energy_factor - dclink_capacitance_factor | 0.211 | 0.009 | 0.573 | 0.211 / 0.285 | 0.211 / 0.211 / 0.211 | 0.211 / 0.047 / 0.024 | 0.211 / 0.211 | 0.211 / 0.082 | 0.211 / 0.334 / 0.424 |
| usable_energy_factor - psu_holdup_ms | 0.160 | 0.002 | 0.358 | 0.160 / 0.146 | 0.258 / 0.218 / 0.160 | 0.160 / 0.160 / 0.160 | 0.222 / 0.160 | 0.160 / 0.060 | 0.160 / 0.160 / 0.160 |

## By season (nominal case)

| factor pair | overall | DJF | MAM | JJA | SON |
|---|---|---|---|---|---|
| storage_resistance_pu - capacity_age_factor | -0.997 | -0.997 | -0.997 | -0.997 | -0.997 |
| psu_holdup_ms - converter_loading | -0.502 | -0.367 | -0.283 | -0.510 | -0.427 |
| storage_resistance_pu - usable_energy_factor | -0.474 | -0.474 | -0.474 | -0.474 | -0.474 |
| capacity_age_factor - usable_energy_factor | 0.473 | 0.473 | 0.473 | 0.473 | 0.473 |
| storage_resistance_pu - dclink_capacitance_factor | -0.445 | -0.445 | -0.445 | -0.445 | -0.445 |
| capacity_age_factor - dclink_capacitance_factor | 0.444 | 0.444 | 0.444 | 0.444 | 0.444 |
| storage_resistance_pu - psu_holdup_ms | -0.337 | -0.397 | -0.435 | -0.334 | -0.371 |
| capacity_age_factor - psu_holdup_ms | 0.337 | 0.396 | 0.434 | 0.333 | 0.370 |
| usable_energy_factor - dclink_capacitance_factor | 0.211 | 0.211 | 0.211 | 0.211 | 0.211 |
| usable_energy_factor - psu_holdup_ms | 0.160 | 0.188 | 0.206 | 0.158 | 0.176 |

## Monte Carlo check

100000 samples per case and group from `sample_drivers`; age ~ uniform centered on 7.5 years with the case's age sd (4.33 gives 0-15); S's curves for curve rows; clipped load_fraction. Pairs whose Monte Carlo correlation differs from the linear result by more than 0.1: 261 of 98280 case x group x pair combinations (full list: `implied_mc_check.csv`).

| factor pair | flagged combinations | difference range |
|---|---|---|
| storage_resistance_pu - converter_current_limit_pu | 108 | -0.121 to -0.100 |
| converter_current_limit_pu - psu_holdup_ms | 81 | -0.120 to +0.228 |
| converter_current_limit_pu - converter_loading | 72 | -0.184 to -0.107 |

Reasons the two differ: curve rows are non-linear (the converter derates only above 25 degC, and the usable-energy curve is steeper in a conditioned room than S's 25-35 degC slope); load_fraction is clipped to [0.2, 0.97] in the Monte Carlo; the linear model uses slopes at the typical value only.

## Sigma_D temperature-load block (sampled)

Estimated from `sample_drivers` (1000000 draws, fixed seed per group). At coupling 1 it should match the fit (`driver_covariance.csv`).

| group | coupling | Var(temp_c) | Var(load_index) | Cov(temp_c, load_index) | fit Cov (coupling 1) |
|---|---|---|---|---|---|
| overall | 0 | 92.783 | 0.0031 | +0.001 |  |
| overall | 0.5 | 92.783 | 0.0206 | +0.631 |  |
| overall | 1 | 92.783 | 0.0731 | +1.261 | 1.255 |
| DJF | 0 | 56.044 | 0.0035 | +0.000 |  |
| DJF | 0.5 | 56.044 | 0.0130 | -0.542 |  |
| DJF | 1 | 56.044 | 0.0414 | -1.085 | -1.099 |
| MAM | 0 | 39.415 | 0.0027 | +0.000 |  |
| MAM | 0.5 | 39.415 | 0.0090 | +0.321 |  |
| MAM | 1 | 39.415 | 0.0279 | +0.642 | 0.630 |
| JJA | 0 | 19.266 | 0.0031 | +0.000 |  |
| JJA | 0.5 | 19.266 | 0.0212 | +0.559 |  |
| JJA | 1 | 19.266 | 0.0757 | +1.117 | 1.126 |
| SON | 0 | 56.156 | 0.0033 | -0.001 |  |
| SON | 0.5 | 56.156 | 0.0159 | +0.600 |  |
| SON | 1 | 56.156 | 0.0536 | +1.201 | 1.208 |

## Assumptions in this step

- Sigma_D: the temperature-load block is sampled from `sample_drivers` at each coupling, so the linear model and the Monte Carlo share one definition: coupling scales the temperature and calendar effects on load together; the centred residual is not scaled. load_fraction = typical x load_index (linear part of to_load_fraction); age is independent of temperature and load.
- Coupling 0 is flat load (independent of weather and time of day). Its load variance is the residual of the grid (NCENT) fit, which is an assumption for a data center.
- Coupling 1.0 is grid-like (upper bound for a data center): NCENT grid load is far more temperature-sensitive than a data center's load.
- Age spread: sd 4.33 years (uniform 0-15) is nominal; 2.5 years ((high - low) / 6) is swept, because the fleet age distribution is unknown. Linear and Monte Carlo use the same spread in every case.
- noise = new-cell spread only (aging spread not found); correlation overstated: applies to pairs whose noise comes only from noise.csv's new-cell spread (Rumpf et al. rows).
- S: S's own slopes for every row (decision (a)); an empty upper slope uses nominal.
- A multiplier slope (converter_current_limit_pu vs temperature) is multiplied by the factor's typical value to get factor units.
- psu_holdup_ms vs load_fraction: S's slope at PSU ratio 1.0 times the mapping k; the 20/L equation is not extrapolated below its sourced range.
- Noise in relative units is multiplied by the factor's typical value. Factors without sourced noise use the master.csv range sd and are flagged "assumed noise"; that sd spans the factor's whole range, so it likely overstates unit-to-unit noise and understates correlations.
- workload_type shifts only the means of osc_amp and osc_freq_hz, so the covariance is the same in every workload category.
- Monte Carlo: conditioned rooms follow clip(18 + attenuation x (T - 3.3), 18, 27) degC, from s_matrix_report.md's thermal-path assumption.

## Assumptions carried from s_matrix_report.md

- Aging slopes are linear averages of power-law fits, from model predictions at 25 °C and 50% charge. The cells were tested at 40–55 °C. UPS batteries kept near full charge likely age faster.
- Capacitor drift is a bound (≤30% over ≥22.8 years at 40 °C), not a measured rate. Its direction and linearity are assumed.
- PSU hold-up below full load is extrapolated from the equation. PSU load is not site load, because redundant supplies share it, and the mapping is unknown.
- All responses come from proxy products: one LFP cell, one capacitor series, one inverter and one PSU.
- Age × temperature interaction (faster aging when hot) is not modeled.
