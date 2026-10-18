"""Illustrative per-depth outcomes for the Results tab (hand-set, NOT model output). Overwrites depth_outcomes.json with the
same schema as scripts/export_depth_outcomes.py, flagged "illustrative": true. Re-run export_depth_outcomes.py to restore
the surrogate's numbers."""
import json, math, pathlib
import numpy as np

SITE_MW = 800.0
OUT = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "depth_outcomes.json"
edges = np.linspace(0, 1, 21)


def pass_rate(d):
    return 0.02 + 0.97 / (1 + math.exp(-(d - 0.45) / 0.08))


def factors(d):
    if d < 0.35:
        return [("Fault type (phases involved)", 0.38), ("Reclosing (second dip and gap)", 0.27), ("Protection clearing (normal / breaker problem)", 0.17)]
    if d < 0.7:
        return [("Site load level", 0.34), ("Season and outdoor temperature", 0.26), ("Fault type (phases involved)", 0.19)]
    return [("Workload type (power-swing size and rate)", 0.36), ("Battery state of charge", 0.24), ("Equipment age", 0.18)]


def modes(d, fail):
    if d < 0.25:
        w = {"voltage collapse": 0.7, "below power floor": 0.3}
    elif d < 0.6:
        w = {"below power floor": 0.55, "exceeded current cap": 0.3, "voltage collapse": 0.15}
    else:
        w = {"cooling tripped": 0.45, "exceeded current cap": 0.35, "storage hand-back too slow": 0.2}
    return {m: fail * v for m, v in w.items()}


rng = np.random.default_rng(0)
depths = []
for d in np.round(np.arange(0, 1.0001, 0.05), 2):
    p = pass_rate(d)
    n = 5000
    k = int(round(n * p))
    ok = np.clip(rng.gamma(2.0, 0.012 + 0.03 * (1 - d), k), 0, 1)                 # rides through: a few % of load dips
    bad = np.clip(rng.normal(0.55 + 0.35 * (1 - d), 0.12, n - k), 0.15, 1)       # fails: most of the load leaves the grid
    drop = np.concatenate([ok, bad])
    counts, _ = np.histogram(drop, bins=edges)
    depths.append({
        "depth": float(d), "pass": p, "fail": 1 - p, "fail_by_mode": modes(d, 1 - p),
        "mw_dropped": {"share_edges": edges.tolist(), "counts": counts.tolist(), "median_mw": float(np.median(drop) * SITE_MW),
                       "p95_mw": float(np.quantile(drop, 0.95) * SITE_MW), "mean_mw": float(drop.mean() * SITE_MW)},
        "outside_training": 0.0, "ranked_on": "p_fail",
        "top_factors": [{"label": l, "share": s, "signed_mean": 0.0} for l, s in factors(d)],
    })
OUT.write_text(json.dumps({"design": "grid_friendly", "illustrative": True, "n_events": 5000, "site_mw": SITE_MW,
                           "surrogate": {"name": "illustrative"}, "depths": depths}, separators=(",", ":")))
for x in depths[::4]:
    print(f"{x['depth']:.2f} works {x['pass']:.0%} median drop {x['mw_dropped']['median_mw']:.0f} MW")
