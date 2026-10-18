# What the Bayesian network rests on

Written 2026-10-18. This file says, for each part of the network, what published document or dataset backs it, how
strong that backing is, and what was not checked. Where a claim is only an assumption it says so.

## 1. What the network computes

External drivers (outdoor temperature, site load, equipment age, workload type) change many equipment factors at
once. Because they share drivers, the factors vary together. The network computes that shared variation:

    Cov(X) = S · Sigma_D · S^T + diag(noise^2)

- X: the 14 factors (rows of `network/s_matrix/s_matrix_long.csv`).
- S: how much each factor moves per unit of each driver (the S matrix).
- Sigma_D: the covariance of the drivers (`ridethrough/drivers/fit.py`, `sample.py`).
- noise: variation of a factor that no driver explains (`network/s_matrix/noise.csv`).

It does not model direct factor-to-factor physics. That belongs to the simulator (`sim/`, `model/`).

## 2. Backing for the method

| Claim | Source | Status |
|---|---|---|
| Output covariance from input covariance and a sensitivity matrix: `U_y = C_x U_x C_x^T` | JCGM 102:2011 (GUM Supplement 2), clause 6.2.1.3, Eq. (3) | Downloaded from BIPM; equation read in the text |
| Correlated inputs add covariance terms to the combined variance | JCGM 100:2008 (GUM), clause 5.2.2, Eq. (13) | Downloaded from BIPM; equation read in the text |
| Outputs that share an input become correlated | JCGM 102:2011, clause 9.2 (Y1 = X1 + X3, Y2 = X2 + X3, shared X3: r(y1, y2) = 0.5) | Read in the text |
| A shared environment induces dependence among components | Lindley and Singpurwalla (1986), J. Applied Probability; Bergman and Ringi (1997) | Seen only in search-result summaries. Not opened. |
| Gaussian copula for the driver dependence (Part A) | none checked | No source looked up. Sklar (1959) and Nelsen's *An Introduction to Copulas* are the usual references. |

Mapping: S = C_x, Sigma_D = U_x, and each factor's noise term is an extra independent input for that factor.

Limits of this backing:
- The GUM and its supplement are about measurement uncertainty. Here the same mathematics is used for variation
  across a fleet of equipment. The formula is the same, the interpretation is not.
- The covariance formula is a linear propagation model. Since 2026-10-18 the same model also runs as a Bayesian
  network (`ridethrough/network/`): `graph.py` assembles roots.yaml, master.csv, edges.csv, tables.csv and the S
  matrix into one DAG (28 nodes, 22 edges); `sampler.py` draws every node given its parents and conditions on
  evidence by rejection (`query`). Five edges.csv links have no number behind them and are structure only
  (`graph.unquantified_edges`). There is still no learning of structure or parameters from data.
- The standards back the arithmetic only. They say nothing about whether the S entries are right.
- No published paper or standard was found that applies this to data-center ride-through.

## 3. Backing for the numbers

### 3.1 Driver links in the S matrix (12 of 53 factor-driver pairs; the rest are "no link found")

| Factor | Driver | Grade | Source | Caveat |
|---|---|---|---|---|
| storage_resistance_pu | outdoor_temp_c | measured (proxy cell) | Panasonic NCR18650PF EIS, Mendeley Data 10.17632/wykht8y7tg.1, CC BY 4.0; cross-check Sandia EIS (Barkholtz 2017) | Slope -0.0201 pu/C at 25 C (range -0.0124 to -0.0246 across datasets and frequencies). One cell per temperature. BBU chemistry unconfirmed. Applies only through the room attenuation. Replaces P3's -0.0889. |
| storage_resistance_pu | equipment_age_years | model-default | Sui et al., Energies 2021, 14, 1732 | A model prediction for one LFP cell, not measured aging data. |
| capacity_age_factor | equipment_age_years | model-default | Sui et al. 2021 | Same. |
| usable_energy_factor | outdoor_temp_c | measured | Sandia SAND2008-5583, Fig. 10 / Table 2 | One 10 Ah LFP cell. Upper attenuation only. |
| usable_energy_factor | equipment_age_years | assumed | defined through capacity_age_factor | A chosen definition. |
| converter_current_limit_pu | outdoor_temp_c | datasheet-proxy | SMA SCS UP-XT datasheet (solar inverter) | Not the BBU converter. Applies only if outdoors. |
| dclink_capacitance_factor | equipment_age_years | datasheet-proxy | TDK B41694/B41794 datasheet | A different capacitor series. |
| psu_holdup_ms | load_fraction | datasheet-proxy | Advanced Energy ORv3 3 kW PSU datasheet | 20 ms is at 100% PSU load; 20/load below that is extrapolated. PSU load is not site load (mapping factor k is assumed). |
| psu_holdup_ms | equipment_age_years | assumed | assumes PSU capacitors age like the TDK series | |
| osc_amp | workload_type | measured | NREL/NLR GenAI Power Profiles (2,246 runs), computed by `ridethrough/responses/workload_swings.py` | Training 0.473, inference 0.196. Metric and trimming differ from the earlier Microsoft figures (0.375 and 0.09). Workload explains 14-38% of the variance, depending on the assumed mix. |
| osc_freq_hz | workload_type | measured, but see caveat | Power Stabilization for AI Training Datacenters, arXiv 2508.14318, Sec. III-A (0.2-3 Hz) | The same NLR traces show no separation by workload (peak about 0.28 Hz training, 0.25 Hz inference; workload explains 1-4% of the variance). |
| converter_loading | load_fraction | assumed (exact equation) | converter loading = site load / capacity | Definition, so it is exact. |

Count: 4 measured, 2 model-default, 3 datasheet-proxy, 3 assumed. In the S matrix file the osc_freq row is still
labeled measured; the NLR check above is why it is shakier than that label.

### 3.2 Noise (variation no driver explains) in `noise.csv`

| Factor | sd | Grade | Source |
|---|---|---|---|
| dclink_capacitance_factor | 0.115 | datasheet-proxy | TDK tolerance -10/+30% |
| capacity_age_factor | 0.0028 | measured | Rumpf et al. 2017, 1,100 new LFP cells (new-cell spread only) |
| storage_resistance_pu | 0.0072 | measured | same study (new-cell spread only) |
| the other 10 factors | (high - low) / 6 from `master.csv` | assumed | no source |

My Sandia EIS replicates give a spread of about 3-7% in resistance, 5-10 times the 0.72% used here. That figure
includes measurement noise. It is in `network/responses/` but not in `noise.csv`.

### 3.3 Drivers (Sigma_D)

| Driver | Source | Status |
|---|---|---|
| outdoor temperature, load | DFW hourly temperature (NOAA LCD) and ERCOT NCENT hourly load, 2021-2025, Gaussian copula by season and 6-hour daypart | Written by Varun. I read the documentation and ran the tests but did not audit `fit.py` line by line. |
| equipment age | uniform 0-15 years (`master.csv`) | assumed |
| workload mix | training/inference/mixed equal shares (`roots.yaml`) | assumed; swept 10-90% in `responses/workload_osc_block_by_mix.csv` |
| room attenuation (outdoor to battery room) | 0 to 0.284 | assumed (S matrix report) |
| converter outdoors or indoors | unknown | not decided |
| temperature-load coupling | 0, 0.5, 1 | swept |

## 4. Factors with no driver link (left to the simulator)

soc_estimate_error, converter_overload_s, relay_accuracy_pct, compressor_trip_pct, compressor_restart_s, osc_freq_hz
(its workload link is not supported by the data).

- soc_estimate_error: SOC error does rise when cold and with aging in the literature, but only for specific
  research estimators, not a BBU's BMS.
- converter_overload_s: one patent (US 10305320) describes an overload limit set from ambient temperature, overload
  level and pre-load, but the PDF is scanned images with no readable numbers.
- relay_accuracy_pct, compressor_trip_pct, compressor_restart_s: settings or tolerances; no dependence found.

## 5. Claims checked and not confirmed

- Sandia long-term aging data (86 cells, impedance every 3% of fade): not confirmed; Battery Archive describes capacity checks only.
- MATR/Severson dataset: every source says 124 cells, not 135, and the platform's download API is gone. Not obtained.
- Bayreuth NMC aging database (9-month study with impedance): the download link did not work. Not obtained.
- Vertiv derating above 40 C and 1% per 100 m: not found. The repo only confirms the EXL S1 runs 0-40 C without derating.
- Chemi-Con: the FAQ confirms the factor 2 per 10 C rule over 60-95 C and says to use at least 40 C, so a conditioned
  hall below 40 C gets no capacitor-aging effect. The "lifetime guide" PDF is for polymer capacitors and is not used.
- GUM Annex F wording on correlation from shared standards: not found in the extracted text, so not relied on.
- Swing amplitude from Fig. 1 of the arXiv paper: not digitized. NERC's 1.9 p.u./s ramp over 250 ms is confirmed;
  its p.u. base is not.

## 6. Known issues

- Fixed 2026-10-18: `tests/test_implied.py::test_written_nominal_correlation_matches` failed for 3 of 5 groups on
  some machines. Cause: `sample.py` drew the copula with numpy's `multivariate_normal` default (`method="svd"`), whose
  factorization depends on the LAPACK library (Apple Accelerate vs OpenBLAS), so the same seed gave different draws.
  It now uses `method="cholesky"` (unique factor, same draws everywhere).
- Fixed 2026-10-18: the `implied_*` files in `network/drivers/` were regenerated with the fitted resistance slope, the
  NLR `osc_amp` range and the Cholesky sampler. Nominal-case correlations moved by less than 1e-3; upper-attenuation
  resistance correlations moved by up to 0.38 (e.g. resistance-capacity -0.77 -> -0.98).
- The fitted resistance slope (-0.0201 pu/degC) rests on two temperatures (10 and 25 C); its 95% range over SOC steps
  is -0.028 to -0.010.
- The age links rest on one paper's model, not on measured aging data.

## 7. Where things are

| What | Where |
|---|---|
| Downloaded datasets (not in git) | `data_bayesian-network/drivers_raw/`; manifest with URLs, licenses, checksums: `network/responses/sources.csv` |
| Resistance vs temperature fit | `ridethrough/responses/battery_resistance.py` -> `network/responses/battery_resistance_*.csv` |
| Effect of that fit on the correlations | `ridethrough/responses/apply_to_implied.py` -> `network/responses/storage_resistance_correlation_comparison.csv` |
| Workload swings | `ridethrough/responses/workload_swings.py` -> `network/responses/workload_*.csv` |
| Method documents | `drivers_raw/method_backing/jcgm100`, `jcgm102` |
| Bayesian network (graph, sampling, conditioning) | `ridethrough/network/graph.py`, `sampler.py`; tests `tests/test_network.py` |
| Tests | `tests/test_responses.py` |
