"""Tests for ridethrough/pipeline: joint sampler, Shapley estimator, and the end-to-end run.

What this file is
    Checks that the joint sampler fills only the block columns and keeps the design elsewhere, keeps the
    network's conditioning (breaker problems give longer sags, fault type sets faulted phases), is
    reproducible; that the Shapley estimator is exact on functions with known answers; and that a small
    end-to-end run returns the documented structure. The end-to-end test uses the committed surrogate
    (surrogate/models/v1) and needs torch.

Reads (read-only): the network specification files, surrogate/models/v1.
Writes: nothing.
"""
from __future__ import annotations

import numpy as np
import pytest

from ridethrough.pipeline import drivers, joint
from sim.scenario import FIELD_ORDER, GRID_FRIENDLY

N = 4000


@pytest.fixture(scope="module")
def sample():
    return joint.sample_joint(N, seed=3)


def test_columns_and_reproducible(sample):
    sc, roots = sample
    assert list(sc.columns) == list(FIELD_ORDER) and len(sc) == len(roots) == N
    sc2, _ = joint.sample_joint(N, seed=3)
    assert sc.equals(sc2)
    assert not sc.equals(joint.sample_joint(N, seed=4)[0])


def test_only_block_columns_vary(sample):
    sc, _ = sample
    varying = {c for c in sc.columns if sc[c].nunique() > 1}
    owned = {c for b in joint.BLOCKS for c in b.columns} | set(joint.NUISANCE)
    assert varying <= owned
    base = dict(zip(FIELD_ORDER, GRID_FRIENDLY.to_vector()))
    for c in set(sc.columns) - owned:
        assert (sc[c] == base[c]).all(), c


def test_network_conditioning_is_kept(sample):
    sc, roots = sample
    dur = sc["dip_duration_s"].groupby(roots["protection_failure"]).min()
    assert dur["normal"] < dur["breaker_failure"] and dur["normal"] < 0.07 and dur["breaker_failure"] >= 10 / 60 - 1e-9
    phase = sc["faulted_phase_frac"].groupby(roots["fault_type"]).first()
    assert phase["SLG"] == pytest.approx(1 / 3) and phase["3LG"] == 1.0
    assert set(sc["second_dip"].unique()) <= {0.0, 1.0}
    assert (sc["second_dip"] == (roots["n_dips"] >= 2)).all()


def test_values_stay_in_simulator_ranges(sample):
    sc, _ = sample
    assert sc["workload"].between(0.5, 1.0).all() and sc["battery_age_yr"].between(0, 14).all()
    assert sc["reclose_gap_s"].between(0.25, 5.0).all() and sc["compressor_restart_s"].between(100, 600).all()
    assert sc["swing_freq_hz"].between(0.2, 3.0).all()


def test_to_scenarios_round_trip(sample):
    sc, _ = sample
    s = joint.to_scenarios(sc.head(3))[1]
    assert isinstance(s.shelves_per_rack, int) and isinstance(s.second_dip, bool)
    assert s.dip_depth_pu == pytest.approx(sc["dip_depth_pu"].iloc[1])


def test_shapley_is_exact_for_additive_and_splits_interaction():
    rng = np.random.default_rng(0)
    fg, bg = rng.normal(size=(300, 4)), rng.normal(size=(300, 4))
    players = [[0], [1], [2, 3]]
    f = lambda z: np.column_stack([2 * z[:, 0] + 0 * z[:, 1] - 3 * z[:, 2] + z[:, 3], z[:, 0] * z[:, 1]])
    phi = drivers.shapley(f, fg, bg, players, n_perm=20, rng=rng)
    assert phi[:, 0, 0] == pytest.approx(2 * (fg[:, 0] - bg[:, 0]))
    assert phi[:, 1, 0] == pytest.approx(0, abs=1e-12)
    assert phi[:, 2, 0] == pytest.approx(-3 * (fg[:, 2] - bg[:, 2]) + (fg[:, 3] - bg[:, 3]))
    full, start = f(fg), f(np.column_stack([bg[:, 0], bg[:, 1], bg[:, 2], bg[:, 3]]))
    assert phi.sum(1) == pytest.approx(full - start)                 # efficiency
    assert phi[:, 0, 1] + phi[:, 1, 1] == pytest.approx(fg[:, 0] * fg[:, 1] - bg[:, 0] * bg[:, 1])
    assert np.abs(phi[:, 2, 1]).max() == 0                           # a player the output ignores gets nothing


def test_end_to_end_small_run():
    pytest.importorskip("torch")
    from ridethrough.pipeline import run
    r = run.run(n=1500, seed=1, design="grid_friendly", events=150, perms=2)
    assert r["headline_output"] in r["outputs"] and r["unit"].startswith("one grid event")
    for g, n_blocks in (("A", len(joint.groups("A"))), ("B", len(joint.groups("B")))):
        rows = r["rankings"][g]["by_output"]["p_fail"]
        assert len(rows) == n_blocks and [x["rank"] for x in rows] == list(range(1, n_blocks + 1))
        assert sum(x["share"] for x in rows) == pytest.approx(1.0)
    p = r["performance"]["fail_probability"]
    assert 0.0 <= p["mean"] <= 1.0 and p["mc_95ci"][0] <= p["mean"] <= p["mc_95ci"][1]
    assert set(r["lifts"]) == {b.name for b in joint.BLOCKS}
    assert "Probability an event fails" in run.to_markdown(r)
