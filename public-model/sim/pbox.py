"""Imprecise-probability layer: epistemic (no-data) parameters are bounded intervals, NOT distributions.
Outer loop: LHS + random corners over the EP box (parameters fixed via do()). Inner loop: aleatory Monte Carlo.
Reports [min, max] of each outcome over the box, plus first-order sensitivity of each EP parameter (binned main effects)."""
import numpy as np
from network import net, EP, OUTCOMES

def lhs(m, d, rng):
    u = np.stack([(rng.permutation(m) + rng.uniform(size=m)) / m for _ in range(d)], 1); return u

def run(n_out=300, n_in=1500, n_corners=100, seed=0, fixed=None):
    rng = np.random.default_rng(seed); names = list(EP); lo = np.array([EP[k][0] for k in names]); hi = np.array([EP[k][1] for k in names])
    U = np.vstack([lhs(n_out, len(names), rng), rng.integers(0, 2, (n_corners, len(names))).astype(float)])
    rows = []
    for u in U:
        th = lo + u * (hi - lo); do = {"ep_" + k: v for k, v in zip(names, th)}; do.update({"ep_" + k: v for k, v in (fixed or {}).items()})
        s = net.sample(n_in, rng, do=do); rows.append([f(s) for f in OUTCOMES.values()])
    return names, U, np.array(rows), list(OUTCOMES)

def main_effects(U, y, bins=6):
    out = []
    for j in range(U.shape[1]):
        idx = np.minimum((U[:, j] * bins).astype(int), bins - 1)
        m = np.array([y[idx == b].mean() if (idx == b).any() else y.mean() for b in range(bins)]); out.append(m.var() / (y.var() + 1e-12))
    return np.array(out)

if __name__ == "__main__":
    names, U, Y, on = run()
    print("outcome                 min      p5     p50     p95     max   (over epistemic box)")
    for i, o in enumerate(on):
        y = Y[:, i]; print(f"{o:22} {y.min():7.3f} {np.percentile(y,5):7.3f} {np.percentile(y,50):7.3f} {np.percentile(y,95):7.3f} {y.max():7.3f}")
    for i, o in enumerate(on[:3]):
        S = main_effects(U, Y[:, i]); order = np.argsort(-S)
        print(f"\nmain-effect share of epistemic variance in {o}:"); [print(f"   {names[j]:16} {S[j]:.2f}") for j in order[:6]]
