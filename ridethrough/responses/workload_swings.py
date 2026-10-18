"""Power-swing amplitude and frequency by workload class, from the measured NLR GenAI power traces.

What this file is
    For each measured run, computes the swing amplitude (fraction of the run's peak power) and the dominant swing
    frequency, then summarizes training vs inference: category means, within-category spread, and the covariance of
    (osc_amp, osc_freq_hz) when workload is a driver.

Reads (read-only)
    datacenter-risk-model/data/interim/nlr_genai/01_aggregated_datasets/<set>/results/*.parquet   power[W] vs time [s]
        sets: training (Llama2-70B LoRA and Stable Diffusion, 2-16 nodes, 0.2 s), inference_offline / online_rate /
        online_finite (Llama3-70B, 0.1 s or 1 ms). NREL/NLR GenAI Power Profiles, Vercellino et al. (arXiv 2604.07345).
    <set>/metadata.csv   (training: model, nodes)

Writes (main())
    data_bayesian-network/network/responses/workload_swings_by_run.csv
    data_bayesian-network/network/responses/workload_swings_summary.csv
    data_bayesian-network/network/responses/workload_osc_block_by_mix.csv   (osc_amp, osc_freq_hz) moments vs P(training)

Definitions (all traces resampled to 0.2 s bins by averaging, so frequencies are limited to < 2.5 Hz)
    amp_2s_p99   99th percentile over time of (max - min of power in a sliding 2 s window) / peak power, peak = 99.9th
                 percentile of the run. Chosen over the single largest jump so it does not grow with run length.
    Trimming: TRIM (10%) of each run is cut from both ends before anything is computed.
    amp_2s_max   the single largest 2 s window, as in the Microsoft ASPLOS 2024 "largest jump in 2 s" metric.
    f_peak_hz    frequency of the largest Welch PSD peak in 0.2-2.5 Hz (mean removed).
    f_centroid_hz  PSD-weighted mean frequency in 0.2-2.5 Hz.
Caveats: power is per measured node group (2-16 nodes), not a campus, so amplitudes are for a synchronized group and
    the campus fraction needs the sync fraction (nlr_node_sync.csv). Only two workload classes were measured; "mixed"
    is not measured. Peak frequency is capped by the 0.2 s grid.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

REPO = Path(__file__).resolve().parents[2]
NLR = REPO / "datacenter-risk-model" / "data" / "interim" / "nlr_genai" / "01_aggregated_datasets"
OUT_DIR = REPO / "data_bayesian-network" / "network" / "responses"
SETS = {"training": "training", "inference_offline": "inference_offline_llama3_70b",
        "inference_online_rate": "inference_online_rate_llama3_70b", "inference_online_finite": "inference_online_finite_llama3_70b"}
WORKLOAD = {"training": "training", "inference_offline": "inference", "inference_online_rate": "inference",
            "inference_online_finite": "inference"}
DT = 0.2
F_LO, F_HI = 0.2, 2.5          # lower edge = master.csv osc_freq_hz low; the PSD otherwise peaks at the lowest bin
WIN = int(round(2.0 / DT))      # 2 s window in samples
MIN_SAMPLES = 100               # 20 s
TRIM = 0.10                     # fraction cut from each end: job start-up and shutdown ramps are not steady-state swings


def resample(t: np.ndarray, p: np.ndarray, dt: float = DT) -> np.ndarray:
    """Mean power in dt-wide bins. The 1e-6 keeps timestamps like 0.6000000000000001 / 0.2 out of the wrong bin."""
    b = np.floor((t - t[0]) / dt + 1e-6).astype(int)
    n = np.bincount(b)
    if (n == 0).any(): raise ValueError("empty bin after resampling: trace has gaps")
    return np.bincount(b, weights=p) / n


def swing_metrics(p: np.ndarray, dt: float = DT, trim: float = TRIM) -> dict:
    k0 = int(len(p) * trim); p = p[k0:len(p) - k0]
    peak = np.percentile(p, 99.9)
    w = np.lib.stride_tricks.sliding_window_view(p, WIN)
    rng2 = (w.max(1) - w.min(1)) / peak
    f, pxx = signal.welch(p - p.mean(), fs=1.0 / dt, nperseg=min(len(p), 1024))
    k = (f >= F_LO) & (f <= F_HI)
    return dict(n=len(p), peak_w=peak, amp_2s_p99=float(np.percentile(rng2, 99)), amp_2s_max=float(rng2.max()),
                dyn_range=float((np.percentile(p, 95) - np.percentile(p, 5)) / peak),
                f_peak_hz=float(f[k][np.argmax(pxx[k])]), f_centroid_hz=float((f[k] * pxx[k]).sum() / pxx[k].sum()))


def run_table(trim: float = TRIM) -> pd.DataFrame:
    rows = []
    for name, d in SETS.items():
        meta = pd.read_csv(NLR / d / "metadata.csv", index_col=0) if name == "training" else None
        for f in sorted((NLR / d / "results").glob("*.parquet")):
            df = pd.read_parquet(f)
            p = resample(df.index.to_numpy(float), df.iloc[:, 0].to_numpy(float))
            if len(p) < MIN_SAMPLES: continue
            r = dict(set=name, workload=WORKLOAD[name], run=f.stem, **swing_metrics(p, trim=trim))
            if meta is not None:
                m = meta.iloc[int(f.stem)] if int(f.stem) < len(meta) else None
                r["model"] = m["model"] if m is not None else ""; r["nodes"] = int(m["nodes"]) if m is not None else 0
            rows.append(r)
    return pd.DataFrame(rows)


def class_stats(runs: pd.DataFrame, weights: dict | None = None) -> dict:
    """Mixture moments of (osc_amp, osc_freq_hz) with workload as the driver.

    Inputs: per-run table; weights {class: probability} (default equal over the classes present).
    Output: dict with means per class, within-class covariance, between-class covariance (the part the workload driver
        explains), total covariance and correlation. Runs within a class are weighted equally by class (each run's
        weight is 1/n of its class) so the large online sets do not dominate; the sets inside a class are pooled by runs.
    """
    cols = ["amp_2s_p99", "f_peak_hz"]
    classes = sorted(runs.workload.unique())
    w = weights or {c: 1.0 / len(classes) for c in classes}
    mu = {c: runs.loc[runs.workload == c, cols].mean().to_numpy() for c in classes}
    within = {c: np.cov(runs.loc[runs.workload == c, cols].to_numpy().T) for c in classes}
    m = sum(w[c] * mu[c] for c in classes)
    between = sum(w[c] * np.outer(mu[c] - m, mu[c] - m) for c in classes)
    within_mix = sum(w[c] * within[c] for c in classes)
    total = between + within_mix
    sd = np.sqrt(np.diag(total))
    return dict(cols=cols, weights=w, mean=mu, within=within, between=between, within_mix=within_mix, total=total,
                corr=total / np.outer(sd, sd), mix_mean=m)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runs = run_table(); runs.to_csv(OUT_DIR / "workload_swings_by_run.csv", index=False)
    g = runs.groupby(["workload", "set"]).agg(n_runs=("run", "size"), amp_p99_mean=("amp_2s_p99", "mean"), amp_p99_sd=("amp_2s_p99", "std"),
                                              amp_max_mean=("amp_2s_max", "mean"), f_peak_median=("f_peak_hz", "median"),
                                              f_peak_sd=("f_peak_hz", "std"), f_centroid_mean=("f_centroid_hz", "mean")).reset_index()
    g.to_csv(OUT_DIR / "workload_swings_summary.csv", index=False)
    print(g.round(3).to_string())
    rows = []
    for pt in np.round(np.arange(0.1, 1.0, 0.2), 1):
        s = class_stats(runs, {"training": pt, "inference": 1 - pt})
        rows.append(dict(p_training=pt, amp_mean=s["mix_mean"][0], amp_sd=np.sqrt(s["total"][0, 0]), freq_mean=s["mix_mean"][1],
                         freq_sd=np.sqrt(s["total"][1, 1]), corr_amp_freq=s["corr"][0, 1],
                         amp_between_share=s["between"][0, 0] / s["total"][0, 0], freq_between_share=s["between"][1, 1] / s["total"][1, 1]))
    sw = pd.DataFrame(rows); sw.to_csv(OUT_DIR / "workload_osc_block_by_mix.csv", index=False)
    print(sw.round(3).to_string())


if __name__ == "__main__":
    main()
