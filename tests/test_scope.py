"""Scope limitation: sampling stays inside the simulator's valid dip-depth band (sim.constants.VALID_DIP_DEPTH_PU)."""
import dataclasses

import numpy as np
import pytest

from sim import constants as C
from sim import scenario as S
from sim.scenario import GRID_FRIENDLY

# The production band is now the full 0-1 pu range, which leaves nothing to exclude. The scope mechanism is tested against a
# narrow band instead, so it keeps working if the band is narrowed again.
LO, HI = 0.70, 0.90


@pytest.fixture(autouse=True)
def _narrow_band(monkeypatch):
    monkeypatch.setattr(C, "VALID_DIP_DEPTH_PU", (LO, HI))


def test_sample_many_in_scope_by_default():
    scs = S.sample_many(3000, seed=1)
    assert any(s.second_dip for s in scs)
    for s in scs:
        assert s.in_scope()
        assert all(LO <= d <= HI for _, _, d in s.dip_sequence())   # second dip included


def test_in_scope_depth_is_conditioned_distribution():
    rng = np.random.default_rng(0)
    d = np.array([S.sample_dip_depth_in_scope(rng) for _ in range(20000)])
    assert d.min() >= LO and d.max() <= HI
    # Eaton/EPRI bucket 0.70-0.90 is uniform, so conditioning on the band gives uniform over it
    assert abs(d.mean() - (LO + HI) / 2) < 0.005


def test_in_scope_follows_band(monkeypatch):
    monkeypatch.setattr(C, "VALID_DIP_DEPTH_PU", (0.50, 0.80))
    rng = np.random.default_rng(0)
    d = np.array([S.sample_dip_depth_in_scope(rng) for _ in range(5000)])
    assert d.min() >= 0.50 and d.max() <= 0.80 and d.min() < 0.70   # spans two Eaton/EPRI buckets


def test_opt_out_reaches_deep_dips():
    scs = S.sample_many(3000, seed=1, in_scope_only=False)
    depths = np.array([s.dip_depth_pu for s in scs])
    assert (depths < LO).mean() > 0.2
    assert not all(s.in_scope() for s in scs)


def test_module_default_switch(monkeypatch):
    monkeypatch.setattr(S, "DEFAULT_IN_SCOPE_ONLY", False)   # what scripts/generate_dataset.py --full-depth-range sets
    assert any(s.dip_depth_pu < LO for s in S.sample_many(500, seed=2))


def test_scenario_in_scope():
    base = dataclasses.replace(GRID_FRIENDLY, dip_depth_pu=0.80, second_dip=False, extra_dips=())
    assert base.in_scope()
    assert dataclasses.replace(base, dip_depth_pu=LO).in_scope()
    assert dataclasses.replace(base, dip_depth_pu=HI).in_scope()
    assert not dataclasses.replace(base, dip_depth_pu=0.60).in_scope()
    assert not dataclasses.replace(base, dip_depth_pu=0.95).in_scope()
    assert dataclasses.replace(base, second_dip=True).in_scope()
    assert not dataclasses.replace(base, extra_dips=((1.0, 0.1, 0.5),)).in_scope()
    assert dataclasses.replace(base, extra_dips=((1.0, 0.1, 0.75),)).in_scope()


def test_sample_joint_in_scope():
    joint = pytest.importorskip("ridethrough.pipeline.joint")
    sc, roots = joint.sample_joint(3000, 0)
    assert (sc["second_dip"] > 0).any()
    assert sc["dip_depth_pu"].between(LO, HI).all()          # second dip reuses this depth
    assert roots["dip_depth_pu"].between(LO, HI).all()
    for s in joint.to_scenarios(sc.head(300)):
        assert s.in_scope()
    assert joint.scope()["dip_depth_pu"] == [LO, HI]
    assert joint.scope()["share_of_sags"] == C.IN_SCOPE_SAG_SHARE
