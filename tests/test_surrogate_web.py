"""Tests for the deployed surrogate: the JSON export, the numpy evaluator, the API endpoint and the browser code.

What this file is
    Checks that frontend/public/data/surrogate.json (exported from surrogate/models/v1 by
    `python -m surrogate.web`) is current and faithful: the numpy evaluator (surrogate.web.WebSurrogate,
    used by the API) matches the PyTorch ensemble; the API's POST /predict serves it; and the browser code
    (frontend/src/surrogate.ts, run under Node) gives the same numbers as the numpy evaluator. Scenarios come
    from sim.scenario.sample_many. Tests needing FastAPI or Node are skipped with the reason when absent.

Reads: surrogate/models/v1, frontend/public/data/surrogate.json, frontend/src/surrogate.ts.
Writes: only pytest's tmp_path.
"""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from sim import scenario
from surrogate import web

JSON_PATH, MODEL_DIR = web.DEFAULT_JSON, web.DEFAULT_MODEL
pytestmark = pytest.mark.skipif(not JSON_PATH.exists(), reason="no exported surrogate; run python -m surrogate.web")


def _values(s) -> dict:
    return {f: float(getattr(s, f)) for f in scenario.FIELD_ORDER}


def test_export_is_current_for_the_committed_model():
    """The deployed JSON was exported from surrogate/models/v1 as it is now (calibration, classes, encoder)."""
    spec = json.loads(JSON_PATH.read_text())
    enc = json.loads((MODEL_DIR / "encoder.json").read_text())
    cal = json.loads((MODEL_DIR / "calibration.json").read_text())
    assert spec["format"] == web.FORMAT and spec["classes"] == enc["classes"]
    assert [c["name"] for c in spec["continuous"]] == enc["continuous"]
    assert {t: v["std_scale"] for t, v in spec["targets"].items()} == cal
    assert spec["background_fields"] == list(scenario.FIELD_ORDER)


def test_numpy_evaluator_matches_pytorch():
    """WebSurrogate (rounded weights in the JSON) vs the PyTorch ensemble on 300 sampled scenarios."""
    d = web.parity(MODEL_DIR, JSON_PATH, n=300, seed=5)
    assert d["p_pass_mean"] < 1e-3 and d["recovery_margin_s_mean"] < 1e-2 and d["failure_mode_agree"] == 1.0


def test_api_predict_serves_the_surrogate():
    """POST /predict returns the numpy evaluator's numbers for the preset plus overrides; bad input -> 400."""
    TestClient = pytest.importorskip("fastapi.testclient", reason="fastapi not installed").TestClient
    from api.main import app
    c = TestClient(app)
    assert c.get("/health").json()["surrogate"]["loaded"] is True
    over = {"dip_depth_pu": 0.8, "dip_duration_s": 0.06, "outdoor_temp_c": 25.0, "battery_age_yr": 4.0}
    r = c.post("/predict", json={"preset": "grid_friendly", "overrides": over})
    assert r.status_code == 200 and r.json()["source"] == "surrogate"
    ref = web.WebSurrogate(JSON_PATH).predict({**_values(scenario.GRID_FRIENDLY), **over})
    assert r.json()["pass_probability"] == pytest.approx(ref["p_pass_mean"], abs=1e-12)
    assert c.post("/predict", json={"overrides": {"not_an_input": 1}}).status_code == 400
    assert c.post("/predict", json={"preset": "nope"}).status_code == 400


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_code_matches_numpy(tmp_path):
    """frontend/src/surrogate.ts (run by Node's TypeScript type stripping) vs WebSurrogate: predict() on 100
    sampled scenarios and marginal() on two slider settings agree to float precision."""
    scs = [_values(s) for s in scenario.sample_many(100, seed=6)]
    fixed = [{"dip_depth_pu": 0.85, "dip_duration_s": 0.06, "outdoor_temp_c": 30.0, "battery_age_yr": 5.0},
             {"dip_depth_pu": 0.0, "dip_duration_s": 0.3, "outdoor_temp_c": -20.0, "battery_age_yr": 10.0}]
    (tmp_path / "in.json").write_text(json.dumps({"scs": scs, "fixed": fixed}))
    ts = web.REPO_ROOT / "frontend" / "src" / "surrogate.ts"
    script = (f"import {{ readFileSync }} from 'node:fs'; import {{ predict, marginal }} from '{ts}';"
              f"const m = JSON.parse(readFileSync('{JSON_PATH}', 'utf8'));"
              f"const i = JSON.parse(readFileSync('{tmp_path / 'in.json'}', 'utf8'));"
              "console.log(JSON.stringify({p: i.scs.map((s) => predict(m, s)), g: i.fixed.map((f) => marginal(m, f))}));")
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout)
    w = web.WebSurrogate(JSON_PATH)
    for s, t in zip(scs, got["p"]):
        ref = w.predict(s)
        assert t["passProbability"] == pytest.approx(ref["p_pass_mean"], abs=1e-9)
        assert t["outputs"]["recovery_margin_s"]["mean"] == pytest.approx(ref["recovery_margin_s_mean"], abs=1e-9)
        assert t["failureMode"] == ref["failure_mode"] and sorted(t["outsideTraining"]) == sorted(ref["outside_training"])
    for f, t in zip(fixed, got["g"]):
        ref = w.marginal(f)
        assert t["passRate"] == pytest.approx(ref["pass_rate"], abs=1e-9) and t["mode"] == ref["mode"]
        assert t["outsideTraining"] == ref["outside_training"]
