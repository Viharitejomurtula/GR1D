"""Item 4: BBU shares the load with the PSUs that are still up. Needs the toolchain (OM_IMAGE)."""
import os
from dataclasses import replace
import numpy as np, pytest
from sim import runner, scenario as S
from validation.cases import CASES

pytestmark = pytest.mark.skipif(not os.environ.get("OM_IMAGE") and not os.environ.get("GR1D_NATIVE"), reason="OpenModelica toolchain not configured")

def _run(sc, tag):
    g = runner.run(sc, tag=tag); return g, runner._read_csv(runner.BUILD / f"{tag}_res.csv")

def test_grouped_facility_matches_lumped_when_the_battery_shares():
    sc = CASES["facility_B"]["sc"]
    gl, _ = _run(sc, "sh_lump"); gg, _ = _run(replace(sc, n_groups=6), "sh_grp")
    assert (1 - gg.final_power_frac) == pytest.approx(1 - gl.final_power_frac, abs=0.02)         # was 72% vs 24.5% with the all-or-none battery
    gold, _ = _run(replace(sc, n_groups=6, bbu_sharing=False), "sh_old")
    assert (1 - gold.final_power_frac) > 0.5                                                       # the old behaviour is still reproducible for comparison

def test_battery_takes_over_once_and_does_not_chatter():
    _, d = _run(replace(CASES["facility_B"]["sc"], n_groups=6), "sh_chat"); t = d["time"]
    for k in range(1, 7):
        rises = np.nonzero(np.diff(d[f"grp[{k}].bbu_active"]) > 0.5)[0]
        assert len(rises) <= 1, (k, [round(t[i + 1], 3) for i in rises])

def test_psus_and_battery_together_meet_the_demand_while_psus_are_partly_down():
    _, d = _run(replace(CASES["facility_B"]["sc"], n_groups=3), "sh_bal"); t = d["time"]
    i = np.searchsorted(t, 3.0)                                                                     # PSUs 2/3 up, tripped third not yet restarted
    full = [k for k in (1, 2, 3) if d[f"grp[{k}].avail"][i] > 0.99]; assert full                  # groups whose load is intact (the legacy group's is mostly gone)
    for k in full:
        psu, bbu, srv = d[f"grp[{k}].p_psu_w"][i], d[f"grp[{k}].p_bbu_w"][i], d[f"grp[{k}].p_server_w"][i]
        assert psu > 0 and bbu > 0                                                                  # both are carrying load: sharing
        assert psu + bbu == pytest.approx(srv, rel=2e-3)

def test_battery_hands_back_after_the_tripped_psus_restart():
    _, d = _run(replace(CASES["facility_B"]["sc"], n_groups=3), "sh_back")
    assert d["bbu_active_frac"].max() > 0.9 and d["bbu_active_frac"][-1] == 0.0

def test_ablation_switch_reproduces_the_old_all_or_none_numbers():
    g, _ = _run(replace(CASES["facility_B"]["sc"], bbu_sharing=False), "sh_abl")
    assert (1 - g.final_power_frac) == pytest.approx(0.245, abs=0.005)
