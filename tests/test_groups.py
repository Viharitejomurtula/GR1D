"""Item 5: the facility as several parallel rack groups. Needs the toolchain (OM_IMAGE)."""
import os
from dataclasses import replace
import numpy as np, pytest
from sim import runner, scenario as S

pytestmark = pytest.mark.skipif(not os.environ.get("OM_IMAGE") and not os.environ.get("GR1D_NATIVE"), reason="OpenModelica toolchain not configured")

def _run(sc, tag):
    g = runner.run(sc, tag=tag); return g, runner._read_csv(runner.BUILD / f"{tag}_res.csv")

DIP = dict(dip_depth_pu=0.3, dip_duration_s=0.2, psu_uv_delay_s=0.0, transfer_threshold_pu=0.10, relay_pickup_pu=0.05)

@pytest.mark.parametrize("n", [3, 6])
def test_identical_groups_equal_one_lumped_group(n):
    base = replace(S.GRID_FRIENDLY, **DIP)
    g1, d1 = _run(base, "grp_one"); gn, dn = _run(replace(base, n_groups=n), f"grp_n{n}")
    t = d1["time"]
    for ch in ("p_grid_w", "p_server_w", "p_psu_w", "p_bbu_w"):
        # compare energy and spot values away from the sub-millisecond collapse edge, whose exact solver step differs between builds
        e1, en = np.trapezoid(d1[ch], t), np.trapezoid(np.interp(t, dn["time"], dn[ch]), t)
        assert en == pytest.approx(e1, rel=2e-3, abs=1e3), (ch, e1, en)
        for tt in (1.05, 1.15, 1.3, 2.0, 5.0, 14.0):
            assert np.interp(tt, dn["time"], dn[ch]) == pytest.approx(np.interp(tt, t, d1[ch]), rel=2e-3, abs=1e4), (ch, tt)

def test_group_with_less_holdup_hands_to_the_battery_sooner():
    sc = replace(S.GRID_FRIENDLY, n_groups=3, grp_holdup_cv=0.5, **DIP)
    g, d = _run(sc, "grp_hold"); t = d["time"]; scales = sc.group_arrays()["grp_holdup_scale"][:3]
    took = []
    for k in (1, 2, 3):
        i = np.nonzero(np.diff(d[f"grp[{k}].bbu_active"]) > 0.5)[0]; assert i.size, f"group {k} never handed to the battery"
        took.append((t[i[0] + 1] - 1.0) * 1e3)
    assert [x for _, x in sorted(zip(scales, took))] == sorted(took)                      # takeover time rises with hold-up health
    # closed form: depletion to the BBU level takes 0.375 * 60 J * scale / (0.85 * 3000 W) = 8.8 ms * scale, plus ~3 ms of detection/takeover delay
    pred = [8.82 * s + 3.0 for s in scales]
    assert np.allclose(took, pred, rtol=0.35), (took, pred)

def test_an_undersized_group_battery_is_visible_only_with_groups():
    base = replace(S.GRID_FRIENDLY, **DIP)
    _, lumped = _run(base, "grp_lump")
    _, mixed = _run(replace(base, n_groups=3, grp_bbu_cv=0.6), "grp_mix")                  # one group at 0.6 x 36 modules: cannot carry its load
    assert lumped["servers_lost_frac"].max() == 0.0
    assert 0.2 < mixed["servers_lost_frac"].max() < 0.5                                     # about one third of the servers lose power

def test_legacy_share_is_filled_group_by_group_in_the_model():
    sc = replace(S.LEGACY_UPS, n_groups=6, legacy_load_frac=0.30, dip_depth_pu=0.5, dip_duration_s=0.1, relay_pickup_pu=0.85, relay_delay_s=0.0)
    g, d = _run(sc, "grp_leg")
    avail_end = [d[f"grp[{k}].avail"][-1] for k in range(1, 7)]
    assert avail_end == pytest.approx([0.0, 0.2, 1.0, 1.0, 1.0, 1.0], abs=1e-6)       # 0.30 * 6 = 1.8 groups opened: one whole, 80% of the next
    assert sc.legacy_fractions() == pytest.approx([1.0, 0.8, 0.0, 0.0, 0.0, 0.0])
    assert d["facility_available_frac"][-1] == pytest.approx(0.70, abs=1e-6)
