"""Deterministic pass/fail map at fixed provisioning levels (PSU loading is a knob). Uses only published limits (AE ORv3 datasheets, NERC durations)."""
def allowed_s(x):   # ORv3 PSU-class overload limits; applying to the BBU converter is an ASSUMPTION
    return float("inf") if x <= 1.0 else 10.0 if x <= 1.15 else 0.1 if x <= 1.55 else 0.01
print("A) PSU rides the NERC dips WITHOUT the battery? (hold-up = 20 ms / load; dips 42-66 ms)  [spec-derived, load<100% is an extrapolation]")
for ld in (0.3, 0.6, 0.8, 1.0):
    h = 20 / ld; print(f"   load {ld:.0%}: hold-up {h:5.1f} ms -> rides 42 ms: {'PASS' if h>=42 else 'fail'} | rides 66 ms: {'PASS' if h>=66 else 'fail'}")
print("\nB) After a battery handoff, does the converter survive the restart surge?  (x = load*surge; PASS if surge duration <= allowed time)")
print("   load  surge   x     allowed     ramp 0.2s  0.5s   2s    5s")
for ld in (0.3, 0.6, 0.8):
    for sp in (1.0, 1.25, 1.5, 2.0):
        x = ld * sp; a = allowed_s(x); print(f"   {ld:.0%}   {sp:4.2f}  {x:4.2f}  {('inf' if a==float('inf') else f'{a:g} s'):>8}   " + "   ".join('PASS' if t <= a else 'fail' for t in (0.2, 0.5, 2, 5)))
