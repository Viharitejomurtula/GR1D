"""Tests for the sourced input distributions in sim/scenario.py.

What this file is
    Checks each sourced distribution drawn by scenario.sample() on 50,000 scenarios from a
    fixed seed: dip duration (ERCOT OWG clearing times), faulted-phase mix (ERCOT SPWG and the
    OWG loss events), cooling split (LBNL / IBM / arXiv ranges), BBU modules (Analog Devices
    Part 4), hand-back delay (Analog Devices Part 1), battery hall temperature (ASHRAE TC9.9)
    and outdoor temperature (NOAA LCD, DFW). Also checks reproducibility and that the
    GRID_FRIENDLY and LEGACY_UPS presets are unchanged. Sources are in sim/constants.py.

Reads (read-only)
    data_bayesian-network/dfw_hourly_temp_clean.csv (through scenario.outdoor_temps)

Writes
    nothing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sim import constants as C
from sim import scenario

N = 50_000
SEED = 20261017
TOL = 1e-12  # float slack on range ends


def _frame(**kwargs) -> pd.DataFrame:
    """N scenarios from SEED as a DataFrame, one column per Scenario field."""
    return pd.DataFrame([s.as_dict() for s in scenario.sample_many(N, seed=SEED, **kwargs)])


@pytest.fixture(scope="module")
def draws() -> pd.DataFrame:
    """N default scenarios (fault_mix "general", no module out, no hall stress)."""
    return _frame()


def _shares(x: pd.Series) -> np.ndarray:
    """Shares of faulted_phase_frac equal to 1/3, 2/3 and 1.0."""
    return np.array([np.isclose(x, v).mean() for v in (1 / 3, 2 / 3, 1.0)])


def test_dip_duration_ranges_and_delayed_share(draws):
    """Every duration is 3-4 cycles or 10-19 cycles at 60 Hz; the delayed share is 2/18 +/- 0.01.

    The bounds are exact cycles/60 (10/60 = 0.16667 s is just below the rounded 0.1667)."""
    d = draws["dip_duration_s"]
    normal = (d >= 3 / 60 - TOL) & (d <= 4 / 60 + TOL)
    delayed = (d >= 10 / 60 - TOL) & (d <= 19 / 60 + TOL)
    assert (normal | delayed).all()
    assert abs(delayed.mean() - 0.111) <= 0.01


def test_faulted_phase_general(draws):
    """General mix: shares of 1, 2, 3 faulted phases within 0.01 of [0.70, 0.26, 0.04]."""
    np.testing.assert_allclose(_shares(draws["faulted_phase_frac"]), [0.70, 0.26, 0.04], atol=0.01)


def test_faulted_phase_loss_events():
    """Loss-events mix: shares within 0.01 of [13/19, 1/19, 5/19]."""
    d = _frame(fault_mix="loss_events")
    np.testing.assert_allclose(_shares(d["faulted_phase_frac"]), [13 / 19, 1 / 19, 5 / 19], atol=0.01)


def test_cooling_split_in_sourced_ranges(draws):
    """For every draw: compressor in [0.46, 0.64], fan in [0.23, 0.38], pump in [0.09, 0.17]."""
    comp, fan = draws["cooling_compressor_frac"], draws["cooling_fan_frac"]
    pump = 1.0 - comp - fan
    for x, (lo, hi) in ((comp, (0.46, 0.64)), (fan, (0.23, 0.38)), (pump, (0.09, 0.17))):
        assert ((x >= lo - TOL) & (x <= hi + TOL)).all()


def test_bbu_modules_six_per_shelf(draws):
    """bbu_modules_per_rack == 6 x shelves_per_rack for every draw."""
    assert (draws["bbu_modules_per_rack"] == 6 * draws["shelves_per_rack"]).all()


def test_bbu_module_out_five_per_shelf():
    """With bbu_module_out=True, bbu_modules_per_rack == 5 x shelves_per_rack."""
    d = _frame(bbu_module_out=True)
    assert (d["bbu_modules_per_rack"] == 5 * d["shelves_per_rack"]).all()


def test_handback_delay(draws):
    """handback_delay_s is 0.2 s in every draw; LEGACY_UPS keeps 3.0 s."""
    assert (draws["handback_delay_s"] == 0.2).all()
    assert scenario.LEGACY_UPS.handback_delay_s == 3.0


def test_battery_temp(draws):
    """battery_temp_c in [18, 27] by default; hall_stress "A1" -> 32.0, "A2" -> 35.0."""
    t = draws["battery_temp_c"]
    assert ((t >= 18.0) & (t <= 27.0)).all()
    rng = np.random.default_rng(SEED)
    assert scenario.sample(rng, hall_stress="A1").battery_temp_c == 32.0
    assert scenario.sample(rng, hall_stress="A2").battery_temp_c == 35.0
    with pytest.raises(ValueError):
        scenario.sample(rng, hall_stress="A3")


@pytest.mark.parametrize("option", [
    {"hall_stress": "A1"}, {"hall_stress": "A2"}, {"fault_mix": "loss_events"}, {"bbu_module_out": True},
], ids=["hall_A1", "hall_A2", "loss_events", "module_out"])
def test_options_change_only_their_field(option):
    """With the same seed, each option changes only the field it targets, so stressed and
    unstressed batches can be compared scenario by scenario."""
    target = {"hall_stress": "battery_temp_c", "fault_mix": "faulted_phase_frac",
              "bbu_module_out": "bbu_modules_per_rack"}[next(iter(option))]
    base = scenario.sample_many(200, seed=SEED)
    varied = scenario.sample_many(200, seed=SEED, **option)
    for a, b in zip(base, varied):
        for f in scenario.FIELD_ORDER:
            if f != target:
                assert getattr(a, f) == getattr(b, f), f


def test_outdoor_temp_matches_dfw(draws):
    """Share of outdoor_temp_c >= 35 degC is 0.046 +/- 0.01 and < 0 degC is 0.024 +/- 0.01
    (DFW complete years 2021-2025)."""
    t = draws["outdoor_temp_c"]
    assert abs((t >= 35.0).mean() - 0.046) <= 0.01
    assert abs((t < 0.0).mean() - 0.024) <= 0.01


def test_same_seed_same_scenarios():
    """The same seed gives identical scenarios; a different seed does not."""
    a = scenario.sample_many(200, seed=SEED)
    b = scenario.sample_many(200, seed=SEED)
    c = scenario.sample_many(200, seed=SEED + 1)
    assert a == b
    assert a != c


# Preset values after the simulator structure fixes (items 1-9) and fix-1-3/fix-4 (4.5 ms sourced PSU debounce,
# bbu_sharing, psu_ilim_x), merged 2026-10-18: GRID_FRIENDLY and
# LEGACY_UPS must not change unless a preset is changed on purpose (then update this snapshot).
_BASE = dict(
    dip_depth_pu=0.6, dip_duration_s=0.083, dip_start_s=1.0, recovery_tau_s=0.0658,
    overshoot_pu=0.049, second_dip=False, reclose_gap_s=0.4, outdoor_temp_c=38.0,
    battery_temp_c=25.0, battery_age_yr=3.0, battery_soc0=0.95, workload=0.85, swing_size_frac=0.2,
    swing_freq_hz=1.0, swing_phase=0.0, restart_surge_x=1.15, restart_surge_s=0.5,
    supply_voltage_v=277.0, shelves_per_rack=6, bbu_modules_per_rack=36, cooling_share_25c=0.3,
    cooling_compressor_frac=0.4, cooling_fan_frac=0.35, z_total_pct=19.75, x_over_r=10.0,
    ramp_back_s=0.3, vfd_dc_uv_trip_pu=0.7, psu_trip_spread_frac=0.04, faulted_phase_frac=1.0,
    chain_loading_frac=0.75, psu_uv_delay_s=0.0045, bbu_sharing=True, psu_ilim_x=0.0, legacy_open_delay_s=0.05,
    ramp_on_grid_only=True, psu_cap_datasheet=True, n_groups=1, grp_load_cv=0.0, grp_holdup_cv=0.0,
    grp_bbu_cv=0.0, grp_trip_cv=0.0, cooling_vfd_frac=0.5, compressor_restart_s=180.0, count_n=0,
    count_threshold_pu=0.9, count_min_dur_s=0.0, count_window_s=60.0, extra_dips=(), horizon_s=0.0,
)
_GRID_FRIENDLY = dict(
    _BASE,
    transfer_threshold_pu=0.85, handback_delay_s=0.2, relay_pickup_pu=0.15, relay_delay_s=0.5,
    cooling_ride_through_s=3.0, psu_restart_delay_s=0.0, legacy_load_frac=0.0, vfd_kinetic=True,
    drive_restart_s=1.0,
)
_LEGACY_UPS = dict(
    _BASE,
    transfer_threshold_pu=0.9, handback_delay_s=3.0, relay_pickup_pu=0.85, relay_delay_s=0.0,
    cooling_ride_through_s=0.02, psu_restart_delay_s=5.5, legacy_load_frac=1.0, vfd_kinetic=False,
    drive_restart_s=600.0,
)

@pytest.mark.parametrize("preset, expected", [
    (scenario.GRID_FRIENDLY, _GRID_FRIENDLY), (scenario.LEGACY_UPS, _LEGACY_UPS),
], ids=["GRID_FRIENDLY", "LEGACY_UPS"])
def test_presets_unchanged(preset, expected):
    """Every preset field equals its value before this change."""
    assert preset.as_dict() == expected


def test_constants_match_sources():
    """The sourced constants hold the listed values."""
    assert C.DELAYED_CLEARING_P == 2 / 18
    assert C.NORMAL_CLEARING_CYCLES == (3, 4) and C.DELAYED_CLEARING_CYCLES == (10, 19)
    assert C.BBU_MODULES_PER_SHELF == 6 and C.BBU_REDUNDANT_MODULES == 1
    assert C.BBU_HANDBACK_CONFIRM_S == 0.2
    assert C.OUTDOOR_TEMP_YEARS == (2021, 2025)


def test_outdoor_temp_uses_complete_years_only():
    """outdoor_temps() holds exactly the non-missing 2021-2025 hours of the DFW file."""
    d = pd.read_csv(C.OUTDOOR_TEMP_CSV)
    year = d["hour_lst"].str[:4].astype(int)
    expected = d.loc[(d["flag"] != "missing") & year.between(2021, 2025), "temp_c"].to_numpy()
    np.testing.assert_array_equal(scenario.outdoor_temps(), expected)
