"""How close are the distributions to real-world behavior? Backtests on held-out data where it exists, explicit transfer-gap checks where it does not.
Writes models/reality_check.json. Usage: python -I reality_check.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
out = {}

# 1. KABI dry-bulb and wet-bulb: fit 1996-2015, test 2016-2026 (month x hour quantile coverage), annual-max GEV fitted <=2015 vs 2016-2025 maxima
h = pd.read_parquet(ROOT / "data/processed/ghcnh_hourly_USW00013962.parquet").temp_c
os_env = __import__("os"); os_env.environ["SITE_STATIONS"] = "USW00013962:KABI"
def coverage(s, qs=(0.05, 0.25, 0.75, 0.95)):
    tr, te = s[(s.index.year >= 1996) & (s.index.year <= 2015)], s[(s.index.year >= 2016)]
    g = tr.groupby([tr.index.month, tr.index.hour]).quantile(list(qs)).unstack()
    k = list(zip(te.index.month, te.index.hour)); v = te.values
    c = {q: g[q].reindex(k).values for q in qs}
    return dict(n_test=int(len(te)), cov_5_95=float(np.mean((v >= c[0.05]) & (v <= c[0.95]))), cov_25_75=float(np.mean((v >= c[0.25]) & (v <= c[0.75]))),
                mean_shift_c=float(te.mean() - tr.mean()), frac_above_p95=float(np.mean(v > c[0.95])))
out["kabi_dry_bulb_holdout_2016_2026"] = coverage(h)
cnt = h.groupby(h.index.year).size(); am = h.groupby(h.index.year).max()[cnt >= 6000]
tr_am, te_am = am[am.index <= 2015], am[(am.index >= 2016) & (am.index <= 2025)]
c, loc, sc = stats.genextreme.fit(tr_am.values)
lvl10 = stats.genextreme.ppf(0.9, c, loc, sc)
out["kabi_annual_max_holdout"] = dict(train_years=int(len(tr_am)), test_years=int(len(te_am)), fitted_10y_level_c=float(lvl10),
                                      test_years_exceeding_10y_level=int((te_am > lvl10).sum()), expected_in_test=float(0.1 * len(te_am)),
                                      test_max_c=float(te_am.max()), train_max_c=float(tr_am.max()))
# cooling-relevant: hours per year above dry-bulb thresholds (air-cooled chillers)
rec = h[h.index.year >= 2000]
byyr = {t: rec[rec > t].groupby(rec[rec > t].index.year).size().reindex(range(2000, 2026), fill_value=0) for t in (35, 38, 40, 42)}
out["kabi_hours_per_year_above_dry_bulb"] = {str(t): dict(mean=float(v.mean()), p90=float(np.percentile(v, 90)), max=int(v.max()), last10_mean=float(v.loc[2016:].mean()), first10_mean=float(v.loc[:2015].mean()))
                                             for t, v in byyr.items()}

# 2. frequency events: model at current response vs observed 2024 and 2025 (per-year rates)
from samplers import FrequencyEventTail  # noqa: E402
ev = FrequencyEventTail(); rng = np.random.default_rng(0)
nad = ev.sample(400000, rng); E = pd.read_csv(ROOT / "data/processed/ercot_frequency_events.csv", parse_dates=["datetime"])
U = E[(E.max_min_freq_hz < 60) & (E.mw_loss > 0)]
res = {}
for yr, (lo, hi) in {"2024": ("2024-01-01", "2025-01-01"), "2025_Jan_Sep": ("2025-01-01", "2025-10-01")}.items():
    s = U[(U.datetime >= lo) & (U.datetime < hi)]; yrs = (pd.Timestamp(hi) - pd.Timestamp(lo)).days / 365.25
    res[yr] = {str(t): dict(model=float(ev.rate * (nad < t).mean()), observed=float((s.max_min_freq_hz < t).sum() / yrs)) for t in (59.95, 59.9, 59.85, 59.8)}
    res[yr]["events_per_year"] = dict(model=float(ev.rate), observed=float(len(s) / yrs))
out["frequency_events_vs_recent_years"] = res

# 3. utilization transfer gap: Alibaba fleet SM utilization vs a dedicated training cluster (NLR measured power fractions)
al = json.load(open(ROOT / "models/alibaba_utilization_params.json"))
pm = al["power_mapping_assumption"]; sm = al["hourly"]["sm_util_frac_q"][1]
alibaba_power_frac = (pm["p_idle_kw"] + (pm["p_peak_kw"] - pm["p_idle_kw"]) * sm) / pm["p_peak_kw"]
swt = pd.read_csv(ROOT / "data/processed/nlr_training_swing_stats.csv")
nlr_frac = float((swt.median_w_per_node / swt.p95_w).median())
out["utilization_transfer_gap"] = dict(alibaba_median_sm_util=sm, implied_node_power_fraction_of_peak=float(alibaba_power_frac), nlr_training_median_over_p95_power=nlr_frac,
                                       ratio_training_to_alibaba=float(nlr_frac / alibaba_power_frac),
                                       note="Alibaba is a mixed fleet dominated by light inference; a dedicated training campus draws ~2x more of its peak power on average")

# 4. voltage dips: model transmission rate vs ERCOT-counted West/Far West fault events affecting large loads
vd = json.load(open(ROOT / "models/voltage_dip_params.json"))["locations"]["transmission"]["site_median_events_per_year"]
out["voltage_dips_plausibility"] = dict(epri_transmission_median_below_0_8pu=vd["SARFI80"], ercot_west_far_west_load_affecting_fault_events_12mo=11,
                                        ratio=11 / vd["SARFI80"], note="same order of magnitude; ERCOT count is a different, load-sensitivity-defined quantity")
json.dump(out, open(ROOT / "models/reality_check.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:5200])
