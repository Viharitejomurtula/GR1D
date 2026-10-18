"""Joint sampler: the Bayesian network and the scenario distributions, merged into full Scenarios.

What this file is
    One grid event hitting one site is one row. The conditions and site state that the Bayesian network
    (ridethrough.network.sampler) models are drawn jointly from it; the quantities it has no node for are
    drawn from the sim.scenario marginals; everything else (the product's design and settings) is held at a
    reference preset, so the result describes that product rather than a random one.

    Each driver is a Block: a named group of Scenario columns that are always changed together (e.g. season and
    outdoor temperature). The driver ranking (drivers.py) swaps whole blocks, so correlations inside a block
    are kept. Blocks are in group "A" (conditions: what the grid and weather do) or "B" (site state: what the
    equipment is like). Group "C" (design and settings) is not varied.

Reads (read-only)
    the Bayesian network specification and driver fits (via ridethrough.network.sampler), sim.scenario.

Writes
    nothing.

Assumptions (each is a modelling choice, not a measured fact)
    - fault_type -> faulted_phase_frac: SLG 1/3, LLG and LL 2/3, 3LG 1.0.
    - protection_failure -> dip_duration_s: normal draws the normal clearing range (3-4 cycles); breaker
      misoperation or failure draws the delayed range (10-19 cycles). The network's own duration is 55, 167
      or 317 ms by the same classes, so this keeps its conditioning and adds within-class spread.
    - dip depth, shape, battery temperature and state of charge come from the sim.scenario marginals: the
      network's dip_depth_pct takes two values (47.2 and 51.4) and its own notes call that placeholder.
    - site load_fraction (network range 0.20-0.85) -> workload (Scenario range 0.50-1.00) by a linear
      rescale. They are not the same quantity (site load vs IT utilisation); the rescale keeps the ordering
      and the link to temperature.
    - the network's reclose gap (0.5-48 s) is clipped to the simulator's 0.25-5 s; compressor restart time
      (network 10-360 s) is clipped to the simulator's 100-600 s, so about 40% of draws sit at 100 s.
    - battery age is clipped to the simulator's 0-14 years.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ridethrough.network import sampler
from sim import constants as C
from sim import scenario as S
from sim.scenario import FIELD_ORDER, GRID_FRIENDLY, Scenario

LOAD_LOW, LOAD_HIGH = 0.20, 0.85          # network load_fraction range, rescaled onto WORKLOAD_RANGE
WORKLOAD_RANGE = (0.50, 1.00)
PHASE_FRAC = {"SLG": 1 / 3, "LLG": 2 / 3, "LL": 2 / 3, "3LG": 1.0}


@dataclass(frozen=True)
class Block:
    name: str
    group: str            # "A" conditions, "B" site state
    label: str
    columns: tuple[str, ...]   # Scenario fields this block sets
    source: str           # "network" or "scenario": where its distribution comes from
    key: str              # column of the roots table that summarises the block (for the lift tables)


BLOCKS: tuple[Block, ...] = (
    Block("fault_type", "A", "Fault type (phases involved)", ("faulted_phase_frac",), "network", "fault_type"),
    Block("protection", "A", "Protection clearing (normal / breaker problem)", ("dip_duration_s",), "network", "protection_failure"),
    Block("dip_depth", "A", "Sag depth", ("dip_depth_pu", "recovery_tau_s", "overshoot_pu"), "scenario", "dip_depth_pu"),
    Block("reclose", "A", "Reclosing (second dip and gap)", ("second_dip", "reclose_gap_s"), "network", "n_dips"),
    Block("weather", "A", "Season and outdoor temperature", ("outdoor_temp_c",), "network", "outdoor_temp_c"),
    Block("workload_type", "A", "Workload type (power-swing size and rate)", ("swing_size_frac", "swing_freq_hz"), "network", "workload_type"),
    Block("site_load", "A", "Site load level", ("workload",), "network", "load_fraction"),
    Block("battery_age", "B", "Equipment age", ("battery_age_yr",), "network", "equipment_age_years"),
    Block("battery_temp", "B", "Battery hall temperature", ("battery_temp_c",), "scenario", "battery_temp_c"),
    Block("battery_soc", "B", "Battery state of charge", ("battery_soc0",), "scenario", "battery_soc0"),
    Block("compressor_restart", "B", "Compressor restart time", ("compressor_restart_s",), "network", "compressor_restart_s"),
    Block("cooling_makeup", "B", "Cooling plant makeup (compressor vs fan share)", ("cooling_compressor_frac", "cooling_fan_frac"), "scenario", "cooling_compressor_frac"),
)
BLOCK = {b.name: b for b in BLOCKS}
NUISANCE = ("swing_phase",)   # drawn per row, never ranked: the phase of the swing at the sag


def groups(group: str) -> tuple[Block, ...]:
    return tuple(b for b in BLOCKS if b.group == group)


def sample_joint(n: int, seed: int = 0, design: Scenario = GRID_FRIENDLY) -> tuple[pd.DataFrame, pd.DataFrame]:
    """n events at one site design.

    Inputs: n; seed (same arguments give identical output); design, the Scenario whose values are kept for
        every field that is not a block column.
    Output: (scenarios, roots). scenarios has one column per sim.scenario.FIELD_ORDER field (what the
        surrogate takes). roots has the human-readable driver values for the same rows: the network's nodes
        plus the sim-side draws, used for the lift tables.
    """
    bn = sampler.sample_network(n, seed, clip=True)
    rng = np.random.default_rng(seed + 1)
    base = design.to_vector()
    sc = pd.DataFrame(np.tile(base, (n, 1)), columns=list(FIELD_ORDER))

    depth = np.array([S.sample_dip_depth(rng) for _ in range(n)])
    shape = np.array([S.sample_shape(rng, d) for d in depth])
    delayed = (bn["protection_failure"] != "normal").to_numpy()
    lo = np.where(delayed, C.DELAYED_CLEARING_CYCLES[0], C.NORMAL_CLEARING_CYCLES[0])
    hi = np.where(delayed, C.DELAYED_CLEARING_CYCLES[1], C.NORMAL_CLEARING_CYCLES[1])
    soc = rng.uniform(0.80, 1.00, n)
    hall = np.array([S.sample_battery_temp(rng) for _ in range(n)])
    load01 = np.clip((bn["load_fraction"].to_numpy() - LOAD_LOW) / (LOAD_HIGH - LOAD_LOW), 0.0, 1.0)
    temps = S.outdoor_temps()

    sc["faulted_phase_frac"] = bn["fault_type"].map(PHASE_FRAC).to_numpy()
    sc["dip_duration_s"] = rng.uniform(lo, hi) / C.NOMINAL_FREQ_HZ
    sc["dip_depth_pu"], sc["recovery_tau_s"], sc["overshoot_pu"] = depth, shape[:, 0], shape[:, 1]
    sc["second_dip"] = (bn["n_dips"].to_numpy() >= 2).astype(float)
    sc["reclose_gap_s"] = np.clip(bn["dip_gap_s"].to_numpy(), 0.25, 5.0)
    sc["outdoor_temp_c"] = np.clip(bn["outdoor_temp_c"].to_numpy(), temps.min(), temps.max())
    sc["swing_size_frac"] = bn["osc_amp"].to_numpy()
    sc["swing_freq_hz"] = np.clip(bn["osc_freq_hz"].to_numpy(), C.AI_SWING_FREQ_MIN_HZ, C.AI_SWING_FREQ_MAX_HZ)
    sc["workload"] = WORKLOAD_RANGE[0] + (WORKLOAD_RANGE[1] - WORKLOAD_RANGE[0]) * load01
    sc["battery_age_yr"] = np.clip(bn["equipment_age_years"].to_numpy(), 0.0, 14.0)
    sc["battery_temp_c"], sc["battery_soc0"] = hall, soc
    sc["compressor_restart_s"] = np.clip(bn["compressor_restart_s"].to_numpy(), 100.0, 600.0)
    sc["swing_phase"] = rng.uniform(0.0, 2 * np.pi, n)
    split = np.array([S.sample_cooling_split(rng) for _ in range(n)])
    sc["cooling_compressor_frac"], sc["cooling_fan_frac"] = split[:, 0], split[:, 1]

    roots = pd.DataFrame({
        "fault_type": bn["fault_type"].to_numpy(), "protection_failure": bn["protection_failure"].to_numpy(),
        "season": bn["season"].to_numpy(), "workload_type": bn["workload_type"].to_numpy(),
        "n_dips": bn["n_dips"].to_numpy(), "load_fraction": bn["load_fraction"].to_numpy(),
        "equipment_age_years": sc["battery_age_yr"].to_numpy(), "outdoor_temp_c": sc["outdoor_temp_c"].to_numpy(),
        "dip_depth_pu": depth, "battery_temp_c": hall, "battery_soc0": soc,
        "compressor_restart_s": sc["compressor_restart_s"].to_numpy(),
        "cooling_compressor_frac": split[:, 0],
    })
    return sc, roots


def to_scenarios(frame: pd.DataFrame, design: Scenario = GRID_FRIENDLY) -> list[Scenario]:
    """Rows of a sample_joint scenarios frame -> Scenario objects (what the simulator takes)."""
    kinds = {f.name: f.type for f in dataclasses.fields(Scenario)}
    cast = {"int": int, "bool": bool, "float": float, "int | None": int}
    out = []
    for row in frame.to_dict("records"):
        out.append(dataclasses.replace(design, **{k: cast.get(str(kinds[k]), float)(v) for k, v in row.items()}))
    return out
