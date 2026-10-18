"""Build a library of realistic voltage dips from ANDES fault studies.

A square dip misses what actually happens after a fault clears: voltage recovers over
tens of milliseconds and typically overshoots before settling. ANDES gives that shape
from grid physics rather than assumption.

The curves are not fed into the simulator verbatim. A surrogate needs fixed-length
numeric inputs, and an FMU carrying external CSVs is awkward to distribute, so each
ANDES run is reduced to four numbers the simulator can take as parameters:

    retained voltage, duration, recovery time constant, overshoot

ANDES then supplies the realistic *joint distribution* of those four, which is the part
a square dip cannot provide. Dip depth comes from fault distance: faulting at the
monitored bus gives ~0 pu, while remote faults give the 0.3-0.8 pu range real
facilities see.

Limitation: ANDES models balanced three-phase faults. The real ERCOT events we validate
against were unbalanced (1-2 phases below 0.7 pu), and a balanced model trips the whole
facility where a real one loses only the affected phases. See Parameter_Table.md.

Usage:  python3 scripts/andes_dips.py --out data/dip_library.csv
"""

from __future__ import annotations

import argparse
import csv
import pathlib

import numpy as np

MONITOR_BUS = 4  # the bus treated as the data center's Service Delivery Point


def characterize(t: np.ndarray, v: np.ndarray, t_fault: float, t_clear: float) -> dict | None:
    """Reduce one voltage trace to the four shape parameters."""
    pre = v[t < t_fault - 0.01]
    if pre.size == 0:
        return None
    v_pre = float(pre.mean())

    during = v[(t >= t_fault) & (t <= t_clear)]
    if during.size == 0:
        return None
    retained = float(during.mean() / v_pre)

    after = (t > t_clear)
    if not after.any():
        return None
    t_a, v_a = t[after], v[after] / v_pre

    # Recovery time constant: time to climb back within 10% of nominal.
    back = np.nonzero(v_a >= 0.9)[0]
    recovery_tau = float(t_a[back[0]] - t_clear) if back.size else float(t_a[-1] - t_clear)

    # Overshoot: the peak above nominal in the half second after clearing.
    window = v_a[t_a <= t_clear + 0.5]
    overshoot = float(max(0.0, window.max() - 1.0)) if window.size else 0.0

    return {
        "retained_pu": round(retained, 4),
        "duration_s": round(t_clear - t_fault, 4),
        "recovery_tau_s": round(recovery_tau, 4),
        "overshoot_pu": round(overshoot, 4),
    }


def run_case(fault_bus: int, clear_s: float) -> dict | None:
    import andes

    andes.config_logger(stream_level=40)
    t_fault = 1.0
    t_clear = t_fault + clear_s
    try:
        ss = andes.load(andes.get_case("ieee14/ieee14_full.xlsx"), setup=False, no_output=True)
        ss.add("Fault", dict(bus=fault_bus, tf=t_fault, tc=t_clear))
        ss.setup()
        ss.PFlow.run()
        ss.TDS.config.tf = t_clear + 1.0
        ss.TDS.run()
    except Exception:
        return None

    t = np.array(ss.dae.ts.t)
    v = np.array(ss.dae.ts.y)[:, ss.Bus.v.a[MONITOR_BUS - 1]]
    row = characterize(t, v, t_fault, t_clear)
    if row:
        row |= {"fault_bus": fault_bus}
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/dip_library.csv")
    # Clearing times from the researched fault-clearing range: 4-6 cycles normal,
    # 9-15 cycles on breaker failure.
    ap.add_argument("--clearing", default="0.067,0.083,0.10,0.15,0.20")
    ap.add_argument("--buses", default="2,3,5,6,9,10,12,13,14")
    args = ap.parse_args()

    buses = [int(b) for b in args.buses.split(",")]
    clearings = [float(c) for c in args.clearing.split(",")]

    rows = []
    for bus in buses:
        if bus == MONITOR_BUS:
            continue
        for clear in clearings:
            row = run_case(bus, clear)
            if row:
                rows.append(row)
                print(
                    f"  bus {bus:>2} clear {clear:.3f}s -> retained {row['retained_pu']:.3f}, "
                    f"recovery {row['recovery_tau_s']:.3f}s, overshoot {row['overshoot_pu']:.3f}"
                )

    if not rows:
        raise SystemExit("no ANDES cases converged")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["fault_bus", "retained_pu", "duration_s", "recovery_tau_s", "overshoot_pu"])
        w.writeheader()
        w.writerows(rows)

    ret = np.array([r["retained_pu"] for r in rows])
    print(f"\n{len(rows)} dips -> {out}")
    print(f"retained voltage: min {ret.min():.3f}, median {np.median(ret):.3f}, max {ret.max():.3f}")


if __name__ == "__main__":
    main()
