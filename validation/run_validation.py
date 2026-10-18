"""Run the documented validation cases and the 70-sag product benchmark; print/record outcomes. Usage: OM_IMAGE=... python3 -m validation.run_validation [out.json]"""
import json, sys, numpy as np
from dataclasses import replace
from sim import runner, scenario as S
from validation.cases import CASES

def sustained_loss(g): return 1.0 - g.final_power_frac

def run_cases():
    out = {}
    for name, c in CASES.items():
        g = runner.run(c["sc"], tag=f"val_{name}")
        out[name] = dict(loss_frac=round(sustained_loss(g), 3), peak_current_pu=round(g.peak_current_pu, 3), passed=bool(g.passed),
                         mode=g.failure_mode, recovery_margin_s=round(g.recovery_margin_s, 3), target=c["target"])
    return out

def run_product(n=70, seed=0):
    rng = np.random.default_rng(seed); rec, disc, dl = [], 0, []
    for i in range(n):
        d = S.sample_dip_depth(rng); tau, os_ = S.sample_shape(rng, d)
        sc = replace(S.GRID_FRIENDLY, dip_depth_pu=d, dip_duration_s=S.sample_dip_duration(rng), recovery_tau_s=tau, overshoot_pu=os_)
        g = runner.run(sc, tag="val_product")
        disc += any(t.startswith("facility_disconnect") for t in g.trips); rec.append(g.recovery_deadline_s - g.recovery_margin_s); dl.append(g.recovery_deadline_s)
    rec = np.array(rec)
    return dict(n=n, never_disconnected=(disc == 0), median_recovery_s=round(float(np.median(rec)), 3), worst_recovery_s=round(float(rec.max()), 3),
                inside_rule_frac=round(float((rec <= np.array(dl) + 1e-9).mean()), 3), within_half_second_frac=round(float((rec <= 0.5).mean()), 3), target=dict(median_recovery_s=0.41, worst_recovery_s=0.49, never_disconnected=True))

from sim import constants as _C
C_REC = _C.RECOVERY_DEADLINE_S

if __name__ == "__main__":
    res = dict(cases=run_cases(), product=run_product())
    print(json.dumps(res, indent=1))
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(res, indent=1))
