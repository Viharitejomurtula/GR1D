"""Load a trained ensemble and predict, in batches, for many scenarios.

What this file is
    Surrogate.load(dir) rebuilds the ensemble from a train() output directory (with its std calibration,
    calibration.json, when present); predict() encodes the
    scenarios and runs them in batches of CONFIG["predict_batch"] rows (1,000,000 rows fit easily).

Inputs: list[sim.scenario.Scenario] or a DataFrame with FIELD_ORDER columns.
Outputs: DataFrame, one row per scenario: p_pass_mean, p_pass_std, <target>_mean / _std for
    recovery_margin_s (s), min_power (pu), peak_current_pu (pu), floor_violation_s (s), failure_mode
    (most likely label), failure_mode_prob (its mean probability), and outside_training: the inputs outside
    the training data's range, ";"-joined (empty when none). A non-empty value means the prediction is an
    extrapolation and should be checked with the simulator. Also prob:<class> (mean probability of each
    failure-mode class, classes in self.classes order), as required by surrogate.registry.SurrogateModel.

Surrogate satisfies surrogate.registry.SurrogateModel (the "torch-ensemble" format).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from surrogate.config import CONFIG
from surrogate.features import FeatureEncoder, scenarios_to_frame
from surrogate.model import Ensemble, MemberNet


class Surrogate:
    """A trained ensemble ready for prediction."""

    def __init__(self, ensemble: Ensemble, batch: int | None = None, provenance: dict | None = None):
        self.ensemble = ensemble
        self.batch = CONFIG["predict_batch"] if batch is None else batch
        self.provenance = dict(provenance or {"format": "torch-ensemble", "n_members": len(ensemble.members)})

    @property
    def classes(self) -> list[str]:
        """Failure-mode labels (including "passed"), in the order of the prob:<class> columns."""
        return list(self.ensemble.encoder.classes)

    @property
    def input_fields(self) -> list[str]:
        """Scenario fields the model reads (sim.scenario.FIELD_ORDER; excluded ones are ignored)."""
        from sim.scenario import FIELD_ORDER
        return list(FIELD_ORDER)

    @torch.no_grad()
    def member_fail_probs(self, scenarios) -> np.ndarray:
        """(n_members, m) probability of failing (1 - P(pass)) from each ensemble member alone."""
        frame = scenarios_to_frame(scenarios)
        out = []
        for member in self.ensemble.members:
            member.eval()
            ps = [1.0 - torch.sigmoid(member(torch.as_tensor(self.ensemble.encoder.transform(frame.iloc[s:s + self.batch]),
                                                             dtype=torch.float32))["passed"]).numpy()
                  for s in range(0, len(frame), self.batch)]
            out.append(np.concatenate(ps))
        return np.stack(out)

    @classmethod
    def load(cls, model_dir: str | Path) -> "Surrogate":
        """Rebuild from encoder.json, config.json and member_<i>.pt in model_dir."""
        d = Path(model_dir)
        enc = FeatureEncoder.load(d / "encoder.json")
        cfg = json.loads((d / "config.json").read_text())
        members = []
        for i in range(cfg["n_members"]):
            m = MemberNet(enc.n_features, len(enc.classes), cfg["hidden_sizes"], cfg["dropout"])
            m.load_state_dict(torch.load(d / f"member_{i}.pt", weights_only=True))
            members.append(m.eval())
        cal = d / "calibration.json"
        scale = json.loads(cal.read_text()) if cal.exists() else None
        return cls(Ensemble(members, enc, scale), cfg.get("predict_batch"))

    def predict(self, scenarios) -> pd.DataFrame:
        """Means and stds for every scenario (see module docstring), in input order."""
        frame = scenarios_to_frame(scenarios)
        parts = []
        for s in range(0, len(frame), self.batch):
            x = self.ensemble.encoder.transform(frame.iloc[s:s + self.batch])
            r = self.ensemble.predict(x)
            probs = r.pop("failure_mode_prob_mean"); r.pop("failure_mode_prob_std")
            r["failure_mode_prob"] = probs.max(1)
            for i, c in enumerate(self.ensemble.encoder.classes):
                r[f"prob:{c}"] = probs[:, i]
            r["outside_training"] = [";".join(f) for f in self.ensemble.encoder.outside_training(frame.iloc[s:s + self.batch])]
            parts.append(pd.DataFrame(r))
        return pd.concat(parts, ignore_index=True)
