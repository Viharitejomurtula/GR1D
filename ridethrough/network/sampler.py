"""Ancestral sampling of the Bayesian network, and conditioning on evidence.

What this file is
    sample_network draws every node in topological order, each from its rule given its parents
    (rules in graph.py). Each row is one consistent joint draw. query conditions on evidence by
    rejection: draw, keep the rows that match, report the acceptance rate.

Reads (read-only)
    the specification files (graph.load_spec) and the driver fit outputs in
    data_bayesian-network/network/drivers/ (sample.load_fitted).

Writes
    nothing.

Assumptions
    Same as the implied-correlation model for the factors (implied.factor_values: S slopes and curves,
    noise.csv or master range / 6 noise, the case's attenuation, coupling, age spread, PSU k and
    DC-link n). Edges marked unquantified in graph.py are not applied. By default factor values are
    not clipped (as in the Monte Carlo check, so correlations match implied.py); the assumed noise
    ((high - low) / 6) then puts some draws outside master.csv's range, e.g. negative restart times.
    clip=True holds every continuous node to its master.csv low-high, which is what a simulator
    input needs, at the cost of piling mass on the range ends.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from ridethrough.drivers import fit, implied, sample
from ridethrough.network import graph


def _assumed_normal(rng: np.random.Generator, row: pd.Series, n: int) -> np.ndarray:
    """normal(typical, (high - low) / 6) clipped to low-high; rounded when the unit is a count."""
    lo, typ, hi = float(row["low"]), float(row["typical"]), float(row["high"])
    x = np.clip(rng.normal(typ, (hi - lo) / 6.0, n), lo, hi)
    return np.round(x) if "count" in str(row["unit"]) else x


def sample_network(n: int, seed: int, case: dict | None = None, spec: dict | None = None,
                   g: nx.DiGraph | None = None, fitted: dict | None = None, clip: bool = False) -> pd.DataFrame:
    """Draw n joint samples of every node.

    Inputs: n; seed (same seed and arguments give identical output); case, the implied-model settings
        (attenuation, coupling, noise_mult, psu_k, age_sd, dclink_n; default implied.NOMINAL_CASE);
        spec, g, fitted (loaded if omitted); clip, hold continuous nodes to master.csv low-high.
    Output: DataFrame, one column per node in topological order (categorical roots as strings,
        continuous nodes in master.csv units), plus the calendar columns month, hour, daytype drawn
        with the drivers.
    """
    case = dict(implied.NOMINAL_CASE if case is None else case)
    spec = graph.load_spec() if spec is None else spec
    g = graph.build_graph(spec) if g is None else g
    problems = graph.validate(g)
    if problems:
        raise ValueError("network is not valid: " + "; ".join(problems))
    fitted = sample.load_fitted() if fitted is None else fitted
    master, inp = spec["master"], spec["implied"]
    rng = np.random.default_rng(seed)
    out: dict[str, np.ndarray] = {}

    for name, a in g.nodes(data=True):                       # categorical roots
        if a["rule"] == "root_categorical":
            cats = list(a["categories"])
            p = np.array([a["categories"][c] for c in cats], dtype=float)
            out[name] = np.array(cats, dtype=object)[rng.choice(len(cats), size=n, p=p / p.sum())]

    temp, load, cal = np.empty(n), np.empty(n), pd.DataFrame(index=range(n), columns=["month", "hour", "daytype"])
    for s in fit.SEASONS:                                     # drivers given season
        sel = np.flatnonzero(out["season"] == s)
        sub_seed = int(rng.integers(2 ** 31))
        if sel.size == 0:
            continue
        d = sample.sample_drivers(sel.size, sub_seed, coupling=case["coupling"], season=s, fitted=fitted)
        temp[sel] = d["temp_c"].to_numpy()
        load[sel] = sample.to_load_fraction(d["load_index"].to_numpy(), float(master.loc["load_fraction", "typical"]),
                                            float(master.loc["load_fraction", "low"]),
                                            float(master.loc["load_fraction", "high"]))
        cal.iloc[sel] = d[["month", "hour", "daytype"]].to_numpy()
    out["outdoor_temp_c"], out["load_fraction"] = temp, load
    out[graph.AGE_NODE] = (float(master.loc[graph.AGE_NODE, "typical"])
                           + case["age_sd"] * np.sqrt(3.0) * rng.uniform(-1.0, 1.0, n))

    for node in nx.topological_sort(g):                       # assumed-normal nodes
        if g.nodes[node]["rule"] == "assumed_normal":
            out[node] = _assumed_normal(rng, master.loc[node], n)

    centres = graph.table_centres(spec)
    for (parent, child), tab in centres.items():
        if g.nodes[child]["rule"] != "table":
            continue
        missing = set(out[parent]) - set(tab)
        if missing:
            raise ValueError(f"{parent}->{child}: no tables.csv centre for {sorted(missing)}")
        out[child] = np.array([tab[c] for c in out[parent]], dtype=float)

    s, _ = implied.build_s(inp["s_long"], inp["master"], case["attenuation"], case["psu_k"])
    noise = implied.build_noise(inp["noise"], inp["master"], list(s.index), case["noise_mult"], case["dclink_n"])["sd"]
    drv = {k: out[k] for k in implied.DRIVERS}
    x = implied.factor_values(inp, s, case, drv, noise, rng)
    for i, f in enumerate(s.index):
        out[f] = x[:, i]
    osc = centres.get(("workload_type", "osc_amp"))           # workload shifts the osc_amp mean
    if osc:
        out["osc_amp"] = out["osc_amp"] - float(master.loc["osc_amp", "typical"]) + np.array([osc[c] for c in out["workload_type"]])
    out[graph.EQUATION_NODE] = out["load_fraction"] / (1.0 - out["units_offline"] / graph.N_UNITS)

    if clip:
        for node in master.index:
            out[node] = np.clip(out[node], float(master.loc[node, "low"]), float(master.loc[node, "high"]))
    frame = pd.DataFrame({k: out[k] for k in nx.topological_sort(g)})
    return pd.concat([frame, cal.reset_index(drop=True)], axis=1)


def query(evidence: dict, n: int = 200_000, seed: int = 0, case: dict | None = None,
          targets: list[str] | None = None, **kwargs) -> tuple[pd.DataFrame, float]:
    """Condition the network on evidence by rejection sampling.

    Inputs: evidence {node: category} for categorical nodes or {node: (low, high)} for continuous
        ones (inclusive); n draws before rejection; seed; case; targets (columns to return, default
        all); kwargs passed to sample_network.
    Output: (accepted rows, acceptance rate). Raises ValueError for unknown nodes or when no draw
        matches.
    """
    d = sample_network(n, seed, case, **kwargs)
    keep = np.ones(len(d), dtype=bool)
    for node, v in evidence.items():
        if node not in d.columns:
            raise ValueError(f"unknown node {node!r}")
        if isinstance(v, (tuple, list)):
            keep &= (d[node] >= v[0]).to_numpy() & (d[node] <= v[1]).to_numpy()
        else:
            keep &= (d[node] == v).to_numpy()
    if not keep.any():
        raise ValueError(f"no draw matches {evidence}; raise n or widen the evidence")
    acc = d.loc[keep, targets] if targets else d.loc[keep]
    return acc.reset_index(drop=True), float(keep.mean())
