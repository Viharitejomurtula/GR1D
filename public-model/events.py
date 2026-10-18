"""Public library of real reclose-sequence disturbances behind customer-initiated load reductions (CILR).
Sources in raw/events/: NERC 2024 review (Table 1), PJM 2026-09-15 LCL deck (events #1-#3), PJM 2026-08-06 Dominion deck (timeline), NERC Reliability Insights 2026-09.
Fields marked ASSUMED are not in the sources."""
import numpy as np
N24 = [(23.351, 42), (23.883, 66), (39.211, 58), (44.630, 50), (99.600, 66), (105.016, 59)]
EVENTS = {
  "2024-07-10": dict(t=[x[0] - N24[0][0] for x in N24], dur_ms=[(d, d) for _, d in N24], residual=(0.25, 0.40), load_mw=1500, peak_v=1.07, peak_hz=60.047,
                     source="NERC Table 1 (all six dips measured)"),
  "2025-02-17": dict(t=[0, 0.5, 16.0, 21.0], dur_ms=[(33, 98)] * 4, residual=(0.25, 0.60), load_mw=1800, peak_v=1.05, peak_hz=60.042,
                     source="PJM deck: 4 sags, SLG fault, 5.9-cycle (98 ms) clearing on one terminal; sag times/depths ASSUMED (copied from 2024 reclose pattern); durations 33-98 ms ASSUMED range"),
  "2026-07-22": dict(t=[0, 0.5, 16.0, 21.0, 76.0, 81.0], dur_ms=[(33, 50)] * 6, residual=(0.25, 0.60), load_mw=3869, peak_v=1.138, peak_hz=60.092,
                     source="PJM Dominion timeline 07:56:09 (instant reclose+retrip), :25, :30, 07:57:25, :30; faults cleared in 2-3 cycles (33-50 ms); instant-reclose gap 0.5 s and residual voltage ASSUMED"),
}
# Ride-through case: AionTracks controlled sag test (ERCOT LLWG deck 2026-08-21, VENDOR claim, lab/software test on a modeled 9 MW facility, NOT a grid event).
# 70 sags run; "7 sags in 64 s met" six-sags-in-90-s rule; sag to 51% retained voltage for 0.5 s; load never disconnected; 90% power back in median 0.41 s.
RIDE_THROUGH = {"aiontracks-test": dict(t=[0, 10.7, 21.3, 32.0, 42.7, 53.3, 64.0], dur_ms=[(500, 500)] * 7, residual=(0.51, 0.51), outcome="rode through (software-controlled)",
                source="ERCOT LLWG deck 2026-08-21 (vendor); hardware chain NOT tested")}
EVENTS_LOSS_ONLY = list(EVENTS)   # 2024/2025/2026 events are public BECAUSE load was lost -> selected on outcome
EVENTS_ALL = {**EVENTS, **RIDE_THROUGH}
# Outcome records (load actually lost, system-level) -- usable later for validation / calibration of the ride-through logic.
OUTCOMES = {"2024-07-10": 1500, "2025-02-17": 1800, "2026-07-22": 3869, "2026-04-18": 500}
ERCOT = dict(n_events=26, load_loss_frac_range=(0.17, 0.95), min_sag_for_loss_pu=0.844, source="NERC crypto review via PJM/ERCOT decks (secondary)")
def library_keys(): return list(EVENTS_ALL)
