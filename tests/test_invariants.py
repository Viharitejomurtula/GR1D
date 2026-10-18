"""Item 1: the model must never report an impossible state. Needs the toolchain (OM_IMAGE)."""
import os
from dataclasses import replace
import numpy as np, pytest
from sim import runner, scenario as S

pytestmark = pytest.mark.skipif(not os.environ.get("OM_IMAGE") and not os.environ.get("GR1D_NATIVE"), reason="OpenModelica toolchain not configured")

def test_the_random_scenario_that_drove_hold_up_negative_now_stays_physical():
    rng = np.random.default_rng(7); sc = [S.sample(rng) for _ in range(7)][6]       # 6 groups, 0.21 pu dip: e_holdup went below zero before the clamp
    g = runner.run(sc, tag="inv_a"); d = runner._read_csv(runner.BUILD / "inv_a_res.csv")
    assert g.numerics_ok, g.numerics_note
    assert all(d[k].min() >= -1e-3 for k in d if k.endswith("e_holdup_j"))

def test_an_undersized_battery_drains_holdup_to_zero_but_not_below():
    sc = replace(S.GRID_FRIENDLY, n_groups=3, grp_bbu_cv=0.6, dip_depth_pu=0.3, dip_duration_s=0.2, transfer_threshold_pu=0.10, relay_pickup_pu=0.05)
    g, d = runner.run(sc, tag="inv_b"), runner._read_csv(runner.BUILD / "inv_b_res.csv")
    assert min(d[k].min() for k in d if k.endswith("e_holdup_j")) >= -1e-3 and g.numerics_ok

def test_invariant_checker_flags_a_bad_trace():
    d = {"time": np.arange(5.0), "e_holdup_j": np.array([1.0, 0.5, -100.0, 0.0, 0.0]), "soc": np.array([0.9, 0.9, 1.2, 0.9, 0.9]),
         "v_sdp_pu": np.ones(5), "p_grid_w": np.ones(5)}
    bad = runner._invariants(d); assert any("hold-up" in b for b in bad) and any("state of charge" in b for b in bad)
