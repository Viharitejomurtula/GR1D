"""Assemble the dependency network into one directed acyclic graph.

What this file is
    Merges the network specification files into a networkx DiGraph and checks it. Each node carries
    the rule that sampler.py uses to draw it given its parents; each edge records where it came from
    and whether a number backs it (quantified) or it is structure only.

Reads (read-only)
    data_bayesian-network/network/roots.yaml     categorical root nodes and their probabilities
    data_bayesian-network/network/master.csv     continuous nodes (low, typical, high, unit)
    data_bayesian-network/network/edges.csv      parent -> child links
    data_bayesian-network/network/tables.csv     child centre per parent category (table edges)
    data_bayesian-network/network/s_matrix/      driver -> factor slopes and curves (via implied.load_inputs)

Writes
    nothing.

Node rules
    root_categorical  draw from roots.yaml probabilities
    drivers           outdoor_temp_c and load_fraction drawn jointly given season by
                      ridethrough.drivers.sample.sample_drivers (Gaussian copula fit to DFW / ERCOT)
    age               equipment_age_years, uniform on master.csv low-high (assumed)
    table             child = tables.csv centre for the parent's category (no within-category spread
                      is given in the files, so none is added)
    s_matrix          factor = typical + driver responses (S slopes and curves) + noise (noise.csv, or
                      master.csv (high - low) / 6 where noise.csv has none); see implied.factor_values
    equation          converter_loading = load_fraction / (1 - units_offline / N_UNITS)
    assumed_normal    no parents with numbers: normal(typical, (high - low) / 6) clipped to low-high,
                      rounded for counts (assumed)
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd
import yaml

from ridethrough.drivers import implied

NETWORK_DIR = implied.NETWORK_DIR
ROOTS_YAML = NETWORK_DIR / "roots.yaml"
EDGES_CSV = NETWORK_DIR / "edges.csv"
TABLES_CSV = NETWORK_DIR / "tables.csv"

DRIVER_NODES = ("outdoor_temp_c", "load_fraction")
AGE_NODE = "equipment_age_years"
EQUATION_NODE = "converter_loading"
# Converter modules in the fixture, from edges.csv (units_offline -> converter_loading note:
# "loading = load_fraction / (1 - units_offline / n_units), n_units = 10 fixture").
N_UNITS = 10


def load_spec(network_dir: Path | None = None) -> dict:
    """Read every specification file.

    Inputs: network_dir (default NETWORK_DIR).
    Output: {"roots": {name: {"categories": {cat: p}, ...}}, "master": master.csv indexed by node,
        "edges": edges.csv, "tables": tables.csv, "implied": implied.load_inputs()}.
    """
    d = NETWORK_DIR if network_dir is None else Path(network_dir)
    return {"roots": yaml.safe_load((d / "roots.yaml").read_text()),
            "master": pd.read_csv(d / "master.csv").set_index("node"),
            "edges": pd.read_csv(d / "edges.csv"),
            "tables": pd.read_csv(d / "tables.csv"),
            "implied": implied.load_inputs()}


def s_links(spec: dict) -> set[tuple[str, str]]:
    """(driver, factor) pairs with a non-zero S response at nominal or upper attenuation."""
    inp = spec["implied"]
    links = set()
    for att in implied.ATTENUATIONS:
        s, _ = implied.build_s(inp["s_long"], inp["master"], att, 1.0)
        links |= {(d, f) for f in s.index for d in s.columns if s.loc[f, d] != 0}
    return links


def table_centres(spec: dict) -> dict[tuple[str, str], dict[str, float]]:
    """{(parent, child): {parent category: child centre}} from tables.csv."""
    out: dict[tuple[str, str], dict[str, float]] = {}
    for _, r in spec["tables"].iterrows():
        parent, child = r["edge"].split("->")
        out.setdefault((parent, child), {})[r["parent_category"]] = float(r["child_center"])
    return out


def node_rule(node: str, spec: dict, factors: list[str], tables: dict) -> str:
    """The sampling rule for a node (see the module docstring)."""
    if node in spec["roots"]:
        return "root_categorical"
    if node in DRIVER_NODES:
        return "drivers"
    if node == AGE_NODE:
        return "age"
    if node == EQUATION_NODE:
        return "equation"
    if node in factors:
        return "s_matrix"
    if any(child == node for _, child in tables):
        return "table"
    return "assumed_normal"


def build_graph(spec: dict | None = None) -> nx.DiGraph:
    """The network as a DiGraph.

    Node attributes: kind ("categorical" | "continuous"), rule, unit, and for categorical roots
        categories {cat: p}.
    Edge attributes: source ("edges.csv" | "s_matrix" | "drivers"), quantified (True when the child's
        rule uses the parent), rule_type (edges.csv), note.
    """
    spec = load_spec() if spec is None else spec
    factors = implied.factor_list(spec["implied"]["s_long"])
    tables = table_centres(spec)
    g = nx.DiGraph()
    for name, r in spec["roots"].items():
        g.add_node(name, kind="categorical", rule="root_categorical", unit="category",
                   categories=dict(r["categories"]))
    for node, r in spec["master"].iterrows():
        g.add_node(node, kind="continuous", rule=node_rule(node, spec, factors, tables), unit=r["unit"])

    links = s_links(spec)
    for _, r in spec["edges"].iterrows():
        p, c = r["parent"], r["child"]
        rule = g.nodes[c]["rule"] if c in g else None
        quantified = ((p, c) in links or (p, c) in tables or rule == "equation"
                      or (rule == "drivers" and p == "season"))
        g.add_edge(p, c, source="edges.csv", quantified=bool(quantified), rule_type=r["rule_type"],
                   note=r["note"])
    for p, c in sorted(links):
        if not g.has_edge(p, c):
            g.add_edge(p, c, source="s_matrix", quantified=True, rule_type="s_matrix", note="")
    for p, c in (("season", "outdoor_temp_c"), ("season", "load_fraction"),
                 ("outdoor_temp_c", "load_fraction")):
        if not g.has_edge(p, c):
            g.add_edge(p, c, source="drivers", quantified=True, rule_type="copula",
                       note="joint draw by sample_drivers (coupling scales the temperature effect)")
    return g


def validate(g: nx.DiGraph) -> list[str]:
    """Problems that would stop sampling: cycles, nodes with no rule (edge endpoints missing from
    roots.yaml and master.csv), root probabilities that do not sum to 1. Empty list = valid."""
    problems = []
    if not nx.is_directed_acyclic_graph(g):
        problems.append(f"cycle: {nx.find_cycle(g)}")
    for n, a in g.nodes(data=True):
        if "rule" not in a:
            problems.append(f"{n}: in edges but not in roots.yaml or master.csv")
        elif a["rule"] == "root_categorical" and abs(sum(a["categories"].values()) - 1.0) > 1e-3:
            problems.append(f"{n}: probabilities sum to {sum(a['categories'].values()):.4f}")
    return problems


def unquantified_edges(g: nx.DiGraph) -> list[tuple[str, str]]:
    """Edges that are structure only: no number in the files sets their effect, so sampling ignores them."""
    return sorted((p, c) for p, c, a in g.edges(data=True) if not a["quantified"])
