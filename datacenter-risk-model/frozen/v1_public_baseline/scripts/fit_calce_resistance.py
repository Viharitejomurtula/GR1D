"""DC internal resistance vs SOC and temperature for an NMC cell (CALCE INR 18650-20R, LiNiMnCo/graphite, 2.0 Ah) from DST dynamic tests at 0/25/45 C.

Method: R = dV/dI across consecutive samples where |dI| >= 1 A and dt <= 1.5 s (pulse step response, ~<=1 s: ohmic + fast charge-transfer, not full polarization).
SOC axis: SOC0 (80% or 50% start, from file name) minus net discharged charge scaled so SOC reaches ~0 at the end of the discharge test; bins of 10% SOC.
Outputs data/processed/calce_inr_dc_resistance.csv, models/battery_dc_resistance_params.json, figures/calce_dc_resistance.png
Usage: python -I fit_calce_resistance.py"""
import glob
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
rows = []
for f in sorted(glob.glob(str(ROOT / "data/interim/calce/SP2_*C_DST/*.xls"))):
    temp = int(re.search(r"SP2_(\d+)C_DST", f).group(1)); soc0 = int(re.search(r"(\d+)SOC", f).group(1)) / 100
    d = pd.read_excel(f, sheet_name=1)[["Test_Time(s)", "Step_Index", "Current(A)", "Voltage(V)", "Charge_Capacity(Ah)", "Discharge_Capacity(Ah)"]].copy()
    d.columns = ["t", "step", "i", "v", "qc", "qd"]
    # net discharged Ah within the DST: capacity counters reset per step, so integrate current
    dt = d.t.diff().fillna(0).clip(0, 60)
    net = -(d.i * dt).cumsum() / 3600.0  # Ah discharged (discharge current negative)
    net = net - net.min()
    soc = soc0 * (1 - net / net.max())
    dI, dV, dT = d.i.diff(), d.v.diff(), d.t.diff()
    ok = (dI.abs() >= 1.0) & (dT <= 1.5) & (d.step == d.step.shift())
    r = (dV / dI)[ok]
    s = pd.DataFrame(dict(temp_c=temp, soc0=soc0, soc=soc[ok], r_ohm=r, di=dI[ok]))
    s = s[(s.r_ohm > 0) & (s.r_ohm < 0.5)]
    rows.append(s)
    print(f"{temp:>2} C soc0 {soc0:.1f}: {len(s)} step responses, median R {s.r_ohm.median()*1000:.0f} mOhm, discharged {net.max():.2f} Ah")
R = pd.concat(rows)
R["soc_bin"] = (np.clip(R.soc, 0, 0.999) * 10).astype(int) * 10
R.to_csv(ROOT / "data/processed/calce_inr_dc_resistance.csv", index=False)
tab = R.groupby(["temp_c", "soc_bin"]).r_ohm.agg(n="size", median="median", p25=lambda x: x.quantile(.25), p75=lambda x: x.quantile(.75)).reset_index()
tab = tab[tab.n >= 20]
print((tab.assign(median=lambda x: (x["median"] * 1000).round(0), p25=lambda x: (x.p25 * 1000).round(0), p75=lambda x: (x.p75 * 1000).round(0))).to_string(index=False))
q = lambda x: np.quantile(x, [0.05, 0.25, 0.5, 0.75, 0.95]).round(4).tolist()
out = dict(source_id="F2e", kind="observed (CALCE INR 18650-20R NMC/graphite 2.0 Ah, DST at 0/25/45 C, starting SOC 50% and 80%)", units="ohm per cell",
           method="pulse response dV/dI over <=1.5 s steps with |dI|>=1 A", soc_bins_pct=sorted(tab.soc_bin.unique().tolist()),
           table=[dict(temp_c=int(r.temp_c), soc_bin_pct=int(r.soc_bin), n=int(r.n), median=float(r["median"]), p25=float(r.p25), p75=float(r.p75)) for _, r in tab.iterrows()],
           pooled_by_temp={f"{int(t)}C": dict(n=int(len(g)), quantiles_5_25_50_75_95=q(g.r_ohm)) for t, g in R.groupby("temp_c")},
           limitations=["Fresh cells only: no aging growth (aging from NASA EIS); pulse resistance depends on pulse duration and current",
                        "SOC axis reconstructed from integrated current within a single discharge test starting at 50% or 80% SOC, so SOC < 50% is covered only by the 80% runs",
                        "One cell type (Samsung-style INR 18650-20R), 1-2 samples; pack-level resistance requires series/parallel scaling assumptions"])
(ROOT / "models/battery_dc_resistance_params.json").write_text(json.dumps(out, indent=1))
fig, ax = plt.subplots(figsize=(6, 4))
for t, g in tab.groupby("temp_c"): ax.plot(g.soc_bin + 5, g["median"] * 1000, "o-", label=f"{t} C")
ax.set(xlabel="SOC %", ylabel="DC resistance mOhm (median)", title="CALCE INR NMC cell"); ax.legend(); fig.tight_layout(); fig.savefig(ROOT / "figures/calce_dc_resistance.png", dpi=120)
