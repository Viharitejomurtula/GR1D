import sys, json, numpy as np, sobol
from network import OUTCOMES
label, fixed, N = sys.argv[1], json.loads(sys.argv[2]), int(sys.argv[3]); on = list(OUTCOMES)
names, s1, st, ci1, cit, Y = sobol.jansen(N=N, n_in=1200, fixed=fixed, seed=11)
print(f"### {label}  fixed={fixed}  N={N}  d={len(names)}")
print("ranges over the box:", "; ".join(f"{o} [{Y[:, j].min():.2f},{Y[:, j].max():.2f}]" for j, o in enumerate(on)))
for j in (0, 3, 4):
    print(f"-- ST for {on[j]} (90% CI)")
    for i in np.argsort(-st[:, j])[:8]: print(f"   {names[i]:16} {st[i, j]:5.2f} [{cit[0, i, j]:.2f},{cit[1, i, j]:.2f}]")
