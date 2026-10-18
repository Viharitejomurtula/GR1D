"""Does facility heterogeneity change what the validation sees? n_groups = 1 (lumped) vs 6 groups with increasing spread in loading,
hold-up health, BBU sizing and lockout threshold. Reports sustained loss and cycle-averaged peak current; nothing is fitted."""
from dataclasses import replace
from sim import runner
from validation.cases import CASES
print("case          n  cv    loss   peak_I  mode")
for name in ("facility_A", "facility_B", "shallow_0p844"):
    for n, cv in ((1, 0.0), (6, 0.0), (6, 0.2), (6, 0.4)):
        sc = replace(CASES[name]["sc"], n_groups=n, grp_load_cv=cv, grp_holdup_cv=cv, grp_bbu_cv=cv, grp_trip_cv=cv)
        g = runner.run(sc, tag="het"); print(f"{name:13} {n}  {cv:.1f}  {1 - g.final_power_frac:6.3f}  {g.peak_current_pu:6.3f}  {g.failure_mode}", flush=True)
