"""Reclose sequences from documented incidents, as Scenario.extra_dips. Gaps are measured from the previous dip's clearing.
Sources: NERC Incident Review (Large Load Loss, 2024-07-10) Table 1; PJM Dominion timeline 2026-07-22 and LCL deck 2026-09-15.
Fields marked ASSUMED are not in the sources."""
from dataclasses import replace
from . import scenario as S

def _gaps(starts, durs):
    """(gap_after_previous_clear, duration) pairs from absolute starts and durations."""
    out, prev_clear = [], None
    for st, du in zip(starts, durs):
        out.append((0.0 if prev_clear is None else st - prev_clear, du)); prev_clear = st + du
    return out

# NERC 2024-07-10 Table 1: faults at 19:00:23.351, 23.883, 39.211, 44.630, 1:39.600, 1:45.016; 42/66/58/50/66/59 ms. Residual 0.25-0.40 pu.
NERC_2024_START = [23.351, 23.883, 39.211, 44.630, 99.600, 105.016]
NERC_2024_DUR = [0.042, 0.066, 0.058, 0.050, 0.066, 0.059]
# PJM 2026-07-22: instant reclose+retrip 07:56:09, :25, :30, 07:57:25, :30; 2-3 cycles each. Instant-reclose gap (0.5 s) and residual ASSUMED.
PJM_2026_START = [0.0, 0.5, 16.0, 21.0, 76.0, 81.0]
PJM_2026_DUR = [0.042] * 6

def sequence(starts, durs, depth, base, dip_start_s=1.0):
    g = _gaps(starts, durs)
    first_dur = g[0][1]
    return replace(base, dip_start_s=dip_start_s, dip_duration_s=first_dur, dip_depth_pu=depth, second_dip=False,
                   extra_dips=tuple((gap, dur, depth) for gap, dur in g[1:]))

def nerc_2024(base, depth=0.325): return sequence(NERC_2024_START, NERC_2024_DUR, depth, base)
def pjm_2026(base, depth=0.5): return sequence(PJM_2026_START, PJM_2026_DUR, depth, base)
