"""Frequency-event model v2 from ERCOT monthly Operations Report event tables (n=311 events, Nov 2018 - Sep 2025; includes nadir/peak).

Stage 1 (event size): annual Poisson rate of under-frequency events (ERCOT reporting criteria: dF>=60 mHz or loss>=350 MW or RRS deployment) and a
  generalized-Pareto tail for MW loss above a threshold (extrapolates beyond the largest observed trip, 2,519 MW).
Stage 2 (nadir given size): log(depth) = a + b log(MW) + c log(inertia) + eps, eps ~ Normal(0, s) (observed relationship, weak R2).
Combining gives annual exceedance rates of nadir thresholds, with bootstrap CIs. A direct GPD on nadir depth is fitted as an independent cross-check.
Everything below the observed range is interpolation; thresholds below ~59.7 Hz are EXTRAPOLATION and the table excludes system-collapse events (Feb 2021).
Over-frequency (load-loss) events fitted with a small regression + empirical rate.
Outputs models/frequency_event_model.json, figures/frequency_events.png.  Usage: python -I fit_frequency_events.py
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
E = pd.read_csv(ROOT / "data/processed/ercot_frequency_events.csv", parse_dates=["datetime"])
years = (E.datetime.max() - E.datetime.min()).days / 365.25
U = E[(E.max_min_freq_hz < 60) & (E.mw_loss > 0)].copy()
U["depth"] = 60 - U.max_min_freq_hz
U["H"] = U.inertia_gws / 1000.0  # GW*s
T0 = pd.Timestamp("2018-11-01"); U["yr"] = (U.datetime - T0).dt.days / 365.25
YR_REF = float((E.datetime.max() - T0).days / 365.25)  # latest observed time: model evaluated at current grid response
O = E[E.max_min_freq_hz > 60].copy(); O["excess"] = O.max_min_freq_hz - 60
rate = len(U) / years
rng = np.random.default_rng(0)
THR_MW = float(U.mw_loss.quantile(0.9))
THRESHOLDS = [59.9, 59.8, 59.7, 59.6, 59.5, 59.4, 59.3]  # nadir levels (Hz)


def fit_stage2(d):
    X = np.column_stack([np.ones(len(d)), np.log(d.mw_loss), np.log(d.H), d.yr]); y = np.log(d.depth)
    b = np.linalg.lstsq(X, y, rcond=None)[0]; res = y - X @ b
    return b, res.std(ddof=4)


def fit_gpd(d):
    ex = d.mw_loss[d.mw_loss > THR_MW].values - THR_MW
    c, _, s = stats.genpareto.fit(ex, floc=0)
    return c, s, len(ex) / len(d)


def simulate(b, s2, c, s, p_exc, d, n_years=2000, yr=None):
    """Annual exceedance rate of nadir thresholds by Monte Carlo over events."""
    n = int(n_years * rate)
    is_exc = rng.uniform(size=n) < p_exc
    body = rng.choice(d.mw_loss.values[d.mw_loss.values <= THR_MW], n)
    tail = THR_MW + stats.genpareto.rvs(c, 0, s, size=n, random_state=rng)
    mw = np.where(is_exc, tail, body)
    H = rng.choice(d.H.values, n)
    yr = YR_REF if yr is None else yr
    depth = np.exp(b[0] + b[1] * np.log(mw) + b[2] * np.log(H) + b[3] * yr + rng.normal(0, s2, n))
    nadir = 60 - depth
    return {t: float((nadir < t).sum() / n_years) for t in THRESHOLDS}, mw, nadir


b, s2 = fit_stage2(U)
c, s, p_exc = fit_gpd(U)
base, mw_s, nad_s = simulate(b, s2, c, s, p_exc, U)
legacy, _, _ = simulate(b, s2, c, s, p_exc, U, yr=0.5)  # sensitivity: 2019-level grid response
boots = []
for _ in range(150):
    d = U.sample(len(U), replace=True, random_state=int(rng.integers(1e9)))
    try:
        bb, ss = fit_stage2(d); cc, sc, pe = fit_gpd(d)
        boots.append(simulate(bb, ss, cc, sc, pe, d, n_years=500)[0])
    except Exception:
        pass
ci = {t: np.percentile([x[t] for x in boots], [2.5, 97.5]).round(4).tolist() for t in THRESHOLDS}
# cross-check: direct GPD on depth
u_d = float(U.depth.quantile(0.9)); ex_d = U.depth[U.depth > u_d].values - u_d
cd, _, sd_ = stats.genpareto.fit(ex_d, floc=0); pd_ = len(ex_d) / len(U)
direct = {t: float(rate * pd_ * stats.genpareto.sf(60 - t - u_d, cd, 0, sd_)) if 60 - t > u_d else float((U.depth > 60 - t).mean() * rate) for t in THRESHOLDS}
obs = {t: float((U.max_min_freq_hz < t).sum() / years) for t in THRESHOLDS}
# MW-loss return levels
mwrl = {f"{T}y": round(float(THR_MW + stats.genpareto.ppf(1 - 1 / (T * rate * p_exc), c, 0, s)), 0) for T in (1, 5, 10, 50, 100)}
# over-frequency
of = None
if len(O) >= 8:
    O2 = O[O.mw_loss.abs() > 0]; X = np.column_stack([np.ones(len(O2)), np.log(O2.mw_loss.abs())]); y = np.log(O2.excess)
    bo = np.linalg.lstsq(X, y, rcond=None)[0]; so = (y - X @ bo).std(ddof=2)
    of = dict(n=int(len(O2)), rate_per_year=round(len(O) / years, 2), log_excess_intercept=float(bo[0]), log_excess_slope=float(bo[1]), resid_sigma=float(so),
              max_peak_hz=float(O.max_min_freq_hz.max()), max_abs_mw=float(O2.mw_loss.abs().max()))
# Systemic-scarcity regime (Uri-class). EVIDENCE (primary: ERCOT House Energy & Commerce slides 2021-03-24, p12/p19; FERC-NERC joint report 2021-11, p231):
# two documented ERCOT events in the window Jan 2011 - Sep 2025: Feb 2011 (lowest frequency 59.58 Hz, 4,000 MW shed, 7.5 h) and Feb 2021 (lowest 59.302 Hz,
# below 59.4 Hz for 4 m 23 s, 20,000 MW peak shed, 70.5 h, 52,277 MW cumulative outages). Rate posterior Gamma(0.5 + k, T) with Jeffreys prior.
SYS_EVENTS = [dict(date="2011-02-02", lowest_freq_hz=59.58, max_load_shed_mw=4000, shed_duration_h=7.5, peak_load_without_shed_mw=59000, cumulative_outages_mw=14702),
              dict(date="2021-02-15", lowest_freq_hz=59.30, nadir_detail_hz=59.302, max_load_shed_mw=20000, shed_duration_h=70.5, peak_load_without_shed_mw=76819,
                   cumulative_outages_mw=52277, below_59_4_hz_s=263, load_shed_orders_mw=[1000, 5000, 8500, 10500])]
T_SYS = (pd.Timestamp("2025-09-30") - pd.Timestamp("2011-01-01")).days / 365.25
post = stats.gamma(a=0.5 + len(SYS_EVENTS), scale=1 / T_SYS)
nlo, nhi = 59.302, 59.58
def p_below(t): return float(np.clip((t - nlo) / (nhi - nlo), 0, 1))
sens = {}
for lam in (0.02, 0.07, float(post.median()), 0.3):
    sens[f"{lam:.2f}"] = {f"P(year min nadir<{t})": round(float((1 - np.exp(-lam)) * p_below(t)), 4) for t in (59.7, 59.5, 59.4, 59.3)}
systemic = dict(events=SYS_EVENTS, window=["2011-01-01", "2025-09-30"], exposure_years=round(T_SYS, 2), rate_mle_per_year=round(len(SYS_EVENTS) / T_SYS, 3),
                rate_posterior_median=float(post.median()), rate_ci95=post.ppf([0.025, 0.975]).round(3).tolist(),
                conditional_nadir=dict(distribution="Uniform(59.302, 59.58) Hz between the two documented events (2 data points: scenario-grade)", low=nlo, high=nhi),
                sensitivity_annual_probability_by_rate=sens,
                note="Rate evidence is 2 events / 14.7 years (credible interval wide); events defined as ERCOT cold-weather/scarcity emergencies with firm load shed. Earlier events (e.g. 1989) not used. "
                     "In-regime nadir comes from 2 events only. Units: rate per year.")
out = dict(source_id="F1a-ev1", kind="observed events (ERCOT monthly Operations Reports, n=%d) + two-stage model; extrapolation beyond observed range is MODELED" % len(E),
           units="Hz nadir; MW loss; rates per year", years_covered=round(years, 2), span=[str(E.datetime.min()), str(E.datetime.max())],
           under_frequency=dict(n=int(len(U)), rate_per_year=round(rate, 1), observed_min_nadir_hz=float(U.max_min_freq_hz.min()),
                                observed_max_mw_loss=float(U.mw_loss.max()),
                                stage1_gpd_mw=dict(threshold_mw=THR_MW, shape=float(c), scale=float(s), p_exceed=float(p_exc), return_levels_mw=mwrl),
                                stage2_nadir=dict(formula="log(depth) = a + b log(MW) + c log(inertia GW*s) + d*years_since_2018-11 + eps; evaluated at yr_ref (latest observed)", a=float(b[0]), b_mw=float(b[1]), c_inertia=float(b[2]), d_year=float(b[3]), yr_ref=YR_REF, eps_sigma=float(s2), r2_note="~0.6 with year term (0.25 without)"),
                                annual_rate_nadir_below_legacy_response_2019=dict(hz=THRESHOLDS, model=[legacy[t] for t in THRESHOLDS]),
                                annual_rate_nadir_below=dict(hz=THRESHOLDS, observed=[obs[t] for t in THRESHOLDS], model=[base[t] for t in THRESHOLDS],
                                                             model_ci95=[ci[t] for t in THRESHOLDS], direct_gpd_depth=[direct[t] for t in THRESHOLDS]),
                                cross_check_direct_gpd=dict(threshold_depth_hz=u_d, shape=float(cd), scale=float(sd_))),
           over_frequency=of, systemic_stress_regime=systemic,
           stress_scenarios_not_probabilistic=[
               dict(name="Winter Storm Uri 2021-02-15", fact="frequency below 59.4 Hz for 4 min 23 s; ~52 GW generation forced out (S&P Global reporting); NOT in event table", use="stress case for system-collapse tail"),
               dict(name="ERCOT largest single contingency", fact="1,430 MW (ERCOT AS study 2024); RRS sized to keep frequency >=59.7 Hz", use="design basis"),
               dict(name="Two largest units", fact="ERCOT procures RRS to survive loss of two largest units and stay above 59.3 Hz (UFLS first stage)", use="design basis (statement of intent, not observed)"),
               dict(name="Lowest inertia", fact="115 GW*s (March 2022, ERCOT AS study 2024)", use="low-inertia stress")],
           limitations=["Table lists unit-trip/load-loss events; system-collapse conditions (Uri) are missing, so true extremes are NOT in the data",
                        "Nadir depth for a given MW loss fell ~11%/yr (t=-16.7) over 2018-2025 (faster/more frequency response); the model holds the latest-year response fixed: it does not extrapolate the trend and assumes the response persists; a legacy-response (2019) sensitivity is provided",
                        "Stage 2 explains ~60% of nadir variance with the year term; response timing and event type remain unmodeled",
                        "Nadir levels below ~59.7 Hz (observed minimum) are extrapolated; rates there have very wide CIs and depend on the tail model",
                        "Reporting thresholds (dF>=60 mHz or >=350 MW) truncate small events; Poisson rate assumes independent events",
                        "Inertia in these reports is a system estimate; future inertia/IBR levels may differ"])
(ROOT / "models/frequency_event_model.json").write_text(json.dumps(out, indent=1))
print(f"under-frequency n={len(U)} rate={rate:.1f}/yr; MW GPD shape {c:.2f} scale {s:.0f} p_exc {p_exc:.2f}; stage2 b_mw={b[1]:.2f} c_H={b[2]:.2f} d_year={b[3]:.3f} sigma={s2:.2f} yr_ref={YR_REF:.2f}")
print("MW return levels", mwrl)
print("nadir below Hz | observed | model | model CI | direct GPD  (events/yr)")
for t in THRESHOLDS:
    print(f"  {t}: {obs[t]:.3f} | {base[t]:.4f} | {ci[t]} | {direct[t]:.4f}")
print("legacy (2019 response) rates:", {t: round(legacy[t], 4) for t in THRESHOLDS})
print("over-frequency", of)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].scatter(U.mw_loss, U.depth, s=10, alpha=.5); ax[0].set(xscale="log", yscale="log", xlabel="MW loss", ylabel="nadir depth Hz", title="Nadir depth vs generation loss (n=%d)" % len(U))
ax[1].errorbar(THRESHOLDS, [base[t] for t in THRESHOLDS], yerr=[[base[t] - ci[t][0] for t in THRESHOLDS], [ci[t][1] - base[t] for t in THRESHOLDS]], fmt="o-", label="model")
ax[1].plot(THRESHOLDS, [max(obs[t], 1e-4) for t in THRESHOLDS], "ks", label="observed"); ax[1].plot(THRESHOLDS, [max(direct[t], 1e-6) for t in THRESHOLDS], "g^", label="direct GPD")
ax[1].set(yscale="log", xlabel="nadir below (Hz)", ylabel="events per year", title="Annual rate of nadir exceedance"); ax[1].invert_xaxis(); ax[1].legend()
fig.tight_layout(); fig.savefig(ROOT / "figures/frequency_events.png", dpi=120)
