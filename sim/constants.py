"""Fixed hardware and regulatory constants.

Nothing here is sampled per scenario. Values that vary run-to-run live in scenario.py.
Sources are tracked in Parameter_Table.md.
"""

from pathlib import Path

# --- Simulation ---------------------------------------------------------------
WINDOW_S = 15.0
DT_S = 1e-4
NOMINAL_FREQ_HZ = 60.0

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
# Analog Devices, Smart Battery Backup Part 4: "The BBU shelf will contain six BBU modules
# with 5+1 redundancy."
# https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part4.html
BBU_MODULES_PER_SHELF = 6
BBU_REDUNDANT_MODULES = 1  # 5+1

BBU_TAKEOVER_V = 48.5
BBU_TAKEOVER_DETECT_S = 0.002
BBU_TAKEOVER_ACT_S = 0.002
BBU_BUSBAR_FLOOR_V = 46.0
# Analog Devices, Smart Battery Backup Part 1: the module exits discharge once the busbar is
# "more than 48.5 V for more than 200 ms". Also the sampled handback_delay_s (scenario.py).
# https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html
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


# --- Sourced scenario distributions -------------------------------------------
# Inputs to scenario.sample(). Each value is quoted from the source named beside it.

# Fault clearing time in cycles at NOMINAL_FREQ_HZ. ERCOT, "Large Load Events", OWG,
# Nov 21 2024:
# https://www.ercot.com/files/docs/2024/11/19/ERCOT%20Large%20Load%20Events_OWG_21Nov2024.pdf
#   normal:  slide 5 "normal 3-cycle clearing", "normal 4-cycle clearing"; slide 9 "3-4 cycle
#            clearing times"
#   delayed: slide 4 "delayed ~10 cycle clearing due to breaker misoperation"; slide 5
#            "delayed 19-cycle clearing due to [breaker] failure"
NORMAL_CLEARING_CYCLES = (3, 4)
DELAYED_CLEARING_CYCLES = (10, 19)

# Probability that clearing is delayed: 2 of the 18 events in the same deck that report a
# clearing time (16 normal, 2 delayed). 95% exact (Clopper-Pearson) CI (0.014, 0.347).
# Caveat: small sample, and only events in which load was lost. Read by
# scenario.sample_dip_duration at call time, so it can be swept.
DELAYED_CLEARING_P = 2 / 18

# Fault-type shares for transmission lines, ERCOT SPWG, "Review of Ground Fault Protection
# Methods for Transmission Lines" (2017), p. 8 table: L-G 65-70%, L-L-G 15-20%, L-L 5-10%,
# 3LG 2-5%. Range midpoints in percent, order (L-G, L-L-G, L-L, 3LG). The document does not
# cite its own source. scenario.py maps 1 phase = L-G, 2 phases = L-L-G + L-L, 3 phases = 3LG
# and normalizes.
FAULT_MIX_SPWG_MIDPOINTS_PCT = (67.5, 17.5, 7.5, 3.5)

# Faulted-phase counts (1, 2, 3 phases) among the 19 events with a known fault type in the
# ERCOT OWG deck above. Outcome-selected (only events where load was lost): use for worst-case
# runs only (scenario.sample(fault_mix="loss_events")).
FAULT_MIX_LOSS_EVENT_COUNTS = (13, 1, 5)

# Component shares of cooling power (compressor, pump, fan), as (low, high).
#   LBNL Data Center Energy Benchmarking, data center #21: chillers 11%, air handlers 9%,
#     pumps 4% of total power -> 46/38/17% of cooling. https://www.osti.gov/servlets/purl/926298
#   Iyengar & Schmidt (IBM), Electronics Cooling, Dec 2010: chiller compressor "about half" of
#     cooling, CRAC air movement "about one-third".
#     https://www.electronics-cooling.com/2010/12/energy-consumption-of-information-technology-data-centers/
#   arXiv 1804.00703 (simulation): chiller 28%, CRAH 12%, pumps ~4% of total at peak
#     -> 64/27/9%.
# These are energy shares at older chilled-water sites, not AI liquid cooling. The uniform
# shape within the sourced ranges is an assumption.
COOLING_COMPRESSOR_FRAC_RANGE = (0.46, 0.64)
COOLING_PUMP_FRAC_RANGE = (0.09, 0.17)
COOLING_FAN_FRAC_RANGE = (0.23, 0.38)

# Battery hall air temperature, degC. ASHRAE TC9.9 Thermal Guidelines, 5th ed., reference
# card, Table 2.1: recommended 18-27 degC; allowable A1 15-32 degC, A2 10-35 degC.
# https://www.ashrae.org/file%20library/technical%20resources/bookstore/supplemental%20files/therm-gdlns-5th-r-e-refcard.pdf
# No source gives the distribution of hall temperatures across sites; the stress values are
# the allowable upper limits.
HALL_TEMP_RECOMMENDED_C = (18.0, 27.0)
HALL_TEMP_ALLOWABLE_MAX_C = {"A1": 32.0, "A2": 35.0}

# Empirical DFW hourly outdoor temperature (column temp_c; rows with flag != "missing").
# NOAA Local Climatological Data, DFW airport station 72259003927, cleaned file in the repo
# (read-only; covers 2021-01-01 to 2026-10-10). Interim, until the Bayesian network's
# ridethrough.drivers.sample.sample_drivers() supplies correlated temperature and load.
OUTDOOR_TEMP_CSV = Path(__file__).resolve().parents[1] / "data_bayesian-network" / "dfw_hourly_temp_clean.csv"
# Only complete calendar years (local standard time) are used, 2021-2025, the same fit
# period as the Bayesian network's driver model. 2026 is excluded because the file stops on
# Oct 10, so it holds a summer without a winter and would overweight hot hours.
OUTDOOR_TEMP_YEARS = (2021, 2025)
