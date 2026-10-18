"""DC-link capacitor capacitance degradation from NASA PCoE electrical-stress EIS (ELECTROLYTIC 2200 uF / 10 V-rated parts stressed at 10/12/14 V).

Per capacitor: relative capacitance loss L(t) = 1 - Cs(t)/Cs(0) (Cs at 100 Hz). Fit L(t) = L_inf*(1-exp(-t/tau)) + k*t (initial saturating step + linear wear-out; a pure power law fits badly), by stress group.
Also observed time to first reach 20% loss (end of life; right-censored at the 5105 h test length).
Cross-capacitor variability of loss at 1000 h and 5000 h; stress dependence of loss at 5000 h. NO extrapolation to end of life (20% loss) beyond
what the 5105 h test shows is attempted; a transfer to film DC-link capacitors is an ASSUMPTION (flagged in output).
Usage: python -I fit_capacitor.py   (needs data/processed/nasa_capacitor_eis.csv; run extract_capacitor_eis.py first)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parent.parent
d = pd.read_csv(ROOT / "data/processed/nasa_capacitor_eis.csv")
d["loss"] = 1 - d.c_rel
rows = []
for cap, g in d.groupby("cap"):
    g = g.sort_values("aging_h").drop_duplicates("aging_h")
    sat = lambda t, linf, tau, k: linf * (1 - np.exp(-t / tau)) + k * t
    (linf, tau, k), _ = curve_fit(sat, g.aging_h.values, g.loss.values, p0=[g.loss.iloc[-1], 50, 0], bounds=([0, 1, 0], [1, 5000, 1e-3]))
    hit = g[g.loss >= 0.2]
    t20 = float(hit.aging_h.iloc[0]) if len(hit) else np.nan
    at = lambda t: float(np.interp(t, g.aging_h, g.loss))
    rows.append(dict(cap=cap, stress_v=int(g.stress_v.iloc[0]), linf=linf, tau_h=tau, k_per_h=k, t20=t20, loss_1000=at(1000), loss_5000=at(5000), loss_max=float(g.loss.max())))
R = pd.DataFrame(rows)
print(R.round(3).to_string())
out = dict(source_id="F2f", kind="observed fit (NASA electrolytic capacitors, accelerated electrical stress); transfer to film is an ASSUMPTION",
           units="relative capacitance loss (fraction of initial Cs at 100 Hz)", groups={}, time_horizon_h=float(d.aging_h.max()))
for v, s in R.groupby("stress_v"):
    out["groups"][f"{v}V"] = dict(n_caps=int(len(s)), loss_1000h_mean=float(s.loss_1000.mean()), loss_1000h_sd=float(s.loss_1000.std(ddof=1)),
                                 loss_5000h_mean=float(s.loss_5000.mean()), loss_5000h_sd=float(s.loss_5000.std(ddof=1)),
                                 loss_5000h_range=[float(s.loss_5000.min()), float(s.loss_5000.max())], linf_mean=float(s.linf.mean()),
                                 linf_sd=float(s.linf.std(ddof=1)), k_per_1000h_mean=float(1000 * s.k_per_h.mean()), k_per_1000h_sd=float(1000 * s.k_per_h.std(ddof=1)),
                                 n_reached_20pct=int(s.t20.notna().sum()), t20_h_observed=[None if np.isnan(x) else float(x) for x in s.t20],
                                 tau_h_median=float(s.tau_h.median()), tau_h_range=[float(s.tau_h.min()), float(s.tau_h.max())],
                                 frac_reaching_20pct=float((s.loss_max >= 0.2).mean()))
if R.stress_v.nunique() >= 2:
    sl = stats.linregress(R.stress_v, R.loss_5000)  # linear in volts over 10-14 V (3 levels; nonlinear in truth)
    out["stress_dependence"] = dict(loss_5000h_per_volt=float(sl.slope), p=float(sl.pvalue), r=float(sl.rvalue), n_caps=int(len(R)), voltages=sorted(R.stress_v.unique().tolist()))
out["limitations"] = ["Electrolytic capacitors (liquid electrolyte), not film; film DC-link caps age far more slowly and by different mechanisms",
                      "Accelerated stress (voltage at/above rating); not operating conditions; no temperature or ripple-current dependence",
                      "5105 h horizon; at 14 V 6 of 8 capacitors reached 20% loss within 5105 h, none at 10-12 V (see n_reached_20pct); end-of-life times are right-censored for lower stress",
                      "Loss saturates within ~100-300 h at these stresses; early dip near ~280 h and later partial recovery in Cs suggest measurement/conditioning effects not removed",
                      "8 capacitors per stress group",
                      "t20_h_observed first-crossing times below ~300 h at 14 V (23-317 h) coincide with the early conditioning dip and are NOT reliable end-of-life times; use n_reached_20pct and loss_5000h instead"]
(ROOT / "models/capacitor_degradation_params.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k in ("groups", "stress_dependence")}, indent=1)[:2500])
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
cm = {10: "C0", 12: "C1", 14: "C3"}
for cap, g in d.groupby("cap"):
    ax[0].plot(g.aging_h, g.loss * 100, color=cm[int(g.stress_v.iloc[0])], lw=.7)
ax[0].set(xscale="symlog", xlabel="aging h", ylabel="capacitance loss %", title="NASA electrolytic caps: loss by stress (10 V blue, 12 V orange)")
for v, s in R.groupby("stress_v"):
    ax[1].scatter([v] * len(s), s.loss_5000 * 100)
ax[1].set(xlabel="stress V", ylabel="loss at 5000 h %"); fig.tight_layout(); fig.savefig(ROOT / "figures/capacitor_degradation.png", dpi=120)
