"""Adapter: factor network -> simulator roots.

What this file is
    Pure conversion functions that turn the output of ridethrough.drivers.sample.sample_drivers()
    and the S matrix / master.csv into the root inputs that public-model/sim needs. It imports
    neither network and changes neither. public-model/sim/integrated.py wires these functions
    into a copy of the simulator's Bayesian network.

Reads (read-only)
    data_bayesian-network/network/master.csv                  ranges and typical values
    data_bayesian-network/network/s_matrix/s_matrix_long.csv  slopes, curves, attenuations

Conversions
    load_index -> load_frac     to_load_fraction(load_index, typical, low=0.2, high=0.85). The cap is
                                the evidence range for PSU loading (servers 20-85% of nameplate), not
                                the 0.97 default of to_load_fraction.
    dip_depth_pct -> residual   residual_pu = 1 - dip_depth_pct / 100 (master.csv depth is the percent
                                of nominal voltage LOST; the simulator uses the voltage RETAINED).
    equipment_age_years -> cap  dclink_capacitance_factor = 1 + slope * age, slope from the S matrix
                                (-0.0132 /yr); cap_loss = 1 - factor. Replaces ep_stress_hours.
    temp_c -> battery R         storage_resistance_pu = 1 + age slope * age + room_atten * (-0.0889) *
                                (clip(T, -20, 25) - 25). Room attenuation 0 (conditioned) to 0.284.
    temp_c -> converter derate  interpolated S curve (25 C: 1.0, 40 C: 0.91, 50 C: 0.85), applied only
                                if the converter is outdoors.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from ridethrough.drivers.sample import to_load_fraction

NETWORK_DIR = Path(__file__).resolve().parents[1] / "data_bayesian-network" / "network"
LOAD_CAP = 0.85    # evidence range for PSU loading: servers 20-85% of nameplate
LOAD_FLOOR = 0.2


def _floats(text: str) -> list[float]:
    return [float(x) for x in text.split(";")]


@lru_cache(maxsize=None)
def _master() -> dict[str, dict]:
    with open(NETWORK_DIR / "master.csv", newline="") as f:
        return {r["node"]: r for r in csv.DictReader(f)}


@lru_cache(maxsize=None)
def _s_row(factor: str, driver: str) -> dict:
    with open(NETWORK_DIR / "s_matrix" / "s_matrix_long.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["factor"] == factor and r["driver"] == driver:
                return r
    raise KeyError(f"no S row for {factor} x {driver}")


@dataclass(frozen=True)
class Constants:
    """Numbers read from master.csv and the S matrix (not hard-coded)."""
    load_typical: float          # master.csv load_fraction typical
    load_floor: float
    load_cap: float
    age_low: float               # master.csv equipment_age_years low / high
    age_high: float
    dip_depth_pct: tuple         # master.csv (low, typical, high), % of nominal voltage lost
    dclink_age_slope: float      # per year (negative)
    res_age_slope: float         # pu per year
    res_temp_slope: float        # pu per degC, before room attenuation (negative)
    res_temp_range: tuple        # degC range the slope was fitted on
    res_pu_range: tuple          # master.csv storage_resistance_pu (low, high)
    room_atten_range: tuple      # (nominal, upper) attenuation of outdoor temp into the battery room
    derate_x: tuple              # converter current-limit curve, degC
    derate_y: tuple              # multiplier on the rated current limit


@lru_cache(maxsize=None)
def load_constants() -> Constants:
    m = _master()
    dip = m["dip_depth_pct"]
    cap = _s_row("dclink_capacitance_factor", "equipment_age_years")
    res_age = _s_row("storage_resistance_pu", "equipment_age_years")
    res_t = _s_row("storage_resistance_pu", "outdoor_temp_c")
    conv = _s_row("converter_current_limit_pu", "outdoor_temp_c")
    return Constants(
        load_typical=float(m["load_fraction"]["typical"]),
        load_floor=LOAD_FLOOR, load_cap=LOAD_CAP,
        age_low=float(m["equipment_age_years"]["low"]), age_high=float(m["equipment_age_years"]["high"]),
        dip_depth_pct=(float(dip["low"]), float(dip["typical"]), float(dip["high"])),
        dclink_age_slope=float(cap["slope_at_typical_nominal"]),
        res_age_slope=float(res_age["slope_at_typical_nominal"]),
        res_temp_slope=float(res_t["component_slope"]),
        res_temp_range=(float(res_t["linear_range_low"]), float(res_t["linear_range_high"])),
        res_pu_range=(float(m["storage_resistance_pu"]["low"]), float(m["storage_resistance_pu"]["high"])),
        room_atten_range=(float(res_t["attenuation_nominal"]), float(res_t["attenuation_upper"])),
        derate_x=tuple(_floats(conv["x_points"])), derate_y=tuple(_floats(conv["y_points"])),
    )


def site_load_fraction(load_index, c: Constants | None = None, typical: float | None = None) -> np.ndarray:
    """Grid load_index -> site load_fraction, capped to the evidence range 0.2-0.85."""
    c = c or load_constants()
    return to_load_fraction(load_index, typical=c.load_typical if typical is None else typical,
                            low=c.load_floor, high=c.load_cap)


def dip_depth_pct_to_residual_pu(dip_depth_pct) -> np.ndarray:
    """master.csv dip depth (% of nominal voltage lost) -> retained voltage in pu."""
    d = np.asarray(dip_depth_pct, dtype=float)
    if ((d < 0) | (d > 100)).any():
        raise ValueError("dip_depth_pct must be between 0 and 100")
    return 1.0 - d / 100.0


def sample_dip_depth_pct(n: int, rng: np.random.Generator, c: Constants | None = None) -> np.ndarray:
    """Triangular draw on master.csv (low, typical, high). Shape is an ASSUMPTION; master.csv gives only three numbers."""
    lo, mode, hi = (c or load_constants()).dip_depth_pct
    return rng.triangular(lo, mode, hi, n)


def draw_age(n: int, rng: np.random.Generator, c: Constants | None = None) -> np.ndarray:
    """Equipment age in years: uniform over master.csv low-high (the sd 4.33 years used by implied.py)."""
    c = c or load_constants()
    return rng.uniform(c.age_low, c.age_high, n)


def dclink_capacitance_factor(age_years, c: Constants | None = None) -> np.ndarray:
    """Fraction of initial DC-link capacitance at a given age (S matrix slope, linear)."""
    c = c or load_constants()
    return np.clip(1.0 + c.dclink_age_slope * np.asarray(age_years, dtype=float), 0.0, 1.0)


def cap_loss_from_age(age_years, c: Constants | None = None) -> np.ndarray:
    """Capacitor loss fraction (the simulator's cap_loss) from age."""
    return 1.0 - dclink_capacitance_factor(age_years, c)


def battery_resistance_pu(age_years, temp_c, room_atten, c: Constants | None = None) -> np.ndarray:
    """Storage resistance relative to new at room temperature.

    Age term: S-matrix slope per year. Temperature term: S-matrix slope per degC below 25 C times
    room_atten (0 = conditioned room holds the cells at setpoint; 0.284 = upper bound). Held flat
    above the fitted range (25 C) and below -20 C (no extrapolation). Clipped to master.csv range.
    """
    c = c or load_constants()
    lo, hi = c.res_temp_range
    t = np.clip(np.asarray(temp_c, dtype=float), lo, hi)
    r = 1.0 + c.res_age_slope * np.asarray(age_years, dtype=float) + np.asarray(room_atten) * c.res_temp_slope * (t - hi)
    return np.clip(r, *c.res_pu_range)


def converter_derate(temp_c, outdoor, c: Constants | None = None) -> np.ndarray:
    """Multiplier on the converter current limit. Flat 1.0 at <= 25 C and when the converter is indoors."""
    c = c or load_constants()
    mult = np.interp(np.asarray(temp_c, dtype=float), c.derate_x, c.derate_y)
    return np.where(np.asarray(outdoor, dtype=bool), mult, 1.0)


def drivers_to_sim_roots(drivers, age_years, room_atten, converter_outdoor,
                         c: Constants | None = None, load_typical: float | None = None) -> dict:
    """Convert sample_drivers() output (DataFrame) plus age and the two site unknowns to simulator roots.

    Inputs: drivers (temp_c, load_index columns); age_years, room_atten, converter_outdoor: scalars or
        arrays of length len(drivers).
    Output: dict of arrays: temp_c, load_frac (before the n_units maintenance scaling), age_years,
        cap_loss, bat_resistance_pu, converter_derate.
    """
    c = c or load_constants()
    t = drivers["temp_c"].to_numpy()
    return {
        "temp_c": t,
        "load_frac": site_load_fraction(drivers["load_index"].to_numpy(), c, load_typical),
        "age_years": np.broadcast_to(np.asarray(age_years, dtype=float), t.shape).copy(),
        "cap_loss": cap_loss_from_age(age_years, c),
        "bat_resistance_pu": battery_resistance_pu(age_years, t, room_atten, c),
        "converter_derate": converter_derate(t, converter_outdoor, c),
    }
