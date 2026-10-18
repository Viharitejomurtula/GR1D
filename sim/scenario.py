"""Scenario definition and sampling.

A Scenario is the complete set of values that vary from run to run. It is the
simulator's input and, flattened, the surrogate's input vector. Fixed hardware and
regulatory values live in constants.py; anything derivable from a scenario field
(cooling share from temperature, pack resistance from age) is computed by the model,
not sampled here.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field, fields
from functools import lru_cache

import numpy as np
import pandas as pd

from . import constants as C

SUPPLY_VOLTAGES = (208.0, 240.0, 277.0)


@dataclass(frozen=True)
class Scenario:
    # --- Grid event ---
    dip_depth_pu: float  # retained voltage, not the drop
    dip_duration_s: float
    dip_start_s: float
    # Post-fault shape from the ANDES library (scripts/andes_dips.py). A square dip has
    # neither: it snaps back instantly and never overshoots.
    recovery_tau_s: float
    overshoot_pu: float
    second_dip: bool
    reclose_gap_s: float

    # --- Conditions ---
    outdoor_temp_c: float
    battery_temp_c: float
    battery_age_yr: float
    battery_soc0: float
    workload: float
    swing_size_frac: float
    # The swing is a periodic 0.2-3 Hz oscillation (NERC/arXiv), not a one-time step, so it
    # is parameterised by frequency and phase rather than by an event time and direction.
    swing_freq_hz: float
    swing_phase: float
    restart_surge_x: float
    restart_surge_s: float

    # --- Facility design ---
    supply_voltage_v: float
    shelves_per_rack: int
    bbu_modules_per_rack: int
    cooling_share_25c: float
    # Only compressors stay off after a NERC stage-2 trip; fans and pumps reconnect. So
    # this split decides how much load is permanently lost, which makes it the single most
    # consequential unknown in the model (see Parameter_Table.md open item 3).
    cooling_compressor_frac: float
    cooling_fan_frac: float
    z_total_pct: float
    x_over_r: float

    # --- Settings ---
    transfer_threshold_pu: float
    handback_delay_s: float
    ramp_back_s: float
    relay_pickup_pu: float
    relay_delay_s: float
    cooling_ride_through_s: float
    vfd_dc_uv_trip_pu: float

    # --- Stochastic hardware behaviour, sampled rather than drawn inside the model ---
    # ORv3 PSUs hold off restart by a deliberate random delay to avoid synchronised
    # inrush. Sampling it here keeps the input -> verdict mapping deterministic, so the
    # surrogate is not trained against label noise.
    psu_restart_delay_s: float
    # Fleet spread of the 172 V trip threshold. Unsourced; sampled so sensitivity
    # analysis can judge whether it matters.
    psu_trip_spread_frac: float
    # 1/3, 2/3 or 1.0 of load on faulted phases (1, 2 or 3 phases; see
    # sample_faulted_phase_frac). ANDES gives balanced faults only, so this is the one place
    # single-phase behaviour enters the model.
    faulted_phase_frac: float
    # Fraction of load behind legacy latching protection. A retrofit question an operator
    # would actually ask: how much of the floor needs upgrading?
    legacy_load_frac: float

    # Installed transformer capacity vs facility load (G). Converts the summed own-base %Z to the facility base.
    chain_loading_frac: float = 0.75
    psu_uv_delay_s: float = 1.0 / 60.0   # lockout debounce (G, ~1 cycle: the value at which BOTH facility A (1.60 pu) and B (1.50 pu) peak currents are
                                         # reproduced -- inferred from the validation data, so NOT independent evidence; see validation/psu_delay_sweep.py)
    legacy_open_delay_s: float = 0.05   # breaker/contactor opening time after the relay operates (G: 2-5 cycles)
    ramp_on_grid_only: bool = field(default=True, metadata={"vector": False})   # False = old behaviour (servers' demand fell with the ramp gate)
    psu_cap_datasheet: bool = field(default=True, metadata={"vector": False})   # False reproduces the old per-unit scaling (ablation only)

    # --- Facility heterogeneity: the IT side is n_groups parallel RackGroups (model/RideThroughCore.mo). n_groups = 1 is the old single
    # lumped facility. Spreads are mean-preserving and assigned deterministically by stratified quantile (no random draw inside a run),
    # so a mixed facility is reproducible. All G (no public data on how real facilities are mixed). ---
    n_groups: int = 1
    grp_load_cv: float = 0.0       # spread of group loading (total workload preserved)
    grp_holdup_cv: float = 0.0     # spread of hold-up capacitor health
    grp_bbu_cv: float = 0.0        # spread of installed BBU power/energy
    grp_trip_cv: float = 0.0       # spread of PSU lockout threshold between groups

    # --- Cooling drives (see VfdClass in the model). Defaults keep the factory ATV320 behaviour.
    cooling_vfd_frac: float = 0.5
    vfd_kinetic: bool = False       # ATV320 'UnderV. prevention = DC Maintain'; factory default off
    drive_restart_s: float = 1.0    # 1 s = auto-restart ladder's first retry; use ~600 for manual reset (Atr factory default is off)
    compressor_restart_s: float = 180.0

    # --- Sag-counting transfer (NERC: sites moved to backup on "N sags in T seconds" and stayed
    # off until manual reset; count_n = 0 disables it, so existing scenarios are unchanged) ---
    count_n: int = 0
    count_threshold_pu: float = 0.90
    count_min_dur_s: float = 0.0
    count_window_s: float = 60.0

    # --- Reclose sequence beyond the first dip (and beyond the simple `second_dip`) ---
    # Each entry is (gap_after_previous_clear_s, duration_s, depth_pu). Real events had 4-6
    # faults over up to 82 s (NERC 2024, PJM 2026), which `second_dip` cannot express. Kept out
    # of the surrogate's input vector: a variable-length sequence is not a fixed-width feature
    # (summarise it as n_dips / total span if the surrogate needs it).
    extra_dips: tuple = field(default=(), metadata={"vector": False})
    # Explicit simulation window; 0 = automatic (last clear + settle). Needed to see cooling restart
    # (compressor anti-short-cycle is 100 s or more, far past the standard window).
    horizon_s: float = field(default=0.0, metadata={"vector": False})

    def dip_sequence(self) -> list[tuple[float, float, float]]:
        """[(start_s, duration_s, retained_pu), ...] in time order, non-overlapping."""
        seq = [(self.dip_start_s, self.dip_duration_s, self.dip_depth_pu)]
        if self.second_dip:
            seq.append((seq[-1][0] + seq[-1][1] + self.reclose_gap_s, self.dip_duration_s, self.dip_depth_pu))
        for gap, dur, depth in self.extra_dips:
            seq.append((seq[-1][0] + seq[-1][1] + gap, dur, depth))
        if len(seq) > C.MAX_DIPS:
            raise ValueError(f"{len(seq)} dips exceeds the model's MAX_DIPS={C.MAX_DIPS}")
        return seq

    def group_arrays(self) -> dict[str, list[float]]:
        """Per-group parameter arrays (length MAX_GROUPS; unused slots have zero weight)."""
        n = int(self.n_groups)
        if not 1 <= n <= C.MAX_GROUPS:
            raise ValueError(f"n_groups must be 1..{C.MAX_GROUPS}")
        u = [2.0 * (k + 0.5) / n - 1.0 for k in range(n)]           # stratified, symmetric about 0, in (-1, 1)
        order = {"load": list(range(n)), **_ORDERINGS[n]}              # fixed permutations so the spreads are not perfectly correlated
        def spread(key, cv): return [1.0 + cv * u[order[key][k]] for k in range(n)]
        load = spread("load", self.grp_load_cv)
        mean_load = sum(load) / n
        load = [max(0.2, x / mean_load) for x in load]                 # total workload preserved
        pad = lambda xs, fill: list(xs) + [fill] * (C.MAX_GROUPS - n)
        return {"grp_w": pad([1.0 / n] * n, 0.0), "grp_workload_scale": pad(load, 1.0),
                "grp_holdup_scale": pad([max(0.3, x) for x in spread("holdup", self.grp_holdup_cv)], 1.0),
                "grp_bbu_scale": pad([max(0.3, x) for x in spread("bbu", self.grp_bbu_cv)], 1.0),
                "grp_trip_offset": pad([self.grp_trip_cv * u[order["trip"][k]] * 0.1 for k in range(n)], 0.0)}

    def legacy_fractions(self) -> list[float]:
        """Per-group legacy share (same cumulative-by-load rule as the model; used by tests and reports only)."""
        a = self.group_arrays(); n = int(self.n_groups); lw = [a["grp_w"][k] * a["grp_workload_scale"][k] for k in range(n)]
        out, done = [], 0.0
        for w in lw:
            out.append(min(1.0, max(0.0, (self.legacy_load_frac - done) / w))); done += w
        return out

    def window_s(self) -> float:
        """Simulation window: default settle time after the last dip clears, never shorter than the base window."""
        start, dur, _ = self.dip_sequence()[-1]
        auto = max(C.WINDOW_S, start + dur + C.POST_EVENT_SETTLE_S)
        return self.horizon_s if self.horizon_s > 0 else auto

    def to_vector(self) -> np.ndarray:
        return np.array([float(getattr(self, f.name)) for f in fields(self) if f.metadata.get("vector", True)])

    def as_dict(self) -> dict:
        return asdict(self)


_ORDERINGS = {1: dict(holdup=[0], bbu=[0], trip=[0]),
              2: dict(holdup=[1, 0], bbu=[1, 0], trip=[1, 0]),
              3: dict(holdup=[2, 0, 1], bbu=[1, 2, 0], trip=[2, 1, 0]),
              4: dict(holdup=[2, 0, 3, 1], bbu=[1, 3, 0, 2], trip=[3, 2, 1, 0]),
              5: dict(holdup=[2, 4, 1, 3, 0], bbu=[3, 0, 4, 1, 2], trip=[4, 3, 2, 1, 0]),
              6: dict(holdup=[3, 0, 5, 2, 4, 1], bbu=[4, 1, 5, 0, 3, 2], trip=[5, 4, 3, 2, 1, 0])}
FIELD_ORDER = tuple(f.name for f in fields(Scenario) if f.metadata.get("vector", True))


def sample_dip_depth(rng: np.random.Generator) -> float:
    """Retained voltage, drawn from the Eaton/EPRI sag depth distribution.

    69% of sags retain 0.70-0.90 pu, 27% retain 0.10-0.70, 4% retain below 0.10.
    """
    u = rng.random()
    if u < 0.69:
        return float(rng.uniform(0.70, 0.90))
    if u < 0.96:
        return float(rng.uniform(0.10, 0.70))
    return float(rng.uniform(0.00, 0.10))


# Fitted across the ANDES dip library: deeper faults overshoot harder on recovery, and
# the climb-back time constant is nearly invariant. Residual scatter is kept so sampling
# is not confined to the handful of discrete library entries.
OVERSHOOT_PER_DEPTH = 0.122
OVERSHOOT_RESIDUAL = 0.018
RECOVERY_TAU_MEAN = 0.0658
RECOVERY_TAU_STD = 0.0017


def sample_shape(rng: np.random.Generator, retained_pu: float) -> tuple[float, float]:
    """Recovery time constant and overshoot, conditioned on dip depth."""
    tau = float(np.clip(rng.normal(RECOVERY_TAU_MEAN, RECOVERY_TAU_STD), 0.02, 0.2))
    mean_os = OVERSHOOT_PER_DEPTH * (1.0 - retained_pu)
    overshoot = float(max(0.0, rng.normal(mean_os, OVERSHOOT_RESIDUAL)))
    return tau, overshoot


def sample_dip_duration(rng: np.random.Generator, p_delayed: float | None = None) -> float:
    """Fault clearing time in seconds, from the ERCOT OWG Large Load Events deck (Nov 2024).

    With probability p_delayed the clearing is delayed, uniform 10-19 cycles; otherwise it
    is normal, uniform 3-4 cycles. Cycles are converted at C.NOMINAL_FREQ_HZ (60 Hz), so the
    ranges are 0.050-0.0667 s and 0.1667-0.3167 s. p_delayed defaults to
    C.DELAYED_CLEARING_P (2/18), read at call time so it can be swept. Sources and caveats
    are in constants.py.
    """
    p = C.DELAYED_CLEARING_P if p_delayed is None else p_delayed
    lo, hi = C.DELAYED_CLEARING_CYCLES if rng.random() < p else C.NORMAL_CLEARING_CYCLES
    return float(rng.uniform(lo, hi)) / C.NOMINAL_FREQ_HZ


FAULT_MIXES = ("general", "loss_events")


def faulted_phase_probs(fault_mix: str = "general") -> np.ndarray:
    """Probabilities of 1, 2 and 3 faulted phases (faulted_phase_frac 1/3, 2/3, 1.0).

    "general": ERCOT SPWG (2017) p. 8 range midpoints, with 1 phase = L-G,
    2 phases = L-L-G + L-L, 3 phases = 3LG, normalized (0.703, 0.260, 0.036).
    "loss_events": the 13/1/5 counts of the 19 ERCOT OWG events with a known fault type.
    Outcome-selected, so for worst-case runs only. Sources are in constants.py.
    """
    if fault_mix == "general":
        lg, llg, ll, three = C.FAULT_MIX_SPWG_MIDPOINTS_PCT
        w = np.array([lg, llg + ll, three])
    elif fault_mix == "loss_events":
        w = np.array(C.FAULT_MIX_LOSS_EVENT_COUNTS, dtype=float)
    else:
        raise ValueError(f"fault_mix must be one of {FAULT_MIXES}, got {fault_mix!r}")
    return w / w.sum()


def sample_faulted_phase_frac(rng: np.random.Generator, fault_mix: str = "general") -> float:
    """Share of load on faulted phases: 1/3, 2/3 or 1.0, weighted by faulted_phase_probs."""
    return float(rng.choice([1 / 3, 2 / 3, 1.0], p=faulted_phase_probs(fault_mix)))


def sample_cooling_split(rng: np.random.Generator) -> tuple[float, float]:
    """(compressor, fan) shares of cooling power; pump is the remainder 1 - compressor - fan.

    Compressor and pump are drawn uniform within C.COOLING_COMPRESSOR_FRAC_RANGE and
    C.COOLING_PUMP_FRAC_RANGE; fan = 1 - compressor - pump, and the pair is redrawn until fan
    lies in C.COOLING_FAN_FRAC_RANGE. So the three shares always sum to 1 and each stays in
    its sourced range (LBNL, IBM 2010, arXiv 1804.00703; see constants.py).
    The result is uniform over the feasible (compressor, pump) region, so the marginals
    are NOT uniform: the compressor share is thinner near 0.46, and compressor and fan are
    strongly anti-correlated. Uniform over the feasible region is an assumption.
    """
    fan_lo, fan_hi = C.COOLING_FAN_FRAC_RANGE
    while True:
        compressor = float(rng.uniform(*C.COOLING_COMPRESSOR_FRAC_RANGE))
        pump = float(rng.uniform(*C.COOLING_PUMP_FRAC_RANGE))
        fan = 1.0 - compressor - pump
        if fan_lo <= fan <= fan_hi:
            return compressor, fan


HALL_STRESS = (None, "A1", "A2")


def sample_battery_temp(rng: np.random.Generator, hall_stress: str | None = None) -> float:
    """Battery hall air temperature, degC.

    Default: uniform over the ASHRAE recommended range C.HALL_TEMP_RECOMMENDED_C (18-27).
    hall_stress "A1" or "A2" returns the allowable upper limit for that class (32.0 or
    35.0). The uniform draw is made either way, so a stressed batch uses the same random
    stream as an unstressed one with the same seed and differs only in battery_temp_c.
    No source gives the spread of hall temperatures across sites, so the uniform shape is
    an assumption.
    """
    if hall_stress is not None and hall_stress not in C.HALL_TEMP_ALLOWABLE_MAX_C:
        raise ValueError(f"hall_stress must be one of {HALL_STRESS}, got {hall_stress!r}")
    temp = float(rng.uniform(*C.HALL_TEMP_RECOMMENDED_C))
    return temp if hall_stress is None else C.HALL_TEMP_ALLOWABLE_MAX_C[hall_stress]


@lru_cache(maxsize=1)
def outdoor_temps() -> np.ndarray:
    """Empirical DFW hourly outdoor temperatures (degC), loaded once and cached.

    Column temp_c of C.OUTDOOR_TEMP_CSV (NOAA LCD, DFW 72259003927), rows with
    flag != "missing" whose local-standard-time year (hour_lst) is within
    C.OUTDOOR_TEMP_YEARS (complete years 2021-2025). The file is read, never written.
    Interim until ridethrough.drivers.sample.sample_drivers() supplies correlated
    temperature and load.
    """
    d = pd.read_csv(C.OUTDOOR_TEMP_CSV, usecols=["hour_lst", "temp_c", "flag"])
    year = d["hour_lst"].str[:4].astype(int)
    first, last = C.OUTDOOR_TEMP_YEARS
    keep = (d["flag"] != "missing") & (year >= first) & (year <= last)
    return d.loc[keep, "temp_c"].to_numpy(dtype=float)


def sample(
    rng: np.random.Generator | None = None,
    *,
    dip_start_s: float = 1.0,
    fault_mix: str = "general",
    bbu_module_out: bool = False,
    hall_stress: str | None = None,
) -> Scenario:
    """Draw one scenario from the ranges in Parameter_Table.md.

    fault_mix: "general" (default) or "loss_events" (worst case); see faulted_phase_probs.
    bbu_module_out: named design scenario with one BBU module out on every shelf
        (5 x shelves instead of 6 x shelves). Not a random draw: no source gives how often a
        module is out.
    hall_stress: None (default, ASHRAE recommended range), "A1" or "A2"; see
        sample_battery_temp.
    """
    rng = rng or np.random.default_rng()

    second_dip = bool(rng.random() < 0.20)  # >80% of faults are temporary -> reclose
    high_speed_reclose = rng.random() < 0.5
    depth = sample_dip_depth(rng)
    tau, overshoot = sample_shape(rng, depth)
    shelves = int(rng.integers(1, C.MAX_SHELVES_PER_RACK + 1))
    # Analog Devices Part 4: six modules per shelf, 5+1 redundant (see constants.py).
    modules_per_shelf = C.BBU_MODULES_PER_SHELF - (C.BBU_REDUNDANT_MODULES if bbu_module_out else 0)
    compressor_frac, fan_frac = sample_cooling_split(rng)

    return Scenario(
        dip_depth_pu=depth,
        dip_duration_s=sample_dip_duration(rng),
        dip_start_s=dip_start_s,
        recovery_tau_s=tau,
        overshoot_pu=overshoot,
        second_dip=second_dip,
        reclose_gap_s=float(
            rng.uniform(0.25, 0.6) if high_speed_reclose else rng.uniform(1.0, 5.0)
        ),
        outdoor_temp_c=float(rng.choice(outdoor_temps())),
        # Hall temperature cannot change meaningfully inside a 15 s window, so this is an
        # initial condition (a facility that is already hot), not something the run evolves.
        battery_temp_c=sample_battery_temp(rng, hall_stress),
        battery_age_yr=float(rng.uniform(0.0, 10.0)),
        battery_soc0=float(rng.uniform(0.80, 1.00)),
        workload=float(rng.uniform(0.50, 1.00)),
        swing_size_frac=float(rng.uniform(0.0, 0.5)),
        swing_freq_hz=float(rng.uniform(C.AI_SWING_FREQ_MIN_HZ, C.AI_SWING_FREQ_MAX_HZ)),
        swing_phase=float(rng.uniform(0.0, 2 * np.pi)),
        restart_surge_x=float(rng.uniform(1.0, 1.3)),
        restart_surge_s=float(rng.uniform(0.1, 2.0)),
        supply_voltage_v=float(rng.choice(SUPPLY_VOLTAGES)),
        shelves_per_rack=shelves,
        bbu_modules_per_rack=modules_per_shelf * shelves,
        cooling_share_25c=float(rng.uniform(0.20, 0.35)),
        # Compressor/fan/pump split: main's sourced draw (compressor_frac, fan_frac).
        cooling_compressor_frac=compressor_frac,
        cooling_fan_frac=fan_frac,
        z_total_pct=float(rng.uniform(15.0, 23.0)),  # substation + distribution + PDU, summed on each unit's own base
        chain_loading_frac=float(rng.uniform(0.5, 1.0)),
        n_groups=int(rng.choice([1, 3, 6])),
        grp_load_cv=float(rng.uniform(0.0, 0.4)), grp_holdup_cv=float(rng.uniform(0.0, 0.4)),
        grp_bbu_cv=float(rng.uniform(0.0, 0.4)), grp_trip_cv=float(rng.uniform(0.0, 0.4)),
        legacy_open_delay_s=float(rng.uniform(2.0, 5.0) / 60.0),
        psu_uv_delay_s=float(np.exp(rng.uniform(np.log(0.001), np.log(0.025)))),   # G: ~1 ms to 1.5 cycles
        x_over_r=float(rng.uniform(5.0, 20.0)),
        transfer_threshold_pu=float(rng.uniform(0.75, 0.90)),
        # Fixed at the BBU's 200 ms busbar confirmation (Analog Devices Part 1).
        handback_delay_s=C.BBU_HANDBACK_CONFIRM_S,
        ramp_back_s=float(rng.uniform(0.1, 1.0)),
        relay_pickup_pu=float(rng.uniform(0.02, 0.90)),
        relay_delay_s=float(rng.uniform(0.0, 2.0)),
        cooling_ride_through_s=float(rng.uniform(0.02, 5.0)),
        vfd_dc_uv_trip_pu=float(rng.uniform(0.65, 0.75)),
        # Cooling drive population: all four are unsourced (G) except the factory defaults noted in the model.
        cooling_vfd_frac=float(rng.uniform(0.2, 0.9)),
        vfd_kinetic=bool(rng.random() < 0.2),
        drive_restart_s=float(rng.uniform(1.0, 10.0) if rng.random() < 0.3 else rng.uniform(120.0, 1800.0)),
        compressor_restart_s=float(rng.uniform(100.0, 600.0)),
        psu_restart_delay_s=float(rng.uniform(0.0, 5.5)),
        psu_trip_spread_frac=float(rng.uniform(0.01, 0.08)),
        faulted_phase_frac=sample_faulted_phase_frac(rng, fault_mix),
        legacy_load_frac=float(rng.uniform(0.0, 1.0)),
    )


def sample_many(n: int, seed: int | None = None, **kwargs) -> list[Scenario]:
    """n scenarios from one seeded generator; kwargs (fault_mix, bbu_module_out, hall_stress,
    dip_start_s) are passed to sample()."""
    rng = np.random.default_rng(seed)
    return [sample(rng, **kwargs) for _ in range(n)]


# --- Presets -----------------------------------------------------------------
# Two reference designs. The legacy preset should reproduce the real-world events in
# Parameter_Table.md section 9; the grid-friendly one should ride through them.

_BASE = dict(
    dip_depth_pu=0.60,
    dip_duration_s=0.083,
    dip_start_s=1.0,
    recovery_tau_s=0.0658,
    overshoot_pu=0.049,
    second_dip=False,
    reclose_gap_s=0.4,
    outdoor_temp_c=38.0,
    battery_temp_c=25.0,
    battery_age_yr=3.0,
    battery_soc0=0.95,
    workload=0.85,
    swing_size_frac=0.2,
    swing_freq_hz=1.0,
    swing_phase=0.0,
    restart_surge_x=1.15,
    restart_surge_s=0.5,
    supply_voltage_v=277.0,
    shelves_per_rack=6,
    bbu_modules_per_rack=36,   # 6 shelves x 6 modules: 108 kW per rack vs ~92 kW of IT at 85% load. The old 12 could carry only 40 MW of a 102 MW load; that was
                               # invisible while the servers' demand fell to zero the moment the PSUs tripped (see ramp_on_grid_only)
    cooling_share_25c=0.30,
    cooling_compressor_frac=0.4,
    cooling_fan_frac=0.35,
    z_total_pct=19.75,
    x_over_r=10.0,
    ramp_back_s=0.3,
    vfd_dc_uv_trip_pu=0.70,
)

GRID_FRIENDLY = Scenario(
    **_BASE,
    transfer_threshold_pu=0.85,
    handback_delay_s=0.2,
    # NOGRR 282 2.14(4) requires protection be set to equipment tolerance, not to the
    # envelope edge, so a compliant design picks up below the deepest envelope tier.
    relay_pickup_pu=0.15,
    relay_delay_s=0.5,
    cooling_ride_through_s=3.0,
    vfd_kinetic=True,          # drives configured for DC Maintain ride-through
    drive_restart_s=1.0,       # auto-restart enabled
    psu_restart_delay_s=0.0,
    psu_trip_spread_frac=0.04,
    faulted_phase_frac=1.0,
    legacy_load_frac=0.0,
)

LEGACY_UPS = Scenario(
    **_BASE,
    transfer_threshold_pu=0.90,
    handback_delay_s=3.0,
    relay_pickup_pu=0.85,
    relay_delay_s=0.0,
    cooling_ride_through_s=0.02,  # unprotected contactor
    vfd_kinetic=False,         # factory default
    drive_restart_s=600.0,     # auto-restart off (factory default): waits for an operator
    psu_restart_delay_s=5.5,
    psu_trip_spread_frac=0.04,
    faulted_phase_frac=1.0,
    legacy_load_frac=1.0,
)
