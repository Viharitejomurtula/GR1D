"""Export everything the models have actually produced to one JSON file for the frontend.

Reads models/*.json, data/processed/nlr_node_sync.csv, sources.csv, config.yaml.
Writes ../frontend/public/report.json. Sections the pipeline has not produced yet are exported as null
(never filled with placeholders); the frontend shows them as pending.
Usage: python -I scripts/export_report.py
"""
import json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "frontend" / "public" / "report.json"
load = lambda p: json.load(open(ROOT / p)) if (ROOT / p).exists() else None

cfg = yaml.safe_load(open(ROOT / "config.yaml"))
src = pd.read_csv(ROOT / "sources.csv").fillna("")
battery = load("models/battery_capacity_params.json")
train = load("models/ai_load_swing_params.json")
infer = load("models/ai_inference_swing_params.json")
temp = load("models/temperature_params.json")

# ---- battery fade fan: SOH(n) = exp(-k n), k ~ LogNormal(mu, sigma)
fade = None
if battery:
    mu, sg = battery["mu_log_k"], battery["sigma_log_k"]
    kq = lambda p: float(np.exp(mu + sg * stats.norm.ppf(p)))
    fade = {
        "mu": mu, "sigma": sg, "mu_ci95": battery["mu_ci95"], "sigma_ci95": battery["sigma_ci95"],
        "n_cells": battery["n_cells"], "temp_range_c": battery["temp_range_c"],
        "cycles_to_70": dict(zip(["p5", "p50", "p95"], battery["cycles_to_70pct_soh_5_50_95"])),
        "curve": [{"n": n, "p5": float(np.exp(-kq(0.95) * n)), "p50": float(np.exp(-kq(0.5) * n)), "p95": float(np.exp(-kq(0.05) * n))}
                  for n in range(0, 301, 5)],
        "temp_effect": battery["temp_effect"], "limitations": battery["limitations"],
    }

# ---- AI load swings (1 s ramp quantiles are [p50, p90, p99, p999], W/s per node)
ai = None
if train and infer:
    rows = []
    for key, v in train["ramps"].items():
        wl, nodes, win = key.split("|")
        if win == "1s":
            rows.append({"workload": wl, "nodes": int(nodes.replace("nodes", "")), "p50": v["up"][0], "p90": v["up"][1], "p99": v["up"][2], "p999": v["up"][3]})
    modes = {}
    for key, v in infer["ramps"].items():
        mode, _, win = key.split("|")
        if win == "1s":
            modes.setdefault(mode.replace("_llama3_70b", "").replace("inference_", ""), []).append(v["abs"][2])
    inference = [{"mode": m, "configs": len(x), "p99_min": float(min(x)), "p99_median": float(np.median(x)), "p99_max": float(max(x))} for m, x in modes.items()]
    ai = {"training": sorted(rows, key=lambda r: (r["workload"], r["nodes"])), "inference": inference,
          "training_runs": train["runs_used"], "inference_runs": infer["runs_used"],
          "limitations": train["limitations"] + infer["limitations"]}

# ---- node synchronization
sync = None
sp = ROOT / "data/processed/nlr_node_sync.csv"
if sp.exists():
    d = pd.read_csv(sp)
    g = d.groupby("n_nodes").agg(jobs=("job", "count"), sync=("sync_ratio", "median"), indep=("indep_ratio", "first"), corr=("mean_pair_corr", "median"), min_corr=("min_pair_corr", "min"))
    sync = [{"nodes": int(n), "jobs": int(r.jobs), "sync_ratio": float(r.sync), "indep_ratio": float(r.indep), "corr": float(r["corr"]), "min_corr": float(r.min_corr)} for n, r in g.iterrows()]

# ---- factor coverage, from what exists on disk
fitted = {"F1b": ai is not None, "F2d": fade is not None, "F1c": temp is not None, "F2b": sync is not None}
note = {"F1c": "fit script exists, not yet run", "F2b": "NLR GPU-power sync measured (training, up to 16 nodes); Alibaba traces not used"}
factors = []
for _, r in src.iterrows():
    if "-ev" in r["id"]:
        continue
    factors.append({"id": r["id"], "name": r["factor"], "category": int(r["category"]), "source": r["source"], "url": r["url"],
                    "status": "fitted" if fitted.get(r["id"]) else "pending", "note": note.get(r["id"], r["notes"])})

report = {
    "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "scenario": {"grid": cfg["location"]["grid"], "region": cfg["location"]["region"], "battery": cfg["hardware"]["battery"], "capacitor": cfg["hardware"]["dc_link_capacitor"]},
    "factors": factors,
    "battery": fade,
    "aiLoad": ai,
    "sync": sync,
    "results": None,
    "pending": [
        "Voltage-dip joint model (F2a): no event data ingested yet",
        "Physics simulators and neural surrogate: not built",
        "Failure search, factor importance, smallest-fix and what-if analysis: not built",
    ],
}
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(report, open(OUT, "w"), indent=1)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes); fitted: {[k for k, v in fitted.items() if v]}")
