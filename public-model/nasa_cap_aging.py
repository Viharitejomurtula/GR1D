"""Empirical electrolytic-capacitor aging from NASA 'Capacitor Electrical Stress-2' (EOS_DataSet.mat; 6 caps, 10 V stress, 194 h).
Values are %-change from baseline. ASSUMPTION: C column = % capacitance LOSS (monotone rising; consistent with electrolytic wear-out),
ESR column = % ESR increase. Sign/units not verified against the paper (could not download it).
CONFLICT: the other agent's fit of a different NASA capacitor set (datacenter-risk-model/models/capacitor_degradation_params.json) gives only ~8% loss at 10 V (saturating) vs ~21% here at 194 h, so this dataset's 'C' column or its stress level is NOT confirmed; treat as unresolved."""
import numpy as np, load_eos, csv, os
_H = os.path.dirname(os.path.abspath(__file__))
D = load_eos.load(os.path.join(_H, "raw/nasa_cap/x/EOS_DataSet.mat"))
HRS, ESR, C = D["aging_time"].ravel(), D["ESR"], D["C"]       # ESR, C: (11 times, 6 caps)

def export(path=os.path.join(_H, "processed/nasa_eos_capacitor.csv")):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["hours", "cap_id", "esr_pct_increase", "c_pct_loss"])
        for i, h in enumerate(HRS):
            for j in range(C.shape[1]): w.writerow([h, j, ESR[i, j], C[i, j]])

def c_multiplier(hours, cap=None):
    """Empirical C/C0 at test-hours (mean across caps, or one cap), linear interp; extrapolation not allowed."""
    y = (C.mean(1) if cap is None else C[:, cap])
    return 1 - np.interp(hours, HRS, y, left=np.nan, right=np.nan) / 100

def esr_multiplier(hours, cap=None):
    y = (ESR.mean(1) if cap is None else ESR[:, cap])
    return 1 + np.interp(hours, HRS, y, left=np.nan, right=np.nan) / 100

if __name__ == "__main__":
    import models as m
    export()
    print("unit-to-unit spread of C loss at 194 h: min %.1f max %.1f mean %.1f std %.2f %%" % (C[-1].min(), C[-1].max(), C[-1].mean(), C[-1].std(ddof=1)))
    print("ESR rise at 194 h: mean %.1f %% std %.2f" % (ESR[-1].mean(), ESR[-1].std(ddof=1)))
    print("hours  Cmult  hold-up@100%  @150%  STS max detect(60Hz,100%)")
    for h in (0, 71, 139, 171, 194):
        cm = float(c_multiplier(h)); print(f"{h:5} {cm:.3f} {m.holdup_aged(1.0, cm):8.2f} {m.holdup_aged(1.5, cm):8.2f} {m.holdup_aged(1.0, cm)-4.167:8.2f}")
    # worst single cap
    cm = float(c_multiplier(194, cap=int(C[-1].argmax()))); print("worst cap @194h: Cmult %.3f hold-up@100%% %.2f ms" % (cm, 20*cm))
