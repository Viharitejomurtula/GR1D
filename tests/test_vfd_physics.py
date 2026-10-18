"""VfdClass checked against closed-form energy balances. Needs the toolchain (OM_IMAGE)."""
import os
from dataclasses import replace
import numpy as np, pytest
from sim import runner, scenario as S

pytestmark = pytest.mark.skipif(not os.environ.get("OM_IMAGE") and not os.environ.get("GR1D_NATIVE"), reason="OpenModelica toolchain not configured")

C_UF_PER_KW, V_LL, UV = 130.0, 480.0, 0.70
def hand_ride_ms(h_s=0.0, kinetic=False):
    """Time from loss of rectifier conduction to the UV level, per unit of rated power (cancels): e_nom*(1-uv^2) [+ H*0.3] seconds."""
    e_per_w = 0.5 * C_UF_PER_KW * 1e-6 / 1000.0 * (1.35 * V_LL) ** 2
    return 1e3 * (e_per_w * (1 - UV ** 2) + (0.3 * h_s if kinetic else 0.0))

def _run(tag, **kw):
    sc = replace(S.GRID_FRIENDLY, dip_depth_pu=kw.pop("depth", 0.30), dip_duration_s=kw.pop("dur", 0.4), vfd_dc_uv_trip_pu=UV, **kw)
    runner.run(sc, tag=tag); d = runner._read_csv(runner.BUILD / f"{tag}_res.csv"); return d, d["time"]

def _first_change(t, x, t0=1.0):
    i = np.nonzero(np.diff(x) != 0)[0]; return (t[i[0] + 1] - t0) * 1e3 if i.size else None

def test_dc_link_ride_through_matches_energy_balance():
    d, t = _run("vfd_a", vfd_kinetic=False)
    stop_ms = _first_change(t, d["vfd_fan.mode"])
    # sensed voltage lags 1 ms and the AC drops below the DC peak slightly after t0: allow ~15%
    assert stop_ms == pytest.approx(hand_ride_ms(), rel=0.15), (stop_ms, hand_ride_ms())

def test_kinetic_ride_through_adds_h_times_f_use():
    d, t = _run("vfd_k", vfd_kinetic=True)
    comp_ms, fan_ms = _first_change(t, d["vfd_comp.mode"]), _first_change(t, d["vfd_fan.mode"])
    assert comp_ms == pytest.approx(hand_ride_ms(0.10, True), rel=0.15), comp_ms
    assert fan_ms == pytest.approx(hand_ride_ms(0.50, True), rel=0.15), fan_ms        # H = 0.5 s -> ~164 ms
    assert fan_ms > comp_ms

def test_shallow_dip_never_stops_drive():
    # AC peak stays above the DC bus at 0.9 pu, so the rectifier keeps conducting. (A brief DEEP dip still stops drives:
    # voltage recovers with tau ~65 ms, long enough for the bus to fall to the UV level.)
    d, t = _run("vfd_s", vfd_kinetic=False, dur=0.008, depth=0.90)
    assert d["vfd_fan.mode"].max() == 0 and d["vfd_comp.mode"].max() == 0

def test_compressor_waits_out_anti_short_cycle():
    d, t = _run("vfd_c", vfd_kinetic=False, dur=0.2, compressor_restart_s=100.0, horizon_s=130.0)
    restart = np.nonzero((np.diff(d["vfd_comp.mode"]) < 0))[0]
    assert restart.size and (t[restart[0] + 1] - 1.014) == pytest.approx(100.0, abs=1.0)
    fan_restart = np.nonzero(np.diff(d["vfd_fan.mode"]) < 0)[0]
    assert t[fan_restart[0] + 1] < 5.0                                                     # fans do not wait for it

def test_manual_reset_drive_stays_down_after_fault():
    # 0.4 s dip: the bus stays low longer than the 0.05 s hold, so the drive faults; with manual reset it never returns in 60 s
    d, t = _run("vfd_m", vfd_kinetic=False, dur=0.4, cooling_ride_through_s=0.05, drive_restart_s=600.0, horizon_s=60.0)
    assert d["vfd_fan.mode"].max() == 2 and d["vfd_fan.mode"][-1] == 2

def test_auto_restart_drive_returns_after_fault():
    d, t = _run("vfd_r", vfd_kinetic=False, dur=0.4, cooling_ride_through_s=0.05, drive_restart_s=1.0, horizon_s=20.0)
    assert d["vfd_fan.mode"].max() == 2 and d["vfd_fan.mode"][-1] == 0
