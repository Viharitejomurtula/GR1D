"""Export a trained ensemble for the browser and the API, and evaluate that export with numpy only.

What this file is
    export_web() writes one JSON file holding everything needed to predict without PyTorch: the
    encoder (standardization, one-hot levels, training ranges), every member's weights, the target
    scaling, the std calibration, the hard upper bounds, the failure-mode classes, the two presets'
    input values, and the model's test metrics. frontend/src/surrogate.ts evaluates it in the browser;
    WebSurrogate evaluates it in numpy for the API (whose image has no PyTorch). parity() checks the
    export against the PyTorch ensemble it came from.

    This module imports only numpy, json and the standard library, so the API can use it as-is.

Inputs: a train() output directory (surrogate/models/v1); scenarios as dicts of Scenario field -> value.
Outputs: frontend/public/data/surrogate.json (default); predictions as dicts (see WebSurrogate.predict).
Units: as in sim.scenario (inputs) and sim.grader (outputs).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = REPO_ROOT / "surrogate" / "models" / "v1"
DEFAULT_JSON = REPO_ROOT / "frontend" / "public" / "data" / "surrogate.json"
FORMAT = "gr1d-surrogate-ensemble/2"
DECIMALS = 5          # weights rounded to this many decimals in the JSON (size vs exactness; checked by parity())
BACKGROUND_N = 300    # scenarios from sim.scenario.sample_many shipped for marginal estimates (design choice)
BACKGROUND_SEED = 20261018


def export_web(model_dir: str | Path = DEFAULT_MODEL, out: str | Path = DEFAULT_JSON) -> Path:
    """Write the browser/API JSON for the ensemble in model_dir. Needs PyTorch (reads member_<i>.pt)."""
    import torch

    from sim import scenario
    from surrogate.model import HEADS, UPPER_BOUNDS
    from surrogate.predict import Surrogate

    d = Path(model_dir)
    sur = Surrogate.load(d)
    enc, cfg = sur.ensemble.encoder, json.loads((d / "config.json").read_text())
    metrics = json.loads((d / "metrics.json").read_text())
    prov = json.loads((d / "provenance.json").read_text())
    r = lambda a: np.round(np.asarray(a, dtype=np.float64), DECIMALS).tolist()  # noqa: E731

    members = []
    for m in sur.ensemble.members:
        lin = [mod for mod in m.trunk if isinstance(mod, torch.nn.Linear)]
        members.append({
            "layers": [{"w": r(l.weight.detach().numpy().T), "b": r(l.bias.detach().numpy())} for l in lin],
            "scalar": {"w": r(m.scalar.weight.detach().numpy().T), "b": r(m.scalar.bias.detach().numpy())},
            "classes": {"w": r(m.classes.weight.detach().numpy().T), "b": r(m.classes.bias.detach().numpy())},
        })
    preset = lambda p: {f: float(getattr(p, f)) for f in scenario.FIELD_ORDER}  # noqa: E731
    blob = {
        "format": FORMAT,
        "activation": "silu",
        "continuous": [{"name": f, "mean": enc.mean[f], "std": enc.std[f], "low": enc.low.get(f), "high": enc.high.get(f)}
                       for f in enc.continuous],
        "categorical": [{"name": f, "levels": levels} for f, levels in enc.categories.items()],
        "excluded": enc.excluded,
        "ood_margin_frac": cfg.get("ood_margin_frac", 0.01),
        "heads": list(HEADS),
        "targets": {t: {"mean": enc.target_mean[t], "std": enc.target_std[t], "log1p": t == "floor_violation_s",
                        "std_scale": sur.ensemble.std_scale.get(t, 1.0), "upper": UPPER_BOUNDS.get(t)}
                    for t in HEADS[1:]},
        "classes": enc.classes,
        "presets": {"grid_friendly": preset(scenario.GRID_FRIENDLY), "legacy_ups": preset(scenario.LEGACY_UPS)},
        # Real sampler draws: a marginal estimate fixes a few inputs and averages over these for the rest
        # ("hold these fixed, vary everything else"), as the results page's slider estimate does.
        "background": [[float(getattr(s, f)) for f in scenario.FIELD_ORDER]
                       for s in scenario.sample_many(BACKGROUND_N, seed=BACKGROUND_SEED)],
        "background_fields": list(scenario.FIELD_ORDER),
        "members": members,
        "metrics": {"test": metrics["test"], "edge": metrics["edge"], "n_rows": metrics["data"]["kept"]},
        "provenance": {"simulator_commit": prov.get("simulator_commit"), "dirty": prov.get("dirty"),
                       "rows": prov.get("n"), "model_dir": str(d.relative_to(REPO_ROOT)) if d.is_relative_to(REPO_ROOT) else str(d)},
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_json_safe(blob), separators=(",", ":"), allow_nan=False))
    return out


def _json_safe(v):
    """NaN/inf -> None (browsers' JSON.parse rejects NaN; e.g. an AUC that cannot be computed)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _json_safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_json_safe(x) for x in v]
    return v


def _silu(x: np.ndarray) -> np.ndarray:
    return x / (1.0 + np.exp(-x))


class WebSurrogate:
    """numpy evaluation of an export_web() JSON: the same arithmetic as frontend/src/surrogate.ts."""

    def __init__(self, path: str | Path = DEFAULT_JSON):
        self.spec = json.loads(Path(path).read_text())
        if self.spec.get("format") != FORMAT:
            raise ValueError(f"{path}: expected format {FORMAT}, got {self.spec.get('format')}")
        self.members = [{"layers": [(np.array(l["w"]), np.array(l["b"])) for l in m["layers"]],
                         "scalar": (np.array(m["scalar"]["w"]), np.array(m["scalar"]["b"])),
                         "classes": (np.array(m["classes"]["w"]), np.array(m["classes"]["b"]))}
                        for m in self.spec["members"]]

    def encode(self, scenario: dict, preset: str = "grid_friendly") -> tuple[np.ndarray, list[str]]:
        """Feature vector for one scenario (missing inputs taken from the preset) and the inputs outside
        the training range (continuous beyond low/high +/- ood_margin_frac x range; categorical level
        never seen in training)."""
        s = {**self.spec["presets"][preset], **scenario}
        x, outside = [], []
        for c in self.spec["continuous"]:
            v = float(s[c["name"]])
            x.append((v - c["mean"]) / c["std"])
            if c["low"] is not None:
                tol = self.spec["ood_margin_frac"] * (c["high"] - c["low"]) + 1e-9 * max(1.0, abs(c["low"]), abs(c["high"]))
                if v < c["low"] - tol or v > c["high"] + tol:
                    outside.append(c["name"])
        for c in self.spec["categorical"]:
            v = float(s[c["name"]])
            hit = [math.isclose(v, lv, rel_tol=1e-9, abs_tol=1e-9) for lv in c["levels"]]
            if not any(hit):
                outside.append(c["name"])
            x.extend(1.0 if h else 0.0 for h in hit)
        return np.array(x), outside

    def marginal(self, fixed: dict) -> dict:
        """Pass probability with the inputs in `fixed` held and every other input varied over the shipped
        background scenarios (the same rule as surrogate.ts marginal()). Output: pass_rate, pass_rate_std
        (spread across members of each member's average), mode (most common predicted non-pass failure mode
        or None), mode_share, outside_training (fixed inputs beyond the training range)."""
        fields = self.spec["background_fields"]
        per_member, modes = np.zeros(len(self.members)), {}
        for row in self.spec["background"]:
            s = {**dict(zip(fields, row)), **fixed}
            x, _ = self.encode(s)
            ps, pr = [], []
            for m in self.members:
                h = x
                for w, b in m["layers"]:
                    h = _silu(h @ w + b)
                ps.append(1.0 / (1.0 + math.exp(-(h @ m["scalar"][0] + m["scalar"][1])[0])))
                z = h @ m["classes"][0] + m["classes"][1]
                pr.append(np.exp(z - z.max()) / np.exp(z - z.max()).sum())
            per_member += np.array(ps)
            mode = self.spec["classes"][int(np.mean(pr, axis=0).argmax())]
            if mode != "passed":
                modes[mode] = modes.get(mode, 0) + 1
        per_member /= len(self.spec["background"])
        top = max(modes.items(), key=lambda kv: kv[1]) if modes else (None, 0)
        _, outside = self.encode(fixed)
        return {"pass_rate": float(per_member.mean()), "pass_rate_std": float(per_member.std()),
                "mode": top[0], "mode_share": top[1] / len(self.spec["background"]),
                "outside_training": [f for f in outside if f in fixed]}

    def predict(self, scenario: dict, preset: str = "grid_friendly") -> dict:
        """One prediction. Output: p_pass_mean, p_pass_std, <target>_mean/_std for each regression target
        (calibrated std, capped at its upper bound), failure_mode, failure_mode_probs {class: p},
        outside_training [names], and preset."""
        x, outside = self.encode(scenario, preset)
        heads, targets = self.spec["heads"], self.spec["targets"]
        p_pass, reg, probs = [], {t: [] for t in heads[1:]}, []
        for m in self.members:
            h = x
            for w, b in m["layers"]:
                h = _silu(h @ w + b)
            sc = h @ m["scalar"][0] + m["scalar"][1]
            p_pass.append(1.0 / (1.0 + math.exp(-sc[0])))
            for i, t in enumerate(heads[1:], start=1):
                spec = targets[t]
                y = sc[i] * spec["std"] + spec["mean"]
                y = math.expm1(y) if spec["log1p"] else y
                reg[t].append(min(y, spec["upper"]) if spec["upper"] is not None else y)
            z = h @ m["classes"][0] + m["classes"][1]
            e = np.exp(z - z.max())
            probs.append(e / e.sum())
        out = {"p_pass_mean": float(np.mean(p_pass)), "p_pass_std": float(np.std(p_pass))}
        for t in heads[1:]:
            out[f"{t}_mean"] = float(np.mean(reg[t]))
            out[f"{t}_std"] = float(np.std(reg[t]) * targets[t]["std_scale"])
        pm = np.mean(probs, axis=0)
        out["failure_mode"] = self.spec["classes"][int(pm.argmax())]
        out["failure_mode_probs"] = {c: float(p) for c, p in zip(self.spec["classes"], pm)}
        out["outside_training"] = outside
        out["preset"] = preset
        return out


def parity(model_dir: str | Path = DEFAULT_MODEL, path: str | Path = DEFAULT_JSON, n: int = 500, seed: int = 0) -> dict:
    """Largest difference between WebSurrogate (the JSON, rounded weights) and the PyTorch ensemble on
    sample_many(n, seed) scenarios, per output. Needs PyTorch."""
    from sim import scenario
    from surrogate.features import REGRESSION_TARGETS
    from surrogate.predict import Surrogate

    scs = scenario.sample_many(n, seed=seed)
    ref = Surrogate.load(model_dir).predict(scs)
    web = WebSurrogate(path)
    got = [web.predict({f: float(getattr(s, f)) for f in scenario.FIELD_ORDER}) for s in scs]
    cols = ["p_pass_mean", "p_pass_std"] + [f"{t}_{k}" for t in REGRESSION_TARGETS for k in ("mean", "std")]
    diff = {c: float(np.max(np.abs(ref[c].to_numpy() - np.array([g[c] for g in got])))) for c in cols}
    diff["failure_mode_agree"] = float(np.mean(ref["failure_mode"].to_numpy() == np.array([g["failure_mode"] for g in got])))
    return diff


if __name__ == "__main__":
    import sys
    p = export_web(*(sys.argv[1:3]))
    print(f"exported -> {p} ({p.stat().st_size / 1024:.0f} KB)")
    print("parity vs PyTorch:", json.dumps(parity(*(sys.argv[1:3])), indent=1))
