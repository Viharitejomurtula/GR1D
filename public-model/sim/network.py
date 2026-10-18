"""Bayesian network v2. Nodes: aleatory (random per scenario), epistemic EP_* (no-data parameters held as bounded intervals), physics.
Run modes: single-loop (EP drawn uniformly -- a convenience prior, NOT evidence) or p-box (pbox.py: outer loop over EP box, report envelopes)."""
import sys, numpy as np
from pathlib import Path
from bn import Node, BN
PM = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(PM))
import evidence as ev, events as E, nasa_cap_aging as na

EP = {}   # name -> (lo, hi, kind, note)
def ep(name, lo, hi, kind, note):
    EP[name] = (lo, hi, kind, note)
    return Node("ep_" + name, [], lambda p, rng, n: rng.uniform(lo, hi, n), "epistemic", f"[{lo},{hi}] {kind}: {note}")

EPN = [
  ep("p_isolated", 0.0, 1.0, "no-data", "share of disturbances that are a single isolated sag (EPRI population) vs a recorded reclose sequence"),
  ep("p_ridetest", 0.0, 1.0, "no-data", "share of non-isolated disturbances drawn from the ride-through test (AionTracks) vs loss-causing events"),
  ep("v_nom_ac", 200.0, 277.0, "published-range", "PSU AC input 200-277 VAC (AE ORv3 datasheet); sets the 172 VAC UVLO as a fraction of nominal"),
  ep("stress_hours", 0.0, 194.0, "no-data", "capacitor age as NASA-EOS stress hours (mapping to calendar age unknown)"),
  ep("load_mean", 0.2, 0.85, "published-range", "PSU loading: metered servers 20-85% of nameplate, mean ~31% (older vendor study); provisioning convention 80%"),
  ep("bbu_fail_p", 0.001, 0.05, "no-data", "probability BBU fails to take over"),
  ep("soc_deficit", 0.0, 0.3, "no-data", "mean SOC shortfall at event"),
  ep("sts_p", 0.0, 1.0, "design", "probability an STS bypass with healthy alternate source is in the path"),
  ep("sts_detect_ms", 2.0, 25.0, "no-data", "STS source-failure detection delay (no manual retrieved)"),
  ep("bbu_rail_sag_v", 0.0, 10.0, "no-data", "extra rail droop below the 47.5 V ORv3 BBU set point while BBU carries load"),
  ep("board_uvlo_v", 36.0, 40.0, "published-range", "board UVLO: servers must run down to 40 V (Renesas 40-60 V rack range, generic) so UVLO <= 40 V; 36 V lower bound assumed"),
  ep("vfd_c_mf", 1.0, 4.0, "no-data", "VFD DC-link capacitance"),
  ep("vfd_H_s", 0.3, 3.0, "no-data", "motor+load inertia constant H"),
  ep("vfd_kinetic_p", 0.0, 1.0, "design", "P(drive configured UnderV.prevention=DC Maintain). ATV320 factory default is No (p259), so 0 is the default"),
  ep("usT_s", 0.2, 5.0, "published-range", "ATV320 [Undervolt. time out]: fault only if undervoltage lasts longer; range 0.2-999.9 s, DEFAULT 0.2 s (p259); upper bound 5 s assumed"),
  ep("hw_uv_trip_p", 0.0, 1.0, "no-data", "P(drive faults on internal DC-bus UV before the timer expires) -- manual does not say"),
  ep("atr_p", 0.0, 1.0, "design", "P(ATV320 [Automatic restart]=Yes); factory default No (p252)"),
  ep("auto_restart_s", 1.0, 60.0, "published-range", "ATV320 auto-restart waits 1, 5, 10 s then 1 min (p252)"),
  ep("chiller_delay_s", 100.0, 600.0, "general-practice", "compressor anti-short-cycle: ~100 s to several minutes (patents/vendor timers; OEM setting governs)"),
  ep("operator_s", 300.0, 3600.0, "no-data", "operator reset time if auto-restart is off"),
  ep("soc_bias_pct", -15.0, 15.0, "assumed", "BMS SOC-estimation bias (bounded bias + noise, no estimator)"),
  ep("soc_noise_pct", 0.0, 8.0, "assumed", "BMS SOC-estimation noise sd"),
  ep("surge_pu", 1.0, 2.0, "assumed", "post-dip load restart surge on storage converter (ERCOT deck: 2.0-4.2 uncontrolled, ~2 capped)"),
  ep("recov_s", 0.2, 5.0, "assumed", "duration of the restart surge/ramp (ERCOT deck: 90% restored in 0.41 s median)"),
  ep("n_units", 2.0, 12.0, "design", "PSU/converter units sharing load in an N+1 group"),
  ep("units_down", 0.0, 1.0, "design", "maintenance: 0 all up, 1 one unit down -- REPORT SEPARATELY (use fixed=), never average"),
]

def N(name, parents, kind, note=""):
    def deco(fn): return Node(name, parents, fn, kind, note)
    return deco

KEYS = E.library_keys()
import json
def _epri():
    p = json.load(open(PM.parent / "datacenter-risk-model" / "models" / "voltage_dip_params.json"))["locations"]["transmission"]["depth_bins_rate_per_year"]
    bins, rates = [], []
    for k, r in p.items():
        lo, hi = (0.0, 0.5) if k.startswith("<") else tuple(float(x.rstrip("pu")) for x in k.split("-")); bins.append((lo, hi)); rates.append(r)
    return bins, np.array(rates)
_EPRI = _epri()
LOSS_IDX = [i for i, k in enumerate(KEYS) if k in E.EVENTS_LOSS_ONLY]; RIDE_IDX = [i for i, k in enumerate(KEYS) if k not in E.EVENTS_LOSS_ONLY]
@N("event_id", ["ep_p_isolated", "ep_p_ridetest"], "empirical",
   "-1 = isolated EPRI sag (general population, not outcome-selected); else loss-causing public events (selected on outcome!) or the AionTracks ride-through test. Equal weights ASSUMED")
def event_id(p, rng, n):
    iso = rng.uniform(size=n) < p["ep_p_isolated"]; ride = rng.uniform(size=n) < p["ep_p_ridetest"]
    return np.where(iso, -1, np.where(ride, rng.choice(RIDE_IDX, n), rng.choice(LOSS_IDX, n)))

@N("dips", ["event_id"], "empirical", "(start_s, dur_ms, residual_pu) arrays, padded to 6 dips")
def dips(p, rng, n):
    S = np.zeros((n, 8)); D = np.zeros((n, 8)); R = np.zeros(n)
    for i, k in enumerate(KEYS):
        m = p["event_id"] == i; e = E.EVENTS_ALL[k]; c = int(m.sum()); L = len(e["t"])
        S[m, :L] = e["t"]; R[m] = rng.uniform(*e["residual"], c)
        for j, (lo, hi) in enumerate(e["dur_ms"]): D[m, j] = rng.uniform(lo, hi, c) if hi > lo else lo
    m = p["event_id"] == -1; c = int(m.sum())
    # isolated sag: depth bin drawn with EPRI DPQ-II rates (datacenter-risk-model/models/voltage_dip_params.json, empirical);
    # duration: 90% 3-5 cycles / 10% 10-20 cycles = the other agent's documented assumption (grounded on ERCOT PDCWG 2024 clearing times, weights assumed); NOT in the EPRI report
    bins, rates = _EPRI
    b = rng.choice(len(bins), c, p=rates / rates.sum()); lo, hi = np.array(bins)[b, 0], np.array(bins)[b, 1]
    R[m] = rng.uniform(lo, hi); D[m, 0] = np.where(rng.uniform(size=c) < 0.9, rng.uniform(3, 5, c), rng.uniform(10, 20, c)) * 1000 / 60   # mixture documented in fit_voltage_dips.py (weights ASSUMED there)
    return np.concatenate([S, D, R[:, None]], 1)

def _S(x): return x[:, :8]
def _D(x): return x[:, 8:16]
def _R(x): return x[:, 16]

@N("cap_loss", ["ep_stress_hours"], "empirical", "NASA EOS C loss at stress hours; unit drawn from 6 measured capacitors")
def cap_loss(p, rng, n):
    j = rng.integers(0, na.C.shape[1], n); h = p["ep_stress_hours"]
    return np.array([float(np.interp(hh, na.HRS, na.C[:, jj])) / 100 for hh, jj in zip(h, j)])

@N("load_frac", ["ep_load_mean", "ep_n_units", "ep_units_down"], "assumed", "mean +- 0.1; one unit down scales load by n/(n-1)")
def load_frac(p, rng, n):
    nu = np.round(p["ep_n_units"]); k = np.where(p["ep_units_down"] >= 0.5, nu / np.maximum(nu - 1, 1), 1.0)
    return np.clip((p["ep_load_mean"] + rng.uniform(-0.1, 0.1, n)) * k, 0.1, 1.5)

@N("holdup_ms", ["cap_loss", "load_frac"], "spec", "AE ORv3 20 ms @100% load, E/P, scaled by capacitor health")
def holdup_ms(p, rng, n): return 20.0 * (1 - p["cap_loss"]) / p["load_frac"]

@N("sts_gap_ms", ["ep_sts_p", "ep_sts_detect_ms"], "spec", "if STS present: detect + 1/4-cycle transfer (Vertiv STS2)")
def sts_gap_ms(p, rng, n):
    present = rng.uniform(size=n) < p["ep_sts_p"]; return np.where(present, p["ep_sts_detect_ms"] + ev.STS_TRANSFER_MS["60Hz"], 1e9)

@N("bbu_ok", ["ep_bbu_fail_p", "ep_soc_deficit", "ep_soc_bias_pct", "ep_soc_noise_pct"], "physics",
   "BMS enables BBU if ESTIMATED SOC > 0.2 floor; BBU works only if TRUE SOC > 0.1 and no failure. Est = true + bias + noise")
def bbu_ok(p, rng, n):
    soc = np.clip(1 - rng.exponential(np.maximum(p["ep_soc_deficit"], 1e-9), n), 0, 1)
    est = soc + p["ep_soc_bias_pct"] / 100 + rng.normal(0, 1, n) * p["ep_soc_noise_pct"] / 100
    return (est > 0.2) & (soc > 0.1) & (rng.uniform(size=n) > p["ep_bbu_fail_p"])

@N("ton_s", [], "spec", "AE TON_noBBU 1-4.5 s")
def ton_s(p, rng, n): return rng.uniform(1.0, 4.5, n)

@N("psu", ["dips", "sts_gap_ms", "holdup_ms", "bbu_ok", "ton_s", "ep_v_nom_ac"], "physics", "(outage_s, output_lost, handoff); DEPTH: dips with residual*Vnom >= 172 VAC UVLO do not interrupt the PSU")
def psu(p, rng, n):
    import engine; ride = (_R(p["dips"]) * p["ep_v_nom_ac"] >= ev.PSU_UVLO_AC.value)[:, None]
    o, l, h = engine.psu_chain(_S(p["dips"]), np.where(ride, 0.0, _D(p["dips"])), p["sts_gap_ms"], p["holdup_ms"], p["bbu_ok"], p["ton_s"])
    return np.stack([o, l, h], 1)

@N("board_trip", ["psu", "ep_bbu_rail_sag_v", "ep_board_uvlo_v"], "physics",
   "board sees the PSU rail, not AC. Trips if rail lost, or if BBU-state rail (47.5 V ORv3 set point - sag) < UVLO*(1+-2%, TPS2663 tol)")
def board_trip(p, rng, n):
    lost, hand = p["psu"][:, 1] > 0, p["psu"][:, 2] > 0
    uvlo = p["ep_board_uvlo_v"] * (1 + rng.uniform(-0.02, 0.02, n)); rail_bbu = 47.5 - p["ep_bbu_rail_sag_v"]
    return lost | (hand & (rail_bbu < uvlo))

@N("vfd_kinetic", ["ep_vfd_kinetic_p"], "design", "drive configured for DC-Maintain kinetic ride-through")
def vfd_kinetic(p, rng, n): return rng.uniform(size=n) < p["ep_vfd_kinetic_p"]

@N("vfd_ride_ms", ["ep_vfd_c_mf", "ep_vfd_H_s", "vfd_kinetic", "cap_loss", "load_frac"], "physics",
   "DC-link energy + (if DC Maintain configured) kinetic energy ride-through, f_usable=0.3 of H*S")
def vfd_ride_ms(p, rng, n):
    cap = 1e3 * p["ep_vfd_c_mf"] * 1e-3 * (1 - p["cap_loss"]) * (540**2 - 350**2) / (2 * 15e3 * p["load_frac"])
    return cap + np.where(p["vfd_kinetic"], 1e3 * 0.3 * p["ep_vfd_H_s"] / p["load_frac"], 0.0)

@N("vfd_trip", ["dips", "vfd_ride_ms", "vfd_kinetic", "ep_usT_s", "ep_hw_uv_trip_p"], "physics",
   "ATV320: fault if a dip outlasts the [Undervolt. time out]; also, if DC bus collapses (dip > ride) without kinetic support, faults with prob hw_uv_trip_p")
def vfd_trip(p, rng, n):
    D = np.where((np.sqrt(2) * 400 * _R(p["dips"]) >= 540.0)[:, None], 0.0, _D(p["dips"]))   # DEPTH: rectifier keeps conducting if AC peak >= Vdc
    timer = (D > p["ep_usT_s"][:, None] * 1000).any(1) if np.ndim(p["ep_usT_s"]) else (D > p["ep_usT_s"] * 1000).any(1)
    collapse = (D > p["vfd_ride_ms"][:, None]).any(1) & ~p["vfd_kinetic"] & (rng.uniform(size=n) < p["ep_hw_uv_trip_p"])
    return timer | collapse

@N("cooling_downtime_s", ["vfd_trip", "ep_atr_p", "ep_auto_restart_s", "ep_chiller_delay_s", "ep_operator_s"], "physics",
   "downtime = max(chiller anti-short-cycle, drive recovery: auto-restart wait if Atr=Yes else operator reset)")
def cooling_downtime(p, rng, n):
    auto = rng.uniform(size=n) < p["ep_atr_p"]; drive = np.where(auto, p["ep_auto_restart_s"], p["ep_operator_s"])
    return np.where(p["vfd_trip"], np.maximum(p["ep_chiller_delay_s"], drive), 0.0)

@N("converter_trip", ["psu", "ep_surge_pu", "ep_recov_s", "load_frac"], "spec",
   "ORv3 power-conversion overload limits (AE 3 kW/5.5 kW datasheets): >115% for 10 s, >120% for 100 ms, constant-current at 155% (10 ms dwell). Applied to the BBU converter by ASSUMPTION")
def converter_trip(p, rng, n):
    x = p["load_frac"] * p["ep_surge_pu"]
    allowed = np.where(x <= 1.0, np.inf, np.where(x <= 1.15, 10.0, np.where(x <= 1.20, 0.1, np.where(x <= 1.55, 0.1, 0.01))))
    return (p["psu"][:, 2] > 0) & (p["ep_recov_s"] > allowed)

@N("it_failure", ["psu", "board_trip", "converter_trip"], "physics", "IT power interrupted (PSU outage), board trip, or storage-converter overload trip")
def it_failure(p, rng, n): return (p["psu"][:, 0] > 0) | p["board_trip"] | p["converter_trip"]

net = BN([Node for Node in EPN] + [event_id, dips, cap_loss, load_frac, holdup_ms, sts_gap_ms, bbu_ok, ton_s, psu, board_trip, converter_trip, vfd_kinetic, vfd_ride_ms, vfd_trip, cooling_downtime, it_failure])
OUTCOMES = {"P_it_failure": lambda s: s["it_failure"].mean(), "P_board_trip": lambda s: s["board_trip"].mean(),
            "P_converter_trip": lambda s: s["converter_trip"].mean(), "P_cooling_trip": lambda s: s["vfd_trip"].mean(), "E_cooling_downtime_s": lambda s: s["cooling_downtime_s"].mean(),
            "E_psu_outage_s": lambda s: s["psu"][:, 0].mean()}
