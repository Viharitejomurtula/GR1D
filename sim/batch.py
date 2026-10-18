"""Run many scenarios and collect summaries.

All simulations for a batch execute inside a single container invocation. Container
startup is a large share of per-run cost, so looping inside one container rather than
spawning one per scenario is several times faster.

Traces are large (thousands of rows x ~40 columns), so only the graded summary is kept
by default; pass keep_traces to retain the CSVs for inspection.
"""

from __future__ import annotations

import csv
import pathlib
import time
from dataclasses import fields

import numpy as np

from . import constants as C
from . import runner
from .scenario import FIELD_ORDER, Scenario, sample_many

DATA = runner.REPO / "data"


def _run_all(scenarios: list[Scenario]) -> list[pathlib.Path]:
    """Execute every scenario inside one container invocation."""
    runner.build()
    ov_file = runner.BUILD / "batch_overrides.txt"
    ov_file.write_text(
        "".join(
            f"{i}|{sc.window_s()}|{C.OUTPUT_STEP_S}|{runner._overrides(sc)}\n"
            for i, sc in enumerate(scenarios)
        )
    )

    script = runner.BUILD / "batch_run.sh"
    script.write_text(
        "#!/bin/sh\n"
        "while IFS= read -r line; do\n"
        '  idx="${line%%|*}"; rest="${line#*|}"\n'
        '  win="${rest%%|*}"; rest="${rest#*|}"\n'
        '  step="${rest%%|*}"; ov="${rest#*|}"\n'
        '  ./RideThroughCore -override "$ov" -stopTime "$win" -stepSize "$step" '
        '-r "b_${idx}_res.csv" >/dev/null 2>&1\n'
        "done < batch_overrides.txt\n"
    )
    script.chmod(0o755)
    runner._docker(["sh", "batch_run.sh"])
    return [runner.BUILD / f"b_{i}_res.csv" for i in range(len(scenarios))]


def run_batch(
    n: int = 500,
    seed: int = 0,
    out: str | pathlib.Path = None,
    keep_traces: bool = False,
) -> list[dict]:
    """Sample n scenarios, simulate, grade, and write a summary CSV."""
    scenarios = sample_many(n, seed=seed)
    t0 = time.time()
    paths = _run_all(scenarios)
    sim_s = time.time() - t0

    rows: list[dict] = []
    failed = 0
    for sc, path in zip(scenarios, paths):
        if not path.exists():
            failed += 1
            continue
        try:
            d = runner._read_csv(path)
            g = runner.grade_trace(d)
        except Exception:
            failed += 1
            continue

        row = {f: getattr(sc, f) for f in FIELD_ORDER}
        row |= {
            "passed": int(g.passed),
            "passed_pre2028": int(g.passed_pre2028),
            "failure_mode": g.failure_mode,
            "recovery_margin_s": g.recovery_margin_s,
            "min_power": g.min_power,
            "final_power_frac": g.final_power_frac,
            "floor_violation_s": g.floor_violation_s,
            "peak_current_pu": g.peak_current_pu,
            "envelope_violation_s": g.envelope_violation_s,
            "storage_left": g.storage_left,
            # grade_trace's voltage-solution check: 0 marks a run whose solution is invalid, so
            # downstream users (surrogate.data.load) can drop it instead of learning it as a failure.
            "numerics_ok": int(g.numerics_ok),
            "numerics_note": g.numerics_note,
            "n_trips": len(g.trips),
        }
        rows.append(row)
        if not keep_traces:
            path.unlink(missing_ok=True)

    out = pathlib.Path(out) if out else DATA / "runs.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    rate = len(rows) / sim_s if sim_s else 0
    print(f"{len(rows)} runs in {sim_s:.1f}s ({rate:.1f}/s), {failed} failed -> {out}")
    if rows:
        p = np.mean([r["passed"] for r in rows])
        pre = np.mean([r["passed_pre2028"] for r in rows])
        print(f"pass rate: post-2028 {p:.1%}, pre-2028 {pre:.1%}")
    return rows
