"""Sensitivity, not a fit: peak current of the two ERCOT facilities versus the two timing parameters that decide it.
Debounce (PSU AC-loss validation): 4-5 ms sourced (AE ORv3 HPR datasheet); wider values shown for the sweep only.
Breaker opening: 3-5 cycles = 50-83 ms (typical ratings); 33 ms shown for the sweep only. Peak current is normalised to the facility's own pre-event
maximum (NOGRR 282 2.14(2)(d)); the real events were 1.60 (A) and 1.50 (B)."""
from dataclasses import replace
from sim import runner
from validation.cases import CASES
print("debounce_ms  breaker_ms |  A: peak  over0.5s?   B: peak  over0.5s?")
for deb in (4.0, 4.5, 5.0, 8.0, 16.7, 25.0):
    for brk in (33.0, 50.0, 83.0):
        row = []
        for n in ("facility_A", "facility_B"):
            g = runner.run(replace(CASES[n]["sc"], psu_uv_delay_s=deb / 1000.0, legacy_open_delay_s=brk / 1000.0), tag=f"dly_{n}")
            row += [round(g.peak_current_pu, 3), "yes" if g.overcurrent_s > 0.5 else "no"]
        print(f"{deb:10}  {brk:9} | {row[0]:8} {row[1]:>9}   {row[2]:7} {row[3]:>9}", flush=True)
