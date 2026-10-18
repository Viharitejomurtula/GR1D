"""Fixed hardware and regulatory constants.

Nothing here is sampled per scenario. Values that vary run-to-run live in scenario.py.
Sources are tracked in Parameter_Table.md.
"""

# --- Simulation ---------------------------------------------------------------
WINDOW_S = 15.0
DT_S = 1e-4
NOMINAL_FREQ_HZ = 60.0
MAX_DIPS = 8             # array size in model/RideThroughCore.mo; NERC/PJM events had 4-6 faults
POST_EVENT_SETTLE_S = 14.0   # window = last clear + this, so late PSU restarts (up to 11.5 s) are still seen
OUTPUT_STEP_S = 2e-3     # result sampling; resolves 20 ms trip delays even in 100 s windows

# Window is 15 s rather than the originally scoped 6-8 s because PSU turn-on after a
# BBU discharge can take up to 11.5 s; a shorter window truncates the restart outcome.

# --- ORv3 power supply --------------------------------------------------------
PSU_RATED_W = 3000.0
PSU_OUTPUT_V = 50.75
PSU_OUTPUT_A = 60.0
PSUS_PER_SHELF = 6
SHELF_RATED_W = 18000.0
MAX_SHELVES_PER_RACK = 10

PSU_UV_SHUTOFF_V = 172.0
PSU_RESTART_V = 178.0
PSU_INPUT_MIN_V = 180.0
PSU_INPUT_MAX_V = 305.0

PSU_HOLDUP_ENERGY_J = 60.0
PSU_HOLDUP_DROOP_FRAC = 0.5  # output droops 3 V once half the hold-up energy is gone
PSU_PULSE_RESERVE_J = 24.0

PSU_OVERLOAD_W = 3600.0
PSU_OVERLOAD_TRIP_S = 0.100
PSU_BBU_HANDOFF_S = 0.006
PSU_SYNC_RETRY_S = 5.0

# Turn-on timing. The random component is NOT drawn here; it is a scenario input so the
# surrogate sees a deterministic mapping (see scenario.psu_restart_delay_s).
PSU_TON_NOBBU_MIN_S, PSU_TON_NOBBU_MAX_S = 1.0, 5.0
PSU_TON_BBU_MIN_S, PSU_TON_BBU_MAX_S = 1.0, 8.5
PSU_TON_SYNC_FAIL_MAX_S = 11.5

_EFFICIENCY = {  # (min_input_v, min_load_frac) -> efficiency
    (230.0, 0.30): 0.965,
    (208.0, 0.30): 0.955,
    (200.0, 0.10): 0.940,
}
PSU_PEAK_EFFICIENCY = 0.975


def psu_efficiency(input_v: float, load_frac: float) -> float:
    """Efficiency from the ORv3 spec's load/voltage bands."""
    for (min_v, min_load), eff in _EFFICIENCY.items():
        if input_v >= min_v and load_frac >= min_load:
            return eff
    return 0.940


# --- 48 V busbar and IT gear --------------------------------------------------
BUSBAR_NOMINAL_V = 48.0
IT_GEAR_MIN_V = 46.0
IT_GEAR_MAX_V = 52.0

# Servers are considered to have lost power below IT_GEAR_MIN_V. This gates the restart
# surge term in the AI load model.
SERVER_POWER_LOSS_V = IT_GEAR_MIN_V

# --- Battery backup unit ------------------------------------------------------
BBU_MODULE_W = 3000.0
BBU_MODULE_ENERGY_WH = 200.0  # 3 kW x 4 min; see Parameter_Table.md on the 333 Wh discrepancy
BBU_MODULES_PER_SHELF = 6
BBU_REDUNDANT_MODULES = 1  # 5+1

BBU_TAKEOVER_V = 48.5
BBU_TAKEOVER_DETECT_S = 0.002
BBU_TAKEOVER_ACT_S = 0.002
BBU_BUSBAR_FLOOR_V = 46.0
BBU_HANDBACK_CONFIRM_S = 0.200

CELLS_SERIES = 11
CELLS_PARALLEL = 6
CELL_CAPACITY_AH = 1.5
CELL_R0_OHM = 0.030
PACK_R0_OHM = CELL_R0_OHM * CELLS_SERIES / CELLS_PARALLEL
PACK_V_MIN = 30.0
PACK_V_MAX = 44.0

# R1/C1 have no citable typical value and need HPPC fitting (PyBaMM + NASA PCoE).
# These are placeholders so the model runs; do not report results that depend on them.
CELL_R1_OHM_PLACEHOLDER = 0.015
CELL_C1_F_PLACEHOLDER = 2000.0

# Ageing and temperature, Sandia SAND2008-5583 Table 2. Resistance grows 1.1-2.3x as fast
# as capacity fades. LFP cells, used as a proxy for the NMC 18650s in an ORv3 BBU.
BAT_R_GROWTH_PER_YR = 0.04
BAT_FADE_PER_YR = 0.025  # G: the source row for this was garbled, see Parameter_Table.md
BAT_R0_UNIT_SPREAD = 0.06
BAT_CAPACITY_UNIT_SPREAD = 0.015

_CAPACITY_VS_TEMP = ((-40.0, 0.03), (-30.0, 0.48), (-20.0, 0.65), (0.0, 0.74), (25.0, 1.00), (35.0, 1.06))


def capacity_derate(temp_c: float) -> float:
    """Capacity relative to 25 C, linearly interpolated from the Sandia table."""
    pts = _CAPACITY_VS_TEMP
    if temp_c <= pts[0][0]:
        return pts[0][1]
    if temp_c >= pts[-1][0]:
        return pts[-1][1]
    for (t0, f0), (t1, f1) in zip(pts, pts[1:]):
        if t0 <= temp_c <= t1:
            return f0 + (f1 - f0) * (temp_c - t0) / (t1 - t0)
    return 1.0

# --- Cooling ------------------------------------------------------------------
AFFINITY_EXPONENT = 2.0  # centrifugal fan/pump load torque ~ omega^2
MOTOR_LOCKED_ROTOR_X = 6.0

# Inertia constants per motor class, NERC Dynamic Load Modeling Table 5.1. These are
# 2-8x lower than the 0.8 s placeholder previously used, so kinetic-buffering
# ride-through is correspondingly shorter.
MOTOR_H_COMPRESSOR_S = 0.10
MOTOR_H_FAN_S = 0.50
MOTOR_H_PUMP_S = 0.15

# Staged undervoltage trip, NERC Table 5.1. Trips are partial, not all-or-nothing, and
# fans/pumps reconnect while compressors stay off for the rest of the run.
MOTOR_TRIP_STAGE1_V_PU = 0.70
MOTOR_TRIP_STAGE1_DELAY_S = 0.05
MOTOR_TRIP_STAGE1_FRACTION = 0.30

MOTOR_TRIP_STAGE2_V_PU = 0.60
MOTOR_TRIP_STAGE2_DELAY_S = 0.02
MOTOR_TRIP_STAGE2_FRACTION_COMPRESSOR = 0.70
MOTOR_TRIP_STAGE2_FRACTION_FAN = 0.50
MOTOR_TRIP_STAGE2_FRACTION_PUMP = 0.50

MOTOR_RECONNECT_V_PU = 0.50
MOTOR_RECONNECT_DELAY_S = 0.25
MOTOR_RECONNECTS = {"compressor": False, "fan": True, "pump": True}

# Trane RTAC rapid restart: stop-to-start 120 s (adjustable 30-120 s). Exceeds the window,
# so a chiller that fully stops does not return within a run.
COOLING_RESTART_S = 120.0

# --- AI / server load ---------------------------------------------------------
# Measured ramp rate for a synchronised AI block, NERC large-loads whitepaper Figs 2.2-2.3
# (1.9 pu/s sustained ~250 ms for a ~0.475 pu change). The swing is periodic at 0.2-3 Hz,
# not a one-time step, so it is modelled as a slew-limited square wave.
AI_SWING_SLEW_PU_S = 1.9
AI_SWING_FREQ_MIN_HZ = 0.2
AI_SWING_FREQ_MAX_HZ = 3.0

# --- Protection ---------------------------------------------------------------
# Legacy cumulative-sag scheme observed in a real event: three disturbances inside one
# minute transfers to backup and stays off until manual reset. NOGRR 282 2.14(6) bans
# exactly this, so it is the non-compliant reference design.
LEGACY_COUNT_N = 3
LEGACY_COUNT_WINDOW_S = 60.0

BREAKER_INTERRUPT_S = 0.042
STS_TRANSFER_S = 0.004
RELAY_PICKUP_MAX_S = 1.5 / NOMINAL_FREQ_HZ
RELAY_V_ACCURACY_FRAC = 0.01
RELAY_V_ACCURACY_OFFSET_V = 0.5
RELAY_T_ACCURACY_FRAC = 0.005
RELAY_T_ACCURACY_OFFSET_S = 0.25 / NOMINAL_FREQ_HZ

# --- ERCOT NOGRR 282 (effective 2026-08-01) -----------------------------------
# Voltage ride-through envelope, Section 2.14(2) Table A.
# (v_low_pu, v_high_pu, min_ride_through_s); None means the load may trip.
VRT_ENVELOPE = (
    (1.20, float("inf"), None),
    (1.10, 1.20, 2.0),
    (0.90, 1.10, float("inf")),  # continuous
    (0.80, 0.90, 2.0),
    (0.50, 0.80, 0.5),
    (0.20, 0.50, 0.25),
    (0.00, 0.20, 0.15),
)

CONTINUOUS_V_LOW_PU = 0.90
CONTINUOUS_V_HIGH_PU = 1.10

RECOVERY_TRIGGER_V_PU = 0.90  # recovery clock starts when V climbs back above this
RECOVERY_FRACTION = 0.90  # of pre-disturbance active power
RECOVERY_DEADLINE_S = 2.0  # the only recovery deadline in the rule

# Power floor, Section 2.14(2)(c): reduction must be proportional to the voltage drop
# between these bounds. Below FLOOR_V_LOW_PU consumption may be reduced as needed.
FLOOR_V_LOW_PU = 0.50
FLOOR_V_HIGH_PU = 0.80

CURRENT_CAP_PU = 1.25  # Section 2.14(2)(d)
CURRENT_CAP_DURATION_S = 0.5  # March 2026 revision

FREQ_CONTINUOUS_LOW_HZ = 58.8
FREQ_CONTINUOUS_HIGH_HZ = 61.2
FREQ_EXTENDED_S = 299.0
FREQ_TRIP_LOW_HZ = 57.0
FREQ_TRIP_HIGH_HZ = 63.0  # raised from 61.8 in the March 2026 revision

LEL_THRESHOLD_MW = 75.0


def power_floor_pu(v_pu: float) -> float:
    """Minimum allowed consumption as a fraction of pre-disturbance power.

    The floor tracks voltage, so compliance must be checked every timestep rather than
    against a single minimum-power scalar.
    """
    if v_pu >= CONTINUOUS_V_LOW_PU:
        return 1.0
    # Proportional across 0.90-0.50. The pre-2028 regime makes the 0.80-0.50 band
    # conditional on "if capable"; we grade against the post-2028 rule, which does not.
    if v_pu >= FLOOR_V_LOW_PU:
        return v_pu
    return 0.0


def required_ride_through_s(v_pu: float) -> float | None:
    """Minimum time the load must stay connected at this voltage. None = may trip."""
    for v_low, v_high, hold_s in VRT_ENVELOPE:
        if v_low <= v_pu < v_high:
            return hold_s
    return None
