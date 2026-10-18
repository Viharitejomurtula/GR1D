import pytest
import numpy as np
from sim import grader

def _trace(events, dur=30.0, dt=1e-3):
    """events: list of (t_dip_start, dip_len, t_power_back_after_clear). Voltage 0.5 during dip, 1.0 otherwise; power 1.0 except shed from dip start until power_back."""
    t = np.arange(0, dur, dt); v = np.ones_like(t); p = np.ones_like(t)
    for ts, ln, back in events:
        v[(t >= ts) & (t < ts + ln)] = 0.5
        p[(t >= ts) & (t < ts + ln + back)] = 0.0
    return t, v, p, np.ones_like(t)

def test_single_dip_recovers_in_time():
    t, v, p, i = _trace([(2.0, 0.1, 1.0)]); g = grader.grade(t, v, p, i); assert g.recovery_margin_s > 0.5

def test_missed_recovery_after_middle_dip_is_caught():
    # dip 1 at 2 s: power back 5 s after clear (late). dip 2 at 15 s: recovers promptly. Old grader looked only at the final return.
    t, v, p, i = _trace([(2.0, 0.1, 5.0), (15.0, 0.1, 0.5)]); g = grader.grade(t, v, p, i)
    assert g.recovery_margin_s < 0

def test_dip_cut_short_by_next_dip_is_not_graded():
    t, v, p, i = _trace([(2.0, 0.1, 0.0), (2.6, 0.1, 0.5)]); g = grader.grade(t, v, p, i); assert g.recovery_margin_s > 0


def test_subcycle_current_spike_is_not_graded_as_a_cycle_rms_peak():
    t = np.arange(0, 5.0, 1e-3); v = np.ones_like(t); v[(t > 1) & (t < 1.05)] = 0.5
    p = np.ones_like(t); i = np.ones_like(t); i[(t >= 1.0) & (t < 1.002)] = 3.0      # 2 ms spike at the dip onset
    g = grader.grade(t, v, p, i)
    assert g.peak_current_raw_pu == 3.0 and g.peak_current_pu < 1.3                  # 2 ms of 3.0 inside a 16.7 ms window -> ~1.24

def test_sustained_overcurrent_is_still_graded():
    t = np.arange(0, 5.0, 1e-3); v = np.ones_like(t); v[(t > 1) & (t < 1.05)] = 0.5
    p = np.ones_like(t); i = np.ones_like(t); i[(t >= 1.0) & (t < 1.05)] = 1.6
    assert grader.grade(t, v, p, i).peak_current_pu == pytest.approx(1.6, abs=1e-6)


# ---- Section 2.14(2)(d) and (c), PUCT report 2026-07-09 ----
def _dip_trace(i_during, dip_len=0.1, over_len=None, dur=10.0, dt=1e-3, p_during=1.0):
    t = np.arange(0, dur, dt); v = np.ones_like(t); v[(t > 2.0) & (t < 2.0 + dip_len)] = 0.5
    i = np.ones_like(t) * 0.9; i[(t >= 2.0) & (t < 2.0 + (over_len or dip_len))] = i_during
    p = np.ones_like(t); p[(t >= 2.0) & (t < 2.0 + dip_len)] = p_during
    return t, v, p, i

def test_current_cap_is_150_percent_of_the_facilitys_own_normal_maximum():
    t, v, p, i = _dip_trace(i_during=0.9 * 1.45)                       # 145% of normal (0.9): allowed
    assert "current" not in grader.grade(t, v, p, i).failure_mode
    t, v, p, i = _dip_trace(i_during=0.9 * 1.60)                       # 160%: over the cap
    g = grader.grade(t, v, p, i); assert not g.passed and "150%" in g.failure_mode

def test_125_percent_is_no_longer_a_violation_when_brief():
    t, v, p, i = _dip_trace(i_during=0.9 * 1.3, dip_len=0.2)
    g = grader.grade(t, v, p, i); assert g.passed and g.peak_current_pu == pytest.approx(1.3, abs=0.02)

def test_overcurrent_must_not_persist_longer_than_half_a_second():
    t, v, p, i = _dip_trace(i_during=0.9 * 1.2, dip_len=0.8)           # 120% for 0.8 s (a 0.8 pu-style sag): under the cap but too long
    g = grader.grade(t, v, p, i); assert not g.passed and g.overcurrent_s > 0.5 and "0.5 s" in g.failure_mode

def test_cooling_that_trips_below_035_pu_is_removed_from_the_reference():
    t = np.arange(0, 10.0, 1e-3); v = np.ones_like(t); v[(t > 2.0) & (t < 2.1)] = 0.2
    p_cool = np.full_like(t, 40.0); p_it = np.full_like(t, 60.0)
    p_cool[t >= 2.0] = 0.0                                              # cooling trips and never returns
    p = p_cool + p_it; i = np.ones_like(t)
    without = grader.grade(t, v, p, i); with_ = grader.grade(t, v, p, i, p_cooling=p_cool)
    assert not without.passed and with_.cooling_exempted and with_.recovery_margin_s > 0

def test_cooling_exemption_does_not_apply_to_shallow_sags():
    t = np.arange(0, 10.0, 1e-3); v = np.ones_like(t); v[(t > 2.0) & (t < 2.1)] = 0.6
    p_cool = np.full_like(t, 40.0); p_cool[t >= 2.0] = 0.0; p = p_cool + 60.0; i = np.ones_like(t)
    g = grader.grade(t, v, p, i, p_cooling=p_cool); assert not g.cooling_exempted and not g.passed

def test_load_transfer_scheme_is_held_to_half_a_second():
    t = np.arange(0, 10.0, 1e-3); v = np.ones_like(t); v[(t > 2.0) & (t < 2.1)] = 0.3
    p = np.ones_like(t); p[(t >= 2.0) & (t < 2.1 + 1.0)] = 0.0          # back 1.0 s after the dip clears
    i = np.ones_like(t)
    assert grader.grade(t, v, p, i).passed                               # fine under the 2.0 s rule
    g = grader.grade(t, v, p, i, used_load_transfer=True); assert not g.passed and g.recovery_deadline_s == 0.5
