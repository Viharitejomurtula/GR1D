"""Low/mid/high scenario matrix for the reference campus. Unobservable inputs (rho, systemic event rate, West-Texas dip multiplier) are NEVER collapsed to a default:
every result is reported at all three settings. Writes reports/scenario_matrix.md and site/abilene/scenario_matrix.json. Usage: python scripts/build_scenario_matrix.py"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from samplers import CapacitorLoss, FrequencyEventTail, VoltageDips  # noqa: E402

J = lambda p: json.load(open(ROOT / p))
prof = J("site/abilene/site_profile.json"); pol = prof["low_mid_high_policy"]
gs = J("site/abilene/gpu_sync_site.json")["results"]; HT = J("models/heat_trend_abilene.json"); FE = J("models/frequency_event_model.json")["systemic_stress_regime"]
RC = J("models/reality_check.json"); CP = J("models/capacitor_degradation_params.json")["groups"]
rng = np.random.default_rng(0)
rho = pol["rho_cross_job_phase_sharing"]; sysr = pol["systemic_event_rate_per_year"]; mult = pol["west_texas_dip_rate_multiplier"]
out = {}; L = []; A = L.append
A("# Scenario matrix: reference campus (Abilene, ERCOT West), low / mid / high\n")
A("Unobservable inputs are reported at **low, mid and high** and never fixed to a default. Low/high are bounds (or 95% interval ends); mid is an illustrative midpoint or posterior median. They are not probabilities. This is a reference campus built from public information, not the operator's actual design.\n")
A("## 1. Campus training-load swing and ramp (vs cross-job phase sharing rho; 1.75 kW/GPU, GB200 NVL72 class)\n")
A("| IT load (mean MW) | rho | " + " | ".join(["swing p99-p1 (MW)", "1 s ramp p99 (MW/s)", "1 s ramp p99.9 (MW/s)"]) + " |\n|---|---|---|---|---|")
out["ai_swing"] = {}
for load in (200, 600, 1200):
    for name, r in (("low", rho["low"]), ("mid", rho["mid"]), ("high", rho["high"])):
        g = gs[f"load{load}MW_kwgpu1.75_rho{r}"]
        A(f"| {load} | {name} (rho={r}) | {g['swing_p99_p1_mw']:.0f} | {g['ramp_1s_p99_mw_per_s']:.1f} | {g['ramp_1s_p999_mw_per_s']:.1f} |")
        out["ai_swing"][f"{load}MW_{name}"] = g
A("- 200 and 1,200 MW are publicly stated phase/total capacities; 600 MW is an illustrative midpoint. The spread between low and high is x20 or more at every size; only operator power traces can narrow it.\n")
A("## 2. Grid frequency stress (vs systemic-event rate; ERCOT-wide, from 2 documented events, 2011 and 2021)\n")
A("| regime rate | per year | P(year min nadir < 59.7 Hz) | < 59.5 Hz | < 59.4 Hz | P(at least one in 10 years, < 59.5 Hz) | annual-min nadir p50 / p5 / p1 (Hz) incl. ordinary events |\n|---|---|---|---|---|---|---|")
ev = FrequencyEventTail(); out["systemic"] = {}
lo, hi = FE["conditional_nadir"]["low"], FE["conditional_nadir"]["high"]
for name in ("low", "mid", "high"):
    lam = sysr[name]; p_yr = 1 - np.exp(-lam)
    pb = lambda t: p_yr * float(np.clip((t - lo) / (hi - lo), 0, 1))
    yrs = ev.sample_years(3000, rng, include_systemic=True, systemic_rate_per_year=lam)
    mins = np.array([y.min() if len(y) else 60.0 for y in yrs]); q = np.percentile(mins, [50, 5, 1])
    A(f"| {name} | {lam} | {pb(59.7):.3f} | {pb(59.5):.3f} | {pb(59.4):.3f} | {1 - (1 - pb(59.5)) ** 10:.2f} | {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f} |")
    out["systemic"][name] = dict(rate=lam, p59_7=pb(59.7), p59_5=pb(59.5), p59_4=pb(59.4), annual_min_p50_p5_p1=q.round(3).tolist())
A("- In-regime nadir is Uniform(59.302, 59.58) Hz from the two documented events; the 2021 event came within 0.002 Hz of the first load-shed stage, so the low end is optimistic. Ordinary trip events at today's response level add only shallow dips (annual-min median ~59.86 Hz).\n")
A("## 3. Voltage dips at the transmission class (EPRI rates x West Texas multiplier)\n")
A("| multiplier | dips per year p5 / p50 / p95 | durations | phases |\n|---|---|---|---|")
out["dips"] = {}
for name in ("low", "mid", "high"):
    d = VoltageDips().sample(1500, rng, rate_multiplier=mult[name]); c = np.array([len(y) for y in d]); q = np.percentile(c, [5, 50, 95])
    A(f"| {name} (x{mult[name]}) | {q[0]:.0f} / {q[1]:.0f} / {q[2]:.0f} | 90% 3-5 cycles, 10% 10-20 cycles (assumed weights) | 20% three-phase (assumed) |")
    out["dips"][name] = q.tolist()
A("- Rate from EPRI (transmission class, site-to-site lognormal); multiplier is a scenario supported by ERCOT's count of 11 load-affecting West/Far-West fault events in 12 months. Whether any dip drops load depends on ride-through settings (data request items 2-4).\n")
A("## 4. Items held at a stated middle value (spread reported, not driven into headlines)\n")
cap = CapacitorLoss(); x = cap.sample(4000, rng, 12, 5000)
A(f"- **Capacitor:** mid = the 12 V stress group, no film-vs-electrolytic scaling: 5000 h capacitance loss {np.percentile(x, 50)*100:.1f}% (5-95%: {np.percentile(x, 5)*100:.1f}-{np.percentile(x, 95)*100:.1f}%). The observed 12 V group mean at 5000 h is {CP['12V']['loss_5000h_mean']*100:.1f}%; the fitted curve (plateau plus wear-out) ignores the partial recovery seen in the data and reads about 1.4 points high. Spread across stress levels {CP['10V']['loss_5000h_mean']*100:.1f}%-{CP['14V']['loss_5000h_mean']*100:.1f}% and the film transfer are unresolved; propagation to failures not tested.")
A(f"- **Mean power fraction:** training-like (NLR, {RC['utilization_transfer_gap']['nlr_training_median_over_p95_power']*100:.0f}% of peak) instead of the Alibaba fleet value ({RC['utilization_transfer_gap']['implied_node_power_fraction_of_peak']*100:.0f}%).")
ht = HT["return_levels_c"]
A(f"- **Heat (cooling margin):** 2026 hot-hour return levels 10/50/100 y = {ht['10y_in_2026']['est']}/{ht['50y_in_2026']['est']}/{ht['100y_in_2026']['est']} C; hours above 40 C per year: {HT['hours_above_dry_bulb']['40']['mean_last_5']:.0f} (last 5-year mean), trend-fitted {HT['hours_above_dry_bulb']['40']['fitted_2026']:.0f}.")
A("- Battery aging remains proxy-based (template only); fresh NMC resistance by temperature and SOC is in `models/battery_dc_resistance_params.json`.")
(ROOT / "reports/scenario_matrix.md").write_text("\n".join(L)); json.dump(out, open(ROOT / "site/abilene/scenario_matrix.json", "w"), indent=1); print("written")
