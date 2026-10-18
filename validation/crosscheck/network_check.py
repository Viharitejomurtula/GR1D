"""Cross-check the model's voltage-drop network (a scalar quadratic) against an exact complex solve and DPsim's power-flow solver.

RideThroughCore.mo computes the service-delivery-point voltage as v = vs - k*(i-1)*vs with i = p/v, k = Z_EFF_FACTOR * z_total * chain_loading,
i.e. the series impedance is collapsed to one real drop factor derived at pf 0.9 and X/R 10. The exact network is a constant-power load (P + jQ)
behind a complex impedance Z = |Z|(cos a + j sin a), |Z| = z_total * chain_loading, tap-set so |V| = 1 at rated load: Vs0 = 1 + Z * conj(S_rated).
A dip scales the source: Vs = d * Vs0. The exact |V| is solved here in plain Python and independently by DPsim (SP power flow, Newton-Raphson).
Usage: .venv/bin/python validation/crosscheck/network_check.py
"""
from __future__ import annotations

import json
import pathlib

import dpsim as d
import numpy as np

Z_TOTAL, CHAIN, XR = 0.1975, 0.75, 10.0   # RideThroughCore.mo defaults
V_NOM, S_BASE, FREQ = 20e3, 100e6, 60.0   # arbitrary physical base for DPsim; results are in per unit
OUT = pathlib.Path(__file__).with_name("network_check.json")


def z_complex() -> complex:
    zmag = Z_TOTAL * CHAIN
    return zmag * (1 + 1j * XR) / np.hypot(1.0, XR)


def model_v(dip: float, p_pu: float, pf_model: float = 0.9) -> float:
    """The model's scalar quadratic: larger root of v^2 - vs(1+k)v + k*vs*p = 0."""
    k = (pf_model + XR * np.sqrt(1 - pf_model**2)) / np.hypot(1.0, XR) * Z_TOTAL * CHAIN
    b = dip * (1 + k)
    disc = b * b - 4 * k * dip * p_pu
    return float("nan") if disc < 0 else 0.5 * (b + np.sqrt(disc))


def exact_v(dip: float, p_pu: float, pf: float) -> float:
    z = z_complex()
    s_rated = 1.0 * (1 + 1j * np.tan(np.arccos(pf)))
    vs = dip * (1 + z * np.conj(s_rated))                    # tap-set so rated load sees 1.0 pu
    s = p_pu * (1 + 1j * np.tan(np.arccos(pf)))
    v = 0.9 + 0j
    for _ in range(500):                                       # fixed point on V = Vs - Z * conj(S/V)
        v_new = vs - z * np.conj(s / v)
        if abs(v_new - v) < 1e-13:
            break
        v = 0.5 * v + 0.5 * v_new
    ok = abs(v - (vs - z * np.conj(s / v))) < 1e-8
    return float(abs(v)) if ok else float("nan")


def dpsim_v(dip: float, p_pu: float, pf: float) -> float:
    z = z_complex()
    zbase = V_NOM**2 / S_BASE
    s_rated = 1.0 * (1 + 1j * np.tan(np.arccos(pf)))
    vs_pu = dip * abs(1 + z * np.conj(s_rated))
    n1, n2 = d.sp.SimNode("n1", d.PhaseType.Single), d.sp.SimNode("n2", d.PhaseType.Single)
    ext = d.sp.ph1.NetworkInjection("slack", d.LogLevel.off)
    ext.set_parameters(vs_pu * V_NOM); ext.set_base_voltage(V_NOM); ext.modify_power_flow_bus_type(d.PowerflowBusType.VD)
    line = d.sp.ph1.PiLine("line", d.LogLevel.off)
    line.set_parameters(z.real * zbase, z.imag * zbase / (2 * np.pi * FREQ), 1e-12, 1e-12); line.set_base_voltage(V_NOM)
    ld = d.sp.ph1.Load("ld", d.LogLevel.off)
    ld.set_parameters(p_pu * S_BASE, p_pu * S_BASE * np.tan(np.arccos(pf)), V_NOM); ld.modify_power_flow_bus_type(d.PowerflowBusType.PQ)
    ext.connect([n1]); line.connect([n1, n2]); ld.connect([n2])
    sim = d.Simulation("nc", d.LogLevel.off)
    sim.set_system(d.SystemTopology(FREQ, [n1, n2], [ext, line, ld])); sim.set_domain(d.Domain.SP); sim.set_solver(d.Solver.NRP)
    sim.set_time_step(1.0); sim.set_final_time(2.0); sim.run()
    v1, v2 = n1.attr("v").get()[0][0] / V_NOM, n2.attr("v").get()[0][0] / V_NOM
    s_calc = v2 * np.conj((v1 - v2) / z)                       # power the line actually delivers at the solved voltage
    s_want = p_pu * (1 + 1j * np.tan(np.arccos(pf)))
    return float(abs(v2)) if abs(s_calc - s_want) < 1e-3 else float("nan")   # DPsim returns its last iterate when NR fails


def summary(rows: list[dict]) -> None:
    ok = [r for r in rows if not np.isnan(r["v_exact"])]
    dp = np.array([abs(r["v_dpsim"] - r["v_exact"]) for r in ok])
    err = np.array([r["v_model"] - r["v_exact"] for r in ok])
    ghost = [r for r in rows if np.isnan(r["v_exact"]) and not np.isnan(r["v_model"])]
    print(f"\nDPsim vs exact: max |diff| {dp.max():.1e} over {len(ok)} solvable cases; DPsim also fails to converge on "
          f"{sum(np.isnan(r['v_dpsim']) for r in rows if np.isnan(r['v_exact']))}/{len(rows) - len(ok)} unsolvable ones")
    print(f"model - exact: mean {err.mean():+.3f}, max {err.max():+.3f} pu (positive = model voltage too high)")
    print(f"cases with NO physical operating point where the model still returns a voltage: {len(ghost)}/{len(rows) - len(ok)}")


def main() -> None:
    rows = []
    for pf in (0.9, 0.98):
        for p in (0.5, 0.85, 1.0):
            for dip in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
                rows.append({"pf_load": pf, "p_pu": p, "dip_pu": dip, "v_model": model_v(dip, p),
                             "v_exact": exact_v(dip, p, pf), "v_dpsim": dpsim_v(dip, p, pf)})
    OUT.write_text(json.dumps(rows, indent=1))
    print(" pf    P   dip | model  exact  dpsim | model-exact  dpsim-exact")
    for r in rows:
        print(f"{r['pf_load']:.2f} {r['p_pu']:.2f} {r['dip_pu']:.1f} | {r['v_model']:.3f}  {r['v_exact']:.3f}  {r['v_dpsim']:.3f} |"
              f" {r['v_model'] - r['v_exact']:+.3f}      {r['v_dpsim'] - r['v_exact']:+.4f}")
    summary(rows)


if __name__ == "__main__":
    main()
