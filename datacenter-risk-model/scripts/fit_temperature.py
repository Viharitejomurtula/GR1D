"""Hour/season-conditioned outdoor temperature distributions + extreme-heat tail from NOAA GHCNh (Austin, DFW).

Cleaning (v2 adds a spike filter; v1 baseline did not): drop missing temps and quality codes 2,3,6,7 (ISD convention: suspect/erroneous; ASSUMED to apply to GHCNh);
one value per local-standard hour (mean of obs within the UTC hour, which is shifted to CST = UTC-6; no DST, so hour of day is
fixed-offset local standard time). Years 1996-2025 (30 y) used for body distributions.
Tail: GEV on annual maxima (1949-2025, years with >= 6000 valid hours); return levels with bootstrap CIs.
Outputs: data/processed/ghcnh_hourly_<station>.parquet, models/temperature_params.json, figures/temperature.png
Usage: python -I fit_temperature.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import os
ROOT = Path(__file__).resolve().parent.parent
BODY_START = int(os.environ.get('BODY_START', 1996))  # site runs use a recent window because of warming
TAG = os.environ.get('SITE_TAG', '')  # e.g. '_abilene'; empty = baseline outputs
STATIONS = ({k: v for k, v in (x.split(":") for x in os.environ["SITE_STATIONS"].split(";"))} if os.environ.get("SITE_STATIONS") else {"USW00013904": "Austin-Bergstrom (KAUS)", "USW00003927": "Dallas-Fort Worth (KDFW)"})
BAD_QC = {"2", "3", "6", "7"}
QS = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
BODY_YEARS = (BODY_START, 2025)
MIN_HOURS = 6000


def hourly(sid: str) -> pd.Series:
    d = pd.read_csv(ROOT / f"data/raw/ghcnh/GHCNh_{sid}_por.psv", sep="|", low_memory=False,
                    usecols=["DATE", "temperature", "temperature_Quality_Code"])
    d = d.dropna(subset=["temperature"])
    d = d[~d.temperature_Quality_Code.astype(str).isin(BAD_QC)]
    d = d[d.temperature.between(-40, 50)]
    t = pd.to_datetime(d.DATE).dt.tz_localize("UTC").dt.tz_convert("Etc/GMT+6").dt.tz_localize(None)  # CST fixed
    h = d.set_index(t).temperature.sort_index().resample("1h").mean().dropna()
    if os.environ.get("NO_SPIKE_FILTER") == "1":  # reproduces frozen v1 behavior
        return h
    med = h.rolling(5, center=True, min_periods=3).median()  # spike filter: drop hours > 6 C from the centered 5-hour rolling median
    return h[(h - med).abs() <= 6]


def main():
    out = dict(source_id="F1c", kind="observed (NOAA GHCNh)", units="degC", stations={}, quantiles=QS,
               cleaning="drop missing, QC codes 2/3/6/7 (ISD convention, assumed), range -40..50 C; hourly mean; CST fixed offset")
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for sid, name in STATIONS.items():
        h = hourly(sid)
        h.to_frame("temp_c").to_parquet(ROOT / f"data/processed/ghcnh_hourly_{sid}.parquet")
        print(name, len(h), h.index.min(), h.index.max())
        b = h[(h.index.year >= BODY_YEARS[0]) & (h.index.year <= BODY_YEARS[1])]
        g = b.groupby([b.index.month, b.index.hour])
        body = {f"{m:02d}-{hr:02d}": dict(n=int(len(v)), q=np.quantile(v, QS).round(1).tolist()) for (m, hr), v in g}
        # annual maxima / minima
        cnt = h.groupby(h.index.year).size()
        yrs = cnt[cnt >= MIN_HOURS].index
        am = h.groupby(h.index.year).max().loc[yrs]
        an = h.groupby(h.index.year).min().loc[yrs]
        c, loc, sc = stats.genextreme.fit(am.values)
        rng = np.random.default_rng(0)
        rl = {}
        for T in (10, 50, 100):
            p = 1 - 1 / T
            boots = []
            for _ in range(500):
                s = rng.choice(am.values, len(am))
                bc, bl, bs = stats.genextreme.fit(s)
                boots.append(stats.genextreme.ppf(p, bc, bl, bs))
            rl[f"{T}y"] = dict(est=round(float(stats.genextreme.ppf(p, c, loc, sc)), 1),
                               ci95=np.percentile(boots, [2.5, 97.5]).round(1).tolist())
        ann = h.groupby(h.index.year).mean().loc[yrs]
        slope = stats.linregress(ann.index.values, ann.values)
        out["stations"][sid] = dict(
            name=name, hours=len(h), span=[str(h.index.min()), str(h.index.max())], body_years=BODY_YEARS, body_month_hour=body,
            annual_max=dict(years=len(am), gev_shape_c=float(c), loc=float(loc), scale=float(sc), return_levels_c=rl,
                            observed_max=float(am.max()), note="scipy c = -xi; c>0 bounded tail"),
            annual_min_observed=float(an.min()), annual_mean_trend_c_per_decade=round(slope.slope * 10, 2),
            annual_mean_trend_p=round(slope.pvalue, 3))
        print(" GEV c=%.2f loc=%.1f scale=%.1f; return levels %s; obs max %.1f; trend %.2f C/dec p=%.3f" %
              (c, loc, sc, {k: v["est"] for k, v in rl.items()}, am.max(), slope.slope * 10, slope.pvalue))
        # plots
        summer = b[b.index.month.isin([7, 8])]
        ax[0].plot(range(24), [summer[summer.index.hour == hr].median() for hr in range(24)], label=name)
        ax[1].hist(am.values, bins=15, alpha=.5, label=name)
        ax[2].plot(ann.index, ann.values, label=name)
    ax[0].set(xlabel="hour (CST)", ylabel="median C", title="Jul-Aug diurnal median (1996-2025)"); ax[0].legend(fontsize=7)
    ax[1].set(xlabel="annual max C", title="Annual maxima"); ax[2].set(xlabel="year", ylabel="annual mean C", title="Annual mean")
    out["limitations"] = ["Airport stations, not the data-center site; urban heat island and microclimate differ",
                          "Body distributions pool 1996-2025 and ignore the warming trend (see annual_mean_trend)",
                          "GEV on ~70 annual maxima: 100-year level is an extrapolation with wide CI",
                          "Dry-bulb only; wet-bulb/humidity (relevant to cooling) not modeled here",
                          "QC code meaning assumed from ISD convention; hourly aggregation uses mean of obs"]
    (ROOT / "models").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / f"models/temperature_params{TAG}.json", "w"), indent=1)
    fig.tight_layout(); fig.savefig(ROOT / f"figures/temperature{TAG}.png", dpi=120)


if __name__ == "__main__":
    main()
