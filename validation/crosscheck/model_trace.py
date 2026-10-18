"""Run the real OpenModelica model on a controlled single-group dip and return the full trace."""
from __future__ import annotations

import dataclasses
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from sim import runner, scenario  # noqa: E402


def trace(depth_pu: float, dur_s: float, *, supply_v: float = 230.0, workload: float = 0.85, uv_delay_s: float = 1 / 60,
          stop_s: float = 3.0, tag: str = "xc", **over) -> dict[str, np.ndarray]:
    sc = scenario.sample(np.random.default_rng(1))
    sc = dataclasses.replace(
        sc, dip_depth_pu=depth_pu, dip_duration_s=dur_s, dip_start_s=1.0, recovery_tau_s=1e-3, overshoot_pu=1e-6, second_dip=False,
        supply_voltage_v=supply_v, psu_trip_spread_frac=1e-3, faulted_phase_frac=1.0, n_groups=1, legacy_load_frac=0.0,
        workload=workload, swing_size_frac=0.0, psu_uv_delay_s=uv_delay_s, **over)
    runner.build()
    cmd = ["./RideThroughCore", "-override", runner._overrides(sc), "-stopTime", str(stop_s), "-stepSize", "0.001", "-r", f"{tag}_res.csv"]
    r = runner._docker(cmd)
    p = runner.BUILD / f"{tag}_res.csv"
    if not p.exists():
        raise RuntimeError(r.stdout[-1500:] + r.stderr[-1500:])
    return runner._read_csv(p)


if __name__ == "__main__":
    d = trace(0.5, 0.2)
    print([k for k in d if any(s in k for s in ("holdup", "e_frac", "p_psu", "p_server", "v_sdp", "tripped", "bbu_active", "p_bbu", "v_sense", "online", "n_psu"))])
