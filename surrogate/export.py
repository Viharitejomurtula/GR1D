"""Export ensemble members to ONNX and check parity with PyTorch.

What this file is
    export() writes one ONNX file per member (opset CONFIG["onnx_opset"]) whose single output is
    MemberNet.forward_flat: [passed logit, regression heads (standardized), failure_mode logits].
    parity() runs the same encoded scenarios through PyTorch and onnxruntime and reports the largest
    absolute difference per member. Uses torch's TorchScript-based exporter (dynamo=False), which
    needs only the onnx package.

Inputs: a Surrogate (predict.Surrogate) or its Ensemble; out_dir; scenarios (sim.scenario.sample_many).
Outputs: member_<i>.onnx files; parity dict {"max_abs_diff": [...], "atol", "passed"}.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from surrogate.config import CONFIG
from surrogate.features import scenarios_to_frame
from surrogate.model import Ensemble, MemberNet


class _Flat(torch.nn.Module):
    """Wraps a MemberNet so forward() returns forward_flat (one tensor, as ONNX needs)."""

    def __init__(self, m: MemberNet):
        super().__init__()
        self.m = m

    def forward(self, x):
        return self.m.forward_flat(x)


def export(ens: Ensemble, out_dir: str | Path) -> list[Path]:
    """Write member_<i>.onnx for every member (dynamic batch dimension). Output: the file paths."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    x = torch.zeros(2, ens.encoder.n_features)
    paths = []
    for i, m in enumerate(ens.members):
        p = out_dir / f"member_{i}.onnx"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")      # the TorchScript exporter warns that it is deprecated
            torch.onnx.export(_Flat(m.eval()), (x,), str(p), opset_version=CONFIG["onnx_opset"], dynamo=False,
                              input_names=["features"], output_names=["heads"],
                              dynamic_axes={"features": {0: "n"}, "heads": {0: "n"}})
        paths.append(p)
    return paths


def parity(ens: Ensemble, onnx_paths: list[Path], scenarios) -> dict:
    """Largest |PyTorch - ONNX| per member on the encoded scenarios, against CONFIG["onnx_parity_atol"]."""
    x = ens.encoder.transform(scenarios_to_frame(scenarios))
    diffs = []
    for m, p in zip(ens.members, onnx_paths):
        with torch.no_grad():
            ref = m.eval().forward_flat(torch.as_tensor(x)).numpy()
        got = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"]).run(None, {"features": x})[0]
        diffs.append(float(np.max(np.abs(ref - got))))
    atol = CONFIG["onnx_parity_atol"]
    return {"max_abs_diff": diffs, "atol": atol, "passed": all(d <= atol for d in diffs), "n_rows": len(x)}
