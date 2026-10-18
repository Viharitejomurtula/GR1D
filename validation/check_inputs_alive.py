"""Wiring check: perturb each Scenario field in several contexts and confirm the simulated traces change. A field that never
changes any trace in any context is dead (sampled by the generator and learned by the surrogate, but ignored by the physics).
Contexts are chosen so conditional inputs (relay, counting, kinetic ride-through, restart delays) are exercised."""
import sys, numpy as np
from dataclasses import replace, fields
from sim import runner, scenario as S, events as E

CONTEXTS = {
    "deep_single": replace(S.LEGACY_UPS, dip_depth_pu=0.45, dip_duration_s=0.12, horizon_s=200.0, legacy_load_frac=0.5, faulted_phase_frac=2/3),
    "shallow_single": replace(S.GRID_FRIENDLY, dip_depth_pu=0.80, dip_duration_s=0.3, relay_pickup_pu=0.85, legacy_load_frac=0.5),
    "sequence_counting": replace(E.nerc_2024(S.GRID_FRIENDLY), count_n=3, count_min_dur_s=0.02, horizon_s=0.0),
    "kinetic_mid": replace(S.GRID_FRIENDLY, dip_depth_pu=0.30, dip_duration_s=0.09, vfd_kinetic=True, horizon_s=40.0),
    # Exercises what the first four contexts cannot: a second dip, a latched transfer that runs the battery down to
    # empty (servers lose power, then restart with a surge), a counting scheme near its thresholds, and a drive fault
    # followed by an auto-restart.
    "second_dip": replace(S.LEGACY_UPS, dip_depth_pu=0.5, dip_duration_s=0.06, second_dip=True, reclose_gap_s=0.8, horizon_s=30.0),
    "battery_runs_out": replace(S.GRID_FRIENDLY, dip_depth_pu=0.5, dip_duration_s=0.06, extra_dips=((10.0, 0.06, 0.5),), count_n=2,
                                count_window_s=60.0, bbu_modules_per_rack=6, horizon_s=170.0),
    "counting_edge": replace(S.GRID_FRIENDLY, dip_depth_pu=0.5, dip_duration_s=0.06, extra_dips=((40.0, 0.06, 0.5),), count_n=2,
                             count_min_dur_s=0.15, count_window_s=60.0, horizon_s=60.0),
    # BBU too small to hold the busbar: servers lose power, the PSUs restart, and the restart surge appears.
    "undersized_bbu": replace(S.GRID_FRIENDLY, dip_depth_pu=0.40, dip_duration_s=0.2, bbu_modules_per_rack=6, horizon_s=30.0),
    "drive_fault": replace(S.GRID_FRIENDLY, dip_depth_pu=0.30, dip_duration_s=0.10, vfd_kinetic=False, cooling_ride_through_s=0.02,
                           drive_restart_s=5.0, compressor_restart_s=10.0, horizon_s=40.0),
}
OVERRIDES = {  # field -> perturbation chosen to cross a threshold in the context that exercises it
    "count_window_s": lambda v: v * 0.5, "count_min_dur_s": lambda v: v * 1.3 if v > 0 else 0.5, "cooling_ride_through_s": lambda v: v * 15.0,
    "battery_soc0": lambda v: 0.4, "battery_age_yr": lambda v: 9.0, "battery_temp_c": lambda v: 5.0,
}
def perturbed(sc, f):
    v = getattr(sc, f.name)
    if f.name in OVERRIDES: return replace(sc, **{f.name: OVERRIDES[f.name](v)})
    if f.name == "extra_dips": return sc
    if isinstance(v, bool): return replace(sc, **{f.name: not v})
    if isinstance(v, int):  return replace(sc, **{f.name: v + (2 if f.name != "count_n" else 1)})
    if f.name in ("battery_soc0", "workload", "faulted_phase_frac", "legacy_load_frac", "cooling_vfd_frac", "cooling_compressor_frac", "cooling_fan_frac", "swing_size_frac"):
        return replace(sc, **{f.name: (v * 0.8 if v > 0.3 else v + 0.15)})
    return replace(sc, **{f.name: (v * 1.3 if abs(v) > 1e-9 else 0.5)})

def signature(sc, tag):
    """Per-channel normalised so a small channel (soc ~ 1) is not drowned by a large one (p_grid ~ 1e8 W); plus whole-trace
    integrals and extrema, which see short events that a 600-point resample can step over."""
    runner.run(sc, tag=tag); d = runner._read_csv(runner.BUILD / f"{tag}_res.csv"); t = d["time"]
    keys = ("v_sdp_pu", "p_grid_w", "i_grid_pu", "p_cooling_w", "p_server_w", "soc", "e_holdup_j", "servers_lost_power", "cooling_available")
    parts = []
    for k in keys:
        if k not in d: continue
        x = d[k]; sc_ = (np.abs(x).max() or 1.0)
        parts.append(np.interp(np.linspace(0, t[-1], 600), t, x) / sc_)
        parts.append(np.array([np.trapezoid(x, t) / (t[-1] * sc_), x.min() / sc_, x.max() / sc_, x[-1] / sc_]))
    return np.concatenate(parts)

if __name__ == "__main__":
    dead = []
    base = {n: signature(sc, f"alive_base_{n}") for n, sc in CONTEXTS.items()}
    print('contexts:', list(CONTEXTS), flush=True)
    only = set(sys.argv[1:])
    for f in fields(S.Scenario):
        if f.name in ("extra_dips", "horizon_s") or (only and f.name not in only): continue
        alive = False
        for n, sc in CONTEXTS.items():
            sig = signature(perturbed(sc, f), f"alive_{n}")
            if not np.allclose(sig, base[n], rtol=1e-7, atol=1e-7): alive = True; break
        print(f"{f.name:28} {'alive' if alive else 'DEAD in all contexts'}", flush=True)
        if not alive: dead.append(f.name)
    print("DEAD:", dead)
