"""Train the deep ensemble on a simulator dataset.

What this file is
    train() loads a CSV (data.load), checks its provenance (warns when the simulator commit is unknown or
    the simulator had uncommitted changes), splits it 70/15/15 stratified on passed x failure_mode (so
    rare failure modes reach every split; warns when one has fewer than CONFIG["min_class_rows"] rows in
    val or test), fits the encoder on the training split, trains K members with AdamW and early stopping
    on validation loss, calibrates the regression stds on the validation split, and writes the model
    directory. Test metrics are reported on the whole test split and on the edge subset (test rows with
    |recovery_margin_s| < edge band).

Loss (per member, weights from CONFIG["loss_weights"])
    BCE(passed) + Huber(recovery_margin_s; for censored rows a one-sided hinge that penalises only
    predictions above the recorded margin) + MSE(min_power) + MSE(peak_current_pu)
    + MSE(log1p floor_violation_s) + CE(failure_mode). Regression terms on standardized targets.

Inputs: csv from data.generate; out_dir; seed; overrides (CONFIG keys to change for this run).
Outputs in out_dir: member_<i>.pt (state dicts), encoder.json, config.json, provenance.json (the
    dataset's simulator commit), split.json (row indices), calibration.json (std scale per regression
    target), metrics.json (including warnings and per-split class counts).
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from surrogate import data as sdata
from surrogate.config import CONFIG
from surrogate.features import REGRESSION_TARGETS, FeatureEncoder
from surrogate.model import Ensemble, MemberNet


def stratified_split(strata: np.ndarray, fractions: dict, seed: int) -> dict[str, np.ndarray]:
    """Row indices for train/val/test, each stratum split by the same fractions.

    strata: one label per row (train() passes "passed|failure_mode"). A stratum with 3 or more rows
    gets at least one row in val and in test; smaller strata go to train only.
    """
    rng = np.random.default_rng(seed)
    parts = {"train": [], "val": [], "test": []}
    for cls in np.unique(strata):
        idx = rng.permutation(np.flatnonzero(strata == cls))
        n = len(idx)
        n_va = max(1, int(round(fractions["val"] * n))) if n >= 3 else 0
        n_te = max(1, int(round(fractions["test"] * n))) if n >= 3 else 0
        n_tr = n - n_va - n_te
        parts["train"].append(idx[:n_tr]); parts["val"].append(idx[n_tr:n_tr + n_va]); parts["test"].append(idx[n_tr + n_va:])
    return {k: np.sort(np.concatenate(v)) for k, v in parts.items()}


def strata(d: pd.DataFrame) -> np.ndarray:
    """Stratum label per row: passed x failure_mode."""
    return (d["passed"].astype(int).astype(str) + "|" + d["failure_mode"].astype(str)).to_numpy()


def calibrate(ens: Ensemble, val: pd.DataFrame) -> dict[str, float]:
    """Std scale per regression target that makes the validation residuals unit-variance in ensemble-std
    units: scale = sqrt(mean((y - mean)^2 / std^2)) (the Gaussian-likelihood optimum). Censored rows
    are left out for recovery_margin_s; rows with zero ensemble std are left out."""
    pr = ens.predict(ens.encoder.transform(val))
    out = {}
    reg_ok = val["regression_ok"].to_numpy(bool) if "regression_ok" in val else np.ones(len(val), bool)
    for t in REGRESSION_TARGETS:
        keep = reg_ok & (~val["censored"].to_numpy(bool) if t == "recovery_margin_s" else True)
        sd = pr[f"{t}_std"] / ens.std_scale.get(t, 1.0)
        keep &= sd > 0
        z2 = ((val[t].astype(float).to_numpy() - pr[f"{t}_mean"]) / np.where(sd > 0, sd, 1.0)) ** 2
        out[t] = float(np.sqrt(z2[keep].mean())) if keep.any() else 1.0
    return out


def provenance_warnings(prov: dict) -> list[str]:
    """Problems with a dataset's provenance: unknown simulator commit, or uncommitted simulator edits."""
    out = []
    if not prov.get("simulator_commit"):
        out.append("dataset has no simulator commit recorded (" + prov.get("note", "no provenance") + ")")
    if prov.get("dirty"):
        out.append("dataset was generated with uncommitted changes in model/ or sim/")
    return out


def member_loss(out: dict, y: dict, cfg: dict) -> torch.Tensor:
    """Weighted multi-task loss for one batch (see module docstring). y holds tensors from
    FeatureEncoder.targets; failure_mode index -1 (class absent from training) is ignored."""
    w = cfg["loss_weights"]
    loss = w["passed"] * F.binary_cross_entropy_with_logits(out["passed"], y["passed"])
    ok = y["regression_ok"]                           # collapse rows: pass/fail and failure mode only
    if ok.any():
        m_pred, m_true, cens = out["recovery_margin_s"][ok], y["recovery_margin_s"][ok], y["censored"][ok]
        resid = torch.where(cens, torch.relu(m_pred - m_true), m_pred - m_true)
        loss = loss + w["recovery_margin_s"] * F.huber_loss(resid, torch.zeros_like(resid), delta=cfg["huber_delta"])
        for t in ("min_power", "peak_current_pu", "floor_violation_s"):
            loss = loss + w[t] * F.mse_loss(out[t][ok], y[t][ok])
    loss = loss + w["failure_mode"] * F.cross_entropy(out["failure_mode"], y["failure_mode"], ignore_index=-1)
    return loss


def _tensors(x: np.ndarray, y: dict) -> tuple[torch.Tensor, dict]:
    """numpy features and targets -> torch tensors."""
    yt = {k: torch.as_tensor(np.array(v), dtype=torch.long if k == "failure_mode" else torch.bool if k in ("censored", "regression_ok") else torch.float32)
          for k, v in y.items()}
    return torch.as_tensor(x, dtype=torch.float32), yt


def train_member(member: MemberNet, xtr, ytr, xva, yva, cfg: dict, seed: int) -> dict:
    """Train one member with AdamW and early stopping; restores the best validation weights.
    Output: {"epochs": run, "best_epoch", "best_val_loss"}."""
    gen = torch.Generator().manual_seed(seed)
    opt = torch.optim.AdamW(member.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    best, best_state, best_epoch, wait, epoch = float("inf"), None, -1, 0, 0
    for epoch in range(1, cfg["max_epochs"] + 1):
        member.train()
        perm = torch.randperm(len(xtr), generator=gen)
        for s in range(0, len(xtr), cfg["batch_size"]):
            b = perm[s:s + cfg["batch_size"]]
            opt.zero_grad()
            member_loss(member(xtr[b]), {k: v[b] for k, v in ytr.items()}, cfg).backward()
            opt.step()
        member.eval()
        with torch.no_grad():
            val = float(member_loss(member(xva), yva, cfg))
        if val < best:
            best, best_epoch, wait = val, epoch, 0
            best_state = {k: v.clone() for k, v in member.state_dict().items()}
        else:
            wait += 1
            if wait >= cfg["patience"]:
                break
    member.load_state_dict(best_state)
    return {"epochs": epoch, "best_epoch": best_epoch, "best_val_loss": best}


def auc(y: np.ndarray, p: np.ndarray) -> float:
    """ROC AUC by the rank (Mann-Whitney) formula; NaN when only one class is present."""
    y = y.astype(bool)
    if y.all() or not y.any():
        return float("nan")
    r = pd.Series(p).rank().to_numpy()
    return float((r[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum()))


def metrics(ens: Ensemble, d: pd.DataFrame, k_std: float) -> dict:
    """Metrics of the ensemble on rows d: passed accuracy, AUC, Brier; failure_mode accuracy; MAE per
    regression target (recovery_margin_s on uncensored rows only); fraction of errors within
    k_std x ensemble std per regression target."""
    if len(d) == 0:
        return {"n": 0}
    pr = ens.predict(ens.encoder.transform(d))
    y = d["passed"].astype(float).to_numpy()
    out = {"n": len(d), "passed_accuracy": float(((pr["p_pass_mean"] > 0.5) == y).mean()),
           "passed_auc": auc(y, pr["p_pass_mean"]), "passed_brier": float(np.mean((pr["p_pass_mean"] - y) ** 2)),
           "failure_mode_accuracy": float((pr["failure_mode"] == d["failure_mode"].to_numpy()).mean())}
    reg_ok = d["regression_ok"].to_numpy(bool) if "regression_ok" in d else np.ones(len(d), bool)
    for t in REGRESSION_TARGETS:
        keep = reg_ok & (~d["censored"].to_numpy(bool) if t == "recovery_margin_s" else True)
        err = np.abs(pr[f"{t}_mean"] - d[t].astype(float).to_numpy())[keep]
        out[f"{t}_mae"] = float(err.mean()) if keep.any() else float("nan")
        out[f"{t}_within_{k_std:g}std"] = float((err <= k_std * pr[f"{t}_std"][keep]).mean()) if keep.any() else float("nan")
        out[f"{t}_n"] = int(keep.sum())
    return out


def train(csv: str | Path, out_dir: str | Path, seed: int, overrides: dict | None = None) -> dict:
    """Train and save the ensemble. Output: the metrics dict (also written to metrics.json)."""
    cfg = {**CONFIG, **(overrides or {})}
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    d, report = sdata.load(csv)
    prov = sdata.read_provenance(csv)
    notes = provenance_warnings(prov)
    split = stratified_split(strata(d), cfg["split"], seed + cfg["split_seed_offset"])
    tr, va, te = (d.iloc[split[k]].reset_index(drop=True) for k in ("train", "val", "test"))
    counts = {k: part["failure_mode"].value_counts().to_dict() for k, part in (("train", tr), ("val", va), ("test", te))}
    for mode in sorted(d["failure_mode"].unique()):
        small = [k for k in ("val", "test") if counts[k].get(mode, 0) < cfg["min_class_rows"]]
        if small:
            notes.append(f"failure_mode {mode!r} has fewer than {cfg['min_class_rows']} rows in {', '.join(small)}")
    for n in notes:
        warnings.warn(n)
    enc = FeatureEncoder().fit_inputs(tr, categories_from=d).fit_targets(tr, classes=sorted(d["failure_mode"].unique()))
    xtr, ytr = _tensors(enc.transform(tr), enc.targets(tr))
    xva, yva = _tensors(enc.transform(va), enc.targets(va))
    ens = Ensemble.create(enc, seed, cfg["n_members"])
    history = [train_member(m, xtr, ytr, xva, yva, cfg, seed + i) for i, m in enumerate(ens.members)]
    if cfg["calibrate_std"]:
        ens.std_scale = calibrate(ens, va)
    (out_dir / "calibration.json").write_text(json.dumps(ens.std_scale, indent=2))
    for i, m in enumerate(ens.members):
        torch.save(m.state_dict(), out_dir / f"member_{i}.pt")
    enc.save(out_dir / "encoder.json")
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2))
    (out_dir / "provenance.json").write_text(json.dumps({"dataset": str(Path(csv).resolve()), **prov}, indent=2))
    (out_dir / "split.json").write_text(json.dumps({k: v.tolist() for k, v in split.items()}))
    edge = te[te["regression_ok"].astype(bool) & (te["recovery_margin_s"].abs() < cfg["edge_band_s"])]
    result = {"data": report, "seed": seed, "warnings": notes, "class_counts": counts,
              "std_scale": ens.std_scale, "members": history,
              "test": metrics(ens, te, cfg["uncertainty_k"]), "edge": metrics(ens, edge, cfg["uncertainty_k"])}
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=2))
    return result
