import numpy as np, evidence as e, models as m, psu_fsm as f, converter_cap as cc
t, v = m.nerc_sequence()
tr = e.STS_TRANSFER_MS["60Hz"]
print("kind  age  Cmult  ESRmult | load holdup_ms  dips_ridden(noBBU,noSTS)  outage_s(noBBU)  STS_max_detect_ms")
for kind in ("endurance", "life"):
    for age in (0.0, 0.5, 1.0):
        cm, rm = cc.health(age, kind)
        for load in (0.5, 1.0, 1.5):
            hold = m.holdup_aged(load, cap_frac=cm)          # ESR effect on efficiency not modeled (unquantified)
            ridden = sum(hold >= d for _, d, _ in e.NERC_DIPS)
            ints, _ = f.run(t, v, load, bbu=False, cap_frac=cm)
            print(f"{kind:9} {age:.1f} {cm:.2f} {rm:.2f} | {load:.1f} {hold:6.1f}  {ridden}/6  {ints.sum()*1e-3:6.2f}  {hold-tr:6.1f}")
# BBU path: handoff time (50% energy) must exceed nothing - check no interruption at worst case
ints, log = f.run(t, v, 1.5, bbu=True, cap_frac=cc.health(1.0, "life")[0])
print("worst case (life, age 1, 150% load) with BBU interrupted s:", ints.sum()*1e-3)
# load below which an unaided PSU rides through the longest/shortest dip at age 0
print("max load to ride 42 ms:", 20/42, " 66 ms:", 20/66)
