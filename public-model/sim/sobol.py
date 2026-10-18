"""Global sensitivity over the epistemic (assumed) intervals: Saltelli/Jansen first-order (S1) and total-order (ST) indices of each
outcome, with common random numbers in the inner loop and bootstrap CIs. Maintenance states are run as SEPARATE scenarios."""
import sys, numpy as np
from network import net, EP, OUTCOMES

def evaluate(U, names, lo, hi, n_in, fixed):
    out = np.empty((len(U), len(OUTCOMES)))
    for i, u in enumerate(U):
        th = lo + u * (hi - lo); do = {"ep_" + k: v for k, v in zip(names, th)}; do.update({"ep_" + k: v for k, v in fixed.items()})
        s = net.sample(n_in, np.random.default_rng(12345), do=do)           # common random numbers
        out[i] = [f(s) for f in OUTCOMES.values()]
    return out

def jansen(N=120, n_in=1200, seed=0, fixed=None, boots=100):
    fixed = fixed or {}; rng = np.random.default_rng(seed); names = [k for k in EP if k not in fixed]; d = len(names)
    lo = np.array([EP[k][0] for k in names]); hi = np.array([EP[k][1] for k in names])
    A, B = rng.uniform(size=(N, d)), rng.uniform(size=(N, d))
    yA, yB = evaluate(A, names, lo, hi, n_in, fixed), evaluate(B, names, lo, hi, n_in, fixed)
    yAB = []
    for i in range(d):
        ABi = A.copy(); ABi[:, i] = B[:, i]; yAB.append(evaluate(ABi, names, lo, hi, n_in, fixed))
    yAB = np.array(yAB)                                                    # (d, N, outcomes)
    def idx(ix):
        a, b, ab = yA[ix], yB[ix], yAB[:, ix]; v = np.var(np.concatenate([a, b]), axis=0) + 1e-12
        s1 = (v - 0.5 * np.mean((b[None] - ab) ** 2, axis=1)) / v; st = 0.5 * np.mean((a[None] - ab) ** 2, axis=1) / v; return s1, st
    s1, st = idx(np.arange(N)); bs1, bst = [], []
    for _ in range(boots):
        ix = rng.integers(0, N, N); a, b = idx(ix); bs1.append(a); bst.append(b)
    return names, s1, st, np.percentile(bs1, [5, 95], 0), np.percentile(bst, [5, 95], 0), np.vstack([yA, yB])

def report(label, fixed, N=120):
    names, s1, st, ci1, cit, Y = jansen(N=N, fixed=fixed); on = list(OUTCOMES)
    print(f"\n=== {label} === outcome ranges over the box: " + "; ".join(f"{o} [{Y[:, j].min():.2f},{Y[:, j].max():.2f}]" for j, o in enumerate(on[:2])))
    for j in (0, 3):
        print(f"-- total-order index (ST, 90% CI) for {on[j]}")
        for i in np.argsort(-st[:, j])[:8]: print(f"   {names[i]:16} ST={st[i, j]:5.2f} [{cit[0, i, j]:.2f},{cit[1, i, j]:.2f}]  S1={s1[i, j]:5.2f}")

if __name__ == "__main__":
    report("all units up", {"units_down": 0.0}); report("one unit down", {"units_down": 1.0})
