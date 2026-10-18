"""Battery internal resistance growth from NASA EIS (Re, Rct): R(n) = R0 * exp(g*n), conditional on ambient temperature.

R = Re + Rct (ohm, per ~2 Ah 18650 cell, EIS 0.1 Hz-5 kHz; NOT DC resistance and NOT SOC-resolved).
Per-cell log-linear fit on valid sweeps vs. discharges completed; pooled across cells by temperature group.
Outputs models/battery_resistance_params.json, figures/battery_resistance.png
Usage: python -I fit_battery_resistance.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
I = pd.read_csv(ROOT / "data/processed/nasa_battery_impedance.csv")
I = I[I.impedance_valid].copy()
# EIS rows log the measurement temperature (24 C for the cold-aged cells); condition on the discharge (aging) ambient instead
D = pd.read_csv(ROOT / "data/processed/nasa_battery_discharge.csv")
I["ambient_c"] = I.cell.map(D.groupby("cell").ambient_c.first())
I["r_ohm"] = I.re_ohm + I.rct_ohm
rows = []
for c, g in I.groupby("cell"):
    if len(g) < 10 or g.discharges_before.nunique() < 8:
        continue
    n, y = g.discharges_before.values.astype(float), np.log(g.r_ohm.values)
    b, a = np.polyfit(n, y, 1)
    r2 = 1 - ((y - (a + b * n)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    rows.append(dict(cell=c, T=g.ambient_c.iloc[0], n=len(g), r0=np.exp(a), g=b, r2=r2, nmax=n.max()))
R = pd.DataFrame(rows)
R["ok"] = (R.r2 >= 0.5) & (R.g > 0)
print(R.round(4).to_string())
C = R[R.ok]
res = dict(source_id="F2e", kind="observed fit (NASA PCoE EIS Re+Rct), small Li-ion cells", units=dict(R="ohm per cell (EIS-derived)", g="1/discharge cycle"), groups={})
for name, mask in {"warm_20_44C": C["T"] >= 20, "cold_4C": C["T"] < 10}.items():
    s = C[mask]
    if len(s) < 3:
        continue
    lg, lr = np.log(s.g.values), np.log(s.r0.values)
    res["groups"][name] = dict(n_cells=int(len(s)), cells=s.cell.tolist(), r0_median=float(np.median(s.r0)), r0_log_mu=float(lr.mean()), r0_log_sigma=float(lr.std(ddof=1)),
                               g_log_mu=float(lg.mean()), g_log_sigma=float(lg.std(ddof=1)), g_median=float(np.exp(lg.mean())),
                               pct_growth_at_100_cycles=float(100 * (np.exp(np.exp(lg.mean()) * 100) - 1)))
w, c4 = C[C["T"] >= 20], C[C["T"] < 10]
if len(w) >= 3 and len(c4) >= 3:
    res["temperature_effect"] = dict(r0_mannwhitney_p=float(stats.mannwhitneyu(w.r0, c4.r0).pvalue), g_mannwhitney_p=float(stats.mannwhitneyu(w.g, c4.g).pvalue))
res["limitations"] = ["Not conditioned on SOC: EIS sweeps are not tied to a state of charge in this dataset",
                      "EIS Re+Rct is not DC/pulse resistance; map to DC resistance is an assumption",
                      "Small 18650 cells, ~100-200 cycle lives; pack-level resistance requires scaling assumption",
                      "Invalid EIS fits dropped (Re/Rct outside 0-1 ohm or complex); cells with poor log-linear fit excluded"]
json.dump(res, open(ROOT / "models/battery_resistance_params.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "limitations"}, indent=1)[:1800])
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for c, g in I[I.cell.isin(C.cell)].groupby("cell"):
    ax[0].plot(g.discharges_before, g.r_ohm, lw=.7, color="C0" if g.ambient_c.iloc[0] >= 20 else "C3")
ax[0].set(xlabel="discharge cycles", ylabel="Re+Rct ohm", title="Resistance growth (blue warm, red 4 C)")
ax[1].scatter(C["T"], C.g); ax[1].set(xlabel="ambient C", ylabel="growth rate g (1/cycle)")
fig.tight_layout(); fig.savefig(ROOT / "figures/battery_resistance.png", dpi=120)
