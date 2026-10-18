"""Sensitivity of the validation results to the (unsourced) PSU input-current limit psu_ilim_x. Usage: .venv/bin/python -m validation.crosscheck.ilim_sensitivity"""
import json
from dataclasses import replace
import numpy as np
from sim import runner, scenario as S
from validation.cases import CASES
from validation.run_validation import C_REC

def bench(ilim, n=70, seed=0):
    rng = np.random.default_rng(seed); v, bad = [], 0
    for _ in range(n):
        d = S.sample_dip_depth(rng); tau, os_ = S.sample_shape(rng, d); dur = S.sample_dip_duration(rng)
        g = runner.run(replace(S.GRID_FRIENDLY, dip_depth_pu=d, dip_duration_s=dur, recovery_tau_s=tau, overshoot_pu=os_, psu_ilim_x=ilim), tag="sens")
        if g.numerics_ok: v.append(C_REC - g.recovery_margin_s)
        else: bad += 1
    return bad, float(np.median(v)), float(max(v))

out = []
for ilim in (0.0, 1.0, 1.5, 2.0):
    row = {"ilim_x": ilim}
    for k in ("facility_A", "facility_B"):
        g = runner.run(replace(CASES[k]["sc"], psu_ilim_x=ilim), tag="sens")
        row[k] = dict(peak=round(g.peak_current_pu, 2), loss=round(1 - g.final_power_frac, 3), mode=g.failure_mode, ok=bool(g.numerics_ok))
    row["bench_invalid"], row["bench_median_s"], row["bench_worst_s"] = bench(ilim)
    print(row, flush=True); out.append(row)
json.dump(out, open("validation/crosscheck/ilim_sensitivity.json", "w"), indent=1)
