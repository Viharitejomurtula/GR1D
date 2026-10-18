# Data Center Ride-Through Simulator

Oct 17, 2026 · @raksshana

## Project overview

We are building a crash tester for data center grid ride-through: a tool that hunts for the realistic ways a data center drops off the grid during a voltage dip. The simulator is the core of it. Everything else learns from it or is checked against it.

**The problem.** When a grid fault (lightning, a branch on a line) causes a split-second voltage dip, every data center in the region can switch to backup power at once. Gigawatts of demand vanish, which threatens grid stability. Per the team proposal, a single 230 kV line fault in Northern Virginia on July 22, 2026 moved roughly 3.8 GW of data center load to backup.

**The gap.** Companies sell ride-through technology, and Texas now requires proof before a large computing load connects. But no certification system exists, and today's studies test a few fixed scenarios. Failures hide in rare combinations: a dip on a hot day, with aged storage, during an AI load swing, followed by a second dip.

**Our idea.** Generate millions of realistic scenarios, find the ones that break a design, explain why, and find the smallest fix. The pipeline:

1. **Scenario generator** produces realistic, correlated "bad days"
2. **Simulator** plays each scenario out with physics and grades it against the Texas rule
3. **Neural surrogate** learns to imitate the simulator in milliseconds, trained on thousands of simulator runs
4. **Failure search** runs millions of scenarios through the surrogate and keeps the likely failures
5. **Verification** re-runs every found failure in the real simulator
6. **Report** groups failures by mode, gives odds, the smallest fix, and which factors matter most

**Hackathon track:** model learning. The neural surrogate is the trained model at the center: it learns the facility's physics from simulator data and makes the million-scenario search possible.

## What the simulator does

The simulator answers one question per scenario: when grid voltage dips, does this data center keep drawing power and recover in time, or does it drop off the grid?

It steps forward in small time increments (about 0.1 ms) for a few seconds. At each step it tracks voltage, power flows, stored energy and every piece of equipment's state, then grades the power the grid sees at the connection point.

**In scope**

- The grid as an input: a voltage dip, optionally a second one ("the grid throws the punch")
- Everything inside the facility: converter, DC link, rack batteries, server power supplies, servers, cooling
- The connection point: power drawn from the grid, where the rule is judged

**Out of scope**

- How the wider grid reacts when data centers drop off (frequency rise, cascades). That is the pitch's consequence, not something we simulate.
- Instantaneous AC waveforms on each phase (PSCAD-level detail)

**Level of detail: an averaged physics model.** We simulate real physics for energy and power flow (current limits, energy balance, battery equivalent circuits, motor torque), not the 60 Hz wave itself. This is the same approach as grid planning tools. Fast equipment behavior that only waveforms could compute (a converter tripping on a millisecond current spike) is captured as datasheet-based rules: "trips if voltage is below X for more than Y ms." We need the *effects* of fast detail, and manufacturers already measured those for us.

## How it works: components and physics

The simulator follows power from the grid to the servers. Our hardware sources describe a rack-level design (Open Rack V3): each rack has its own power supplies and battery backup unit (BBU) on a 50 V busbar, rather than one central UPS.

```
                                          +---------- Each rack (Open Rack V3) ----------+
+-----------+        +-------------+      |  +------------+      +-----------------+    |
|   Grid    |        | Transformer |      |  |    PSUs    |      |   50 V busbar   |    |
| dip input |--> o -->| impedance Z |----->|->| hold-up    |----->| feeds servers   |    |
| square or |    ^   | facility    |      |  | 20 ms,     |      | AI load swings  |    |
| ANDES     |    |   | side        |      |  | trip 172 V |      +-----------------+    |
+-----------+    |   +-------------+      |  +------------+               ^             |
                 |          |             |                      +-----------------+    |
     Connection point       |             |                      |   BBU battery   |    |
     (graded vs Texas rule) |             |                      | 2 ms takeover   |    |
                            |             |                      | 200 ms hand-back|    |
                            |             |                      +-----------------+    |
                            |             +----------------------------------------------+
                            |
                            +------> Cooling: VFDs and motors
                                     (torque falls with voltage squared; trips on low DC bus)
```

Power enters at the connection point, passes the facility transformer, then splits to each rack's power supplies (backed by the BBU on the 50 V busbar) and to cooling.

### 1. Grid connection

The grid is a voltage source behind an impedance. The dip is a drop in the source voltage, either a square dip or a realistic curve from ANDES. The impedance is only the facility's transformer and feeder, because ANDES voltages already include the wider grid.

$$V_{poi}(t) = V_{source}(t) - Z_{xfmr} \cdot I(t)$$

### 2. Front-end converter current limit

Converters cannot exceed a current limit, so the power they can draw falls with voltage. This creates the shortfall that forces batteries to take over, from physics rather than a made-up rule.

$$P_{available} = \sqrt{3} \cdot V_{ac} \cdot I_{max}$$

### 3. DC link energy balance

Capacitors between converters and loads store a little energy. When power out exceeds power in, DC voltage sags; below a threshold, equipment trips or the BBU takes over.

$$C \, V_{dc} \frac{dV_{dc}}{dt} = P_{in} - P_{out}$$

### 4. Rack battery (BBU)

A standard equivalent-circuit battery model. Capacity Q shrinks and resistance R0 grows with temperature and age.

$$\frac{dSOC}{dt} = -\frac{I}{3600\,Q}, \qquad V_{term} = OCV(SOC) - I R_0 - V_1, \qquad \frac{dV_1}{dt} = -\frac{V_1}{R_1 C_1} + \frac{I}{C_1}$$

### 5. Server power supplies (PSUs)

PSUs are constant-power loads: as voltage drops, current rises, which can hit current limits. Their internal capacitors ride short dips (hold-up time).

$$I = \frac{P}{V}, \qquad t_{hold} = \frac{C\,(V_0^2 - V_{min}^2)}{2P}$$

### 6. Cooling motors and drives (VFDs)

Motor torque falls with the square of voltage, so motors slow and can stall in deep dips. Each drive has its own DC link (equation 3) and trips on DC-bus undervoltage, then restarts after a delay.

$$J \frac{d\omega}{dt} = T_{motor} - T_{load}, \qquad T_{motor} \propto V^2$$

### 7. Servers and AI load

Server power follows a workload profile: steady utilization, swings when jobs synchronize, and a surge when jobs restart after a disruption.

### 8. Controllers and protection (logic, not physics)

UPS/BBU transfer logic, ramp-back rules, relay pickup and breaker timing are software and settings in real equipment. Coding them as logic is exactly how they work, not a shortcut. Their thresholds and delays come from datasheets.

### 9. Grader

Applies the Texas rule at the connection point. Between 80% and 120% voltage, the facility must keep drawing power. Below 80% it may reduce, but must return to at least 90% of pre-fault load within 0.5 s of voltage recovery.

### Solving it

All of this is a set of differential equations stepped forward in time.

- **Easy route:** `scipy.integrate.solve_ivp` with a stiff solver (Radau or BDF); its events feature catches trips at the exact moment
- **Fast route:** a fixed step of about 0.1 ms, accelerated with Numba and batched across scenarios
- **Watch out:** DC-link equations are fast (stiff). Too large a step makes the simulation unstable, so start small and check results stay stable

A working prototype with placeholder numbers exists (`ride_through_sim.py`, NumPy, 1 ms steps). It already reproduces three distinct failure modes: storage running out, cooling tripping, and a too-sensitive trip setting.

## Inputs: the scenario

A scenario is a flat list of numbers, one value per factor. The scenario generator samples these from the ranges in the parameter table; the surrogate learns to map them to outputs.

| Group | Inputs |
| --- | --- |
| Grid event | dip depth, dip duration, second dip yes/no, gap between dips, dip shape (square or ANDES curve) |
| Conditions | outdoor temperature, battery age, workload level, AI swing size, restart surge |
| Facility design | storage size, converter current limit, supply voltage (208 / 230 / 277 V), transformer impedance |
| Settings | UPS/BBU trip threshold, ride-through delay, ramp-back time, relay pickup and delay, VFD undervoltage trip and ride-through time |

Example:

```python
{"dip_depth": 0.6, "dip_dur": 0.083, "second_dip": True, "gap": 0.4,
 "temp_C": 38, "battery_age_yr": 3, "workload": 0.85,
 "supply_voltage": 230, "trip_threshold": 0.80, "ramp_time": 0.3}
```

Settings are tested two ways: at their design value with datasheet tolerance (for realistic odds), and deliberately wrong (for "what if this setting is off" tests). The two results are reported separately, as the proposal requires.

## Outputs: what the simulator must produce

Every simulator we use (our Python model now, OpenModelica or PSCAD later) writes the same output format, so the ML pipeline never changes when the simulator underneath does.

PSCAD itself outputs raw waveforms: voltage and current on each phase, sampled every few microseconds, wherever meters are placed, plus switch and controller states. Engineers boil each run down to a few numbers. Our simulator skips the waveforms and produces those numbers directly.

**1. Summary per run (the training labels)**

```python
{
  "passed": False,
  "recovery_margin_s": -0.15,   # negative = missed the 0.5 s deadline by this much
  "min_power": 0.20,            # lowest grid draw, fraction of pre-fault load
  "storage_left": 0.35,         # fraction of battery energy left at the end
  "trips": ["bbu_takeover@0.502s", "cooling_vfd@0.74s"],
  "failure_mode": "cooling tripped"
}
```

| Field | Why we need it |
| --- | --- |
| `passed` | The verdict; what judges and the report care about |
| `recovery_margin_s` | A smooth signal of how close a case is to the edge, which trains the surrogate better than pass/fail alone. Negative on failures, not empty |
| `min_power` | How deep the load drop went; the 84% dip / 19% load-loss NERC finding is checked against it |
| `storage_left` | Shows whether storage was close to running out |
| `trips` | Every equipment trip with its time, not just the first; explains why a run failed |
| `failure_mode` | Groups failures into mechanisms for the report |

**2. Time series per run (for the demo and validation)**

Voltage at the connection point, power drawn from the grid, battery, server and cooling power, and equipment states, over time. These drive the demo's "one failure played out" graph and sanity checks. They are not used for training.

**Possible later addition:** reactive power (Q). The Texas rule grades real power, so Q is future work.

## Parameters: researched values and gaps

Every number becomes a range in the scenario generator, labeled measured, datasheet or guess. The values below are researched; the open gaps follow. Times assume a 60 Hz grid (1 cycle is about 16.7 ms).

### Grid events

| Parameter | Value | Type | Source |
| --- | --- | --- | --- |
| Normal fault clearing time | 4 cycles (500 kV), 5 (230 kV), 6 (138 kV), about 0.07 to 0.10 s | Engineering reference | [GE Vernova](https://gevernova.com/grid-solutions/products/applications/Back%20up%20Protection%20Systems.pdf) |
| Breaker-failure clearing time | 9 to 15 cycles, about 0.15 to 0.25 s | Engineering reference | [GE Vernova](https://gevernova.com/grid-solutions/products/applications/Back%20up%20Protection%20Systems.pdf) |
| Stability limit on clearing | 12 to 20 cycles | Engineering reference | [SEL](https://selinc.com/api/download/3166) |
| Breaker interrupt time | 2 to 3 cycles | Engineering reference | [SEL](https://selinc.com/api/download/3166) |
| High-speed reclose dead time | 0.25 to 0.6 s | Engineering reference | [NERC SPCS](https://nercstg.nerc.com:443/comm/PC/System%20Protection%20and%20Control%20Subcommittee%20SPCS%20DL/SPCS_AutoReclosing_Final_20091209.pdf) |
| Delayed reclose dead time | 1 s or more; examples 0.5 s and 5 s | Engineering reference | [NERC SPCS](https://nercstg.nerc.com:443/comm/PC/System%20Protection%20and%20Control%20Subcommittee%20SPCS%20DL/SPCS_AutoReclosing_Final_20091209.pdf) |
| Share of faults that are temporary | more than 80%, so a second dip about 20% of the time | Literature | [Khan et al. 2019](https://link.springer.com/doi/10.1186/s41601-019-0133-5) |

Grader rule values (80 to 120% band, 90% within 0.5 s) come from the Texas requirement as described in the team proposal's ERCOT sources.

### Facility hardware

| Parameter | Value | Type | Source |
| --- | --- | --- | --- |
| PSU normal input | 200 to 277 V AC (operates 180 to 305 V) | Datasheet | [Advanced Energy PSU](https://WWW.advancedenergy.COM/getmedia/b530c4fb-6ef2-4d50-8296-24a02c9501fd/ENG-50V-3kW-OPEN-RACK-V3-PSU-235-01-04-27-22.pdf) |
| PSU undervoltage shutoff | 172 V AC, restart at 178 V | Datasheet | [Advanced Energy PSU](https://WWW.advancedenergy.COM/getmedia/b530c4fb-6ef2-4d50-8296-24a02c9501fd/ENG-50V-3kW-OPEN-RACK-V3-PSU-235-01-04-27-22.pdf) |
| PSU hold-up time | 20 ms at 100% load; 13.3 ms at 150% | Datasheet | [Advanced Energy PSU](https://WWW.advancedenergy.COM/getmedia/b530c4fb-6ef2-4d50-8296-24a02c9501fd/ENG-50V-3kW-OPEN-RACK-V3-PSU-235-01-04-27-22.pdf) |
| PSU output and overload | 50.5 to 51 V, 60 A, 3 kW; above 3.6 kW for 100 ms hands load to BBU, retries every 5 s | Datasheet | [Advanced Energy PSU](https://WWW.advancedenergy.COM/getmedia/b530c4fb-6ef2-4d50-8296-24a02c9501fd/ENG-50V-3kW-OPEN-RACK-V3-PSU-235-01-04-27-22.pdf) |
| BBU power and backup time | 3 kW per module, 4 min, 6 modules per shelf (5+1) | Design spec | [Analog Devices Part 1](https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html) |
| BBU cells | Li-ion 18650, 11S6P, at least 1.5 Ah each, 30 to 44 V pack | Design spec | [Analog Devices Part 1](https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html) |
| BBU takeover | busbar at 48.5 V for more than 2 ms; takes over within 2 ms; busbar never below 46 V | Design spec | [Analog Devices Part 1](https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html) |
| BBU hand-back delay | stays on battery until busbar is above 48.5 V for 200 ms | Design spec | [Analog Devices Part 1](https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html) |
| Static transfer switch time | 1/4 cycle max, about 4 ms | Datasheet | [Vertiv STS2](https://www.vertivco.com/globalassets/products/critical-power/power-transfer-switches/liebert-sts2-static-transfer-brochure_00.pdf) |
| Relay undervoltage accuracy | plus or minus 1% of setting + 0.5 V; pickup under 1.5 cycles | Datasheet | [SEL-751A](https://selinc.com/api/download/2822) |
| Relay timer accuracy | plus or minus 0.5% of setting + 1/4 cycle | Datasheet | [SEL-751A](https://selinc.com/api/download/2822) |
| VFD DC-bus undervoltage trip | about 70 to 75% of nominal; sags deeper than 20% for over 2 cycles usually trip | Secondary source, verify | [Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/vfd-supply-voltage-sag-response-ride-through-vs-trip) |
| VFD ride-through setting | configurable 0.1 to 30 s, commonly 3 to 5 s; kinetic buffering 1 to 3 s | Secondary source, verify | [Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/vfd-supply-voltage-sag-response-ride-through-vs-trip) |

### What these numbers change

- **The PSU trip point depends on supply voltage.** 172 V is about 83% of a 208 V supply, 75% of 230 V and 62% of 277 V. Supply voltage is therefore a key scenario input.
- **Rack storage rarely runs out in a sub-second dip.** Four minutes of backup makes "storage ran out" unlikely unless storage is degraded, undersized or covering repeated events. Don't build the demo around it without checking.
- **The 200 ms BBU hand-back delay uses much of the 0.5 s recovery deadline.** This is likely the most important number for the grader.
- **Relay tolerances are real inputs for setting-mismatch tests.**

### Open gaps

| Parameter | Where to look |
| --- | --- |
| Dip depth range and realistic dip shapes | NERC / Texas RE incident reports, ANDES runs |
| Battery capacity and resistance versus temperature and age | NASA PCoE (datasets 5, 11), CALCE |
| Facility-level converter current limit (if a central UPS is modeled) | Tesla Megapack, EPC Power material |
| Transformer and feeder impedance | Schneider transformer impedance data |
| Breaker opening time | Eaton Magnum manual |
| Cooling restart delay, motor inertia, cooling share of load | ABB ACS880, Schneider ATV320, Copeland manuals |
| AI load swing size and speed, restart surge | Texas A&M / ERCOT AI data center PSCAD model paper |
| Ride-through controller recovery behavior | Tesla and AionTracks ERCOT presentations, EPRI |
| Validation targets | NERC finding: a dip to about 84% cut 19% of one facility's load; Virginia event reviews |

## Tools: why not PSCAD, and what we use instead

We build our own Python simulator and use free tools only where they add realism.

| Tool | What it is | Role in our project |
| --- | --- | --- |
| PSCAD | Industry-standard waveform (EMT) simulator; commercial license, Windows only, slow per run | Not used. Pitched as the production plug-in |
| Our Python simulator | Averaged physics model, about 0.1 ms steps | **Main engine**: thousands of training runs |
| ANDES | Free Python grid simulator (smoothed, phasor-level) | **Optional**: realistic dip shapes for the grid input |
| OpenModelica | Free equation-based modeling tool, PSCAD-like components, scriptable from Python | **Optional checker**: a detailed model of a few failures, plus realistic waveform plots for the demo |
| ParaEMT (NREL) | Free Python waveform simulator, validated against PSCAD | Future work. Built for transmission grids, so data center equipment would need to be added |

### How ANDES plugs in

1. Pick a test grid (for example IEEE 14-bus) and treat one bus as the data center's connection point
2. Run a few hundred faults, varying location, severity, clearing time and reclosing, using the researched ranges
3. Record voltage at that bus and save each curve, resampled to our time step
4. Feed a saved curve in as the source voltage, replacing the square dip

**Limits to state honestly:** ANDES runs a textbook grid, not Texas or Virginia, so check its dip depths against reported events. It models balanced faults, while most real faults hit one phase. It is one-way: the facility's response does not feed back into the wider grid.

**Pitch line:** "The learning pipeline is simulator-agnostic. Today it runs on our physics model with ANDES disturbances; for certification-grade results, plug in PSCAD."

## From simulator to surrogate to demo

The simulator is used twice: once to create training data, and again to confirm every failure the surrogate finds.

1. **Batch runner:** sample thousands of scenarios, run each through the simulator in parallel, save a CSV of inputs and summary outputs
2. **Surrogate:** a small ensemble of PyTorch networks predicts recovery margin and pass/fail, plus how unsure it is (from disagreement between networks)
3. **Failure search:** run millions of scenarios through the surrogate, weighted toward realistic conditions, and keep the predicted failures
4. **Verify:** re-run each predicted failure in the simulator; only confirmed failures reach the report. The surrogate's predictions are never reported as findings
5. **Analyze:** group failures by mode, find the smallest fix for each, rank factors with Sobol sensitivity analysis, and estimate realistic failure odds with a separate unbiased sampling run

**Model-learning evidence for judges:** surrogate accuracy against fresh simulator runs, especially near the pass/fail edge, and the speed gain (millions of scenarios in minutes versus one simulator run each).

### Demo flow (about 2 minutes)

1. Show a design that passes the standard test scenarios
2. Hit "Hunt for failures": a failure map (for example dip depth versus temperature) fills in green and red as the surrogate tests scenarios
3. Click a red point: the simulator's power curve shows the dip and the load failing to return above 90% within 0.5 s, marked "confirmed in simulator"
4. Show the report card: failure modes, odds, smallest fix, most sensitive setting
5. Apply the fix and rerun: the red region shrinks

Precompute the simulator runs and surrogate training; only the fast surrogate runs live. Keep a screen recording as a backup.

## Limitations, build order and next steps

### Limitations to state in the pitch

- Every finding is "according to our simulator." A mechanism the model leaves out cannot be found by varying inputs
- Fast equipment behavior is modeled as datasheet rules, not computed from waveforms
- Datasheets give limits and tolerances, not how values vary across real units; anything without a tolerance is labeled a guess
- Grid dips are one-way and balanced (ANDES); single-phase faults and grid feedback are future work

### Build order

1. Core energy balance: BBU battery, server load, DC link
2. Grid connection and converter current limit (creates the realistic shortfall)
3. Controller logic and grader, reused from the prototype, with the new output format
4. Cooling motor and VFD
5. PSU hold-up, relay and breaker rules
6. Swap placeholders for the parameter table's ranges; check against the NERC 84% dip / 19% load-loss finding
7. Optional: ANDES dip library

### Owners (proposed)

| Area | Owner |
| --- | --- |
| Simulator physics, batch runner, cooling and battery research | Vihari |
| Controller and grader logic, validation targets, surrogate, failure search | Raksshana |
| Scenario generator, AI load research, parameter ranges | Varun |

### Next steps

- [ ] Decide the architecture: rack-level BBU (matches our sources) or a central UPS
- [ ] Finish the parameter table, filling the open gaps
- [ ] Rewrite the prototype with the physics equations and the standard output format
- [ ] Verify VFD trip values against the ABB and Schneider manuals
- [ ] Check whether NERC's Virginia review ties data center trips to repeated reclosing dips

## Sources

- Team proposal: *Probabilistic Failure-Hunting for Data Center Ride-Through* (event figures, Texas rule, ERCOT and EPRI references)
- [Advanced Energy, 50 V 3 kW Open Rack V3 PSU datasheet](https://WWW.advancedenergy.COM/getmedia/b530c4fb-6ef2-4d50-8296-24a02c9501fd/ENG-50V-3kW-OPEN-RACK-V3-PSU-235-01-04-27-22.pdf)
- [Analog Devices, Smart Battery Backup Part 1](https://www.analog.com/en/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part1.html)
- [Analog Devices, Smart Battery Backup Part 4](https://www.analog.com/en/resources/analog-dialogue/articles/smart-battery-backup-for-uninterrupted-energy-part4.html)
- [Vertiv, Liebert STS2 brochure](https://www.vertivco.com/globalassets/products/critical-power/power-transfer-switches/liebert-sts2-static-transfer-brochure_00.pdf)
- [SEL, SEL-751A datasheet](https://selinc.com/api/download/2822)
- [SEL, High-Speed Distribution Protection Made Easy](https://selinc.com/api/download/3166)
- [GE Vernova, Backup Protection Systems](https://gevernova.com/grid-solutions/products/applications/Back%20up%20Protection%20Systems.pdf)
- [NERC SPCS, Considerations for Autoreclosing](https://nercstg.nerc.com:443/comm/PC/System%20Protection%20and%20Control%20Subcommittee%20SPCS%20DL/SPCS_AutoReclosing_Final_20091209.pdf)
- [Khan, Bi and Jia, single-phase adaptive auto-reclosing review (2019)](https://link.springer.com/doi/10.1186/s41601-019-0133-5)
- [Industrial Monitor Direct, VFD voltage sag response](https://industrialmonitordirect.com/blogs/knowledgebase/vfd-supply-voltage-sag-response-ride-through-vs-trip)
- [NREL, ParaEMT](https://research-hub.nrel.gov/en/publications/paraemt-an-open-source-parallelizable-and-hpc-compatible-emt-simu/)
- [ANDES on PyPI](https://pypi.org/project/andes)
- [OpenModelica EMT study (arXiv 2112.00862)](https://export.arxiv.org/abs/2112.00862)
