"""Input encoding: Scenario fields -> model feature matrix, and the targets' scaling.

What this file is
    excluded_fields() finds the Scenario fields the simulator never receives, by asking the actual
    runner: a field is used if changing it changes sim.runner._overrides() for any of a set of sampled
    scenarios (several are needed because some fields act only conditionally, e.g. reclose_gap_s only
    with a second dip and the group spreads only with n_groups > 1). FeatureEncoder is fit on the
    training split only: continuous fields are standardized, the categorical fields (supply_voltage_v,
    faulted_phase_frac, second_dip) are one-hot encoded with the categories seen in training
    (fit_inputs), and the regression targets are standardized and the failure_mode classes recorded
    (fit_targets). It saves to / loads from JSON.

Inputs: DataFrames whose columns include sim.scenario.FIELD_ORDER (and, for fitting, the outputs).
Outputs: float32 feature matrices (n x n_features); target arrays in standardized units.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sim import runner, scenario
from surrogate.config import CONFIG

CATEGORICAL = ("supply_voltage_v", "faulted_phase_frac", "second_dip")
CONSTANT_IF_FIXED = "dip_start_s"
REGRESSION_TARGETS = ("recovery_margin_s", "min_power", "peak_current_pu", "floor_violation_s")
CONSTANT_REL_TOL = 1e-9   # an input whose spread is below this x max(1, |mean|) is constant (floating-point noise, not variation)


def _scale(x: pd.Series) -> tuple[float, float]:
    """(mean, std) for standardizing; std is 1 for an input that is constant up to floating-point noise, so a
    constant column maps to ~0 instead of being divided by ~1e-17."""
    mean, sd = float(x.mean()), float(x.std(ddof=0))
    return mean, (sd if sd > CONSTANT_REL_TOL * max(1.0, abs(mean)) else 1.0)
LOG1P_TARGETS = ("floor_violation_s",)


def _reaches_runner(sc, f: str) -> bool:
    """True if changing field f alone (bools flipped, numbers + 1) changes runner._overrides(sc), or makes
    it reject the scenario (the field is then checked by the runner, so it matters)."""
    v = getattr(sc, f)
    try:
        changed = runner._overrides(dataclasses.replace(sc, **{f: (not v) if isinstance(v, bool) else v + 1}))
    except ValueError:
        return True
    return changed != runner._overrides(sc)


def excluded_fields(seed: int = 0, n: int = 200) -> list[str]:
    """Scenario fields (scenario.FIELD_ORDER) that never reach the simulator for any of
    scenario.sample_many(n, seed): perturbing them alone leaves runner._overrides() unchanged."""
    scs = scenario.sample_many(n, seed=seed)
    return [f for f in scenario.FIELD_ORDER if not any(_reaches_runner(sc, f) for sc in scs)]


def scenarios_to_frame(scenarios) -> pd.DataFrame:
    """List of Scenario -> DataFrame with FIELD_ORDER columns (a DataFrame is returned unchanged)."""
    if isinstance(scenarios, pd.DataFrame):
        return scenarios
    return pd.DataFrame([s.to_vector() for s in scenarios], columns=list(scenario.FIELD_ORDER))


class FeatureEncoder:
    """Standardize continuous inputs, one-hot categorical inputs, scale regression targets.

    Attributes (all set by fit): excluded (dropped fields), continuous (field names), mean/std per
    continuous field, low/high (training range per continuous field), categories {field: [values]},
    target_low/target_high (training range of each regression target, in target units), target_mean/target_std per regression target
    (floor_violation_s on log1p scale), classes (failure_mode labels, sorted).
    """

    def __init__(self):
        self.excluded: list[str] = []
        self.continuous: list[str] = []
        self.mean: dict[str, float] = {}
        self.std: dict[str, float] = {}
        self.low: dict[str, float] = {}
        self.high: dict[str, float] = {}
        self.target_low: dict[str, float] = {}
        self.target_high: dict[str, float] = {}
        self.categories: dict[str, list[float]] = {}
        self.target_mean: dict[str, float] = {}
        self.target_std: dict[str, float] = {}
        self.classes: list[str] = []

    def fit(self, train: pd.DataFrame, classes: list[str] | None = None) -> "FeatureEncoder":
        """Fit inputs and targets on the training split (fit_inputs then fit_targets)."""
        return self.fit_inputs(train).fit_targets(train, classes)

    def fit_inputs(self, frame: pd.DataFrame, categories_from: pd.DataFrame | None = None) -> "FeatureEncoder":
        """Input statistics from Scenario rows (frame) and categorical levels from categories_from (default
        frame). train() passes the whole dataset there: levels are inputs, not labels, so using every split
        leaks nothing, and a rare level that lands only in val or test no longer breaks encoding.
        dip_start_s must be constant (asserted) and is then excluded with the fields that never reach the
        simulator."""
        train = frame
        levels = frame if categories_from is None else categories_from
        assert train[CONSTANT_IF_FIXED].nunique() == 1, f"{CONSTANT_IF_FIXED} varies in the data; it cannot be dropped"
        self.excluded = excluded_fields() + [CONSTANT_IF_FIXED]
        used = [f for f in scenario.FIELD_ORDER if f not in self.excluded]
        self.continuous = [f for f in used if f not in CATEGORICAL]
        for f in self.continuous:
            x = train[f].astype(float)
            self.mean[f], self.std[f] = _scale(x)
            self.low[f], self.high[f] = float(x.min()), float(x.max())
        self.categories = {f: sorted(float(v) for v in levels[f].astype(float).unique())
                           for f in CATEGORICAL if f in used}
        return self

    def fit_targets(self, train: pd.DataFrame, classes: list[str] | None = None) -> "FeatureEncoder":
        """Regression-target scaling and failure_mode classes (default: those in train) from simulator outputs.
        Scaling uses only rows whose regression targets are valid (regression_ok, when the column exists)."""
        classes_src = train
        if "regression_ok" in train:
            train = train[train["regression_ok"].astype(bool)]
        for t in REGRESSION_TARGETS:
            self.target_mean[t], self.target_std[t] = _scale(pd.Series(self.target_raw(train, t)))
            self.target_low[t], self.target_high[t] = float(train[t].min()), float(train[t].max())
        self.classes = sorted(classes if classes is not None else classes_src["failure_mode"].unique())
        return self

    @property
    def n_features(self) -> int:
        """Width of the feature matrix."""
        return len(self.continuous) + sum(len(v) for v in self.categories.values())

    def feature_names(self) -> list[str]:
        """Column names of the feature matrix (one-hot columns as field=value)."""
        return self.continuous + [f"{f}={v:g}" for f, vals in self.categories.items() for v in vals]

    def transform(self, data) -> np.ndarray:
        """Scenarios (list or DataFrame) -> float32 matrix. An unseen category raises ValueError."""
        d = scenarios_to_frame(data)
        cols = [((d[f].astype(float).to_numpy() - self.mean[f]) / self.std[f]) for f in self.continuous]
        for f, vals in self.categories.items():
            x = d[f].astype(float).to_numpy()
            hit = np.isclose(x[:, None], np.array(vals)[None, :])
            if not hit.any(axis=1).all():
                raise ValueError(f"{f}: value(s) {sorted(set(x[~hit.any(axis=1)]))} not seen in training {vals}")
            cols.extend(hit.T.astype(float))
        return np.column_stack(cols).astype(np.float32)

    def outside_training(self, data) -> list[list[str]]:
        """Per row, the continuous inputs outside the training range [low, high] widened by
        CONFIG["ood_margin_frac"] of the range (so values at the edge of a sampled range are not flagged). The ensemble extrapolates there, so its prediction and spread are not trustworthy.
        An encoder saved before training ranges were recorded (no low/high) reports nothing."""
        d = scenarios_to_frame(data)
        out = [[] for _ in range(len(d))]
        for f in (self.continuous if self.low else []):
            lo, hi = self.low[f], self.high[f]
            tol = CONFIG["ood_margin_frac"] * (hi - lo) + CONSTANT_REL_TOL * max(1.0, abs(lo), abs(hi))
            x = d[f].astype(float).to_numpy()
            for i in np.flatnonzero((x < lo - tol) | (x > hi + tol)):
                out[i].append(f)
        return out

    @staticmethod
    def target_raw(d: pd.DataFrame, t: str) -> np.ndarray:
        """Target column in model units before standardizing (log1p for LOG1P_TARGETS)."""
        y = d[t].astype(float).to_numpy()
        return np.log1p(y) if t in LOG1P_TARGETS else y

    def targets(self, d: pd.DataFrame) -> dict[str, np.ndarray]:
        """Training targets: passed (0/1), standardized regression targets, failure_mode class index,
        censored (bool, if present)."""
        out = {"passed": d["passed"].astype(float).to_numpy()}
        for t in REGRESSION_TARGETS:
            out[t] = (self.target_raw(d, t) - self.target_mean[t]) / self.target_std[t]
        idx = {c: i for i, c in enumerate(self.classes)}
        out["failure_mode"] = d["failure_mode"].map(idx).fillna(-1).astype(int).to_numpy()
        out["censored"] = d["censored"].to_numpy(bool) if "censored" in d else np.zeros(len(d), bool)
        out["regression_ok"] = d["regression_ok"].to_numpy(bool) if "regression_ok" in d else np.ones(len(d), bool)
        for t in REGRESSION_TARGETS:                  # masked rows: any finite placeholder, excluded from the loss
            out[t] = np.where(out["regression_ok"], np.nan_to_num(out[t]), 0.0)
        return out

    def unscale(self, t: str, z: np.ndarray) -> np.ndarray:
        """Standardized model output -> target units (expm1 for LOG1P_TARGETS)."""
        y = z * self.target_std[t] + self.target_mean[t]
        return np.expm1(y) if t in LOG1P_TARGETS else y

    def save(self, path: str | Path) -> None:
        """Write every fitted attribute as JSON."""
        Path(path).write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "FeatureEncoder":
        """Read an encoder written by save()."""
        enc = cls()                                    # defaults first, so older files without low/high still load
        enc.__dict__.update(json.loads(Path(path).read_text()))
        return enc
