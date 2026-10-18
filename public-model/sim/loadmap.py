"""PSU loading as a KNOB (provisioning choice), not a random factor. For each fixed load level x restart-surge level: min/max P(IT failure)
over the remaining unknown intervals (LHS outer, aleatory inner). Maintenance fixed: all units up. Event class: general sags and loss events."""
import sys, numpy as np
from network import net, EP, OUTCOMES
rng = np.random.default_rng(3)
free = [k for k in EP if k not in ("load_mean", "surge_pu", "units_down", "p_isolated", "p_ridetest")]
lo = np.array([EP[k][0] for k in free]); hi = np.array([EP[k][1] for k in free])
M = 120
U = np.stack([(rng.permutation(M) + rng.uniform(size=M)) / M for _ in free], 1)
for cls, cdo in (("loss events", {"ep_p_isolated": 0, "ep_p_ridetest": 0}), ("general sags", {"ep_p_isolated": 1, "ep_p_ridetest": 0})):
    print(f"\n[{cls}]  P(IT failure) over the other unknowns: min-max   (P_cooling_trip is load-independent)")
    print("load \\ surge   " + "   ".join(f"{sp:>10.2f}" for sp in (1.0, 1.25, 1.5, 2.0)))
    for ld in (0.3, 0.6, 0.8):
        row = []
        for sp in (1.0, 1.25, 1.5, 2.0):
            ys = []
            for u in U:
                do = {"ep_" + k: v for k, v in zip(free, lo + u * (hi - lo))}; do.update(cdo); do.update({"ep_load_mean": ld, "ep_surge_pu": sp, "ep_units_down": 0.0})
                ys.append(net.sample(800, np.random.default_rng(5), do=do)["it_failure"].mean())
            row.append(f"{min(ys):.2f}-{max(ys):.2f}")
        print(f"{ld:>5.0%}         " + "   ".join(f"{r:>10}" for r in row))
