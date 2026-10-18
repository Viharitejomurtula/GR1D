"""Part B of the external-driver task: implied covariance between factors from shared drivers.

What this file is
    Combines the fitted driver covariance (Part A, fit.py) with the S matrix to get the covariance
    and correlation that shared external drivers imply between the network's factors:
        Cov(X) = S Sigma_D S^T + diag(noise^2)
    It sweeps the uncertain inputs, decomposes each pair's covariance by driver, and checks the
    linear result against a Monte Carlo that uses the sampler and S's curves.

Reads (read-only)
    data_bayesian-network/network/s_matrix/s_matrix_long.csv   S: one row per factor x driver
    data_bayesian-network/network/s_matrix/noise.csv           sourced unit-to-unit noise sd
    data_bayesian-network/network/s_matrix/s_matrix_report.md  assumptions section (quoted in the report)
    data_bayesian-network/network/master.csv                   factor and driver ranges
    data_bayesian-network/network/drivers/driver_covariance.csv  Sigma_D from fit.py
    plus the fit.py outputs that sample.py reads (Monte Carlo only)

Writes (data_bayesian-network/network/drivers/)
    implied_covariance_nominal_<group>.csv   factor x factor covariance, nominal case, per group
    implied_correlation_nominal_<group>.csv  factor x factor correlation, nominal case, per group
    implied_all_cases.csv.gz                 every case x group x pair (long format, gzip-compressed)
    implied_summary.csv                      pairs with shared-driver covariance: correlation per case,
                                             drivers it comes through, assumptions it depends on
    implied_mc_check.csv                     Monte Carlo vs linear correlation, pairs differing > 0.1
    implied_report.md                        top pairs, sweep ranges, Monte Carlo check, assumptions
    (<group> is overall, DJF, MAM, JJA or SON.)

Run
    python -m ridethrough.drivers.implied        (needs fit.py outputs in network/drivers/)

Choices (also stated in the report)
    - Drivers D = [outdoor_temp_c, load_fraction, equipment_age_years].
      Sigma_D's temperature-load block is estimated from sample.sample_drivers at each coupling
      (SIGMA_N = 1,000,000 draws, a fixed seed per group), so the linear model and the Monte Carlo
      use the same definition of coupling (temperature and calendar effects on load both scaled;
      coupling 0 = flat load). load_fraction = typical x load_index (the linear part of
      sample.to_load_fraction), so its variance is typical^2 x Var(load_index) and its temperature
      covariance is typical x Cov(temp, load_index). Age is independent of both.
    - Age spread (fleet age distribution unknown; decision B, 2026-10-17): swept over
      sd = (high - low) / sqrt(12) = 4.33 years (uniform 0-15, nominal) and (high - low) / 6 = 2.5
      years. The Monte Carlo draws age from a uniform centered on the typical age with the same sd,
      so the linear and Monte Carlo results use the same spread.
    - S uses s_matrix_long's slope_at_typical_nominal or slope_at_typical_upper for every row
      (decision (a), 2026-10-17); an empty upper slope falls back to nominal. Rows with
      response_type none, and category_table rows (workload_type), contribute 0.
    - A slope whose unit is a "multiplier" (converter_current_limit_pu vs temperature) is converted
      to factor units by multiplying by the factor's master.csv typical value.
    - psu_holdup_ms vs load_fraction: the S slope is per unit of PSU load ratio. PSU ratio = k x
      load_fraction with k unknown, so the slope is multiplied by k (swept 0.5 and 1.0).
    - Noise: noise.csv sd where given ("relative" units are multiplied by the factor's typical
      value); otherwise the factor's master.csv sd, (high - low) / 6, flagged "assumed". The noise
      multiplier (1, 5, 10) scales only the sourced terms.
    - DC-link noise: noise.csv's 0.115 is a per-capacitor initial tolerance; a bank of n capacitors
      has 0.115 / sqrt(n). The capacitor count is unknown, so n is swept over 1, 4, 16.
    - Pairs whose noise comes only from noise.csv's new-cell spread (Rumpf et al. rows: basis
      "cell-to-cell") are flagged: aging spread was not found, so their correlation is overstated.
    - workload_type moves only the means of osc_amp and osc_freq_hz, so Cov(X) is the same within
      every workload category; one matrix is reported.
    - Nominal case: attenuation nominal, coupling 1.0 (grid-like, an upper bound for a data center),
      noise multiplier 1, PSU mapping k 1.0, age sd 4.33 years, DC-link capacitors n = 1.
"""
from __future__ import annotations

import gzip
import itertools
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ridethrough.drivers import fit, sample

NETWORK_DIR = fit.DATA_DIR / "network"
S_DIR = NETWORK_DIR / "s_matrix"
MASTER_CSV = NETWORK_DIR / "master.csv"

DRIVERS = ("outdoor_temp_c", "load_fraction", "equipment_age_years")
ATTENUATIONS = ("nominal", "upper")
COUPLINGS = (0.0, 0.5, 1.0)
NOISE_MULTS = (1, 5, 10)
PSU_KS = (0.5, 1.0)
AGE_SDS = (4.33, 2.5)            # years: (high - low) / sqrt(12) (uniform 0-15) and (high - low) / 6
DCLINK_NS = (1, 4, 16)           # capacitors per DC-link bank
NOMINAL_CASE = {"attenuation": "nominal", "coupling": 1.0, "noise_mult": 1, "psu_k": 1.0,
                "age_sd": 4.33, "dclink_n": 1}
COUPLING_LABEL = {0.0: "flat load (independent of weather and time of day)", 0.5: "half",
                  1.0: "grid-like (upper bound for a data center)"}
PSU_FACTOR = "psu_holdup_ms"
DCLINK_FACTOR = "dclink_capacitance_factor"
NEW_CELL_FLAG = "noise = new-cell spread only (aging spread not found); correlation overstated"
MC_N = 100_000
MC_SEED = 20261017
SIGMA_N = 1_000_000
SIGMA_SEEDS = {g: 1000 + i for i, g in enumerate(fit.GROUPS)}   # fixed seed per group for Sigma_D
MC_FLAG = 0.1
TOP_N = 10
# Room-temperature mapping for conditioned equipment (s_matrix_report.md, "Thermal path"): the room
# spans 18-27 degC while DFW outdoor temperature spans its 5th-95th percentiles, 3.3-35.0 degC.
ROOM_LOW_C, ROOM_HIGH_C, OUTDOOR_P05_C = 18.0, 27.0, 3.3


# ----------------------------------------------------------------------------- inputs

def load_inputs() -> dict:
    """Read every input table (read-only).

    Output: {"s_long", "noise", "master" (indexed by node), "driver_cov", "s_report" (text)}.
    """
    return {"s_long": pd.read_csv(S_DIR / "s_matrix_long.csv"),
            "noise": pd.read_csv(S_DIR / "noise.csv"),
            "master": pd.read_csv(MASTER_CSV).set_index("node"),
            "driver_cov": pd.read_csv(fit.OUT_DIR / "driver_covariance.csv"),
            "s_report": (S_DIR / "s_matrix_report.md").read_text()}


def factor_list(s_long: pd.DataFrame) -> list[str]:
    """Factors (rows of S) in the order they appear in s_matrix_long.csv."""
    return list(dict.fromkeys(s_long["factor"]))


def master_sd(master: pd.DataFrame, node: str) -> float:
    """Range-based sd of a master.csv node: (high - low) / 6, in the node's units."""
    return float((master.loc[node, "high"] - master.loc[node, "low"]) / 6.0)


# ----------------------------------------------------------------------------- S, Sigma_D, noise

def build_s(s_long: pd.DataFrame, master: pd.DataFrame, attenuation: str, psu_k: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """S matrix for one case, linearized at each driver's typical value.

    Inputs: s_matrix_long rows; master.csv; attenuation ("nominal" | "upper"); psu_k (PSU load
        ratio per unit load_fraction).
    Output: (S as a factors x DRIVERS DataFrame in factor units per driver unit,
        notes DataFrame with one row per non-zero cell: factor, driver, slope_used, column used,
        conversion, s_slope_unit, evidence, source_url).
    """
    factors = factor_list(s_long)
    s = pd.DataFrame(0.0, index=factors, columns=list(DRIVERS))
    notes = []
    for _, r in s_long[s_long["driver"].isin(DRIVERS)].iterrows():
        if r["response_type"] in ("none", "category_table"):
            continue
        col = f"slope_at_typical_{attenuation}"
        slope = r[col]
        if pd.isna(slope):
            col = "slope_at_typical_nominal (upper empty)"
            slope = r["slope_at_typical_nominal"]
        if pd.isna(slope) or slope == 0:
            continue
        slope = float(slope)
        conversion = ""
        if "multiplier" in str(r["slope_unit"]):
            typical = float(master.loc[r["factor"], "typical"])
            slope *= typical
            conversion = f"multiplier x typical {typical:g}"
        if r["factor"] == PSU_FACTOR and r["driver"] == "load_fraction":
            slope *= psu_k
            conversion = f"x PSU mapping k {psu_k:g}"
        s.loc[r["factor"], r["driver"]] = slope
        notes.append({"factor": r["factor"], "driver": r["driver"], "slope_used": slope, "column": col,
                      "conversion": conversion, "s_slope_unit": r["slope_unit"],
                      "evidence": r["evidence"], "source_url": r["source_url"]})
    return s, pd.DataFrame(notes)


def sampled_temp_load_cov(group: str, coupling: float, fitted: dict | None = None,
                          n: int = SIGMA_N) -> np.ndarray:
    """Covariance of (temp_c, load_index) from sample.sample_drivers.

    Inputs: group (overall | DJF | MAM | JJA | SON; a season restricts the calendar); coupling 0-1;
        fitted (sample.load_fitted output); n draws with the group's fixed seed SIGMA_SEEDS[group].
    Output: 2 x 2 array [[Var(temp) degC^2, Cov degC], [Cov degC, Var(load_index)]].
    """
    d = sample.sample_drivers(n, SIGMA_SEEDS[group], coupling=coupling,
                              season=None if group == "overall" else group, fitted=fitted)
    return np.cov(d["temp_c"].to_numpy(), d["load_index"].to_numpy())


def build_sigma_d(temp_load_cov: np.ndarray, master: pd.DataFrame, age_sd: float) -> pd.DataFrame:
    """Driver covariance Sigma_D (DRIVERS x DRIVERS).

    Inputs: temp_load_cov from sampled_temp_load_cov (one group and coupling); master.csv;
        age_sd (years).
    Output: 3 x 3 DataFrame. Units: degC^2, load_fraction^2, years^2 and their products.
        load_fraction = typical x load_index; age is independent with sd age_sd.
    """
    typical = float(master.loc["load_fraction", "typical"])
    var_t = float(temp_load_cov[0, 0])
    var_lf = typical ** 2 * float(temp_load_cov[1, 1])
    cov_t_lf = typical * float(temp_load_cov[0, 1])
    var_age = age_sd ** 2
    m = np.array([[var_t, cov_t_lf, 0.0], [cov_t_lf, var_lf, 0.0], [0.0, 0.0, var_age]])
    return pd.DataFrame(m, index=list(DRIVERS), columns=list(DRIVERS))


def build_noise(noise: pd.DataFrame, master: pd.DataFrame, factors: list[str], mult: float,
                dclink_n: int = 1) -> pd.DataFrame:
    """Unit-to-unit noise sd per factor, in factor units.

    Inputs: noise.csv; master.csv; factor list; mult (scales the sourced terms only); dclink_n,
        capacitors per DC-link bank (the per-capacitor sd is divided by sqrt(dclink_n)).
    Output: DataFrame indexed by factor with sd, basis ("sourced" | "assumed"), new_cell_only
        (True for noise.csv rows whose basis is the new-cell "cell-to-cell" spread) and note.
        Sourced: noise.csv sd, times the factor's master typical value when sd_unit says "relative".
        Assumed: master.csv (high - low) / 6, used where noise.csv has no sd.
    """
    n = noise.set_index("factor")
    rows = []
    for f in factors:
        if f in n.index and pd.notna(n.loc[f, "sd"]):
            sd = float(n.loc[f, "sd"])
            note = f"noise.csv {sd:g} {n.loc[f, 'sd_unit']}"
            if "relative" in str(n.loc[f, "sd_unit"]):
                typical = float(master.loc[f, "typical"])
                sd *= typical
                note += f" x typical {typical:g}"
            if f == DCLINK_FACTOR:
                sd /= np.sqrt(dclink_n)
                note += f" / sqrt({dclink_n})"
            rows.append({"factor": f, "sd": sd * mult, "basis": "sourced",
                         "new_cell_only": "cell-to-cell" in str(n.loc[f, "basis"]),
                         "note": note + f" x {mult:g}"})
        else:
            rows.append({"factor": f, "sd": master_sd(master, f), "basis": "assumed",
                         "new_cell_only": False, "note": "master.csv (high - low) / 6"})
    return pd.DataFrame(rows).set_index("factor")


def implied_cov(s: pd.DataFrame, sigma_d: pd.DataFrame, noise_sd: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cov(X) = S Sigma_D S^T + diag(noise^2) and its correlation matrix.

    Inputs: S (factors x DRIVERS), Sigma_D (DRIVERS x DRIVERS), noise sd per factor (factor units).
    Output: (covariance, correlation), both factors x factors DataFrames.
    """
    cov = s.to_numpy() @ sigma_d.to_numpy() @ s.to_numpy().T + np.diag(noise_sd.reindex(s.index).to_numpy() ** 2)
    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)
    return (pd.DataFrame(cov, index=s.index, columns=s.index),
            pd.DataFrame(corr, index=s.index, columns=s.index))


def driver_terms(s: pd.DataFrame, sigma_d: pd.DataFrame, fi: str, fj: str) -> dict[str, float]:
    """Split the shared-driver covariance of factors fi and fj by driver term.

    Output: {"<driver>" or "<driver_a>x<driver_b>": contribution} for every non-zero term of
        sum_d sum_e S[fi, d] Sigma_D[d, e] S[fj, e]; a cross term combines both orderings.
    """
    out = {}
    for a, b in itertools.combinations_with_replacement(DRIVERS, 2):
        v = s.loc[fi, a] * sigma_d.loc[a, b] * s.loc[fj, b]
        if a != b:
            v += s.loc[fi, b] * sigma_d.loc[b, a] * s.loc[fj, a]
        if abs(v) > 1e-15:
            out[a if a == b else f"{a}x{b}"] = float(v)
    return out


# ----------------------------------------------------------------------------- cases

def case_grid() -> list[dict]:
    """Every combination of attenuation, coupling, noise multiplier, PSU mapping, age sd and
    DC-link capacitor count (2 x 3 x 3 x 2 x 2 x 3 = 216 cases)."""
    return [{"attenuation": a, "coupling": c, "noise_mult": m, "psu_k": k, "age_sd": s, "dclink_n": n}
            for a in ATTENUATIONS for c in COUPLINGS for m in NOISE_MULTS for k in PSU_KS
            for s in AGE_SDS for n in DCLINK_NS]


def case_id(case: dict) -> str:
    """Short case label, e.g. att-nominal_cpl-1_noise-1_psuk-1_agesd-4.33_dcn-1."""
    return (f"att-{case['attenuation']}_cpl-{case['coupling']:g}_noise-{case['noise_mult']:g}"
            f"_psuk-{case['psu_k']:g}_agesd-{case['age_sd']:g}_dcn-{case['dclink_n']:g}")


def pair_assumptions(fi: str, fj: str, terms: dict[str, float], noise: pd.DataFrame,
                     s_notes: pd.DataFrame, case: dict) -> list[str]:
    """Assumptions a pair's result depends on.

    Output: labels among: NEW_CELL_FLAG (both factors' noise is noise.csv's new-cell spread only),
        assumed attenuation (a temperature term in the upper case), assumed noise (either factor uses
        the master.csv fallback), PSU mapping k (the pair involves PSU hold-up through load), coupling
        (a temperature x load term), bound slope (a slope S labels a bound), unit conversion (a
        multiplier slope converted to factor units).
    """
    out = []
    if noise.loc[fi, "new_cell_only"] and noise.loc[fj, "new_cell_only"]:
        out.append(NEW_CELL_FLAG)
    temp_terms = [t for t in terms if "outdoor_temp_c" in t]
    if temp_terms and case["attenuation"] == "upper":
        out.append("assumed attenuation")
    if "assumed" in (noise.loc[fi, "basis"], noise.loc[fj, "basis"]):
        out.append("assumed noise")
    if PSU_FACTOR in (fi, fj) and any("load_fraction" in t for t in terms):
        out.append("PSU mapping k")
    if any("x" in t and "outdoor_temp_c" in t and "load_fraction" in t for t in terms):
        out.append("coupling")
    used = s_notes[s_notes["factor"].isin([fi, fj])]
    drivers_used = {d for t in terms for d in t.split("x")}
    used = used[used["driver"].isin(drivers_used)]
    if used["s_slope_unit"].str.contains("bound").any():
        out.append("bound slope")
    if used["conversion"].str.startswith("multiplier").any():
        out.append("unit conversion")
    return out


def run_cases(inp: dict, fitted: dict | None = None) -> dict:
    """Compute Cov(X) and the correlation for every case and group.

    Inputs: load_inputs output; fitted (sample.load_fitted output; read from fit.OUT_DIR if omitted).
    Output: {"factors", "all" (long DataFrame), "summary" (long DataFrame), "nominal" ({group:
        (cov, corr)}), "s" ({case_id: (S, notes)}), "noise" ({(noise_mult, dclink_n): noise table}),
        "sigma_d" ({(group, coupling, age_sd): Sigma_D}), "temp_load_cov" ({(group, coupling):
        2 x 2 sampled covariance}), "fitted"}.
    """
    fitted = sample.load_fitted() if fitted is None else fitted
    tl_cov = {(g, c): sampled_temp_load_cov(g, c, fitted) for g in fit.GROUPS for c in COUPLINGS}
    factors = factor_list(inp["s_long"])
    all_rows, summary_rows, nominal, s_cache, noise_cache, sig_cache = [], [], {}, {}, {}, {}
    for case in case_grid():
        cid = case_id(case)
        s, notes = build_s(inp["s_long"], inp["master"], case["attenuation"], case["psu_k"])
        s_cache[cid] = (s, notes)
        nkey = (case["noise_mult"], case["dclink_n"])
        if nkey not in noise_cache:
            noise_cache[nkey] = build_noise(inp["noise"], inp["master"], factors, *nkey)
        noise = noise_cache[nkey]
        for group in fit.GROUPS:
            skey = (group, case["coupling"], case["age_sd"])
            if skey not in sig_cache:
                sig_cache[skey] = build_sigma_d(tl_cov[(group, case["coupling"])], inp["master"],
                                                case["age_sd"])
            sig = sig_cache[skey]
            cov, corr = implied_cov(s, sig, noise["sd"])
            if case == NOMINAL_CASE:
                nominal[group] = (cov, corr)
            for i, fi in enumerate(factors):
                for fj in factors[i:]:
                    all_rows.append({"case": cid, **case, "group": group, "factor_i": fi, "factor_j": fj,
                                     "covariance": cov.loc[fi, fj], "correlation": corr.loc[fi, fj]})
                    if fi == fj:
                        continue
                    terms = driver_terms(s, sig, fi, fj)
                    if not terms:
                        continue
                    summary_rows.append({
                        "factor_i": fi, "factor_j": fj, "case": cid, **case, "group": group,
                        "correlation": corr.loc[fi, fj], "covariance": cov.loc[fi, fj],
                        "drivers": ";".join(terms),
                        "driver_terms": ";".join(f"{k}={v:.4g}" for k, v in terms.items()),
                        "depends_on_assumption": ";".join(pair_assumptions(fi, fj, terms, noise, notes, case))})
    return {"factors": factors, "all": pd.DataFrame(all_rows), "summary": pd.DataFrame(summary_rows),
            "nominal": nominal, "s": s_cache, "noise": noise_cache, "sigma_d": sig_cache,
            "temp_load_cov": tl_cov, "fitted": fitted}


# ----------------------------------------------------------------------------- Monte Carlo

def _component_temp(outdoor_c: np.ndarray, attenuation: float) -> np.ndarray:
    """Component temperature for a curve row: outdoor itself when attenuation is 1; otherwise the
    conditioned-room mapping clip(ROOM_LOW_C + attenuation x (T - OUTDOOR_P05_C), ROOM_LOW_C, ROOM_HIGH_C)."""
    if attenuation >= 1.0:
        return outdoor_c
    return np.clip(ROOM_LOW_C + attenuation * (outdoor_c - OUTDOOR_P05_C), ROOM_LOW_C, ROOM_HIGH_C)


def _parse_attenuation(value) -> float:
    """Attenuation as a number; a text entry such as "1 (outdoor) / 0 (indoor)" takes its first number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        m = re.search(r"[-+]?\d*\.?\d+", str(value))
        return float(m.group()) if m else 0.0


def monte_carlo_corr(inp: dict, s: pd.DataFrame, case: dict, group: str, noise_sd: pd.Series,
                     n: int = MC_N, seed: int = MC_SEED, fitted: dict | None = None) -> pd.DataFrame:
    """Monte Carlo correlation of the factors for one case and group.

    Drivers: sample.sample_drivers (season = group unless overall, the case's coupling);
        load_fraction = sample.to_load_fraction(load_index) (clipped); age ~ uniform centered on the
        typical age with the case's age_sd (half-width age_sd x sqrt(3); 4.33 gives 0-15 years).
    Factors: typical + response + noise. Linear rows use the case's S slope times (driver - typical).
        Curve rows with a non-zero slope use S's curve (x_points, y_points) at the component
        temperature (see _component_temp), minus its value at the typical outdoor temperature;
        multiplier curves are scaled by the factor's typical value. PSU hold-up uses its linear
        slope (the 20/L equation is outside its sourced range here).
    Output: factors x factors correlation DataFrame.
    """
    master, s_long = inp["master"], inp["s_long"]
    rng = np.random.default_rng(seed + 1)
    d = sample.sample_drivers(n, seed, coupling=case["coupling"],
                              season=None if group == "overall" else group, fitted=fitted)
    drv = {"outdoor_temp_c": d["temp_c"].to_numpy(),
           "load_fraction": sample.to_load_fraction(d["load_index"].to_numpy(),
                                                    float(master.loc["load_fraction", "typical"]),
                                                    float(master.loc["load_fraction", "low"]),
                                                    float(master.loc["load_fraction", "high"])),
           "equipment_age_years": float(master.loc["equipment_age_years", "typical"])
                                  + case["age_sd"] * np.sqrt(3.0) * rng.uniform(-1.0, 1.0, n)}
    typ = {k: float(master.loc[k, "typical"]) for k in DRIVERS}
    curves = s_long[s_long["response_type"] == "curve"].set_index(["factor", "driver"])
    x = np.empty((n, len(s.index)))
    for fi, f in enumerate(s.index):
        val = np.full(n, float(master.loc[f, "typical"]))
        for dname in DRIVERS:
            slope = s.loc[f, dname]
            if slope == 0:
                continue
            if (f, dname) in curves.index and f != PSU_FACTOR:
                row = curves.loc[(f, dname)]
                xs = np.array([float(v) for v in str(row["x_points"]).split(";")])
                ys = np.array([float(v) for v in str(row["y_points"]).split(";")])
                att = _parse_attenuation(row[f"attenuation_{case['attenuation']}"])
                comp = _component_temp(drv[dname], att)
                comp_typ = _component_temp(np.array([typ[dname]]), att)
                resp = np.interp(comp, xs, ys) - np.interp(comp_typ, xs, ys)[0]
                if "multiplier" in str(row["slope_unit"]):
                    resp = resp * float(master.loc[f, "typical"])
                val += resp
            else:
                val += slope * (drv[dname] - typ[dname])
        x[:, fi] = val + rng.standard_normal(n) * float(noise_sd[f])
    return pd.DataFrame(np.corrcoef(x, rowvar=False), index=s.index, columns=s.index)


def monte_carlo_check(inp: dict, res: dict, n: int = MC_N) -> pd.DataFrame:
    """Compare Monte Carlo and linear correlations for every case and group.

    Output: one row per case x group x factor pair whose correlations differ by more than MC_FLAG:
        case, group, factor_i, factor_j, linear, monte_carlo, difference.
    """
    fitted = res["fitted"]
    lin = res["all"].set_index(["case", "group", "factor_i", "factor_j"])["correlation"]
    rows = []
    for case in case_grid():
        cid = case_id(case)
        s, _ = res["s"][cid]
        noise_sd = res["noise"][(case["noise_mult"], case["dclink_n"])]["sd"]
        for group in fit.GROUPS:
            mc = monte_carlo_corr(inp, s, case, group, noise_sd, n, fitted=fitted)
            for i, fi in enumerate(res["factors"]):
                for fj in res["factors"][i + 1:]:
                    lv, mv = float(lin[(cid, group, fi, fj)]), float(mc.loc[fi, fj])
                    if abs(mv - lv) > MC_FLAG:
                        rows.append({"case": cid, "group": group, "factor_i": fi, "factor_j": fj,
                                     "linear": lv, "monte_carlo": mv, "difference": mv - lv})
    return pd.DataFrame(rows, columns=["case", "group", "factor_i", "factor_j", "linear",
                                       "monte_carlo", "difference"])


# ----------------------------------------------------------------------------- outputs

def s_report_assumptions(text: str) -> str:
    """The "Assumptions to state in the demo" section of s_matrix_report.md, verbatim."""
    m = re.search(r"## Assumptions to state in the demo\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1).strip() if m else "(section not found in s_matrix_report.md)"


def build_report(inp: dict, res: dict, mc: pd.DataFrame) -> str:
    """Content of implied_report.md, built only from the computed tables.

    Output: Markdown: method and nominal case, S used, noise used, top pairs (nominal, overall)
        with their drivers and sources, how they move across the sweeps and seasons, the Monte
        Carlo check, and the assumptions (this step's and s_matrix_report.md's).
    """
    summ = res["summary"]
    nom_id = case_id(NOMINAL_CASE)
    s_nom, notes_nom = res["s"][nom_id]
    noise1 = res["noise"][(1, NOMINAL_CASE["dclink_n"])]
    L = ["# Implied factor covariance (Part B)", "",
         f"Produced by `ridethrough/drivers/implied.py` on {date.today().isoformat()}. "
         "Cov(X) = S Sigma_D S^T + diag(noise^2), linearized at each driver's typical value.", "",
         f"Nominal case: attenuation {NOMINAL_CASE['attenuation']}; coupling {NOMINAL_CASE['coupling']:g}, "
         f"{COUPLING_LABEL[NOMINAL_CASE['coupling']]}; noise multiplier {NOMINAL_CASE['noise_mult']:g}; "
         f"PSU mapping k {NOMINAL_CASE['psu_k']:g}; age sd {NOMINAL_CASE['age_sd']:g} years (uniform 0-15); "
         f"DC-link capacitors per bank n = {NOMINAL_CASE['dclink_n']}.", "",
         f"Sweeps: attenuation {ATTENUATIONS}; coupling {COUPLINGS} "
         f"({', '.join(f'{c:g} = {COUPLING_LABEL[c]}' for c in COUPLINGS)}); noise multiplier {NOISE_MULTS}; "
         f"PSU mapping k {PSU_KS}; age sd {AGE_SDS} years (fleet age distribution unknown: uniform 0-15 vs "
         f"(high - low) / 6); DC-link n {DCLINK_NS} (DC-link noise 0.115 / sqrt(n); capacitor count unknown). "
         f"{len(case_grid())} cases x groups {fit.GROUPS}.", "",
         "## S used (nominal case; factor units per driver unit)", "",
         "| factor | " + " | ".join(DRIVERS) + " |", "|---|" + "---|" * len(DRIVERS)]
    for f in res["factors"]:
        L.append(f"| {f} | " + " | ".join(f"{s_nom.loc[f, d]:.4g}" if s_nom.loc[f, d] else "0"
                                          for d in DRIVERS) + " |")
    L += ["", "Non-zero cells and their sources:", "",
          "| factor | driver | slope | S column | conversion | evidence | source |", "|---|---|---|---|---|---|---|"]
    for _, r in notes_nom.iterrows():
        L.append(f"| {r['factor']} | {r['driver']} | {r['slope_used']:.4g} | {r['column']} | "
                 f"{r['conversion'] or '-'} | {r['evidence']} | "
                 f"{r['source_url'] if pd.notna(r['source_url']) else '- (equation row)'} |")
    upper_s, upper_notes = res["s"][case_id({**NOMINAL_CASE, "attenuation": "upper"})]
    extra = upper_notes[~upper_notes.set_index(["factor", "driver"]).index.isin(
        notes_nom.set_index(["factor", "driver"]).index)]
    if len(extra):
        L += ["", "Cells that are non-zero only in the upper-attenuation case:", ""]
        L += [f"- {r['factor']} x {r['driver']}: {r['slope_used']:.4g} ({r['conversion'] or 'as in S'})"
              for _, r in extra.iterrows()]
    L += ["", f"## Noise used (multiplier 1, DC-link n = {NOMINAL_CASE['dclink_n']})", "",
          "| factor | sd | basis | note |", "|---|---|---|---|"]
    L += [f"| {f} | {r['sd']:.4g} | {r['basis']} | {r['note']} |" for f, r in noise1.iterrows()]
    L += ["", "DC-link: noise.csv's 0.115 is a per-capacitor initial tolerance (kept as given). A bank of n "
              "independent capacitors has 0.115 / sqrt(n); the count is unknown, so n = "
              f"{', '.join(str(n) for n in DCLINK_NS)} is swept. s_matrix/ is unchanged."]

    ov = summ[summ["group"] == "overall"]

    def at(p: pd.DataFrame, **kw) -> str:
        """Correlation of one pair at the nominal case with the given settings changed."""
        sel = p
        for k, v in {**NOMINAL_CASE, **kw}.items():
            sel = sel[sel[k] == v]
        return f"{sel['correlation'].iloc[0]:.3f}" if len(sel) else "-"

    def pair_rows(p_all: pd.DataFrame, fi: str, fj: str) -> pd.DataFrame:
        return p_all[(p_all["factor_i"] == fi) & (p_all["factor_j"] == fj)]

    nom = summ[(summ["case"] == nom_id) & (summ["group"] == "overall")].copy()
    nom = nom.reindex(nom["correlation"].abs().sort_values(ascending=False).index).head(TOP_N)
    L += ["", f"## Top {TOP_N} pairs by |correlation| (nominal case, overall)", "",
          "Only pairs that share a driver are listed; every other pair has exactly zero implied correlation. "
          f"Both age spreads are shown; the ranking uses age sd {NOMINAL_CASE['age_sd']:g}.", "",
          f"| factor pair | correlation (age sd {AGE_SDS[0]:g}) | correlation (age sd {AGE_SDS[1]:g}) | drivers | "
          "depends on |", "|---|---|---|---|---|"]
    for _, r in nom.iterrows():
        p = pair_rows(ov, r["factor_i"], r["factor_j"])
        L.append(f"| {r['factor_i']} - {r['factor_j']} | {r['correlation']:.3f} | {at(p, age_sd=AGE_SDS[1])} | "
                 f"{r['drivers']} | {r['depends_on_assumption'] or '-'} |")
    L += ["", "## Across the sweeps (overall)", "",
          "Each column changes one setting from the nominal case; min and max are over all "
          f"{len(case_grid())} cases.", "",
          "| factor pair | nominal | min | max | attenuation (nom / upper) | coupling (0 / 0.5 / 1) | "
          "noise multiplier (1 / 5 / 10) | PSU k (0.5 / 1) | age sd (4.33 / 2.5) | DC-link n (1 / 4 / 16) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in nom.iterrows():
        p = pair_rows(ov, r["factor_i"], r["factor_j"])
        L.append(f"| {r['factor_i']} - {r['factor_j']} | {r['correlation']:.3f} | {p['correlation'].min():.3f} | "
                 f"{p['correlation'].max():.3f} | {' / '.join(at(p, attenuation=a) for a in ATTENUATIONS)} | "
                 f"{' / '.join(at(p, coupling=c) for c in COUPLINGS)} | "
                 f"{' / '.join(at(p, noise_mult=m) for m in NOISE_MULTS)} | "
                 f"{' / '.join(at(p, psu_k=k) for k in PSU_KS)} | "
                 f"{' / '.join(at(p, age_sd=s) for s in AGE_SDS)} | "
                 f"{' / '.join(at(p, dclink_n=n) for n in DCLINK_NS)} |")
    L += ["", "## By season (nominal case)", "", "| factor pair | " + " | ".join(fit.GROUPS) + " |",
          "|---|" + "---|" * len(fit.GROUPS)]
    nc = summ[summ["case"] == nom_id]
    for _, r in nom.iterrows():
        p = pair_rows(nc, r["factor_i"], r["factor_j"]).set_index("group")
        L.append(f"| {r['factor_i']} - {r['factor_j']} | " + " | ".join(
            f"{p.loc[g, 'correlation']:.3f}" if g in p.index else "0" for g in fit.GROUPS) + " |")
    L += ["", "## Monte Carlo check", "",
          f"{MC_N} samples per case and group from `sample_drivers`; age ~ uniform centered on 7.5 years with "
          f"the case's age sd (4.33 gives 0-15); S's curves for curve rows; clipped load_fraction. "
          f"Pairs whose Monte Carlo correlation differs from the "
          f"linear result by more than {MC_FLAG}: {len(mc)} of "
          f"{len(case_grid()) * len(fit.GROUPS) * len(res['factors']) * (len(res['factors']) - 1) // 2} "
          "case x group x pair combinations (full list: `implied_mc_check.csv`).", ""]
    if len(mc):
        agg = (mc.groupby(["factor_i", "factor_j"])["difference"]
               .agg(n="size", min="min", max="max").reset_index().sort_values("n", ascending=False))
        L += ["| factor pair | flagged combinations | difference range |", "|---|---|---|"]
        L += [f"| {r['factor_i']} - {r['factor_j']} | {r['n']} | {r['min']:+.3f} to {r['max']:+.3f} |"
              for _, r in agg.iterrows()]
        L += ["", "Reasons the two differ: curve rows are non-linear (the converter derates only above "
                  "25 degC, and the usable-energy curve is steeper in a conditioned room than S's 25-35 degC "
                  "slope); load_fraction is clipped to [0.2, 0.97] in the Monte Carlo; the linear model uses "
                  "slopes at the typical value only."]
    L += ["", "## Sigma_D temperature-load block (sampled)", "",
          f"Estimated from `sample_drivers` ({SIGMA_N} draws, fixed seed per group). At coupling 1 it should "
          "match the fit (`driver_covariance.csv`).", "",
          "| group | coupling | Var(temp_c) | Var(load_index) | Cov(temp_c, load_index) | fit Cov (coupling 1) |",
          "|---|---|---|---|---|---|"]
    dc = inp["driver_cov"].set_index(["group", "var_i", "var_j"])["covariance"]
    for g in fit.GROUPS:
        for c in COUPLINGS:
            m = res["temp_load_cov"][(g, c)]
            ref = f"{dc[(g, 'temp_c', 'load_index')]:.3f}" if c == 1.0 else ""
            L.append(f"| {g} | {c:g} | {m[0, 0]:.3f} | {m[1, 1]:.4f} | {m[0, 1]:+.3f} | {ref} |")
    L += ["", "## Assumptions in this step", "",
          "- Sigma_D: the temperature-load block is sampled from `sample_drivers` at each coupling, so the "
          "linear model and the Monte Carlo share one definition: coupling scales the temperature and "
          "calendar effects on load together; the centred residual is not scaled. load_fraction = typical x "
          "load_index (linear part of to_load_fraction); age is independent of temperature and load.",
          f"- Coupling 0 is {COUPLING_LABEL[0.0]}. Its load variance is the residual of the grid (NCENT) "
          "fit, which is an assumption for a data center.",
          f"- Coupling 1.0 is {COUPLING_LABEL[1.0]}: NCENT grid load is far more temperature-sensitive "
          "than a data center's load.",
          f"- Age spread: sd {AGE_SDS[0]:g} years (uniform 0-15) is nominal; {AGE_SDS[1]:g} years "
          "((high - low) / 6) is swept, because the fleet age distribution is unknown. Linear and Monte "
          "Carlo use the same spread in every case.",
          f"- {NEW_CELL_FLAG}: applies to pairs whose noise comes only from noise.csv's new-cell spread "
          "(Rumpf et al. rows).",
          "- S: S's own slopes for every row (decision (a)); an empty upper slope uses nominal.",
          "- A multiplier slope (converter_current_limit_pu vs temperature) is multiplied by the factor's "
          "typical value to get factor units.",
          "- psu_holdup_ms vs load_fraction: S's slope at PSU ratio 1.0 times the mapping k; the 20/L "
          "equation is not extrapolated below its sourced range.",
          "- Noise in relative units is multiplied by the factor's typical value. Factors without sourced "
          "noise use the master.csv range sd and are flagged \"assumed noise\"; that sd spans the factor's "
          "whole range, so it likely overstates unit-to-unit noise and understates correlations.",
          "- workload_type shifts only the means of osc_amp and osc_freq_hz, so the covariance is the same "
          "in every workload category.",
          "- Monte Carlo: conditioned rooms follow clip(18 + attenuation x (T - 3.3), 18, 27) degC, from "
          "s_matrix_report.md's thermal-path assumption.", "",
          "## Assumptions carried from s_matrix_report.md", "", s_report_assumptions(inp["s_report"]), ""]
    return "\n".join(L)


def build_outputs(inp: dict, res: dict, mc: pd.DataFrame) -> dict[str, str | bytes]:
    """Build every output file's content in memory.

    Output: {file name: text, or gzip bytes for implied_all_cases.csv.gz (mtime 0, so identical
        inputs give identical bytes)}.
    """
    files = {}
    for group, (cov, corr) in res["nominal"].items():
        files[f"implied_covariance_nominal_{group}.csv"] = cov.to_csv(float_format="%.6g", index_label="factor")
        files[f"implied_correlation_nominal_{group}.csv"] = corr.to_csv(float_format="%.6g", index_label="factor")
    files["implied_all_cases.csv.gz"] = gzip.compress(
        res["all"].to_csv(index=False, float_format="%.6g").encode(), mtime=0)
    files["implied_summary.csv"] = res["summary"].to_csv(index=False, float_format="%.6g")
    files["implied_mc_check.csv"] = mc.to_csv(index=False, float_format="%.6g")
    files["implied_report.md"] = build_report(inp, res, mc)
    return files


def main() -> None:
    """Run every case, the Monte Carlo check, write all outputs to fit.OUT_DIR, print the top pairs."""
    inp = load_inputs()
    res = run_cases(inp)
    mc = monte_carlo_check(inp, res)
    for p in fit.write_outputs(build_outputs(inp, res, mc)):
        print("wrote", p.relative_to(fit.REPO_ROOT) if p.is_relative_to(fit.REPO_ROOT) else p)
    summ = res["summary"]
    nom = summ[(summ["case"] == case_id(NOMINAL_CASE)) & (summ["group"] == "overall")]
    nom = nom.reindex(nom["correlation"].abs().sort_values(ascending=False).index).head(TOP_N)
    print(f"top {TOP_N} implied correlations, nominal case, overall:")
    for _, r in nom.iterrows():
        print(f"  {r['factor_i']} - {r['factor_j']}: {r['correlation']:+.3f}  via {r['drivers']}"
              f"  [{r['depends_on_assumption'] or 'no flagged assumption'}]")
    print(f"Monte Carlo vs linear: {len(mc)} case x group x pair combinations differ by > {MC_FLAG}")


if __name__ == "__main__":
    main()
