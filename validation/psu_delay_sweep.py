"""Diagnostic (not a fit): how long must PSUs keep drawing before locking out for the model to show the sustained facility
overcurrent seen in the ERCOT events (A: 1.60, B: 1.50 pu)? Reports the dependence; picks nothing."""
from dataclasses import replace
from sim import runner
from validation.cases import CASES
print("delay_ms   A: peak_i  loss    B: peak_i  loss")
for ms in (0, 1, 4, 8, 16, 25):
    row = []
    for n in ("facility_A", "facility_B"):
        g = runner.run(replace(CASES[n]["sc"], psu_uv_delay_s=ms / 1000.0), tag=f"dly_{n}"); row += [round(g.peak_current_pu, 3), round(1 - g.final_power_frac, 3)]
    print(f"{ms:7}   {row[0]:8} {row[1]:6}   {row[2]:8} {row[3]:6}", flush=True)
