# Data Center Ride-Through Simulator: Parameter Table

Setup: OpenModelica model of one representative Texas AI data center, rack-level
architecture (Open Rack V3: rack PSUs + rack battery backup units on a 48 V busbar).
Averaged (RMS) model, ~0.1 ms steps, **~15 s window per scenario** (raised from 6–8 s;
see §3 note on PSU restart). Results are graded at the Service Delivery Point against
ERCOT NOGRR 282, effective Aug 1, 2026.

Type tags: R = rule/standard, D = datasheet/design spec, L = literature,
S = secondary source (blog/summary), Dv = derived from sources, M = measured data, G = guess.
"Range" is what the scenario generator samples. "Value" is the nominal/default.

> **Revision note.** Original table by Vihari. Revised Oct 17, 2026 after reading the primary
> ERCOT source ([SPWG Feb 2026 deck](https://www.ercot.com/files/docs/2026/03/02/04_LEL-RT-Requirements_SPWG_Feb2026.pdf))
> and the ORv3 power-system spec. Rows that changed are marked **[CORRECTED]**; rows that are
> new are marked **[NEW]**. Nothing was deleted silently.

---

## 0. Facility scale **[NEW]**

Nothing in the original table anchored the model in absolute MW, but the validation targets
are absolute, so this is required.

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| lel_threshold_mw | 75 | - | R | NPRR 1308 | Large Load = ≥75 MW aggregate peak at one site; LEL = Large Load with ≥50% computational demand |
| facility_it_mw | 100 | 75-500 | Dv | ERCOT queue data | One representative hall/building. TX campuses run larger (Stargate/Abilene 1,200 MW; Vantage Frontier 1,400 MW) but those are multi-building |
| racks_per_facility | derived | - | Dv | - | = facility_it_mw / rack_power |
| rack_power_kw | 18-180 | - | D | ORv3 | One 18 kW shelf up to 10 shelves in parallel per rack |

Context: ERCOT's large-load interconnection queue is ~410 GW, ~87% data centers, with <6 GW
energized (RTO Insider, Mar 2026).

## 1. Grid event (ANDES + reclosing)

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| fault_clear_s | 0.083 | 0.067-0.10 | L | GE Vernova | 4 cycles (500 kV), 5 (230 kV), 6 (138 kV) |
| fault_clear_breaker_fail_s | 0.20 | 0.15-0.25 | L | GE Vernova | 9-15 cycles |
| stability_clear_limit | 12-20 cycles | - | L | SEL | upper bound on clearing |
| second_dip | false | true ~20% of scenarios | L | Khan et al. 2019 | >80% of faults are temporary -> reclose |
| reclose_gap_s | 0.4 | 0.25-0.6 high-speed; 1-5 delayed | L | NERC SPCS | dead time before reclose |
| andes_system_base_mva | 100 | - | R | ERCOT convention | per-unit base for ANDES |
| dip_shape | from ANDES | - | - | ANDES | balanced faults only (limitation). **Adoption still an open team decision** |

Check ANDES dips against real sag statistics (Eaton voltage sag white paper,
EPRI distribution data). Retained voltage: 0.70-0.90 pu ~69% of sags,
0.10-0.70 pu ~27%, 0.00-0.10 pu ~4%. Duration: most < 0.5 s; fitted
lognormal median 0.1 s, sigma ~1.0, truncated 0.02-1.0 s (Dv).

## 2. Transformer / feeder

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| z_substation_pct | 10% | 8-12% | L | Schneider (add link) | own base, 40-100+ MVA |
| z_distribution_pct | 5.75% | 5.75-6.5% | L | Schneider (add link) | MV -> 480 V, 1.5-3.75 MVA |
| z_pdu_pct | 4% | 3.5-5% | L | Schneider (add link) | floor PDU / isolation |
| x_over_r | 10 | 5-20 | G | - | not researched |
| **pdu_kva** **[NEW]** | 1000 | 500-2250 | S | Giga Energy | 500-750 kVA typical; up to 2,250 for AI density |
| **pf_it_load** **[NEW]** | 0.90 | 0.85-0.90 | S | Giga Energy | for kW -> kVA conversion |
| **xfmr_sizing_factor** **[NEW]** | 1.35 | 1.25-1.50 | S | Giga Energy | transformer sized at 125-150% of downstream rating |

> **Still open:** %Z values are on each transformer's own base, so a base MVA must be chosen at
> each level before they convert to ohms. Pick a coherent chain for `facility_it_mw` rather than
> researching further (e.g. for 100 MW: substation 2×75 MVA N+1, MV 2.5 MVA units, PDU 1 MVA).

## 3. Rack hardware (PSU, BBU, transfer, protection)

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| **supply_voltage_v** **[CORRECTED]** | **277** | 208 / 240 / 277 | D | ORv3 power system | **Was 230.** Shelf takes 200-277 Vac 3ph 4-wire or 346-480 Vac 3ph 5-wire. A US 480Y/277 chain (per §2) gives **277 V** at the PSU; 230 V implies a European 400Y/230 system |
| psu_input_range_v | 200-277 | operates 180-305 | D | Advanced Energy PSU | |
| psu_uv_shutoff_v | 172 | restart at 178 | D | Advanced Energy PSU | **= 83% of 208 V, 72% of 240 V, 62% of 277 V.** At the corrected 277 V default, PSUs ride much deeper sags than previously assumed |
| psu_holdup_ms | 20 | 13.3 at 150% load | D | Advanced Energy PSU | at 200-277 Vac input, 100% load |
| **psu_holdup_energy_j** **[NEW]** | 60 | - | D | ORv3 power system | Output droops 3 V once 50% (30 J) is gone; 24 J reserved for pulse power. **Model as an energy reservoir — avoids needing C, V0, Vmin for the internal bus** |
| psu_output | 50.5-51 V, 60 A, 3 kW | - | D | Advanced Energy PSU | |
| **psus_per_shelf** **[NEW]** | 6 | - | D | ORv3 power system | 6 × 3 kW = **18 kW shelf**, 50 V / 300 A out |
| **shelves_per_rack** **[NEW]** | up to 10 | 1-10 | D | ORv3 power system | shelves operate in parallel |
| **psu_efficiency** **[NEW]** | 0.965 | 0.94-0.975 | D | ORv3 power system | 97.5% peak; ≥96.5% @ 230-277 V, 30-100% load; 95.5% @ 208 V; 94% @ 10-30% load |
| psu_overload | >3.6 kW for 100 ms -> hands load to BBU, retries every 5 s | - | D | Advanced Energy PSU | 6 ms allowed for BBU to take over before PSU shuts down |
| **psu_ton_nobbu_s** **[NEW]** | 1.0-5.0 | max 6.5-8.0 | D | ORv3 power system | PSU turn-on time, no BBU discharge |
| **psu_ton_bbu_s** **[NEW]** | 1.0-8.5 | max 10-11.5 | D | ORv3 power system | PSU turn-on **after BBU discharge** |
| **psu_random_delay_s** **[NEW]** | 0-5.5 | 0-2.0 if no BBU discharge | D | ORv3 power system | Deliberate randomized delay to avoid synchronized inrush across racks |
| bbu_module | 3 kW, 4 min backup | 6 modules/shelf (5+1) | D | Analog Devices Part 1 | |
| bbu_cells | Li-ion 18650, 11S6P, >=1.5 Ah | pack 30-44 V | D | Analog Devices Part 1 | |
| bbu_takeover | busbar < 48.5 V for > 2 ms -> takes over within 2 ms; busbar never < 46 V | - | D | Analog Devices Part 1 | |
| bbu_handback_s | 0.2 | 0.2-0.5 | D | Analog Devices Part 1 | stays on battery until busbar > 48.5 V for 200 ms |
| **busbar_nominal_v** **[NEW]** | 48 | - | D | OCP ORv3 base spec | PSU outputs 50-51 V onto a 48 V nominal busbar |
| **it_gear_tolerance_v** **[NEW]** | 46-52 | - | D | OCP ORv3 base spec | **Defines "servers lost power": busbar < 46 V.** Gates the restart surge |
| sts_transfer_ms | 4 | <= 1/4 cycle | D | Vertiv Liebert STS2 | only if a static switch is modeled |
| relay_uv_accuracy | +/-1% of setting + 0.5 V; pickup < 1.5 cycles | - | D | SEL-751A | use for setting-tolerance sampling |
| relay_timer_accuracy | +/-0.5% of setting + 1/4 cycle | - | D | SEL-751A | |
| **relay_27_pickup_range** **[NEW]** | 0.02-1.00 × Vnom | - | D | SEL-751A | The *setting range*. Compliant designs must set below 0.20 pu (see §8) |
| **relay_27_delay_range** **[NEW]** | 0.00-120.00 s | 0.01 s steps | D | SEL-751A | |
| breaker_interrupt_s | 0.042 | 0.033-0.050 | L | SEL | 2-3 cycles |

> ### ⚠️ PSU restart is a first-class failure mode **[NEW]**
> After a BBU discharge, PSU turn-on takes **1.0-8.5 s typical, up to 11.5 s** on sync failure,
> including a **0-5.5 s random delay**. That exceeds the 2.0 s recovery deadline outright — so
> if PSUs actually shut down, compliance is physically unreachable. The randomness also means
> identical scenarios can return different verdicts, which matters for surrogate training
> (fix the seed, or treat the delay as a sampled scenario input).
>
> This is why the simulation window moved from 6-8 s to ~15 s.

## 4. Battery aging and temperature (Li-ion)

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| **bat_r0_cell_mohm** **[NEW]** | 30 | 20-35 (up to 80) | S | Li-ion resistance literature | Healthy 18650 at room temp. **Pack R0 = ×11/6 ≈ 55 mΩ** for 11S6P |
| **bat_r1_mohm** | TBD | - | - | - | **No citable typical value. Needs HPPC fitting (PyBaMM + NASA PCoE)** |
| **bat_c1_f** | TBD | - | - | - | same |
| **bat_ocv_curve** | TBD | - | - | - | Standard 18650 OCV(SOC); per-cell 2.7-4.0 V implied by the 30-44 V pack over 11S |
| battery_age_yr | 3 | 0-10 | L | Li-ion life 8-15 yr | |
| bat_fade_per_yr | 2.5% | 1.5-4% | G | - | calendar aging at high charge, 25 C |
| bat_fade_temp_doubling_c | 10 | 8-15 | G | common rule of thumb | aging rate doubles per +10 C |
| bat_eol_capacity | 0.80 | - | G | industry convention | |
| bat_r_growth_per_yr | 4% | 2-8% | G | - | internal resistance increase — **now anchored to bat_r0_cell_mohm** |
| bat_cold_capacity_0c | 0.80 | 0.70-0.90 | G | - | temporary, vs 25 C |
| bat_cold_r_0c | 2.5x | 2-3x | G | - | temporary, vs 25 C |
| bat_soc0 | 0.95 | 0.80-1.00 | S | UPS practice (80-100% float) | |
| bat_temp_c | = server hall temp, 25 | 20-30 normal; up to 40 if cooling fails | G | assumption | NOT outdoor temperature. **Sample as an initial condition** — hall temperature cannot rise meaningfully inside a 15 s window |

> **Energy reconciliation, unresolved:** 3 kW × 4 min = **200 Wh** per module, but 11S6P × 1.5 Ah
> at ~37 V ≈ **333 Wh**. Suggest treating 200 Wh usable as authoritative — "≥1.5 Ah" is a floor
> and the 4 min figure is likely EOL-derated. Flag in the writeup either way.

## 5. Cooling

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| cooling_share | 0.30 x IT load at 25 C | 0.20-0.35 (0.5 = legacy stress test) | L | Texas PUE 1.2-1.4 sources | 25-40%-of-total figure is older facilities |
| cooling_temp_coeff | 0.04 / C | 0.02-0.06 | Dv | PacketPower, DgtlInfra | floor at 0.4x the 25 C level in winter (G) |
| outdoor_temp_c | from Texas weather data | ~0-42 | M | NOAA / Meteostat | Bayesian network root node |
| cooling_trip_v_pu | 0.70 | 0.50-0.85 | L/S | SEMI F47; Industrial Monitor Direct | **Most decisive parameter in the model — see box below** |
| cooling_ride_through_s | 0.2 | 0.02-5 | L/S/G | SEMI F47; IMD | 0.02 = unprotected contactor; VFD ride-through configurable 0.1-30 s (commonly 3-5 s) |
| vfd_dc_uv_trip | 70-75% of nominal | 65-75% | S | IMD; ABB ACS880 | sags > 20% for > 2 cycles usually trip |
| **vfd_ride_through_mechanism** **[NEW]** | kinetic buffering | - | D | ABB ACS880 (param 30.31) | **Ride-through comes from motor inertia, not DC capacitance** — the drive regenerates off the spinning motor. So no VFD DC-link C value is needed; H is the parameter that matters |
| cooling_restart_s | 120 | 43-300 | L | rapid-restart chillers 43-60 s; standard 90 s-5 min | longer than sim window -> stays off |
| motor_inertia_H_s | 0.8 | 0.2-2.5 (pumps 0.2-0.8, fans 1-2.5) | S | swing-equation refs | pump/fan split is G |
| **motor_load_torque** **[NEW]** | T_rated·(ω/ω_rated)² | - | R | centrifugal affinity law | Standard for fans and pumps. Was missing — the swing equation can't be integrated without it |
| motor_locked_rotor_x | 6 | 5-6 x rated current | L | NERC large-load guideline | stalled-motor current |

> ### ⚠️ Any cooling trip is an automatic fail **[NEW]**
> Cooling = 0.30 × IT, so total = 1.30. Lose cooling → 1.0/1.30 = **77%** of pre-fault.
> With the 1.15× restart surge → **88%**. Both below the 90% recovery bar, and
> `cooling_restart_s` = 120 s means it never returns inside the window.
>
> So `cooling_trip_v_pu` effectively decides pass/fail on its own across a huge
> part of the scenario space. Expect the failure map to look like a picture of that
> one threshold. Worth running a design variant where cooling sits on ride-through-enabled
> VFDs (3-5 s) as the candidate "smallest fix."

## 6. AI / server load

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| workload | 0.85 | 0.5-1.0 | G | - | fraction of IT rating |
| swing_size_frac | 0.2 | 0-0.5 of IT load (+/-) | S | Battalion, Archiwise (500 MW swings, 1 GW campus) | |
| swing_timing | random in window | - | G | - | one step per scenario |
| **swing_duration** **[NEW]** | persists | - | G | - | No literature value at this timescale. Swing holds for the rest of the window once triggered — also the conservative choice for failure hunting |
| **swing_ramp_tau_s** **[NEW]** | 0.03 | 0.02-0.05 | G | - | Smoothing constant. A true discontinuity destabilizes the stiff DC-link solver |
| restart_surge_x | 1.15 | 1.0-1.3 x pre-fault | G | - | only if servers actually lost power (busbar < 46 V) |
| restart_surge_s | 0.5 | 0.1-2.0 | G | - | exponential decay time constant |

**Functional form** (was missing — magnitudes existed but no waveform):

```
P_server(t) = w·P_rated                                                  [baseline]
            ± s·P_rated · ½(1 + tanh((t − t_sw)/τ_r))                    [one smoothed step]
            + (k−1)·P_rated · exp(−(t − t_rec)/τ_s)   if busbar fell <46 V  [restart surge]

  w = workload,  s = swing_size_frac,  k = restart_surge_x,  τ_s = restart_surge_s
  t_sw ~ Uniform(0, window),  sign drawn at random
  t_rec = the instant power is actually restored (an event, not a preset time)
```

## 7. Ride-through controller

| Name | Value | Range | Type | Source | Notes |
|---|---|---|---|---|---|
| transfer_threshold_pu | 0.85 | 0.75-0.90 | R/L | ERCOT LEL RT Criteria, LLWG Jul 2025 | |
| handback_delay_s (grid-friendly) | 0.2 | 0.2-0.5 | D | Analog Devices BBU | product under test |
| handback_delay_s (legacy UPS) | 3 | 2-10 | L | ERCOT LLWG; ESIG Large Loads (2026) | "several seconds" safety delay |
| ramp_back_s | 0.3 | 0.1-1.0 | G | team doc example | time to return to full grid draw; **shape unspecified — assume linear** |

> **Note:** under the corrected **2.0 s** recovery deadline, the 200 ms hand-back is comfortable
> (it was the dominant constraint only under the earlier, incorrect 0.5 s reading). The binding
> constraints are now PSU restart timing and cooling trips.

## 8. Grader — ERCOT NOGRR 282 (effective Aug 1, 2026) **[CORRECTED]**

Graded on **RMS positive-sequence voltage at the Service Delivery Point** (or the POIB if
co-located with generation). Four independent checks.

### (a) Voltage ride-through envelope — §2.14(2) Table A

| RMS positive-seq voltage (pu) | Must stay connected for |
|---|---|
| V > 1.20 | may ride through or trip |
| 1.10 < V ≤ 1.20 | 2.0 s |
| 0.90 ≤ V ≤ 1.10 | continuous |
| 0.80 ≤ V < 0.90 | 2.0 s |
| 0.50 ≤ V < 0.80 | 0.5 s |
| **0.20 ≤ V < 0.50** | **0.25 s** |
| **V < 0.20** | **0.15 s** |

> **[CORRECTED] Deep edge is 0.20 pu, not 0.35.** This was open item #1 in the original table
> ("some secondary sources say 0.20") — now confirmed against the primary ERCOT deck.

### (b) Power floor during the dip — §2.14(2)(c)

Reduction must be **proportional to the voltage drop** across 0.80–0.50 pu; below 0.50 pu,
consumption may be reduced as needed. There is a compliance-date split:

| Energized | Requirement across 0.80–0.50 pu |
|---|---|
| after Nov 14 2025, on/before Jan 1 2028 | proportional reduction **"if capable"** — explicit escape clause; if not capable, may reduce as needed but must still meet (c) recovery |
| after Jan 1 2028 | **shall** continue consuming; proportional reduction permitted |

> **[CORRECTED]** The original note said the 0.50 cutoff was "the authors' interpretation."
> It is literal ERCOT text. **Open decision: which regime do we grade against?** Post-2028 is stricter.

### (c) Recovery — §2.14(2)(b)/(c)

Return to **≥90% of pre-disturbance active power within 2.0 s** of voltage returning above
0.90 pu.

> **[CORRECTED] There is no "fast scheme."** The original table listed an "optional fast scheme:
> transfer within 0.25 s, recover within 0.5 s." That does not exist in NOGRR 282 — the 0.5 s and
> 0.25 s figures are *envelope hold times* at those sag depths, not recovery deadlines.
> **2.0 s is the only recovery deadline.** The ESIG 1.0 s recommendation remains a what-if only.

### (d) Current cap — §2.14(2)(d) **[NEW — was missing entirely]**

An LEL **shall not consume current exceeding 125% of its maximum normal operating current**
during a disturbance. March 2026 revision limits this to **≤0.5 s** during transients.

ERCOT's own notes: real LEL ride-through events showed **150–200%** current during voltage
suppression, and 125% is exactly what permits constant power down to 0.8 pu.

This is both a grading criterion and the facility-level current limit that component 2 of the
plan doc previously had no value for.

### Protection-setting constraints — §2.14(4)(5)(6) **[NEW — was missing entirely]**

- **(4)** Protection must allow ride-through *beyond* the envelope, to the maximum the equipment
  tolerates. Settings must reflect actual equipment capability, **not be set at or just outside
  the curve**. → compliant preset = UV pickup below 0.20 pu; legacy preset = 0.85 pu.
- **(5)** Instantaneous OV protection must use a measurement window of **≥1 cycle**.
- **(6)** **Cumulative-sag trip schemes are banned** — an LEL may not trip or transfer "due solely
  to a certain number of voltage sags or swells within a certain period of time." ERCOT cites the
  northern Virginia events. → directly constrains `second_dip`/reclose scenarios; a design that
  trips on repeated dips is non-compliant by construction and makes an excellent legacy demo.

### Frequency envelope — §2.6.4

Continuous 58.8–61.2 Hz; 299 s at 57.0–58.8 and 61.2–61.8 Hz; may trip outside 57.0–61.8 Hz.
March 2026 raised the high-frequency threshold to **63 Hz**. The modeled design has no frequency
trip, so this is assumed met.

### Normal-operation limits (NOT ride-through, optional checks)

- ≤10 MW peak-to-peak in any rolling 5 s (ERCOT LLWG, proposed; S)
- 20 MW/min load ramp (S, consulting blog)

### Outputs per run

```python
{
  "passed": bool,
  "recovery_margin_s": float,   # vs the 2.0 s deadline; negative on failure
  "min_power": float,
  "floor_violation_s": float,   # [NEW] floor is voltage-proportional => needs a time-domain check
  "peak_current_pu": float,     # [NEW] vs the 1.25 cap
  "storage_left": float,
  "psu_restart_s": float|None,  # [NEW] None if PSUs never shut down
  "trips": list,                # all, with times
  "failure_mode": str,
}
```

Plus time series of V, I, P at Service Delivery Point, transformer, PSUs, busbar, BBU,
servers and cooling.

## 9. Validation targets (compare outputs; never feed in as inputs)

| Target | Number | Source |
|---|---|---|
| Shallow dip, one facility | dip to ~84% voltage cut 19% of load | NERC review via AionTracks at ERCOT |
| Virginia 2024 | ~1.5 GW lost, all data-center-type load | POWER Magazine |
| N. Virginia, Jul 22 2026 | one 230 kV fault -> ~3.8 GW to backup | Texas RE, ERCOT |
| Texas event count | 26 large-load ride-through events in < 3 yr | AionTracks at ERCOT |
| PSU tolerance | PSUs ride through anything inside ITIC curve | ITIC/CBEMA curve |
| ANDES dips | match Eaton sag depth/duration distribution | Eaton white paper |
| **Observed fault currents** **[NEW]** | 150-200% during voltage suppression | ERCOT SPWG Feb 2026 |

Presets to compare: legacy UPS (transfer ~0.85-0.9 pu, multi-second hand-back, cumulative-sag
tripping) should reproduce the events above; grid-friendly design (200 ms hand-back, protection
set to equipment tolerance) should ride through them.

## 10. Open items

**Resolved since v1:**

- ~~Verify the ERCOT envelope and recovery timing~~ → done from the primary SPWG deck. Deep edge
  **0.20 pu**; recovery **2.0 s** from 0.90 pu; **no fast scheme exists**; **125% current cap**
  and **protection-setting rules** added.
- ~~Confirm rack-level architecture~~ → **rack-level**, all hardware sources are ORv3.
- ~~Missing: PSUs per shelf, PSU efficiency, busbar tolerance, "servers lost power" threshold,
  cooling load-torque law, VFD ride-through mechanism, relay setting ranges, facility scale~~ → filled above.

**Still open:**

1. **Decide:** ANDES required, or optional/deferred? (Plan doc says optional; this table's setup
   line assumes it is the dip source.)
2. **Decide:** grade against the pre-2028 or post-2028 power-floor regime.
3. Battery **R1 / C1** — needs HPPC fitting (PyBaMM + NASA PCoE datasets 5, 11). No citable
   typical value exists.
4. **BBU energy reconciliation** — 200 Wh (3 kW × 4 min) vs ~333 Wh (11S6P × 1.5 Ah).
5. Add source links for transformer impedances; pick MVA bases for the chosen facility size.
6. Cooling ride-through spans contactor (~0.02 s) to VFD with ride-through enabled (3-5 s):
   pick a baseline design value; verify against ABB ACS880 / Schneider ATV320 manuals.
7. All `G`-tagged values: run sensitivity analysis to see which matter.

**Out of scope:** backup generator transition (10 s - 5 min), reactive power (Q), grid feedback
from facility load loss, single-phase faults.

---

## Sources added in this revision

- [ERCOT, LEL Ride-Through Requirements — NOGRR 282 / NPRR 1308, SPWG Feb 24 2026](https://www.ercot.com/files/docs/2026/03/02/04_LEL-RT-Requirements_SPWG_Feb2026.pdf)
- [ERCOT LLWG summary, March 2026 (63 Hz, 125%/0.5 s)](https://www.zeroemissiongrid.com/iso-rto/ercot-llwg-3-13/)
- [Advanced Energy, ORv3 Power System — shelf, PSU, BBU, restart timing](https://www.advancedenergy.com/getmedia/bc56a0b4-4980-4107-97cf-62a6eb792f34/TRN-AC-DC-Open-Rack-V3-Power-System-Release-1-0-(091323).pdf)
- [OCP, Open Rack V3 Base Specification](https://www.opencompute.org/documents/open-rack-base-specification-version-3-pdf/)
- [ABB ACS880 power-loss ride-through (param 30.31)](https://www.manualslib.com/manual/1354559/Abb-Acs880-17.html?page=83)
- [SEL-751A data sheet — 27 element ranges](https://selinc.com/api/download/2822)
- [RTO Insider — ERCOT large load queue hits 410 GW](https://www.rtoinsider.com/129421-ercot-large-load-requests-soar-again/)
- [Giga Energy — PDU sizing and data center power distribution](https://www.gigaenergy.com/blog/what-is-a-power-distribution-unit)
- [Lithium-ion internal resistance reference](https://www.ufinebattery.com/blog/lithium-ion-battery-internal-resistance/)
