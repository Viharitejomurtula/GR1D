"""Relay (SEL-751A UV) and STS bypass checks against the NERC six-dip sequence.
Assumptions (labelled): relay/STS see the same RMS envelope; alternate STS source is healthy (dual-bus UPS);
detection delay for the STS is swept because no public Eaton/Vertiv detection-delay figure was extracted."""
import numpy as np
import evidence as e, models as m

F = 60.0; CYC_MS = 1000 / F
V_NOM = 230.0

def relay_pickup_window(setting_v):
    h = e.RELAY_UV_ACC[0].value / 100 * setting_v + e.RELAY_UV_ACC[1].value
    return setting_v - h, setting_v + h

def relay_check(setting_pu_list=(0.5, 0.7, 0.8, 0.9)):
    """UV element picks up if v <= threshold within accuracy band; time < 1.5 cycles (spec max)."""
    rows = []
    for sp in setting_pu_list:
        lo, hi = relay_pickup_window(sp * V_NOM)
        for ts, d, _ in e.NERC_DIPS:
            v_dip = 0.325 * V_NOM
            picked = v_dip <= lo          # picks up for any threshold in the band
            tmax = e.RELAY_TIME_CYCLES.value * CYC_MS
            rows.append((sp, ts, d, picked, d >= tmax))   # last: dip long enough to complete pickup at worst case
    return rows

def sts_ridethrough(detect_ms, transfer_ms, holdup_ms, dips=e.NERC_DIPS):
    """Load sees an interruption of detect+transfer after each dip starts (if dip lasts long enough to be detected).
    Ride-through if that gap <= PSU hold-up. Dip shorter than detect time -> no transfer, PSU hold-up only vs dip."""
    out = []
    for ts, d, _ in dips:
        if d <= detect_ms: gap = d             # dip over before STS acts; PSU sees the dip itself
        else: gap = detect_ms + transfer_ms
        out.append((ts, d, gap, gap <= holdup_ms))
    return out

if __name__ == "__main__":
    print("== Relay (SEL-751A UV): pickup band & coverage ==")
    for sp in (0.5, 0.7, 0.8, 0.9):
        lo, hi = relay_pickup_window(sp * V_NOM)
        rows = [r for r in relay_check((sp,))]
        print(f"setting {sp} pu ({sp*V_NOM:.1f} V): band {lo:.2f}-{hi:.2f} V, picked all dips: {all(r[3] for r in rows)}, "
              f"dips >= worst-case pickup time ({e.RELAY_TIME_CYCLES.value*CYC_MS:.1f} ms): {sum(r[4] for r in rows)}/6")
    print("\n== STS bypass vs PSU hold-up (gap = detect + transfer) ==")
    for tr_name, tr in e.STS_TRANSFER_MS.items():
        for load in (0.5, 1.0, 1.5):
            hold = 20 / load
            need = hold - tr
            print(f"{tr_name} transfer {tr:.2f} ms, load {load}: hold-up {hold:.1f} ms -> max detection delay that rides through = {need:.1f} ms")
    print("\nper-dip, detect=2 ms, 60Hz transfer, load 1.0:")
    for r in sts_ridethrough(2.0, e.STS_TRANSFER_MS['60Hz'], 20.0): print(r)
    print("\nper-dip, detect=8.3 ms (half cycle), load 1.0:")
    for r in sts_ridethrough(8.33, e.STS_TRANSFER_MS['60Hz'], 20.0): print(r)
    print("\ndetect=1.5 cycles (25 ms, worst relay-class), load 1.0:")
    print(all(r[3] for r in sts_ridethrough(25, e.STS_TRANSFER_MS['60Hz'], 20.0)))
