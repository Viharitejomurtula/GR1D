"""Generate simulation inputs by sampling each fitted factor model.
Usage: python sample_scenarios.py [n] [seed]  -> prints a summary and writes reports/sample_scenarios_summary.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "models"))
from samplers import (AIWorkloadSwing, BatteryCapacityFade, BatteryResistanceGrowth, FrequencyDeviation,  # noqa: E402
                      FrequencyEventTail, Temperature, VoltageDips, CapacitorLoss, DataCenterUtilization, GPUSyncGroupSize, GPUSyncFacility, BatteryDCResistance)


def main(n: int = 1000, seed: int = 0):
    rng = np.random.default_rng(seed)
    out = {}
    T = Temperature()
    out["temp_aug_15h_c"] = np.percentile(T.sample(n, rng, month=8, hour=15), [5, 50, 95]).round(1).tolist()
    out["temp_annual_max_c"] = np.percentile(T.sample_annual_max(n, rng), [5, 50, 95]).round(1).tolist()
    F = FrequencyDeviation(); tr = F.sample(min(n, 200), rng, seconds=60)
    out["freq_dev_mhz_1s_p1_p99"] = np.percentile(tr, [1, 99]).round(1).tolist()
    out["freq_rocof_mhz_s_p1_p99"] = np.percentile(F.rocof(tr), [1, 99]).round(2).tolist()
    ev = FrequencyEventTail()
    out["freq_event_nadir_hz_p50_p1"] = np.percentile(ev.sample(n, rng), [50, 1]).round(3).tolist()
    yrs_ev = ev.sample_years(2000, rng)
    out["freq_annual_min_nadir_hz_p50_p5_p1_with_systemic"] = np.percentile([y.min() if len(y) else 60 for y in yrs_ev], [50, 5, 1]).round(3).tolist()
    out["freq_p_year_nadir_below_59.7_with_systemic"] = round(float(np.mean([(y < 59.7).any() for y in yrs_ev])), 3)
    out["battery_soh_100cycles_p5_p50_p95"] = np.percentile(BatteryCapacityFade().sample(n, rng, 100), [5, 50, 95]).round(3).tolist()
    out["battery_R_growth_100cycles_p5_p50_p95"] = np.percentile(BatteryResistanceGrowth().sample(n, rng, 100), [5, 50, 95]).round(3).tolist()
    yrs = VoltageDips().sample(200, rng)
    out["voltage_dips_per_year_p5_p50_p95"] = np.percentile([len(y) for y in yrs], [5, 50, 95]).tolist()
    out["ai_swing_w_per_node_5s_p50_p99"] = np.percentile(AIWorkloadSwing().sample(n, rng), [50, 99]).round(0).tolist()
    out["capacitor_loss_14V_5000h_p5_p50_p95"] = np.percentile(CapacitorLoss().sample(n, rng, 14, 5000), [5, 50, 95]).round(3).tolist()
    U = DataCenterUtilization(); u = U.sample(n, rng)
    out["dc_sm_util_p5_p50_p95"] = np.percentile(u, [5, 50, 95]).round(3).tolist()
    out["dc_node_power_kw_p50"] = round(float(np.median(U.node_power_kw(u))), 2)
    out["gpu_group_training_p50_p99"] = np.percentile(GPUSyncGroupSize().sample(n, rng), [50, 99]).round(0).tolist()
    out["battery_dc_R_mohm_25C_50soc_100cycles_p5_p50_p95"] = (1000 * np.percentile(BatteryDCResistance().sample(n, rng, 25, 50, 100), [5, 50, 95])).round(1).tolist()
    out["battery_dc_R_mohm_0C_vs_25C_fresh"] = [round(1000 * BatteryDCResistance().fresh(0, 50), 1), round(1000 * BatteryDCResistance().fresh(25, 50), 1)]
    out["wetbulb_aug_15h_c_p5_p50_p95"] = np.percentile(T.sample_wetbulb(n, rng, 8, 15), [5, 50, 95]).round(1).tolist()
    out["gpu_sync_facility_swing_mw_rho0_rho1"] = [round(GPUSyncFacility().swing_mw(r), 2) for r in (0.0, 1.0)]
    Path(__file__).parent.joinpath("reports/sample_scenarios_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000, int(sys.argv[2]) if len(sys.argv) > 2 else 0)
