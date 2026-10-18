"""Test node synchronization in NLR multi-node training runs from raw per-node GPU logs.

Per job: node GPU power (sum of 4 GPUs, W) on a 0.2 s grid; metrics on 1 s power differences:
  sync_ratio = std(sum over nodes) / sum(std per node)  (1 = lockstep, 1/sqrt(N) = independent)
  mean pairwise correlation, and median |lag| of the best cross-correlation within +-2 s.
Usage: python node_sync.py <00_raw_datasets dir>
Writes data/processed/nlr_node_sync.csv
"""
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FMT = "%Y-%m-%d_%H:%M:%S.%f"


def load_node(f: Path) -> pd.Series:
    with open(f) as fh:
        cols = [c for c in fh.readline().split() if c != "#"]
    d = pd.read_csv(f, sep=r"\s+", engine="python", header=None, skiprows=1, names=cols, index_col=False)
    gpu = [c for c in d.columns if re.fullmatch(r"gpu-\d+\[mW\]", c)]
    t = pd.to_datetime(d["timestamp"], format=FMT)
    w = d[gpu].apply(pd.to_numeric, errors="coerce").sum(axis=1) / 1000.0
    s = pd.Series(w.values, index=t).groupby(level=0).mean()
    return s.resample("200ms").mean().interpolate(limit=5)


def analyze(series: list[pd.Series]):
    df = pd.concat(series, axis=1, join="inner").dropna()
    if len(df) < 1500:
        return None
    n = df.shape[1]
    d = df.diff(5).dropna()  # 1 s differences
    ratio = d.sum(axis=1).std() / d.std().sum()
    corr = d.corr().values[np.triu_indices(n, 1)]
    lags = []
    for a, b in list(combinations(range(n), 2))[:30]:
        x, y = d.iloc[:, a].values, d.iloc[:, b].values
        x, y = x - x.mean(), y - y.mean()
        cc = [np.corrcoef(x[max(0, k):len(x) + min(0, k)], y[max(0, -k):len(y) - max(0, k)])[0, 1] for k in range(-10, 11)]
        lags.append(abs(int(np.argmax(cc)) - 10) * 0.2)
    return dict(n_nodes=n, seconds=len(df) * 0.2, sync_ratio=ratio, indep_ratio=1 / np.sqrt(n),
                mean_pair_corr=float(np.mean(corr)), min_pair_corr=float(np.min(corr)), median_best_lag_s=float(np.median(lags)))


def main(src: Path):
    rows = []
    for model in ("training_llama2_70b_lora", "training_stable_diffusion"):
        for nd in sorted((src / model).glob("*node")):
            if nd.name == "1node":
                continue
            jobs = defaultdict(list)
            for f in nd.glob("nvml_*.log"):
                jobs[re.search(r"slurmid_(\d+)", f.name).group(1)].append(f)
            for jid, fs in jobs.items():
                try:
                    r = analyze([load_node(f) for f in fs])
                except Exception as e:
                    print("skip", model, nd.name, jid, e); continue
                if r:
                    rows.append(dict(model=model, node_dir=nd.name, job=jid, **r))
    S = pd.DataFrame(rows)
    S.to_csv(ROOT / "data/processed/nlr_node_sync.csv", index=False)
    print(S.groupby(["model", "node_dir"]).agg(jobs=("job", "size"), sync_ratio=("sync_ratio", "median"), indep=("indep_ratio", "first"),
                                              corr=("mean_pair_corr", "median"), min_corr=("min_pair_corr", "min"), lag=("median_best_lag_s", "median")).round(2).to_string())


if __name__ == "__main__":
    main(Path(sys.argv[1]))
