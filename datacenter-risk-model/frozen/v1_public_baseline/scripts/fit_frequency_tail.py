"""Event-based tail model for ERCOT frequency: peaks-over-threshold (GPD) on BAL-003 selected-event settling DelFreq.

Data: data/processed/ercot_bal003_events.csv (55 events, OY2020-2022, transcribed from PDCWG decks). Under-frequency (generation loss)
events only: x = -DelFreq (Hz). GPD on exceedances over u with bootstrap CIs, plus event rate. Also records over-frequency
load-loss case points from ERCOT's Nov-2024 large-load deck (scenario points, not fitted).
Usage: python -I fit_frequency_tail.py
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
E = pd.read_csv(ROOT / "data/processed/ercot_bal003_events.csv")
years = E.op_year.nunique()
under = E[E.delfreq_hz < 0]
x = -under.delfreq_hz.values
print("events", len(E), "under-freq", len(x), "over-freq", int((E.delfreq_hz > 0).sum()), "per-year counts", E.groupby("op_year").size().to_dict())

U = 0.06
exc = x[x > U] - U
rate = len(exc) / years
c, _, sc = stats.genpareto.fit(exc, floc=0)
ks = stats.kstest(exc, "genpareto", args=(c, 0, sc))
rng = np.random.default_rng(0)
RET = (1, 5, 10, 25)  # years


def level(c, sc, rate, T):  # |dF| exceeded on average once per T years
    p = 1 - 1 / (T * rate)
    return U + stats.genpareto.ppf(p, c, 0, sc)


boot = []
for _ in range(2000):
    s = rng.choice(exc, len(exc))
    try:
        bc, _, bs = stats.genpareto.fit(s, floc=0)
        boot.append((bc, bs))
    except Exception:
        pass
boot = np.array(boot)
rl = {f"{T}y": dict(est=round(float(level(c, sc, rate, T)), 3),
                    ci95=np.percentile([level(b[0], b[1], rate, T) for b in boot], [2.5, 97.5]).round(3).tolist()) for T in RET}
# exponential alternative (c = 0) for comparison
sc_exp = exc.mean()
print(f"u={U}: n_exc={len(exc)} rate={rate:.1f}/yr  GPD shape c={c:.2f} (CI {np.percentile(boot[:,0],[2.5,97.5]).round(2).tolist()}) scale={sc:.3f}  KS p={ks.pvalue:.2f}")
print("return levels |dF| Hz:", {k: v["est"] for k, v in rl.items()}, "observed max", x.max())
# sensitivity to threshold
sens = {}
for u in (0.05, 0.06, 0.07, 0.08):
    e = x[x > u] - u
    cc, _, ss = stats.genpareto.fit(e, floc=0)
    sens[str(u)] = dict(n=int(len(e)), shape=round(float(cc), 2), scale=round(float(ss), 4))
print("threshold sensitivity", sens)
# over-frequency events in BAL-003 table
over = E[E.delfreq_hz > 0]
out = dict(source_id="F1a-ev1", kind="observed events (ERCOT BAL-003 selected events, OY2020-2022, n=%d) + GPD fit; extrapolation is model-based" % len(E),
           units="Hz (settling DelFreq, B to A; not the instantaneous nadir)", under_frequency=dict(
               n_events=int(len(x)), years=int(years), threshold_hz=U, n_exceed=int(len(exc)), rate_per_year=round(rate, 2),
               gpd=dict(shape=float(c), scale=float(sc), shape_ci95=np.percentile(boot[:, 0], [2.5, 97.5]).round(2).tolist(), ks_p=float(ks.pvalue)),
               return_levels_abs_dfreq_hz=rl, observed_max_hz=float(x.max()), threshold_sensitivity=sens),
           over_frequency_bal003=dict(n=int(len(over)), delfreq_hz=sorted(over.delfreq_hz.tolist()), note="too few to fit; all small"),
           over_frequency_large_load_cases=[dict(peak_hz=60.086, mw_load_reduction=415, note="West Texas, multiple 3LG faults"),
                                            dict(peak_hz=60.132, mw_load_reduction=500, note="DFW 2022-10-31, delayed clearing"),
                                            dict(peak_hz=60.235, mw_load_reduction=1560, note="Far West Texas 2022-12-07, recovered in 12m27s"),
                                            dict(peak_hz=60.11, mw_load_reduction=None, note="Texas coast single load, 5 FMEs, 7 min recovery")],
           limitations=["55 BAL-003 'selected' events: selection criteria change by year (OY2020 events are larger on average) and exclude extreme/UFLS events",
                        "Settling-frequency deltas, not nadirs; nadir needs a separate dynamic relationship",
                        "OY2023+ not collected; values transcribed from images (OY2021/22) and an EMF (OY2020), spot-check recommended",
                        "GPD fitted to ~%d exceedances: shape poorly constrained; return levels beyond ~25 years are not supported by data" % len(exc),
                        "Over-frequency load-loss cases are 4 scenario points from an ERCOT presentation, not a fitted distribution"])
json.dump(out, open(ROOT / "models/frequency_tail_params.json", "w"), indent=1)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
xs = np.sort(x)[::-1]; ax[0].plot(xs, np.arange(1, len(xs) + 1) / years, "o", label="events")
g = np.linspace(U, x.max() * 1.6, 100); ax[0].plot(g, rate * stats.genpareto.sf(g - U, c, 0, sc), label="GPD")
ax[0].set(yscale="log", xlabel="|settling dF| Hz", ylabel="events per year exceeding", title="Under-frequency events"); ax[0].legend()
ax[1].hist(exc, bins=10); ax[1].set(title="Exceedances over %.2f Hz" % U, xlabel="Hz")
fig.tight_layout(); fig.savefig(ROOT / "figures/frequency_tail.png", dpi=120)
