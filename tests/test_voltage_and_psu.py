"""Item 6 (voltage solution) and item 9 (PSU capability vs input voltage). Need the toolchain (OM_IMAGE)."""
import os
from dataclasses import replace
import numpy as np, pytest
from sim import runner, scenario as S
import sim.constants as C

pytestmark = pytest.mark.skipif(not os.environ.get("OM_IMAGE") and not os.environ.get("GR1D_NATIVE"), reason="OpenModelica toolchain not configured")

def _trace(sc, tag):
    g = runner.run(sc, tag=tag); return g, runner._read_csv(runner.BUILD / f"{tag}_res.csv")

def _closed_form_v(vs, p, k):
    disc = vs ** 2 * (1 + k) ** 2 - 4 * k * vs * p
    return 0.5 * (vs * (1 + k) + np.sqrt(np.maximum(disc, 0.0)))

@pytest.mark.parametrize("depth", [0.9, 0.7, 0.5, 0.3])
def test_solver_voltage_equals_physical_root_of_quadratic(depth):
    """Independent plain-Python solution of v^2 - vs(1+k)v + k*vs*p = 0 (larger root) vs the Modelica trace, whole run."""
    sc = replace(S.GRID_FRIENDLY, dip_depth_pu=depth, dip_duration_s=0.1)
    g, d = _trace(sc, f"vs_{int(depth*100)}")
    p_total = sc.workload * 120e6 + d["p_cooling_w"][0]            # = p_total_rated_w in the model
    # reconstruct k from the model's own definition
    pf, xr = 0.9, sc.x_over_r
    k = ((pf + xr * np.sqrt(1 - pf ** 2)) / np.sqrt(1 + xr ** 2)) * (sc.z_total_pct / 100.0) * sc.chain_loading_frac
    v_ref = _closed_form_v(d["v_source_pu"], d["p_grid_w"] / p_total, k)
    assert np.max(np.abs(v_ref - d["v_sdp_pu"])) < 2e-3, np.max(np.abs(v_ref - d["v_sdp_pu"]))
    assert g.numerics_ok

def test_deep_dip_stays_on_physical_branch_across_random_scenarios():
    rng = np.random.default_rng(3)
    for i in range(12):
        sc = replace(S.sample(rng), dip_depth_pu=float(rng.uniform(0.0, 0.5)))
        g, d = _trace(sc, "vs_rand"); assert g.numerics_ok, (i, g.numerics_note)

def test_psu_delivers_full_power_down_to_lockout_when_per_unit_voltage_is_low():
    # 277 V supply, 0.74 pu sag = 205 V at the PSU: above lockout, so no shortfall may drain hold-up (the old per-unit scaling
    # capped capability at 74% here and drained it).
    sc = replace(S.GRID_FRIENDLY, supply_voltage_v=277.0, dip_depth_pu=0.74, dip_duration_s=0.5, legacy_load_frac=0.0,
                 transfer_threshold_pu=0.10, relay_pickup_pu=0.05, count_n=0)
    g, d = _trace(sc, "psu_cap_hi")
    assert d["psu_enabled"].min() == 1.0
    assert d["e_holdup_j"].min() > 0.999 * d["e_holdup_j"][0]

def test_old_scaling_would_have_drained_holdup_in_the_same_case():
    sc = replace(S.GRID_FRIENDLY, supply_voltage_v=277.0, dip_depth_pu=0.74, dip_duration_s=0.5, legacy_load_frac=0.0,
                 transfer_threshold_pu=0.10, relay_pickup_pu=0.05, count_n=0, psu_cap_datasheet=False)
    g, d = _trace(sc, "psu_cap_old")
    assert d["e_holdup_j"].min() < 0.99 * d["e_holdup_j"][0]
