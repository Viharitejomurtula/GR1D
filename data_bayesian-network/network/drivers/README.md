# network/drivers: external-driver model and implied factor covariance

This folder holds the outputs of two linked steps in the ride-through dependency network.

- **Part A, driver fit** (`ridethrough/drivers/fit.py`): estimates how the external drivers behave
  together, from DFW hourly weather (NOAA LCD) and ERCOT hourly native load (NCENT zone, with the ERCOT
  total as a cross-check). The drivers are outdoor temperature, dewpoint and the grid load index.
  It fits on 2021-2025 and holds out 2026.
- **Part B, implied covariance** (`ridethrough/drivers/implied.py`): computes
  Cov(X) = S Σ_D Sᵀ + diag(noise²), using the S matrix in `../s_matrix/`. Here Σ_D covers
  [outdoor_temp_c, load_fraction, equipment_age_years]:
  - temperature and load come from Part A; load_index is converted to load_fraction, and the
    temperature-load covariance is scaled by `coupling`;
  - equipment age comes from master.csv (sd 2.5 years) and is independent of the other two.
  Dewpoint is fitted in Part A but not used in Part B. The linear calculation uses S's own
  `slope_at_typical_nominal` and `slope_at_typical_upper` for every row. Curves from
  `../s_matrix/curve_points_s.csv` are used only in the Monte Carlo check.

Inputs are read-only: `../../dfw_hourly_temp_clean.csv`, `../../ercot_native_load_2021_2026.csv`,
`../master.csv`, `../s_matrix/`. Nothing here modifies them.

Change history: see `CHANGELOG.md`.

## Output files

Each entry gives: file name; what it contains; columns with units; how it was produced
(script and function); date produced.

### Part A: driver fit (produced 2026-10-17 by `python -m ridethrough.drivers.fit`)

**temp_by_month_hour.csv**: Model 1, DFW temperature and dewpoint climatology for 2021-2025,
one row per month x hour (288 rows). Produced by `fit.fit_temp_month_hour`.
- month (1-12), hour (0-23, Central wall clock)
- mean_c, sd_c: mean and sd of temp_c (degC); n: hours in the cell
- q05_c, q95_c: 5th and 95th percentiles of temp_c (degC)
- dew_mean_c, dew_sd_c: mean and sd of dewpoint_c (degC)

**load_model.json**: Model 2, the NCENT load_index model (chosen: spline, 7 knots) and its
diagnostics. Produced by `fit.fit_load_model` and `fit.load_model_json`.
- model: intercept, hour_daytype_effect (weekday and weekend_holiday, 24 values each),
  month_effect (12, January = 0), curve (temperature curve f(T): type, knots_c in degC, coef),
  fbar_month_hour (12 x 24); all in load_index units (dimensionless). Evaluate with
  `fit.predict_load_index`.
- shape: balance points (degC) and end slopes (load_index per degC); r2_fit; residual_sd by
  group; residual_autocorrelation (lags 1, 24 and 168 h); holdout_2026 (n, rmse, bias by group)
- candidates (hinge vs spline), spline_knot_cv_rmse, ercot_crosscheck, load_index_definition
  (window rule, dates per window, mean by year)

**driver_covariance.csv**: Model 3, Sigma_D for temp_c (degC), load_index (dimensionless) and
dewpoint_c (degC), overall and by season, with 95% moving-block bootstrap CIs (7-day blocks, 500
resamples). 30 rows. Produced by `fit.sigma_d_stats`, `fit.bootstrap_ci` and
`fit.driver_covariance_table`.
- group (overall | DJF | MAM | JJA | SON), var_i, var_j (a variance row has var_i = var_j), n (hours)
- pearson, spearman (dimensionless) and covariance (product of the two variables' units), each
  with _lo and _hi (95% CI)

**driver_copula.json**: the Gaussian copula of the driver residuals (temp_z, dew_z, load_resid),
used by `sample.py`. Produced by `fit.copula_corr` and `fit.copula_json`.
- seasons: per season, n and the 3 x 3 correlation with 95% CI (reported, not used by the sampler)
- cells: per season x 6-hour daypart (16 cells, e.g. "JJA|12-17"), n, the 3 x 3 correlation with
  95% CI, and marginal quantiles of each variable at quantile_probs (temp_z and dew_z
  dimensionless; load_resid in load_index units)
- calendar_counts: fit-period hours per (month, hour, daytype); quantile_probs; n_boot; block_days; seed

**driver_fit_report.md**: results of Part A: cleaning counts, load_index rule and yearly means,
Models 1-3, ERCOT cross-check, 2026 holdout and caveats. Produced by `fit.build_report`.

**fig_load_vs_temp.png, fig_load_by_hour.png, fig_temp_heatmap.png, fig_residuals.png,
fig_holdout_2026.png**: figures in the report (load vs temperature with both curves, load by hour,
temperature by month x hour, residual distributions, 2026 holdout). Produced by `fit.make_figures`.

### Part B: implied factor covariance (produced 2026-10-17 by `python -m ridethrough.drivers.implied`)

Factors (rows and columns below) are the 14 rows of S in `../s_matrix/s_matrix_long.csv`. A case
is one combination of attenuation (nominal | upper), coupling (0 | 0.5 | 1), noise_mult (1 | 5 | 10),
psu_k (0.5 | 1), age_sd (4.33 | 2.5 years) and dclink_n (1 | 4 | 16): 216 cases. The nominal case is
attenuation nominal, coupling 1 (grid-like, an upper bound for a data center), noise_mult 1,
psu_k 1, age_sd 4.33, dclink_n 1. Groups: overall, DJF, MAM, JJA, SON.

**implied_covariance_nominal_<group>.csv** (5 files): Cov(X) = S Sigma_D S^T + diag(noise^2) for the
nominal case, 14 x 14. Column factor holds the row name; each other column is a factor. Units: the
product of the two factors' units (master.csv). Produced by `implied.implied_cov` via
`implied.run_cases`.

**implied_correlation_nominal_<group>.csv** (5 files): the matching correlation matrices
(dimensionless, -1 to 1). Produced by `implied.implied_cov`.

**implied_all_cases.csv.gz**: every case x group x factor pair (i <= j), gzip-compressed (113,400 rows).
Columns: case (label), attenuation, coupling, noise_mult, psu_k, age_sd (years), dclink_n, group,
factor_i, factor_j, covariance (factor-unit product), correlation. Produced by `implied.run_cases`.

**implied_summary.csv**: the factor pairs that share a driver (every other pair has zero
correlation), for every case and group. Columns: factor_i, factor_j, case and its six settings,
group, correlation, covariance, drivers (the driver terms the covariance comes through),
driver_terms (each term's contribution, factor-unit product), depends_on_assumption (flags:
new-cell noise only, assumed attenuation, assumed noise, PSU mapping k, coupling, bound slope,
unit conversion). Produced by `implied.run_cases`, `implied.driver_terms` and
`implied.pair_assumptions`.

**implied_mc_check.csv**: case x group x pairs whose Monte Carlo correlation (100,000 samples from
`sample.sample_drivers`, with S's curves) differs from the linear result by more than 0.1 (585 rows).
Columns: case, group, factor_i, factor_j, linear, monte_carlo, difference (monte_carlo - linear).
Produced by `implied.monte_carlo_check`.

**implied_report.md**: S and noise used, top 10 pairs (both age spreads), sweep and seasonal tables,
the sampled Sigma_D temperature-load block, the Monte Carlo check, and every assumption (this
step's and s_matrix_report.md's). Produced by `implied.build_report`.
