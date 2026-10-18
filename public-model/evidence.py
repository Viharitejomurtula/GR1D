"""Public-spec parameters with evidence labels. Values only where stated in the plan; others are None (to extract)."""
from dataclasses import dataclass
from typing import Optional

PUB_SPEC, PUB_MEAS, PUB_EX, NO_DATA = "public_specification", "public_measurement", "public_example", "no_direct_public_data"

@dataclass(frozen=True)
class Param:
    name: str; value: Optional[float]; unit: str; evidence: str; source: str; note: str = ""

# AE ORv3 3 kW PSU: load fraction -> hold-up (ms)
PSU_HOLDUP = {1.00: 20.00, 1.20: 16.67, 1.50: 13.33}
PSU_CURRENT_LIMIT_LOAD = Param("psu_current_limit_load_frac", 1.55, "frac", PUB_SPEC, "Advanced Energy ORv3 3kW datasheet")
# SEL-751A undervoltage pickup accuracy: +-1% of setting +-0.5 V; pickup/dropout < 1.5 cycles
RELAY_UV_ACC = (Param("relay_acc_pct", 1.0, "% of setting", PUB_SPEC, "SEL-751A datasheet"),
                Param("relay_acc_abs", 0.5, "V", PUB_SPEC, "SEL-751A datasheet"))
RELAY_TIME_CYCLES = Param("relay_pickup_time_max", 1.5, "cycles", PUB_SPEC, "SEL-751A datasheet")
# Copeland CoreSense: control supply < 17 VAC for 2 s (controller supply, NOT compressor line trip)
COPELAND_LOW_SUPPLY = (Param("coresense_low_vac", 17.0, "VAC", PUB_SPEC, "Copeland CoreSense bulletin"),
                       Param("coresense_low_time", 2.0, "s", PUB_SPEC, "Copeland CoreSense bulletin"))
# --- Advanced Energy ORv3 3kW PSU (raw/ae/psu3kw.pdf) ---
PSU_HOLDUP_100_MS = Param("psu_holdup_100pct", 20.0, "ms", PUB_SPEC, "AE ORv3 3kW datasheet", "200-277VAC input; typical column")
PSU_OCP = [  # (avg power kW, duration s) -> soft shutdown
    Param("psu_ocp_avg_long_kW", 3.45, "kW", PUB_SPEC, "AE ORv3 3kW datasheet", "for 10 s (protection section); an older section says 3.3 kW"),
    Param("psu_ocp_avg_short_kW", 3.6, "kW", PUB_SPEC, "AE ORv3 3kW datasheet", "for 100 ms")]
PSU_SOFT_SHUTDOWN = Param("psu_softshutdown_vdrop", 3.0, "V", PUB_SPEC, "AE ORv3 3kW datasheet", "drop then wait 6 ms for BBU (text also says 5 ms in one place)")
PSU_SOFT_WAIT = Param("psu_softshutdown_wait", 6.0, "ms", PUB_SPEC, "AE ORv3 3kW datasheet")
PSU_CC_DWELL = Param("psu_cc_dwell", 10.0, "ms", PUB_SPEC, "AE ORv3 3kW datasheet", "or output droops <48.5 V in constant-current mode")
PSU_OVP = (Param("psu_ovp_trip", 52.5, "V", PUB_SPEC, "AE ORv3 3kW datasheet", "react <=200 ms; fast OVP never exceeds 54 V"),)
PSU_UVLO_AC = Param("psu_ac_uvlo", 172.0, "VAC", PUB_SPEC, "AE ORv3 3kW datasheet", "start-up 178 VAC")
PSU_RETRY_S = Param("psu_retry_period", 5.0, "s", PUB_SPEC, "AE ORv3 3kW datasheet")

# --- Vertiv Liebert STS2 brochure (raw/vertiv/sts2.pdf) ---
STS_TRANSFER_CYCLES = Param("sts_transfer_max_cycles", 0.25, "cycles", PUB_SPEC, "Vertiv STS2 brochure", "'break-before-make, 1/4 cycle maximum'")
STS_TRANSFER_MS = {"60Hz": 1000/60*0.25, "50Hz": 1000/50*0.25}  # derived: 4.17 / 5.0 ms

# --- OCP BBU: official spec host unreachable from sandbox; secondary source only ---
BBU_POWER = Param("bbu_power", 15000.0, "W", "secondary_source", "Analog Devices ORv3 BBU article", "UNVERIFIED vs OCP spec; ~4 min per BBU")

# --- NERC Incident Review, 2024-07-10 (raw/nerc/review.pdf), Table 1 ---
NERC_DIPS = [  # (clock time s after 19:00:00, duration ms, cause)
    (23.351, 42, "initial fault (arrestor failure)"),
    (23.883, 66, "instantaneous simultaneous reclose both terminals"),
    (39.211, 58, "2nd reclose terminal A"),
    (44.630, 50, "2nd reclose terminal B"),
    (99.600, 66, "3rd reclose terminal A"),
    (105.016, 59, "3rd reclose terminal B")]
NERC_FAULT_V_PU = (0.25, 0.40)       # voltage during fault in load-loss area
NERC_PEAK_V_PU, NERC_PEAK_F_HZ, NERC_LOAD_LOSS_MW = 1.07, 60.047, 1500

# --- TI LM5176 (raw/ti/lm5176.pdf), TJ -40..125C, VIN=24V unless noted. HTSSOP-28 limits ---
LM5176 = dict(
    ilim_buck_mV=(66.0, 80.0, 94.0),     # valley, min/typ/max
    ilim_boost_mV=(100.0, 120.0, 140.0), # peak
    avg_loop_mV=(43.0, 50.0, 57.0),      # average current loop target (ISNS)
    fsw_200k_kHz=(175.0, 200.0, 225.0),  # RT=40k
    fsw_390k_kHz=(350.0, 390.0, 430.0))  # RT=20k
LM5176_SRC = "TI LM5176 datasheet SNVSAI1D"; LM5176_EV = PUB_SPEC

# --- Maxwell MC-series BCAP3000 P270 (raw/maxwell/mc.pdf; doc 1009361.10) ---
BCAP3000 = dict(C_nom_F=3000.0, C_tol=(0.0, +0.20), esr_dc_mohm=0.29, rated_V=2.7, surge_V=2.8,
                C_temp_pct=5.0, endurance_dC=-0.20, endurance_dR=+0.60,   # 1500 h, 65C, rated V
                life_dC=-0.30, life_dR=+1.50,                              # 10 y, 25C (end-of-life criteria)
                rth_CperW=3.2, T_range=(-40.0, 65.0))
BCAP_SRC = "Maxwell MC power series datasheet 1009361.10"
BCAP_NOTE = "Extracted ESR-vs-temperature line ('150% at 25C') is ambiguous in text extraction; treat ESR(T) as unresolved."

# --- Schneider ATV320 Programming Manual NVE41295 (rev 10/2017; raw/atv/m1.pdf, mirror ingenioer.au.dk), pages cited ---
ATV320 = dict(
    underv_fault_mgt={"options": ["Std fault", "Flt wo relay", "Alarm"], "default": "Std fault", "page": 259},
    underv_level_USL_V=(100.0, 276.0),            # mains-side undervoltage fault level, factory value per drive rating (p259)
    underv_timeout_USt_s=(0.2, 999.9, 0.2),       # min, max, FACTORY DEFAULT 0.2 s (p259) -> drive ignores UV shorter than this
    underv_prevention_StP={"options": ["No", "DC Maintain (inertia)", "Ramp stop", "Lock-out"], "default": "No", "page": 259},
    prevention_level_UPL_V=(133.0, 261.0), dc_maintain_tbS_s=(1, 9999), stop_ramp_StM_s=(0.01, 60.0, 1.0),
    underv_restart_tSM_s=(1.0, 999.9, 1.0),
    auto_restart_Atr={"default": "No", "waits_s": [1, 5, 10, 60], "tAr_default_min": 5, "needs": "2-wire level control", "page": 252})
