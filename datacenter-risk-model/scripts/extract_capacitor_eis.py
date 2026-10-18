"""Extract per-capacitor capacitance (Cs at 100 Hz, uF) and ESR proxy (Re(Z) at 100 Hz) vs aging hours from NASA capacitor EIS (.mat v7.3).

Structure (decoded): EIS_Data/<cap>/EIS_Measurement/Data is a 73x1 cell; each cell is 5+ repeated sweeps, each an 18x59 matrix,
rows = [freq, Re(Z), -Im(Z), |Z|, phase, time, ..., Cs(uF) (row 8), Cp(uF) (row 9), ...]. EIS_Reference_Table row 3 = aging time (h).
Outputs data/processed/nasa_capacitor_eis.csv
Usage: python -I extract_capacitor_eis.py <ES10.mat> [ES12.mat ...]
"""
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main(paths):
    rows = []
    for p in paths:
        f = h5py.File(p, "r")
        grp = Path(p).stem  # ES10
        volts = int(grp[2:])
        eis = f[grp]["EIS_Data"]
        t = eis["EIS_Reference_Table"]
        hours = [float("".join(chr(int(c)) for c in np.asarray(f[t[3, j]][()]).ravel()) or "nan") for j in range(t.shape[1])]
        for cap in sorted(k for k in eis.keys() if k.startswith(grp + "C")):
            D = eis[cap]["EIS_Measurement"]["Data"]
            for i in range(D.shape[0]):
                try:
                    sweeps = [np.asarray(f[x][()]) for x in f[D[i, 0]][()].ravel()]
                except Exception:
                    continue
                sweeps = [s for s in sweeps if s.ndim == 2 and s.shape[0] >= 10 and abs(s[0, -1] - 100) < 5]
                if not sweeps:
                    continue
                cs = np.array([s[8, -1] for s in sweeps]); re = np.array([s[1, -1] for s in sweeps])
                rows.append(dict(group=grp, stress_v=volts, cap=cap, meas=i, aging_h=hours[i] if i < len(hours) else np.nan,
                                 n_sweeps=len(sweeps), cs_uf=float(np.median(cs)), cs_sd=float(cs.std()), re_z_ohm_100hz=float(np.median(re))))
    d = pd.DataFrame(rows)
    d["c_rel"] = d.cs_uf / d.groupby("cap").cs_uf.transform(lambda s: s.iloc[:3].median())
    d.to_csv(ROOT / "data/processed/nasa_capacitor_eis.csv", index=False)
    print(d.groupby("cap").agg(n=("meas", "size"), h_max=("aging_h", "max"), c0=("cs_uf", "first"), c_last=("cs_uf", "last"), c_rel_min=("c_rel", "min")).round(2).to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
