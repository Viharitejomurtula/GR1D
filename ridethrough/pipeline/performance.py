"""Surrogate evaluation and the performance distribution.

What this file is
    Evaluator wraps the trained surrogate ensemble as a function from Scenario-field arrays to a fixed set of
    outputs (probability of failing, probability of each failure mode, and four continuous severity measures).
    performance() summarises those over a joint sample as a distribution.

    "Fail" is the simulator's own verdict, Grade.passed (post-2028 NOGRR rule). It already covers both halves
    of the criterion: the grid-facing side (power floor, current cap, recovery) and operations (cooling trip,
    PSU shutdown, storage hand-back). P(fail) for an event is 1 - the ensemble's mean pass probability, so the
    average over events is an expected failure rate and not a count of thresholded verdicts.

Uncertainty reported separately
    - event-to-event spread (the distribution itself, from the joint sampler);
    - Monte Carlo error on every rate (bootstrap over events);
    - surrogate disagreement: each ensemble member's overall failure rate, and the mean per-event spread.
    Parameter uncertainty in the network's assumed inputs is NOT included here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sim.scenario import FIELD_ORDER
from surrogate.registry import SurrogateModel

CONTINUOUS = ("min_power", "peak_current_pu", "floor_violation_s", "recovery_margin_s")
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
CHUNK = 65_536


class Evaluator:
    """Uses only the surrogate.registry.SurrogateModel contract, so any registered model can be swapped in."""

    def __init__(self, surrogate: SurrogateModel):
        self.sur = surrogate
        self.modes = [c for c in surrogate.classes if c != "passed"]
        self.names = ["p_fail", *[f"mode:{m}" for m in self.modes], *CONTINUOUS]

    @staticmethod
    def _frame(X) -> pd.DataFrame:
        return X if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=list(FIELD_ORDER))

    def _chunks(self, X):
        frame = self._frame(X)
        for s in range(0, len(frame), CHUNK):
            yield frame.iloc[s:s + CHUNK]

    def __call__(self, X) -> np.ndarray:
        """(m, len(names)) array: ensemble-mean outputs for m scenarios."""
        parts = []
        for chunk in self._chunks(X):
            r = self.sur.predict(chunk)
            parts.append(np.column_stack([1.0 - r["p_pass_mean"].to_numpy()] + [r[f"prob:{m}"].to_numpy() for m in self.modes] +
                                         [r[f"{t}_mean"].to_numpy() for t in CONTINUOUS]))
        return np.vstack(parts)

    def member_fail_probs(self, X) -> np.ndarray:
        """(members, m) probability of failing from each ensemble member alone ((1, m) for a single model)."""
        return np.concatenate([np.asarray(self.sur.member_fail_probs(c)) for c in self._chunks(X)], axis=1)

    def outside_training(self, X) -> np.ndarray:
        return np.concatenate([(self.sur.predict(c)["outside_training"].to_numpy() != "") for c in self._chunks(X)])


def _boot_ci(values: np.ndarray, rng: np.random.Generator, reps: int = 200) -> list[float]:
    idx = rng.integers(0, len(values), (reps, len(values)))
    m = values[idx].mean(1)
    return [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))]


def performance(ev: Evaluator, sc: pd.DataFrame, seed: int = 0) -> tuple[dict, np.ndarray]:
    """Distribution of outcomes over the joint sample sc. Returns (summary dict, per-event output array)."""
    rng = np.random.default_rng(seed)
    y = ev(sc)
    names = ev.names
    col = {n: y[:, i] for i, n in enumerate(names)}
    members = ev.member_fail_probs(sc)
    ood = ev.outside_training(sc)
    summary = {
        "n_events": int(len(sc)),
        "fail_probability": {
            "mean": float(col["p_fail"].mean()), "mc_95ci": _boot_ci(col["p_fail"], rng),
            "by_ensemble_member": [float(v) for v in members.mean(1)],
            "mean_per_event_member_spread": float(members.std(0).mean()),
            "share_events_fail_prob_above_0.9": float((col["p_fail"] > 0.9).mean()),
            "share_events_fail_prob_below_0.1": float((col["p_fail"] < 0.1).mean()),
        },
        "failure_mode_share": {m: float(col[f"mode:{m}"].mean()) for m in ev.modes},
        "continuous": {},
        "share_inputs_outside_training": float(ood.mean()),
    }
    for t in CONTINUOUS:
        v = col[t]
        counts, edges = np.histogram(v, bins=30)
        summary["continuous"][t] = {"mean": float(v.mean()), "quantiles": {str(q): float(np.quantile(v, q)) for q in QUANTILES},
                                     "hist_counts": counts.tolist(), "hist_edges": [float(e) for e in edges]}
    return summary, y
