"""Julia vs the Modelica simulator on one rack group + the voltage chain. Julia is a from-the-equations re-implementation (crosscheck/rack_group.jl).
Cooling power and the AI swing are fed to Julia from the Modelica trace (they are not what is compared). Usage: OM_IMAGE=... python3 -m crosscheck.run_crosscheck"""
import subprocess, sys, pathlib, numpy as np
from dataclasses import replace
from sim import runner, scenario as S

HERE = pathlib.Path(__file__).resolve().parent; WORK = HERE / "work"; WORK.mkdir(exist_ok=True)
BASE = replace(S.GRID_FRIENDLY, transfer_threshold_pu=0.10, relay_pickup_pu=0.05, legacy_load_frac=0.0, count_n=0, n_groups=1, outdoor_temp_c=25.0)
SCENARIOS = {"deep_0.30_277V": dict(dip_depth_pu=0.30, dip_duration_s=0.20, supply_voltage_v=277.0, faulted_phase_frac=1.0),
             "partial_0.60_2of3": dict(dip_depth_pu=0.60, dip_duration_s=0.10, supply_voltage_v=277.0, faulted_phase_frac=2 / 3),
             "edge_0.80_208V": dict(dip_depth_pu=0.80, dip_duration_s=0.30, supply_voltage_v=208.0, faulted_phase_frac=1.0),
             "no_trip_0.80_277V": dict(dip_depth_pu=0.80, dip_duration_s=0.30, supply_voltage_v=277.0, faulted_phase_frac=1.0)}

def params(sc, tstop):
    p_it = 120e6; cs = max(0.4 * sc.cooling_share_25c, sc.cooling_share_25c * (1 + 0.04 * (sc.outdoor_temp_c - 25.0)))
    n_racks = p_it / (sc.shelves_per_rack * 18000.0); derate = max(0.3, (1 - 0.025 * sc.battery_age_yr) * 1.0)   # 25 C: temperature derate 1.0
    seq = sc.dip_sequence(); d = dict(p_it=p_it, workload=sc.workload, ptot=p_it * sc.workload + cs * p_it, pf=0.9, xr=sc.x_over_r, ztot=sc.z_total_pct / 100,
        chain=sc.chain_loading_frac, soc0=sc.battery_soc0, bbu_w=n_racks * sc.bbu_modules_per_rack * 3000.0,
        bbu_j=n_racks * sc.bbu_modules_per_rack * 200 * 3600 * derate, spread=sc.psu_trip_spread_frac, uvdelay=sc.psu_uv_delay_s, supply=sc.supply_voltage_v,
        faulted=sc.faulted_phase_frac, restart_delay=sc.psu_restart_delay_s, handback=sc.handback_delay_s, ramp=sc.ramp_back_s, tau=sc.recovery_tau_s,
        os=sc.overshoot_pu, ndip=len(seq), stop=tstop)
    for i, (a, b, c) in enumerate(seq, 1): d[f"dip_start{i}"], d[f"dip_dur{i}"], d[f"dip_depth{i}"] = a, b, c
    return d

def edges(t, x, rising=True):
    i = np.nonzero(np.diff((x > 0.5).astype(int)) == (1 if rising else -1))[0]; return [round(float(t[k + 1]), 4) for k in i]

def compare(name, kw):
    sc = replace(BASE, **kw); runner.run(sc, tag=f"cc_{name}"); m = runner._read_csv(runner.BUILD / f"cc_{name}_res.csv"); t = m["time"]
    (WORK / f"{name}_params.txt").write_text("\n".join(f"{k}={v}" for k, v in params(sc, float(t[-1])).items()))
    (WORK / f"{name}_in.csv").write_text("t,p_cool,p_swing\n" + "\n".join(f"{a},{b},{c}" for a, b, c in zip(t, m["p_cooling_w"], m["p_swing_w"])))
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{WORK}:/work", "-v", f"{HERE}:/src", "julia:1.11", "julia", "/src/rack_group.jl",
                        f"/work/{name}_params.txt", f"/work/{name}_in.csv", f"/work/{name}_out.csv"], capture_output=True, text=True)
    if r.returncode: print(r.stderr[-1500:]); raise SystemExit(1)
    rows = np.genfromtxt(WORK / f"{name}_out.csv", delimiter=",", names=True); jt = rows["time"]
    mi = lambda col: np.interp(jt, t, m[col])
    res = {}
    # A step in voltage is sampled as two points at the same instant in the Modelica trace, so a 1 ms comparison at the step itself differs by the
    # full step height whatever the model does. Mask +-1.5 ms around each dip start and clear; the edge TIMES are compared separately.
    edges_t = [x for a, b, _ in sc.dip_sequence() for x in (a, a + b)]; keep = np.ones_like(jt, bool)
    for x in edges_t: keep &= np.abs(jt - x) > 0.0015
    res["v_sdp max|d| (pu)"] = float(np.max(np.abs(rows["v_sdp"] - mi("v_sdp_pu"))[keep]))
    res["v_source max|d| (pu)"] = float(np.max(np.abs(rows["v_source"] - mi("v_source_pu"))[keep]))
    pg = mi("p_grid_w"); res["p_grid rms rel"] = float(np.sqrt(np.mean((rows["p_grid"] - pg) ** 2)) / np.abs(pg).max())
    res["p_grid energy rel d"] = float((np.trapezoid(rows["p_grid"], jt) - np.trapezoid(pg, jt)) / np.trapezoid(pg, jt))
    res["e_holdup rms rel"] = float(np.sqrt(np.mean((rows["e_holdup"] - mi("e_holdup_j")) ** 2)) / max(np.abs(mi("e_holdup_j")).max(), 1))
    res["soc end d"] = float(rows["soc"][-1] - m["soc"][-1])
    ev = {}
    for lab, jcol, mcol, rising in (("bbu takeover", rows["bbu_active"], m["bbu_active"], True), ("bbu hand-back", rows["bbu_active"], m["bbu_active"], False)):
        ev[lab] = (edges(jt, jcol, rising)[:2], edges(t, mcol, rising)[:2])
    jtrip = jt[np.argmax(rows["trip"] > 0.5)] if (rows["trip"] > 0.5).any() else None; mtrip = t[np.argmax(m["psu_tripped_frac"] > 0.5)] if (m["psu_tripped_frac"] > 0.5).any() else None
    ev["psu trip(>50%)"] = ([round(float(jtrip), 4)] if jtrip is not None else [], [round(float(mtrip), 4)] if mtrip is not None else [])
    return res, ev

if __name__ == "__main__":
    for name, kw in SCENARIOS.items():
        res, ev = compare(name, kw); print(f"\n=== {name}")
        for k, v in res.items(): print(f"   {k:24} {v:+.5f}")
        for k, (j, mm) in ev.items(): print(f"   {k:16} julia {j}  modelica {mm}")
