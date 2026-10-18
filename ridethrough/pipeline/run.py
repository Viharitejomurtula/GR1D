"""End to end: joint sample -> surrogate -> performance distribution and failure-driver rankings.

Usage
    python -m ridethrough.pipeline.run [--n 100000] [--seed 0] [--design grid_friendly|legacy_ups]
        [--events 2000] [--perms 12] [--out reports/pipeline] [--check check.json]

What it produces (in --out)
    pipeline_<design>.json   everything below, machine-readable
    pipeline_<design>.md     the same, written for a person

Contents
    performance   distribution of outcomes for one grid event hitting one site (see performance.py)
    rankings      group A (conditions) and group B (site state): Shapley importance per output, interactions
    lifts         outcome by level of each driver, from the joint sample
    change_points where each numeric driver moves the outcome most
    caveats       computed warnings (saturation, out-of-training share) plus the standing ones

Headline output. Ranking on P(fail) is uninformative when almost every event fails (or none does): a driver
cannot move a probability that is already 0 or 1. If the overall failure rate is outside [0.05, 0.95] the
headline switches to floor_violation_s, seconds spent below the grid power floor, and the report says so.
Both are always present.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np

from ridethrough.pipeline import drivers, joint, performance
from sim.scenario import GRID_FRIENDLY, LEGACY_UPS
from surrogate.predict import Surrogate

DESIGNS = {"grid_friendly": GRID_FRIENDLY, "legacy_ups": LEGACY_UPS}
SATURATION = (0.05, 0.95)
FLAT = 0.10   # a driver whose best and worst levels differ by less than this share of the mean outcome has no 'worst level'
STANDING_CAVEATS = [
    "Verdicts come from the neural surrogate, not the simulator; see 'surrogate_check' for how well it agrees on these events.",
    "The simulator is cross-checked with known gaps, not validated (validation/SCOPE.md).",
    "Design and settings are held at the chosen preset; this describes that product, not the range of possible designs.",
    "Network inputs marked assumed or placeholder (uniform season, workload type, grid strength, breaker misoperation rates) are not varied here.",
    "Driver blocks are swapped as wholes: dependence between blocks (e.g. site load and temperature) is not preserved in the Shapley step.",
    "Site load level is mapped onto the simulator's 'workload' by a rescale (joint.py); they are different quantities.",
]


def run(n: int, seed: int, design: str, events: int, perms: int, check: dict | None = None) -> dict:
    t0 = time.time()
    sc, roots = joint.sample_joint(n, seed, DESIGNS[design])
    ev = performance.Evaluator(Surrogate.load("surrogate/models/v1"))
    perf, y = performance.performance(ev, sc, seed)
    names = ev.names
    fail = perf["fail_probability"]["mean"]
    saturated = not (SATURATION[0] <= fail <= SATURATION[1])
    headline = "floor_violation_s" if saturated else "p_fail"

    f = ev
    rankings = {g: drivers.rank_group(f, names, sc, g, events, perms, seed + 10 + i) for i, g in enumerate(("A", "B"))}
    split = drivers.group_split(f, names, sc, events, perms, seed + 20)
    caveats = list(STANDING_CAVEATS)
    if saturated:
        caveats.insert(0, f"Failure rate is {fail:.1%}: P(fail) cannot be ranked meaningfully, so the headline ranking uses {headline}.")
    if perf["share_inputs_outside_training"] > 0.05:
        caveats.insert(0, f"{perf['share_inputs_outside_training']:.0%} of events have an input outside the surrogate's training range.")
    return {
        "design": design, "n_events": n, "seed": seed, "unit": "one grid event hitting one site",
        "headline_output": headline, "saturated": saturated, "outputs": names,
        "performance": perf, "rankings": rankings, "group_split": split,
        "lifts": drivers.lift_tables(roots, y, names), "change_points": drivers.change_points(roots, y, names),
        "surrogate_check": check, "caveats": caveats,
        "settings": {"shapley_events": events, "shapley_walks": 2 * perms}, "runtime_s": round(time.time() - t0, 1),
    }


def _worst_level(lifts: dict, block: str, output: str) -> str:
    key = "p_fail" if output == "p_fail" else f"mean_{output}"
    levels = lifts[block]["levels"]
    if not levels or key not in levels[0]:
        return ""
    vals = [lv[key] for lv in levels]
    mean = sum(lv["share_of_events"] * lv[key] for lv in levels)
    if mean == 0 or (max(vals) - min(vals)) / abs(mean) < FLAT:     # levels barely differ: "worst" would be noise
        return "no clear difference"
    w = max(levels, key=lambda lv: lv[key])
    return f"{w['level']} ({w[key]:.3g})"


def _fmt_rank(rows: list[dict], lifts: dict, output: str, top: int = 8) -> list[str]:
    out = ["| # | driver | importance | share | worst level (mean outcome) | rank 90% range |", "|---|---|---|---|---|---|"]
    for r in rows[:top]:
        out.append(f"| {r['rank']} | {r['label']} | {r['importance']:.4f} | {r['share']:.0%} | {_worst_level(lifts, r['block'], output)} | "
                   f"{r['rank_90ci'][0]}-{r['rank_90ci'][1]}{'' if r['rank_resolved'] else ' (unresolved)'} |")
    return out


def to_markdown(r: dict) -> str:
    p = r["performance"]
    fp = p["fail_probability"]
    L = [f"# Product performance and failure drivers: {r['design']}", "",
         f"Unit: {r['unit']}. {r['n_events']:,} events, seed {r['seed']}.", "",
         "## Performance", "",
         f"- Probability an event fails: **{fp['mean']:.1%}** (Monte Carlo 95% interval {fp['mc_95ci'][0]:.1%} to {fp['mc_95ci'][1]:.1%}).",
         f"- By ensemble member: {', '.join(f'{v:.1%}' for v in fp['by_ensemble_member'])} (surrogate disagreement).",
         f"- Events that almost surely fail (P>0.9): {fp['share_events_fail_prob_above_0.9']:.1%}; almost surely pass (P<0.1): {fp['share_events_fail_prob_below_0.1']:.1%}.",
         "", "How events fail (share of all events):", ""]
    for m, v in sorted(p["failure_mode_share"].items(), key=lambda kv: -kv[1]):
        L.append(f"- {m}: {v:.1%}")
    L += ["", "| measure | 5% | 25% | median | 75% | 95% |", "|---|---|---|---|---|---|"]
    for t, c in p["continuous"].items():
        q = c["quantiles"]
        L.append(f"| {t} | " + " | ".join(f"{q[k]:.3g}" for k in ("0.05", "0.25", "0.5", "0.75", "0.95")) + " |")
    h = r["headline_output"]
    for g, title in (("A", "Group A: conditions (what the grid and weather do)"), ("B", "Group B: site state (what the equipment is like)")):
        L += ["", f"## {title}", "", f"Ranked on **{h}**" + (" (P(fail) is saturated)" if r["saturated"] else "") + ":", ""]
        L += _fmt_rank(r["rankings"][g]["by_output"][h], r["lifts"], h)
        if h != "p_fail":
            L += ["", "Ranked on P(fail):", ""] + _fmt_rank(r["rankings"][g]["by_output"]["p_fail"], r["lifts"], "p_fail")
        inter = r["rankings"][g]["interactions"][h][:3]
        L += ["", "Strongest pairwise interactions: " + "; ".join(f"{a}+{b} ({i['importance']:.4f})" for i in inter for a, b in [i["blocks"]]) + "."]
    L += ["", "## Conditions versus site state", ""]
    for s in r["group_split"]:
        if s["output"] in (h, "p_fail"):
            L.append(f"- {s['output']}: conditions {s['A_share']:.0%}, site state {1 - s['A_share']:.0%}")
    if r.get("surrogate_check"):
        c = r["surrogate_check"]["all"]
        L += ["", "## Surrogate check against the simulator", "",
              f"{r['surrogate_check']['usable']} events: verdict accuracy {c['verdict_accuracy']:.1%}, simulator failure rate "
              f"{c['sim_fail_rate']:.1%} vs surrogate {c['surrogate_fail_rate']:.1%}."]
    L += ["", "## Caveats", ""] + [f"- {c}" for c in r["caveats"]]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--design", choices=list(DESIGNS), default="grid_friendly")
    ap.add_argument("--events", type=int, default=2000)
    ap.add_argument("--perms", type=int, default=12)
    ap.add_argument("--out", default="reports/pipeline")
    ap.add_argument("--check", default=None, help="JSON written by ridethrough.pipeline.check, embedded in the report")
    a = ap.parse_args()
    check = json.loads(pathlib.Path(a.check).read_text()) if a.check else None
    res = run(a.n, a.seed, a.design, a.events, a.perms, check)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"pipeline_{a.design}.json").write_text(json.dumps(res, indent=1))
    (out / f"pipeline_{a.design}.md").write_text(to_markdown(res))
    print(to_markdown(res))


if __name__ == "__main__":
    main()
