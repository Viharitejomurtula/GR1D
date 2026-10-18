"""Ramp-rate and swing distributions from NLR GenAI aggregated training traces (0.2 s total power per run).

For each run: power per node (W) -> ramps over lag L (P[t+L]-P[t])/L and swings (max-min within a window W).
Outputs data/processed/nlr_training_swing_stats.csv (per-run), models/ai_load_swing_params.json
(pooled empirical quantiles by timescale and node count) and figures/ai_load_swings.png.
Usage: python -I extract_load_swings.py <01_aggregated_datasets/training dir>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DT = 0.2
LAGS_S = [0.2, 1, 5, 10]  # ramp timescales
WINS_S = [1, 5, 30]  # swing windows
QS = [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]


def run_stats(p: np.ndarray, nodes: int):
    pn = p / nodes  # W per node
    med = np.median(pn)
    out = {"median_w_per_node": med, "p5_w": np.percentile(pn, 5), "p95_w": np.percentile(pn, 95)}
    ramps = {}
    for L in LAGS_S:
        k = int(round(L / DT))
        r = (pn[k:] - pn[:-k]) / L  # W/s per node
        ramps[L] = r
        out[f"ramp_up_p99_{L}s"] = np.percentile(r, 99)
        out[f"ramp_dn_p01_{L}s"] = np.percentile(r, 1)
        out[f"ramp_absmax_{L}s"] = np.abs(r).max()
    swings = {}
    s = pd.Series(pn)
    for W in WINS_S:
        k = int(round(W / DT))
        sw = (s.rolling(k).max() - s.rolling(k).min()).dropna().values  # W per node
        swings[W] = sw
        out[f"swing_p99_{W}s"] = np.percentile(sw, 99)
        out[f"swing_max_{W}s"] = sw.max()
    return out, ramps, swings, med


def main(src: Path):
    meta = pd.read_csv(src / "metadata.csv", index_col=0)
    rows, pooled_r, pooled_s = [], {}, {}
    for i, m in meta.iterrows():
        f = src.parent / m["path_save"]
        if not f.exists():
            print("missing", f); continue
        p = pd.read_parquet(f)["power[W]"].dropna().values
        if len(p) < 600:
            print("short run", f.name, len(p)); continue
        st, ramps, swings, med = run_stats(p, int(m["nodes"]))
        rows.append(dict(run=f.stem, model=m["model"], nodes=int(m["nodes"]), repeat=int(m["repeat"]), n_samples=len(p),
                         duration_s=len(p) * DT, **st))
        key = (m["model"], int(m["nodes"]))
        for L, r in ramps.items():
            pooled_r.setdefault((key, L), []).append(r)
        for W, sw in swings.items():
            pooled_s.setdefault((key, W), []).append(sw)
    S = pd.DataFrame(rows)
    (ROOT / "data/processed").mkdir(exist_ok=True)
    S.to_csv(ROOT / "data/processed/nlr_training_swing_stats.csv", index=False)
    print(S.groupby(["model", "nodes"])[["median_w_per_node", "p5_w", "p95_w", "ramp_up_p99_1s", "ramp_dn_p01_1s",
                                          "swing_p99_5s"]].median().round(0).to_string())

    params = dict(source_id="F1b", kind="observed (NLR GenAI power profiles, training runs, 0.2 s aggregate power)",
                  units=dict(ramp="W/s per node", swing="W per node (max-min within window)"),
                  quantiles=QS, runs_used=len(S), ramps={}, swings={})
    for (key, L), lst in pooled_r.items():
        r = np.concatenate(lst)
        params["ramps"][f"{key[0]}|{key[1]}nodes|{L}s"] = dict(
            n=len(r), up=np.quantile(r[r > 0], QS).round(1).tolist(), down=np.quantile(-r[r < 0], QS).round(1).tolist())
    for (key, W), lst in pooled_s.items():
        sw = np.concatenate(lst)
        params["swings"][f"{key[0]}|{key[1]}nodes|{W}s"] = dict(n=len(sw), q=np.quantile(sw, QS).round(0).tolist())
    params["limitations"] = [
        "Research cluster (Kestrel), MLPerf-style training jobs; not a production fleet mix",
        "Per-node values divide the aggregate by node count: assumes nodes are identical/synchronized-in-average, hides per-node timing",
        "Only 2-16 node runs; extrapolation to thousands of GPUs needs explicit synchronization assumptions",
        "Runs are minutes to ~1 h; checkpoint/failure events and rare stalls are under-sampled"]
    (ROOT / "models").mkdir(exist_ok=True)
    json.dump(params, open(ROOT / "models/ai_load_swing_params.json", "w"), indent=1)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for (key, L), lst in sorted(pooled_r.items(), key=lambda x: str(x[0])):
        if L == 1 and key[1] in (2, 16):
            r = np.sort(np.abs(np.concatenate(lst)))
            ax[0].plot(r, 1 - np.arange(1, len(r) + 1) / len(r), label=f"{key[0]} {key[1]}n")
    ax[0].set(xscale="log", yscale="log", xlabel="|ramp| W/s per node (1 s lag)", ylabel="exceedance prob", title="Ramp-rate tails"); ax[0].legend(fontsize=7)
    for (key, W), lst in sorted(pooled_s.items(), key=lambda x: str(x[0])):
        if W == 5:
            ax[1].hist(np.concatenate(lst), bins=60, histtype="step", density=True, label=f"{key[0][:6]} {key[1]}n")
    ax[1].set(xlabel="5 s swing, W per node", title="Swing magnitude"); ax[1].legend(fontsize=7)
    fig.tight_layout(); (ROOT / "figures").mkdir(exist_ok=True); fig.savefig(ROOT / "figures/ai_load_swings.png", dpi=120)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
