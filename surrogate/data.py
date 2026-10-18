"""Produce and load simulator datasets for the surrogate.

What this file is
    generate() runs the actual simulator (sim.batch.run_batch) and records which simulator version
    produced the CSV. load() reads such a CSV, drops runs that are not usable training labels and
    flags censored runs. No synthetic or placeholder data is produced anywhere.

Inputs
    generate: n scenarios, seed, out_csv path (never data/runs.csv).
    merge: shard CSVs from generate() (run in parallel with different seeds), out_csv.
    load: a CSV written by sim.batch.run_batch (inputs = Scenario fields, outputs = Grade fields).
Outputs
    generate: the CSV plus <out_csv>.provenance.json {simulator_commit, dirty, n, seed, created}.
    merge: one CSV plus provenance {simulator_commit, dirty, n, seeds, shards}.
    load: (DataFrame with a boolean "censored" column, report dict of counts).
Units: as written by the simulator (seconds, pu, fractions).
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from sim import runner, scenario

REPO_ROOT = runner.REPO
PROTECTED_CSV = (REPO_ROOT / "data" / "runs.csv").resolve()
OUTPUT_COLUMNS = ("passed", "passed_pre2028", "failure_mode", "recovery_margin_s", "min_power",
                  "final_power_frac", "floor_violation_s", "peak_current_pu", "envelope_violation_s",
                  "storage_left", "n_trips")
NUMERIC_OUTPUTS = tuple(c for c in OUTPUT_COLUMNS if c not in ("failure_mode", "storage_left"))
COLLAPSE_MODE = "voltage collapse"
COLLAPSE_MAX_DEPTH_PU = 0.2   # at or below this retained voltage a sustained collapse is a real failure (see load())
NUMERICS_COLUMN = "numerics_ok"   # written by sim.batch since the structure fixes; 0 = the solver's voltage solution is invalid
CRASH_MODE = "no disturbance"
CRASH_DEPTH_PU = 0.9        # a run graded "no disturbance" while the dip retained < 0.9 pu never saw its dip
RECOVERY_FRACTION = 0.9     # final_power_frac below this = the run never recovered (grader's 90% rule)


def simulator_available() -> tuple[bool, str]:
    """Whether the actual simulator can run here: (ok, reason).

    Native mode (GR1D_NATIVE=1) needs `omc` on PATH; otherwise Docker must be installed and running.
    """
    if runner.NATIVE:
        return (shutil.which("omc") is not None, "GR1D_NATIVE=1 but omc is not on PATH")
    if shutil.which("docker") is None:
        return False, "Docker is not installed (or set GR1D_NATIVE=1 with OpenModelica's omc on PATH)"
    r = subprocess.run(["docker", "info"], capture_output=True, text=True)
    return (r.returncode == 0, "Docker is installed but its daemon is not running")


def simulator_commit() -> dict:
    """Git commit of the last change to model/ and sim/, and whether either has uncommitted edits."""
    commit = subprocess.run(["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%H", "--", "model", "sim"],
                            capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", "model", "sim"],
                           capture_output=True, text=True).stdout.strip() != ""
    return {"simulator_commit": commit or None, "dirty": dirty}


def generate(n: int, seed: int, out_csv: str | Path) -> Path:
    """Run n scenarios (sim.scenario.sample_many(n, seed)) through the actual simulator.

    Inputs: n runs; seed; out_csv, the CSV to write (must not be data/runs.csv).
    Output: path of the CSV; <out_csv>.provenance.json is written next to it.
    Raises RuntimeError when the simulator is unavailable, ValueError for data/runs.csv.
    """
    out_csv = Path(out_csv).resolve()
    if out_csv == PROTECTED_CSV:
        raise ValueError("generate() never writes data/runs.csv; choose another path")
    ok, why = simulator_available()
    if not ok:
        raise RuntimeError(f"simulator unavailable: {why}")
    prov = simulator_commit() | {"n": n, "seed": seed, "created": dt.datetime.now().isoformat(timespec="seconds")}
    from sim import batch
    batch.run_batch(n=n, seed=seed, out=out_csv)
    provenance_path(out_csv).write_text(json.dumps(prov, indent=2))
    return out_csv


def provenance_path(csv: str | Path) -> Path:
    """<csv>.provenance.json."""
    csv = Path(csv)
    return csv.with_name(csv.name + ".provenance.json")


def read_provenance(csv: str | Path) -> dict:
    """The provenance written by generate(), or {"simulator_commit": None, "note": ...} if absent."""
    p = provenance_path(csv)
    if p.exists():
        return json.loads(p.read_text())
    return {"simulator_commit": None, "note": f"no {p.name}: dataset not produced by surrogate.data.generate"}


def missing_inputs(csv: str | Path) -> list[str]:
    """Current Scenario inputs (scenario.FIELD_ORDER) absent from the CSV's header: non-empty means the
    dataset predates the current simulator and cannot train or test the surrogate."""
    cols = set(pd.read_csv(csv, nrows=0).columns)
    return [f for f in scenario.FIELD_ORDER if f not in cols]


def merge(shards: list, out_csv: str | Path) -> Path:
    """Concatenate shard CSVs written by generate() into one dataset.

    Every shard must have a provenance file, the same simulator commit and dirty flag, distinct seeds,
    and the same columns. Output: out_csv (never data/runs.csv) and its provenance
    {simulator_commit, dirty, n (rows written), seeds, shards: [each shard's provenance + path]}.
    """
    out_csv = Path(out_csv).resolve()
    if out_csv == PROTECTED_CSV:
        raise ValueError("merge() never writes data/runs.csv; choose another path")
    provs = []
    for s in shards:
        if not provenance_path(s).exists():
            raise ValueError(f"{s}: no provenance file; only generate() output can be merged")
        provs.append(read_provenance(s) | {"path": str(Path(s).resolve())})
    if len({(p["simulator_commit"], p["dirty"]) for p in provs}) != 1:
        raise ValueError("shards come from different simulator versions: "
                         + str(sorted({(p["simulator_commit"], p["dirty"]) for p in provs})))
    seeds = [p["seed"] for p in provs]
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"duplicate seeds {seeds}: shards would repeat scenarios")
    frames = [pd.read_csv(s) for s in shards]
    if any(list(f.columns) != list(frames[0].columns) for f in frames):
        raise ValueError("shards have different columns")
    d = pd.concat(frames, ignore_index=True)
    d.to_csv(out_csv, index=False)
    provenance_path(out_csv).write_text(json.dumps(
        {"simulator_commit": provs[0]["simulator_commit"], "dirty": provs[0]["dirty"], "n": len(d),
         "seeds": seeds, "shards": provs}, indent=2))
    return out_csv


def load(csv: str | Path, require_inputs: bool = True) -> tuple[pd.DataFrame, dict]:
    """Read a simulator CSV, apply the filters and flag censored runs.

    Inputs: csv; require_inputs (default True) raises ValueError when the CSV lacks any current Scenario
        input (missing_inputs). Set False only to inspect the outputs of an older dataset.
    Collapse rule: a run that ended in "voltage collapse" (no operating point even after the PSUs locked out) with
        dip_depth_pu <= COLLAPSE_MAX_DEPTH_PU is KEPT as a failure (passed = 0, failure_mode "voltage collapse") with
        regression_ok = False, so training uses its pass/fail and failure mode but not its other outputs (they come
        from a solve with no operating point). At such depths the network cannot supply the facility, NOGRR 282 still
        requires staying connected, and real ERCOT loads at ~0 pu lost all consumption.
    Filters (each count reported):
        numerics: numerics_ok == 0 (the simulator flagged an invalid run), when the column exists, except collapses
            kept by the collapse rule
        crash: failure_mode == "no disturbance" with dip_depth_pu < 0.9 (the solver failed before the dip)
        non_finite: any numeric output (NUMERIC_OUTPUTS) not finite
    Censored: recovery_margin_s < 0 and final_power_frac < 0.9 (never recovered inside the window, so
        the true margin is at most the recorded one).
    Output: (kept rows with "censored" and "regression_ok" columns, {"rows_read", "collapse_kept", "dropped_numerics",
        "dropped_crash", "dropped_non_finite", "kept", "censored", "missing_inputs"}).
    """
    gone = missing_inputs(csv)
    if gone and require_inputs:
        raise ValueError(f"{csv} predates the current simulator: missing inputs {gone}. "
                         "Regenerate it with surrogate.data.generate.")
    d = pd.read_csv(csv)
    missing = [c for c in OUTPUT_COLUMNS if c not in d.columns]
    if missing:
        raise ValueError(f"{csv}: missing simulator output columns {missing}")
    invalid = (d[NUMERICS_COLUMN] == 0) if NUMERICS_COLUMN in d else pd.Series(False, index=d.index)
    collapse = invalid & (d["failure_mode"] == COLLAPSE_MODE) & (d["dip_depth_pu"] <= COLLAPSE_MAX_DEPTH_PU)
    bad_num = invalid & ~collapse
    crash = ~invalid & (d["failure_mode"] == CRASH_MODE) & (d["dip_depth_pu"] < CRASH_DEPTH_PU)
    finite = np.isfinite(d[list(NUMERIC_OUTPUTS)].astype(float)).all(axis=1) | collapse
    non_finite = ~bad_num & ~crash & ~finite
    kept = d[~bad_num & ~crash & finite].copy()
    kept["regression_ok"] = ~collapse[kept.index]
    kept.loc[~kept["regression_ok"], "passed"] = 0
    kept["censored"] = kept["regression_ok"] & (kept["recovery_margin_s"] < 0) & (kept["final_power_frac"] < RECOVERY_FRACTION)
    report = {"rows_read": len(d), "collapse_kept": int(collapse.sum()), "dropped_numerics": int(bad_num.sum()), "dropped_crash": int(crash.sum()),
              "dropped_non_finite": int(non_finite.sum()), "kept": len(kept), "censored": int(kept["censored"].sum()),
              "missing_inputs": gone}
    return kept.reset_index(drop=True), report
