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

_No outputs yet. Entries are added when each output is generated._
