"""Network definitions: one ensemble member and the deep ensemble.

What this file is
    MemberNet: input -> [Linear(h) -> SiLU -> Dropout] x 2 -> Linear(h) -> SiLU -> heads, sizes and
    dropout from CONFIG. Heads: passed (1 logit), recovery_margin_s, min_power, peak_current_pu,
    floor_violation_s (1 each, standardized; floor on log1p scale), failure_mode (one logit per class).
    Ensemble: K members; prediction = mean across members, uncertainty = std across members,
    multiplied per regression target by std_scale when the ensemble was calibrated (train.calibrate).

Inputs: float32 features from features.FeatureEncoder.transform (n x n_features).
Outputs: MemberNet.forward -> dict of tensors; Ensemble.predict -> dict of numpy arrays in target
    units: p_pass_mean/std (mean and std of member sigmoids), <target>_mean/_std for each regression
    target, failure_mode_prob_mean/_std (n x n_classes, softmax per member) and failure_mode (label of
    the highest mean probability).
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from sim import constants as C

from surrogate.config import CONFIG
from surrogate.features import REGRESSION_TARGETS, FeatureEncoder

HEADS = ("passed",) + REGRESSION_TARGETS
# Hard upper bounds that hold by definition, applied to each member's prediction before averaging:
# recovery_margin_s = deadline - recovery time, so it cannot exceed the grader's deadline (NOGRR 282 2.0 s).
UPPER_BOUNDS = {"recovery_margin_s": C.RECOVERY_DEADLINE_S}


class MemberNet(nn.Module):
    """One multi-output MLP. forward(x) -> {"passed": (n,), each regression target: (n,),
    "failure_mode": (n, n_classes)}; regression outputs are in standardized units."""

    def __init__(self, n_in: int, n_classes: int, hidden: list[int] | None = None, dropout: float | None = None):
        super().__init__()
        hidden = CONFIG["hidden_sizes"] if hidden is None else hidden
        p = CONFIG["dropout"] if dropout is None else dropout
        layers, width = [], n_in
        for i, h in enumerate(hidden):
            layers += [nn.Linear(width, h), nn.SiLU()]
            if i < len(hidden) - 1:
                layers.append(nn.Dropout(p))
            width = h
        self.trunk = nn.Sequential(*layers)
        self.scalar = nn.Linear(width, len(HEADS))
        self.classes = nn.Linear(width, n_classes)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Head outputs for a batch of features."""
        z = self.trunk(x)
        s = self.scalar(z)
        out = {h: s[:, i] for i, h in enumerate(HEADS)}
        out["failure_mode"] = self.classes(z)
        return out

    def forward_flat(self, x: torch.Tensor) -> torch.Tensor:
        """All heads as one (n, len(HEADS) + n_classes) tensor; used for ONNX export."""
        z = self.trunk(x)
        return torch.cat([self.scalar(z), self.classes(z)], dim=1)


class Ensemble:
    """K MemberNets plus the encoder that maps their outputs back to target units."""

    def __init__(self, members: list[MemberNet], encoder: FeatureEncoder, std_scale: dict | None = None):
        self.members = members
        self.encoder = encoder
        self.std_scale = dict(std_scale or {})      # {regression target: factor}; missing = 1

    @classmethod
    def create(cls, encoder: FeatureEncoder, seed: int, k: int | None = None) -> "Ensemble":
        """K freshly initialised members; member i is initialised with torch seed seed + i."""
        members = []
        for i in range(CONFIG["n_members"] if k is None else k):
            torch.manual_seed(seed + i)
            members.append(MemberNet(encoder.n_features, len(encoder.classes)))
        return cls(members, encoder)

    @torch.no_grad()
    def predict(self, x: np.ndarray | torch.Tensor) -> dict[str, np.ndarray]:
        """Mean and std across members, in target units (members in eval mode: dropout off).
        Regression stds are multiplied by std_scale[target] (1 when uncalibrated); member predictions are
        capped at UPPER_BOUNDS first (the regression heads are otherwise unbounded)."""
        xt = torch.as_tensor(x, dtype=torch.float32)
        outs = []
        for m in self.members:
            m.eval()
            outs.append(m(xt))
        res: dict[str, np.ndarray] = {}
        p = np.stack([torch.sigmoid(o["passed"]).numpy() for o in outs])
        res["p_pass_mean"], res["p_pass_std"] = p.mean(0), p.std(0)
        for t in REGRESSION_TARGETS:
            y = np.stack([self.encoder.unscale(t, o[t].numpy()) for o in outs])
            if t in UPPER_BOUNDS:
                y = np.minimum(y, UPPER_BOUNDS[t])
            res[f"{t}_mean"], res[f"{t}_std"] = y.mean(0), y.std(0) * self.std_scale.get(t, 1.0)
        pr = np.stack([torch.softmax(o["failure_mode"], dim=1).numpy() for o in outs])
        res["failure_mode_prob_mean"], res["failure_mode_prob_std"] = pr.mean(0), pr.std(0)
        res["failure_mode"] = np.array(self.encoder.classes, dtype=object)[res["failure_mode_prob_mean"].argmax(1)]
        return res
