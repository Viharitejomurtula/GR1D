"""Precompute a dense grid of simulator results for the interactive UI.

With four knobs a grid covers every combination the user can select, so the frontend
returns exact simulator output rather than a prediction. No surrogate, no server, and
nothing that can be wrong at the pass/fail boundary.

Everything not on an axis is held at the reference design, so the user is exploring one
facility under varying conditions rather than a different facility per slider position.

    python3 scripts/make_grid.py --steps 21,10,10,11      # 23,100 runs, ~40 min
    python3 scripts/make_grid.py --steps 16,8,8,8         #  8,192 runs, ~14 min

Writes frontend/public/data/grid.json:

    { axes: {name: [values...]}, shape: [...], order: [names],
      cells: [{p, m, r, c}, ...] }   flat, row-major over `order`

      p  passed (0/1)        m  failure mode index
      r  recovery margin s   c  peak current pu
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sim import batch, constants as C, runner  # noqa: E402
from sim.grader import grade  # noqa: E402
from sim.scenario import GRID_FRIENDLY  # noqa: E402

AXES = ("dip_depth_pu", "dip_duration_s", "outdoor_temp_c", "battery_age_yr")
MODES = (
    "passed", "exceeded 125% current cap", "cooling tripped",
    "PSU shutdown and restart delay", "below power floor",
    "storage hand-back too slow", "disconnected inside envelope", "no disturbance",
)


def build_axes(steps: list[int]) -> dict[str, list[float]]:
    d, t, c, a = steps
    return {
        "dip_depth_pu": np.linspace(0.05, 1.0, d).round(4).tolist(),
        # Log-spaced: most sags are short, and the interesting behaviour (PSU hold-up is
        # 20 ms) lives at the bottom of the range.
        "dip_duration_s": np.geomspace(0.02, 1.0, t).round(4).tolist(),
        "outdoor_temp_c": np.linspace(0.0, 42.0, c).round(2).tolist(),
        # Past the 8-15 yr service life, so this reaches deferred-replacement packs --
        # degraded storage is where failures hide, which is the point of the sweep.
        "battery_age_yr": np.linspace(0.0, 14.0, a).round(2).tolist(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="16,8,8,8", help="steps per axis, in AXES order")
    ap.add_argument("--out", default="frontend/public/data/grid.json")
    ap.add_argument("--chunk", type=int, default=2000, help="runs per container invocation")
    args = ap.parse_args()

    steps = [int(s) for s in args.steps.split(",")]
    if len(steps) != len(AXES):
        raise SystemExit(f"--steps needs {len(AXES)} numbers, one per axis: {AXES}")

    axes = build_axes(steps)
    combos = list(itertools.product(*(axes[a] for a in AXES)))
    total = len(combos)
    print(f"{total:,} combinations over {AXES}")
    print(f"estimated {total / 9.6 / 60:.0f} min at ~9.6 runs/sec\n")

    runner.build()
    mode_ix = {m: i for i, m in enumerate(MODES)}
    cells: list[dict | None] = [None] * total
    t0 = time.time()
    failed = 0

    for start in range(0, total, args.chunk):
        block = combos[start : start + args.chunk]
        scen = [
            dataclasses.replace(GRID_FRIENDLY, **dict(zip(AXES, values)))
            for values in block
        ]
        paths = batch._run_all(scen)

        for offset, path in enumerate(paths):
            if not path.exists():
                failed += 1
                continue
            try:
                d = runner._read_csv(path)
                # A run that does not reach the end of the window did not converge; grading
                # a partial trace is how deep dips previously scored as clean passes.
                if d["time"][-1] < 0.99 * C.WINDOW_S or len(d["time"]) < 100:
                    failed += 1
                    continue
                g = grade(
                    d["time"], d["v_sdp_pu"], d["p_grid_w"], d["i_grid_pu"],
                    connected=(d["facility_connected"] > 0.5) if "facility_connected" in d else None,
                    trips=runner._extract_trips(d),
                )
                cells[start + offset] = {
                    "p": int(g.passed),
                    "m": mode_ix.get(g.failure_mode, 0),
                    "r": round(g.recovery_margin_s, 3),
                    "c": round(g.peak_current_pu, 3),
                }
            except Exception:
                failed += 1
            finally:
                path.unlink(missing_ok=True)

        done = min(start + args.chunk, total)
        rate = done / (time.time() - t0)
        eta = (total - done) / rate / 60 if rate else 0
        print(f"  {done:,}/{total:,}  {rate:.1f}/s  eta {eta:.0f} min  ({failed} failed)")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "axes": axes,
        "order": list(AXES),
        "shape": steps,
        "modes": list(MODES),
        "design": "GRID_FRIENDLY reference facility; all other inputs held at its values",
        "cells": cells,
    }))
    ok = sum(c is not None for c in cells)
    print(f"\n{ok:,}/{total:,} cells -> {out}  ({out.stat().st_size / 1024:.0f} KB)")
    if failed:
        print(f"{failed:,} runs did not converge and are null in the grid")


if __name__ == "__main__":
    main()
