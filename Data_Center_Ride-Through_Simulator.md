# Data Center Ride-Through Simulator

Oct 17, 2026 · @raksshana · *revised after ERCOT NOGRR 282 primary-source review*

> **Companion file:** [`Parameter_Table.md`](Parameter_Table.md) holds every numeric value,
> its range, its provenance tag and its source. This file holds the architecture,
> physics and plan. When the two disagree, the parameter table wins on numbers.

## Project overview

We are building a crash tester for data center grid ride-through: a tool that hunts for the realistic ways a data center drops off the grid during a voltage dip. The simulator is the core of it. Everything else learns from it or is checked against it.

**The problem.** When a grid fault (lightning, a branch on a line) causes a split-second voltage dip, every data center in the region can switch to backup power at once. Gigawatts of demand vanish, which threatens grid stability. Per the team proposal, a single 230 kV line fault in Northern Virginia on July 22, 2026 moved roughly 3.8 GW of data center load to backup.

**The gap.** Companies sell ride-through technology, and Texas now requires proof before a large computing load connects — ERCOT NOGRR 282 / NPRR 1308 took effect **August 1, 2026**. But no certification system exists, and today's studies test a few fixed scenarios. Failures hide in rare combinations: a dip on a hot day, with aged storage, during an AI load swing, followed by a second dip.

**Our idea.** Generate millions of realistic scenarios, find the ones that break a design, explain why, and find the smallest fix. The pipeline:

1. **Scenario generator** produces realistic, correlated "bad days"
2. **Simulator** plays each scenario out with physics and grades it against NOGRR 282
3. **Neural surrogate** learns to imitate the simulator in milliseconds, trained on thousands of simulator runs
4. **Failure search** runs millions of scenarios through the surrogate and keeps the likely failures
5. **Verification** re-runs every found failure in the real simulator
6. **Report** groups failures by mode, gives odds, the smallest fix, and which factors matter most

**Hackathon track:** model learning. The neural surrogate is the trained model at the center: it learns the facility's physics from simulator data and makes the million-scenario search possible.

## What the simulator does

**Scope (known limitation).** The simulator, and everything built on it (training data, surrogate, pipeline reports), is only trusted for grid dips whose **retained voltage is 0.70-0.90 pu** (`sim.constants.VALID_DIP_DEPTH_PU`), which covers about 69% of sags (Eaton/EPRI; `IN_SCOPE_SAG_SHARE`). Deeper sags hit an unresolved voltage-collapse / invalid-root problem in the voltage solution (see `validation/CROSSCHECK.md`), so they are out of scope for now: sampling stays inside the band by default (`sim.scenario.sample(..., in_scope_only=True)`), results are conditional on an in-band dip, and deeper sags are unassessed, neither pass nor fail.

The simulator answers one question per scenario: when grid voltage dips, does this data center stay connected and restore consumption in time, or does it violate the ride-through rule?

It steps forward in small time increments (about 0.1 ms) for **up to ~15 s** (see note below) and tracks voltage, power flows, stored energy and every piece of equipment's state, then grades the power the grid sees at the Service Delivery Point.

> **Window length.** Originally scoped at 6–8 s. Raised to ~15 s because ORv3 PSUs can take
> **up to 11.5 s** to turn back on after a BBU discharge (see component 5). A shorter window
> would cut off the restart outcome, which is one of the most consequential failure modes.

**In scope**

- The grid as an input: a voltage dip, optionally a second one ("the grid throws the punch")
- Everything inside the facility: converter, DC link, rack batteries, server power supplies, servers, cooling
- The Service Delivery Point: power drawn from the grid, where the rule is judged

**Out of scope**

- How the wider grid reacts when data centers drop off (frequency rise, cascades). That is the pitch's consequence, not something we simulate.
- Instantaneous AC waveforms on each phase (PSCAD-level detail)
- Backup generator transition (10 s – 5 min), reactive power (Q), single-phase faults

**Level of detail: an averaged physics model.** We simulate real physics for energy and power flow (current limits, energy balance, battery equivalent circuits, motor torque), not the 60 Hz wave itself. This is the same approach as grid planning tools. Fast equipment behavior that only waveforms could compute is captured as datasheet-based rules: "trips if voltage is below X for more than Y ms." We need the *effects* of fast detail, and manufacturers already measured those for us.

NOGRR 282 grades **RMS positive-sequence** voltage, which is exactly the quantity an averaged model produces — so the rule and the model are measured in the same units. This is a real argument for the modeling choice, not a concession.

## Engine decision

**The live engine is OpenModelica, compiled to an FMU and driven from Python via FMPy.**

| Role | Tool | Why |
| --- | --- | --- |
| **Live engine** | OpenModelica → FMU → FMPy | Equation-based; trips/state machines are native `when` clauses rather than hand-rolled event detection |
| Batch runner / ML pipeline | Python | Scenario sampling, surrogate training, failure search |
| Offline calibration | PyBaMM, ngspice, DPsim | Run *once* to produce parameters or validate a formula — never inside the solve loop |
| Grid dip input | ANDES *(decision pending)* | Realistic dip shapes; plan doc had this optional, parameter table assumes it. **Resolve this.** |

**Install caveat:** OpenModelica discontinued official macOS binaries after v1.16. On Apple Silicon the route is MacPorts (`openmodelica-devel +libraries`) or a source build. Budget setup time, and keep the existing NumPy prototype as a fallback until the FMU toolchain is proven.

**Offline calibration plan** (do this *after* the core model runs, not before):

- **PyBaMM** — fit `Q(T, age)` and `R0(T, age)` for the BBU from NASA PCoE data, then bake the fitted curves in as lookup tables.
- **ngspice/PySpice** — cross-check the lumped PSU hold-up formula against a circuit-level transient on ~5–10 representative dips.
- **DPsim** — EMT-level check that the averaged dip shape and transformer response aren't hiding anything.

## How it works: components and physics

The simulator follows power from the grid to the servers. Hardware is rack-level (Open Rack V3): each rack has its own power shelves and battery backup units (BBU) on a 48 V busbar, rather than one central UPS.

```
                                          +---------- Each rack (Open Rack V3) ----------+
+-----------+        +-------------+      |  +------------+      +-----------------+    |
|   Grid    |        | Transformer |      |  |    PSUs    |      |   48 V busbar   |    |
| dip input |--> o -->| impedance Z |----->|->| 6 x 3 kW   |----->| 46-52 V to IT   |    |
| square or |    ^   | facility    |      |  | hold-up    |      | AI load swings  |    |
| ANDES     |    |   | side        |      |  | 20 ms/60 J |      +-----------------+    |
+-----------+    |   +-------------+      |  | trip 172 V |               ^             |
                 |          |             |  +------------+      +-----------------+    |
  Service Delivery Point    |             |                      |   BBU battery   |    |
  (graded vs NOGRR 282)     |             |                      | 2 ms takeover   |    |
  + 125% current cap        |             |                      | 200 ms hand-back|    |
                            |             |                      +-----------------+    |
                            |             +----------------------------------------------+
                            |
                            +------> Cooling: VFDs and motors
                                     (torque falls with voltage squared;
                                      rides through on motor inertia, then trips)
```

Power enters at the Service Delivery Point, passes the facility transformer chain, then splits to each rack's power shelves (backed by BBUs on the 48 V busbar) and to cooling.

### 1. Grid connection

The grid is a voltage source behind an impedance. The dip is a drop in the source voltage, either a square dip or a realistic curve from ANDES. The impedance is the facility's transformer chain and feeder, because ANDES voltages already include the wider grid.

$$V_{sdp}(t) = V_{source}(t) - Z_{xfmr} \cdot I(t)$$

### 2. Front-end converter current limit

Converters cannot exceed a current limit, so the power they can draw falls with voltage. This creates the shortfall that forces batteries to take over, from physics rather than a made-up rule.

$$P_{available} = \sqrt{3} \cdot V_{ac} \cdot I_{max}$$

**In rack-level architecture this is not a separate facility device** — it is the aggregate of the PSUs' own limits (3 kW each, overload >3.6 kW for 100 ms hands off to BBU). The facility-level number that *does* bind is regulatory, not hardware: NOGRR 282 §2.14(2)(d) caps consumption at **125% of maximum normal operating current** during a disturbance. ERCOT's own note: 125% is exactly what permits constant power down to 0.8 pu, and observed real events drew **150–200%**.

### 3. DC link energy balance

Capacitors between converters and loads store a little energy. When power out exceeds power in, DC voltage sags; below a threshold, equipment trips or the BBU takes over.

$$C \, V_{dc} \frac{dV_{dc}}{dt} = P_{in} - P_{out}$$

For the PSU, model this as an **energy reservoir of 60 J** rather than solving for C: the ORv3 spec states the PSU output droops 3 V once 50% (30 J) of hold-up energy is gone, with 24 J of that reserved for pulse-power events. That sidesteps needing V₀/V_min for the internal bus.

### 4. Rack battery (BBU)

A standard equivalent-circuit battery model. Capacity Q shrinks and resistance R0 grows with temperature and age.

$$\frac{dSOC}{dt} = -\frac{I}{3600\,Q}, \qquad V_{term} = OCV(SOC) - I R_0 - V_1, \qquad \frac{dV_1}{dt} = -\frac{V_1}{R_1 C_1} + \frac{I}{C_1}$$

Pack is 11S6P 18650. Cell R0 ≈ 20–35 mΩ healthy at room temperature → pack R0 ≈ ×11/6 ≈ **55 mΩ**. R1/C1 have no citable typical value and must be fitted (HPPC via PyBaMM against NASA PCoE).

### 5. Server power supplies (PSUs)

PSUs are constant-power loads: as voltage drops, current rises, which can hit current limits. Their internal capacitors ride short dips.

$$I = \frac{P}{V}, \qquad t_{hold} = \frac{C\,(V_0^2 - V_{min}^2)}{2P} \;\;\rightarrow\;\; \text{(use the 60 J reservoir instead)}$$

Six 3 kW PSUs per 18 kW shelf; up to 10 shelves in parallel per rack. Efficiency 97.5% peak, ≥96.5% at 230–277 V across 30–100% load.

> ### ⚠️ Restart timing is a first-class failure mode
>
> | Condition | Typical turn-on | Max (sync failure) |
> | --- | --- | --- |
> | No BBU discharge | 1.0 – 5.0 s | 6.5 – 8.0 s |
> | **After BBU discharge** | **1.0 – 8.5 s** | **10 – 11.5 s** |
>
> Plus a deliberate **0–5.5 s random delay** after BBU discharge (to avoid synchronized
> inrush across racks), and PSUs retry sync every 5 s.
>
> **If PSUs actually shut down, the 2.0 s recovery requirement is physically unreachable** —
> and because the delay is random, identical scenarios can return different verdicts.
> This is hardware-sourced, not assumed, and it is likely the most interesting failure
> mechanism in the model.

### 6. Cooling motors and drives (VFDs)

Motor torque falls with the square of voltage, so motors slow and can stall in deep dips.

$$J \frac{d\omega}{dt} = T_{motor} - T_{load}, \qquad T_{motor} \propto V^2, \qquad T_{load} = T_{rated}\left(\frac{\omega}{\omega_{rated}}\right)^2$$

The load-torque term is the centrifugal affinity law (fans and pumps).

**Ride-through comes from motor inertia, not DC capacitance.** ABB ACS880-class drives implement power-loss ride-through (param 30.31) as *kinetic buffering*: the drive briefly regenerates off the motor's own rotating inertia to hold the DC bus up. So the inertia constant H is the parameter that matters; a VFD DC-link capacitance value is not needed. UV trip ≈ 65–75% of nominal DC bus.

> ### 🔄 Retracted: cooling trips are partial, not automatically fatal
>
> An earlier revision concluded any cooling trip forces a fail (losing all 0.30 of cooling
> leaves 77% of load, under the 90% bar). **That assumed all-or-nothing loss and was wrong.**
>
> NERC Dynamic Load Modeling Table 5.1 gives a *staged, partial* trip:
>
> | Stage | Condition | Compressors | Fans | Pumps |
> | --- | --- | --- | --- | --- |
> | 1 | V < 0.70 pu for 0.05 s | 30% trip | 30% | 30% |
> | 2 | V < 0.60 pu for 0.02 s | **70%** trip | 50% | 50% |
> | Reconnect | V > 0.5 pu after 0.25 s | **stays off** | reconnects | reconnects |
>
> Redoing the arithmetic: a stage-1 trip loses 0.3 × 0.30 = 0.09 → **93% remaining, which
> passes.** Stage 2 drops further, but fans and pumps come back inside 0.25 s. Only
> compressors stay off.
>
> **So the outcome hinges on the compressor/fan/pump split of cooling load — which we don't
> have.** That split is now the single most consequential unknown in the model.

### 7. Servers and AI load

Server power follows a workload profile: steady utilization, a synchronized swing, and a surge if jobs restart after losing power.

> **🔄 Revised:** an earlier draft modelled the swing as a single smoothed step that persists
> for the window, because no duration data existed. Measured data (NERC large-loads whitepaper;
> arXiv 2508.14318) shows it is **periodic at 0.2–3 Hz with a 1.9 pu/s ramp rate**. This also
> dissolves the `swing_duration` gap — periodic behaviour has a period, not a duration.

The swing is a **slew-rate-limited square wave**:

$$\text{target}(t) = \tfrac{s}{2} P_{rated}\,\text{sgn}\!\left(\sin(2\pi f t + \phi)\right), \qquad \left|\tfrac{dP_{sw}}{dt}\right| \le 1.9\,P_{rated}\;[\text{pu/s}]$$

$$P_{server}(t) = \underbrace{w P_{rated}}_{\text{baseline}} + \underbrace{P_{sw}(t)}_{\text{synchronized swing}} + \underbrace{(k-1)P_{rated}e^{-(t - t_{rec})/\tau_s}}_{\text{restart surge, conditional}}$$

- `w` = workload, `s` = swing_size_frac, `f` = swing_freq_hz (0.2–3), `k` = restart_surge_x
- The slew limit makes the shape emergent rather than assumed: near-square at 0.2 Hz, and at 3 Hz the edge fills most of the half-period so the wave never reaches full amplitude (0.32 of a commanded 0.50 pu). No discontinuity, which also suits the stiff DC-link equations.
- The surge term is gated on an *event*, not a time: it fires only if the busbar actually fell **below 46 V** (the ORv3 IT-gear floor), at the moment power is restored

### 8. Controllers and protection (logic, not physics)

UPS/BBU transfer logic, ramp-back rules, relay pickup and breaker timing are software and settings in real equipment. Coding them as logic is exactly how they work, not a shortcut.

NOGRR 282 §2.14(4)–(5) constrains how these may be set, which defines our two presets cleanly:

- **Compliant preset** — protection set to *equipment tolerance*, not to the envelope edge. UV pickup below 0.20 pu. Instantaneous OV protection must use a ≥1-cycle measurement window.
- **Legacy preset** — UV pickup at ~0.85 pu, multi-second hand-back. Should reproduce the real-world events in §9.

§2.14(6) additionally **bans cumulative-sag trip schemes**: an LEL may not disconnect or transfer "due solely to a certain number of voltage sags or swells within a certain period of time." ERCOT cites the northern Virginia events as the motivation. This directly constrains the reclose/`second_dip` scenarios — a design that trips on repeated dips is non-compliant by construction, which makes it an excellent legacy demo.

### 9. Grader — ERCOT NOGRR 282 (effective Aug 1, 2026)

Graded on **RMS positive-sequence voltage at the Service Delivery Point**. Four independent checks:

**(a) Stay connected through the envelope** (§2.14(2), Table A):

| RMS positive-seq V (pu) | Minimum ride-through time |
| --- | --- |
| V > 1.20 | may ride through or trip |
| 1.10 < V ≤ 1.20 | 2.0 s |
| 0.90 ≤ V ≤ 1.10 | continuous |
| 0.80 ≤ V < 0.90 | 2.0 s |
| 0.50 ≤ V < 0.80 | 0.5 s |
| 0.20 ≤ V < 0.50 | 0.25 s |
| V < 0.20 | 0.15 s |

**(b) Power floor during the dip.** Reduction must be *proportional to the voltage drop* across 0.80–0.50 pu; below 0.50 pu consumption may be reduced as needed. Note the compliance-date split:

- Energized **before Jan 1, 2028** — proportional reduction required *"if capable"* (explicit escape clause; if not capable, may reduce as needed but must still meet the recovery rule)
- Energized **after Jan 1, 2028** — *shall* continue consuming across 0.80–0.50 pu

**Pick which regime you grade against.** Post-2028 is the stricter and more interesting target.

**(c) Recovery.** Return to **≥90% of pre-disturbance active power within 2.0 s** of voltage returning above 0.90 pu. This is the *only* recovery deadline in the rule.

**(d) Current cap.** Consumption must not exceed **125% of maximum normal operating current** during the disturbance (March 2026 revision limits this to ≤0.5 s during transients). This is a check we must actually implement — observed real events drew 150–200%.

**Frequency** (§2.6.4): continuous 58.8–61.2 Hz; 299 s at 57.0–58.8 and 61.2–61.8 Hz; may trip outside. March 2026 raised the high-frequency threshold to 63 Hz. The modeled design has no frequency trip, so this is assumed met.

> **Implementation note:** the power floor is **voltage-proportional and therefore time-varying**.
> A scalar `min_power` cannot verify it — the floor must be evaluated at every timestep and
> violations recorded with their times.

### Solving it

All of this is a set of differential equations stepped forward in time. In Modelica the trips and transfers are `when` clauses, so the solver finds exact crossing times rather than us hand-rolling event detection.

- **Watch out:** DC-link equations are stiff. Start with a small step and confirm results stay stable. This is also why the AI load swing is a smoothed `tanh` step rather than a true discontinuity.
- **FMU flavor:** co-simulation is simpler; model-exchange gives control over stiff-solver choice. Decide once the model exists.

A working prototype with placeholder numbers exists (`ride_through_sim.py`, NumPy, 1 ms steps). It already reproduces three failure modes: storage running out, cooling tripping, and a too-sensitive trip setting. Keep it as the fallback until the FMU path is proven.

## Inputs: the scenario

A scenario is a flat list of numbers, one value per factor. The scenario generator samples these from the ranges in [`Parameter_Table.md`](Parameter_Table.md); the surrogate learns to map them to outputs.

| Group | Inputs |
| --- | --- |
| Grid event | dip depth, dip duration, second dip yes/no, gap between dips, dip shape (square or ANDES curve) |
| Conditions | outdoor temperature, battery age, battery temperature, workload level, AI swing size, restart surge |
| Facility design | storage size, PSU count per rack, **supply voltage (208 / 240 / 277 V)**, transformer impedance chain |
| Settings | UPS/BBU trip threshold, ride-through delay, ramp-back time, relay pickup and delay, VFD undervoltage trip and ride-through time |

Example:

```python
{"dip_depth": 0.6, "dip_dur": 0.083, "second_dip": True, "gap": 0.4,
 "temp_C": 38, "battery_age_yr": 3, "workload": 0.85,
 "supply_voltage": 277, "trip_threshold": 0.80, "ramp_time": 0.3}
```

> **Supply voltage default changed 230 → 277 V.** The ORv3 shelf accepts 200–277 Vac 3-phase
> 4-wire or 346–480 Vac 3-phase 5-wire. A US/Texas 480Y/277 chain puts **277 V** at the PSU;
> 230 V implies a European 400Y/230 system, which contradicts the 480 V distribution level in
> the parameter table. This matters a lot: the 172 V PSU trip is **62% of 277 V** but 75% of
> 230 V, so PSUs ride far deeper dips than previously assumed — expect PSU trips to become rare
> and cooling/BBU behavior to dominate the failure picture.

Settings are tested two ways: at their design value with datasheet tolerance (for realistic odds), and deliberately wrong (for "what if this setting is off" tests). The two results are reported separately.

## Outputs: what the simulator must produce

Every simulator we use writes the same output format, so the ML pipeline never changes when the simulator underneath does.

**1. Summary per run (the training labels)**

```python
{
  "passed": False,
  "recovery_margin_s": -0.15,      # negative = missed the 2.0 s deadline by this much
  "min_power": 0.20,               # lowest grid draw, fraction of pre-fault load
  "floor_violation_s": 0.08,       # time spent below the voltage-proportional power floor
  "peak_current_pu": 1.42,         # vs the 1.25 cap
  "storage_left": 0.35,            # fraction of battery energy left at the end
  "psu_restart_s": 6.3,            # None if PSUs never shut down
  "trips": ["bbu_takeover@0.502s", "cooling_vfd@0.74s"],
  "failure_mode": "cooling tripped"
}
```

| Field | Why we need it |
| --- | --- |
| `passed` | The verdict; what judges and the report care about |
| `recovery_margin_s` | A smooth signal of how close a case is to the edge, which trains the surrogate better than pass/fail alone. Negative on failures, not empty |
| `min_power` | How deep the load drop went; checked against the NERC 84% dip / 19% load-loss finding |
| `floor_violation_s` | **New.** The §2.14 power floor is voltage-proportional, so a scalar minimum can't verify it |
| `peak_current_pu` | **New.** Checks the 125% current cap, which is a separate pass condition |
| `storage_left` | Shows whether storage was close to running out |
| `psu_restart_s` | **New.** Captures the restart-delay failure mode; random, so worth recording per run |
| `trips` | Every equipment trip with its time, not just the first; explains why a run failed |
| `failure_mode` | Groups failures into mechanisms for the report |

**2. Time series per run (for the demo and validation)**

Voltage, current and power at the Service Delivery Point, transformer, PSUs, busbar, BBU, servers and cooling, plus equipment states, over time. These drive the demo's "one failure played out" graph and sanity checks. They are not used for training.

## Parameters

All numeric values, ranges, provenance tags and sources live in **[`Parameter_Table.md`](Parameter_Table.md)**.

### What the key numbers change

- **The PSU trip point depends on supply voltage.** 172 V is 83% of 208 V, 72% of 240 V and 62% of 277 V. At the corrected 277 V default, PSUs tolerate much deeper sags than the original 230 V assumption implied.
- **Rack storage rarely runs out in a sub-second dip.** Four minutes of backup makes "storage ran out" unlikely unless storage is degraded, undersized or covering repeated events. Don't build the demo around it without checking.
- **The 200 ms BBU hand-back delay is small against a 2.0 s deadline.** Under the original (incorrect) 0.5 s reading this was the dominant number; under the real 2.0 s rule it is comfortable. The binding constraint moved to PSU restart timing and cooling trips.
- **PSU restart after BBU discharge can exceed the 2.0 s deadline outright** (1.0–8.5 s typical, up to 11.5 s). This is now the headline mechanism.
- **Relay tolerances are real inputs for setting-mismatch tests**, and §2.14(4) makes "set to the envelope edge" explicitly non-compliant.

### Still open

| # | Item | Nature |
| --- | --- | --- |
| 1 | Battery R1 / C1 | Needs HPPC fitting (PyBaMM + NASA PCoE) — no citable typical value exists |
| 2 | BBU energy reconciliation: 3 kW × 4 min = 200 Wh vs 11S6P × 1.5 Ah ≈ 333 Wh | Suggest treating 200 Wh usable as authoritative ("≥1.5 Ah" is a floor; 4 min is likely EOL-derated) |
| 3 | Substation / MV transformer MVA bases | Pick a coherent chain for the chosen facility size rather than research further |
| 4 | ANDES: required or optional? | **Team decision.** Plan doc says optional; parameter table assumes it is the dip source |
| 5 | Compliance regime: pre- or post-Jan 2028 power floor | **Team decision.** Post-2028 is stricter |
| 6 | All `G`-tagged values | Resolve by sensitivity analysis, not research |

## Tools

| Tool | What it is | Role |
| --- | --- | --- |
| **OpenModelica → FMU → FMPy** | Equation-based modeling, compiled, driven from Python | **Main engine** |
| PSCAD | Industry-standard waveform (EMT) simulator; commercial, Windows-only, slow | Not used. Pitched as the production plug-in |
| `ride_through_sim.py` (NumPy) | Existing prototype, 1 ms steps | Fallback until the FMU toolchain is proven |
| ANDES | Free Python grid simulator (phasor-level) | Realistic dip shapes — **status pending** |
| PyBaMM | Li-ion electrochemical model | Offline: fit `Q(T, age)`, `R0(T, age)` from NASA PCoE |
| ngspice / PySpice | Circuit-level transient | Offline: cross-check the PSU hold-up formula |
| DPsim | EMT / dynamic phasor | Offline: validate dip shape and transformer response |
| ParaEMT (NREL) | Free Python waveform simulator | Future work; built for transmission, needs data-center equipment added |

### How ANDES plugs in (if adopted)

1. Pick a test grid (e.g. IEEE 14-bus) and treat one bus as the Service Delivery Point
2. Run a few hundred faults, varying location, severity, clearing time and reclosing
3. Record voltage at that bus, resampled to our time step
4. Feed a saved curve in as the source voltage, replacing the square dip

**Limits to state honestly:** ANDES runs a textbook grid, not Texas, so check its dip depths against reported events and the Eaton sag distribution. It models balanced faults, while most real faults hit one phase. It is one-way: the facility's response does not feed back into the wider grid.

**Pitch line:** "The learning pipeline is simulator-agnostic. Today it runs on an OpenModelica physics model with ANDES disturbances; for certification-grade results, plug in PSCAD."

## From simulator to surrogate to demo

The simulator is used twice: once to create training data, and again to confirm every failure the surrogate finds.

1. **Batch runner:** sample thousands of scenarios, run each through the FMU in parallel, save a CSV of inputs and summary outputs
2. **Surrogate:** a small ensemble of PyTorch networks predicts recovery margin and pass/fail, plus how unsure it is (from disagreement between networks)
3. **Failure search:** run millions of scenarios through the surrogate, weighted toward realistic conditions, and keep the predicted failures
4. **Verify:** re-run each predicted failure in the simulator; only confirmed failures reach the report. The surrogate's predictions are never reported as findings
5. **Analyze:** group failures by mode, find the smallest fix for each, rank factors with Sobol sensitivity analysis, and estimate realistic failure odds with a separate unbiased sampling run

> **Caveat for the surrogate:** PSU restart carries a deliberate 0–5.5 s *random* delay, so the
> simulator is not fully deterministic. Either fix the random seed per scenario (making the
> delay a sampled scenario input, which is cleaner) or the surrogate will be learning against
> label noise.

**Model-learning evidence for judges:** surrogate accuracy against fresh simulator runs, especially near the pass/fail edge, and the speed gain.

### Demo flow (about 2 minutes)

1. Show a design that passes the standard test scenarios
2. Hit "Hunt for failures": a failure map (e.g. dip depth vs temperature) fills in green and red as the surrogate tests scenarios
3. Click a red point: the power curve shows the dip and the load failing to return above 90% within 2.0 s, marked "confirmed in simulator"
4. Show the report card: failure modes, odds, smallest fix, most sensitive setting
5. Apply the fix and rerun: the red region shrinks

Precompute the simulator runs and surrogate training; only the fast surrogate runs live. Keep a screen recording as a backup.

## Limitations, build order and next steps

### Limitations to state in the pitch

- Every finding is "according to our simulator." A mechanism the model leaves out cannot be found by varying inputs
- Fast equipment behavior is modeled as datasheet rules, not computed from waveforms
- Datasheets give limits and tolerances, not how values vary across real units; anything without a tolerance is labeled a guess
- Grid dips are one-way and balanced; single-phase faults and grid feedback are future work
- Cooling trips are effectively terminal within the window (120 s restart), so the model cannot show cooling recovery

### Build order

1. Core energy balance: BBU battery, server load, DC link
2. Grid connection and converter current limit (creates the realistic shortfall)
3. Controller logic and grader — **note the grader is now 4 checks, not 1**
4. Cooling motor and VFD (with affinity-law load torque and kinetic-buffering ride-through)
5. PSU hold-up (60 J reservoir), restart timing with random delay, relay and breaker rules
6. Swap placeholders for the parameter table's ranges; check against the NERC 84% dip / 19% load-loss finding
7. Optional: ANDES dip library
8. Offline calibration: PyBaMM battery fit, then ngspice and DPsim spot-checks

### Owners (proposed)

| Area | Owner |
| --- | --- |
| Simulator physics, batch runner, cooling and battery research | Vihari |
| Controller and grader logic, validation targets, surrogate, failure search | Raksshana |
| Scenario generator, AI load research, parameter ranges | Varun |

### Next steps

- [x] ~~Decide the architecture: rack-level BBU or central UPS~~ → **rack-level** (all hardware sources are ORv3)
- [x] ~~Verify the ERCOT envelope~~ → done; deep edge is **0.20 pu**, recovery is **2.0 s**, no "fast scheme" exists
- [ ] **Decide:** ANDES required or optional
- [ ] **Decide:** grade against the pre-2028 or post-2028 power-floor regime
- [ ] Get OpenModelica installed (MacPorts or source build) and prove the FMU → FMPy round trip
- [ ] Fit battery R1/C1 from NASA PCoE
- [ ] Verify VFD trip values against the ABB ACS880 and Schneider ATV320 manuals
- [ ] Check whether NERC's Virginia review ties data center trips to repeated reclosing dips (now doubly relevant — §2.14(6) bans cumulative-sag trip schemes)

## Sources

**Regulatory (primary)**

- [ERCOT, Large Electronic Load Ride-Through Requirements — NOGRR 282 / NPRR 1308, SPWG, Feb 24 2026](https://www.ercot.com/files/docs/2026/03/02/04_LEL-RT-Requirements_SPWG_Feb2026.pdf) — the authoritative envelope, recovery rule, current cap and protection-setting language
- [ERCOT, NOGRR282 Item 6.2, Dec 2025](https://www.ercot.com/files/docs/2025/12/01/6.2-NOGRR282-Large-Electronic-Load-Ride-Through-Requirements-and-NPRR1308.pdf)
- [ERCOT LLWG summary, March 2026 — 63 Hz and 125%/0.5 s updates](https://www.zeroemissiongrid.com/iso-rto/ercot-llwg-3-13/)
- [NOGRR 282 overview — EPE Consulting](https://epeconsulting.com/epe-intelligence/news/preparing-for-nogrr-282-ercot-s-next-phase-of-large-load-requirements)

**Hardware**

- [Advanced Energy, ORv3 Power System (shelf, PSU, BBU, restart timing)](https://www.advancedenergy.com/getmedia/bc56a0b4-4980-4107-97cf-62a6eb792f34/TRN-AC-DC-Open-Rack-V3-Power-System-Release-1-0-(091323).pdf)
- [Advanced Energy, 50 V 3 kW ORv3 PSU datasheet](https://www.mouser.com/datasheet/2/863/eng_50v_3kw_open_rack_v3_psu_21663144142-3441551.pdf)
- [OCP, Open Rack V3 Base Specification](https://www.opencompute.org/documents/open-rack-base-specification-version-3-pdf/)
- [Analog Devices, Smart Battery Backup Part 1](https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html)
- [Analog Devices, Smart Battery Backup Part 4](https://www.analog.com/en/resources/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part4.html)
- [Vertiv, Liebert STS2 brochure](https://www.vertivco.com/globalassets/products/critical-power/power-transfer-switches/liebert-sts2-static-transfer-brochure_00.pdf)
- [SEL-751A datasheet](https://selinc.com/api/download/2822)
- [ABB ACS880 power-loss ride-through](https://www.manualslib.com/manual/1354559/Abb-Acs880-17.html?page=83)

**Grid / protection**

- [SEL, High-Speed Distribution Protection Made Easy](https://selinc.com/api/download/3166)
- [GE Vernova, Backup Protection Systems](https://gevernova.com/grid-solutions/products/applications/Back%20up%20Protection%20Systems.pdf)
- [NERC SPCS, Considerations for Autoreclosing](https://nercstg.nerc.com:443/comm/PC/System%20Protection%20and%20Control%20Subcommittee%20SPCS%20DL/SPCS_AutoReclosing_Final_20091209.pdf)
- [Khan, Bi and Jia, single-phase adaptive auto-reclosing review (2019)](https://link.springer.com/doi/10.1186/s41601-019-0133-5)
- [Industrial Monitor Direct, VFD voltage sag response](https://industrialmonitordirect.com/blogs/knowledgebase/vfd-supply-voltage-sag-response-ride-through-vs-trip)

**Context / scale**

- [RTO Insider, ERCOT large load queue hits 410 GW](https://www.rtoinsider.com/129421-ercot-large-load-requests-soar-again/)
- [Giga Energy, data center power distribution and PDU sizing](https://www.gigaenergy.com/blog/what-is-a-power-distribution-unit)

**Tools**

- [NREL, ParaEMT](https://research-hub.nrel.gov/en/publications/paraemt-an-open-source-parallelizable-and-hpc-compatible-emt-simu/)
- [ANDES on PyPI](https://pypi.org/project/andes)
- [OpenModelica macOS installation notes](https://openmodelica.org/forum/default-topic/2747-installation-in-mac-os)
- Team proposal: *Probabilistic Failure-Hunting for Data Center Ride-Through*
