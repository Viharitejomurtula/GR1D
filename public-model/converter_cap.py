"""Converter (LM5176-based representative design) and BCAP3000 ultracapacitor models. Bounds from evidence.py;
distribution shapes are sensitivity assumptions. Design choices (RSENSE etc.) are explicit parameters, not datasheet values."""
import numpy as np
import evidence as e

def _shape(rng, n, shape):
    return {"uniform": lambda: rng.uniform(-1, 1, n), "triangular": lambda: rng.triangular(-1, 0, 1, n),
            "edge": lambda: np.sign(rng.uniform(-1, 1, n)) * rng.beta(.5, .5, n)}[shape]()

def current_limit_A(n, rsense_mohm, mode="buck", shape="uniform", rng=None):
    """Factor 10: I_lim = V_cs/Rsense, V_cs in datasheet [min,max] around typ."""
    rng = rng or np.random.default_rng(0)
    lo, typ, hi = e.LM5176["ilim_buck_mV" if mode == "buck" else "ilim_boost_mV"]
    u = _shape(rng, n, shape); v = np.where(u >= 0, typ + u * (hi - typ), typ + u * (typ - lo))
    return v / rsense_mohm  # mV/mohm = A

def step_response(t, bw_hz, delay_s=0.0, order=1):
    """Factor 11: closed-loop response to a unit load step; bandwidth must be swept (no published load-step curve extracted)."""
    tau = 1 / (2 * np.pi * bw_hz); ts = np.clip(t - delay_s, 0, None)
    if order == 1: return 1 - np.exp(-ts / tau)
    w = 1 / tau; return 1 - np.exp(-w * ts) * (1 + w * ts)   # critically damped 2nd order

def bandwidth_from_fsw(fsw_hz, ratio=(0.05, 0.1)):
    """Rule-of-thumb crossover 1/20-1/10 of fsw (design guidance, NOT a datasheet value)."""
    return fsw_hz * np.array(ratio)

def overload_duration_s(p_w, T0, Tmax, tamb, Rth, Cth, loss_frac=0.05):
    """Factor 12: lumped thermal: Cth dT/dt = loss - (T-Tamb)/Rth, loss = loss_frac*P. Time to reach Tmax (inf if steady state below)."""
    q = loss_frac * p_w; Tss = tamb + q * Rth
    if Tss <= Tmax: return np.inf
    tau = Rth * Cth; return tau * np.log((Tss - T0) / (Tss - Tmax))

def pmax_W(v_store, i_lim_A, p_rated_W, T, T_derate_start=85.0, T_max=125.0):
    """Factor 15: min(current limit * V, rated), linear thermal derate T_derate_start..T_max (derate points are assumptions)."""
    d = np.clip((T_max - T) / (T_max - T_derate_start), 0, 1)
    return np.minimum(v_store * i_lim_A, p_rated_W) * d

# ---- Ultracapacitor (factors 17, 18) ----
def health(age_frac, kind="life"):
    """age_frac 0..1 of spec'd life; end-of-life criteria from datasheet: C -30%, R +150% (life) or C -20%, R +60% (endurance)."""
    b = e.BCAP3000; dC = b["life_dC" if kind == "life" else "endurance_dC"]; dR = b["life_dR" if kind == "life" else "endurance_dR"]
    return 1 + dC * age_frac, 1 + dR * age_frac      # (C multiplier, ESR multiplier), linear aging assumption

def capacitance_F(n, age_frac=0.0, kind="life", shape="uniform", rng=None):
    rng = rng or np.random.default_rng(0); b = e.BCAP3000
    tol = (1 + b["C_tol"][1] * (_shape(rng, n, shape) + 1) / 2)       # 0..+20% manufacturing (one-sided per datasheet)
    cm, _ = health(age_frac, kind)
    return b["C_nom_F"] * tol * cm

def esr_mohm(age_frac=0.0, kind="life"):
    """ESR_DC is 'max' per datasheet -> treated as upper bound; aging multiplier from end-of-life criteria."""
    return e.BCAP3000["esr_dc_mohm"] * health(age_frac, kind)[1]

if __name__ == "__main__":
    rng = np.random.default_rng(1)
    print("current limit, Rsense=1 mohm buck:", {s: (lambda x: (x.min().round(1), x.max().round(1)))(current_limit_A(10000, 1.0, 'buck', s, rng)) for s in ("uniform", "triangular", "edge")})
    t = np.linspace(0, 5e-3, 5001)
    for bw in bandwidth_from_fsw(200e3):
        r = step_response(t, bw); print(f"bw {bw/1e3:.0f} kHz: 90% rise {t[np.argmax(r>=.9)]*1e6:.0f} us")
    print("thermal ex (3kW,Rth=.5,Cth=200,Tamb=40,T0=60,Tmax=125):", overload_duration_s(3000, 60, 125, 40, .5, 200, .05), "s")
    print("Pmax @48V, 60A limit, 3kW rated: 25C", pmax_W(48, 60, 3000, 25), " 105C", pmax_W(48, 60, 3000, 105))
    for a in (0, .5, 1):
        print(f"age {a}: C mean {capacitance_F(5000,a,rng=rng).mean():.0f} F, ESR {esr_mohm(a):.3f} mohm")
    # PSU hold-up link: effective-cap aging on holdup
    import models as m; print("holdup @100% load, cap -30%:", m.holdup_aged(1.0, cap_frac=0.7), "ms")
