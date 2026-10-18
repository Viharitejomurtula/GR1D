"""Clean NASA PCoE battery .mat files into per-cycle tables (CSV).

Outputs (data/processed/):
  nasa_battery_discharge.csv  one row per discharge cycle (capacity, temps, voltages)
  nasa_battery_impedance.csv  one row per EIS sweep (Re, Rct)
Usage: python -I clean_nasa_battery.py <extracted_dir> <out_dir>
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio


RATED_AH = 2.0
CAP_MIN_AH, CAP_MAX_AH = 0.5, 2.2  # outside this: README-noted anomalous/low-capacity runs
Z_MAX_OHM = 1.0  # EIS Re/Rct above this are fit failures (values up to ~1e15 seen)


def start_time(v) -> datetime:
    v = np.atleast_1d(v).astype(float)
    return datetime(int(v[0]), int(v[1]), int(v[2]), int(v[3]), int(v[4])) + timedelta(seconds=float(v[5]))


def scalar(x):
    x = np.atleast_1d(x)
    if not x.size:
        return np.nan
    return float(x[0].real) if abs(np.imag(x[0])) < 1e-12 else np.nan  # complex => bad EIS fit


def load_cell(path: Path):
    cell = path.stem
    cycles = sio.loadmat(path, squeeze_me=True, struct_as_record=False)[cell].cycle
    dis, imp = [], []
    n_dis = n_imp = 0
    for i, c in enumerate(np.atleast_1d(cycles)):
        t = start_time(c.time)
        d = c.data
        if c.type == "discharge":
            n_dis += 1
            v, cur, temp, tm = (np.atleast_1d(getattr(d, k)).astype(float) for k in
                                ("Voltage_measured", "Current_measured", "Temperature_measured", "Time"))
            dis.append(dict(cell=cell, op_index=i, discharge_n=n_dis, start=t,
                            ambient_c=float(c.ambient_temperature), capacity_ah=scalar(d.Capacity),
                            duration_s=tm[-1] if tm.size else np.nan,
                            mean_current_a=cur.mean(), v_start=v[0], v_end=v[-1],
                            temp_mean_c=temp.mean(), temp_max_c=temp.max()))
        elif c.type == "impedance":
            n_imp += 1
            imp.append(dict(cell=cell, op_index=i, impedance_n=n_imp, start=t,
                            ambient_c=float(c.ambient_temperature),
                            re_ohm=scalar(d.Re), rct_ohm=scalar(d.Rct),
                            discharges_before=n_dis))
    return dis, imp


def main(src: Path, out: Path):
    dis, imp, seen = [], [], {}
    for p in sorted(src.rglob("B*.mat")):
        d, i = load_cell(p)
        key = p.stem
        # Cells 25-28 appear in two archives; keep the longer record
        if key in seen and len(d) <= seen[key][0]:
            print(f"skip duplicate {p.parent.name}/{p.name} ({len(d)} <= {seen[key][0]} discharges)")
            continue
        if key in seen:
            print(f"replace earlier {key} ({seen[key][0]} discharges) with {p.parent.name} ({len(d)})")
            dis = [r for r in dis if r["cell"] != key]
            imp = [r for r in imp if r["cell"] != key]
        seen[key] = (len(d), p.parent.name)
        dis += d
        imp += i
    D, I = pd.DataFrame(dis), pd.DataFrame(imp)
    D["source_archive"] = D["cell"].map(lambda c: seen[c][1])
    # Quality flags (rows are kept; filter on *_valid when fitting)
    D["soh_vs_rated"] = D["capacity_ah"] / RATED_AH  # EOL = 0.70 (README: 2.0 -> 1.4 Ah)
    D["capacity_valid"] = D["capacity_ah"].between(CAP_MIN_AH, CAP_MAX_AH)
    I["impedance_valid"] = I["re_ohm"].between(0, Z_MAX_OHM) & I["rct_ohm"].between(0, Z_MAX_OHM)
    out.mkdir(parents=True, exist_ok=True)
    D.to_csv(out / "nasa_battery_discharge.csv", index=False)
    I.to_csv(out / "nasa_battery_impedance.csv", index=False)
    print(D.groupby(["ambient_c"]).agg(cells=("cell", "nunique"), rows=("cell", "size")))
    print("valid capacity rows:", int(D.capacity_valid.sum()), "of", len(D),
          "| valid impedance rows:", int(I.impedance_valid.sum()), "of", len(I))
    print(len(D), "discharge rows;", len(I), "impedance rows;", D.cell.nunique(), "cells")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
