"""Server / AI load profile.

Reference implementation of the load model, used to cross-check the Modelica version
and to drive the NumPy fallback.

The synchronised AI swing is a periodic 0.2-3 Hz oscillation with a measured 1.9 pu/s
ramp rate (NERC large-loads whitepaper), modelled as a slew-rate-limited square wave.
That shape is right in both regimes: at 0.2 Hz the 250 ms edge is a fast transition on a
long plateau, while at 3 Hz the edge fills most of the period and the wave is effectively
triangular.
"""

from __future__ import annotations

import numpy as np

from . import constants as C
from .scenario import Scenario


def swing_profile(t: np.ndarray, sc: Scenario, p_rated: float) -> np.ndarray:
    """Slew-limited square wave, in watts, centred on zero."""
    target = 0.5 * sc.swing_size_frac * p_rated * np.sign(
        np.sin(2 * np.pi * sc.swing_freq_hz * t + sc.swing_phase)
    )
    slew_w_per_s = C.AI_SWING_SLEW_PU_S * p_rated

    out = np.empty_like(t)
    value = target[0]
    for i in range(t.size):
        dt = t[i] - t[i - 1] if i else 0.0
        step = slew_w_per_s * dt
        value += np.clip(target[i] - value, -step, step)
        out[i] = value
    return out


def server_power(
    t: np.ndarray,
    sc: Scenario,
    p_rated: float,
    restart_at_s: float | None = None,
) -> np.ndarray:
    """Total server power draw over time.

    restart_at_s is the instant power was restored after the busbar fell below the ORv3
    IT-gear floor; None means servers never lost power, so no restart surge applies.
    """
    p = sc.workload * p_rated + swing_profile(t, sc, p_rated)

    if restart_at_s is not None:
        after = t >= restart_at_s
        surge = (sc.restart_surge_x - 1.0) * p_rated
        p = p + np.where(
            after, surge * np.exp(-(t - restart_at_s) / sc.restart_surge_s), 0.0
        )
    return p


def cooling_share(outdoor_temp_c: float, share_25c: float) -> float:
    """Cooling load as a fraction of IT load, derated from the 25 C design point."""
    share = share_25c * (1.0 + 0.04 * (outdoor_temp_c - 25.0))
    return float(np.clip(share, 0.4 * share_25c, None))
