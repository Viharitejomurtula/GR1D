"""Run scenarios through the Modelica model and grade the results.

This is the piece that joins scenario.py to grader.py. A Scenario goes in, a Grade
comes out.

The model is compiled once into an executable that accepts -override, rather than
recompiled per scenario -- compilation dominates runtime (tens of seconds versus well
under a second to simulate), so recompiling per run would make batches impossible.

On macOS the toolchain runs in a container, because OpenModelica dropped macOS binaries
after v1.16. The compiled binary is therefore a Linux binary and must also be *run*
inside the container. On Windows or Linux, set GR1D_NATIVE=1 to skip Docker entirely.
"""

from __future__ import annotations

import csv
import os
import pathlib
import subprocess

import numpy as np

from . import constants as C
from .grader import Grade, grade
from .scenario import Scenario

REPO = pathlib.Path(__file__).resolve().parent.parent
BUILD = REPO / "build"
MODEL = "RideThroughCore"
IMAGE = os.environ.get("OM_IMAGE", "openmodelica/openmodelica:v1.27.1-ompython")
NATIVE = os.environ.get("GR1D_NATIVE") == "1"

# Scenario field -> Modelica parameter. Only fields the model actually declares are sent;
# omc rejects overrides for parameters that do not exist. Fields absent here (relay
# settings, VFD thresholds, rack composition) are sampled but not yet consumed by the
# model -- they are wired in as those components are built out.
PARAM_MAP = {
    "dip_depth_pu": "dip_depth_pu",
    "dip_duration_s": "dip_duration_s",
    "dip_start_s": "dip_start_s",
    "recovery_tau_s": "recovery_tau_s",
    "overshoot_pu": "overshoot_pu",
    "reclose_gap_s": "reclose_gap_s",
    "workload": "workload",
    "swing_size_frac": "swing_size_frac",
    "swing_freq_hz": "swing_freq_hz",
    "swing_phase": "swing_phase",
    "supply_voltage_v": "supply_voltage_v",
    "outdoor_temp_c": "outdoor_temp_c",
    "cooling_share_25c": "cooling_share_25c",
    "cooling_compressor_frac": "cooling_compressor_frac",
    "cooling_fan_frac": "cooling_fan_frac",
    "battery_soc0": "battery_soc0",
    "battery_age_yr": "battery_age_yr",
    "psu_restart_delay_s": "psu_restart_delay_s",
    "handback_delay_s": "handback_delay_s",
    "ramp_back_s": "ramp_back_s",
    "transfer_threshold_pu": "transfer_threshold_pu",
    "relay_pickup_pu": "relay_pickup_pu",
    "relay_delay_s": "relay_delay_s",
    "restart_surge_x": "restart_surge_x",
    "restart_surge_s": "restart_surge_s",
    "battery_temp_c": "battery_temp_c",
    "psu_trip_spread_frac": "psu_trip_spread_frac",
    "faulted_phase_frac": "faulted_phase_frac",
    "legacy_load_frac": "legacy_load_frac",
}

INT_PARAMS = {"shelves_per_rack": "shelves_per_rack", "bbu_modules_per_rack": "bbu_modules_per_rack"}

TRIP_SIGNALS = {
    "psu_enabled": ("psu_shutdown", False),
    "bbu_active": ("bbu_takeover", True),
    "cool_s1_tripped": ("cooling_stage1", True),
    "cool_s2_tripped": ("cooling_stage2", True),
    "servers_lost_power": ("servers_lost", True),
    "facility_connected": ("facility_disconnect", False),
}


def _docker(cmd: list[str], workdir: str = "/work/build") -> subprocess.CompletedProcess:
    if NATIVE:
        return subprocess.run(cmd, cwd=BUILD, capture_output=True, text=True, timeout=900)
    full = ["docker", "run", "--rm", "-v", f"{REPO}:/work", "-w", workdir, IMAGE] + cmd
    return subprocess.run(full, capture_output=True, text=True, timeout=900)


def build(force: bool = False) -> pathlib.Path:
    """Compile the model once. Returns the executable path."""
    BUILD.mkdir(exist_ok=True)
    exe = BUILD / MODEL
    if exe.exists() and not force:
        return exe

    script = BUILD / "build_exe.mos"
    script.write_text(
        f'loadFile("/work/model/{MODEL}.mo"); getErrorString();\n'
        f'buildModel({MODEL}, startTime=0, stopTime={C.WINDOW_S}, '
        f'numberOfIntervals=4000, method="dassl", tolerance=1e-6, outputFormat="csv");\n'
        f"getErrorString();\n"
    )
    r = _docker(["omc", "build_exe.mos"])
    if not exe.exists():
        raise RuntimeError(f"build failed:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
    return exe


def _overrides(sc: Scenario) -> str:
    parts = []
    for field, param in PARAM_MAP.items():
        parts.append(f"{param}={float(getattr(sc, field))}")
    for field, param in INT_PARAMS.items():
        parts.append(f"{param}={int(getattr(sc, field))}")
    parts.append(f"z_total_pu={sc.z_total_pct / 100.0}")
    parts.append(f"second_dip={'true' if sc.second_dip else 'false'}")
    return ",".join(parts)


def _read_csv(path: pathlib.Path) -> dict[str, np.ndarray]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise RuntimeError(f"empty result file: {path}")
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def _extract_trips(data: dict[str, np.ndarray]) -> list[str]:
    """Turn boolean state transitions into timestamped trip labels."""
    t = data["time"]
    trips: list[str] = []
    for signal, (label, on_rise) in TRIP_SIGNALS.items():
        if signal not in data:
            continue
        v = data[signal] > 0.5
        edges = np.nonzero(np.diff(v.astype(int)) == (1 if on_rise else -1))[0]
        for e in edges[:3]:  # a few per signal is enough to explain a run
            trips.append(f"{label}@{t[e + 1]:.3f}s")
    return sorted(trips, key=lambda s: float(s.split("@")[1].rstrip("s")))


def run(sc: Scenario, tag: str = "run") -> Grade:
    """Simulate one scenario and grade it."""
    build()
    prefix = f"{tag}"
    cmd = [f"./{MODEL}", "-override", _overrides(sc), "-r", f"{prefix}_res.csv"]
    r = _docker(cmd)

    res = BUILD / f"{prefix}_res.csv"
    if not res.exists():
        raise RuntimeError(f"simulation produced no result:\n{r.stdout[-2000:]}\n{r.stderr[-1500:]}")

    d = _read_csv(res)
    storage_left = float(d["soc"][-1]) if "soc" in d else float("nan")

    psu_restart_s = None
    if "psu_enabled" in d:
        on = d["psu_enabled"] > 0.5
        down = np.nonzero(np.diff(on.astype(int)) == -1)[0]
        up = np.nonzero(np.diff(on.astype(int)) == 1)[0]
        if down.size and up.size and up[-1] > down[0]:
            psu_restart_s = float(d["time"][up[-1] + 1] - d["time"][down[0] + 1])

    return grade(
        d["time"],
        d["v_sdp_pu"],
        d["p_grid_w"],
        d["i_grid_pu"],
        # The envelope check grades whether the facility stayed *connected to the grid*,
        # which is the relay state -- not whether the servers kept power (a facility can be
        # connected while its servers ride on battery).
        connected=None if "facility_connected" not in d else (d["facility_connected"] > 0.5),
        storage_left=storage_left,
        psu_restart_s=psu_restart_s,
        trips=_extract_trips(d),
    )
