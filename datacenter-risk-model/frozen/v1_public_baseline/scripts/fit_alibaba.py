"""Alibaba ASI GPU trace v2026: GPU request/job sizes, allocation and SM utilization -> data-center capacity utilization and an
EXPLICIT utilization->power mapping (assumption). Runs on whatever hourly partitions are present in data/raw/alibaba_2026/pod_hourly_sample.

Observed: pod GPU requests (summary table, 40.5M GPU pods), per-hour allocation fraction, SM utilization (avg_gpu_sm_util is summed over a
pod's GPUs, so per-GPU util = value / gpu_request), concurrent GPU footprint per workload_id (only ~42% of GPU pods carry a workload_id).
ASSUMPTION: node power = P_IDLE + (P_PEAK - P_IDLE) * util, with 4 GPUs/node endpoints anchored to NLR measurements.
Outputs models/alibaba_utilization_params.json, data/processed/alibaba_hourly_util.csv, figures/alibaba_utilization.png
Usage: python -I fit_alibaba.py
"""
import glob
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
QS = [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]
P_IDLE_KW, P_PEAK_KW, GPUS_PER_NODE = 0.6, 3.0, 4  # ASSUMPTION anchored to NLR 4-GPU H100 node: low state ~0.6 kW, high ~3.0 kW

# --- job sizes from summary
S = pd.read_parquet(ROOT / "data/interim/alibaba_summary/asi_opensource_job_execution_summary/part-000.parquet",
                    columns=["job_type_public", "gpu_request", "duration_hours", "workload_id"])
S = S[S.gpu_request > 0]
sizes = {}
for jt, g in S.groupby("job_type_public"):
    r = g.gpu_request
    sizes[jt] = dict(n=int(len(g)), frac_multi_gpu=float((r > 1).mean()), frac_fractional=float((r < 1).mean()),
                     gpu_request_q=np.quantile(r, QS).round(2).tolist(), max=float(r.max()),
                     duration_h_q=np.quantile(g.duration_hours.dropna(), QS).round(2).tolist())
print({k: (v["n"], v["frac_multi_gpu"], v["gpu_request_q"]) for k, v in sizes.items()})

# --- hourly sample
rows, groups = [], []
for f in sorted(glob.glob(str(ROOT / "data/raw/alibaba_2026/pod_hourly_sample/**/part-000.parquet"), recursive=True)):
    day, hour = (int(x) for x in re.search(r"day=(\d+)/hour=(\d+)", f).groups())
    try:
        d = pd.read_parquet(f, columns=["pod_id", "workload_id", "server_id", "server_gpu_count", "job_type_public", "gpu_request", "used_gpu_hours",
                                        "avg_gpu_sm_util"])
    except Exception as e:  # file still being written / truncated
        print("skip unreadable", f.split("pod_hourly_sample/")[-1], e.__class__.__name__)
        continue
    cap = d.drop_duplicates("server_id").server_gpu_count.sum()
    g = d[(d.gpu_request > 0) & (d.used_gpu_hours > 0)].copy()
    g["sm_total"] = g.avg_gpu_sm_util.clip(upper=100 * g.gpu_request) / 100  # GPU-equivalents of SM busy time; NaN where not reported
    known = g.sm_total.notna()
    row = dict(day=day, hour=hour, capacity_gpus=int(cap), alloc_frac=g.used_gpu_hours.sum() / cap,
               sm_util_frac=g.sm_total.sum() / cap * (g.used_gpu_hours.sum() / g.used_gpu_hours[known].sum()),  # scale for pods without SM report
               frac_pods_sm_reported=known.mean())
    for jt in ("training", "online_inference", "offline_inference"):
        row[f"alloc_{jt}"] = g[g.job_type_public == jt].used_gpu_hours.sum() / cap
    rows.append(row)
    w = g.dropna(subset=["workload_id"]).groupby(["workload_id", "job_type_public"]).agg(gpus=("used_gpu_hours", "sum"), pods=("pod_id", "nunique")).reset_index()
    w["day"], w["hour"] = day, hour
    groups.append(w)
H = pd.DataFrame(rows).sort_values(["day", "hour"])
H["node_power_kw_mean"] = P_IDLE_KW + (P_PEAK_KW - P_IDLE_KW) * H.sm_util_frac  # per-node (4 GPUs), fleet-average utilization
H.to_csv(ROOT / "data/processed/alibaba_hourly_util.csv", index=False)
W = pd.concat(groups)
print(H.round(3).to_string())
wsz = {jt: dict(n=int(len(g)), gpus_q=np.quantile(g.gpus, QS).round(1).tolist(), max=float(g.gpus.max()), frac_ge8=float((g.gpus >= 8).mean()))
       for jt, g in W.groupby("job_type_public") if len(g) > 20}
print(wsz)

out = dict(source_id="F2c/F2b", kind="observed (Alibaba ASI GPU trace v2026) + EXPLICIT power-mapping assumption",
           pod_gpu_request_by_type=sizes, concurrent_workload_gpu_footprint=wsz,
           hourly=dict(n_hours=len(H), days=sorted(H.day.unique().tolist()),
                       alloc_frac_q=np.quantile(H.alloc_frac, [0.05, 0.5, 0.95]).round(3).tolist(),
                       sm_util_frac_q=np.quantile(H.sm_util_frac, [0.05, 0.5, 0.95]).round(3).tolist(),
                       sm_util_frac_by_hour_of_day={int(h): round(float(v), 3) for h, v in H.groupby("hour").sm_util_frac.mean().items()}),
           power_mapping_assumption=dict(form="P_node = P_idle + (P_peak - P_idle) * sm_util", p_idle_kw=P_IDLE_KW, p_peak_kw=P_PEAK_KW,
                                         gpus_per_node=GPUS_PER_NODE, basis="NLR 4-GPU H100 node: training low state ~0.6 kW, high state ~3.0 kW. "
                                         "Alibaba fleet is mixed GPUs (H20, L20, A10, XPU...), so absolute power is NOT transferable; use fractions."),
           limitations=[f"Only {H.day.nunique()} day(s) / {len(H)} hours of the 185-day hourly table sampled via HTTP range extraction",
                        "Hourly averages hide sub-hour dynamics; SM utilization != power draw",
                        "avg_gpu_sm_util missing for fractional-GPU pods; scaled assuming same util as reporting pods",
                        "Concurrent group sizes only for pods with workload_id (~42%); 'workload' may not equal one synchronous job",
                        "Single Chinese hyperscaler cluster mix; not representative of a Texas facility"])
json.dump(out, open(ROOT / "models/alibaba_utilization_params.json", "w"), indent=1)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for day, g in H.groupby("day"):
    ax[0].plot(g.hour, g.sm_util_frac, "o-", label=f"day {day} SM util"); ax[0].plot(g.hour, g.alloc_frac, "--", label=f"day {day} allocated")
ax[0].set(xlabel="hour", ylabel="fraction of GPUs", title="Fleet allocation vs SM utilization"); ax[0].legend(fontsize=7)
for jt, g in W.groupby("job_type_public"):
    if len(g) > 50:
        x = np.sort(g.gpus.values); ax[1].plot(x, 1 - np.arange(1, len(x) + 1) / len(x), label=jt)
ax[1].set(xscale="log", yscale="log", xlabel="concurrent GPUs per workload_id", ylabel="exceedance", title="Concurrent workload size"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(ROOT / "figures/alibaba_utilization.png", dpi=120)
