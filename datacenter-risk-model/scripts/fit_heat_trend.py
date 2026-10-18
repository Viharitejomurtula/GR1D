"""Non-stationary extreme heat for the site: GEV with linear trend in location, mu(t) = mu0 + mu1*(year-2000), fitted to KABI annual maxima (dry-bulb).
Compared with the stationary GEV by AIC; return levels for 2026 and 2040 (trend extrapolation, flagged). Also hours/year above 35/38/40/42 C trend.
Outputs models/heat_trend_abilene.json. Usage: python -I fit_heat_trend.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
h = pd.read_parquet(ROOT / "data/processed/ghcnh_hourly_USW00013962.parquet").temp_c
cnt = h.groupby(h.index.year).size(); am = h.groupby(h.index.year).max()[cnt >= 6000]
yr = am.index.values.astype(float) - 2000.0; z = am.values


def nll(p, y, z):
    mu0, mu1, ls, xi = p
    return -stats.genextreme.logpdf(z, -xi, loc=mu0 + mu1 * y, scale=np.exp(ls)).sum()


c0, l0, s0 = stats.genextreme.fit(z)
stat_nll = -stats.genextreme.logpdf(z, c0, l0, s0).sum()
best = min((minimize(nll, [l0, m1, np.log(s0), -c0], args=(yr, z), method="Nelder-Mead", options=dict(maxiter=4000, xatol=1e-6, fatol=1e-8)) for m1 in (0.0, 0.03, 0.06)), key=lambda r: r.fun)
mu0, mu1, ls, xi = best.x
aic_s, aic_t = 2 * 3 + 2 * stat_nll, 2 * 4 + 2 * best.fun


def level(T, year, p=best.x):
    return stats.genextreme.ppf(1 - 1 / T, -p[3], loc=p[0] + p[1] * (year - 2000), scale=np.exp(p[2]))


rng = np.random.default_rng(0); boots = []
for _ in range(200):
    i = rng.integers(len(z), size=len(z))
    try:
        r = minimize(nll, best.x, args=(yr[i], z[i]), method="Nelder-Mead", options=dict(maxiter=3000)); boots.append(r.x)
    except Exception:
        pass
boots = np.array(boots)
rl = {f"{T}y_in_{Y}": dict(est=round(float(level(T, Y)), 1), ci95=np.percentile([level(T, Y, b) for b in boots], [2.5, 97.5]).round(1).tolist()) for Y in (2026, 2040) for T in (10, 50, 100)}
rec = h[h.index.year >= 2000]
hours = {}
for t in (35, 38, 40, 42):
    s = rec[rec > t].groupby(rec[rec > t].index.year).size().reindex(range(2000, 2026), fill_value=0)
    sl = stats.linregress(s.index.values, s.values)
    hours[str(t)] = dict(trend_per_year=float(sl.slope), p=float(sl.pvalue), fitted_2026=float(max(0, sl.intercept + sl.slope * 2026)), mean_last_5=float(s.loc[2021:].mean()), max_2000_2025=int(s.max()))
out = dict(source_id="F1c", kind="DERIVED from observed KABI hourly data; trend model", years=[int(am.index.min()), int(am.index.max())], n_years=int(len(am)),
           stationary=dict(shape_xi=float(-c0), loc=float(l0), scale=float(s0), aic=float(aic_s)),
           trend=dict(mu0_at_2000=float(mu0), mu1_per_year=float(mu1), mu1_ci95=np.percentile(boots[:, 1], [2.5, 97.5]).round(3).tolist(), scale=float(np.exp(ls)), shape_xi=float(xi), aic=float(aic_t),
                      note="lower AIC is better; a trend of mu1 C/yr in the annual-maximum location"),
           return_levels_c=rl, hours_above_dry_bulb=hours,
           limitations=["Trend extrapolation to 2040 is a projection, not data; 2026 values are near the end of the observed record",
                        "Airport station, not the campus; hours above thresholds are linear trends over 26 years", "Dry-bulb only; coincident humidity/wind/grid stress not modelled"])
(ROOT / "models/heat_trend_abilene.json").write_text(json.dumps(out, indent=1))
print(f"years {out['years']} n={len(z)}; stationary AIC {aic_s:.1f} vs trend AIC {aic_t:.1f}; mu1={mu1:.3f} C/yr CI {out['trend']['mu1_ci95']}, xi={xi:.2f}, scale={np.exp(ls):.2f}")
print({k: v["est"] for k, v in rl.items()})
print({t: (round(v["fitted_2026"], 1), round(v["mean_last_5"], 1), round(v["trend_per_year"], 2), round(v["p"], 3)) for t, v in hours.items()})
