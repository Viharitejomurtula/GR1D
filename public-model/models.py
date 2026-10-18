import numpy as np
from evidence import PSU_HOLDUP, RELAY_UV_ACC

def holdup_ms(load):
    """NOTE: datasheet table covers 100-150% load only; below 100% this is an extrapolation of t=E/P (unverified; real units may differ at light load)."""
    """Hold-up = E/P: fit t = k/load to AE table (20ms@1.0 -> 16.67@1.2 -> 13.33@1.5 all equal 20/load)."""
    return 20.0 / np.asarray(load, float)

def holdup_aged(load, cap_frac=1.0, eff_scale=1.0):
    return holdup_ms(load) * cap_frac * eff_scale

def relay_threshold_samples(setting_v, n, shape="uniform", rng=None):
    """Bounded sensitivity shapes within SEL +-1%+-0.5V. Shapes are assumptions, not measured."""
    rng = rng or np.random.default_rng(0)
    h = RELAY_UV_ACC[0].value / 100 * setting_v + RELAY_UV_ACC[1].value
    u = {"uniform": lambda: rng.uniform(-1, 1, n),
         "triangular": lambda: rng.triangular(-1, 0, 1, n),
         "edge": lambda: np.sign(rng.uniform(-1, 1, n)) * rng.beta(0.5, 0.5, n)}[shape]()
    return setting_v + h * u

def voltage_dip(t, depth_pu, t0, dur, shape="rect", ramp=0.0):
    """Synthetic RMS envelope (pu). shapes: rect, gradual (linear recovery over `ramp`)."""
    v = np.ones_like(t)
    m = (t >= t0) & (t < t0 + dur); v[m] = 1 - depth_pu
    if shape == "gradual":
        r = (t >= t0 + dur) & (t < t0 + dur + ramp)
        v[r] = (1 - depth_pu) + depth_pu * (t[r] - t0 - dur) / ramp
    return v

def nerc_sequence(dt=1e-3, pad=2.0, depth_range=(0.60, 0.75)):
    """Historical NERC 2024 six-dip event as RMS envelope (pu). Depth drawn from reported 0.25-0.40 pu residual; shape rectangular (assumed)."""
    from evidence import NERC_DIPS
    t0 = NERC_DIPS[0][0]; t = np.arange(0, NERC_DIPS[-1][0] - t0 + pad, dt); v = np.ones_like(t)
    for ts, d, _ in NERC_DIPS:
        v[(t >= ts - t0) & (t < ts - t0 + d / 1000)] = 0.325  # midpoint of 0.25-0.40
    return t, v

def nerc_gaps():
    from evidence import NERC_DIPS
    ts = [d[0] for d in NERC_DIPS]; return np.diff(ts)
