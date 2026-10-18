"""Physics engine. psu_chain returns outage seconds, whether the PSU output rail was lost, and whether a BBU handoff occurred."""
import numpy as np

def psu_chain(start_s, dur_ms, gap_ms, holdup_ms, bbu_ok, ton_s):
    n, k = start_s.shape; out = np.zeros(n); off_until = np.full(n, -1.0); lost = np.zeros(n, bool); handoff = np.zeros(n, bool)
    for j in range(k):
        valid = dur_ms[:, j] > 0
        seen = np.minimum(dur_ms[:, j], gap_ms)
        active = valid & (start_s[:, j] >= off_until)
        loses = active & (seen > holdup_ms) & ~bbu_ok
        handoff |= active & (seen > 0.5 * holdup_ms) & bbu_ok          # 3 V drop at 50% hold-up energy -> BBU supplies
        out += np.where(loses, ton_s, 0.0); lost |= loses
        off_until = np.where(loses, start_s[:, j] + holdup_ms * 1e-3 + ton_s, off_until)
    return out, lost, handoff

def vfd_trip(dur_ms, ride_ms):
    return (dur_ms > ride_ms[:, None]).any(1)

def cooling_downtime(trip, restart_s):
    return np.where(trip, restart_s, 0.0)
