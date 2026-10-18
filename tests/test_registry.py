"""Tests for surrogate/registry.py: model selection, pluggable loaders, and the SurrogateModel contract.

What this file is
    (a) resolution order: explicit argument > GR1D_SURROGATE > surrogate/models/ACTIVE;
    (b) a dummy model (numpy only, no torch) registered under a fake format in a tmp dir runs through
        ridethrough.pipeline.performance, proving a new architecture can be swapped in;
    (c) the committed v1 loads through the registry and satisfies the protocol (needs torch);
    (d) the registry and surrogate.web import without torch/pandas (the API image has neither).

Reads (read-only): surrogate/models/v1. Writes: only pytest tmp dirs.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from ridethrough.pipeline import joint, performance
from sim.scenario import FIELD_ORDER
from surrogate import registry

CLASSES = ["passed", "cooling_trip", "psu_shutdown"]


def _model_dir(root, name, fmt=None):
    d = root / name
    d.mkdir(parents=True)
    if fmt:
        (d / "manifest.json").write_text(json.dumps({"format": fmt, "name": name}))
    return d


def test_resolution_order(tmp_path, monkeypatch):
    models = tmp_path / "models"
    for n in ("a", "b", "c"):
        _model_dir(models, n)
    monkeypatch.setattr(registry, "MODELS_DIR", models)
    monkeypatch.setattr(registry, "ACTIVE_FILE", models / "ACTIVE")
    monkeypatch.delenv(registry.ENV_VAR, raising=False)
    with pytest.raises(FileNotFoundError):
        registry.resolve()
    (models / "ACTIVE").write_text("a\n")
    assert registry.resolve() == (models / "a").resolve()
    monkeypatch.setenv(registry.ENV_VAR, "b")
    assert registry.resolve() == (models / "b").resolve()
    assert registry.resolve("c") == (models / "c").resolve()
    assert registry.resolve(str(models / "a")) == (models / "a").resolve()      # a path works too
    with pytest.raises(FileNotFoundError):
        registry.resolve("nope")


class DummySurrogate:
    """A non-ensemble model of a made-up format: P(fail) rises with dip depth. No torch."""

    classes = CLASSES
    input_fields = list(FIELD_ORDER)

    def __init__(self):
        self.provenance = {"trained_rows": 0}

    def _p_fail(self, frame):
        z = frame.to_numpy(float)
        return 1.0 / (1.0 + np.exp(-(z[:, 0] - z[:, 0].mean())))

    def predict(self, scenarios) -> pd.DataFrame:
        frame = scenarios if isinstance(scenarios, pd.DataFrame) else pd.DataFrame(scenarios, columns=list(FIELD_ORDER))
        pf = self._p_fail(frame)
        out = {"p_pass_mean": 1 - pf, "p_pass_std": np.zeros(len(pf))}
        for t in registry.REGRESSION:
            out[f"{t}_mean"], out[f"{t}_std"] = pf * 2.0, np.zeros(len(pf))
        probs = np.column_stack([1 - pf, 0.25 * pf, 0.75 * pf])
        for i, c in enumerate(CLASSES):
            out[f"prob:{c}"] = probs[:, i]
        out["failure_mode"] = np.array(CLASSES)[probs.argmax(1)]
        out["failure_mode_prob"] = probs.max(1)
        out["outside_training"] = [""] * len(pf)
        return pd.DataFrame(out)

    def member_fail_probs(self, scenarios) -> np.ndarray:
        frame = scenarios if isinstance(scenarios, pd.DataFrame) else pd.DataFrame(scenarios, columns=list(FIELD_ORDER))
        return self._p_fail(frame)[None, :]


def test_dummy_model_swaps_in(tmp_path, monkeypatch):
    calls = []

    def loader(d, manifest):
        calls.append((d, manifest))
        return DummySurrogate()

    registry.register_loader("dummy-test/1", loader)
    d = _model_dir(tmp_path, "dummy", fmt="dummy-test/1")
    monkeypatch.setenv(registry.ENV_VAR, str(d))
    sur = registry.load_active()
    assert calls and calls[0][1]["format"] == "dummy-test/1"
    assert isinstance(sur, registry.SurrogateModel)
    assert sur.provenance["name"] == "dummy" and sur.provenance["format"] == "dummy-test/1" and sur.provenance["trained_rows"] == 0

    sc, _ = joint.sample_joint(500, seed=1)
    ev = performance.Evaluator(sur)
    assert ev.names == ["p_fail", "mode:cooling_trip", "mode:psu_shutdown", *performance.CONTINUOUS]
    y = ev(sc.to_numpy())                       # drivers.py calls it with arrays
    assert y.shape == (500, len(ev.names))
    np.testing.assert_allclose(y[:, 1] + y[:, 2], y[:, 0])
    summary, y2 = performance.performance(ev, sc, seed=0)
    np.testing.assert_array_equal(y, y2)
    assert summary["n_events"] == 500 and len(summary["fail_probability"]["by_ensemble_member"]) == 1
    assert summary["fail_probability"]["mean_per_event_member_spread"] == 0.0
    assert summary["share_inputs_outside_training"] == 0.0
    assert set(summary["failure_mode_share"]) == {"cooling_trip", "psu_shutdown"}


def test_unknown_format(tmp_path):
    with pytest.raises(KeyError):
        registry.load(_model_dir(tmp_path, "x", fmt="no-such-format"))


def test_v1_via_registry():
    pytest.importorskip("torch")
    sur = registry.load_active("v1")
    assert isinstance(sur, registry.SurrogateModel)
    assert "passed" in sur.classes and sur.provenance["name"] == "v1" and sur.provenance["format"] == "torch-ensemble"
    sc, _ = joint.sample_joint(200, seed=2)
    pred = sur.predict(sc)
    for c in ["p_pass_mean", "p_pass_std", "failure_mode", "failure_mode_prob", "outside_training",
              *[f"{t}_{k}" for t in registry.REGRESSION for k in ("mean", "std")], *[f"prob:{c}" for c in sur.classes]]:
        assert c in pred.columns, c
    probs = pred[[f"prob:{c}" for c in sur.classes]].to_numpy()
    np.testing.assert_allclose(probs.sum(1), 1.0, atol=1e-5)
    np.testing.assert_allclose(probs.max(1), pred["failure_mode_prob"].to_numpy())
    m = sur.member_fail_probs(sc)
    assert m.shape == (sur.provenance["n_members"], 200)
    np.testing.assert_allclose(1 - m.mean(0), pred["p_pass_mean"].to_numpy(), atol=1e-6)


def test_api_side_imports_without_torch():
    code = ("import sys; sys.modules['torch'] = None; sys.modules['pandas'] = None\n"
            "from surrogate import registry, web\n"
            "p = web.active_json(); assert p.exists(), p\n"
            "print(p)")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=registry.REPO_ROOT)
    assert r.returncode == 0, r.stderr
