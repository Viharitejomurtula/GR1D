"""Replay the three documented ERCOT dips against both designs.

Panel 04 of the results page compares legacy equipment against the product on the same
facility, and its numbers are currently invented. This produces them: six runs, three
dip depths by two designs.

Each bar is the share of pre-disturbance power the site had regained 2.0 s after voltage
returned above 0.90 pu -- the NOGRR recovery test. Crossing 90% is a pass.

Both designs run on the same facility (same supply voltage, same faulted-phase share), so
the only thing that differs is the equipment. That is the comparison a utility or financier
would want: not two facilities, one upgrade.

    python3 scripts/export_events.py
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sim import constants as C  # noqa: E402
from sim import runner  # noqa: E402
from sim.scenario import GRID_FRIENDLY, LEGACY_UPS  # noqa: E402

# The three dips in the NERC crypto incident review (Jan 2026). Phase shares are as
# reported; the 0.844 case has no phase detail published, so it runs balanced.
EVENTS = [
    {"pu": 0.535, "duration_s": 0.10, "phases": 2 / 3, "tag": "Deepest"},
    {"pu": 0.670, "duration_s": 0.10, "phases": 1 / 3, "tag": "Mid"},
    {"pu": 0.844, "duration_s": 0.10, "phases": 1.0, "tag": "Shallow"},
]

# Crypto facilities ran 208 V; the validation cases only reproduce at that supply.
SUPPLY_V = 208.0

# The LEGACY_UPS preset carries two separate non-compliant behaviours: a slow hand-back
# and a latching relay at 0.85 pu. All three documented dips sit below 0.85, so the relay
# alone takes the whole facility off permanently and every bar reads zero.
#
# This panel is "same facility, better UPS", not "same facility, and also remove a trip
# scheme NOGRR 2.14(6) bans outright". So the legacy side here keeps the slow hand-back,
# the late PSU restart and the unprotected cooling contactor, and drops the latching relay.
# The counting-scheme design is a separate comparison, and a more damning one.
LEGACY_RELAY_OVERRIDE = {"relay_pickup_pu": 0.15, "relay_delay_s": 0.5}


def recovered_pct(d, scenario) -> tuple[float, float]:
    """Percent of pre-disturbance power at the 2.0 s deadline, and the minimum reached."""
    t, v, p = d["time"], d["v_sdp_pu"], d["p_grid_w"]
    t0 = float(scenario.dip_start_s)
    t1 = t0 + float(scenario.dip_duration_s)

    pre = p[t < t0 - 0.01]
    p_pre = float(pre.mean()) if pre.size else float(p.max() or 1.0)
    pct = 100.0 * p / (p_pre or 1.0)

    back = np.nonzero((t > t1) & (v >= C.RECOVERY_TRIGGER_V_PU))[0]
    if not back.size:
        return 0.0, float(pct.min())

    deadline = float(t[back[0]]) + C.RECOVERY_DEADLINE_S
    # Average over a short window rather than reading one sample: the AI swing is a
    # periodic +/-20% of IT load, so a single sample at the deadline can land on a peak
    # or a trough. The rule is about sustained recovery.
    win = (t >= deadline - 0.1) & (t <= deadline + 0.1)
    held = float(pct[win].mean()) if win.any() else float(pct[-1])
    dip = (t >= t0) & (t <= t1 + 1.0)
    return held, float(pct[dip].min() if dip.any() else pct.min())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="frontend/public/data/events.json")
    ap.add_argument("--facility-mw", type=float, default=300.0, help="reference campus rating")
    args = ap.parse_args()

    runner.build()
    out = []
    for ev in EVENTS:
        row = {"pu": f"{ev['pu']:.3f}", "tag": ev["tag"]}
        for label, preset in (("legacy", LEGACY_UPS), ("product", GRID_FRIENDLY)):
            extra = LEGACY_RELAY_OVERRIDE if label == "legacy" else {}
            sc = dataclasses.replace(
                preset,
                dip_depth_pu=ev["pu"],
                dip_duration_s=ev["duration_s"],
                faulted_phase_frac=ev["phases"],
                supply_voltage_v=SUPPLY_V,
                **extra,
            )
            runner.run(sc, tag=f"ev_{label}")
            d = runner._read_csv(runner.BUILD / f"ev_{label}_res.csv")
            held, lowest = recovered_pct(d, sc)
            row[label] = round(held, 1)
            row[f"{label}_min"] = round(lowest, 1)
            (runner.BUILD / f"ev_{label}_res.csv").unlink(missing_ok=True)

        shed_mw = args.facility_mw * max(0.0, 100.0 - row["legacy"]) / 100.0
        row["note"] = (
            "Both hold" if row["legacy"] >= 90 and row["product"] >= 90
            else f"Legacy sheds {shed_mw:.0f} MW"
        )
        out.append(row)
        print(
            f"  {row['pu']} pu ({ev['tag']:8s}): legacy {row['legacy']:5.1f}%  "
            f"product {row['product']:5.1f}%   {row['note']}"
        )

    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    print(f"\n-> {p}")
    print("Bars are % of pre-disturbance power at the 2.0 s deadline; 90% is the pass line.")


if __name__ == "__main__":
    main()
