"""After replacing the scalar voltage drop with the exact complex solve, re-run facilities A/B and the 0.844 case across the two unsourced PSU
choices that the earlier fit leaned on: lockout debounce (psu_uv_delay_s) and PSU capability mode (psu_cap_datasheet True = full power until
lockout; False = power scaled with voltage, which the ngspice cross-check shows tracks a 17.3 A input-limited PFC).
Targets (validation/cases.py): A loss 0.46 / peak 1.60; B loss 0.24 / peak 1.50; 0.844 loss 0.19.
Usage: .venv/bin/python -m validation.crosscheck.network_refit [out.json]"""
import json, sys
from dataclasses import replace
from sim import runner
from validation.cases import CASES

def main():
    rows = []
    for name, c in CASES.items():
        for ds in (True, False):
            for delay in (0.0, 1 / 120, 1 / 60, 1 / 30):
                g = runner.run(replace(c["sc"], psu_cap_datasheet=ds, psu_uv_delay_s=delay), tag="refit")
                rows.append(dict(case=name, datasheet=ds, delay_ms=round(delay * 1e3, 1), loss=round(1 - g.final_power_frac, 3),
                                 peak=round(g.peak_current_pu, 3), mode=g.failure_mode, numerics_ok=bool(g.numerics_ok),
                                 target_loss=c["target"].get("loss_frac"), target_peak=c["target"].get("peak_current_pu")))
                print(rows[-1], flush=True)
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(rows, indent=1))

if __name__ == "__main__":
    main()
