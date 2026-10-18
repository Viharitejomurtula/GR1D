"""Export simulator runs in the shape the results page expects.

Results.tsx computes everything -- the headline pass rate and its 95% band, the failure
map, the report card -- from one array called SAMPLE. Its own note says:

    To connect the backend, replace SAMPLE with real runs (data/runs.csv) and
    classify() with the run's failure_mode.

This writes that array. Each point is {depth, duration, temp, age, mode}, with duration
in MILLISECONDS because that is what the page's sliders and bands use.

    python3 scripts/export_sample.py                       # from data/runs.csv
    python3 scripts/export_sample.py --in data/postfix.csv

Two notes for whoever wires it up:

  - `mode` carries the grader's real mechanisms ("cooling tripped", "exceeded 125%
    current cap", ...), not the placeholder A/B/C. Those were regions of the input space;
    these are mechanisms, and they are what the report card should group by. MODE_KEYS
    and the mode labels need updating to match.
  - Runs the solver could not solve are dropped rather than scored. Including them is how
    collapsed-root solutions previously counted as passes.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent

# Modes that mean "this run has no verdict", not "this run failed".
INVALID = {"voltage collapse", "invalid: collapsed-root solution"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/runs.csv")
    ap.add_argument("--out", default="frontend/public/data/sample.json")
    ap.add_argument("--limit", type=int, default=0, help="cap the number of points, 0 = all")
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    if not src.exists():
        raise SystemExit(f"{src} not found — run sim.batch.run_batch() first")

    rows = list(csv.DictReader(src.open()))
    points, dropped = [], 0
    for r in rows:
        mode = r["failure_mode"]
        if mode in INVALID:
            dropped += 1
            continue
        points.append({
            "depth": round(float(r["dip_depth_pu"]), 4),
            "duration": round(float(r["dip_duration_s"]) * 1000, 1),  # page works in ms
            "temp": round(float(r["outdoor_temp_c"]), 2),
            "age": round(float(r["battery_age_yr"]), 2),
            "mode": "pass" if int(float(r["passed"])) == 1 else mode,
        })

    if args.limit and len(points) > args.limit:
        step = len(points) / args.limit
        points = [points[int(i * step)] for i in range(args.limit)]

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(points))

    counts = Counter(p["mode"] for p in points)
    n = len(points)
    print(f"{n:,} points -> {out}  ({out.stat().st_size / 1024:.0f} KB)")
    if dropped:
        print(f"{dropped:,} runs dropped as unsolved (no verdict, not a failure)")
    print(f"pass rate {counts['pass'] / n:.1%}")
    print("\nmodes present (MODE_KEYS in Results.tsx needs these, not A/B/C):")
    for mode, count in counts.most_common():
        print(f"  {mode:34s} {count:5d}  {count / n:5.1%}")


if __name__ == "__main__":
    main()
