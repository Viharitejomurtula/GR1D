"""Minimal Bayesian-network layer: DAG of nodes sampled by ancestral (forward) sampling, vectorised over n scenarios.
Supports do()-interventions and rejection conditioning. Each node declares its evidence kind so results can be audited."""
from dataclasses import dataclass, field
from typing import Callable, Dict, List
import numpy as np

@dataclass
class Node:
    name: str
    parents: List[str]
    fn: Callable            # fn(parents: dict[str, ndarray], rng, n) -> ndarray (n,) or (n,k)
    kind: str               # 'empirical' | 'spec' | 'physics' | 'assumed'
    note: str = ""

class BN:
    def __init__(self, nodes: List[Node]):
        self.nodes = {x.name: x for x in nodes}; self.order = self._topo()
    def _topo(self):
        seen, out = set(), []
        def visit(k, stack=()):
            if k in stack: raise ValueError(f"cycle at {k}")
            if k in seen: return
            for p in self.nodes[k].parents: visit(p, stack + (k,))
            seen.add(k); out.append(k)
        for k in self.nodes: visit(k)
        return out
    def sample(self, n, rng, do: Dict[str, object] = None):
        do, v = do or {}, {}
        for k in self.order:
            nd = self.nodes[k]
            v[k] = np.broadcast_to(np.asarray(do[k]), (n,)).copy() if k in do else nd.fn({p: v[p] for p in nd.parents}, rng, n)
        return v
    def condition(self, n, rng, where: Callable, max_draws=20, **kw):
        """Rejection conditioning: keep scenarios where `where(samples)` is True (boolean array)."""
        kept = []
        for _ in range(max_draws):
            s = self.sample(n, rng, **kw); m = where(s); kept.append({k: x[m] for k, x in s.items()})
            if sum(len(x[self.order[0]]) for x in kept) >= n: break
        return {k: np.concatenate([x[k] for x in kept])[:n] for k in kept[0]}
    def audit(self):
        return {k: (nd.kind, nd.parents) for k, nd in self.nodes.items()}
