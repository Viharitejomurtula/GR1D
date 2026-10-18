"""Ramp/swing statistics for NLR Llama3-70B inference traces (single node, 0.2 s), grouped by load setting.
Usage: python extract_inference_swings.py <01_aggregated_datasets dir>
Writes data/processed/nlr_inference_swing_stats.csv and models/ai_inference_swing_params.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from extract_load_swings import QS, ROOT, run_stats

SETS = {  # dir -> column holding the load setting
    "inference_offline_llama3_70b": "batch_size",
    "inference_online_finite_llama3_70b": "request_rate_x",
    "inference_online_rate_llama3_70b": "request_rate",
}


def main(src: Path):
    rows, pooled_r, pooled_s = [], {}, {}
    for name, col in SETS.items():
        meta = pd.read_csv(src / name / "metadata.csv")
        for i, m in meta.iterrows():
            f = src / name / "results" / f"{i:06d}.parquet"
            if not f.exists():
                continue
            p = pd.read_parquet(f)["power[W]"].dropna().values
            if len(p) < 300:
                continue
            st, ramps, swings, _ = run_stats(p, 1)
            setting = float(m[col])
            rows.append(dict(set=name, setting=setting, run=f.stem, n_samples=len(p), **st))
            for L, r in ramps.items():
                pooled_r.setdefault((name, setting, L), []).append(r)
            for W, sw in swings.items():
                pooled_s.setdefault((name, setting, W), []).append(sw)
    S = pd.DataFrame(rows)
    S.to_csv(ROOT / "data/processed/nlr_inference_swing_stats.csv", index=False)
    g = S.groupby(["set", "setting"])[["median_w_per_node", "p5_w", "p95_w", "ramp_up_p99_1s", "ramp_dn_p01_1s", "swing_p99_5s"]].median().round(0)
    print(g.to_string())
    params = dict(source_id="F1b", kind="observed (NLR GenAI inference, Llama3-70B, 1 node, 0.2 s)",
                  units=dict(ramp="W/s per node", swing="W per node"), quantiles=QS, runs_used=len(S), ramps={}, swings={})
    for (n, s, L), lst in pooled_r.items():
        r = np.concatenate(lst)
        params["ramps"][f"{n}|{s:g}|{L}s"] = dict(n=len(r), abs=np.quantile(np.abs(r), QS).round(1).tolist())
    for (n, s, W), lst in pooled_s.items():
        sw = np.concatenate(lst)
        params["swings"][f"{n}|{s:g}|{W}s"] = dict(n=len(sw), q=np.quantile(sw, QS).round(0).tolist())
    params["limitations"] = ["Single node only; no multi-node inference traces", "vLLM benchmark traffic, not production request patterns",
                             "Runs are 1-3 minutes"]
    json.dump(params, open(ROOT / "models/ai_inference_swing_params.json", "w"), indent=1)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
