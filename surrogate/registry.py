"""Which surrogate is active, and how to load it: the one place the pipeline and API get a model from.

What this file is
    SurrogateModel is the contract the pipeline relies on (ridethrough/pipeline/performance.py uses only
    this). Any model that satisfies it can be swapped in without code changes elsewhere.

    Selection (resolve()): explicit argument > env var GR1D_SURROGATE > the pointer file
    surrogate/models/ACTIVE. A value is a name under surrogate/models/ or a path to a model directory.

    Loading (load_active()/load()): the model directory's manifest.json "format" picks the loader
    (default "torch-ensemble", the format of surrogate/models/v1, when there is no manifest). A new
    architecture plugs in with register_loader("<format>", fn), fn(model_dir: Path, manifest: dict) ->
    SurrogateModel.

    This module imports only the standard library at import time (the API image has no torch or pandas); the
    torch loader imports lazily.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable

if TYPE_CHECKING:                     # the API image has numpy only: no pandas/torch imports at run time here
    import numpy as np
    import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "surrogate" / "models"
ACTIVE_FILE = MODELS_DIR / "ACTIVE"
ENV_VAR = "GR1D_SURROGATE"
DEFAULT_FORMAT = "torch-ensemble"
REGRESSION = ("recovery_margin_s", "min_power", "peak_current_pu", "floor_violation_s")


@runtime_checkable
class SurrogateModel(Protocol):
    """What the pipeline needs from a surrogate.

    classes        failure-mode labels, including "passed"
    input_fields   Scenario field names the model reads (frames passed in carry sim.scenario.FIELD_ORDER)
    provenance     dict for reports: name, version/format, what it was trained on
    predict(x)     x: list of Scenario or DataFrame with FIELD_ORDER columns -> DataFrame, one row per input,
                   in order, with p_pass_mean, p_pass_std, <t>_mean/<t>_std for t in REGRESSION,
                   failure_mode, failure_mode_prob, outside_training (";"-joined names, "" when none),
                   and prob:<class> for every class in `classes`
    member_fail_probs(x) -> (n_members, m) array of P(fail) per member; a non-ensemble model returns (1, m)
    """

    classes: list[str]
    input_fields: list[str]
    provenance: dict

    def predict(self, scenarios) -> "pd.DataFrame": ...

    def member_fail_probs(self, scenarios) -> "np.ndarray": ...


Loader = Callable[[Path, dict], SurrogateModel]
_LOADERS: dict[str, Loader] = {}


def register_loader(fmt: str, fn: Loader) -> None:
    """Register fn(model_dir, manifest) -> SurrogateModel for model dirs whose manifest says format=fmt."""
    _LOADERS[fmt] = fn


def resolve(name: str | os.PathLike | None = None) -> Path:
    """Model directory for name (or GR1D_SURROGATE, or surrogate/models/ACTIVE)."""
    val = name if name else os.environ.get(ENV_VAR) or (ACTIVE_FILE.read_text().strip() if ACTIVE_FILE.exists() else "")
    if not val:
        raise FileNotFoundError(f"no surrogate selected: pass a name, set {ENV_VAR}, or write {ACTIVE_FILE}")
    val = str(val)
    for p in (MODELS_DIR / val, Path(val)):
        if p.is_dir():
            return p.resolve()
    raise FileNotFoundError(f"surrogate {val!r}: not a directory under {MODELS_DIR} nor a path")


def manifest(model_dir: str | os.PathLike) -> dict:
    """model_dir/manifest.json, or {"format": DEFAULT_FORMAT} when absent."""
    p = Path(model_dir) / "manifest.json"
    m = json.loads(p.read_text()) if p.exists() else {}
    m.setdefault("format", DEFAULT_FORMAT)
    return m


def load(model_dir: str | os.PathLike) -> SurrogateModel:
    d = Path(model_dir)
    m = manifest(d)
    if m["format"] not in _LOADERS:
        raise KeyError(f"{d}: no loader registered for format {m['format']!r} (have {sorted(_LOADERS)})")
    model = _LOADERS[m["format"]](d, m)
    prov = {"name": m.get("name", d.name), "format": m["format"], "model_dir": _rel(d), **dict(getattr(model, "provenance", {}) or {})}
    model.provenance = prov
    return model


def load_active(name: str | os.PathLike | None = None) -> SurrogateModel:
    """Load the selected surrogate (see resolve())."""
    return load(resolve(name))


def web_json(name: str | os.PathLike | None = None) -> Path | None:
    """<active model dir>/web.json if it exists (the numpy export the API serves), else None."""
    try:
        p = resolve(name) / "web.json"
    except FileNotFoundError:
        return None
    return p if p.exists() else None


def _rel(d: Path) -> str:
    d = d.resolve()
    return str(d.relative_to(REPO_ROOT)) if d.is_relative_to(REPO_ROOT) else str(d)


def _load_torch_ensemble(d: Path, m: dict) -> SurrogateModel:
    from surrogate.predict import Surrogate     # imports torch

    sur = Surrogate.load(d)
    prov = {"n_members": len(sur.ensemble.members)}
    pp = d / "provenance.json"
    if pp.exists():
        p = json.loads(pp.read_text())
        prov.update({"simulator_commit": p.get("simulator_commit"), "dirty": p.get("dirty"), "trained_rows": p.get("n"),
                     "dataset": p.get("dataset")})
    prov.update({k: v for k, v in m.items() if k not in ("format",)})
    sur.provenance = prov
    return sur


register_loader(DEFAULT_FORMAT, _load_torch_ensemble)
