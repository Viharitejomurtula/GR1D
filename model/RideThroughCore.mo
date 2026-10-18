model VfdClass
  "Aggregate of identical VFD-driven motors in one cooling class (compressor, fan or pump).

   Physics: a diode rectifier feeds a DC link that carries the motor load. While the AC peak is
   above the DC bus the rectifier conducts and the link tracks the AC; below it the link
   discharges at the load power (energy balance on a capacitor). If the bus reaches the drive's
   undervoltage level the drive either keeps running by decelerating the motor (kinetic
   ride-through, only if configured: ATV320 'UnderV. prevention = DC Maintain', factory default
   OFF) or stops its output and coasts. A drive that coasts resumes after a flying-restart delay
   once the bus recovers; if it coasts longer than hold_s it declares a fault and restarts only
   after fault_restart_s (auto-restart ladder) or never (manual reset). Compressors also respect
   an anti-short-cycle off-time (min_off_s). Averaged model: ripple, harmonics and the motor's
   electrical transient are not resolved."
  parameter Real p_rated_w = 1.0e6 "Class rating on the drive input side";
  parameter Real h_s = 0.5 "Inertia constant of motor plus driven load";
  parameter Real uv_trip_pu = 0.70 "DC-bus undervoltage level, fraction of nominal DC";
  parameter Real hold_s = 0.2 "Coast time before the drive declares a fault";
  parameter Real resume_s = 0.5 "Flying-restart delay once the bus has recovered";
  parameter Real fault_restart_s = 1.0 "Wait before restarting after a fault (large = manual reset)";
  parameter Real min_off_s = 0.0 "Anti-short-cycle: minimum time stopped before any restart";
  parameter Boolean kinetic = false "Configured to ride through on motor inertia";
  parameter Real c_uf_per_kw = 130.0 "DC-link capacitance per kW (G: unsourced)";
  parameter Real v_ll_v = 480.0 "Line-to-line supply";
  constant Real PEAK_OVER_RMS = 1.41421356;
  constant Real VDC_OVER_VLL = 1.35 "Ideal diode-rectifier DC / line-to-line RMS";
  constant Real F_KIN_USE = 0.3 "Usable fraction of H*S before the load collapses (speed to ~84%)";
  constant Real KRES_TAU_S = 1.0 "Re-acceleration time constant of the kinetic reserve";
  constant Real P_IDLE = 0.02 "Recharge draw while stopped, fraction of rated";
  constant Real GAP_NOM = PEAK_OVER_RMS / VDC_OVER_VLL - 1.0 "AC-peak headroom over the DC bus at nominal";
  final parameter Real uv2 = uv_trip_pu * uv_trip_pu;
  final parameter Real e_nom_j = 0.5 * c_uf_per_kw * 1.0e-6 * (p_rated_w / 1000.0) * (VDC_OVER_VLL * v_ll_v) ^ 2;
  final parameter Real e_kin_j = max(h_s * p_rated_w * F_KIN_USE, 1.0);

  input Real v_sense_pu "Filtered supply voltage";
  output Real p_grid_w "Active power drawn from the supply";
  output Real run_frac "1 while the drive is delivering";
  output Boolean stopped "Not running (coasting or faulted)";
  output Boolean faulted "Declared a fault";

  Real w(start = 1.0, fixed = true) "DC-link energy, fraction of nominal (= DC voltage squared)";
  Real kres(start = 1.0, fixed = true) "Kinetic reserve remaining";
  Integer mode(start = 0, fixed = true) "0 run, 1 coast, 2 faulted";
  Real t_coast(start = 0, fixed = true);
  Real t_off(start = 0, fixed = true);
  Real v_dc "DC voltage, fraction of nominal";
  Real f_in "Rectifier conduction factor";
  Real p_load_w;
  Real p_in_w;
  Boolean bus_low "Bus at or below the undervoltage level while load exceeds input";
  Boolean resumable "Bus recovered enough to restart";

equation
  v_dc = sqrt(max(w, 1.0e-6));
  f_in = max(0.0, min(3.0, (PEAK_OVER_RMS * v_sense_pu / VDC_OVER_VLL - v_dc) / GAP_NOM));
  p_load_w = if mode == 0 then p_rated_w else 0.0;
  p_in_w = f_in * max(p_load_w, P_IDLE * p_rated_w);
  bus_low = w <= uv2 + 1.0e-9 and p_in_w < p_load_w;
  resumable = v_dc >= uv_trip_pu + 0.05;

  der(w) = if w > uv2 + 1.0e-9 or p_in_w > p_load_w then (p_in_w - p_load_w) / e_nom_j else 0.0;
  der(kres) = if mode == 0 and kinetic and bus_low and kres > 0.0 then -(p_load_w - p_in_w) / e_kin_j
              elseif kres < 1.0 and w > uv2 + 0.01 then (1.0 - kres) / KRES_TAU_S
              else 0.0;

  der(t_coast) = if mode == 1 then 1.0 else 0.0;
  der(t_off) = if mode <> 0 then 1.0 else 0.0;
  when pre(mode) == 0 and mode <> 0 then
    reinit(t_off, 0);
  end when;
  when pre(mode) <> 1 and mode == 1 then
    reinit(t_coast, 0);
  end when;

  when {bus_low and (not kinetic or kres <= 0.0),
        t_coast >= hold_s and not resumable,
        resumable and t_off >= max(resume_s, min_off_s),
        v_sense_pu > 0.9 and resumable and t_off >= max(fault_restart_s, min_off_s)} then
    if pre(mode) == 0 and bus_low and (not kinetic or kres <= 0.0) then
      mode = 1;
    elseif pre(mode) == 1 and t_coast >= hold_s and not resumable then
      mode = 2;   // a drive whose bus has recovered is only waiting out its interlocks, not faulted
    elseif pre(mode) == 1 and resumable and t_off >= max(resume_s, min_off_s) then
      mode = 0;
    elseif pre(mode) == 2 and v_sense_pu > 0.9 and resumable and t_off >= max(fault_restart_s, min_off_s) then
      mode = 0;
    else
      mode = pre(mode);
    end if;
  end when;

  run_frac = if mode == 0 then 1.0 else 0.0;
  stopped = mode <> 0;
  faulted = mode == 2;
  p_grid_w = p_in_w;
end VfdClass;

model RideThroughCore
  "Rack-level data center ride-through: grid -> PSU -> 48 V busbar -> servers, with BBU
   backup and staged cooling trips. Averaged (RMS) power-balance model; see
   Parameter_Table.md for every value and its provenance."

  // ===================== Scenario parameters (set per run via the FMU) =====================
  // Reclose sequence: up to N_MAX dips, time-ordered and non-overlapping (scenario.py enforces it).
  // Unused slots are parked at 1e9 s. Real events: 6 faults over 82 s (NERC 2024, PJM 2026).
  constant Integer N_MAX = 8;
  parameter Integer n_dips = 1 "Number of dips actually used";
  parameter Real dip_start_s[N_MAX] = cat(1, {1.0}, fill(1.0e9, N_MAX - 1)) "Start of each dip";
  parameter Real dip_dur_s[N_MAX] = fill(0.083, N_MAX) "Duration of each dip";
  parameter Real dip_depth_pu[N_MAX] = fill(0.60, N_MAX) "Retained voltage during each dip";
  // Post-fault shape, measured from ANDES fault studies (scripts/andes_dips.py).
  // A square dip assumes voltage snaps back instantly and never overshoots; neither holds.
  parameter Real recovery_tau_s = 0.065 "Time constant of the climb back after clearing";
  parameter Real overshoot_pu = 0.06 "Peak above nominal after clearing";

  parameter Real p_it_rated_w = 120e6 "Facility IT rating";
  parameter Real workload = 0.85 "Fraction of IT rating";
  parameter Real swing_size_frac = 0.2;
  parameter Real swing_freq_hz = 1.0;
  parameter Real swing_phase = 0.0;

  parameter Real supply_voltage_v = 277.0 "PSU input, line-to-neutral";
  parameter Real z_total_pu = 0.1975 "Sum of the chain's transformer impedances, each on its OWN rating";
  // A transformer's %Z is on its own MVA. Converting to the facility's load base multiplies by (facility load / installed
  // transformer capacity), i.e. by how heavily the chain is loaded; summing own-base percentages implicitly assumes 100%
  // loading and overstates the voltage drop. Installed capacity is not public: G, 0.5-1.0.
  parameter Real chain_loading_frac = 0.75 "Facility load / installed transformer capacity";
  parameter Boolean psu_cap_datasheet = true "PSU delivers rated power until lockout (false = old per-unit-voltage scaling, kept for ablation)";

  parameter Real cooling_share_25c = 0.30;
  parameter Real outdoor_temp_c = 38.0;
  parameter Real cooling_compressor_frac = 0.40 "Compressor share of cooling load";
  parameter Real cooling_fan_frac = 0.35;
  // Cooling drives. A share of each class is VFD-driven (DC-link physics, VfdClass); the rest is
  // direct-on-line behind contactors, which follow the NERC staged-trip table.
  parameter Real cooling_vfd_frac = 0.5 "Share of each cooling class on VFDs";
  parameter Real cooling_ll_v = 480.0 "Cooling plant line-to-line voltage";
  parameter Real vfd_dc_uv_trip_pu = 0.70 "Drive DC-bus undervoltage level, fraction of nominal";
  parameter Real cooling_ride_through_s = 0.2 "Coast time before a drive declares a fault (ATV320 undervolt time-out)";
  parameter Boolean vfd_kinetic = false "Drives configured to ride through on motor inertia (ATV320 DC Maintain; factory default off)";
  parameter Real drive_restart_s = 1.0 "Restart wait after a drive fault (auto-restart ladder starts at 1 s; large = manual reset)";
  parameter Real compressor_restart_s = 180.0 "Compressor anti-short-cycle off-time (G: ~100 s to several minutes, OEM-set)";
  parameter Real vfd_c_uf_per_kw = 130.0 "DC-link capacitance per kW (G)";
  parameter Real x_over_r = 10.0 "Transformer-chain X/R";
  parameter Real load_pf = 0.9 "Facility power factor, sets how much of |Z| becomes real voltage drop";

  parameter Real battery_soc0 = 0.95;
  parameter Real battery_age_yr = 3.0;

  parameter Real psu_restart_delay_s = 0.0 "Sampled, not drawn internally (see scenario.py)";
  parameter Real handback_delay_s = 0.2;
  parameter Real ramp_back_s = 0.3 "Time to return to full grid draw after the PSUs restart";

  // Grid-side transfer. A legacy UPS leaves the grid early on a shallow sag; a compliant
  // design rides through. This is the knob that separates the two reference presets.
  parameter Real transfer_threshold_pu = 0.85;
  parameter Real transfer_delay_s = 0.02;

  // Sag-counting transfer (NERC Large Load Loss review: sites transferred to backup on "N sags
  // in T seconds" and stayed off until manual reset; after the 2024 event some sites lengthened
  // the time a dip must last to be counted and raised N). count_n = 0 disables it.
  parameter Integer count_n = 0 "Counted sags within the window that trigger transfer (0 = off, max 5)";
  parameter Real count_threshold_pu = 0.90 "Voltage below which a sag is being timed";
  parameter Real count_min_dur_s = 0.0 "A sag counts only once it has lasted this long";
  parameter Real count_window_s = 60.0 "Sliding window the counted sags must fall inside";

  // Facility undervoltage relay. NOGRR 2.14(4) requires protection be set to equipment
  // tolerance rather than to the envelope edge, so a compliant design picks up below
  // 0.20 pu while a legacy one sits at 0.85 and disconnects inside the envelope.
  // Fraction of facility load behind legacy latching protection. Real facilities run mixed
  // equipment vintages: some racks on older gear that trips and needs a manual reset, some
  // on modern ride-through capable gear. With this at 1.0 the whole facility trips together,
  // which is the behaviour the model had before.
  parameter Real legacy_load_frac = 1.0;

  parameter Real relay_pickup_pu = 0.15;
  parameter Real relay_delay_s = 0.5;
  parameter Real legacy_open_delay_s = 0.05 "Breaker/contactor opening time after the relay operates (G: 2-5 cycles; 3 cycles = 50 ms)";

  parameter Real restart_surge_x = 1.15 "Peak server draw on restart, times pre-fault";
  parameter Real restart_surge_s = 0.5 "Decay time constant of the restart surge";

  // PSUs do not trip as one block. The 172 V figure is nominal: manufacturing spread,
  // per-rack feeder differences and (in reality) unbalanced faults mean the fleet sheds
  // progressively. Unsourced -- sampled so sensitivity analysis can judge whether it matters.
  parameter Real psu_trip_spread_frac = 0.04 "Half-width of the fleet trip threshold spread";
  parameter Real psu_uv_delay_s = 0.0 "Undervoltage must persist this long before a PSU latches off (G: not in the datasheet; 0 = trips as fast as the 1 ms sense filter)";

  // Fraction of facility load sitting on phases that actually dip. ORv3 PSUs connect
  // line-to-neutral, so a single-phase fault leaves two thirds of the fleet at nominal
  // voltage. The real ERCOT events were unbalanced (1-2 of 3 phases below 0.7 pu), which
  // is why a balanced model over-predicts load loss. 1.0 = balanced three-phase fault.
  parameter Real faulted_phase_frac = 1.0;

  parameter Real battery_temp_c = 25.0 "Server hall temperature, an initial condition";
  parameter Integer shelves_per_rack = 6;
  parameter Integer bbu_modules_per_rack = 12;

  // ===================== Fixed constants (Parameter_Table.md) =====================
  constant Real PSU_RATED_W = 3000.0;
  constant Real SHELF_RATED_W = 18000.0;
  constant Real BBU_MODULE_W = 3000.0;
  constant Real BBU_MODULE_WH = 200.0;
  constant Real PSU_UV_V = 172.0;
  constant Real PSU_RESTART_V = 178.0;
  constant Real PSU_HOLDUP_J = 60.0 "Per PSU";
  constant Real PSU_EFF = 0.965;
  constant Real PSU_TON_BBU_S = 1.0 "Base turn-on; the sampled random delay adds to this";

  constant Real BUS_PSU_V = 50.75;
  constant Real BUS_DROOP_FULL_V = 6.0 "3 V droop at 50% hold-up depletion";
  constant Real BBU_TAKEOVER_V = 48.5;
  constant Real BBU_TAKEOVER_DELAY_S = 0.002;
  constant Real BBU_BUS_V = 48.0;
  constant Real IT_FLOOR_V = 46.0 "Servers lose power below this";

  constant Real COOL_S1_V = 0.70;
  constant Real COOL_S1_DELAY_S = 0.05;
  constant Real COOL_S1_FRAC = 0.30;
  constant Real COOL_S2_V = 0.60;
  constant Real COOL_S2_DELAY_S = 0.02;
  constant Real COOL_S2_FRAC_COMP = 0.70;
  constant Real COOL_S2_FRAC_FANPUMP = 0.50;
  constant Real COOL_RECONNECT_V = 0.50;
  constant Real COOL_RECONNECT_S = 0.25;

  constant Real SWING_SLEW_PU_S = 1.9;

  // ===================== Derived sizing =====================
  final parameter Real t_clear_s[N_MAX] = {dip_start_s[k] + dip_dur_s[k] for k in 1:N_MAX};
  final parameter Real cooling_share =
    max(0.4 * cooling_share_25c, cooling_share_25c * (1.0 + 0.04 * (outdoor_temp_c - 25.0)));
  final parameter Real p_cooling_rated_w = cooling_share * p_it_rated_w;
  final parameter Real p_total_rated_w = p_it_rated_w * workload + p_cooling_rated_w;
  final parameter Real n_psu = p_it_rated_w / PSU_RATED_W;
  final parameter Real e_holdup_max_j = n_psu * PSU_HOLDUP_J;
  final parameter Real PSU_UV_HIGH_V = PSU_UV_V * (1.0 + psu_trip_spread_frac);
  final parameter Real PSU_UV_LOW_V = PSU_UV_V * (1.0 - psu_trip_spread_frac);
  constant Real TRIP_TAU_S = 0.001;
  // Capacity derating, Sandia SAND2008-5583 Table 2: 0.74 at 0 C rising to 1.06 at 35 C.
  final parameter Real bat_temp_derate =
    if battery_temp_c >= 25.0 then 1.0 + 0.006 * (battery_temp_c - 25.0)
    else 0.74 + 0.0104 * battery_temp_c;
  final parameter Real bat_derate =
    max(0.3, (1.0 - 0.025 * battery_age_yr) * bat_temp_derate);

  // Rack composition now sizes the backup, so an undersized BBU is a reachable failure:
  // modules deliver 3 kW each, and if that total is below demand the busbar collapses
  // however much energy is in the pack.
  final parameter Real n_racks = p_it_rated_w / (shelves_per_rack * SHELF_RATED_W);
  final parameter Real bbu_power_w = n_racks * bbu_modules_per_rack * BBU_MODULE_W;
  final parameter Real bbu_energy_j =
    n_racks * bbu_modules_per_rack * BBU_MODULE_WH * 3600.0 * bat_derate;
  final parameter Real cooling_pump_frac = max(0.0, 1.0 - cooling_compressor_frac - cooling_fan_frac);

  // VFD-driven share of each cooling class. Inertia constants: NERC Dynamic Load Modeling Table 5.1.
  VfdClass vfd_comp(p_rated_w = p_cooling_rated_w * cooling_compressor_frac * cooling_vfd_frac, h_s = 0.10,
                    uv_trip_pu = vfd_dc_uv_trip_pu, hold_s = cooling_ride_through_s, fault_restart_s = drive_restart_s,
                    min_off_s = compressor_restart_s, kinetic = vfd_kinetic, c_uf_per_kw = vfd_c_uf_per_kw, v_ll_v = cooling_ll_v);
  VfdClass vfd_fan(p_rated_w = p_cooling_rated_w * cooling_fan_frac * cooling_vfd_frac, h_s = 0.50,
                   uv_trip_pu = vfd_dc_uv_trip_pu, hold_s = cooling_ride_through_s, fault_restart_s = drive_restart_s,
                   min_off_s = 0.0, kinetic = vfd_kinetic, c_uf_per_kw = vfd_c_uf_per_kw, v_ll_v = cooling_ll_v);
  VfdClass vfd_pump(p_rated_w = p_cooling_rated_w * cooling_pump_frac * cooling_vfd_frac, h_s = 0.15,
                    uv_trip_pu = vfd_dc_uv_trip_pu, hold_s = cooling_ride_through_s, fault_restart_s = drive_restart_s,
                    min_off_s = 0.0, kinetic = vfd_kinetic, c_uf_per_kw = vfd_c_uf_per_kw, v_ll_v = cooling_ll_v);

  // Busbar voltage is an exact algebraic function of the hold-up energy state, so the
  // busbar-side thresholds can be expressed against that state directly. This keeps the BBU
  // and server-power-loss decisions out of the grid-side algebraic loop entirely.
  final parameter Real E_FRAC_BBU = 1.0 - (BUS_PSU_V - BBU_TAKEOVER_V) / BUS_DROOP_FULL_V;
  final parameter Real E_FRAC_IT_FLOOR = 1.0 - (BUS_PSU_V - IT_FLOOR_V) / BUS_DROOP_FULL_V;

  constant Real SENSE_TAU_S = 0.001 "Protection sensing lag";
  // Fraction of |Z| that becomes real voltage drop: R/|Z|*cos(phi) + X/|Z|*sin(phi); 0.523 at X/R = 10, pf = 0.9.
  final parameter Real Z_EFF_FACTOR = (load_pf + x_over_r * sqrt(1.0 - load_pf * load_pf)) / sqrt(1.0 + x_over_r * x_over_r);
  constant Real OVERSHOOT_PEAK_X = 4.0 "Overshoot peaks this many recovery time constants after clearing";

  // ===================== Variables =====================
  Real v_source_pu "Source voltage, before facility impedance";
  Real v_recovering "Post-clearing recovery shape";
  Real dt_recover "Time since the most recent clearing";
  Integer k_started(start = 0, fixed = true) "Dips started";
  Integer k_cleared(start = 0, fixed = true) "Dips already cleared";
  Real v_active "Retained voltage of the dip in progress (1.0 if none)";
  Real depth_last "Depth of the most recently cleared dip";
  // Constant-power load behind a series impedance gives a quadratic in voltage with two real
  // roots. Start near the physical (high-voltage) root or the solver latches onto the spurious
  // collapsed-voltage branch, which looks plausible but inverts the physics entirely.
  Real v_sdp_pu(start = 1.0) "Voltage at the Service Delivery Point";
  Real v_psu_in_v "PSU input voltage";
  Real z_drop_pu "Chain impedance on the facility base, real part";
  Real v_disc "Discriminant of the voltage quadratic; negative = no operating point";
  Real v_branch_margin "Voltage above the quadratic's midpoint; negative = on the collapsed root";
  // Protection senses a filtered voltage, not an instantaneous one. This is required by
  // NOGRR 282 2.14(5) ("filtered quantities or time delays to prevent misoperation") and is
  // also what breaks the grid-side algebraic loop: a when-equation cannot sit inside a
  // nonlinear system, but it can act on a state. Decisions faster than SENSE_TAU_S are not
  // resolved by this model, which is inherent to the averaged-RMS approach.
  Real v_sense_pu(start = 1.0) "Filtered Service Delivery Point voltage, for protection";
  Real e_frac "Hold-up energy remaining, fraction";
  Real p_surge_w "Restart surge above baseline";
  Real psu_trip_demand "Fraction of the fleet below its own trip threshold right now";
  Real psu_trip_demand_eff "Trip demand after the lockout debounce";
  Real t_psu_uv(start = 0, fixed = true) "Time undervoltage has persisted";
  Real psu_tripped_frac(start = 0, fixed = true) "Fraction latched off";
  Real psu_online_frac "Fraction still supplying";
  Real ramp_gate "Ramp-back gate, 0 to 1, after the PSUs restart";
  Boolean facility_connected(start = true, fixed = true) "False only if the whole facility is off";
  Boolean legacy_cmd(start = false, fixed = true) "Relay has issued its trip command";
  Real t_open(start = 0, fixed = true) "Time since the trip command";
  Boolean legacy_tripped(start = false, fixed = true) "Legacy portion latched off";
  Real facility_available_frac "Fraction of facility load still able to draw";
  Boolean transfer_demanded(start = false, fixed = true) "Grid-side transfer to backup";
  Real t_sag(start = 0, fixed = true) "Time the present sag has lasted";
  Real count_t1(start = -1.0e9, fixed = true) "Times of the five most recent counted sags, newest first";
  Real count_t2(start = -1.0e9, fixed = true);
  Real count_t3(start = -1.0e9, fixed = true);
  Real count_t4(start = -1.0e9, fixed = true);
  Real count_t5(start = -1.0e9, fixed = true);
  Integer n_in_window "Counted sags inside the sliding window";
  Boolean count_transfer(start = false, fixed = true) "Latched: sag count reached, stays on backup until manual reset";
  Real t_relay(start = 0, fixed = true);
  Real t_transfer(start = 0, fixed = true);
  Real t_restore(start = -1, fixed = true);
  Real t_psu_up(start = 1.0e3, fixed = true) "Seconds since the PSUs last (re)started; starts large so the run begins at full draw, not mid-ramp";

  Real p_server_w "Server/IT demand";
  Real p_swing_w(start = 0, fixed = true);
  Real p_swing_target_w;

  Real p_cooling_w "Cooling demand after trips";
  Real cooling_available "Fraction of cooling still running";

  Real e_holdup_j(start = 0, fixed = false) "PSU hold-up energy store";
  Real v_bus_v "48 V busbar";
  Real p_psu_w "Power the PSUs deliver to the busbar";
  Real p_bbu_w "Power the BBU delivers";
  Real soc(start = battery_soc0, fixed = true);

  Real p_grid_w "Active power drawn from the grid";
  Real i_grid_pu "Grid current as a fraction of maximum normal";

  // Discrete state
  Boolean psu_enabled(start = true, fixed = true);
  Boolean bbu_active(start = false, fixed = true);
  Boolean cool_s1_tripped(start = false, fixed = true);
  Boolean cool_s2_tripped(start = false, fixed = true);
  Boolean servers_lost_power(start = false, fixed = true);

  // Timers
  Real t_bus_low(start = 0, fixed = true);
  Real t_bus_ok(start = 0, fixed = true);
  Real t_cool_s1(start = 0, fixed = true);
  Real t_cool_s2(start = 0, fixed = true);
  Real t_cool_ok(start = 0, fixed = true);
  Real t_dol_off(start = 0, fixed = true) "Time the contactor-driven loads have been tripped";
  Real v_rect_pu "Effective drive-rectifier supply voltage under an unbalanced dip";
  Real p_dol_w "Contactor-driven cooling demand";
  Real p_vfd_w "VFD-driven cooling demand";
  Boolean vfd_stopped_any;
  Boolean vfd_faulted_any;
  Real t_psu_down(start = 0, fixed = true);

initial equation
  e_holdup_j = e_holdup_max_j;

equation
  // ---------------- Grid ----------------
  // Realistic dip shape. During a fault the voltage sits at the retained level; after
  // clearing it climbs back exponentially and overshoots before settling. The overshoot
  // term peaks at overshoot_pu one time constant after clearing, then decays to zero, so
  // the expression is continuous and tends to 1.0.
  //
  //   v(dt) = v_dip + (1 - v_dip)(1 - e^(-dt/tau)) + A (dt/tau) e^(1 - dt/tau)
  //
  // This matters for grading: ANDES runs show overshoot reaching 1.124 pu, which is above
  // NOGRR's 1.10 continuous band and into the tier demanding 2.0 s of ride-through. A
  // square dip cannot produce that failure mode at all.
  // Event-driven bookkeeping. Written as `when` on time rather than as reductions over the
  // arrays: reductions hide the time comparisons from the solver, which then steps straight
  // past a dip (the first attempt produced a one-sample dip). Dips are time-ordered, so the
  // counters identify the dip in progress and the last one cleared.
  when time >= dip_start_s[min(pre(k_started) + 1, N_MAX)] and pre(k_started) < n_dips then
    k_started = pre(k_started) + 1;
  end when;
  when time >= t_clear_s[min(pre(k_cleared) + 1, N_MAX)] and pre(k_cleared) < n_dips then
    k_cleared = pre(k_cleared) + 1;
  end when;
  v_active = if k_started > k_cleared then dip_depth_pu[max(k_started, 1)] else 1.0;
  dt_recover = if k_cleared >= 1 then time - t_clear_s[max(k_cleared, 1)] else 0.0;
  depth_last = if k_cleared >= 1 then dip_depth_pu[max(k_cleared, 1)] else 1.0;

  // Written as a decaying departure from nominal plus an overshoot pulse, so the peak
  // actually lands near 1 + overshoot_pu. The pulse peaks at OVERSHOOT_PEAK_X time
  // constants, by which point the climb term has decayed to ~2% -- peaking it earlier
  // (at 1 tau, as first written) merely speeds the recovery and never exceeds nominal.
  //
  // The ANDES library measures overshoot magnitude but not its timing, so the 4x factor
  // is an assumption; see Parameter_Table.md.
  v_recovering = 1.0
    + (depth_last - 1.0) * exp(-dt_recover / recovery_tau_s)
    + overshoot_pu * (dt_recover / (OVERSHOOT_PEAK_X * recovery_tau_s))
      * exp(1.0 - dt_recover / (OVERSHOOT_PEAK_X * recovery_tau_s));

  v_source_pu =
    if k_started > k_cleared then v_active
    elseif k_cleared >= 1 then v_recovering
    else 1.0;

  // Voltage drop across the transformer chain, referenced to the rated operating point.
  //
  // Two corrections over a naive v = v_src - Z*i*v_src:
  //  1. Drop is taken against (i - 1), not i. Real facilities tap-regulate so that nominal
  //     voltage appears at the PSU at rated load; the impedance governs the *change* when
  //     current departs from rated, which is what a dip causes.
  //  2. Z_EFF_FACTOR converts |Z| into an actual voltage drop. The chain is mostly reactive
  //     (X/R ~ 10) against a ~0.9 pf load, so drop ~ I*(R*cos(phi) + X*sin(phi)) is roughly
  //     half of I*|Z|. Without this the model showed a 25% drop at idle.
  //
  // Note the summed transformer percentages are each on their own MVA base; converting them
  // to a common facility base is still open (Parameter_Table.md, open item 8).
  v_sdp_pu = v_source_pu - z_drop_pu * (i_grid_pu - 1.0) * v_source_pu;
  z_drop_pu = Z_EFF_FACTOR * z_total_pu * chain_loading_frac;
  // Constant-power load behind a series impedance: v^2 - vs(1+k)v + k vs p = 0 has two roots (k = z_drop_pu, p = grid power in
  // per unit). Only the larger is physical. These two signals let the runner reject a run whose solver sat on the collapsed
  // root or lost the real solution altogether (no operating point: voltage collapse), instead of grading it as if valid.
  v_disc = v_source_pu * v_source_pu * (1.0 + z_drop_pu) ^ 2 - 4.0 * z_drop_pu * v_source_pu * (p_grid_w / p_total_rated_w);
  v_branch_margin = v_sdp_pu - 0.5 * v_source_pu * (1.0 + z_drop_pu);
  v_psu_in_v = supply_voltage_v * max(v_sdp_pu, 0.0);
  der(v_sense_pu) = (v_sdp_pu - v_sense_pu) / SENSE_TAU_S;
  e_frac = max(0.0, min(1.0, e_holdup_j / e_holdup_max_j));

  // ---------------- Server / AI load ----------------
  // Slew-limited square wave: periodic 0.2-3 Hz synchronised swing, 1.9 pu/s ramp.
  p_swing_target_w = 0.5 * swing_size_frac * p_it_rated_w
    * (if sin(6.283185307179586 * swing_freq_hz * time + swing_phase) >= 0 then 1.0 else -1.0);
  der(p_swing_w) = max(-SWING_SLEW_PU_S * p_it_rated_w,
                   min( SWING_SLEW_PU_S * p_it_rated_w,
                        (p_swing_target_w - p_swing_w) / 0.001));

  // Capture the instant power is restored so the surge decays from there.
  when (not servers_lost_power) and pre(servers_lost_power) then
    t_restore = time;
  end when;
  p_surge_w = if t_restore >= 0.0 and time >= t_restore then
                (restart_surge_x - 1.0) * p_it_rated_w * exp(-(time - t_restore) / restart_surge_s)
              else 0.0;

  // Ramp back to full grid draw rather than snapping, once the PSUs are supplying again.
  der(t_psu_up) = if psu_enabled then 1.0 else 0.0;
  // The ramp restarts after a hand-back as well as after a PSU restart: a UPS returning
  // load to the grid ramps it rather than stepping it, which is why the measured product
  // recovery is hand-back plus ramp rather than hand-back alone.
  when not psu_enabled or (pre(bbu_active) and not bbu_active) then
    reinit(t_psu_up, 0);
  end when;
  ramp_gate = min(1.0, t_psu_up / max(ramp_back_s, 1e-3));

  p_server_w = if servers_lost_power then 0.0
               else ((workload * p_it_rated_w + p_swing_w) * ramp_gate + p_surge_w)
                    * facility_available_frac;

  // ---------------- Cooling, staged NERC Table 5.1 trips ----------------
  der(t_cool_s1) = if v_sense_pu < COOL_S1_V then 1.0 else 0.0;
  der(t_cool_s2) = if v_sense_pu < COOL_S2_V then 1.0 else 0.0;
  der(t_cool_ok) = if v_sense_pu > COOL_RECONNECT_V then 1.0 else 0.0;

  when v_sense_pu >= COOL_S1_V then
    reinit(t_cool_s1, 0);
  end when;
  when v_sense_pu >= COOL_S2_V then
    reinit(t_cool_s2, 0);
  end when;
  when v_sense_pu <= COOL_RECONNECT_V then
    reinit(t_cool_ok, 0);
  end when;

  // Contactor-driven loads (the NERC staged-trip table). A tripped class comes back when its own
  // restart rule allows: fans and pumps once voltage has held above the reconnect level, compressors
  // only after the anti-short-cycle off-time AND recovered voltage. Both flags clear together so a
  // later dip in a reclose sequence can trip them again (they used to latch for the whole run).
  der(t_dol_off) = if cool_s1_tripped or cool_s2_tripped then 1.0 else 0.0;
  when not (cool_s1_tripped or cool_s2_tripped) then
    reinit(t_dol_off, 0);
  end when;
  when t_cool_s1 > COOL_S1_DELAY_S then
    cool_s1_tripped = true;
  elsewhen t_dol_off > compressor_restart_s and v_sense_pu > 0.9 then   // timer only runs while tripped
    cool_s1_tripped = false;
  end when;
  when t_cool_s2 > COOL_S2_DELAY_S then
    cool_s2_tripped = true;
  elsewhen t_dol_off > compressor_restart_s and v_sense_pu > 0.9 then   // timer only runs while tripped
    cool_s2_tripped = false;
  end when;

  cooling_available =
    (if cool_s2_tripped then (1.0 - COOL_S2_FRAC_COMP)
     elseif cool_s1_tripped then (1.0 - COOL_S1_FRAC)
     else 1.0) * cooling_compressor_frac
    + (if cool_s2_tripped and t_cool_ok < COOL_RECONNECT_S then (1.0 - COOL_S2_FRAC_FANPUMP)
       elseif cool_s1_tripped and t_cool_ok < COOL_RECONNECT_S then (1.0 - COOL_S1_FRAC)
       else 1.0) * (cooling_fan_frac + cooling_pump_frac);

  p_dol_w = p_cooling_rated_w * (1.0 - cooling_vfd_frac) * cooling_available;
  // A three-phase diode rectifier's DC bus follows the envelope of its line-to-line voltages, so an
  // unbalanced dip is far milder for a drive than the positive-sequence voltage suggests: with one
  // phase down, one line-to-line pair is untouched; with two down, the other two pairs sit at about
  // (1 + v)/2. The PSU path already accounts for unbalance (faulted_phase_frac); the first draft of
  // the drive model did not, which made facility B (one phase at 0.67 pu) lose all its drives.
  v_rect_pu = if faulted_phase_frac < 0.5 then max(v_sense_pu, 1.0)
              elseif faulted_phase_frac < 0.9 then 0.5 * (1.0 + v_sense_pu)
              else v_sense_pu;
  vfd_comp.v_sense_pu = v_rect_pu;
  vfd_fan.v_sense_pu = v_rect_pu;
  vfd_pump.v_sense_pu = v_rect_pu;
  p_vfd_w = vfd_comp.p_grid_w + vfd_fan.p_grid_w + vfd_pump.p_grid_w;
  vfd_stopped_any = vfd_comp.stopped or vfd_fan.stopped or vfd_pump.stopped;
  vfd_faulted_any = vfd_comp.faulted or vfd_fan.faulted or vfd_pump.faulted;

  p_cooling_w = (p_dol_w + p_vfd_w) * facility_available_frac;

  // ---------------- Facility relay and grid-side transfer ----------------
  der(t_relay) = if v_sense_pu < relay_pickup_pu then 1.0 else 0.0;
  when v_sense_pu >= relay_pickup_pu then
    reinit(t_relay, 0);
  end when;
  // Latching: a tripped facility stays disconnected for the rest of the run, which is what
  // NOGRR 2.14(6) is about -- no automatic re-closure on a sag count.
  // The relay protects the legacy portion only; the modern portion rides through.
  // The relay's operate delay and the breaker's mechanical opening time are separate. Once the relay has operated, its trip
  // command seals in (voltage recovering does not recall it); the load stays connected, drawing from the depressed grid, until the
  // contacts open. Opening time of 2-5 cycles is standard breaker/contactor practice. The first version opened the load the
  // instant the relay operated, which removed the facility's sustained overcurrent during the dip.
  when t_relay > relay_delay_s + 1.0e-6 then
    legacy_cmd = true;
  end when;
  der(t_open) = if legacy_cmd then 1.0 else 0.0;
  when t_open > legacy_open_delay_s + 1.0e-6 then
    legacy_tripped = true;
  end when;
  facility_available_frac =
    (1.0 - legacy_load_frac) + legacy_load_frac * (if legacy_tripped then 0.0 else 1.0);
  // NOGRR grades whether the LEL stayed *connected*. Partial load loss is not
  // disconnection, so this is false only when nothing is left drawing.
  facility_connected = facility_available_frac > 0.01;

  der(t_transfer) = if v_sense_pu < transfer_threshold_pu then 1.0 else 0.0;
  when v_sense_pu >= transfer_threshold_pu then
    reinit(t_transfer, 0);
  end when;

  // Sag counter. A sag is timed while the sensed voltage is below the counting threshold and
  // counted once, the instant it has lasted count_min_dur_s; the timer restarts when voltage
  // returns. Counted-sag times shift through five slots, and the count inside the sliding
  // window is read directly from them.
  der(t_sag) = if v_sense_pu < count_threshold_pu then 1.0 else 0.0;
  when v_sense_pu >= count_threshold_pu then
    reinit(t_sag, 0);
  end when;
  // The epsilon matters: with count_min_dur_s = 0 the timer restarts at exactly 0, and a
  // threshold crossing that starts on the threshold is not detected, so only the first sag counted.
  when t_sag > count_min_dur_s + 1.0e-6 then
    count_t1 = time;
    count_t2 = pre(count_t1);
    count_t3 = pre(count_t2);
    count_t4 = pre(count_t3);
    count_t5 = pre(count_t4);
  end when;
  n_in_window = (if time - count_t1 <= count_window_s then 1 else 0)
              + (if time - count_t2 <= count_window_s then 1 else 0)
              + (if time - count_t3 <= count_window_s then 1 else 0)
              + (if time - count_t4 <= count_window_s then 1 else 0)
              + (if time - count_t5 <= count_window_s then 1 else 0);
  when count_n > 0 and n_in_window >= count_n then
    count_transfer = true;
  end when;

  // Transfer is demanded by either element. The count element latches: NOGRR 282 2.14(6) is
  // about exactly this -- no automatic re-closure on a sag count -- so it holds for the run.
  when t_transfer > transfer_delay_s or count_transfer then
    transfer_demanded = true;
  elsewhen v_sense_pu > transfer_threshold_pu and psu_enabled and not count_transfer then
    transfer_demanded = false;
  end when;

  // ---------------- PSU ----------------
  der(t_psu_down) = if psu_tripped_frac > 0.01 then 1.0 else 0.0;
  when psu_tripped_frac < 0.01 then
    reinit(t_psu_down, 0);
  end when;

  // Fraction of the fleet whose own threshold is above the present voltage.
  psu_trip_demand = max(0.0, min(1.0,
    (PSU_UV_HIGH_V - supply_voltage_v * v_sense_pu) / (PSU_UV_HIGH_V - PSU_UV_LOW_V)));

  // Ratchets up only: a tripped PSU stays off until the restart conditions are met, so the
  // fleet does not follow voltage back up instantaneously.
  // Real PSUs keep drawing constant power from the AC until their lockout debounce expires, which is what produces the 150-160%
  // facility current seen in the ERCOT events; a model that sheds load within the 1 ms sense filter cannot show it.
  der(t_psu_uv) = if psu_trip_demand > 0.0 then 1.0 else 0.0;
  when psu_trip_demand <= 0.0 then
    reinit(t_psu_uv, 0);
  end when;
  psu_trip_demand_eff = if t_psu_uv > psu_uv_delay_s + 1.0e-6 then psu_trip_demand else 0.0;
  der(psu_tripped_frac) = max(0.0, (psu_trip_demand_eff - psu_tripped_frac) / TRIP_TAU_S);
  // Only the faulted-phase portion of the fleet can trip; the rest never sees the dip.
  psu_online_frac = (1.0 - faulted_phase_frac) + faulted_phase_frac * (1.0 - psu_tripped_frac);
  psu_enabled = psu_online_frac > 0.5;

  when supply_voltage_v * v_sense_pu > PSU_RESTART_V
      and t_psu_down > PSU_TON_BBU_S + psu_restart_delay_s then
    reinit(psu_tripped_frac, 0.0);
  end when;

  // PSUs deliver what they can; the shortfall drains hold-up energy, then the BBU.
  // Once the facility transfers to backup, the server load comes off the battery and the
  // PSUs stop pulling it from the grid. This is the mechanism ERCOT exists to worry about --
  // demand vanishing from the grid, as in the Virginia events -- and the model previously
  // could not express it: the BBU only filled the shortfall when PSUs could not supply, so
  // a transfer left grid draw unchanged.
  p_psu_w = if bbu_active and soc > 0 then 0.0
            else min(p_server_w, psu_online_frac * n_psu * PSU_RATED_W *
                   (if psu_cap_datasheet then 1.0 else max(v_sdp_pu, 0.0)));
  // psu_cap_datasheet: the Advanced Energy ORv3 3 kW datasheet rates the unit at 3 kW over the whole 180-305 VAC input range and
  // specifies an undervoltage lockout at 172 VAC -- full power down to the lockout, then shutdown, which the trip logic above
  // already models. The old per-unit scaling (0.8 pu -> 80% capability) had no source. No derating between 172 and 180 V is
  // documented, so none is applied.

  der(e_holdup_j) =
    if psu_enabled and (bbu_active or p_psu_w >= p_server_w) then
      max(0.0, (e_holdup_max_j - e_holdup_j) / 0.05)
    else
      -(p_server_w - p_psu_w - p_bbu_w);

  // Busbar droops as hold-up depletes; the BBU clamps it once it takes over.
  v_bus_v = if bbu_active and soc > 0 then BBU_BUS_V
            else BUS_PSU_V - BUS_DROOP_FULL_V * (1.0 - max(0.0, min(1.0, e_holdup_j / e_holdup_max_j)));

  // ---------------- BBU ----------------
  der(t_bus_low) = if e_frac < E_FRAC_BBU then 1.0 else 0.0;
  // Hand back only once the PSUs are actually supplying the busbar again. Ticking this
  // while the BBU is carrying the load hands back to nothing during the PSU restart
  // delay, which dropped the servers after the dip had already cleared.
  der(t_bus_ok) = if psu_enabled and not transfer_demanded then 1.0 else 0.0;

  when e_frac >= E_FRAC_BBU then
    reinit(t_bus_low, 0);
  end when;
  when transfer_demanded or not psu_enabled then
    reinit(t_bus_ok, 0);
  end when;

  when t_bus_low > BBU_TAKEOVER_DELAY_S or transfer_demanded then
    bbu_active = true;
  elsewhen t_bus_ok > handback_delay_s then
    bbu_active = false;
  end when;

  // Modules cannot deliver more than their rated power regardless of stored energy.
  // Carrying the whole server load, capped by installed module power.
  p_bbu_w = if bbu_active and soc > 0 then min(bbu_power_w, p_server_w) else 0.0;
  der(soc) = -p_bbu_w / bbu_energy_j;

  when e_frac < E_FRAC_IT_FLOOR and not bbu_active then
    servers_lost_power = true;
  elsewhen e_frac > E_FRAC_BBU and psu_enabled then
    servers_lost_power = false;
  end when;

  // ---------------- Grid-side totals ----------------
  p_grid_w = p_psu_w / PSU_EFF + p_cooling_w;
  // Constant-power behaviour: current rises as voltage falls.
  i_grid_pu = if v_sdp_pu > 0.01 then (p_grid_w / p_total_rated_w) / v_sdp_pu else 0.0;

  annotation(experiment(StartTime = 0, StopTime = 15, Tolerance = 1e-6, Interval = 1e-3));
end RideThroughCore;
