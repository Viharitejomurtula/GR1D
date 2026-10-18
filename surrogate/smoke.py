"""Smoke test for a saved surrogate model directory: does it load and behave sanely?

What this file is
    A self-contained check that anyone (or any agent) can run on a trained model without knowing how it
    was built:  python -m surrogate.smoke [model_dir] [--sim N]
    Each check prints PASS/FAIL with a one-line reason; the exit code is 0 only if every check passes.
    It tests mechanics and sanity, not accuracy: accuracy is in the model's metrics.json and from
    surrogate.verify against the simulator.

Checks
    files        every artifact train() writes is present (members, encoder, config, calibration,
                 provenance, split, metrics)
    provenance   the dataset's simulator commit is recorded (warns if the simulator had uncommitted changes)
    load         predict.Surrogate.load works and the member count matches config.json
    inputs       the encoder's inputs equal today's sim.scenario.FIELD_ORDER minus the excluded fields
                 (a model trained on another simulator version fails here)
    predict      2,000 fresh sample_many scenarios: no NaN or inf, P(pass) in [0, 1], stds >= 0, failure
                 modes among the trained classes, deterministic (same input -> same output)
    ranges       predicted means stay within the training targets' range widened by 10% of it (upper side
                 only for recovery_margin_s, which censoring bounds from above; older encoders without target
                 ranges: mean +/- 10 std)
    calibration  calibration.json is applied (regression stds = raw member std x scale)
    ranges_recorded  the encoder stores each input's training range (models trained before this was added fail)
    presets      GRID_FRIENDLY and LEGACY_UPS give finite predictions; inputs outside the training range
                 are reported in outside_training
    onnx         every member exports to ONNX and matches PyTorch within CONFIG["onnx_parity_atol"]
    simulator    (only with --sim N and a working simulator) N fresh scenarios through surrogate.verify

Inputs: model_dir (default surrogate/models/v1, relative to the repo root).
Outputs: printed report; exit code 0 (all PASS) or 1.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

from sim import scenario
from surrogate import data as sdata
from surrogate.config import CONFIG
from surrogate.features import REGRESSION_TARGETS
from surrogate.predict import Surrogate

DEFAULT_DIR = sdata.REPO_ROOT / "surrogate" / "models" / "v1"
FILES = ("encoder.json", "config.json", "calibration.json", "provenance.json", "split.json", "metrics.json")
RANGE_MARGIN = 0.10        # "ranges" check: predicted means within the training target range +/- this x range
RANGE_STDS = 10.0          # fallback for encoders without target ranges: target mean +/- this many target stds


def run(model_dir: str | Path = DEFAULT_DIR, sim_n: int = 0, seed: int = 424242) -> list[tuple[str, bool, str]]:
    """All checks on model_dir. Output: [(check, passed, detail)]. seed draws the fresh scenarios."""
    d, out = Path(model_dir), []

    def check(name: str, ok: bool, detail: str) -> bool:
        out.append((name, bool(ok), detail))
        return bool(ok)

    cfg = json.loads((d / "config.json").read_text()) if (d / "config.json").exists() else {}
    k = cfg.get("n_members", CONFIG["n_members"])
    missing = [f for f in FILES + tuple(f"member_{i}.pt" for i in range(k)) if not (d / f).exists()]
    if not check("files", not missing, f"missing {missing}" if missing else f"{len(FILES) + k} artifacts present"):
        return out

    prov = json.loads((d / "provenance.json").read_text())
    check("provenance", bool(prov.get("simulator_commit")),
          f"simulator commit {str(prov.get('simulator_commit'))[:9]}, dirty={prov.get('dirty')}, rows={prov.get('n')}"
          + (" (WARNING: built from uncommitted simulator changes)" if prov.get("dirty") else ""))

    try:
        sur = Surrogate.load(d)
    except Exception as e:  # noqa: BLE001 - report any load failure as a failed check
        check("load", False, f"{type(e).__name__}: {e}")
        return out
    enc = sur.ensemble.encoder
    check("load", len(sur.ensemble.members) == k, f"{len(sur.ensemble.members)} members, {enc.n_features} features")

    check("ranges_recorded", bool(enc.low), "training input ranges stored (extrapolation can be flagged)" if enc.low
          else "encoder predates training-range tracking: out-of-range inputs cannot be flagged; retrain")

    expected = [f for f in scenario.FIELD_ORDER if f not in enc.excluded]
    have = enc.continuous + list(enc.categories)
    check("inputs", sorted(have) == sorted(expected),
          "matches today's Scenario fields" if sorted(have) == sorted(expected)
          else f"model inputs differ from today's simulator: only in model {sorted(set(have) - set(expected))}, "
               f"only in simulator {sorted(set(expected) - set(have))}")

    scs = scenario.sample_many(2_000, seed=seed)
    p, p2 = sur.predict(scs), sur.predict(scs)
    num = p.select_dtypes("number")
    bad = []
    if not np.isfinite(num.to_numpy()).all():
        bad.append("NaN/inf")
    if not p["p_pass_mean"].between(0, 1).all():
        bad.append("P(pass) outside [0, 1]")
    if (p[[c for c in p if c.endswith("_std")]] < 0).any().any():
        bad.append("negative std")
    if not set(p["failure_mode"]) <= set(enc.classes):
        bad.append("unknown failure mode")
    if not p.equals(p2):
        bad.append("not deterministic")
    check("predict", not bad, ", ".join(bad) if bad else
          f"2,000 scenarios; P(pass) mean {p['p_pass_mean'].mean():.3f}; modes {p['failure_mode'].nunique()}")

    far = []
    for t in REGRESSION_TARGETS:
        y = p[f"{t}_mean"].to_numpy()
        if enc.target_low:
            lo, hi = enc.target_low[t], enc.target_high[t]
            pad = RANGE_MARGIN * (hi - lo)
            # recovery_margin_s: censored runs only bound the margin from above, and training lets
            # predictions go below the recorded value, so only the upper side is checked.
            low_ok = (t == "recovery_margin_s") | (y >= lo - pad)
            if (~low_ok | (y > hi + pad)).any():
                far.append(f"{t} [{y.min():.3g}, {y.max():.3g}] vs training [{lo:.3g}, {hi:.3g}]")
        else:
            z = np.log1p(np.clip(y, 0, None)) if t == "floor_violation_s" else y
            if (np.abs(z - enc.target_mean[t]) > RANGE_STDS * enc.target_std[t]).any():
                far.append(t)
    check("ranges", not far, f"predictions outside the training targets' range: {far}" if far
          else f"all predicted means within the training targets' range (+/- {RANGE_MARGIN:.0%})")

    scale = json.loads((d / "calibration.json").read_text())
    x = enc.transform(scs[:200])
    raw = sur.ensemble.std_scale; sur.ensemble.std_scale = {}
    r0 = sur.ensemble.predict(x); sur.ensemble.std_scale = raw
    r1 = sur.ensemble.predict(x)
    ok = all(np.allclose(r1[f"{t}_std"], r0[f"{t}_std"] * scale.get(t, 1.0), rtol=1e-6) for t in REGRESSION_TARGETS)
    check("calibration", ok and bool(scale), "scales " + ", ".join(f"{t} x{v:.2f}" for t, v in scale.items()))

    pr = sur.predict([scenario.GRID_FRIENDLY, scenario.LEGACY_UPS])
    finite = np.isfinite(pr.select_dtypes("number").to_numpy()).all()
    check("presets", finite, "; ".join(f"{n}: P(pass) {r.p_pass_mean:.2f}, outside training [{r.outside_training or 'none'}]"
                                       for n, (_, r) in zip(("GRID_FRIENDLY", "LEGACY_UPS"), pr.iterrows())))

    from surrogate import export
    with tempfile.TemporaryDirectory() as tmp:
        par = export.parity(sur.ensemble, export.export(sur.ensemble, tmp), scs[:500])
    check("onnx", par["passed"], f"max |PyTorch - ONNX| {max(par['max_abs_diff']):.1e} (atol {par['atol']:g})")

    if sim_n:
        ok_sim, why = sdata.simulator_available()
        if not ok_sim:
            check("simulator", False, f"--sim requested but {why}")
        else:
            from surrogate import verify
            v = verify.verify(d, n=sim_n, seed=seed)
            check("simulator", v["usable"] > 0, f"{v['usable']}/{v['n']} usable runs, accuracy {v['accuracy']:.2f}, "
                                               f"confusion {v['confusion']}")
    return out


def main(argv: list[str] | None = None) -> int:
    """Command line: python -m surrogate.smoke [model_dir] [--sim N]. Prints the report; returns the exit code."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model_dir", nargs="?", default=str(DEFAULT_DIR))
    ap.add_argument("--sim", type=int, default=0, help="also check N fresh scenarios against the simulator")
    a = ap.parse_args(argv)
    res = run(a.model_dir, a.sim)
    for name, ok, detail in res:
        print(f"{'PASS' if ok else 'FAIL'}  {name:12s} {detail}")
    passed = all(ok for _, ok, _ in res)
    print(f"\nSMOKE TEST {'PASSED' if passed else 'FAILED'} ({sum(ok for _, ok, _ in res)}/{len(res)} checks) for {a.model_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
