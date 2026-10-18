import sys, numpy as np, sobol
from network import OUTCOMES
ud = float(sys.argv[1]); N = int(sys.argv[2]); on = list(OUTCOMES)
names, s1, st, ci1, cit, Y = sobol.jansen(N=N, n_in=1200, fixed={"units_down": ud}, seed=7)
print(f"### units_down={ud}  N={N}  d={len(names)}")
print("outcome ranges over the box:", "; ".join(f"{o} [{Y[:, j].min():.2f},{Y[:, j].max():.2f}]" for j, o in enumerate(on)))
for j in (0, 3, 4):
    print(f"-- ST for {on[j]}  (90% bootstrap CI)")
    for i in np.argsort(-st[:, j])[:9]: print(f"   {names[i]:16} {st[i, j]:5.2f} [{cit[0, i, j]:.2f},{cit[1, i, j]:.2f}]")
