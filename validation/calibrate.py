"""Separate FITTING from VALIDATION for the legacy-load share (item 7).

legacy_load_frac is a free knob: it is inferred from a facility's sustained load loss, so a match on that loss is a fit, not a test.
This script (1) shows how identifiable the knob is (loss vs legacy_load_frac), (2) infers it per facility, and (3) reports only
quantities that were NOT fitted: peak current, recovery behaviour, and leave-one-out loss predictions (fit on one facility,
predict the other / the shallow case).

Usage: OM_IMAGE=... python3 -m validation.calibrate [out.json]"""
import json, sys
import numpy as np
from dataclasses import replace
from sim import runner
from validation.cases import CASES

def loss_at(sc, frac, tag="cal"):
    g = runner.run(replace(sc, legacy_load_frac=float(frac)), tag=tag); return 1.0 - g.final_power_frac, g

def infer_frac(sc, target_loss, tol=0.005):
    """Bisection; loss is monotone in the legacy share. Returns (frac, achievable) — achievable False if the target is outside [loss(0), loss(1)]."""
    lo_l, _ = loss_at(sc, 0.0); hi_l, _ = loss_at(sc, 1.0)
    if not (min(lo_l, hi_l) - tol <= target_loss <= max(lo_l, hi_l) + tol): return (0.0 if target_loss < lo_l else 1.0), False
    lo, hi = 0.0, 1.0
    for _ in range(10):
        mid = 0.5 * (lo + hi); l, _ = loss_at(sc, mid)
        if abs(l - target_loss) < tol: return mid, True
        if l < target_loss: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi), True

def identifiability(sc):
    xs = np.linspace(0, 1, 6); return [(float(x), round(loss_at(sc, x)[0], 3)) for x in xs]

def main():
    out = {"identifiability": {}, "fit": {}, "unfitted": {}, "leave_one_out": {}}
    for name in ("facility_A", "facility_B"):
        sc, tgt = CASES[name]["sc"], CASES[name]["target"]
        out["identifiability"][name] = identifiability(sc)
        frac, ok = infer_frac(sc, tgt["loss_frac"]); loss, g = loss_at(sc, frac, tag=f"cal_{name}")
        out["fit"][name] = dict(inferred_frac=round(frac, 3), achievable=ok, fitted_loss=round(loss, 3), target_loss=tgt["loss_frac"])
        out["unfitted"][name] = dict(peak_current_pu=round(g.peak_current_pu, 3), target_peak=tgt["peak_current_pu"],
                                     error_pct=round(100 * (g.peak_current_pu - tgt["peak_current_pu"]) / tgt["peak_current_pu"], 1))
    # leave-one-out: use the fraction inferred on one facility to predict the other facility's loss and the shallow case
    for src, dst in (("facility_A", "facility_B"), ("facility_B", "facility_A")):
        f = out["fit"][src]["inferred_frac"]; loss, g = loss_at(CASES[dst]["sc"], f, tag="cal_loo")
        out["leave_one_out"][f"fit_on_{src}_predict_{dst}"] = dict(frac=f, predicted_loss=round(loss, 3), real_loss=CASES[dst]["target"]["loss_frac"],
                                                                   error_pts=round(100 * (loss - CASES[dst]["target"]["loss_frac"]), 1))
    f = out["fit"]["facility_B"]["inferred_frac"]; loss, _ = loss_at(CASES["shallow_0p844"]["sc"], f, tag="cal_shallow")
    out["leave_one_out"]["fit_on_B_predict_0p844"] = dict(frac=f, predicted_loss=round(loss, 3), real_loss=0.19, error_pts=round(100 * (loss - 0.19), 1))
    print(json.dumps(out, indent=1))
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
