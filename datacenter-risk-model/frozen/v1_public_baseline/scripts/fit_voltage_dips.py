"""Voltage-sag event model from EPRI DPQ II (Report 1002199, Tables 2-1 and 2-2; values transcribed from the PDF text).

OBSERVED (EPRI): site-median annual sag counts by depth threshold and monitoring location, and ITIC-sag quartiles across sites
(events <= 1 min, 1-minute aggregation). From these: annual event rate per depth bin and a lognormal across-site rate distribution.
NOT in the report (explicit ASSUMPTIONS, must be set/validated by the user): duration distribution and number of phases affected.
Outputs models/voltage_dip_params.json, figures/voltage_dips.png
Usage: python -I fit_voltage_dips.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
# Table 2-1: site medians (events/yr)
T21 = {  # location -> {threshold: median events/yr}
    "transmission": {"SARFI80": 9.0, "SARFI_ITIC": 6.3, "SARFI70": 5.8, "SARFI_SEMI": 4.8, "SARFI50": 3.3},
    "substation": {"SARFI80": 20.8, "SARFI_ITIC": 12.6, "SARFI70": 10.3, "SARFI_SEMI": 8.4, "SARFI50": 3.8},
    "feeder": {"SARFI80": 30.8, "SARFI_ITIC": 21.5, "SARFI70": 20.4, "SARFI_SEMI": 16.1, "SARFI50": 10.9},
}
# Table 2-2: DPQ II SARFI_ITIC quartiles across sites (25th, 50th, 75th percentile)
T22 = {"transmission": (3.5, 6.3, 10.7), "substation": (5.7, 9.4, 16.1), "feeder": (14.4, 22.1, 35.9)}

out = dict(source_id="F2a", kind="observed aggregate (EPRI DPQ II sag statistics, monitored 2000s) + explicit assumptions",
           units=dict(rate="events per year at a site", depth="per-unit residual voltage"), locations={})
z75 = 0.6745
for loc, t in T21.items():
    # depth bins by residual voltage: SARFI_x counts events below x (cumulative); bin = difference
    b80_70 = t["SARFI80"] - t["SARFI70"]
    b70_50 = t["SARFI70"] - t["SARFI50"]
    b50 = t["SARFI50"]
    q25, q50, q75 = T22[loc]
    # lognormal across sites for rate multiplier (relative to median), from quartiles (log-space, symmetric approx)
    sigma = (np.log(q75) - np.log(q25)) / (2 * z75)
    out["locations"][loc] = dict(
        site_median_events_per_year=t,
        depth_bins_rate_per_year={"0.70-0.80pu": round(b80_70, 2), "0.50-0.70pu": round(b70_50, 2), "<0.50pu": round(b50, 2)},
        itic_site_quartiles=[q25, q50, q75], site_rate_lognormal_sigma=round(float(sigma), 3),
        note="medians (not means: mean 31-115% above median per EPRI); sag counts exclude events > 1 min")
out["sampling"] = dict(method="site rate multiplier m ~ LogNormal(0, sigma); annual count per bin ~ Poisson(m * bin_rate); depth uniform within bin (assumption)",
                       depth_within_bin="uniform (assumption)")
out["assumptions_not_from_data"] = dict(
    duration="NOT IN EPRI REPORT (EPRI: duration follows protective-device clearing). Grounded on ERCOT evidence (PDCWG Nov 2024 large-load deck): normal clearing 3-4 cycles; "
             "delayed clearing from breaker failure 10-19 cycles. Default mixture (weights ASSUMED): 90% normal clearing 3-5 cycles, 10% delayed clearing 10-20 cycles. "
             "ITIC/SEMI vs SARFI80 gap is the only duration signal in the data (transmission: 30% of sags below 80% fall inside the ITIC envelope).",
    phases="NOT IN EPRI REPORT. Phase count (1 vs 3) must be assumed; ERCOT 2024 large-load deck reports SLG faults causing larger load reductions than modeled for shallow positive-sequence dips.",
    transfer="EPRI sites are US distribution-system sites; ERCOT/Texas lightning, line length and local grid strength not represented (EPRI prediction equations need site parameters not available here).")
out["limitations"] = ["Aggregate site statistics, not raw events; no joint depth-duration-phase distribution",
                      "Dataset from early-2000s DPQ II monitoring; grid and loads have changed",
                      "Transmission group has N=53 sites; Texas not isolated",
                      "Depth bins derived by differencing cumulative SARFI medians (medians do not strictly add)"]
(ROOT / "models" / "voltage_dip_params.json").write_text(json.dumps(out, indent=1))
for loc, d in out["locations"].items():
    print(loc, d["depth_bins_rate_per_year"], "sigma", d["site_rate_lognormal_sigma"])
fig, ax = plt.subplots(figsize=(6, 4))
w = 0.25
for i, (loc, d) in enumerate(out["locations"].items()):
    r = d["depth_bins_rate_per_year"]; ax.bar(np.arange(3) + i * w, list(r.values()), w, label=loc)
ax.set_xticks(np.arange(3) + w); ax.set_xticklabels(list(r.keys())); ax.set(ylabel="events/yr (site median)", title="EPRI DPQ II sag rate by depth"); ax.legend()
fig.tight_layout(); fig.savefig(ROOT / "figures/voltage_dips.png", dpi=120)
