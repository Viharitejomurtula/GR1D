"""Ablation: validation outcomes with each structural fix switched off, to see what each one changes.
Variants: OLD (chain loading 1.0, per-unit PSU scaling) / +chain loading / +PSU datasheet / BOTH (current). Usage: OM_IMAGE=... python3 -m validation.ablate"""
import json, sys
from dataclasses import replace
from sim import runner
from validation.cases import CASES

VARIANTS = {"old": dict(chain_loading_frac=1.0, psu_cap_datasheet=False), "chain_only": dict(chain_loading_frac=0.75, psu_cap_datasheet=False),
            "psu_only": dict(chain_loading_frac=1.0, psu_cap_datasheet=True), "both": dict(chain_loading_frac=0.75, psu_cap_datasheet=True)}
out = {}
for v, kw in VARIANTS.items():
    out[v] = {}
    for name, c in CASES.items():
        g = runner.run(replace(c["sc"], **kw), tag=f"abl_{v}_{name}")
        out[v][name] = dict(loss=round(1 - g.final_power_frac, 3), peak_i=round(g.peak_current_pu, 3), mode=g.failure_mode, numerics_ok=g.numerics_ok)
    print(v, {k: (x["loss"], x["peak_i"]) for k, x in out[v].items()}, flush=True)
if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(out, indent=1))
