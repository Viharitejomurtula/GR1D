"""Scenario definition and sampling.

A Scenario is the complete set of values that vary from run to run. It is the
simulator's input and, flattened, the surrogate's input vector. Fixed hardware and
regulatory values live in constants.py; anything derivable from a scenario field
(cooling share from temperature, pack resistance from age) is computed by the model,
not sampled here.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields

import numpy as np

from . import constants as C

SUPPLY_VOLTAGES = (208.0, 240.0, 277.0)


@dataclass(frozen=True)
class Scenario:
    # --- Grid event ---
    dip_depth_pu: float  # retained voltage, not the drop
    dip_duration_s: float
    dip_start_s: float
    second_dip: bool
    reclose_gap_s: float

    # --- Conditions ---
    outdoor_temp_c: float
    battery_temp_c: float
    battery_age_yr: float
    battery_soc0: float
    workload: float
    swing_size_frac: float
    swing_sign: float
    swing_time_s: float
    restart_surge_x: float
    restart_surge_s: float

    # --- Facility design ---
    supply_voltage_v: float
    shelves_per_rack: int
    bbu_modules_per_rack: int
    cooling_share_25c: float
    z_total_pct: float
    x_over_r: float
    motor_inertia_h_s: float

    # --- Settings ---
    transfer_threshold_pu: float
    handback_delay_s: float
    ramp_back_s: float
    relay_pickup_pu: float
    relay_delay_s: float
    cooling_trip_v_pu: float
    cooling_ride_through_s: float
    vfd_dc_uv_trip_pu: float

    # --- Stochastic hardware behaviour, sampled rather than drawn inside the model ---
    # ORv3 PSUs hold off restart by a deliberate random delay to avoid synchronised
    # inrush. Sampling it here keeps the input -> verdict mapping deterministic, so the
    # surrogate is not trained against label noise.
    psu_restart_delay_s: float

    def to_vector(self) -> np.ndarray:
        return np.array([float(getattr(self, f.name)) for f in fields(self)])

    def as_dict(self) -> dict:
        return asdict(self)


FIELD_ORDER = tuple(f.name for f in fields(Scenario))


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


def sample_dip_duration(rng: np.random.Generator) -> float:
    """Lognormal, median 0.1 s, sigma 1.0, truncated to 0.02-1.0 s."""
    for _ in range(100):
        d = float(rng.lognormal(mean=np.log(0.1), sigma=1.0))
        if 0.02 <= d <= 1.0:
            return d
    return 0.1


def sample(rng: np.random.Generator | None = None, *, dip_start_s: float = 1.0) -> Scenario:
    """Draw one scenario from the ranges in Parameter_Table.md."""
    rng = rng or np.random.default_rng()

    second_dip = bool(rng.random() < 0.20)  # >80% of faults are temporary -> reclose
    high_speed_reclose = rng.random() < 0.5

    return Scenario(
        dip_depth_pu=sample_dip_depth(rng),
        dip_duration_s=sample_dip_duration(rng),
        dip_start_s=dip_start_s,
        second_dip=second_dip,
        reclose_gap_s=float(
            rng.uniform(0.25, 0.6) if high_speed_reclose else rng.uniform(1.0, 5.0)
        ),
        outdoor_temp_c=float(rng.uniform(0.0, 42.0)),
        # Hall temperature cannot change meaningfully inside a 15 s window, so this is an
        # initial condition (a facility that is already hot), not something the run evolves.
        battery_temp_c=float(rng.uniform(20.0, 40.0)),
        battery_age_yr=float(rng.uniform(0.0, 10.0)),
        battery_soc0=float(rng.uniform(0.80, 1.00)),
        workload=float(rng.uniform(0.50, 1.00)),
        swing_size_frac=float(rng.uniform(0.0, 0.5)),
        swing_sign=float(rng.choice([-1.0, 1.0])),
        swing_time_s=float(rng.uniform(0.0, C.WINDOW_S)),
        restart_surge_x=float(rng.uniform(1.0, 1.3)),
        restart_surge_s=float(rng.uniform(0.1, 2.0)),
        supply_voltage_v=float(rng.choice(SUPPLY_VOLTAGES)),
        shelves_per_rack=int(rng.integers(1, C.MAX_SHELVES_PER_RACK + 1)),
        bbu_modules_per_rack=int(rng.integers(C.BBU_MODULES_PER_SHELF, 3 * C.BBU_MODULES_PER_SHELF + 1)),
        cooling_share_25c=float(rng.uniform(0.20, 0.35)),
        z_total_pct=float(rng.uniform(15.0, 23.0)),  # substation + distribution + PDU
        x_over_r=float(rng.uniform(5.0, 20.0)),
        motor_inertia_h_s=float(rng.uniform(0.2, 2.5)),
        transfer_threshold_pu=float(rng.uniform(0.75, 0.90)),
        handback_delay_s=float(rng.uniform(0.2, 10.0)),
        ramp_back_s=float(rng.uniform(0.1, 1.0)),
        relay_pickup_pu=float(rng.uniform(0.02, 0.90)),
        relay_delay_s=float(rng.uniform(0.0, 2.0)),
        cooling_trip_v_pu=float(rng.uniform(0.50, 0.85)),
        cooling_ride_through_s=float(rng.uniform(0.02, 5.0)),
        vfd_dc_uv_trip_pu=float(rng.uniform(0.65, 0.75)),
        psu_restart_delay_s=float(rng.uniform(0.0, 5.5)),
    )


def sample_many(n: int, seed: int | None = None) -> list[Scenario]:
    rng = np.random.default_rng(seed)
    return [sample(rng) for _ in range(n)]


# --- Presets -----------------------------------------------------------------
# Two reference designs. The legacy preset should reproduce the real-world events in
# Parameter_Table.md section 9; the grid-friendly one should ride through them.

_BASE = dict(
    dip_depth_pu=0.60,
    dip_duration_s=0.083,
    dip_start_s=1.0,
    second_dip=False,
    reclose_gap_s=0.4,
    outdoor_temp_c=38.0,
    battery_temp_c=25.0,
    battery_age_yr=3.0,
    battery_soc0=0.95,
    workload=0.85,
    swing_size_frac=0.2,
    swing_sign=1.0,
    swing_time_s=5.0,
    restart_surge_x=1.15,
    restart_surge_s=0.5,
    supply_voltage_v=277.0,
    shelves_per_rack=6,
    bbu_modules_per_rack=12,
    cooling_share_25c=0.30,
    z_total_pct=19.75,
    x_over_r=10.0,
    motor_inertia_h_s=0.8,
    ramp_back_s=0.3,
    cooling_trip_v_pu=0.70,
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
    psu_restart_delay_s=0.0,
)

LEGACY_UPS = Scenario(
    **_BASE,
    transfer_threshold_pu=0.90,
    handback_delay_s=3.0,
    relay_pickup_pu=0.85,
    relay_delay_s=0.0,
    cooling_ride_through_s=0.02,  # unprotected contactor
    psu_restart_delay_s=5.5,
)
