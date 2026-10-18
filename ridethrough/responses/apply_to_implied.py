"""What the data-derived storage-resistance response does to the implied factor correlations.

What this file is
    Re-runs ridethrough.drivers.implied (unchanged) for one case, with the storage_resistance_pu rows replaced:
        slope vs outdoor temperature: the local slope near 25 C (local_slope_near25_pu_per_C) from battery_resistance_fit.csv (replaces the
            P3 two-point average -0.0889 pu/degC), times the room attenuation as before;
        noise: the Sandia replicate-cell spread (replaces 0.72%, the 1100-cell new-cell spread).
    Compared against the unchanged S matrix. s_matrix/ and noise.csv are not modified.

Case: coupling 1, noise_mult 1, psu_k 1, age_sd 4.33, dclink_n 1; attenuation "upper" (at "nominal" attenuation
    temperature has no effect on any factor, so nothing here changes).

Reads:  data_bayesian-network/network/responses/battery_resistance_fit.csv, battery_resistance_spread.csv, plus
        implied.load_inputs() files (read-only).
Writes: data_bayesian-network/network/responses/storage_resistance_correlation_comparison.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ridethrough.drivers import fit, implied, sample
from ridethrough.responses import battery_resistance as br

FACTOR = "storage_resistance_pu"
CASE = dict(implied.NOMINAL_CASE, attenuation="upper")
GROUPS = ("overall", "DJF", "JJA")


def variant_inputs(base: dict, slope: float | None, noise_rel: float | None) -> dict:
    """Copy of the implied inputs with the storage_resistance rows replaced (None = keep the original)."""
    inp = dict(base)
    s = base["s_long"].copy()
    m = (s["factor"] == FACTOR) & (s["driver"] == "outdoor_temp_c")
    if slope is not None:
        att = float(str(s.loc[m, "attenuation_upper"].iloc[0]))
        s.loc[m, "component_slope"] = slope
        s.loc[m, "slope_at_typical_nominal"] = 0.0
        s.loc[m, "slope_at_typical_upper"] = slope * att
    inp["s_long"] = s
    if noise_rel is not None:
        n = base["noise"].copy(); k = n["factor"] == FACTOR
        n.loc[k, "sd"] = noise_rel; n.loc[k, "sd_unit"] = "fraction (relative)"
        inp["noise"] = n
    return inp


def correlations(inp: dict, fitted: dict) -> pd.DataFrame:
    factors = implied.factor_list(inp["s_long"])
    s, _ = implied.build_s(inp["s_long"], inp["master"], CASE["attenuation"], CASE["psu_k"])
    noise = implied.build_noise(inp["noise"], inp["master"], factors, CASE["noise_mult"], CASE["dclink_n"])
    rows = []
    for g in GROUPS:
        sig = implied.build_sigma_d(implied.sampled_temp_load_cov(g, CASE["coupling"], fitted), inp["master"], CASE["age_sd"])
        cov, corr = implied.implied_cov(s, sig, noise["sd"])
        driven = float((s.loc[FACTOR] @ sig @ s.loc[FACTOR]) / cov.loc[FACTOR, FACTOR])
        for f in factors:
            if f != FACTOR and abs(corr.loc[FACTOR, f]) > 1e-12:
                rows.append(dict(group=g, other=f, correlation=corr.loc[FACTOR, f], driver_share_of_resistance_variance=driven))
    return pd.DataFrame(rows)


def main() -> None:
    base, fitted = implied.load_inputs(), sample.load_fitted()
    f = pd.read_csv(br.OUT_DIR / "battery_resistance_fit.csv"); sp = pd.read_csv(br.OUT_DIR / "battery_resistance_spread.csv")
    slopes = {"Sandia 1 Hz": f.loc[0, "local_slope_near25_pu_per_C"], "Panasonic 1 Hz": f.loc[1, "local_slope_near25_pu_per_C"],
              "Panasonic 10 mHz": f.loc[2, "local_slope_near25_pu_per_C"]}
    sd_rep = float(np.median(sp.loc[0, ["LCO", "LFP", "NCA"]].astype(float)))      # NMC excluded: one outlier cell
    variants = {"original (P3 slope, 0.72% noise)": (None, None)}
    for k, v in slopes.items():
        variants[f"slope {k} ({v:.4f}), noise {sd_rep:.3f}"] = (v, sd_rep)
    variants[f"original slope, noise {sd_rep:.3f}"] = (None, sd_rep)
    out = []
    for name, (sl, nz) in variants.items():
        c = correlations(variant_inputs(base, sl, nz), fitted); c.insert(0, "variant", name); out.append(c)
    res = pd.concat(out); res.to_csv(br.OUT_DIR / "storage_resistance_correlation_comparison.csv", index=False)
    pv = res.pivot_table(index=["group", "other"], columns="variant", values="correlation")
    print(pv.round(3).to_string())
    print(res.groupby(["variant", "group"]).driver_share_of_resistance_variance.first().unstack().round(3).to_string())


if __name__ == "__main__":
    main()
