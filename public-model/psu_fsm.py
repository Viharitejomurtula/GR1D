"""ORv3 3kW PSU protection state machine (AC-side dips only), driven by an AC RMS envelope in pu.
Timers/thresholds come from evidence.py (Advanced Energy datasheet). Energy model: hold-up energy
drains at rate load/20ms (t_hold = 20ms/load); 3 V drop (BBU handoff) when 50% of hold-up energy is gone."""
import numpy as np
from evidence import PSU_UVLO_AC, PSU_RETRY_S, PSU_HOLDUP_100_MS
V_NOM_AC = 230.0
T_ON_NO_BBU = (1.0, 4.5)   # s, TON_noBBU min/max from datasheet

def run(t, v_pu, load=1.0, bbu=True, ton=T_ON_NO_BBU[1], cap_frac=1.0, tau_recharge_s=0.2):
    """tau_recharge_s: hold-up capacitor recharge time constant after AC returns (ASSUMED 0.2 s; previous version recharged instantly)."""
    dt = t[1] - t[0]
    e_full = 1.0 * cap_frac                        # normalized hold-up energy
    drain = load / (PSU_HOLDUP_100_MS.value * 1e-3)  # per s
    state, e, t_ev, out = "NORMAL", e_full, 0.0, []
    interrupted, log = np.zeros(len(t), bool), []
    prev = state
    for i, v in enumerate(v_pu):
        ac_ok = v * V_NOM_AC >= PSU_UVLO_AC.value
        if state == "NORMAL":
            if not ac_ok: state = "HOLDUP"           # starts from whatever energy has been recovered
        elif state == "HOLDUP":
            if ac_ok: state = "NORMAL"
            else:
                e -= drain * dt
                if e <= 0.5 * e_full and bbu: state = "BBU"       # 3 V drop, BBU takes load
                elif e <= 0: state = "OFF"; t_ev = t[i]
        elif state == "BBU":
            if ac_ok: state = "NORMAL"
        elif state == "OFF":
            interrupted[i] = True
            if ac_ok and t[i] - t_ev >= ton: state = "NORMAL"; e = e_full
        if state in ("NORMAL", "BBU") and ac_ok and e < e_full: e += (e_full - e) * dt / tau_recharge_s
        if state == "OFF": interrupted[i] = True
        if state != prev: log.append((round(t[i], 4), prev, state)); prev = state
    return interrupted, log

if __name__ == "__main__":
    import models as m
    t, v = m.nerc_sequence()
    print("load  bbu  interrupted_s  first_loss_t  transitions")
    for bbu in (True, False):
        for load in (0.5, 1.0, 1.2, 1.5):
            ints, log = run(t, v, load, bbu)
            n = int(ints.sum()); ft = t[ints.argmax()] if n else None
            print(f"{load:4.1f} {str(bbu):5} {n*1e-3:8.3f} {ft} {len(log)}")
    # hold-up vs shortest/longest dip: which loads ride through without BBU?
    for load in (0.5, 0.6, 0.8, 1.0):
        print(load, "holdup ms", 20/load, "rides 42ms dip:", 20/load >= 42, "66ms:", 20/load >= 66)
