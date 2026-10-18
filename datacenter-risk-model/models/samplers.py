"""Samplers for fitted risk-factor distributions. Each class loads its params JSON from models/ and exposes
sample(n, rng, **conditions). Labels: kind = observed fit or modeling assumption (see each params file's limitations)."""
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from base import FactorModel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _load(name):
    return json.load(open(HERE / name))


def _interp_quantile(qs, vals, u):
    """Sample from empirical quantile function by linear interpolation on (qs, vals); u uniform(0,1)."""
    qs, vals = np.asarray(qs, float), np.asarray(vals, float)
    return np.interp(u, qs, vals)


@dataclass
class Temperature(FactorModel):
    name: str = "outdoor_temperature"
    units: str = "degC"
    source_id: str = "F1c"
    kind: str = "observed"
    station: str = "USW00013904"
    tag: str = ""  # e.g. "_abilene" selects models/temperature_params_abilene.json and wetbulb_params_abilene.json

    def __post_init__(self):
        self.p = _load(f"temperature_params{self.tag}.json")["stations"][self.station]
        self.qs = _load(f"temperature_params{self.tag}.json")["quantiles"]

    def sample(self, n, rng, month=7, hour=15):
        q = self.p["body_month_hour"][f"{month:02d}-{hour:02d}"]["q"]
        u = rng.uniform(self.qs[0], self.qs[-1], n)  # body only (1-99%)
        return _interp_quantile(self.qs, q, u)

    def sample_wetbulb(self, n, rng, month=7, hour=15):
        w = _load(f"wetbulb_params{self.tag}.json"); q = w["stations"][self.station]["body_month_hour"][f"{month:02d}-{hour:02d}"]["q"]
        return _interp_quantile(w["quantiles"], q, rng.uniform(w["quantiles"][0], w["quantiles"][-1], n))

    def sample_annual_max(self, n, rng):
        a = self.p["annual_max"]
        return stats.genextreme.rvs(a["gev_shape_c"], a["loc"], a["scale"], size=n, random_state=rng)


@dataclass
class FrequencyDeviation(FactorModel):
    """1 s trajectories (mHz) from resampled contiguous 5-min blocks of measured Texas data (body only)."""
    name: str = "grid_frequency_deviation"
    units: str = "mHz from 60 Hz"
    source_id: str = "F1a"
    kind: str = "observed"

    def __post_init__(self):
        self.blocks = np.vstack(pd.read_parquet(ROOT / "data/processed/frequency_blocks.parquet").dev_mhz.map(np.asarray).values)

    def sample(self, n, rng, seconds=300):
        idx = rng.integers(0, len(self.blocks), n)
        return self.blocks[idx][:, :seconds]

    def rocof(self, traj, lag=1):
        return (traj[:, lag:] - traj[:, :-lag]) / lag


@dataclass
class FrequencyEventTail(FactorModel):
    """Annual frequency events (ERCOT Operations Report event tables, 2018-2025) via a two-stage model: Poisson count; MW loss from empirical body +
    GPD tail; nadir depth | MW, inertia (lognormal regression). Optional systemic-scarcity (Uri-class) regime, whose rate is a Gamma posterior from 2
    documented events in 14.7 years (override with systemic_rate_per_year) and whose in-regime nadir is Uniform(59.302, 59.58) Hz from the two documented events (2011, 2021). Nadirs below ~59.7 Hz are extrapolations."""
    name: str = "frequency_event_nadir"
    units: str = "Hz (nadir of under-frequency events)"
    source_id: str = "F1a-ev1"
    kind: str = "observed events + modeled extrapolation + assumed systemic regime"

    def __post_init__(self):
        self.p = _load("frequency_event_model.json")
        self.ev = pd.read_csv(ROOT / "data/processed/ercot_frequency_events.csv")
        self.ev = self.ev[(self.ev.max_min_freq_hz < 60) & (self.ev.mw_loss > 0)]
        self.H = (self.ev.inertia_gws / 1000.0).values
        u = self.p["under_frequency"]; self.s1, self.s2, self.rate = u["stage1_gpd_mw"], u["stage2_nadir"], u["rate_per_year"]
        self.body = self.ev.mw_loss.values[self.ev.mw_loss.values <= self.s1["threshold_mw"]]

    def _events(self, n, rng, yr=None):
        exc = rng.uniform(size=n) < self.s1["p_exceed"]
        mw = np.where(exc, self.s1["threshold_mw"] + stats.genpareto.rvs(self.s1["shape"], 0, self.s1["scale"], size=n, random_state=rng), rng.choice(self.body, n))
        H = rng.choice(self.H, n)
        yr = self.s2["yr_ref"] if yr is None else yr
        depth = np.exp(self.s2["a"] + self.s2["b_mw"] * np.log(mw) + self.s2["c_inertia"] * np.log(H) + self.s2["d_year"] * yr + rng.normal(0, self.s2["eps_sigma"], n))
        return mw, 60 - depth

    def sample(self, n, rng, legacy_response=False):
        return self._events(n, rng, yr=0.5 if legacy_response else None)[1]

    def sample_years(self, n_years, rng, include_systemic=True, systemic_nadir_hz=None, systemic_rate_per_year=None, legacy_response=False):
        """Per year: array of event nadirs (Hz). Systemic regime year adds one event at systemic_nadir_hz."""
        sy = self.p["systemic_stress_regime"]; post_a = 0.5 + len(sy["events"]); post_scale = 1 / sy["exposure_years"]; cn = sy["conditional_nadir"]
        out = []
        for _ in range(n_years):
            nadirs = self._events(rng.poisson(self.rate), rng, yr=0.5 if legacy_response else None)[1]
            if include_systemic:
                lam = systemic_rate_per_year if systemic_rate_per_year is not None else rng.gamma(post_a, post_scale)
                if rng.uniform() < 1 - np.exp(-lam):
                    nadirs = np.append(nadirs, systemic_nadir_hz if systemic_nadir_hz is not None else rng.uniform(cn['low'], cn['high']))
            out.append(nadirs)
        return out


@dataclass
class BatteryCapacityFade(FactorModel):
    name: str = "battery_capacity_fade"
    units: str = "SOH relative to initial"
    source_id: str = "F2d"
    kind: str = "observed fit (small-cell proxy; transfer is an assumption)"

    def __post_init__(self):
        self.p = _load("battery_capacity_params.json")

    def sample(self, n, rng, cycles=100):
        k = np.exp(rng.normal(self.p["mu_log_k"], self.p["sigma_log_k"], n))
        return np.exp(-k * cycles)


@dataclass
class BatteryResistanceGrowth(FactorModel):
    name: str = "battery_resistance_growth"
    units: str = "R/R0 (EIS Re+Rct, not DC, not SOC-resolved)"
    source_id: str = "F2e"
    kind: str = "observed fit (small-cell proxy; transfer is an assumption)"

    def __post_init__(self):
        self.p = _load("battery_resistance_params.json")["groups"]["warm_20_44C"]

    def sample(self, n, rng, cycles=100):
        g = np.exp(rng.normal(self.p["g_log_mu"], self.p["g_log_sigma"], n))
        return np.exp(g * cycles)


@dataclass
class VoltageDips(FactorModel):
    """Annual sag events by depth bin (EPRI DPQ II). Duration and phases are NOT from data: caller supplies assumptions."""
    name: str = "voltage_dips"
    units: str = "events/year; depth in pu"
    source_id: str = "F2a"
    kind: str = "observed rates + assumptions (duration, phases)"
    location: str = "transmission"

    def __post_init__(self):
        self.p = _load("voltage_dip_params.json")["locations"][self.location]

    def sample(self, n, rng, p_delayed_clearing=0.1, normal_cycles=(3, 5), delayed_cycles=(10, 20), p_three_phase=0.2, rate_multiplier=1.0):
        out = []
        for _ in range(n):
            m = np.exp(rng.normal(0, self.p["site_rate_lognormal_sigma"]))
            rows = []
            for b, rate in self.p["depth_bins_rate_per_year"].items():
                lo, hi = (0.0, 0.5) if b.startswith("<") else tuple(float(x.rstrip("pu")) for x in b.split("-"))
                k = rng.poisson(m * rate * rate_multiplier)
                depth = rng.uniform(lo, hi, k)
                dly = rng.uniform(size=k) < p_delayed_clearing  # ASSUMPTION: mixture weights; cycle ranges from ERCOT 2024 large-load deck
                dur = np.where(dly, rng.uniform(*delayed_cycles, k), rng.uniform(*normal_cycles, k))
                ph = np.where(rng.uniform(size=k) < p_three_phase, 3, 1)  # ASSUMPTION
                rows += list(zip(depth, dur, ph))
            out.append(rows)
        return out


@dataclass
class AIWorkloadSwing(FactorModel):
    """Per-node power swing and ramp quantile samplers from NLR training/inference traces (observed)."""
    name: str = "ai_load_swing"
    units: str = "W per node"
    source_id: str = "F1b"
    kind: str = "observed"

    def __post_init__(self):
        self.p = _load("ai_load_swing_params.json")
        self.qs = self.p["quantiles"]

    def sample_swing(self, n, rng, workload="llama2_70b_lora", nodes=16, window_s=5):
        q = self.p["swings"][f"{workload}|{nodes}nodes|{window_s}s"]["q"]
        return _interp_quantile(self.qs, q, rng.uniform(self.qs[0], self.qs[-1], n))

    def sample(self, n, rng, **kw):
        return self.sample_swing(n, rng, **kw)

    def job_swing_mw(self, per_node_w, n_nodes):
        """Aggregate swing for a job of n_nodes: ASSUMPTION of lockstep (supported by measured corr 0.97-0.98 up to 16 nodes)."""
        return per_node_w * n_nodes / 1e6


@dataclass
class CapacitorLoss(FactorModel):
    """Relative capacitance loss vs stress voltage: L(t) = L_inf*(1-exp(-t/tau)). NASA ELECTROLYTIC capacitors; transfer to the target
    (film) technology is an ASSUMPTION - scale_to_target multiplies L_inf (user-set, default 1.0 = no transfer)."""
    name: str = "dc_link_capacitance_loss"
    units: str = "fraction of initial capacitance lost"
    source_id: str = "F2f"
    kind: str = "observed fit (electrolytic proxy; transfer assumed)"

    def __post_init__(self):
        self.p = _load("capacitor_degradation_params.json")["groups"]

    def sample(self, n, rng, stress_v=12, hours=5000, scale_to_target=1.0):
        g = self.p[f"{stress_v}V"]
        linf = np.clip(rng.normal(g["linf_mean"], g["linf_sd"], n), 0, 1) * scale_to_target
        tau = g["tau_h_median"]
        k = np.clip(rng.normal(g["k_per_1000h_mean"], g["k_per_1000h_sd"], n), 0, None) / 1000
        return linf * (1 - np.exp(-hours / tau)) + k * hours


@dataclass
class DataCenterUtilization(FactorModel):
    """Fleet GPU allocation / SM utilization by hour (Alibaba ASI sample) and an ASSUMED linear power mapping per 4-GPU node."""
    name: str = "datacenter_utilization"
    units: str = "fraction of GPUs"
    source_id: str = "F2c"
    kind: str = "observed utilization + assumed power mapping"

    def __post_init__(self):
        self.h = pd.read_csv(ROOT / "data/processed/alibaba_hourly_util.csv")
        self.m = _load("alibaba_utilization_params.json")["power_mapping_assumption"]

    def sample(self, n, rng, which="sm_util_frac"):
        return rng.choice(self.h[which].values, n)

    def node_power_kw(self, util):
        return self.m["p_idle_kw"] + (self.m["p_peak_kw"] - self.m["p_idle_kw"]) * np.asarray(util)


@dataclass
class GPUSyncGroupSize(FactorModel):
    """Concurrent GPU footprint per workload_id by job type (Alibaba); lockstep within a job is supported by NLR measurements (corr~0.97)."""
    name: str = "gpu_sync_group_size"
    units: str = "GPUs"
    source_id: str = "F2b"
    kind: str = "observed group sizes + assumed synchronization"

    def __post_init__(self):
        self.p = _load("alibaba_utilization_params.json")["concurrent_workload_gpu_footprint"]
        self.qs = [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]

    def sample(self, n, rng, job_type="training"):
        q = self.p[job_type]["gpus_q"]
        u = rng.uniform(self.qs[0], self.qs[-1], n)
        return np.interp(u, self.qs, q)


@dataclass
class GPUSyncFacility(FactorModel):
    """Aggregate training-load swing (MW, p99-p1 range) for the placeholder 10k-GPU facility vs cross-job phase-sharing rho (ASSUMED)."""
    name: str = "gpu_sync_facility_swing"
    units: str = "MW"
    source_id: str = "F2b"
    kind: str = "observed job sizes + observed within-job lockstep + assumed cross-job sharing"

    def __post_init__(self):
        self.p = _load("gpu_sync_params.json")

    def swing_mw(self, rho, training_gpus=None):
        keys = sorted(self.p["results_by_rho"], key=lambda k: float(k.split("_")[1]))
        xs = [float(k.split("_")[1]) for k in keys]; ys = [self.p["results_by_rho"][k]["range_p99_p1_mw_mean"] for k in keys]
        base = float(np.interp(rho, xs, ys)); f = self.p["facility"]
        return base * (training_gpus / (f["gpus"] * f["training_share_assumed"]) if training_gpus else 1.0)

    def sample(self, n, rng, **kw):
        return np.full(n, self.swing_mw(**kw))


@dataclass
class BatteryDCResistance(FactorModel):
    """Cell DC pulse resistance (ohm): fresh-cell level vs temperature and SOC (CALCE NMC INR 18650-20R, observed) times aging growth R/R0 from
    NASA cycling (observed, other chemistry/cell). Multiplying them is an ASSUMPTION (growth ratio transfers across cells)."""
    name: str = "battery_dc_resistance"
    units: str = "ohm per cell"
    source_id: str = "F2e"
    kind: str = "observed fresh-cell level (NMC) x observed aging growth ratio (NASA cells, assumed to transfer)"

    def __post_init__(self):
        self.t = pd.DataFrame(_load("battery_dc_resistance_params.json")["table"])
        self.growth = BatteryResistanceGrowth()

    def fresh(self, temp_c, soc_pct):
        temps = sorted(self.t.temp_c.unique()); out = []
        for tc in temps:
            g = self.t[self.t.temp_c == tc].sort_values("soc_bin_pct")
            out.append(np.interp(soc_pct, g.soc_bin_pct + 5, g["median"]))  # table in ohm
        return float(np.interp(temp_c, temps, out))

    def sample(self, n, rng, temp_c=25, soc_pct=50, cycles=0):
        base = self.fresh(temp_c, soc_pct)
        return base * (self.growth.sample(n, rng, cycles) if cycles else np.ones(n))
