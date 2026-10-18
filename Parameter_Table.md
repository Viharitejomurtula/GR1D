# Data Center Ride-Through Simulator: Parameter Table

Setup: OpenModelica model of one representative Texas AI data center, rack-level
architecture (Open Rack V3: rack PSUs + rack battery backup units on a 48 V busbar).
Averaged (RMS) model, ~0.1 ms steps, **~15 s window per scenario** (raised from 6-8 s;
see the PSU restart note in §3). Graded at the Service Delivery Point against
ERCOT NOGRR 282, effective Aug 1, 2026.

**Status tags:** ✅ checked against the primary source · ☑️ confirmed in team CSV, not
re-checked · ⚠️ partial / secondary · Dv derived · G guess (no source; resolve by
sensitivity analysis, not research)

**Revision history**
- v1 — Vihari, original table
- v2 — ERCOT NOGRR 282 primary source (SPWG Feb 2026) + ORv3 power-system spec
- v3 — Vihari's fact-checked parameter pass (Sandia battery, NERC motor + AI load,
  Eaton/Schneider transformers, AionTracks product data, NERC incident reviews)

---

## 0. Facility scale

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| lel_threshold_mw | 75 | - | ✅ | NPRR 1308 | Large Load = ≥75 MW at one site; LEL = ≥50% computational |
| facility_it_mw | 120 | 75-500 | ✅ | NERC crypto review | Anchored on real graded facilities: A = 112.3 MW, B = 157.0 MW |
| rack_power_kw | 18-180 | - | ✅ | ORv3 | One 18 kW shelf, up to 10 shelves per rack |

ERCOT's large-load queue is ~410 GW, ~87% data centers, <6 GW energized (RTO Insider, Mar 2026).

## 1. Grid event

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| dip_depth_pu | sampled | 0.70-0.90: **69%** · 0.10-0.70: **27%** · 0-0.10: **4%** | ✅ | [EPRI DPQS 1993-95 via Eaton](https://www.eaton.com/content/dam/eaton/products/backup-power-ups-surge-it-power-distribution/power-conditioners/sag-ride-through/voltage-sag-white-paper.PDF) | Rescaled from 66/26/4% (excludes 4% "other events"). Distribution-level, 30 yrs old |
| dip_duration_s | lognormal median 0.1, σ≈1.0 | truncated 0.02-1.0 | Dv | Eaton + GE Vernova clearing times | most sags < 0.5 s |
| fault_clear_s | 0.083 | 0.067-0.10 | ☑️ | GE Vernova | 4 cycles (500 kV), 5 (230 kV), 6 (138 kV) |
| fault_clear_breaker_fail_s | 0.20 | 0.15-0.25 | ☑️ | GE Vernova | 9-15 cycles |
| second_dip | false | true ~20% | ☑️ | Khan et al. 2019 | >80% of faults are temporary → reclose |
| reclose_gap_s | 0.4 | 0.25-0.6 high-speed; 1-5 delayed | ☑️ | NERC SPCS | dead time before reclose |
| dip_shape | from ANDES | - | - | ANDES | **Balanced faults only — see limitation below.** Adoption still an open decision |

**Real Texas dips (validation inputs, not sampled):** 0.535 pu, 0.670 pu, 0.844 pu at ERCOT
facilities. ✅ [NERC Incident Review: Voltage-Sensitive Crypto Load Reductions, Jan 9 2026, p.5](https://www.nerc.com/globalassets/our-work/reports/event-reports/incident_review_considering_voltage-sensitive_crypto_load_reductions.pdf)

> **Limitation now documented with evidence:** the real ERCOT dips were **unbalanced** —
> 1-2 phases below 0.7 pu for >20 ms. ANDES models balanced faults only, so our dip inputs
> are structurally different from the events we validate against. State this in the pitch.

## 2. Transformer / feeder

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| z_pdu_pct | 4 | **3-8 by size** (±7.5% tol) | ✅ | Schneider FAQ citing NEMA *(URL still to add)* | For 15-750 kVA units |
| z_distribution_pct | 5.75 | **5.3-6.2** (incl. ±7.5%) | ✅ | [Eaton pad-mount guide p.17.0-2, IEEE C57.12.34](https://eaton.com/content/dam/eaton/products/design-guides---consultant-audience/canada/cag/eaton-pad-mounted-transformers-consulting-application-guide-tb01909001e-tab-17-ca08104001e-ca.pdf) | 1.5-3.75 MVA |
| z_substation_pct | 10 | 8-12 | ⚠️ | no primary source | 40-100+ MVA. Alternative: use the ANDES case transformer |
| x_over_r | 10 | 5-20 | G | - | not researched |

> **Conflict to resolve:** the NEMA/Schneider figures cover **15-750 kVA** PDU transformers,
> while a hyperscale floor PDU is typically **500-2,250 kVA** (Giga Energy). Different
> equipment classes. Pick the class that matches `facility_it_mw` before fixing %Z.

## 3. Rack hardware (PSU, BBU, transfer, protection)

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| supply_voltage_v | **277** | 208 / 240 / 277 | ✅ | ORv3 power system | Shelf takes 200-277 Vac 3ph 4-wire or 346-480 Vac 3ph 5-wire. US 480Y/277 → **277 V** at the PSU |
| psu_uv_shutoff_v | 172 | restart at 178 | ☑️ | Advanced Energy PSU | = 83% of 208 V, 72% of 240 V, **62% of 277 V** |
| psu_holdup_ms | 20 | 13.3 at 150% load | ☑️ | Advanced Energy PSU | at 200-277 Vac, 100% load |
| psu_holdup_energy_j | 60 | - | ✅ | ORv3 power system | Output droops 3 V at 50% (30 J) depletion; 24 J reserved for pulse. **Model as an energy reservoir** |
| psus_per_shelf | 6 | - | ✅ | ORv3 power system | 6 × 3 kW = 18 kW shelf, 50 V / 300 A |
| shelves_per_rack | 6 | 1-10 | ✅ | ORv3 power system | parallel operation |
| psu_efficiency | 0.965 | 0.94-0.975 | ✅ | ORv3 power system | 97.5% peak; ≥96.5% @ 230-277 V, 30-100% load; 94% @ 10-30% |
| psu_overload | >3.6 kW for 100 ms → BBU; retry every 5 s | - | ☑️ | Advanced Energy PSU | 6 ms allowed for BBU handoff before shutdown |
| psu_ton_nobbu_s | 1.0-5.0 | max 6.5-8.0 | ✅ | ORv3 power system | turn-on, no BBU discharge |
| psu_ton_bbu_s | **1.0-8.5** | max **10-11.5** | ✅ | ORv3 power system | turn-on **after BBU discharge** |
| psu_restart_delay_s | sampled | 0-5.5 (0-2.0 without BBU) | ✅ | ORv3 power system | Deliberate randomized delay, prevents synchronized inrush |
| bbu_module | 3 kW, 4 min | 6/shelf (5+1) | ☑️ | Analog Devices Pt 1 | |
| bbu_cells | 18650, 11S6P, ≥1.5 Ah | pack 30-44 V | ☑️ | Analog Devices Pt 1 | |
| bbu_takeover | busbar <48.5 V for >2 ms → takeover within 2 ms; never <46 V | - | ☑️ | Analog Devices Pt 1 | |
| bbu_handback_s | 0.2 | 0.2-0.5 | ☑️ | Analog Devices Pt 1 | busbar >48.5 V for 200 ms |
| busbar_nominal_v | 48 | - | ✅ | OCP ORv3 base spec | PSU outputs 50-51 V |
| it_gear_tolerance_v | 46-52 | - | ✅ | OCP ORv3 base spec | **Defines "servers lost power": busbar <46 V** |
| relay_27_pickup_range | 0.02-1.00 × Vnom | - | ☑️ | SEL-751A | Compliant designs set below 0.20 pu (§8) |
| relay_uv_accuracy | ±1% + 0.5 V; pickup <1.5 cyc | - | ☑️ | SEL-751A | setting-tolerance sampling |
| breaker_interrupt_s | 0.042 | 0.033-0.050 | ☑️ | SEL | 2-3 cycles |

> ### ⚠️ PSU restart is a first-class failure mode
> After a BBU discharge, PSU turn-on takes **1.0-8.5 s typical, up to 11.5 s**, including a
> **0-5.5 s random delay**. That exceeds the 2.0 s recovery deadline outright. The randomness
> also means identical scenarios can return different verdicts — sample the delay as a scenario
> input rather than drawing it inside the model, or the surrogate trains against label noise.

## 4. Battery (BBU)

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| bat_r_growth_per_yr | **4%** | **3-6%** | ✅ | [Sandia SAND2008-5583 Table 2](https://www.thierry-lequeu.fr/data/SAND2008-5583.pdf) | Resistance grows **1.1-2.3× as fast as capacity fades** (R 0.0036→0.0042 Ω = +17%; capacity −7.3 to −15%). **Was G, now sourced** |
| bat_capacity_vs_temp | vs 25 °C | 35 °C **1.06** · 0 °C **0.74** · −20 °C **0.65** · −30 °C 0.48 · −40 °C 0.03 | ✅ | Sandia Table 2 (Cell #3) | **Corrects the earlier 0.80-at-0 °C guess to 0.74** |
| bat_r0_spread | ±6% | 0.0033-0.0037 Ω | ✅ | Sandia Table 2 | Unit-to-unit, 3 cells only |
| bat_capacity_spread | ±1.5% | 9.61-9.88 Ah | ✅ | Sandia Table 2 | Unit-to-unit |
| bat_r0_cell_mohm | 30 | 20-35 (to 80) | ⚠️ | Li-ion resistance literature | Healthy 18650 at room temp. **Pack R0 = ×11/6 ≈ 55 mΩ** |
| bat_r1_mohm / bat_c1_f | TBD | - | - | - | **No citable typical value — needs HPPC fitting (PyBaMM + NASA PCoE)** |
| bat_ocv_curve | TBD | - | - | - | Per-cell 2.7-4.0 V implied by the 30-44 V pack over 11S |
| battery_age_yr | 3 | 0-10 | ☑️ | Li-ion life 8-15 yr | |
| bat_eol_capacity | 0.80 | - | G | industry convention | |
| bat_soc0 | 0.95 | 0.80-1.00 | ⚠️ | UPS float practice | |
| bat_temp_c | 25 | 20-30 normal; to 40 if cooling already degraded | G | assumption | **Not outdoor temperature. Sample as an initial condition** — hall temperature cannot move meaningfully inside a 15 s window |

> **Proxy caveat:** the Sandia data is **LFP**, while ORv3 BBUs use **NMC 18650** cells.
> Fade and resistance-growth behaviour differ between chemistries. Treat as order-of-magnitude
> until the PyBaMM/NASA fit lands.
>
> **Energy reconciliation, still unresolved:** 3 kW × 4 min = **200 Wh** vs 11S6P × 1.5 Ah
> ≈ **333 Wh**. Suggest 200 Wh usable as authoritative ("≥1.5 Ah" is a floor; 4 min is likely
> EOL-derated).

## 5. Cooling

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| cooling_share | 0.30 × IT at 25 °C | 0.20-0.35 | Dv | Texas PUE 1.2-1.4 | 0.5 = legacy stress test |
| cooling_temp_coeff | +0.04 /°C | 0.02-0.06 | Dv | heat-wave PUE rise 0.2-0.3 | winter floor 0.4× (G) |
| outdoor_temp_c | Texas weather | ~0-42 | M | NOAA / Meteostat | Bayesian network root node |
| **motor_inertia_H_s** | **compressor 0.1 · fan 0.5 · pump 0.15** | - | ✅ | [NERC Dynamic Load Modeling Tech Ref, Table 5.1](https://www.nerc.com/globalassets/our-work/technical-reference-documents/dynamic-load-modeling-technical-reference.pdf) | **Was 0.8 (range 0.2-2.5) — 2-8× too high.** Much less kinetic ride-through than assumed |
| motor_load_torque | T_rated·(ω/ω_rated)² | - | R | centrifugal affinity law | fans and pumps |
| motor_locked_rotor_x | 6 | 5-6 | ☑️ | NERC large-load guideline | stalled-motor current |
| cooling_restart_s | 120 | 30-120 adjustable | ✅ | [Trane Rapid Restart (RTAC)](https://support.trane.com/hc/en-us/articles/19411961163021-Data-Centers-Rapid-Restart) | Power-up checks 15-30 s; 1st compressor 1-2 min; 2nd 2-5 min later; start-to-start 5 min. **Longer than the window → stays off** |

### Motor trip model — NERC Table 5.1 ✅ *(replaces the single `cooling_trip_v_pu` threshold)*

| Stage | Condition | Compressors (A) | Fans (B) | Pumps (C) |
|---|---|---|---|---|
| 1 | V < 0.70 pu for 0.05 s | 30% trip | 30% trip | 30% trip |
| 2 | V < 0.60 pu for 0.02 s | **70%** trip | 50% trip | 50% trip |
| Reconnect | V > 0.5 pu after 0.25 s | **stays off** | reconnects | reconnects |

**Motor electrical model** (NERC Table 5.1, A/B/C): Lfm 0.8 · Rs 0.01/0.005/0.01 ·
Ls 3.1/4.0/3.1 · L′ 0.1384/0.185/0.185 · L″ 0.121/0.16/0.16 · T0′ 0.1028/0.8/0.35 s ·
T0″ 0.0028/0.0044/0.0036 s · Etrq 0/2/2

> ### 🔄 Retraction: cooling trips are NOT automatically fatal
> An earlier revision concluded that any cooling trip forces a fail (losing all 0.30 of
> cooling leaves 77% of load, under the 90% bar). **That assumed all-or-nothing loss and is
> wrong.** With the NERC staged model:
>
> - Stage 1 (30% trip): lose 0.3 × 0.30 = 0.09 → **93% remaining → passes**
> - Stage 2 (50% of fans/pumps): → 88% → fails, **but they reconnect after 0.25 s**
> - Only **compressors stay off**, so the lasting loss is compressor share alone
>
> The outcome now depends on the **compressor/fan/pump split of cooling load**, which we do
> not have. That split is the parameter to find next — it is what decides how much load is
> permanently lost.

## 6. AI / server load ✅ *(substantially revised)*

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| workload | 0.85 | 0.5-1.0 | G | - | fraction of IT rating |
| **swing_freq_hz** | 1.0 | **0.2-3** | ✅ | [arXiv 2508.14318 §III-A](https://arxiv.org/pdf/2508.14318); NERC large-loads whitepaper p.7 | Dominant band; periods 0.33-5 s. Training↔checkpoint transitions <1 s |
| **swing_slew_pu_s** | **1.9** | - | ✅ | [NERC large-loads whitepaper p.7, Figs 2.2-2.3](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/whitepaper-characteristics-and-risks-of-emerging-large-loads.pdf) | Measured ramp rate (data: EdgeTunePower). pu base inferred = the 50 MW block's own demand |
| swing_size_frac | 0.2 | 0-0.5 | ✅ | NERC whitepaper | ≈0.475 pu change observed over ~250 ms at 1.9 pu/s |
| restart_surge_x | 1.15 | 1.0-1.3 | G | - | only if servers actually lost power (busbar <46 V) |
| restart_surge_s | 0.5 | 0.1-2.0 | G | - | decay time constant |

> ### 🔄 Revision: the swing is periodic, not a one-time step
> v2 modelled the swing as a single smoothed step that persists for the window, because no
> duration data existed. The NERC/arXiv data shows it is **oscillatory at 0.2-3 Hz with a
> 1.9 pu/s slew rate**. This also dissolves the `swing_duration` gap — periodic behaviour has
> a period, not a duration.

**Revised functional form** — a square wave at the sampled frequency, slew-rate limited.
This is physically right in both regimes: at 0.2 Hz a 250 ms edge is a fast transition on a
long plateau (near-square), while at 3 Hz the edge occupies most of the period (near-triangular).

```
target(t) = ½ · swing_size_frac · P_rated · sign( sin(2π · swing_freq_hz · t + phase) )

d/dt P_swing = clamp( (target − P_swing)/dt , −slew, +slew ),  slew = 1.9 pu/s · P_rated

P_server(t) = workload·P_rated + P_swing(t)
            + (restart_surge_x − 1)·P_rated·exp(−(t − t_rec)/restart_surge_s)
                                              if the busbar fell below 46 V
```

## 7. Ride-through controller

| Name | Value | Range | Status | Source | Notes |
|---|---|---|---|---|---|
| transfer_threshold_pu | 0.85 | 0.75-0.90 | ☑️ | ERCOT LEL RT Criteria, LLWG Jul 2025 | |
| handback_delay_s (product) | 0.2 | 0.2-0.5 | ☑️ | Analog Devices BBU | busbar >48.5 V for 200 ms |
| handback_delay_s (legacy) | 3 | 2-10 | ⚠️ | [ERCOT LLWG Jul 2025](https://www.ercot.com/files/docs/2025/07/11/ERCOT-LEL-Ride-Through-Criteria_LLWG-final.pptx); ESIG 2026 | "several seconds" — no exact number published |
| **legacy_count_scheme** | **3 disturbances in 1 min → transfer to backup, stay off until manual reset** | - | ☑️ | [NERC Incident Review: Large Load Loss, p.8](https://nerc.com/pa/rrm/ea/Documents/Incident_Review_Large_Load_Loss.pdf) | **Exactly what NOGRR §2.14(6) bans** — implement as the legacy preset |
| ramp_back_s | 0.3 | 0.1-1.0 | G | team doc | shape unspecified; assume linear |

> **2.0 s is supported by evidence, not just rule text:** an ERCOT Jan 2026 study found better
> grid performance when large loads reconnect within 2 s (AionTracks LLWG deck). ✅

## 8. Grader — ERCOT NOGRR 282 (effective Aug 1, 2026)

Graded on **RMS positive-sequence voltage at the Service Delivery Point**. Four checks.

### (a) Ride-through envelope — §2.14(2) Table A ✅

| RMS positive-seq V (pu) | Must stay connected |
|---|---|
| V > 1.20 | may trip |
| 1.10 < V ≤ 1.20 | 2.0 s |
| 0.90 ≤ V ≤ 1.10 | continuous |
| 0.80 ≤ V < 0.90 | 2.0 s |
| 0.50 ≤ V < 0.80 | 0.5 s |
| 0.20 ≤ V < 0.50 | 0.25 s |
| V < 0.20 | 0.15 s |

### (b) Power floor — §2.14(2)(c)

Proportional to the voltage drop across 0.80-0.50 pu; below 0.50 pu may reduce as needed.

| Energized | Requirement 0.80-0.50 pu |
|---|---|
| after Nov 14 2025, on/before Jan 1 2028 | proportional **"if capable"** (escape clause) |
| after Jan 1 2028 | **shall** continue consuming |

**Open decision: which regime do we grade against?** Post-2028 is stricter.

### (c) Recovery — §2.14(2)(b)/(c)

**≥90% of pre-disturbance active power within 2.0 s** of voltage returning above 0.90 pu.
This is the **only** recovery deadline in the rule — there is no "0.5 s fast scheme."

### (d) Current cap — §2.14(2)(d)

**≤125% of maximum normal operating current** during a disturbance. March 2026 revision adds a
≤0.5 s qualifier. ☑️ **Draft-rule caveat:** the SPWG deck itself notes *"Recommend that DWG and
SPWG review this threshold"* — confirm the figure survived into the approved Aug 2026 text.

Observed real events drew **150-200%** (and the NERC crypto review gives exact numbers — see §9).

### Protection-setting constraints — §2.14(4)(5)(6)

- **(4)** Protection must allow ride-through *beyond* the envelope, to equipment tolerance —
  **not** set at or just outside the curve. → compliant preset pickup below 0.20 pu; legacy 0.85 pu.
- **(5)** Instantaneous OV protection needs a **≥1-cycle** measurement window.
- **(6)** **Cumulative-sag trip schemes are banned.** → the `legacy_count_scheme` in §7 (3 dips
  in 1 min) is non-compliant by construction; perfect legacy demo.

### Frequency — §2.6.4

Continuous 58.8-61.2 Hz; 299 s at 57.0-58.8 and 61.2-61.8; may trip outside. March 2026 raised
the high-frequency threshold to 63 Hz. Modelled design has no frequency trip → assumed met.

### Outputs per run

```python
{"passed", "recovery_margin_s", "min_power", "final_power_frac",
 "floor_violation_s", "peak_current_pu", "envelope_violation_s",
 "storage_left", "psu_restart_s", "trips", "failure_mode"}
```

Plus time series of V, I, P at SDP, transformer, PSUs, busbar, BBU, servers, cooling.

## 9. Validation targets (compare outputs; never feed in as inputs)

| Case | Input | Observed | Use | Status |
|---|---|---|---|---|
| **Crypto facility A** (ERCOT) | 0.535 pu; 2 phases <0.7 pu >20 ms | **160% current**; 112.3 → 60.6 MW (**46% lost**); ~2 h recovery | Calibrate current limit; validate legacy | ✅ NERC crypto review p.5 + Table 1 |
| **Crypto facility B** (ERCOT) | 0.670 pu; 1 phase <0.7 pu >20 ms | **150% current**; 157.0 → 119.3 MW (**24% lost**); ~5 min recovery | Validate | ✅ same |
| Shallow dip (ERCOT) | 0.844 pu | 19% load lost | Validate legacy | ✅ via AionTracks slide 3 — *confirm 0.844 in the NERC PDF* |
| **Product recovery** | 70 sags | **0.41 s median, 0.49 s worst; never disconnected** | Calibrate/validate the grid-friendly preset | ✅ [AionTracks LLWG deck slides 10-11](https://www.ercot.com/files/docs/2026/08/14/AIONTRACKS_LLWG_2026-08-21_FINAL_v3.pdf) |
| Counting scheme | 3 dips in 1 min | stays off until manual reset | Validate legacy | ☑️ NERC Large Load Loss p.8 |
| Eastern event | 3rd dip / 3rd reclose | ~1,260 MW did not return for hours | Validate legacy (fleet) | ☑️ NERC Large Load Loss p.9 — non-Texas |
| ERCOT context | — | 26 large-load ride-through events in <3 yr | Pitch context | ✅ AionTracks slide 3 |

**Counting caveat:** most validation comes from **one** report (NERC crypto incident review,
Jan 2026). The "50 ms dip, 5 min-2 h recovery" case on AionTracks slide 3 is the **same event**
as facilities A/B — count it once, not twice.

## 10. Open items

**Resolved in v3:** battery resistance growth and temperature derating (Sandia) · motor inertia,
trip staging and electrical model (NERC Table 5.1) · AI swing frequency and slew rate (NERC +
arXiv) · chiller restart timing (Trane) · distribution and PDU transformer impedance (Eaton/NEMA) ·
legacy counting scheme (NERC) · product recovery benchmark (AionTracks) · facility scale anchor.

**Still open:**

1. **Decide:** ANDES required or optional? (The balanced-fault limitation is now documented
   evidence against it — real ERCOT dips were unbalanced.)
2. **Decide:** pre-2028 or post-2028 power-floor regime.
3. **Find: the compressor / fan / pump split of cooling load.** Now the single most
   consequential unknown — it decides how much load is permanently lost after a cooling trip,
   since only compressors stay off.
4. Battery **R1 / C1** — HPPC fitting (PyBaMM + NASA PCoE 5, 11).
5. **BBU energy reconciliation** — 200 Wh vs ~333 Wh.
6. Confirm the **125% current cap** survived into the approved Aug 2026 NOGRR text
   (the deck flags it as under review).
7. Confirm **0.844 pu** appears in the NERC crypto PDF; add the Schneider FAQ URL.
8. Pick the PDU transformer class (15-750 kVA NEMA vs 500-2,250 kVA hyperscale) to match
   `facility_it_mw`, then fix %Z and the MVA bases.
9. **Garbled row in the v3 source** — one row read
   *"Capacity fade per year | 2.5%/yt 0.535 pu; facility B 150% at 0.670 pu"*, which merges a
   battery fade figure with facility A/B current data. Recorded `bat_fade_per_yr = 2.5%/yr (G)`
   and the current figures under §9. **Vihari: confirm the intended value and source.**
10. All `G`-tagged values: sensitivity analysis, not research.

**Proxy caveats to state in the pitch:** crypto facilities are proxies for AI data centers
(similar power electronics, possibly different controls) · NERC Table 5.1 motor values are
industrial-motor defaults, not data-center measurements · Sandia battery data is LFP while
BBUs are NMC · real Texas dips were unbalanced while ANDES models balanced faults.

**Out of scope:** backup generator transition (10 s - 5 min), reactive power (Q), grid feedback
from facility load loss, single-phase faults.
