"""Neural surrogate: imitate the simulator fast enough to run in a browser.

The simulator needs OpenModelica, which is why exposing it to a user means standing up a
server. This learns the same input-to-verdict mapping as a small network whose weights
export to JSON, so the frontend evaluates it directly with no runtime dependency and no
network call.

Three heads, because the UI needs three different things:
  pass probability   - the headline verdict
  recovery margin    - a smooth signal; pass/fail alone gives the network almost nothing
                       to learn near the boundary, which is exactly where it matters
  failure mode       - which of the graded mechanisms, for the report card

An ensemble gives uncertainty for free: where the members disagree, the surrogate is
guessing, and those are the scenarios worth re-running in the real simulator.

IMPORTANT: a surrogate reproduces whatever it was trained on, bugs included. Retrain
after any change to the simulator.
"""

from __future__ import annotations

import csv
import json
import pathlib

import numpy as np
import torch
import torch.nn as nn

from .scenario import FIELD_ORDER

REPO = pathlib.Path(__file__).resolve().parent.parent
MODES = (
    "passed", "exceeded 125% current cap", "cooling tripped",
    "PSU shutdown and restart delay", "below power floor",
    "storage hand-back too slow", "disconnected inside envelope", "no disturbance",
)


class Surrogate(nn.Module):
    def __init__(self, n_in: int, n_modes: int, width: int = 128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(n_in, width), nn.ReLU(),
            nn.Linear(width, width), nn.ReLU(),
        )
        self.head_pass = nn.Linear(width, 1)
        self.head_margin = nn.Linear(width, 1)
        self.head_mode = nn.Linear(width, n_modes)

    def forward(self, x):
        h = self.trunk(x)
        return self.head_pass(h).squeeze(-1), self.head_margin(h).squeeze(-1), self.head_mode(h)


def load(path: str | pathlib.Path = None) -> tuple[np.ndarray, dict]:
    path = pathlib.Path(path) if path else REPO / "data" / "runs.csv"
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise SystemExit(f"no rows in {path}")

    def val(v: str) -> float:
        # Booleans round-trip through the CSV as "True"/"False".
        if v in ("True", "False"):
            return 1.0 if v == "True" else 0.0
        return float(v)

    X = np.array([[val(r[f]) for f in FIELD_ORDER] for r in rows], dtype=np.float32)
    y_pass = np.array([float(r["passed"]) for r in rows], dtype=np.float32)
    # Clamp the margin: runs that never recover carry a value set by window length rather
    # than severity, and that tail would dominate the regression loss.
    y_margin = np.clip(
        np.array([float(r["recovery_margin_s"]) for r in rows], dtype=np.float32), -3.0, 2.0
    )
    mode_ix = {m: i for i, m in enumerate(MODES)}
    y_mode = np.array([mode_ix.get(r["failure_mode"], 0) for r in rows], dtype=np.int64)
    return X, {"pass": y_pass, "margin": y_margin, "mode": y_mode}


def train(
    n_members: int = 5,
    epochs: int = 300,
    data: str | pathlib.Path = None,
    seed: int = 0,
    quiet: bool = False,
) -> dict:
    X, y = load(data)
    n = len(X)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    cut = int(n * 0.8)
    tr, te = perm[:cut], perm[cut:]

    mu, sd = X[tr].mean(0), X[tr].std(0)
    sd[sd < 1e-8] = 1.0
    Xn = (X - mu) / sd

    members, reports = [], []
    for m in range(n_members):
        torch.manual_seed(seed + m)
        net = Surrogate(X.shape[1], len(MODES))
        opt = torch.optim.Adam(net.parameters(), lr=3e-3)
        bce, mse, ce = nn.BCEWithLogitsLoss(), nn.MSELoss(), nn.CrossEntropyLoss()

        xt = torch.tensor(Xn[tr])
        tp, tm, tc = torch.tensor(y["pass"][tr]), torch.tensor(y["margin"][tr]), torch.tensor(y["mode"][tr])
        for ep in range(epochs):
            opt.zero_grad()
            p, mg, md = net(xt)
            loss = bce(p, tp) + 0.3 * mse(mg, tm) + 0.5 * ce(md, tc)
            loss.backward()
            opt.step()

        net.eval()
        with torch.no_grad():
            p, mg, md = net(torch.tensor(Xn[te]))
            acc = ((torch.sigmoid(p) > 0.5).numpy() == y["pass"][te]).mean()
            mae = float(np.abs(mg.numpy() - y["margin"][te]).mean())
            macc = (md.argmax(1).numpy() == y["mode"][te]).mean()
        members.append(net)
        reports.append({"pass_acc": float(acc), "margin_mae": mae, "mode_acc": float(macc)})
        if not quiet:
            print(f"  member {m}: pass {acc:.1%}  margin MAE {mae:.3f}s  mode {macc:.1%}")

    # Boundary accuracy is the number that matters: predicting an obvious pass or an obvious
    # failure is easy, and the UI lives on the edge.
    with torch.no_grad():
        Xte = torch.tensor(Xn[te])
        probs = np.stack([torch.sigmoid(m(Xte)[0]).numpy() for m in members])
    mean_p = probs.mean(0)
    edge = (mean_p > 0.25) & (mean_p < 0.75)
    edge_acc = ((mean_p[edge] > 0.5) == y["pass"][te][edge]).mean() if edge.sum() else float("nan")

    return {
        "members": members, "mu": mu, "sd": sd, "reports": reports,
        "n_train": len(tr), "n_test": len(te),
        "ensemble_acc": float(((mean_p > 0.5) == y["pass"][te]).mean()),
        "edge_acc": float(edge_acc), "n_edge": int(edge.sum()),
        "disagreement": float(probs.std(0).mean()),
    }


def export(trained: dict, out: str | pathlib.Path = None) -> pathlib.Path:
    """Write weights as JSON. The frontend does the forward pass directly."""
    out = pathlib.Path(out) if out else REPO / "frontend" / "public" / "data" / "surrogate.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Weights round to 4 decimals: inference is unaffected and the JSON shrinks several-fold,
    # which matters when the frontend loads this on every page view.
    def r(a):
        # Widen before rounding: rounding a float32 and then calling tolist() re-expands it
        # to the full float64 repr (0.12349999696...), which defeats the point entirely.
        return np.round(np.asarray(a, dtype=np.float64), 4).tolist()

    def layers(net):
        return [
            {"w": r(m.weight.detach().numpy().T), "b": r(m.bias.detach().numpy())}
            for m in [net.trunk[0], net.trunk[2]]
        ] , {
            "pass": {"w": r(net.head_pass.weight.detach().numpy().T),
                     "b": r(net.head_pass.bias.detach().numpy())},
            "margin": {"w": r(net.head_margin.weight.detach().numpy().T),
                       "b": r(net.head_margin.bias.detach().numpy())},
            "mode": {"w": r(net.head_mode.weight.detach().numpy().T),
                     "b": r(net.head_mode.bias.detach().numpy())},
        }

    members = []
    for net in trained["members"]:
        trunk, heads = layers(net)
        members.append({"trunk": trunk, "heads": heads})

    blob = {
        "inputs": list(FIELD_ORDER),
        "modes": list(MODES),
        "mu": r(trained["mu"]),
        "sd": r(trained["sd"]),
        "members": members,
        "accuracy": {
            "ensemble": trained["ensemble_acc"],
            "boundary": trained["edge_acc"],
            "n_train": trained["n_train"],
            "n_test": trained["n_test"],
        },
    }
    out.write_text(json.dumps(blob))
    return out


if __name__ == "__main__":
    t = train()
    print(f"\nensemble pass accuracy : {t['ensemble_acc']:.1%}")
    print(f"accuracy near boundary : {t['edge_acc']:.1%}  (n={t['n_edge']})")
    print(f"mean ensemble spread   : {t['disagreement']:.3f}")
    p = export(t)
    print(f"exported -> {p}  ({p.stat().st_size / 1024:.0f} KB)")
