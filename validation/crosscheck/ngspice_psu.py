"""Cross-check the model's PSU hold-up behaviour against an ngspice power-stage circuit driven by the model's own inputs.

The real RideThroughCore model is run on a controlled single-group dip. The circuit is then driven by the SAME service-voltage trace,
the same lockout state (psu_online_frac) and the same server/BBU demand, and the two hold-up energy traces are compared.

What the circuit has that the model's energy bucket does not:
  * a PFC stage whose power is limited by its INPUT CURRENT (P <= eta * Vrms * I_lim), so a sag that does not lock the PSU out still
    leaves a shortfall that the bulk capacitor must cover;
  * a recharge rate set by the PFC's power headroom (P_max - P_load), not by a fixed time constant;
  * a constant-power DC-DC stage (I = P / V) on the bulk capacitor.

Parameters come from the spec the model already cites, not from the model's 60 J:
  C is sized so the capacitor delivers 20 ms at 3 kW OUTPUT through a DC-DC stage of efficiency PSU_EFF (the model's constant), and
  I_lim from the datasheet's 'full 3 kW down to 180 Vac' (I_lim = 3000 / (eta * 180)). Both are swept in run_all().
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from model_trace import trace  # noqa: E402
from sim import constants as K  # noqa: E402

V0, V_MIN = 400.0, 300.0
ETA = 0.965                       # sim.constants / model PSU_EFF
HOLDUP_S_SPEC = 0.020            # ORv3: 20 ms at full load
E_FRAC_BBU = 1.0 - (50.75 - 48.5) / 6.0   # RideThroughCore.mo: BBU takes over at 48.5 V


def pwl(t, y, t0, t1, scale=1.0):
    m = (t >= t0) & (t <= t1)
    return " ".join(f"{a - t0:.6f} {b * scale:.6g}" for a, b in zip(t[m], y[m]))


def circuit(t, vrms, online, p_load_out, *, c_f, i_lim, p_max, t0, t1, esr=0.0):
    c = f"""* PSU power stage driven by model traces
Vrms nrms 0 PWL({pwl(t, vrms, t0, t1)})
Vonl nonl 0 PWL({pwl(t, online, t0, t1)})
Vpld npld 0 PWL({pwl(t, p_load_out, t0, t1)})
Cb vint 0 {c_f:.9g} ic={V0}
Resr vb vint {max(esr, 1e-6):.6g}
Bpfc 0 vb I = v(nonl) * max(0, min(0.5e3*(6.0)*({V0} - v(vb)), min({p_max}, {ETA}*v(nrms)*{i_lim}))) / max(v(vb), 1)
Bld vb 0 I = v(npld) / {ETA} / max(v(vb), 1)
.ic v(vint)={V0} v(vb)={V0}
.tran 20u {t1 - t0} uic
.control
set noaskquit
run
wrdata OUT v(vint) v(vb)
quit
.endc
.end
"""
    return c


def run_circuit(t, vrms, online, p_load_out, **kw):
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "o.dat"
        cir = pathlib.Path(d) / "c.cir"
        cir.write_text(circuit(t, vrms, online, p_load_out, **kw).replace("OUT", str(out)))
        r = subprocess.run(["ngspice", "-b", str(cir)], capture_output=True, text=True, timeout=300)
        if not out.exists():
            raise RuntimeError(r.stdout[-1500:] + r.stderr[-800:])
        tt, vint, vb = np.loadtxt(out, usecols=(0, 1, 3), unpack=True)
    return tt + kw["t0"], vint, vb


def crossing(t, y, level, after):
    """First time at or after `after` that y falls below `level`, linearly interpolated (nan if never)."""
    m = t >= after
    tt, yy = t[m], y[m]
    idx = np.nonzero(yy < level)[0]
    if idx.size == 0:
        return float("nan")
    i = idx[0]
    return float(tt[0]) if i == 0 else float(np.interp(level, [yy[i], yy[i - 1]], [tt[i], tt[i - 1]]))


def compare(depth, dur, *, datasheet=True, workload=0.85, supply_v=230.0, i_lim_scale=1.0, c_scale=1.0, p_max_w=None, stop_s=3.0, uv_delay_s=1 / 60, esr=0.0):
    d = trace(depth, dur, supply_v=supply_v, workload=workload, uv_delay_s=uv_delay_s, stop_s=stop_s, psu_cap_datasheet=datasheet)
    t = d["time"]
    if t[-1] < stop_s - 1e-3:
        raise RuntimeError(f"model run ended early at {t[-1]:.3f}s (voltage collapse); not comparable")
    n_psu = d["grp[1].e_holdup_j"][0] / K.PSU_HOLDUP_ENERGY_J
    ps = d["grp[1].p_server_w"] / n_psu
    pb = d["grp[1].p_bbu_w"] / n_psu
    online = d["grp[1].psu_online_frac"]
    vrms = d["grp[1].v_sdp_pu"] * supply_v
    e_cap_j = K.PSU_RATED_W * HOLDUP_S_SPEC / ETA        # energy the capacitor must hand to the DC-DC stage
    c_f = c_scale * 2.0 * e_cap_j / (V0**2 - V_MIN**2)
    i_lim = i_lim_scale * K.PSU_RATED_W / (ETA * 180.0)
    p_max = p_max_w if p_max_w is not None else K.PSU_RATED_W / ETA
    t0, t1 = 0.9, stop_s
    tt, vint, vb = run_circuit(t, vrms, online, np.maximum(ps - pb, 0.0), c_f=c_f, i_lim=i_lim, p_max=p_max, t0=t0, t1=t1, esr=esr)
    e_ng = (vint**2 - V_MIN**2) / (V0**2 - V_MIN**2)
    e_ng = e_ng / e_ng[0]
    e_md = d["grp[1].e_frac"]
    m = (t >= t0) & (t <= t1)
    start = 1.0
    out = {
        "depth_pu": depth, "dur_ms": dur * 1e3, "workload": workload, "supply_v": supply_v,
        "e_min_model": float(e_md[m].min()), "e_min_ngspice": float(e_ng.min()),
        "t_bbu_model_ms": 1e3 * (crossing(t[m], e_md[m], E_FRAC_BBU, start) - start),
        "t_bbu_ngspice_ms": 1e3 * (crossing(tt, e_ng, E_FRAC_BBU, start) - start),
        "model_bbu_active": bool(d["bbu_active"][m].max() > 0.5),
    }
    t_end = start + dur
    for name, tr, tm in (("model", e_md[m], t[m]), ("ngspice", e_ng, tt)):
        k = np.nonzero((tm >= t_end) & (tr >= 0.95))[0]
        out[f"t_recharge95_{name}_ms"] = 1e3 * (tm[k[0]] - t_end) if k.size else float("nan")
        out[f"e_at_clear_{name}"] = float(np.interp(t_end, tm, tr))
    return out, (t[m], e_md[m], tt, e_ng)
