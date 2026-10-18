"""HTTP API around the ride-through simulator.

Runs the real OpenModelica model per request, about 0.3 s. The model is compiled into
the container image at build time; compiling per request would take tens of seconds.

The frontend falls back to the precomputed grid when this is unreachable, so an outage
degrades the demo rather than ending it.
"""

from __future__ import annotations

import dataclasses
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


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": runner.MODEL, "window_s": C.WINDOW_S}


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

    clean: dict[str, float] = {}
    for key, value in req.overrides.items():
        if key not in FIELD_ORDER:
            raise HTTPException(400, f"unknown input {key!r}")
        lo, hi = LIMITS.get(key, (None, None))
        if lo is not None:
            value = max(lo, min(hi, value))
        clean[key] = int(value) if isinstance(getattr(base, key), int) else float(value)

    scenario = dataclasses.replace(base, **clean)
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
    )
