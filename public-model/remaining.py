"""Remaining factor models (4-9, 16, 23-30, 32). Each function states its evidence label.
EVIDENCE TAGS: [SPEC]=published spec, [DATA]=public measurement, [EX]=public example, [PHYS]=physics model, [ASSUME]=explicit assumption, not calibrated."""
import numpy as np, csv, evidence as e
RNG = np.random.default_rng(0)

# ---- 4. Phase jump [PHYS][ASSUME]: voltage divider between source Zs and fault Zf seen from the PCC ----
def phase_jump_deg(xr_source, xr_fault, depth_pu):
    """Pre-fault 1<0. During fault V = Zf/(Zs+Zf); |Zf|/|Zs| is solved so that |V| = 1-depth exactly (previous version only
    matched the magnitude when angles were equal). Jump = arg(V). Sweep X/R mismatch; no measured angle-jump data."""
    from math import atan
    zs = np.exp(1j * atan(xr_source)); target = 1 - depth_pu
    f = lambda k: abs(k * np.exp(1j * atan(xr_fault)) / (zs + k * np.exp(1j * atan(xr_fault)))) - target
    lo, hi = 1e-9, 1e9
    for _ in range(200):
        mid = np.sqrt(lo * hi); (lo, hi) = (mid, hi) if f(mid) < 0 else (lo, mid)
    zf = mid * np.exp(1j * atan(xr_fault)); return float(np.degrees(np.angle(zf / (zs + zf))))

# ---- 5. Post-dip overvoltage [PHYS][EX]: load rejection dV = (dP R + dQ X)/V^2, decay by tap/shunt action ----
OV_EVENTS = [(1500, 1.07), (1800, 1.05), (3869, 1.138)]   # (MW lost, peak pu): NERC 2024; PJM 2025-02-17; PJM 2026-07-22 (raw/events/)
def overvoltage_peak_range(d_mw):
    """Peak pu after a load loss of d_mw, as an interval from the 3 public events' dV/MW (2.8e-5 .. 4.7e-5 pu/MW).
    NOT monotone in MW across events, so grid strength / shunt state matter; n=3, no distribution claimed."""
    s = [(v - 1) / mw for mw, v in OV_EVENTS]; return 1 + min(s) * d_mw, 1 + max(s) * d_mw

def overvoltage_traj(t, d_mw=1500.0, scc_mva=60000.0, xr=10.0, tau_s=120.0, v_peak_target=None):
    """Peak from the physics divider dP/Scc*(X/R factor), or v_peak_target; exponential decay (operators trip shunt capacitors)."""
    dv = (d_mw / scc_mva) * xr / np.sqrt(1 + xr**2)
    if v_peak_target: dv = v_peak_target - 1
    return 1 + dv * np.exp(-t / tau_s)

# ---- 6. AI job crash/restart power trajectories [ASSUME] (shape library, fractions are parameters) ----
def ai_power_traj(t, scenario, p_full=1.0, t_crash=0.0, drop_to=0.25, restart_after=30.0, ramp_s=5.0, n_nodes=100, stagger_s=20.0):
    p = np.full_like(t, p_full)
    if scenario == "immediate_drop": p[t >= t_crash] = drop_to * p_full
    elif scenario == "partial_drop":  p[t >= t_crash] = 0.6 * p_full
    elif scenario in ("synchronized_restart", "staggered_restart"):
        p[t >= t_crash] = drop_to * p_full
        starts = (np.full(n_nodes, t_crash + restart_after) if scenario == "synchronized_restart"
                  else t_crash + restart_after + RNG.uniform(0, stagger_s, n_nodes))
        frac = np.mean([np.clip((t - s) / ramp_s, 0, 1) for s in starts], axis=0)
        p = np.where(t >= t_crash, (drop_to + (1 - drop_to) * frac) * p_full, p)
    return p

# ---- 7. Battery SOC when a dip arrives [PHYS][ASSUME]: fixed charge policy, random discharge events ----
def soc_samples(n=10000, soc_target=1.0, charge_c=0.2, event_rate_per_day=0.5, event_dod=0.1, recov_cap=1.0):
    """Renewal process: SOC drops event_dod at events, recharges at charge_c/h to soc_target (CC). Returns SOC at random observation times."""
    out = np.empty(n)
    for i in range(n):
        gap = RNG.exponential(24 / event_rate_per_day)      # hours since last discharge event
        soc_after = soc_target - event_dod * RNG.uniform(0.5, 1.5)
        out[i] = min(soc_target, soc_after + charge_c * gap)
    return out

# ---- 8. Units offline [ASSUME] enumerated configurations (no weights) ----
def maintenance_states(n_units=2, redundancy="N+1"):
    base = {"normal": n_units, "one_unit_offline": n_units - 1}
    if redundancy == "2N": base["one_side_offline"] = n_units // 2
    return base

# ---- 9. Equipment age [DATA] -> stress-hours; see nasa_cap_aging.py ----

# ---- 16. Battery SOC-estimation error [DATA] from NASA battery capacity fade: estimator assuming rated capacity ----
def soc_error_from_fade(path="../datacenter-risk-model/data/processed/nasa_battery_discharge.csv"):
    rows = [r for r in csv.DictReader(open(path)) if r["capacity_valid"] == "True"]
    soh = np.array([float(r["soh_vs_rated"]) for r in rows]); amb = np.array([float(r["ambient_c"]) for r in rows])
    # Coulomb-counting SOC error after discharging fraction f of ACTUAL capacity, estimator uses RATED capacity (soh=1):
    # est_drop = f*soh... error = f*(1-soh) as fraction-of-rated SOC (underestimates remaining energy if soh<1 ... sign: est SOC too high)
    return soh, amb

def soc_error_samples(f_discharged=0.5, bias_pct=0.0):
    soh, amb = soc_error_from_fade()
    return f_discharged * (1 - soh) + bias_pct / 100 * f_discharged

# ---- 23. Rack energy buffer [SPEC-secondary] ----
def rack_usable_energy_kwh(n_modules=3, e_nom_kwh=1.0, soc=1.0, soc_min=0.1, health=1.0, p_load_kw=15.0, p_max_kw=15.0):
    """Usable = n*E*health*(soc-soc_min); runtime = E/p, power-limited to p_max per module. BBU 15kW/~4min=1kWh is UNVERIFIED (Analog Devices)."""
    e_use = n_modules * e_nom_kwh * health * max(soc - soc_min, 0); return e_use, e_use / min(p_load_kw, n_modules * p_max_kw) * 60

# ---- 24. Board undervoltage trip [SPEC TPS2663 tolerance + ASSUME design threshold] ----
def board_uv_trip(t, v_rail, thresh_v=42.0, tol=0.02, delay_us=11.0, rng=None):
    """Input is the RAIL voltage (V), not AC. Threshold = design setting with +-2% comparator tolerance (TPS2663 UVLO 1.09-1.15 V falling
    on 1.122 typ => ~+-2.5%); turn-off delay 9-16 us (typ 11). Trips if rail below threshold for >= delay."""
    rng = rng or RNG; th = thresh_v * (1 + tol * rng.uniform(-1, 1)); dt_us = (t[1] - t[0]) * 1e6; need = max(1, int(np.ceil(delay_us / dt_us)))
    below = v_rail < th; run = np.convolve(below.astype(int), np.ones(need, int), "full")[:len(below)]
    return run >= need

# ---- 25. Compressor controller trip [SPEC Copeland CoreSense] ----
def coresense_lockout(t, supply_vac):
    lo, hold = e.COPELAND_LOW_SUPPLY[0].value, e.COPELAND_LOW_SUPPLY[1].value; dt = t[1] - t[0]; acc = 0.0
    for v in supply_vac:
        acc = acc + dt if v < lo else 0.0
        if acc >= hold: return True
    return False

# ---- 26. Compressor/drive restart state machine [SPEC+CONFIG] ----
def restart_time_s(mode, lockout_delay_s=180.0, auto_delay_s=5.0, manual_reset_s=None):
    """Config parameters (anti-short-cycle lockout delay is a configuration, not random). 180 s is a COMMON default, [ASSUME]."""
    return {"immediate": 0.0, "delayed_auto": auto_delay_s, "lockout": lockout_delay_s, "manual": manual_reset_s if manual_reset_s is not None else np.inf}[mode]

# ---- 27. VFD ride-through [PHYS]: DC-link energy ----
def vfd_ridethrough_ms(p_load_w, c_dc_f, v_dc0=540.0, v_uv=350.0, residual_pu=0.0, v_ll=400.0, kinetic_H_s=0.0, s_rated_w=15e3, f_use=0.3):
    """Time before DC-link hits Vuv. If AC peak (sqrt2*V_LL*residual) still exceeds Vdc the rectifier keeps conducting -> inf.
    Otherwise t = [C(Vdc0^2-Vuv^2)/2 + kinetic]/P. Kinetic term (motor/load inertia, f_use of H*S) only if the drive is configured to use it."""
    if np.sqrt(2) * v_ll * residual_pu >= v_dc0: return np.inf
    e = 0.5 * c_dc_f * (v_dc0**2 - v_uv**2) + kinetic_H_s * s_rated_w * f_use
    return 1e3 * e / max(p_load_w, 1e-9)

# ---- 28. Pump VFD+contactor trip boundary [PHYS][ASSUME] ----
def pump_trip_boundary(residual_pu, load_frac, c_dc_f=2e-3, p_rated_w=15e3, v_uv=350.0, v_dc0=540.0, kinetic_H_s=0.0):
    """Max survivable dip duration (ms) at a residual voltage (pu of line-line 400 V). inf if rectifier keeps conducting."""
    return vfd_ridethrough_ms(p_rated_w * load_frac, c_dc_f, v_dc0, v_uv, residual_pu, 400.0, kinetic_H_s, p_rated_w)

# ---- 29. Transformer impedance [ASSUME tolerance] ----
def transformer_z_pu(n=1000, z_nom=0.0575, tol=0.075, shape="uniform"):
    """Nominal %Z with +-7.5% tolerance (standard two-winding transformer practice; value from general knowledge, not fetched)."""
    u = {"uniform": RNG.uniform(-1, 1, n), "triangular": RNG.triangular(-1, 0, 1, n)}[shape]; return z_nom * (1 + tol * u)

# ---- 30. Transformer energization / recovery inrush [PHYS] ----
def inrush_peak_pu(res_flux_pu, switch_angle_deg, phi_sat=1.2, l_air_pu=0.2, r_pu=0.01, f=60.0, cycles=10, dt=1e-5):
    """Single-phase flux model: dphi/dt = v - r i (v=cos so flux amplitude is 1 pu); i = (phi-phi_sat)/l_air above saturation else magnetizing~0. Returns peak current (pu)."""
    w = 2 * np.pi * f; phi = res_flux_pu; th = np.radians(switch_angle_deg); i_pk = 0.0
    for k in range(int(cycles / f / dt)):
        tt = k * dt; v = np.cos(w * tt + th) * w
        i = max(abs(phi) - phi_sat, 0) / l_air_pu * np.sign(phi)
        phi += (v - r_pu * i) * dt
        i_pk = max(i_pk, abs(i))
    return i_pk

# ---- 32. Breaker timing [ASSUME]: closing time ~60 ms per ETH VCB manual (arXiv 2208.07607); drift with operation count assumed ----
def breaker_close_time_ms(n_ops, nominal_ms=60.0, jitter_ms=0.5, drift_ms_per_1000=0.05, n=1):
    return nominal_ms + drift_ms_per_1000 * n_ops / 1000 + RNG.normal(0, jitter_ms, n)

if __name__ == "__main__":
    t = np.linspace(0, 600, 6001)
    print("4 phase jump deg (Xr_s=10, residual .325): ", {xf: round(phase_jump_deg(10, xf, .675), 1) for xf in (1, 3, 10)})
    print("5 peak range for 1500/3869 MW:", overvoltage_peak_range(1500), overvoltage_peak_range(3869))
    print("6 sync restart peak/ min:", ai_power_traj(t, "synchronized_restart", t_crash=10).max(), ai_power_traj(t, "immediate_drop", t_crash=10).min())
    print("7 SOC p5/p50/p95 by events/day:", {r: np.percentile(soc_samples(rate_ := r) if False else soc_samples(event_rate_per_day=r), [5, 50, 95]).round(2).tolist() for r in (0.5, 2, 6)})
    print("8", maintenance_states())
    err = soc_error_samples(0.5); print("16 SOC err (50%% discharge): mean %.3f p95 %.3f max %.3f (n=%d)" % (err.mean(), np.percentile(err, 95), err.max(), len(err)))
    print("23 rack:", rack_usable_energy_kwh(soc=0.8, health=0.9))
    tt = np.linspace(0, .2, 200001); vr = np.full_like(tt, 51.0); vr[(tt > .05) & (tt < .06)] = 30.0
    print("24 rail-based trip (thr 42 V, 10 ms rail sag to 30 V):", board_uv_trip(tt, vr).any(), "| 5 us sag:", board_uv_trip(tt, np.where((tt > .05) & (tt < .050005), 30., 51.)).any(), "| rail 44 V:", board_uv_trip(tt, np.full_like(tt, 44.)).any())
    ts = np.linspace(0, 5, 50001); sv = np.full_like(ts, 24.0); sv[(ts > 1) & (ts < 1.066)] = 0
    print("25 coresense lockout on 66 ms dip:", coresense_lockout(ts, sv), "| on 2.5 s outage:", coresense_lockout(ts, np.where((ts > 1) & (ts < 3.5), 0, 24.0)))
    print("26", {m: restart_time_s(m) for m in ("immediate", "delayed_auto", "lockout")})
    print("27 VFD ride-through ms @15kW,C=2mF, residual .325:", round(vfd_ridethrough_ms(15e3, 2e-3, residual_pu=.325), 1), "| residual .95 (rectifier conducts):", vfd_ridethrough_ms(15e3, 2e-3, residual_pu=.95), "| with H=1 s kinetic:", round(vfd_ridethrough_ms(15e3, 2e-3, residual_pu=.325, kinetic_H_s=1.0), 1))
    print("28 pump trip boundary (residual .325, load 1.0):", round(pump_trip_boundary(.325, 1.0), 1), "ms")
    z = transformer_z_pu(); print("29 Z range:", z.min().round(4), z.max().round(4))
    print("30 inrush peak pu: flux 0 / +0.8 @ switch 0deg:", round(inrush_peak_pu(0.0, 0), 2), round(inrush_peak_pu(0.8, 0), 2))
    print("32 breaker close ms @0/20000 ops:", breaker_close_time_ms(0, n=3).round(2), breaker_close_time_ms(20000, n=3).round(2))
