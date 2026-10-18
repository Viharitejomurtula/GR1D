"""For each dip depth, the outcome distribution across realistic conditions, for the Results tab.

Usage
    python scripts/export_depth_outcomes.py [--n 5000] [--step 0.05] [--model <name>] [--out frontend/public/data/depth_outcomes.json]

At each depth (0.00-1.00 pu) the Bayesian network and the scenario distributions draw n events (sample_joint, everything but
the dip depth varies), the active surrogate (surrogate/models/ACTIVE) predicts each one, and the page gets:
  pass / fail     expected share of events that pass the ride-through rule, and the share failing by each mode
  mw_dropped      histogram of the load that leaves the grid (1 - lowest grid power, as a share of pre-fault draw), and the same
                  in MW for a site of --site-mw (the 800 MW site drawn on the map)
  top_factors     the three blocks of inputs with the highest Shapley importance on P(fail) (on MW dropped when nearly every
                  event passes or fails, since a saturated probability cannot be ranked); the dip depth itself is held fixed.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from ridethrough.pipeline import drivers, joint, performance  # noqa: E402
from sim.scenario import GRID_FRIENDLY  # noqa: E402
from surrogate import registry  # noqa: E402

SATURATED = (0.02, 0.98)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--events", type=int, default=300, help="events in the Shapley estimate")
    ap.add_argument("--perms", type=int, default=4)
    ap.add_argument("--site-mw", type=float, default=800.0)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "depth_outcomes.json"))
    a = ap.parse_args()

    sur = registry.load_active(a.model)
    ev = performance.Evaluator(sur)
    names = ev.names
    sc0, _ = joint.sample_joint(a.n, a.seed, GRID_FRIENDLY)
    blocks = [b for b in joint.BLOCKS if b.name != "dip_depth"]
    players = [drivers._cols(b) for b in blocks]
    edges = np.linspace(0.0, 1.0, 21)

    out_depths = []
    for depth in np.round(np.arange(0.0, 1.0 + a.step / 2, a.step), 4):
        sc = sc0.copy()
        sc["dip_depth_pu"] = depth
        y = ev(sc)
        col = {n: y[:, i] for i, n in enumerate(names)}
        p_fail = float(col["p_fail"].mean())
        dropped = np.clip(1.0 - col["min_power"], 0.0, 1.0)
        counts, _ = np.histogram(dropped, bins=edges)

        target = "p_fail" if SATURATED[0] <= p_fail <= SATURATED[1] else "min_power"
        rng = np.random.default_rng(a.seed + int(depth * 1000))
        X = sc.to_numpy(dtype=float)
        fg = X[rng.choice(len(X), a.events, replace=False)]
        bg = X[rng.choice(len(X), a.events, replace=True)]
        phi = drivers.shapley(ev, fg, bg, players, a.perms, rng)
        rows = drivers._rank_table(phi, blocks, names.index(target), rng)[:3]

        out_depths.append({
            "depth": float(depth), "pass": 1.0 - p_fail, "fail": p_fail,
            "fail_by_mode": {m: float(col[f"mode:{m}"].mean()) for m in ev.modes},
            "mw_dropped": {"share_edges": edges.tolist(), "counts": counts.tolist(),
                           "median_mw": float(np.median(dropped) * a.site_mw), "p95_mw": float(np.quantile(dropped, 0.95) * a.site_mw),
                           "mean_mw": float(dropped.mean() * a.site_mw)},
            "outside_training": float(ev.outside_training(sc).mean()),
            "ranked_on": target,
            "top_factors": [{"label": r["label"], "share": r["share"], "signed_mean": r["signed_mean"]} for r in rows],
        })
        print(f"{depth:.2f} pu: pass {1 - p_fail:.1%}  median drop {np.median(dropped) * a.site_mw:.0f} MW  top: "
              + ", ".join(r["label"] for r in rows))

    out = {"design": "grid_friendly", "n_events": a.n, "site_mw": a.site_mw, "surrogate": sur.provenance, "depths": out_depths}
    p = pathlib.Path(a.out)
    p.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {p} ({p.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
