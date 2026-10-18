# Factor coverage (public-data models; none site-calibrated)
Tags: SPEC published spec | DATA public measurement | EX public example | PHYS physics model | ASSUME explicit assumption
| # | Factor | Module | Tag |
|---|---|---|---|
| 1-3 | dip shape / count / gaps | models.py, evidence.py (NERC Table 1) | EX (+ASSUME shapes) |
| 4 | phase jump | remaining.phase_jump_deg | PHYS/ASSUME |
| 5 | post-dip overvoltage | remaining.overvoltage_traj (peak scaled to NERC 1.07) | PHYS/EX |
| 6 | AI crash/restart | remaining.ai_power_traj | ASSUME |
| 7 | SOC at dip | remaining.soc_samples | PHYS/ASSUME |
| 8 | units offline | remaining.maintenance_states | ASSUME |
| 9 | equipment age | nasa_cap_aging.py (NASA EOS, 194 h stress) | DATA |
| 10-12,15 | converter | converter_cap.py (LM5176) | SPEC/PHYS |
| 13-14 | bypass | switch_relay.py (Vertiv) | SPEC |
| 16 | SOC-estimation error | remaining.soc_error_samples (NASA battery fade) | DATA (capacity-fade error only) |
| 17-18 | ultracap | converter_cap.py (Maxwell BCAP3000) | SPEC |
| 19-22 | PSU | psu_fsm.py, models.holdup | SPEC |
| 23 | rack buffer | remaining.rack_usable_energy_kwh (BBU unverified) | ASSUME |
| 24 | board UV trip | remaining.board_uv_trip | ASSUME |
| 25-26 | compressor | remaining.coresense_lockout, restart_time_s | SPEC (17 VAC/2 s, from brief) + CONFIG |
| 27-28 | VFD / pump | remaining.vfd_ridethrough_ms, pump_trip_boundary | PHYS |
| 29-30 | transformer | remaining.transformer_z_pu, inrush_peak_pu | ASSUME/PHYS |
| 31 | relay | switch_relay.py (SEL-751A) | SPEC |
| 32 | breaker timing | remaining.breaker_close_time_ms (60 ms nominal from ETH paper) | ASSUME (dataset not retrieved) |
