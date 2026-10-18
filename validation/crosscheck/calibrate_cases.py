"""Convert the cases' OBSERVED retained voltage into the model's source depth (bisection on the model's own min v_sdp during the dip), then
sweep the legacy-load share. Usage: .venv/bin/python -m validation.crosscheck.calibrate_cases"""
from dataclasses import replace
from sim import runner
from validation.cases import CASES

OBSERVED = {"facility_A": 0.535, "facility_B": 0.670, "shallow_0p844": 0.844}

def min_v(sc, tag="cal"):
    g = runner.run(sc, tag=tag); r = runner._read_csv(runner.BUILD / f"{tag}_res.csv")
    m = (r["time"] >= sc.dip_start_s) & (r["time"] <= sc.dip_start_s + sc.dip_duration_s)
    return float(r["v_sdp_pu"][m].min()), g

def source_depth(sc, observed, lo=0.5, hi=0.99):
    for _ in range(9):
        mid = 0.5 * (lo + hi)
        v, _ = min_v(replace(sc, dip_depth_pu=mid))
        lo, hi = (mid, hi) if v < observed else (lo, mid)
    return round(0.5 * (lo + hi), 3)

if __name__ == "__main__":
    depth = {}
    for k, obs in OBSERVED.items():
        depth[k] = source_depth(CASES[k]["sc"], obs); print(k, "observed", obs, "-> source depth", depth[k], flush=True)
    for k, lo, hi, step in (("facility_A", 0.38, 0.58, 0.04), ("facility_B", 0.20, 0.40, 0.04)):
        n = int(round((hi - lo) / step)) + 1
        for i in range(n):
            lf = round(lo + i * step, 2)
            g = runner.run(replace(CASES[k]["sc"], dip_depth_pu=depth[k], legacy_load_frac=lf), tag="cal")
            print(f"{k} legacy={lf:.2f} loss={1 - g.final_power_frac:.3f} peak={g.peak_current_pu:.2f} {g.failure_mode}  (target loss {CASES[k]['target']['loss_frac']})", flush=True)
