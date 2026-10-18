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
