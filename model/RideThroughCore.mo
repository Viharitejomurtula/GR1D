model RideThroughCore
  "Rack-level data center ride-through: grid -> PSU -> 48 V busbar -> servers, with BBU
   backup and staged cooling trips. Averaged (RMS) power-balance model; see
   Parameter_Table.md for every value and its provenance."

  // ===================== Scenario parameters (set per run via the FMU) =====================
  parameter Real dip_depth_pu = 0.60 "Retained voltage during the dip";
  parameter Real dip_start_s = 1.0;
  parameter Real dip_duration_s = 0.083;
  parameter Boolean second_dip = false;
  parameter Real reclose_gap_s = 0.4;
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
  parameter Real z_total_pu = 0.1975 "Transformer chain impedance";

  parameter Real cooling_share_25c = 0.30;
  parameter Real outdoor_temp_c = 38.0;
  parameter Real cooling_compressor_frac = 0.40 "Compressor share of cooling load";
  parameter Real cooling_fan_frac = 0.35;

  parameter Real battery_soc0 = 0.95;
  parameter Real battery_age_yr = 3.0;
  parameter Real bbu_backup_s = 240.0 "Rated backup time at module rating";

  parameter Real psu_restart_delay_s = 0.0 "Sampled, not drawn internally (see scenario.py)";
  parameter Real handback_delay_s = 0.2;

  // ===================== Fixed constants (Parameter_Table.md) =====================
  constant Real PSU_RATED_W = 3000.0;
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
  final parameter Real cooling_share =
    max(0.4 * cooling_share_25c, cooling_share_25c * (1.0 + 0.04 * (outdoor_temp_c - 25.0)));
  final parameter Real p_cooling_rated_w = cooling_share * p_it_rated_w;
  final parameter Real p_total_rated_w = p_it_rated_w * workload + p_cooling_rated_w;
  final parameter Real n_psu = p_it_rated_w / PSU_RATED_W;
  final parameter Real e_holdup_max_j = n_psu * PSU_HOLDUP_J;
  final parameter Real bbu_energy_j = p_it_rated_w * bbu_backup_s
    * max(0.5, 1.0 - 0.025 * battery_age_yr) "Capacity fade with age";
  final parameter Real cooling_pump_frac = max(0.0, 1.0 - cooling_compressor_frac - cooling_fan_frac);

  // Busbar voltage is an exact algebraic function of the hold-up energy state, so the
  // busbar-side thresholds can be expressed against that state directly. This keeps the BBU
  // and server-power-loss decisions out of the grid-side algebraic loop entirely.
  final parameter Real E_FRAC_BBU = 1.0 - (BUS_PSU_V - BBU_TAKEOVER_V) / BUS_DROOP_FULL_V;
  final parameter Real E_FRAC_IT_FLOOR = 1.0 - (BUS_PSU_V - IT_FLOOR_V) / BUS_DROOP_FULL_V;

  constant Real SENSE_TAU_S = 0.001 "Protection sensing lag";
  // R/|Z|*cos(phi) + X/|Z|*sin(phi) at X/R = 10, pf = 0.9.
  constant Real Z_EFF_FACTOR = 0.523 "Fraction of |Z| that becomes real voltage drop";
  constant Real OVERSHOOT_PEAK_X = 4.0 "Overshoot peaks this many recovery time constants after clearing";

  // ===================== Variables =====================
  Real v_source_pu "Source voltage, before facility impedance";
  Real v_recovering "Post-clearing recovery shape";
  Real dt_recover "Time since the most recent clearing";
  Real t_clear1, t_start2, t_clear2;
  // Constant-power load behind a series impedance gives a quadratic in voltage with two real
  // roots. Start near the physical (high-voltage) root or the solver latches onto the spurious
  // collapsed-voltage branch, which looks plausible but inverts the physics entirely.
  Real v_sdp_pu(start = 1.0) "Voltage at the Service Delivery Point";
  Real v_psu_in_v "PSU input voltage";
  // Protection senses a filtered voltage, not an instantaneous one. This is required by
  // NOGRR 282 2.14(5) ("filtered quantities or time delays to prevent misoperation") and is
  // also what breaks the grid-side algebraic loop: a when-equation cannot sit inside a
  // nonlinear system, but it can act on a state. Decisions faster than SENSE_TAU_S are not
  // resolved by this model, which is inherent to the averaged-RMS approach.
  Real v_sense_pu(start = 1.0) "Filtered Service Delivery Point voltage, for protection";
  Real e_frac "Hold-up energy remaining, fraction";

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
  t_clear1 = dip_start_s + dip_duration_s;
  t_start2 = t_clear1 + reclose_gap_s;
  t_clear2 = t_start2 + dip_duration_s;

  dt_recover = if second_dip and time >= t_clear2 then time - t_clear2
               else if time >= t_clear1 then time - t_clear1
               else 0.0;

  // Written as a decaying departure from nominal plus an overshoot pulse, so the peak
  // actually lands near 1 + overshoot_pu. The pulse peaks at OVERSHOOT_PEAK_X time
  // constants, by which point the climb term has decayed to ~2% -- peaking it earlier
  // (at 1 tau, as first written) merely speeds the recovery and never exceeds nominal.
  //
  // The ANDES library measures overshoot magnitude but not its timing, so the 4x factor
  // is an assumption; see Parameter_Table.md.
  v_recovering = 1.0
    + (dip_depth_pu - 1.0) * exp(-dt_recover / recovery_tau_s)
    + overshoot_pu * (dt_recover / (OVERSHOOT_PEAK_X * recovery_tau_s))
      * exp(1.0 - dt_recover / (OVERSHOOT_PEAK_X * recovery_tau_s));

  v_source_pu =
    if time < dip_start_s then 1.0
    elseif time < t_clear1 then dip_depth_pu
    elseif second_dip and time >= t_start2 and time < t_clear2 then dip_depth_pu
    else v_recovering;

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
  v_sdp_pu = v_source_pu - Z_EFF_FACTOR * z_total_pu * (i_grid_pu - 1.0) * v_source_pu;
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

  p_server_w = if servers_lost_power then 0.0
               else workload * p_it_rated_w + p_swing_w;

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

  when t_cool_s1 > COOL_S1_DELAY_S then
    cool_s1_tripped = true;
  end when;
  when t_cool_s2 > COOL_S2_DELAY_S then
    cool_s2_tripped = true;
  end when;

  // Fans and pumps reconnect once voltage recovers; compressors stay off for the run.
  cooling_available =
    (if cool_s2_tripped then (1.0 - COOL_S2_FRAC_COMP)
     elseif cool_s1_tripped then (1.0 - COOL_S1_FRAC)
     else 1.0) * cooling_compressor_frac
    + (if cool_s2_tripped and t_cool_ok < COOL_RECONNECT_S then (1.0 - COOL_S2_FRAC_FANPUMP)
       elseif cool_s1_tripped and t_cool_ok < COOL_RECONNECT_S then (1.0 - COOL_S1_FRAC)
       else 1.0) * (cooling_fan_frac + cooling_pump_frac);

  p_cooling_w = p_cooling_rated_w * cooling_available;

  // ---------------- PSU ----------------
  der(t_psu_down) = if psu_enabled then 0.0 else 1.0;

  when supply_voltage_v * v_sense_pu < PSU_UV_V then
    psu_enabled = false;
    reinit(t_psu_down, 0);
  elsewhen supply_voltage_v * v_sense_pu > PSU_RESTART_V
      and t_psu_down > PSU_TON_BBU_S + psu_restart_delay_s then
    psu_enabled = true;
  end when;

  // PSUs deliver what they can; the shortfall drains hold-up energy, then the BBU.
  p_psu_w = if psu_enabled then min(p_server_w, n_psu * PSU_RATED_W * max(v_sdp_pu, 0.0)) else 0.0;

  der(e_holdup_j) =
    if psu_enabled and p_psu_w >= p_server_w then
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
  der(t_bus_ok) = if psu_enabled and e_frac > E_FRAC_BBU then 1.0 else 0.0;

  when e_frac >= E_FRAC_BBU then
    reinit(t_bus_low, 0);
  end when;
  when e_frac <= E_FRAC_BBU or not psu_enabled then
    reinit(t_bus_ok, 0);
  end when;

  when t_bus_low > BBU_TAKEOVER_DELAY_S then
    bbu_active = true;
  elsewhen t_bus_ok > handback_delay_s then
    bbu_active = false;
  end when;

  p_bbu_w = if bbu_active and soc > 0 then max(0.0, p_server_w - p_psu_w) else 0.0;
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
