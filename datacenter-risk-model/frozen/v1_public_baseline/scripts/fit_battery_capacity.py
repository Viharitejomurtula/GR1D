"""Fit NMC-proxy capacity fade from NASA cells: soh(n) = exp(-k n), k varies cell to cell.

Per-cell k from log-linear regression on valid discharges; keep clean cells only
(start SOH 0.85-1.05 of rated, R2 >= 0.7, >= 20 cycles). Pooled lognormal for k with
bootstrap CIs. Writes models/battery_capacity_params.json and figures/battery_capacity_fade.png.
Usage: python -I fit_battery_capacity.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path(".")
D = pd.read_csv(ROOT / "data/processed/nasa_battery_discharge.csv")
D = D[D.capacity_valid]

rows = []
for c, g in D.groupby("cell"):
    n, y = g.discharge_n.values, np.log(g.soh_vs_rated.values)
    if len(g) < 20:
        continue
    b, a = np.polyfit(n, y, 1)
    r2 = 1 - ((y - (a + b * n)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    rows.append(dict(cell=c, ambient_c=g.ambient_c.iloc[0], n=len(g), s0=np.exp(a), k=-b, r2=r2, max_cycle=n.max()))
R = pd.DataFrame(rows)
R["clean"] = R.s0.between(0.85, 1.05) & (R.r2 >= 0.7) & (R.k > 0)
C = R[R.clean]
warm = C[C.ambient_c >= 20]
print(R.round(4).to_string())
print(f"\nclean cells: {len(C)} (warm 20-44C: {len(warm)}, cold 4C: {(C.ambient_c < 10).sum()})")

lk = np.log(warm.k.values)
mu, sd = lk.mean(), lk.std(ddof=1)
rng = np.random.default_rng(0)
boot = [(lambda s: (s.mean(), s.std(ddof=1)))(rng.choice(lk, len(lk))) for _ in range(5000)]
mu_ci = np.percentile([b[0] for b in boot], [2.5, 97.5]).tolist()
sd_ci = np.percentile([b[1] for b in boot], [2.5, 97.5]).tolist()
rho, p = stats.spearmanr(warm.ambient_c, warm.k)
sw = stats.shapiro(lk)
print(f"lognormal k: mu={mu:.3f} (CI {mu_ci}) sigma={sd:.3f} (CI {sd_ci}); median k={np.exp(mu):.5f}/cycle")
print(f"k vs temperature (warm cells): spearman rho={rho:.2f} p={p:.2f}; Shapiro on log k p={sw.pvalue:.2f}")

cycles_to_eol = np.log(1 / 0.7) / np.exp(rng.normal(mu, sd, 100000))
q = np.percentile(cycles_to_eol, [5, 50, 95]).round(0).tolist()
print("cycles to 70% SOH (5/50/95%):", q)

params = dict(model="soh(n) = exp(-k*n), SOH relative to initial; k ~ LogNormal(mu, sigma) per cell",
              source_id="F2d", kind="observed fit (NASA PCoE, small Li-ion 18650 cells, ~2 Ah)",
              units=dict(k="1/discharge cycle"), mu_log_k=mu, sigma_log_k=sd, mu_ci95=mu_ci, sigma_ci95=sd_ci,
              n_cells=int(len(warm)), cells=warm.cell.tolist(), temp_range_c=[float(warm.ambient_c.min()), float(warm.ambient_c.max())],
              temp_effect=dict(spearman_rho=float(rho), p=float(p), note="not significant at this sample size" if p > 0.05 else "significant"),
              cycles_to_70pct_soh_5_50_95=q,
              limitations=["10 cells; temperature dependence not resolved", "4C cells excluded: reversible cold capacity loss confounds fade (only 1 clean cold cell)",
                           "cycles at 1.5A charge / 2A discharge (~1C), constant conditions; no calendar aging or SOC/DoD dependence",
                           "small 18650 cells, not NMC-specific; transfer to a data-center UPS/BESS pack is an assumption"])
(ROOT / "models").mkdir(exist_ok=True)
json.dump(params, open(ROOT / "models/battery_capacity_params.json", "w"), indent=2)

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for c, g in D[D.cell.isin(warm.cell)].groupby("cell"):
    ax[0].plot(g.discharge_n, g.soh_vs_rated / warm.set_index("cell").s0[c], lw=.8, alpha=.7)
nn = np.arange(0, 200)
ax[0].plot(nn, np.exp(-np.exp(mu) * nn), "k", lw=2, label="median k")
ax[0].fill_between(nn, np.exp(-np.exp(mu + 1.645 * sd) * nn), np.exp(-np.exp(mu - 1.645 * sd) * nn), color="k", alpha=.15, label="5-95% of k")
ax[0].set(xlabel="discharge cycle", ylabel="SOH relative to initial", title="Clean warm cells (20-44 C)"); ax[0].legend()
ax[1].scatter(warm.ambient_c, warm.k, c="C0"); ax[1].set(xlabel="ambient C", ylabel="fade rate k (1/cycle)", title=f"k vs temperature (rho={rho:.2f}, p={p:.2f})")
fig.tight_layout(); (ROOT / "figures").mkdir(exist_ok=True); fig.savefig(ROOT / "figures/battery_capacity_fade.png", dpi=120)
