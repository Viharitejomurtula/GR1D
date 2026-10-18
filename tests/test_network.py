"""Tests for the Bayesian network (ridethrough/network/graph.py and sampler.py).

What this file is
    Checks that the specification files assemble into a valid DAG, that ancestral sampling reproduces
    the root probabilities, the table and equation rules and the implied-correlation model, and that
    conditioning (query) behaves.

Reads (read-only)
    data_bayesian-network/network/ specification files and the driver fit outputs.

Writes
    nothing.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from ridethrough.drivers import implied
from ridethrough.network import graph, sampler

N = 100_000


@pytest.fixture(scope="module")
def spec() -> dict:
    """All specification files (graph.load_spec)."""
    return graph.load_spec()


@pytest.fixture(scope="module")
def g(spec) -> nx.DiGraph:
    """The assembled network."""
    return graph.build_graph(spec)


@pytest.fixture(scope="module")
def draws(spec, g) -> pd.DataFrame:
    """N joint draws at the nominal case."""
    return sampler.sample_network(N, 1, spec=spec, g=g)


def test_graph_is_valid_dag_with_every_node(spec, g):
    """No cycles, every node has a rule, and every root, master.csv node and edges.csv edge is present."""
    assert graph.validate(g) == []
    assert set(spec["roots"]) | set(spec["master"].index) == set(g.nodes)
    for _, r in spec["edges"].iterrows():
        assert g.has_edge(r["parent"], r["child"])


def test_unquantified_edges_are_the_placeholder_shifts(g):
    """Only edges.csv links with no number behind them are structure-only."""
    assert graph.unquantified_edges(g) == [
        ("capacity_age_factor", "usable_energy_factor"), ("converter_loading", "converter_overload_s"),
        ("n_dips", "dip_gap_s"), ("outdoor_temp_c", "converter_overload_s"),
        ("soc_estimate_error", "usable_energy_factor")]


def test_sampling_is_reproducible(spec, g):
    """Same seed gives identical draws; a different seed does not."""
    a = sampler.sample_network(2_000, 5, spec=spec, g=g)
    b = sampler.sample_network(2_000, 5, spec=spec, g=g)
    c = sampler.sample_network(2_000, 6, spec=spec, g=g)
    pd.testing.assert_frame_equal(a, b)
    assert not a.equals(c)


def test_root_frequencies_match_roots_yaml(spec, draws):
    """Each categorical root's sampled shares are within 0.01 of roots.yaml."""
    for name, r in spec["roots"].items():
        p = pd.Series(r["categories"], dtype=float)
        got = draws[name].value_counts(normalize=True).reindex(p.index, fill_value=0.0)
        np.testing.assert_allclose(got.to_numpy(), (p / p.sum()).to_numpy(), atol=0.01)


def test_table_and_equation_rules(spec, draws):
    """Table children equal their category centre; converter_loading follows its equation."""
    for (parent, child), tab in graph.table_centres(spec).items():
        if child == "osc_amp" or parent == "season":
            continue
        expected = draws[parent].map(tab).to_numpy(dtype=float)
        np.testing.assert_array_equal(draws[child].to_numpy(), expected)
    loading = draws["load_fraction"] / (1 - draws["units_offline"] / graph.N_UNITS)
    np.testing.assert_allclose(draws["converter_loading"], loading)


def test_workload_shifts_osc_amp_mean(spec, draws):
    """osc_amp mean per workload type is its tables.csv centre (within 0.005)."""
    tab = graph.table_centres(spec)[("workload_type", "osc_amp")]
    for cat, centre in tab.items():
        assert abs(draws.loc[draws["workload_type"] == cat, "osc_amp"].mean() - centre) < 0.005


def test_factor_correlations_match_implied_monte_carlo(spec, draws):
    """Within season JJA, factor correlations match implied.monte_carlo_corr (same model) within 0.03."""
    inp = spec["implied"]; case = implied.NOMINAL_CASE
    s, _ = implied.build_s(inp["s_long"], inp["master"], case["attenuation"], case["psu_k"])
    nz = implied.build_noise(inp["noise"], inp["master"], list(s.index), 1, 1)["sd"]
    mc = implied.monte_carlo_corr(inp, s, case, "JJA", nz, n=N)
    pairs = [("storage_resistance_pu", "capacity_age_factor"), ("storage_resistance_pu", "dclink_capacitance_factor"),
             ("capacity_age_factor", "psu_holdup_ms")]
    jja = draws[draws["season"] == "JJA"]
    for a, b in pairs:
        assert abs(jja[a].corr(jja[b]) - mc.loc[a, b]) < 0.03, (a, b)


def test_clip_holds_master_range(spec, g):
    """clip=True keeps every continuous node inside master.csv low-high."""
    d = sampler.sample_network(20_000, 2, spec=spec, g=g, clip=True)
    for node, r in spec["master"].iterrows():
        assert d[node].between(r["low"], r["high"]).all(), node


def test_query_conditions_on_evidence(spec, g):
    """Evidence on a root shifts its children: summer is hotter than winter, a failed breaker gives
    the 317 ms clearing time, and an interval keeps only matching rows."""
    hot, acc = sampler.query({"season": "JJA"}, n=40_000, seed=3, spec=spec, g=g)
    cold, _ = sampler.query({"season": "DJF"}, n=40_000, seed=3, spec=spec, g=g)
    assert 0.2 < acc < 0.3 and hot["outdoor_temp_c"].mean() > cold["outdoor_temp_c"].mean() + 10
    bf, _ = sampler.query({"protection_failure": "breaker_failure"}, n=40_000, seed=3, spec=spec, g=g)
    assert (bf["dip_duration_ms"] == 317).all()
    old, _ = sampler.query({"equipment_age_years": (12.0, 15.0)}, n=40_000, seed=3, spec=spec, g=g)
    assert old["equipment_age_years"].between(12.0, 15.0).all()
    with pytest.raises(ValueError):
        sampler.query({"not_a_node": 1}, n=100, spec=spec, g=g)
