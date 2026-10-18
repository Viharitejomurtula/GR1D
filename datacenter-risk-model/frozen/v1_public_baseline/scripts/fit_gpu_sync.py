"""GPU synchronization (Factor #2): aggregate facility power swing from job sizes (Alibaba, observed) and per-node swings (NLR, observed)
under explicit synchronization assumptions.

OBSERVED: (a) concurrent GPUs per training workload (Alibaba); (b) nodes within a job swing in lockstep (NLR, corr 0.97-0.98 up to 16 nodes);
(c) per-node power level distribution of training (NLR, 0.2 s).
ASSUMED (labelled): (1) lockstep holds within a job of any size (beyond 16 nodes is extrapolation); (2) across jobs, a fraction RHO of training jobs
share phase (RHO=0 independent random phase, RHO=1 all aligned); facility size and training share of GPUs.
Method: Monte Carlo facility = jobs drawn until the training GPU budget is filled; each job toggles the NLR per-node power distribution
(sampled per-node trajectory blocks) for nodes_j = ceil(GPUs_j/4); aggregate std and p99-p1 range reported for RHO in {0,.25,.5,1}.
Outputs models/gpu_sync_params.json, figures/gpu_sync.png.  Usage: python -I fit_gpu_sync.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A = json.load(open(ROOT / "models/alibaba_utilization_params.json"))
Q = np.array([0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999])
gq = np.array(A["concurrent_workload_gpu_footprint"]["training"]["gpus_q"])
FAC_GPUS, TRAIN_SHARE, GPN = 10_000, 0.20, 4  # ASSUMED facility; training share ~0.16-0.19 of allocated GPUs in Alibaba sample
rng = np.random.default_rng(0)

# per-node training power trajectories (W/node, 0.2 s) from NLR aggregated runs (observed)
meta = pd.read_csv(ROOT / "data/interim/nlr_genai/01_aggregated_datasets/training/metadata.csv", index_col=0)
trajs = []
for i, m in meta.iterrows():
    p = pd.read_parquet(ROOT / "data/interim/nlr_genai/01_aggregated_datasets" / m["path_save"])["power[W]"].dropna().values / m["nodes"]
    if len(p) > 3000:
        trajs.append(p[:3000])
T = np.array(trajs); print("trajectories", T.shape, "per-node mean/std W:", T.mean().round(0), T.std().round(0))


def draw_job_nodes():
    g = np.interp(rng.uniform(0, 0.999), Q, gq)
    return max(1, int(np.ceil(g / GPN)))


def facility(rho, n_rep=200):
    out = []
    budget = int(FAC_GPUS * TRAIN_SHARE / GPN)
    for _ in range(n_rep):
        nodes, tot = [], 0
        while tot < budget:
            n = draw_job_nodes(); n = min(n, budget - tot); nodes.append(n); tot += n
        shared = T[rng.integers(len(T))]  # phase-shared trajectory
        agg = np.zeros(T.shape[1])
        for n in nodes:
            tr = shared if rng.uniform() < rho else np.roll(T[rng.integers(len(T))], rng.integers(T.shape[1]))
            agg += n * tr
        out.append((agg.std() / 1e6, (np.percentile(agg, 99) - np.percentile(agg, 1)) / 1e6, agg.mean() / 1e6, len(nodes), max(nodes)))
    o = np.array(out)
    return dict(std_mw_mean=float(o[:, 0].mean()), range_p99_p1_mw_mean=float(o[:, 1].mean()), range_p99_p1_mw_p5_p95=np.percentile(o[:, 1], [5, 95]).round(2).tolist(),
                mean_training_power_mw=float(o[:, 2].mean()), jobs_per_facility_mean=float(o[:, 3].mean()), largest_job_nodes_mean=float(o[:, 4].mean()))


res = {f"rho_{r}": facility(r) for r in (0.0, 0.25, 0.5, 1.0)}
for k, v in res.items():
    print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items()})
out = dict(source_id="F2b", kind="observed job sizes (Alibaba) + observed within-job lockstep (NLR) + ASSUMED cross-job phase sharing",
           units="MW", facility=dict(gpus=FAC_GPUS, training_share_assumed=TRAIN_SHARE, gpus_per_node=GPN, training_nodes=int(FAC_GPUS * TRAIN_SHARE / GPN)),
           assumptions=dict(within_job="full lockstep at any size (measured corr 0.97-0.98 up to 16 nodes; extrapolated beyond)",
                            cross_job="rho = fraction of training jobs sharing one phase; rho unknown - bounds only (0 = independent random phase, 1 = all aligned)"),
           results_by_rho=res, group_size_quantiles=dict(q=Q.tolist(), gpus=gq.tolist()),
           limitations=["Cross-job synchronization is NOT observable in either dataset: rho is a free scenario parameter",
                        "Job sizes from Alibaba (workload_id groups, ~42% of GPU pods); NLR trajectories are 2-16 node research runs",
                        "Aggregated per-node trajectories already average over nodes in a run; treated as one job-level power shape",
                        "Facility size and training share are placeholders; scale results linearly with training GPUs"])
(ROOT / "models/gpu_sync_params.json").write_text(json.dumps(out, indent=1))
fig, ax = plt.subplots(figsize=(6, 4))
rs = [0.0, 0.25, 0.5, 1.0]; ax.bar([str(r) for r in rs], [res[f"rho_{r}"]["range_p99_p1_mw_mean"] for r in rs])
ax.set(xlabel="rho (fraction of jobs sharing phase)", ylabel="p99-p1 aggregate swing MW", title="Facility training load swing (10k GPUs, 20% training)")
fig.tight_layout(); fig.savefig(ROOT / "figures/gpu_sync.png", dpi=120)
