"""Facility A was entered with dip_depth_pu = 0.535, the retained voltage OBSERVED at the facility ('PSU sees 148 V at 277 V supply'), but the model treats
dip_depth_pu as the SOURCE voltage behind the transformer chain. With the exact network those differ. Sweep the source depth and report the voltage the PSUs
actually see, peak current and loss. Usage: .venv/bin/python -m validation.crosscheck.caseA_depth"""
from dataclasses import replace
import numpy as np
from sim import runner
from validation.cases import CASES

sc = CASES["facility_A"]["sc"]
print("target: PSU-side retained voltage 0.535, loss 0.46, peak 1.60")
for ds in (True, False):
    for d in (0.55, 0.60, 0.65, 0.70, 0.75):
        s = replace(sc, dip_depth_pu=d, psu_cap_datasheet=ds)
        g = runner.run(s, tag="caseA")
        r = runner._read_csv(runner.BUILD / "caseA_res.csv")
        t = r["time"]; m = (t >= 1.0) & (t <= 1.05)
        print(f"datasheet={ds!s:<5} source={d:.2f}  min v_sdp={r['v_sdp_pu'][m].min():.3f}  loss={1 - g.final_power_frac:.3f}  peak={g.peak_current_pu:.2f}  {g.failure_mode}  ok={g.numerics_ok}", flush=True)
