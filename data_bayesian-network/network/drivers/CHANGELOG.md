# CHANGELOG: network/drivers

Running log of approved changes for the external-driver model (Part A: driver fit) and the
implied factor covariance (Part B). One row per approved change. Times are local machine time
(America/Los_Angeles). Paths are relative to the repo root.

| time | path | action | reason |
|---|---|---|---|
| 2026-10-17 20:21 | .env | install | holidays 0.106, matplotlib 3.11.2 (+ deps) for the holiday calendar and fit plots |
| 2026-10-17 20:22 | data_bayesian-network/network/drivers/CHANGELOG.md | create | running log of approved changes (also creates the drivers/ folder) |
| 2026-10-17 20:33 | data_bayesian-network/network/drivers/CHANGELOG.md | edit | fix timezone label (machine is America/Los_Angeles) and use repo-root paths |
| 2026-10-17 20:33 | data_bayesian-network/network/drivers/README.md | create | catalog of output files (Rule 1); entries added as outputs are produced |
| 2026-10-17 20:35 | ridethrough/__init__.py | create | package marker so tests can import ridethrough (also creates ridethrough/) |
| 2026-10-17 20:35 | ridethrough/drivers/__init__.py | create | subpackage marker for fit, sample, implied (also creates ridethrough/drivers/) |
| 2026-10-17 21:01 | ridethrough/drivers/fit.py | create | Part A driver fit: join/clean, load_index, temp + load models, Sigma_D + copula with block-bootstrap CIs, 2026 holdout |
| 2026-10-17 21:06 | ridethrough/drivers/fit.py | edit | add copula by season x 6-hour daypart (sampler uses it); seasonal-only copula put sampled JJA temp-load Spearman outside the data CI |
| 2026-10-17 21:07 | ridethrough/drivers/sample.py | create | Part A driver sampler (copula by season x daypart, coupling) and to_load_fraction |
| 2026-10-17 21:22 | ridethrough/drivers/sample.py | edit | coupling scales temperature and calendar effects together (coupling 0 = flat load independent of weather and time of day) |
| 2026-10-17 21:24 | ridethrough/drivers/sample.py | edit | move the residual's season x time-of-day mean into the coupling-scaled calendar part (coupling 0 was still tied to time of day in JJA) |
| 2026-10-17 21:31 | ridethrough/drivers/implied.py | create | Part B implied covariance: S x sampled Sigma_D x noise over 216 cases, driver breakdown, assumption flags, Monte Carlo check |
