"""Check a trained surrogate against the actual simulator.

What this file is
    simulate() runs a list of scenarios through the actual simulator in ONE container invocation
    (sim.batch._run_all, the loop run_batch uses; starting a container per scenario dominates run
    time) and grades each run with sim.runner.grade_trace, the grading runner.run and run_batch share. verify() draws new scenarios (a
    seed not used for the training data), runs them through the surrogate and simulate(), and reports
    agreement (the seed must not be one that produced the training data, including any merged shard's).
    verify_failures() re-runs scenarios the surrogate predicts to fail and returns those the
    simulator confirms. All need OpenModelica (Docker or GR1D_NATIVE=1) and raise RuntimeError without it.

Inputs: model_dir (train() output); n and seed, or candidate scenarios.
Outputs: simulate -> DataFrame with the Scenario fields and Grade outputs (run_batch's CSV columns);
    verify -> {"n", "seed", "simulated" (runs graded), "usable" (after data.load's filters),
    "confusion" {tp, fp, fn, tn} with pass as positive, "accuracy", "margin_mae_s" (uncensored),
    "within_<k>_std" per regression target}; verify_failures -> list of (Scenario, Grade-row dict).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from sim import batch, runner, scenario
from surrogate import data as sdata
from surrogate.config import CONFIG
from surrogate.features import REGRESSION_TARGETS
from surrogate.predict import Surrogate


def _require_simulator() -> None:
    """Raise RuntimeError with the reason when the simulator cannot run."""
    ok, why = sdata.simulator_available()
    if not ok:
        raise RuntimeError(f"simulator unavailable: {why}")


def simulate(scenarios: list) -> pd.DataFrame:
    """Simulate and grade scenarios in one container invocation; one row per scenario that produced a
    result (same columns and grading as sim.batch.run_batch), with column "index" = position in input."""
    _require_simulator()
    rows = []
    for i, (sc, path) in enumerate(zip(scenarios, batch._run_all(scenarios))):
        if not path.exists():
            continue
        g = runner.grade_trace(runner._read_csv(path))
        inputs = {f: getattr(sc, f) for f in scenario.FIELD_ORDER}
        rows.append({"index": i, **inputs, "passed": int(g.passed), "passed_pre2028": int(g.passed_pre2028),
                     "failure_mode": g.failure_mode, "recovery_margin_s": g.recovery_margin_s, "min_power": g.min_power,
                     "final_power_frac": g.final_power_frac, "floor_violation_s": g.floor_violation_s,
                     "peak_current_pu": g.peak_current_pu, "envelope_violation_s": g.envelope_violation_s,
                     "storage_left": g.storage_left, "numerics_ok": int(g.numerics_ok),
                     "numerics_note": g.numerics_note, "peak_current_raw_pu": g.peak_current_raw_pu,
                     "n_trips": len(g.trips)})
        path.unlink(missing_ok=True)
    return pd.DataFrame(rows)


def verify(model_dir: str | Path, n: int, seed: int) -> dict:
    """Surrogate vs simulator on scenario.sample_many(n, seed); the seed must differ from the training
    dataset's seed (read from its provenance). Simulated runs go through data.load's filters first."""
    prov = json.loads((Path(model_dir) / "provenance.json").read_text())
    if seed == prov.get("seed") or seed in prov.get("seeds", []):
        raise ValueError(f"seed {seed} produced the training data; use another")
    _require_simulator()
    sim = simulate(scenario.sample_many(n, seed=seed))
    with tempfile.TemporaryDirectory() as tmp:
        csv = Path(tmp) / "verify.csv"
        sim.drop(columns="index").to_csv(csv, index=False)
        d, _ = sdata.load(csv)
    pred = Surrogate.load(model_dir).predict(d)
    sim_pass, sur_pass = d["passed"].to_numpy(bool), pred["p_pass_mean"].to_numpy() > 0.5
    k = CONFIG["uncertainty_k"]
    within = {t: float((np.abs(d[t].to_numpy(float) - pred[f"{t}_mean"]) <= k * pred[f"{t}_std"]).mean())
              for t in REGRESSION_TARGETS}
    unc = ~d["censored"].to_numpy(bool)
    return {"n": n, "seed": seed, "simulated": len(sim), "usable": len(d),
            "confusion": {"tp": int((sur_pass & sim_pass).sum()), "fp": int((sur_pass & ~sim_pass).sum()),
                          "fn": int((~sur_pass & sim_pass).sum()), "tn": int((~sur_pass & ~sim_pass).sum())},
            "accuracy": float((sur_pass == sim_pass).mean()),
            "margin_mae_s": float(np.abs(d["recovery_margin_s"].to_numpy() - pred["recovery_margin_s_mean"])[unc].mean()),
            f"within_{k:g}_std": within}


def verify_failures(model_dir: str | Path, candidates: list) -> list:
    """Simulate the candidates the surrogate predicts to fail (P(pass) < 0.5), in one batch.
    Output: [(Scenario, graded row as dict)] for those the simulator also grades as failed."""
    _require_simulator()
    pred = Surrogate.load(model_dir).predict(candidates)
    flagged = [candidates[i] for i in np.flatnonzero(pred["p_pass_mean"].to_numpy() < 0.5)]
    if not flagged:
        return []
    sim = simulate(flagged)
    return [(flagged[r["index"]], r) for r in sim.to_dict("records") if not r["passed"]]
