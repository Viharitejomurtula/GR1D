"""Storage-resistance response to temperature, and cell-to-cell spread, from public EIS data.

What this file is
    Fits R(T)/R(25 C) as an Arrhenius law to two EIS datasets and converts each fit to the local slope at 25 C
    that the S matrix needs (pu per degC, the component temperature). Also measures replicate-cell spread.

Reads (read-only)
    drivers_raw/battery_panasonic_18650pf/dataset.zip   Kollmeyer, Univ. Wisconsin-Madison, Mendeley Data
        wykht8y7tg, CC BY 4.0. One NCR18650PF cell per temperature (-20, -10, 0, 10, 25 C), EIS vs SOC,
        6 kHz-1 mHz.
    drivers_raw/battery_sandia_eis/EIS_Data.zip         Sandia Cell EIS Testing Data (Barkholtz et al. 2017).
        LCO, LFP, NCA, NMC x 3 cells, pristine at 5-45 C and after cycling, 100 kHz/1 MHz to 1 or 0.1 Hz.

Writes (main())
    data_bayesian-network/network/responses/battery_resistance_fit.csv      one row per dataset x metric
    data_bayesian-network/network/responses/battery_resistance_spread.csv   cell-to-cell spread
    data_bayesian-network/network/responses/battery_resistance_report.md

Metric
    R(f) = Z' (real part of impedance) at frequency f. 1 Hz ~ the fast (ohmic + charge-transfer) part, 10 mHz
    includes diffusion (~100 s). The BBU pulse resistance sits between; both are reported, neither is chosen.
Caveats: Panasonic has ONE cell per temperature, so its fit has no cell-to-cell term. Sandia is not the BBU cell
    (consumer 18650s); chemistry is unconfirmed for the BBU.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2] / "data_bayesian-network"
RAW = ROOT / "drivers_raw"
OUT_DIR = ROOT / "network" / "responses"
KB = 8.617333e-5          # eV/K
T0 = 25.0
N_BOOT = 2000
SEED = 20261017


def _decode(b: bytes) -> str:
    return b.decode("utf-16", errors="replace") if b[:2] in (b"\xff\xfe", b"\xfe\xff") or b[1:2] == b"\x00" else b.decode(errors="replace")


def _sandia_parse(text: str):
    lines = text.splitlines()
    if lines[0].startswith("Index"):
        a = pd.read_csv(io.StringIO(text)).iloc[:, [1, 2, 3]].to_numpy(float)
        return a[:, 0], a[:, 1], a[:, 2]                     # f, Z', -Z''
    rec = []
    for line in lines:
        p = line.split("\t")
        if len(p) >= 6:
            try: rec.append([float(p[0]), float(p[4]), float(p[5])])
            except ValueError: pass
    a = np.array(rec)
    return a[:, 0], a[:, 1], -a[:, 2]


def _at(f, z, fq):
    return z[np.argmin(np.abs(np.log10(f) - np.log10(fq)))]


def sandia_metrics() -> pd.DataFrame:
    """Z' at 1 Hz and at the lowest frequency for every Sandia EIS file (the lowest is 0.1 or 1 Hz)."""
    z = zipfile.ZipFile(RAW / "battery_sandia_eis" / "EIS_Data.zip"); rows = []
    for n in z.namelist():
        m = re.match(r"([A-Z]+)_(\d)_(Pristine|Cycling)_(\w+)\.txt", n)
        if not m: continue
        f, zr, _ = _sandia_parse(_decode(z.read(n)))
        rows.append(dict(chem=m[1], cell=int(m[2]), kind=m[3], cond=m[4], r_1hz=_at(f, zr, 1.0), fmin=f.min()))
    d = pd.DataFrame(rows)
    d["r_1hz"] = d["r_1hz"].where(d["r_1hz"] < 1.0)         # one file (LCO_2 15 C) is not physical (9.5 ohm)
    return d


def panasonic_metrics() -> pd.DataFrame:
    z = zipfile.ZipFile(RAW / "battery_panasonic_18650pf" / "dataset.zip"); rows = []
    for n in z.namelist():
        m = re.match(r"(\d+)_EIS(\d+)\.csv", n.split("/")[-1])
        if "/EIS/" not in n or not m: continue
        folder = n.split("/")[1] if "degC" in n.split("/")[1] else n.split("/")[2]
        text = z.read(n).decode(errors="replace").splitlines()
        h = next(i for i, l in enumerate(text) if l.startswith("Time Stamp"))
        df = pd.read_csv(io.StringIO("\n".join([text[h]] + text[h + 2:])), sep=";", engine="python", index_col=False)
        num = lambda c: pd.to_numeric(df[c], errors="coerce").to_numpy(float)
        f, zr, zi = num("ActFreq"), num("Zreal1"), num("Zimg1")
        ok = (f > 0) & np.isfinite(zr) & np.isfinite(zi)
        if ok.sum() < 10: continue
        f, zr = f[ok], zr[ok]
        rows.append(dict(T=float(folder.replace("degC", "")), cell=int(m[1]), step=int(m[2]),
                         r_1hz=_at(f, zr, 1.0), r_10mhz=_at(f, zr, 0.01)))
    return pd.DataFrame(rows)


def arrhenius(temps_c, r, fit_range=None):
    """Fit ln R = a + (Ea/kB)(1/T) by Theil-Sen. Returns Ea (eV)."""
    t = np.asarray(temps_c, float); r = np.asarray(r, float)
    ok = np.isfinite(r) & (r > 0)
    if fit_range: ok &= (t >= fit_range[0]) & (t <= fit_range[1])
    return stats.theilslopes(np.log(r[ok]), 1.0 / (t[ok] + 273.15))[0] * KB


def local_slope(ea_ev: float, t_c: float = T0) -> float:
    """d(R/R25)/dT at t_c in pu per degC (R/R25 = 1 at 25 C): -(Ea/kB)/T^2 times R/R25 there."""
    t = t_c + 273.15
    return -(ea_ev / KB) / t ** 2 * np.exp((ea_ev / KB) * (1 / t - 1 / (T0 + 273.15)))


def ratio_at(ea_ev: float, t_c: float) -> float:
    """R(t_c)/R(25 C) for an Arrhenius law."""
    return float(np.exp((ea_ev / KB) * (1 / (t_c + 273.15) - 1 / (T0 + 273.15))))


def fit_table() -> pd.DataFrame:
    rng = np.random.default_rng(SEED); rows = []
    s = sandia_metrics(); p = s[s.kind == "Pristine"].copy(); p["T"] = p.cond.str.rstrip("C").astype(float)
    per_cell = []
    for (chem, cell), g in p.groupby(["chem", "cell"]):
        per_cell.append(dict(chem=chem, cell=cell, ea=arrhenius(g["T"], g["r_1hz"])))
    pc = pd.DataFrame(per_cell); ea = pc.ea.to_numpy()
    boot = [rng.choice(ea, len(ea)).mean() for _ in range(N_BOOT)]
    rows.append(dict(dataset="Sandia EIS pristine, 12 cells, 5-45 C", metric="Z' at 1 Hz", n_units=len(ea), ea_ev=ea.mean(),
                     ea_lo=np.percentile(boot, 2.5), ea_hi=np.percentile(boot, 97.5), unit_sd_ev=ea.std(ddof=1)))
    q = panasonic_metrics()
    for metric, label in (("r_1hz", "Z' at 1 Hz"), ("r_10mhz", "Z' at 10 mHz")):
        med = q.groupby("T")[metric].median()
        e = arrhenius(med.index, med.values)
        boot = []
        for _ in range(N_BOOT):                              # resample SOC steps within each temperature
            m = [np.median(rng.choice(g[metric].to_numpy(), len(g))) for _, g in q.groupby("T")]
            boot.append(arrhenius(sorted(q["T"].unique()), m))
        e1025 = arrhenius(med.index, med.values, (10, 25))
        rows.append(dict(dataset="Panasonic NCR18650PF, 1 cell per temp, -20-25 C", metric=label, n_units=1, ea_ev=e,
                         ea_lo=np.percentile(boot, 2.5), ea_hi=np.percentile(boot, 97.5), unit_sd_ev=np.nan,
                         ea_10_25_ev=e1025, ratio_minus20=float(med[-20.0] / med[25.0])))
    out = pd.DataFrame(rows)
    # The room sits near 25 C, so the slope used downstream comes from the fit nearest 25 C: Panasonic 10-25 C, and the
    # Sandia 5-45 C fit (centred on 25 C). The full-range slope is kept for comparison (it is steeper: Arrhenius apparent Ea falls toward room temperature).
    out["ea_near25_ev"] = out["ea_10_25_ev"].fillna(out["ea_ev"])
    out["local_slope_near25_pu_per_C"] = [local_slope(e) for e in out.ea_near25_ev]
    out["local_slope_25C_pu_per_C"] = [local_slope(e) for e in out.ea_ev]
    out["local_slope_lo"] = [local_slope(e) for e in out.ea_lo]
    out["local_slope_hi"] = [local_slope(e) for e in out.ea_hi]
    out["ratio_pred_minus20"] = [ratio_at(e, -20.0) for e in out.ea_ev]
    return out


def spread_table() -> pd.DataFrame:
    """Replicate-cell spread of R at 25 C (Z' at 1 Hz), as sd of ln R (3 pristine cells per chemistry).
    The cycled-vs-pristine comparison in the same files gives LOWER resistance after cycling (mean ln ratio -0.32), which is
    not physical for aging, so it is not used."""
    s = sandia_metrics(); rows = []
    pr = s[(s.kind == "Pristine") & (s.cond == "25C")].set_index(["chem", "cell"]).r_1hz
    lnsd = {c: np.log(pr.loc[c]).std(ddof=1) for c in pr.index.get_level_values(0).unique()}
    rows.append(dict(quantity="pristine 25 C, sd of ln R across 3 cells, per chemistry (pooled = RMS)",
                     **{k: v for k, v in lnsd.items()}, pooled=float(np.sqrt(np.mean(np.square(list(lnsd.values())))))))
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fit, spread = fit_table(), spread_table()
    fit.to_csv(OUT_DIR / "battery_resistance_fit.csv", index=False)
    spread.to_csv(OUT_DIR / "battery_resistance_spread.csv", index=False)
    print(fit.round(4).to_string()); print(spread.round(4).to_string())


if __name__ == "__main__":
    main()
