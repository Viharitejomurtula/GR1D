# datacenter-risk-model
Empirical-first distributions for Category 1 and 2 risk factors from public data. Reference scenario (not site-calibrated): ERCOT, Li-ion NMC, film DC-link capacitors (`config.yaml`).

- **Report:** `reports/final_report.md` (all factors, numbers, validation, limitations; observed vs assumed labelled).
- **Samplers:** `models/samplers.py`, fitted parameters `models/*.json`; `python sample_scenarios.py [n] [seed]`.
- **Sources / confidence register:** `sources.csv`.
- **Pipeline:** `scripts/download_*.py` -> `data/raw` (untouched) -> `data/interim` (unpacked, git-ignored) -> `scripts/extract_*.py`, `clean_*.py` -> `data/processed` -> `scripts/fit_*.py` -> `models/`, `figures/` -> `scripts/validate.py` -> `scripts/build_report.py`.
- Install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt h5py python-pptx pypdf`. Run download scripts from inside `scripts/`.
