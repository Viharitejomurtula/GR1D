"""ERCOT frequency deviation (mHz from 60 Hz) and RoCoF body distributions from Open Frequency Database US_TX01/US_TX02 (1 s).

Empirical-first: stores quantiles and clean contiguous trajectory blocks so joint (deviation, RoCoF) behavior is preserved when
sampling. Validation: RMS vs ERCOT published RMS1 (15.6 mHz, 2023 PDCWG), and two-sample KS between the two files.
Outputs: data/processed/frequency_blocks.parquet, models/frequency_body_params.json, figures/frequency_body.png
Usage: python -I fit_frequency_body.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
BLOCK = 300  # seconds per stored trajectory block
QS = [0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999]


def load(n):
    d = pd.read_csv(ROOT / f"data/raw/open_frequency_db/FrequencyData/{n}/{n}.csv", sep=";", parse_dates=["Time"])
    d.columns = ["t", "dev_mhz", "qi"]
    d["good"] = d.qi == 0
    d = d.set_index("t").asfreq("1s")
    d.loc[d.good.isna() | ~d.good.fillna(False).astype(bool), "dev_mhz"] = np.nan
    return d.dev_mhz


def main():
    res, blocks, series = {}, [], {}
    for n in ("US_TX01", "US_TX02"):
        s = load(n)
        series[n] = s
        v = s.dropna()
        r1 = s.diff().dropna()  # mHz/s, 1 s
        r10 = ((s - s.shift(10)) / 10).dropna()
        ac = [float(s.autocorr(l)) for l in (1, 10, 60, 300)]
        res[n] = dict(n=int(len(v)), days=round(len(s) / 86400, 2), mean=float(v.mean()), rms=float(np.sqrt((v ** 2).mean())),
                      std=float(v.std()), dev_q=np.quantile(v, QS).round(2).tolist(), rocof1s_q=np.quantile(r1, QS).round(2).tolist(),
                      rocof10s_q=np.quantile(r10, QS).round(3).tolist(), rocof1s_abs_max=float(r1.abs().max()),
                      autocorr_lags_1_10_60_300s=[round(a, 3) for a in ac])
        # contiguous good blocks
        arr = s.values
        for i in range(0, len(arr) - BLOCK + 1, BLOCK):
            seg = arr[i:i + BLOCK]
            if not np.isnan(seg).any():
                blocks.append(dict(source=n, start=str(s.index[i]), hour=int(s.index[i].hour), dev_mhz=seg.tolist()))
    pd.DataFrame(blocks).to_parquet(ROOT / "data/processed/frequency_blocks.parquet")
    ks = stats.ks_2samp(series["US_TX01"].dropna(), series["US_TX02"].dropna())
    allv = pd.concat(series.values()).dropna()
    out = dict(source_id="F1a", kind="observed (Open Frequency Database, Texas, 1 s, 2019-05; 5.1 days total)",
               units=dict(deviation="mHz from 60 Hz", rocof="mHz/s"), quantiles=QS, files=res,
               pooled=dict(rms=float(np.sqrt((allv ** 2).mean())), std=float(allv.std())),
               validation=dict(ercot_published_rms1_mhz_2023=[12.48, 18.21], ks_between_files=dict(stat=float(ks.statistic), p=float(ks.pvalue)),
                               pooled_rms_in_published_range=bool(12.48 <= np.sqrt((allv ** 2).mean()) <= 18.21)),
               sampling=dict(method=f"resample {BLOCK}-s contiguous blocks from data/processed/frequency_blocks.parquet", n_blocks=len(blocks)),
               limitations=["5.1 days in one May window: no seasonal, load-level or diurnal coverage", "Body only: tails come from event model (frequency_tail)",
                            "Measurement site/accuracy not verified; 1 s resolution misses sub-second RoCoF", "QI==0 samples only (2-4% flagged bad)"])
    json.dump(out, open(ROOT / "models/frequency_body_params.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k in ("pooled", "validation", "sampling")}, indent=1))
    for n, r in res.items():
        print(n, "rms %.1f std %.1f" % (r["rms"], r["std"]), "dev q", r["dev_q"], "rocof1s q", r["rocof1s_q"], "acf", r["autocorr_lags_1_10_60_300s"])
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for n, s in series.items():
        v = s.dropna(); ax[0].hist(v, bins=100, histtype="step", density=True, label=n)
        ax[1].hist(s.diff().dropna(), bins=100, histtype="step", density=True, label=n)
    ax[0].set(xlabel="deviation mHz", title="Frequency deviation"); ax[0].legend()
    ax[1].set(yscale="log", xlabel="RoCoF mHz/s (1 s)", title="RoCoF"); ax[2].plot(series["US_TX02"].iloc[:3600].values); ax[2].set(title="1 h sample", xlabel="s", ylabel="mHz")
    fig.tight_layout(); fig.savefig(ROOT / "figures/frequency_body.png", dpi=120)


if __name__ == "__main__":
    main()
