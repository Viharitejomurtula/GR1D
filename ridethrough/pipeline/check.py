"""Check the surrogate against the actual simulator on events drawn from the joint sampler.

What this file is
    The surrogate was trained on independent draws from sim.scenario.sample(); the pipeline feeds it correlated
    draws at one design. This runs n of the pipeline's own scenarios through the surrogate and through the
    real simulator (surrogate.verify.simulate; needs OpenModelica via Docker or GR1D_NATIVE=1) and reports
    agreement overall and for rows the surrogate flags as outside its training range.

Inputs: n, seed, model_dir. Output: dict (also printed as JSON by `python -m ridethrough.pipeline.check`).
"""
from __future__ import annotations

import json
import sys

import numpy as np

from ridethrough.pipeline import joint
from surrogate import verify
from surrogate.predict import Surrogate

MODEL_DIR = "surrogate/models/v1"


def check(n: int = 300, seed: int = 12345, model_dir: str = MODEL_DIR) -> dict:
    sc, _ = joint.sample_joint(n, seed)
    sur = Surrogate.load(model_dir)
    pred = sur.predict(sc)
    truth = verify.simulate(joint.to_scenarios(sc)).set_index("index")
    keep = [i for i in truth.index if truth.loc[i, "numerics_ok"]]
    p, t = pred.loc[keep], truth.loc[keep]
    pass_pred, pass_true = (p["p_pass_mean"].to_numpy() > 0.5), t["passed"].to_numpy().astype(bool)
    ood = (p["outside_training"] != "").to_numpy()

    def block(mask):
        m = mask.sum()
        if m == 0:
            return {"n": 0}
        return {"n": int(m), "verdict_accuracy": float((pass_pred[mask] == pass_true[mask]).mean()),
                "sim_fail_rate": float((~pass_true[mask]).mean()),
                "surrogate_fail_rate": float(1 - p["p_pass_mean"].to_numpy()[mask].mean()),
                "min_power_mae": float(np.abs(p["min_power_mean"].to_numpy()[mask] - t["min_power"].to_numpy()[mask]).mean()),
                "peak_current_mae": float(np.abs(p["peak_current_pu_mean"].to_numpy()[mask] - t["peak_current_pu"].to_numpy()[mask]).mean()),
                "failure_mode_accuracy": float((p["failure_mode"].to_numpy()[mask] == t["failure_mode"].to_numpy()[mask]).mean())}

    age = sc.loc[keep, "battery_age_yr"].to_numpy()
    return {"requested": n, "simulated": len(truth), "usable": len(keep), "seed": seed, "all": block(np.ones(len(keep), bool)),
            "inside_training": block(~ood), "outside_training": block(ood),
            "age_le_10": block(age <= 10.0), "age_gt_10": block(age > 10.0)}


if __name__ == "__main__":
    print(json.dumps(check(int(sys.argv[1]) if len(sys.argv) > 1 else 300), indent=2))
