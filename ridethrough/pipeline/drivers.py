"""Failure-driver ranking: Shapley attribution over driver blocks, interactions, lift tables, change points.

What this file is
    The ranking answers "which drivers move the outcome most" separately for group A (conditions) and group B
    (site state); the design is held fixed, so it is not ranked here. The unit being attributed is a Block
    (joint.BLOCKS): a set of Scenario columns that always change together.

Method (interventional Shapley values, estimated by permutation sampling)
    For a foreground event x and a background event b (two different rows of the joint sample), a coalition S of
    blocks takes x's values and the other blocks of the same group take b's; blocks outside the group keep x's
    values. v(S) is the surrogate's output for that mixed event. Walking the blocks in a random order and
    recording how v changes when each block flips from b to x gives one estimate of its Shapley value for that
    event (each order is also run reversed). The importance of a block is the mean over events of the absolute
    value, in output units (probability for P(fail) and mode shares). Signed means are reported too, but with
    the foreground and background drawn from the same distribution they average near zero, so they are not a
    direction; use the lift tables for direction.

    Because blocks are swapped whole, correlation INSIDE a block (season with temperature, workload type with
    swing size) is kept. Correlation BETWEEN blocks is not: the network couples site load to temperature
    weakly, and the swap treats them as independent. The lift tables below are the correlation-aware
    complement: they use only the joint sample, with no swapping.

Reported uncertainty
    Bootstrap over the foreground events gives an interval on each importance and on each block's rank; a rank
    whose 90% interval spans more than two adjacent places is flagged unresolved.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ridethrough.pipeline.joint import BLOCK, Block, groups
from sim.scenario import FIELD_ORDER

COL = {c: i for i, c in enumerate(FIELD_ORDER)}


def _cols(block: Block) -> list[int]:
    return [COL[c] for c in block.columns]


def shapley(f, fg: np.ndarray, bg: np.ndarray, players: list[list[int]], n_perm: int, rng: np.random.Generator) -> np.ndarray:
    """Per-event Shapley values, shape (events, players, outputs). Each of the n_perm random orders is also run
    reversed, so 2 * n_perm walks are averaged."""
    m, k = len(fg), len(players)
    phi = None
    walks = 0
    start = fg.copy()
    for cols in players:
        start[:, cols] = bg[:, cols]
    base = f(start)
    phi = np.zeros((m, k, base.shape[1]))
    for _ in range(n_perm):
        order = rng.permutation(k)
        for o in (order, order[::-1]):
            z, prev = start.copy(), base
            for j in o:
                z[:, players[j]] = fg[:, players[j]]
                cur = f(z)
                phi[:, j, :] += cur - prev
                prev = cur
            walks += 1
    return phi / walks


def _rank_table(phi: np.ndarray, blocks: list[Block], d: int, rng: np.random.Generator, reps: int = 200) -> list[dict]:
    """Importance table for output column d from per-event values phi (events, players, outputs)."""
    a = np.abs(phi[:, :, d])
    imp = a.mean(0)
    idx = rng.integers(0, len(a), (reps, len(a)))
    boot = a[idx].mean(1)                                  # (reps, players)
    ranks = (-boot).argsort(1).argsort(1) + 1
    order = (-imp).argsort()
    rows = []
    for pos, j in enumerate(order):
        lo, hi = np.quantile(ranks[:, j], [0.05, 0.95])
        rows.append({
            "rank": pos + 1, "block": blocks[j].name, "label": blocks[j].label, "group": blocks[j].group,
            "importance": float(imp[j]), "importance_90ci": [float(np.quantile(boot[:, j], 0.05)), float(np.quantile(boot[:, j], 0.95))],
            "share": float(imp[j] / imp.sum()) if imp.sum() > 0 else 0.0,
            "signed_mean": float(phi[:, j, d].mean()),
            "rank_90ci": [int(lo), int(hi)], "rank_resolved": bool(hi - lo <= 1),
            "p_top3": float((ranks[:, j] <= 3).mean()),
        })
    return rows


def rank_group(f, names: list[str], sc: pd.DataFrame, group: str, events: int, n_perm: int, seed: int) -> dict:
    """Rank the blocks of one group on every output in names."""
    rng = np.random.default_rng(seed)
    blocks = list(groups(group))
    X = sc.to_numpy(dtype=float)
    fg = X[rng.choice(len(X), events, replace=False)]
    bg = X[rng.choice(len(X), events, replace=True)]
    phi = shapley(f, fg, bg, [_cols(b) for b in blocks], n_perm, rng)
    out = {"group": group, "events": events, "walks": 2 * n_perm, "by_output": {}}
    for d, name in enumerate(names):
        out["by_output"][name] = _rank_table(phi, blocks, d, rng)
    out["interactions"] = interactions(f, names, fg, bg, blocks)
    return out


def interactions(f, names: list[str], fg: np.ndarray, bg: np.ndarray, blocks: list[Block], top: int = 5) -> dict:
    """Mean absolute pairwise interaction per output: |f(xi,xj) - f(xi,bj) - f(bi,xj) + f(bi,bj)|, other blocks at x."""
    def mix(*swap_to_bg: Block) -> np.ndarray:
        z = fg.copy()
        for b in swap_to_bg:
            z[:, _cols(b)] = bg[:, _cols(b)]
        return f(z)
    full = mix()
    single = {b.name: mix(b) for b in blocks}
    res: dict[str, list[dict]] = {n: [] for n in names}
    for i, bi in enumerate(blocks):
        for bj in blocks[i + 1:]:
            inter = full - single[bi.name] - single[bj.name] + mix(bi, bj)
            for d, n in enumerate(names):
                res[n].append({"blocks": [bi.name, bj.name], "importance": float(np.abs(inter[:, d]).mean()),
                               "signed_mean": float(inter[:, d].mean())})
    return {n: sorted(v, key=lambda r: -r["importance"])[:top] for n, v in res.items()}


def group_split(f, names: list[str], sc: pd.DataFrame, events: int, n_perm: int, seed: int) -> list[dict]:
    """Two-player game: how much of the outcome's movement comes from group A (conditions) versus B (site state)."""
    rng = np.random.default_rng(seed)
    X = sc.to_numpy(dtype=float)
    fg = X[rng.choice(len(X), events, replace=False)]
    bg = X[rng.choice(len(X), events, replace=True)]
    players = [[c for b in groups(g) for c in _cols(b)] for g in ("A", "B")]
    phi = shapley(f, fg, bg, players, n_perm, rng)
    imp = np.abs(phi).mean(0)
    return [{"output": n, "A_conditions": float(imp[0, d]), "B_site_state": float(imp[1, d]),
             "A_share": float(imp[0, d] / (imp[:, d].sum() or 1.0))} for d, n in enumerate(names)]


def _label(x: float) -> str:
    return f"{x:.3g}"


def lift_tables(roots: pd.DataFrame, y: np.ndarray, names: list[str], bins: int = 5) -> dict:
    """Per block: the outcome by level of the block's key variable, from the joint sample (no swapping).
    Categorical keys use their levels; numeric keys use equal-count bins."""
    p = y[:, names.index("p_fail")]
    extra = {n: y[:, names.index(n)] for n in ("min_power", "floor_violation_s", "peak_current_pu")}
    base = float(p.mean())
    out = {}
    for b in BLOCK.values():
        v = roots[b.key]
        numeric = pd.api.types.is_numeric_dtype(v) and v.nunique() > 8
        if numeric:
            cats = pd.qcut(v, bins, duplicates="drop")
            keys = [(f"{_label(iv.left)} to {_label(iv.right)}", cats == iv) for iv in cats.cat.categories]
        else:
            keys = [(str(lv), v == lv) for lv in sorted(v.unique(), key=str)]
        rows = []
        for lab, mask in keys:
            mask = np.asarray(mask)
            if mask.sum() == 0:
                continue
            rows.append({"level": lab, "share_of_events": float(mask.mean()), "p_fail": float(p[mask].mean()),
                         "lift": float(p[mask].mean() / base) if base > 0 else None,
                         **{f"mean_{k}": float(a[mask].mean()) for k, a in extra.items()}})
        out[b.name] = {"key": b.key, "numeric": bool(numeric), "levels": rows}
    return out


def change_points(roots: pd.DataFrame, y: np.ndarray, names: list[str], bins: int = 20, min_jump: float = 0.0) -> dict:
    """For each numeric block key and output, the value where the mean output moves most between adjacent
    equal-count bins (the largest step). Reported as the boundary value, the step, and the step relative to the
    output's overall spread (std), so a small step in a flat output is not mistaken for a threshold."""
    out = {}
    for b in BLOCK.values():
        v = roots[b.key]
        if not (pd.api.types.is_numeric_dtype(v) and v.nunique() > 8):
            continue
        cats = pd.qcut(v, bins, duplicates="drop")
        codes = cats.cat.codes.to_numpy()
        edges = [iv.right for iv in cats.cat.categories]
        res = {}
        for n in ("p_fail", "min_power", "floor_violation_s", "peak_current_pu"):
            col = y[:, names.index(n)]
            means = np.array([col[codes == c].mean() for c in range(len(edges))])
            steps = np.diff(means)
            if len(steps) == 0:
                continue
            j = int(np.abs(steps).argmax())
            sd = float(col.std()) or 1.0
            if abs(steps[j]) / sd >= min_jump:
                res[n] = {"at": float(edges[j]), "step": float(steps[j]), "step_over_std": float(steps[j] / sd)}
        out[b.name] = res
    return out
