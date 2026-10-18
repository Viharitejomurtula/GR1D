"""Wet-bulb temperature (cooling-relevant) from GHCNh dry-bulb + dew point (Stull 2011 approximation, valid RH 5-99%, T -20..50 C).
Same cleaning as fit_temperature.py (QC 2/3/6/7 dropped, hourly mean, CST fixed offset). Month x hour quantiles 1996-2025, GEV on annual maxima.
Outputs models/wetbulb_params.json. Usage: python -I fit_wetbulb.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
STATIONS = {"USW00013904": "Austin-Bergstrom (KAUS)", "USW00003927": "Dallas-Fort Worth (KDFW)"}
BAD = {"2", "3", "6", "7"}
QS = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]


def series(sid):
    d = pd.read_csv(ROOT / f"data/raw/ghcnh/GHCNh_{sid}_por.psv", sep="|", low_memory=False,
                    usecols=["DATE", "temperature", "temperature_Quality_Code", "dew_point_temperature", "dew_point_temperature_Quality_Code"])
    d = d.dropna(subset=["temperature", "dew_point_temperature"])
    d = d[~d.temperature_Quality_Code.astype(str).isin(BAD) & ~d.dew_point_temperature_Quality_Code.astype(str).isin(BAD)]
    d = d[d.temperature.between(-40, 50) & d.dew_point_temperature.between(-60, 40) & (d.dew_point_temperature <= d.temperature + 0.5)]
    t = pd.to_datetime(d.DATE).dt.tz_localize("UTC").dt.tz_convert("Etc/GMT+6").dt.tz_localize(None)
    d = d.set_index(t)[["temperature", "dew_point_temperature"]].sort_index().resample("1h").mean().dropna()
    # spike filter: drop hours whose dew point (or dry-bulb) departs > 6 C from the centered 5-hour rolling median (isolated sensor errors)
    for col in ("dew_point_temperature", "temperature"):
        med = d[col].rolling(5, center=True, min_periods=3).median()
        d = d[(d[col] - med).abs() <= 6]
    T, Td = d.temperature.values, d.dew_point_temperature.values
    rh = 100 * np.exp(17.625 * Td / (243.04 + Td)) / np.exp(17.625 * T / (243.04 + T))
    rh = np.clip(rh, 5, 99)
    tw = (T * np.arctan(0.151977 * (rh + 8.313659) ** 0.5) + np.arctan(T + rh) - np.arctan(rh - 1.676331)
          + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh) - 4.686035)
    return pd.Series(tw, index=d.index), d


out = dict(source_id="F1c", kind="derived from observed dry-bulb and dew point (Stull 2011 wet-bulb approximation)", units="degC wet-bulb", stations={},
           quantiles=QS, limitations=["Stull formula valid for RH 5-99% and T -20..50 C (clipped); error ~0.3 C", "Airport stations, not the site",
                                      "No station pressure correction (small effect at Texas elevations)", "Isolated spikes (>6 C from 5-hour rolling median) removed, e.g. a 32.9 C dew point at KAUS on 2000-08-01", "Pools 1996-2025, ignores warming trend"])
for sid, name in STATIONS.items():
    tw, d = series(sid)
    b = tw[(tw.index.year >= 1996) & (tw.index.year <= 2025)]
    body = {f"{m:02d}-{h:02d}": dict(n=int(len(v)), q=np.quantile(v, QS).round(1).tolist()) for (m, h), v in b.groupby([b.index.month, b.index.hour])}
    cnt = tw.groupby(tw.index.year).size(); am = tw.groupby(tw.index.year).max().loc[cnt[cnt >= 6000].index]
    c, loc, sc = stats.genextreme.fit(am.values); rng = np.random.default_rng(0)
    rl = {}
    for T_ in (10, 50, 100):
        p = 1 - 1 / T_
        bs = [stats.genextreme.ppf(p, *stats.genextreme.fit(rng.choice(am.values, len(am)))) for _ in range(300)]
        rl[f"{T_}y"] = dict(est=round(float(stats.genextreme.ppf(p, c, loc, sc)), 1), ci95=np.percentile(bs, [2.5, 97.5]).round(1).tolist())
    # joint hot-humid hours: share of hours with dry-bulb>35C and wet-bulb>25C in Jul-Aug
    summer = d.join(tw.rename("tw"))[lambda x: x.index.month.isin([7, 8]) & (x.index.year >= 1996)]
    out["stations"][sid] = dict(name=name, hours=int(len(tw)), body_month_hour=body, annual_max=dict(years=int(len(am)), gev_shape_c=float(c), loc=float(loc), scale=float(sc),
                                return_levels_c=rl, observed_max=float(am.max())),
                                jul_aug_frac_hours_tw_gt_25=float((summer.tw > 25).mean()), jul_aug_corr_tdb_tw=float(summer.temperature.corr(summer.tw)))
    print(name, "hours", len(tw), "GEV c=%.2f" % c, {k: v["est"] for k, v in rl.items()}, "obs max", round(am.max(), 1), "Jul-Aug Tw>25 frac", round(out["stations"][sid]["jul_aug_frac_hours_tw_gt_25"], 3),
          "Aug15h q", body["08-15"]["q"])
(ROOT / "models/wetbulb_params.json").write_text(json.dumps(out, indent=1))
