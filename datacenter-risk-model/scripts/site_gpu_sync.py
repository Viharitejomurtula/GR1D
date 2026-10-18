"""Site-scale AI load swing and ramp: facility Monte Carlo at the site's MW, hardware-agnostic via normalized power shapes.

Observed inputs: job-size distribution (Alibaba concurrent GPUs per training workload) and NLR training power trajectories, each normalized by its own mean
(power shape = fraction of mean). Scenario inputs (ASSUMED, from site_profile.json / user): IT load MW, training share, kW per GPU (all-in IT power per GPU
for the actual hardware generation), and rho = fraction of jobs sharing one phase.
GPUs = training MW / kW_per_GPU. Aggregate = sum over jobs of (job GPUs * kW_per_GPU) * shape(t).
Outputs p99-p1 swing (MW), std (MW) and 1 s ramp p99/p99.9 (MW/s) -> site/abilene/gpu_sync_site.json
Usage: python -I site_gpu_sync.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A = json.load(open(ROOT / "models/alibaba_utilization_params.json"))
Q = np.array([0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999])
gq = np.array(A["concurrent_workload_gpu_footprint"]["training"]["gpus_q"])
meta = pd.read_csv(ROOT / "data/interim/nlr_genai/01_aggregated_datasets/training/metadata.csv", index_col=0)
shapes = []
for i, m in meta.iterrows():
    p = pd.read_parquet(ROOT / "data/interim/nlr_genai/01_aggregated_datasets" / m["path_save"])["power[W]"].dropna().values
    if len(p) > 3000:
        shapes.append(p[:3000] / p[:3000].mean())
S = np.array(shapes); print("shapes", S.shape)
rng = np.random.default_rng(0)
prof = json.load(open(ROOT / "site/abilene/site_profile.json"))["scenario_inputs"]
SHARE = prof["training_share_of_load"]
res = {}


def facility(train_mw, kw_gpu, rho, reps=12):
    gpus_total = train_mw * 1000 / kw_gpu
    T = S.shape[1]; t = np.arange(T)
    out = []
    for _ in range(reps):
        n_draw = int(gpus_total / max(1.0, np.interp(0.5, Q, gq)) * 3) + 100
        g = np.maximum(1.0, np.interp(rng.uniform(0, 0.999, n_draw), Q, gq))
        cum = np.cumsum(g); k = np.searchsorted(cum, gpus_total) + 1
        sizes = g[:k].copy(); sizes[-1] -= cum[k - 1] - gpus_total
        w = sizes * kw_gpu / 1000.0                                  # MW of each job
        idx = rng.integers(len(S), size=k); rolls = rng.integers(T, size=k); is_sh = rng.uniform(size=k) < rho
        agg = np.zeros(T)
        shared = S[rng.integers(len(S))]
        agg += w[is_sh].sum() * shared
        ind = np.where(~is_sh)[0]
        for c0 in range(0, len(ind), 400):                         # chunked gather
            sel = ind[c0:c0 + 400]
            cols = (t[None, :] + rolls[sel][:, None]) % T
            agg += (w[sel][:, None] * S[idx[sel][:, None], cols]).sum(axis=0)
        ramp1 = np.abs(agg[5:] - agg[:-5])
        out.append((np.percentile(agg, 99) - np.percentile(agg, 1), agg.std(), np.percentile(ramp1, 99), np.percentile(ramp1, 99.9), agg.mean(), k))
    o = np.array(out).mean(axis=0)
    return dict(swing_p99_p1_mw=round(float(o[0]), 1), std_mw=round(float(o[1]), 1), ramp_1s_p99_mw_per_s=round(float(o[2]), 1), ramp_1s_p999_mw_per_s=round(float(o[3]), 1),
                mean_training_mw=round(float(o[4]), 1), n_jobs=int(o[5]))


for load in (200, 600, 1200):
    for kw in (1.25, 1.75, 2.25):
        for rho in (0.0, 0.25, 1.0):
            r = facility(load * SHARE, kw, rho)
            res[f"load{load}MW_kwgpu{kw}_rho{rho}"] = r
            print(load, kw, rho, r, flush=True)
json.dump(dict(kind="site-scale facility MC; job sizes + power shapes observed, MW/kW-per-GPU/rho are scenario inputs", training_share=SHARE, results=res,
               note="swing scales ~linearly with load only when rho=1; for independent jobs it grows more slowly (central-limit averaging)",
               limitations=["kW per GPU and training share are placeholders", "power shapes from H100 training runs of 2-16 nodes applied to other hardware as normalized fractions",
                            "job sizes from Alibaba (not this site's scheduler)", "rho unobservable"]), open(ROOT / "site/abilene/gpu_sync_site.json", "w"), indent=1)
