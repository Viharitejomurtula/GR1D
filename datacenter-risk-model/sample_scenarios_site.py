"""Reference-campus scenario summary (Abilene, public-information proxy): site weather samples plus the low/mid/high matrix.
Unobservable inputs (rho, systemic event rate, dip multiplier) are never fixed to a default: results are listed at low, mid and high.
Usage: python sample_scenarios_site.py [n] [seed]  (run scripts/build_scenario_matrix.py first)"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "models"))
from samplers import CapacitorLoss, Temperature  # noqa: E402


def main(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    T = Temperature(station="USW00013962", tag="_abilene")
    out = dict(site="Reference campus (Abilene weather station KABI; ERCOT West; 138/345 kV transmission class) - public-information proxy",
               dry_bulb_aug_15h_c_p5_p50_p95=np.percentile(T.sample(n, rng, 8, 15), [5, 50, 95]).round(1).tolist(),
               capacitor_loss_12V_5000h_p5_p50_p95_mid_default=np.percentile(CapacitorLoss().sample(n, rng, 12, 5000), [5, 50, 95]).round(3).tolist())
    m = json.load(open(HERE / "site/abilene/scenario_matrix.json"))
    out["low_mid_high"] = dict(ai_swing_200MW_mw_p99_p1={k.split("_")[1]: v["swing_p99_p1_mw"] for k, v in m["ai_swing"].items() if k.startswith("200MW")},
                               systemic_P_year_below_59_5Hz={k: round(v["p59_5"], 3) for k, v in m["systemic"].items()},
                               voltage_dips_per_year_p5_p50_p95=m["dips"])
    (HERE / "reports/sample_scenarios_site_summary.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000, int(sys.argv[2]) if len(sys.argv) > 2 else 0)
