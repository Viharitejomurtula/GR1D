"""Documented validation cases (Parameter_Table.md section 9). Reconstructed because the original ad-hoc runs were never committed.
Each case: scenario overrides on top of the named preset, plus the real-world targets. Inputs only; targets are never fed to the model."""
from dataclasses import replace
from sim import scenario as S

def _legacy(**kw): return replace(S.LEGACY_UPS, **kw)

# dip_depth_pu below is the SOURCE depth. The published numbers (0.535 / 0.670 / 0.844) are retained voltage OBSERVED at the facility; with the exact
# network model the two differ, so each was converted by bisection on the model's own min v_sdp during the dip (validation/crosscheck/calibrate_cases.py).
# Facility A's legacy share was re-fitted (0.46 -> 0.50) after the network change; its loss is a FIT (slope ~1), only peak current is an unfitted check.
CASES = {
    # facility, 0.535 pu retained, 2 of 3 phases <0.7 pu for >20 ms, ~50 ms dip; PSU sees 148 V at 277 V supply
    "facility_A": dict(sc=_legacy(dip_depth_pu=0.671, dip_duration_s=0.05, faulted_phase_frac=2/3, legacy_load_frac=0.50, supply_voltage_v=277.0),
                       target=dict(loss_frac=0.46, peak_current_pu=1.60, recovers=False)),
    # 0.670 pu, 1 of 3 phases, 208 V supply
    "facility_B": dict(sc=_legacy(dip_depth_pu=0.749, dip_duration_s=0.05, faulted_phase_frac=1/3, legacy_load_frac=0.30, supply_voltage_v=208.0),
                       target=dict(loss_frac=0.24, peak_current_pu=1.50, recovers=True)),
    # out-of-sample: legacy share inherited from B, nothing refitted
    "shallow_0p844": dict(sc=_legacy(dip_depth_pu=0.875, dip_duration_s=0.05, faulted_phase_frac=1/3, legacy_load_frac=0.30, supply_voltage_v=208.0),
                          target=dict(loss_frac=0.19)),
}
