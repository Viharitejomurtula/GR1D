"""HTTP API around the ride-through simulator.

Runs the real OpenModelica model per request, about 0.3 s. The model is compiled into
the container image at build time; compiling per request would take tens of seconds.

The frontend falls back to the precomputed grid when this is unreachable, so an outage
degrades the demo rather than ending it.

POST /predict answers instantly from the neural surrogate (surrogate/models/v1, exported to
frontend/public/data/surrogate.json and evaluated here in numpy: the same file and arithmetic as the
browser). It is an estimate with uncertainty, not a simulation; /simulate stays the ground truth.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import sys
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sim import constants as C  # noqa: E402
from sim import runner  # noqa: E402
from sim.grader import grade  # noqa: E402
from sim.scenario import FIELD_ORDER, GRID_FRIENDLY, LEGACY_UPS  # noqa: E402
from surrogate.web import DEFAULT_JSON, WebSurrogate  # noqa: E402  (numpy only: the image has no PyTorch)

SURROGATE_JSON = pathlib.Path(os.environ.get("SURROGATE_JSON", DEFAULT_JSON))
_surrogate: WebSurrogate | None = None


def surrogate() -> WebSurrogate:
    """The exported surrogate, loaded on first use. 503 when the file is missing or unreadable."""
    global _surrogate
    if _surrogate is None:
        try:
            _surrogate = WebSurrogate(SURROGATE_JSON)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, f"surrogate unavailable ({SURROGATE_JSON}): {exc}") from exc
    return _surrogate

app = FastAPI(title="GR1D ride-through simulator", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

PRESETS = {"grid_friendly": GRID_FRIENDLY, "legacy_ups": LEGACY_UPS}

# Clamped server-side: the UI should not be the only thing stopping a request that cannot
# converge, and out-of-range values are the main way to make the solver fail.
LIMITS = {
    "dip_depth_pu": (0.05, 1.0),
    "dip_duration_s": (0.02, 1.0),
    "outdoor_temp_c": (-10.0, 50.0),
    "battery_age_yr": (0.0, 14.0),
    "workload": (0.3, 1.0),
    "legacy_load_frac": (0.0, 1.0),
    "handback_delay_s": (0.1, 10.0),
    "battery_soc0": (0.2, 1.0),
    "supply_voltage_v": (200.0, 290.0),
    "faulted_phase_frac": (0.0, 1.0),
    "bbu_modules_per_rack": (1, 60),
    "shelves_per_rack": (1, 10),
}


class SimulateRequest(BaseModel):
    preset: str = Field("grid_friendly", description="grid_friendly or legacy_ups")
    overrides: dict[str, float] = Field(default_factory=dict)
    include_trace: bool = Field(False, description="return the time series for the replay panel")
    trace_points: int = Field(300, ge=50, le=2000, description="downsample target")


class Trace(BaseModel):
    """Time series plus the markers the replay panel draws.

    Downsampled: a 15 s run at the 2 ms output step is ~7,500 samples per channel, which
    is far more than a chart needs and too much to ship on every slider move.
    """
    t: list[float]
    voltage_pu: list[float]
    facility_pct: list[float]        # grid draw as % of pre-disturbance
    battery_pct: list[float]         # BBU output as % of pre-disturbance facility power
    t0: float                        # dip start
    t1: float                        # dip clears
    back: float | None               # voltage back above 0.90 pu
    deadline: float | None           # back + 2.0 s, the NOGRR recovery deadline
    reached90: float | None          # when draw regained 90% of pre-disturbance
    min_pct: float


class SimulateResponse(BaseModel):
    passed: bool
    passed_pre2028: bool
    failure_mode: str
    recovery_margin_s: float
    min_power: float
    final_power_frac: float
    peak_current_pu: float
    floor_violation_s: float
    envelope_violation_s: float
    storage_left: float
    trips: list[str]
    scenario: dict[str, float]
    source: str = "simulator"
    trace: Trace | None = None


@app.get("/health")
def health() -> dict:
    try:
        prov = surrogate().spec["provenance"]
        sur = {"loaded": True, "simulator_commit": prov.get("simulator_commit"), "rows": prov.get("rows")}
    except HTTPException as exc:
        sur = {"loaded": False, "error": exc.detail}
    return {"ok": True, "model": runner.MODEL, "window_s": C.WINDOW_S, "surrogate": sur}


class Estimate(BaseModel):
    mean: float
    std: float = Field(description="calibrated: about 95% of test errors fall within +/- 2 std")


class PredictRequest(BaseModel):
    preset: str = Field("grid_friendly", description="grid_friendly or legacy_ups; supplies every input not overridden")
    overrides: dict[str, float] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    pass_probability: float
    pass_probability_std: float = Field(description="spread across ensemble members; high means guessing")
    recovery_margin_s: Estimate
    min_power: Estimate
    peak_current_pu: Estimate
    floor_violation_s: Estimate
    failure_mode: str
    failure_mode_probs: dict[str, float]
    outside_training: list[str] = Field(description="inputs beyond the training data: the answer is an extrapolation")
    scenario: dict[str, float]
    source: str = "surrogate"
    model: dict


def _clean_overrides(base, overrides: dict[str, float]) -> dict[str, float]:
    """Validate and clamp overrides exactly as /simulate does (unknown input -> 400; LIMITS clamp)."""
    clean: dict[str, float] = {}
    for key, value in overrides.items():
        if key not in FIELD_ORDER:
            raise HTTPException(400, f"unknown input {key!r}")
        lo, hi = LIMITS.get(key, (None, None))
        if lo is not None:
            value = max(lo, min(hi, value))
        clean[key] = int(value) if isinstance(getattr(base, key), int) else float(value)
    return clean


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    """Instant surrogate estimate for the preset plus overrides (the same scenario /simulate would run)."""
    base = PRESETS.get(req.preset)
    if base is None:
        raise HTTPException(400, f"unknown preset {req.preset!r}; expected one of {list(PRESETS)}")
    scenario = dataclasses.replace(base, **_clean_overrides(base, req.overrides))
    values = {k: float(getattr(scenario, k)) for k in FIELD_ORDER}
    sur = surrogate()
    p = sur.predict(values, req.preset)
    est = lambda t: Estimate(mean=p[f"{t}_mean"], std=p[f"{t}_std"])  # noqa: E731
    spec = sur.spec
    return PredictResponse(
        pass_probability=p["p_pass_mean"], pass_probability_std=p["p_pass_std"],
        recovery_margin_s=est("recovery_margin_s"), min_power=est("min_power"),
        peak_current_pu=est("peak_current_pu"), floor_violation_s=est("floor_violation_s"),
        failure_mode=p["failure_mode"], failure_mode_probs=p["failure_mode_probs"],
        outside_training=p["outside_training"], scenario=values,
        model={**spec["provenance"], "test_accuracy": spec["metrics"]["test"].get("passed_accuracy"),
               "test_auc": spec["metrics"]["test"].get("passed_auc")},
    )


PIPELINE_DIR = pathlib.Path(os.environ.get("PIPELINE_DIR", pathlib.Path(__file__).resolve().parent.parent / "reports" / "pipeline"))


@app.get("/pipeline")
def pipeline(design: str = "grid_friendly") -> dict:
    """The saved product-performance report (python -m ridethrough.pipeline.run): the outcome distribution for one grid
    event hitting one site and the ranked failure drivers. Read from disk, not computed here (the image has no PyTorch)."""
    if design not in PRESETS:
        raise HTTPException(400, f"design must be one of {list(PRESETS)}")
    path = PIPELINE_DIR / f"pipeline_{design}.json"
    if not path.exists():
        raise HTTPException(404, f"no pipeline report at {path}; run python -m ridethrough.pipeline.run --design {design}")
    return json.loads(path.read_text())


@app.get("/schema")
def schema() -> dict:
    """What the UI may send, and the bounds it will be held to."""
    return {
        "presets": list(PRESETS),
        "inputs": list(FIELD_ORDER),
        "limits": {k: list(v) for k, v in LIMITS.items()},
        "defaults": {k: float(getattr(GRID_FRIENDLY, k)) for k in FIELD_ORDER},
    }


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    base = PRESETS.get(req.preset)
    if base is None:
        raise HTTPException(400, f"unknown preset {req.preset!r}; expected one of {list(PRESETS)}")

    scenario = dataclasses.replace(base, **_clean_overrides(base, req.overrides))
    res = runner.BUILD / "unset"

    try:
        # A unique name per request. Reusing one path meant deleting and recreating the
        # same file through the container's virtiofs mount, whose cache then intermittently
        # reported a converged run as missing -- and it also ruled out ever grading a
        # previous request's trace.
        name = f"api_{uuid.uuid4().hex}_res.csv"
        res = runner.BUILD / name
        cmd = [f"./{runner.MODEL}", "-override", runner._overrides(scenario), "-r", name]
        runner._docker(cmd)
        # The container writes through a virtiofs mount, which can lag the process exit by
        # a few hundred milliseconds. Without this wait the API intermittently reports a
        # converged run as a failure.
        for _ in range(40):
            if res.exists():
                break
            time.sleep(0.05)
        if not res.exists():
            raise HTTPException(
                422,
                "simulation did not converge for this combination — typically a dip too "
                "deep for the constant-power load model",
            )

        d = runner._read_csv(res)
        # A trace that stops short did not converge. Grading it anyway is how deep dips
        # previously came back as clean passes.
        if d["time"][-1] < 0.99 * C.WINDOW_S:
            raise HTTPException(
                422,
                "simulation did not converge for this combination — "
                "typically a dip too deep for the constant-power load model",
            )

        g = grade(
            d["time"], d["v_sdp_pu"], d["p_grid_w"], d["i_grid_pu"],
            connected=(d["facility_connected"] > 0.5) if "facility_connected" in d else None,
            storage_left=float(d["soc"][-1]) if "soc" in d else float("nan"),
            trips=runner._extract_trips(d),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"simulation failed: {exc}") from exc
    finally:
        res.unlink(missing_ok=True)

    trace = _build_trace(d, scenario, req.trace_points) if req.include_trace else None

    return SimulateResponse(
        passed=g.passed,
        passed_pre2028=g.passed_pre2028,
        failure_mode=g.failure_mode,
        recovery_margin_s=g.recovery_margin_s,
        min_power=g.min_power,
        final_power_frac=g.final_power_frac,
        peak_current_pu=g.peak_current_pu,
        floor_violation_s=g.floor_violation_s,
        envelope_violation_s=g.envelope_violation_s,
        storage_left=g.storage_left,
        trips=g.trips,
        scenario={k: float(getattr(scenario, k)) for k in FIELD_ORDER},
        trace=trace,
    )


def _build_trace(d, scenario, n_points: int) -> Trace:
    import numpy as np

    t = d["time"]
    v = d["v_sdp_pu"]
    p = d["p_grid_w"]

    t0 = float(scenario.dip_start_s)
    t1 = t0 + float(scenario.dip_duration_s)

    pre = p[t < t0 - 0.01]
    p_pre = float(pre.mean()) if pre.size else float(p.max() or 1.0)
    pct = 100.0 * p / (p_pre or 1.0)

    bat = d.get("p_bbu_w")
    bat_pct = 100.0 * bat / (p_pre or 1.0) if bat is not None else np.zeros_like(t)

    # Voltage back above 0.90 pu after the dip: where the NOGRR recovery clock starts.
    after = np.nonzero((t > t1) & (v >= C.RECOVERY_TRIGGER_V_PU))[0]
    back = float(t[after[0]]) if after.size else None
    deadline = back + C.RECOVERY_DEADLINE_S if back is not None else None

    reached = None
    if back is not None:
        got = np.nonzero((t >= back) & (pct >= 100.0 * C.RECOVERY_FRACTION))[0]
        reached = float(t[got[0]]) if got.size else None

    # Even downsample; the charts do not need every solver sample.
    step = max(1, len(t) // n_points)
    sl = slice(None, None, step)
    r3 = lambda a: [round(float(x), 3) for x in a[sl]]

    dip = (t >= t0) & (t <= t1 + 1.0)
    return Trace(
        t=r3(t),
        voltage_pu=r3(v),
        facility_pct=r3(pct),
        battery_pct=r3(bat_pct),
        t0=t0, t1=t1, back=back, deadline=deadline, reached90=reached,
        min_pct=round(float(pct[dip].min()) if dip.any() else float(pct.min()), 2),
    )
