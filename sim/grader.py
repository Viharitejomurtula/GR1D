"""ERCOT NOGRR 282 compliance grading.

Operates on a finished time series, so it is independent of which engine produced it
(OpenModelica FMU, the NumPy prototype, or anything later). Four checks, all of which
must pass:

  (a) stay connected through the Section 2.14(2) Table A envelope
  (b) hold the voltage-proportional power floor, Section 2.14(2)(c)
  (c) return to 90% of pre-disturbance power within 2.0 s of V crossing back above 0.90 pu
  (d) never exceed 125% of maximum normal operating current, Section 2.14(2)(d)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import constants as C


@dataclass
class Grade:
    passed: bool
    # NOGRR 2.14(2)(c) splits on energization date: before Jan 1 2028 the proportional power
    # floor applies only "if capable", after it is mandatory. `passed` grades the post-2028
    # rule (the standard anything designed today will actually energize under, given ERCOT's
    # 410 GW queue). `passed_pre2028` is the same run under the escape clause -- reporting
    # both costs nothing and "passes today, fails in 2028" is the actionable answer.
    passed_pre2028: bool
    failure_mode: str
    recovery_margin_s: float
    min_power: float
    # Distinguishes "recovered late" from "settled on a permanent plateau". Without it,
    # recovery_margin_s for a never-recovering run is dominated by window length rather
    # than by how badly the run failed, which is a poor training signal.
    final_power_frac: float
    floor_violation_s: float
    peak_current_pu: float
    envelope_violation_s: float
    storage_left: float = float("nan")
    psu_restart_s: float | None = None
    trips: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        d = self.__dict__.copy()
        d["passed"] = bool(self.passed)
        return d


def _disturbance_mask(v_pu: np.ndarray) -> np.ndarray:
    return (v_pu < C.CONTINUOUS_V_LOW_PU) | (v_pu > C.CONTINUOUS_V_HIGH_PU)


def _elapsed_in_disturbance(t: np.ndarray, disturbed: np.ndarray) -> np.ndarray:
    """Time since the current contiguous disturbance began, 0 where not disturbed."""
    elapsed = np.zeros_like(t)
    start = None
    for i, d in enumerate(disturbed):
        if d and start is None:
            start = t[i]
        elif not d:
            start = None
        if start is not None:
            elapsed[i] = t[i] - start
    return elapsed


def grade(
    t: np.ndarray,
    v_pu: np.ndarray,
    p_grid: np.ndarray,
    i_pu: np.ndarray,
    connected: np.ndarray | None = None,
    *,
    storage_left: float = float("nan"),
    psu_restart_s: float | None = None,
    trips: list[str] | None = None,
) -> Grade:
    """Grade one run.

    t, v_pu, p_grid, i_pu are equal-length traces. i_pu is current as a fraction of
    maximum normal operating current. connected defaults to always-connected.
    """
    t = np.asarray(t, dtype=float)
    v_pu = np.asarray(v_pu, dtype=float)
    p_grid = np.asarray(p_grid, dtype=float)
    i_pu = np.asarray(i_pu, dtype=float)
    connected = np.ones_like(t, dtype=bool) if connected is None else np.asarray(connected, dtype=bool)
    trips = list(trips or [])

    dt = float(np.median(np.diff(t))) if t.size > 1 else 0.0
    disturbed = _disturbance_mask(v_pu)

    if not disturbed.any():
        p_pre = float(np.mean(p_grid)) if p_grid.size else 0.0
        return Grade(
            passed=True,
            passed_pre2028=True,
            failure_mode="no disturbance",
            recovery_margin_s=C.RECOVERY_DEADLINE_S,
            min_power=float(np.min(p_grid) / p_pre) if p_pre else 1.0,
            final_power_frac=float(p_grid[-1] / p_pre) if p_pre else 1.0,
            floor_violation_s=0.0,
            peak_current_pu=float(np.max(i_pu)) if i_pu.size else 0.0,
            envelope_violation_s=0.0,
            storage_left=storage_left,
            psu_restart_s=psu_restart_s,
            trips=trips,
        )

    first = int(np.argmax(disturbed))
    # Pre-disturbance power: median of the later half of the quiet period, so start-up
    # transients cannot bias the reference (the mean over the whole prefix did, and its value
    # then depended on the output sampling step).
    p_pre = float(np.median(p_grid[first // 2:first])) if first > 1 else float(p_grid[0])
    if p_pre <= 0:
        p_pre = float(np.max(p_grid)) or 1.0

    p_frac = p_grid / p_pre

    # (a) Envelope. At each instant the requirement is read from the instantaneous
    # voltage; the load must still be connected while the disturbance has run for less
    # than that tier's minimum hold time.
    elapsed = _elapsed_in_disturbance(t, disturbed)
    required = np.array([C.required_ride_through_s(v) or 0.0 for v in v_pu])
    must_hold = disturbed & (elapsed <= required)
    envelope_violation_s = float(np.sum(must_hold & ~connected) * dt)

    # (b) Power floor.
    floor = np.array([C.power_floor_pu(v) for v in v_pu])
    below_floor = disturbed & (p_frac < floor - 1e-9)
    floor_violation_s = float(np.sum(below_floor) * dt)

    # (c) Recovery: after EVERY return above 0.90 pu that is followed by at least the deadline of
    # undisturbed voltage (or by the end of the trace), power must be back to 90% within 2.0 s.
    # Earlier versions graded only the final return, so a load that failed to come back after
    # dip 2 of 6 and sat shed until dip 3 passed unnoticed. A return cut short by the next dip
    # inside the deadline is not graded: NOGRR 282's clock semantics for that case are unread.
    above = v_pu >= C.RECOVERY_TRIGGER_V_PU
    recovery_margin_s = -C.RECOVERY_DEADLINE_S
    margins = []
    returns = [i for i in range(1, t.size) if above[i] and not above[i - 1]]
    for r in returns:
        later_below = np.nonzero(~above[r:])[0]
        window_end = t[r + later_below[0]] if later_below.size else t[-1]
        if window_end - t[r] < C.RECOVERY_DEADLINE_S - 1e-9 and later_below.size:
            continue  # next dip arrived before the deadline: not gradable
        t_ret = t[r]
        recovered = np.nonzero((t >= t_ret) & (t <= window_end) & (p_frac >= C.RECOVERY_FRACTION))[0]
        if recovered.size:
            margins.append(float(C.RECOVERY_DEADLINE_S - (t[recovered[0]] - t_ret)))
        else:
            margins.append(min(float(C.RECOVERY_DEADLINE_S - (window_end - t_ret)), -1e-9))
    if margins:
        recovery_margin_s = min(margins)
    elif above.any():
        # No gradable return (every return was cut short): fall back to the final sustained return.
        last_below = np.nonzero(~above)[0]
        candidate = int(last_below[-1]) + 1 if last_below.size else 0
        if candidate < t.size:
            recovered = np.nonzero((t >= t[candidate]) & (p_frac >= C.RECOVERY_FRACTION))[0]
            recovery_margin_s = (float(C.RECOVERY_DEADLINE_S - (t[recovered[0]] - t[candidate])) if recovered.size
                                 else min(float(C.RECOVERY_DEADLINE_S - (t[-1] - t[candidate])), -1e-9))

    # (d) Current cap. Section 2.14(2)(d) is an absolute limit: exceeding 125% at any
    # point during the disturbance is a violation. The March 2026 revision adds a "<= 0.5 s"
    # qualifier, but only a secondary source describes it and the semantics are ambiguous
    # (a 0.80 pu sag held for the required 2.0 s draws 1.25 pu throughout, which a naive
    # duration limit would fail). Gating on magnitude alone until the primary text is read.
    peak_current_pu = float(np.max(i_pu)) if i_pu.size else 0.0
    current_violation = peak_current_pu > C.CURRENT_CAP_PU

    failures = []
    if envelope_violation_s > 0:
        failures.append("disconnected inside envelope")
    if current_violation:
        failures.append("exceeded 125% current cap")
    if recovery_margin_s < 0:
        failures.append("missed 2.0 s recovery")

    # The power floor is the only check the energization-date split touches.
    failures_pre2028 = list(failures)
    if floor_violation_s > 0:
        failures.append("below power floor")

    mode = _classify(failures, trips)

    return Grade(
        passed=not failures,
        passed_pre2028=not failures_pre2028,
        failure_mode=mode,
        recovery_margin_s=recovery_margin_s,
        min_power=float(np.min(p_frac)),
        final_power_frac=float(p_frac[-1]),
        floor_violation_s=floor_violation_s,
        peak_current_pu=peak_current_pu,
        envelope_violation_s=envelope_violation_s,
        storage_left=storage_left,
        psu_restart_s=psu_restart_s,
        trips=trips,
    )


def _classify(failures: list[str], trips: list[str]) -> str:
    """Name the mechanism, preferring equipment evidence over the symptom."""
    if not failures:
        return "passed"
    joined = " ".join(trips)
    if "cooling" in joined or "vfd" in joined:
        return "cooling tripped"
    if "psu" in joined:
        return "PSU shutdown and restart delay"
    if "bbu" in joined and "missed 2.0 s recovery" in failures:
        return "storage hand-back too slow"
    return failures[0]
