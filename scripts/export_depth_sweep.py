"""Simulate one design across dip depth 0.00-1.00 pu and export the graded runs with traces for the Results tab.

Usage
    python scripts/export_depth_sweep.py [--design grid_friendly] [--step 0.01] [--out frontend/public/data/depth_sweep.json]

Every depth the page's slider can reach is a real simulator run (sim.batch, one container), graded by sim.runner.grade_trace,
so the page replays simulator output rather than a prediction. Everything except the dip depth is held at the design preset
(sim.scenario.GRID_FRIENDLY / LEGACY_UPS). Runs outside C.VALID_DIP_DEPTH_PU are kept but marked out of scope, and runs where
the solver found no valid operating point are kept with numerics_ok = false so the page can say so instead of guessing.

Traces are resampled: fine around the dip, coarse elsewhere, to keep the file small.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sim import batch, runner, scenario as S  # noqa: E402
from sim import constants as C  # noqa: E402

DESIGNS = {"grid_friendly": S.GRID_FRIENDLY, "legacy_ups": S.LEGACY_UPS}
# signal in the trace -> exported name; scaled below to fractions of pre-fault values where noted
SIGNALS = {
    "v_sdp_pu": "v",            # voltage at the service delivery point, pu
    "i_grid_pu": "i",           # grid current, pu of maximum normal
    "p_grid_w": "p",            # grid power, fraction of pre-fault
    "p_bbu_w": "bbu",           # battery power, fraction of pre-fault server power
    "p_server_w": "srv",        # server power, fraction of pre-fault
    "psu_online_frac": "psu",   # share of PSUs supplying
    "soc": "soc",
}


def _times(window: float, start: float, end: float) -> np.ndarray:
    return np.unique(np.round(np.concatenate([
        np.arange(0.0, start - 0.1, 0.02),
        np.arange(start - 0.1, end + 1.0, 0.004),
        np.arange(end + 1.0, window, 0.05),
        [window],
    ]), 4))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", choices=list(DESIGNS), default="grid_friendly")
    ap.add_argument("--step", type=float, default=0.01)
    ap.add_argument("--out", default=str(runner.REPO / "frontend" / "public" / "data" / "depth_sweep.json"))
    a = ap.parse_args()

    base = DESIGNS[a.design]
    depths = [round(x, 4) for x in np.arange(0.0, 1.0 + a.step / 2, a.step)]
    scenarios = [dataclasses.replace(base, dip_depth_pu=d) for d in depths]
    t0 = time.time()
    paths = batch._run_all(scenarios)
    print(f"simulated {len(depths)} depths in {time.time() - t0:.0f} s")

    runs = []
    for d, sc, path in zip(depths, scenarios, paths):
        run = {"depth": d, "in_scope": sc.in_scope()}
        if not path.exists():
            runs.append(run | {"ok": False, "error": "no result"}); continue
        try:
            tr = runner._read_csv(path)
            g = runner.grade_trace(tr)
        except Exception as exc:  # noqa: BLE001
            runs.append(run | {"ok": False, "error": str(exc)[:200]}); continue
        start, dur, _ = sc.dip_sequence()[0]
        tt = _times(float(tr["time"][-1]), start, start + dur)
        pre = int(np.searchsorted(tr["time"], start - 0.05))
        scale = {"p_grid_w": tr["p_grid_w"][pre], "p_bbu_w": tr["p_server_w"][pre], "p_server_w": tr["p_server_w"][pre]}
        series = {}
        for sig, name in SIGNALS.items():
            if sig not in tr:
                continue
            y = np.interp(tt, tr["time"], tr[sig]) / (scale.get(sig) or 1.0)
            series[name] = [round(float(v), 4) for v in y]
        runs.append(run | {
            "ok": True, "numerics_ok": g.numerics_ok, "numerics_note": g.numerics_note, "passed": g.passed,
            "failure_mode": g.failure_mode, "peak_current_pu": round(g.peak_current_pu, 4), "min_power": round(g.min_power, 4),
            "recovery_margin_s": round(g.recovery_margin_s, 4), "floor_violation_s": round(g.floor_violation_s, 4),
            "trips": g.trips[:12], "t": [float(x) for x in tt], **series,
        })
        path.unlink(missing_ok=True)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=runner.REPO).stdout.strip()
    out = {
        "design": a.design, "simulator_commit": commit,
        "dip": {"start_s": base.dip_start_s, "duration_s": base.dip_duration_s, "second_dip": base.second_dip},
        "valid_dip_depth_pu": list(C.VALID_DIP_DEPTH_PU), "current_cap_pu": C.CURRENT_CAP_PU,
        "p_pre_mw": None, "runs": runs,
    }
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, separators=(",", ":")))
    ok = [r for r in runs if r.get("ok")]
    print(f"wrote {p} ({p.stat().st_size / 1e6:.1f} MB): {len(ok)}/{len(runs)} runs, "
          f"{sum(r['passed'] for r in ok)} pass, {sum(not r['numerics_ok'] for r in ok)} no valid operating point")


if __name__ == "__main__":
    main()
