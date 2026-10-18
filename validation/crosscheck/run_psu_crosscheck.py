"""Run the ngspice PSU cross-check sweeps and write ngspice_psu.json.  Usage: .venv/bin/python validation/crosscheck/run_psu_crosscheck.py

A: sag shorter than the lockout debounce (12 ms < 16.7 ms), so no PSU trips and the only thing draining the hold-up store is the
   shortfall between the load and what the PFC can pull through its input-current limit. Model run in both PSU-capability modes
   (psu_cap_datasheet True = full power until lockout; False = power scaled with per-unit voltage) vs the circuit at four input
   current limits (1.0x = 3 kW / (eta * 180 V) = 17.3 A, the datasheet's full-power-at-180-Vac point).
B: hold-up recharge after the same sag, where the model uses a fixed 50 ms time constant and the circuit is limited by PFC headroom.
   Only rows where the BBU did not take over are kept (when it does, the circuit's load is removed and the comparison is meaningless).
"""
from __future__ import annotations

import json
import pathlib

import ngspice_psu as n

OUT = pathlib.Path(__file__).with_name("ngspice_psu.json")


def main() -> None:
    res = {"A": [], "B": []}
    for depth in (0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75):
        row = {"depth_pu": depth}
        try:
            row["e_min_model_datasheet"] = n.compare(depth, 0.012, datasheet=True, stop_s=1.6)[0]["e_min_model"]
            row["e_min_model_per_unit"] = n.compare(depth, 0.012, datasheet=False, stop_s=1.6)[0]["e_min_model"]
        except RuntimeError as e:
            row["skipped"] = str(e)
            res["A"].append(row)
            continue
        for s in (1.0, 1.25, 1.5, 2.0):
            row[f"e_min_ngspice_ilim_x{s}"] = n.compare(depth, 0.012, datasheet=True, stop_s=1.6, i_lim_scale=s)[0]["e_min_ngspice"]
        res["A"].append(row)
    for w in (0.5, 0.7, 0.85, 0.95):
        for depth, dur in ((0.5, 0.012), (0.45, 0.015)):
            try:
                r = n.compare(depth, dur, datasheet=False, workload=w, stop_s=2.2)[0]
            except RuntimeError:
                continue
            if r["model_bbu_active"] or r["e_min_model"] > 0.97:
                continue
            res["B"].append({k: r[k] for k in ("workload", "depth_pu", "dur_ms", "e_min_model", "e_min_ngspice",
                                               "t_recharge95_model_ms", "t_recharge95_ngspice_ms")})
    OUT.write_text(json.dumps(res, indent=1))
    print("A: min hold-up fraction during a 12 ms sag (1.0 = untouched)")
    print(f"{'depth':>6} {'model ds':>9} {'model pu':>9} | " + " ".join(f"{'ng x'+str(s):>8}" for s in (1.0, 1.25, 1.5, 2.0)))
    for r in res["A"]:
        if "skipped" in r:
            print(f"{r['depth_pu']:6.2f} skipped")
            continue
        print(f"{r['depth_pu']:6.2f} {r['e_min_model_datasheet']:9.3f} {r['e_min_model_per_unit']:9.3f} | "
              + " ".join(f"{r[f'e_min_ngspice_ilim_x{s}']:8.3f}" for s in (1.0, 1.25, 1.5, 2.0)))
    print("\nB: recharge to 95% after the sag (ms), BBU not engaged")
    for r in res["B"]:
        print(f"  load {r['workload']:.2f} dip {r['depth_pu']:.2f}x{r['dur_ms']:.0f}ms  e_min model/ng {r['e_min_model']:.2f}/{r['e_min_ngspice']:.2f}  "
              f"t95 model {r['t_recharge95_model_ms']:.0f}  ngspice {r['t_recharge95_ngspice_ms']:.0f}")


if __name__ == "__main__":
    main()
