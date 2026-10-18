"""ridethrough.drivers: external drivers of the ride-through dependency network.

Package marker. It holds no code of its own.

Modules:
    fit:     Part A. Joins DFW hourly temperature with ERCOT NCENT hourly load, cleans the data,
             builds load_index, fits the temperature (month x hour) and load models, estimates
             Sigma_D and the Gaussian copula with block-bootstrap CIs, and validates on the 2026 holdout.
    sample:  Part A. sample_drivers() draws calendar, temp_c, dewpoint_c and load_index from the fitted
             copula; to_load_fraction() maps load_index to site load_fraction.
    implied: Part B. Combines Sigma_D with the S matrix (../s_matrix/) to get
             Cov(X) = S Sigma_D S^T + diag(noise^2) across the sweep cases, plus a Monte Carlo check.

Reads:  nothing.
Writes: nothing.
Task:   external-driver model + S-matrix combination (package scaffolding).
"""
