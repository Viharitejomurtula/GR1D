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

  // ===================== Variables =====================
  Real v_source_pu "Source voltage, before facility impedance";
  Real v_sdp_pu "Voltage at the Service Delivery Point";
  Real v_psu_in_v "PSU input voltage";

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
  v_source_pu =
    if time >= dip_start_s and time < dip_start_s + dip_duration_s then dip_depth_pu
    elseif second_dip
      and time >= dip_start_s + dip_duration_s + reclose_gap_s
      and time < dip_start_s + 2 * dip_duration_s + reclose_gap_s then dip_depth_pu
    else 1.0;

  // Averaged model: the facility draws roughly constant power, so the voltage drop across
  // the transformer chain scales with the current it pulls.
  v_sdp_pu = v_source_pu - z_total_pu * i_grid_pu * v_source_pu;
  v_psu_in_v = supply_voltage_v * max(v_sdp_pu, 0.0);

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
  der(t_cool_s1) = if v_sdp_pu < COOL_S1_V then 1.0 else 0.0;
  der(t_cool_s2) = if v_sdp_pu < COOL_S2_V then 1.0 else 0.0;
  der(t_cool_ok) = if v_sdp_pu > COOL_RECONNECT_V then 1.0 else 0.0;

  when v_sdp_pu >= COOL_S1_V then
    reinit(t_cool_s1, 0);
  end when;
  when v_sdp_pu >= COOL_S2_V then
    reinit(t_cool_s2, 0);
  end when;
  when v_sdp_pu <= COOL_RECONNECT_V then
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

  when v_psu_in_v < PSU_UV_V then
    psu_enabled = false;
    reinit(t_psu_down, 0);
  elsewhen v_psu_in_v > PSU_RESTART_V
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
  der(t_bus_low) = if v_bus_v < BBU_TAKEOVER_V then 1.0 else 0.0;
  der(t_bus_ok) = if v_bus_v > BBU_TAKEOVER_V then 1.0 else 0.0;

  when v_bus_v >= BBU_TAKEOVER_V then
    reinit(t_bus_low, 0);
  end when;
  when v_bus_v <= BBU_TAKEOVER_V then
    reinit(t_bus_ok, 0);
  end when;

  when t_bus_low > BBU_TAKEOVER_DELAY_S then
    bbu_active = true;
  elsewhen t_bus_ok > handback_delay_s then
    bbu_active = false;
  end when;

  p_bbu_w = if bbu_active and soc > 0 then max(0.0, p_server_w - p_psu_w) else 0.0;
  der(soc) = -p_bbu_w / bbu_energy_j;

  when v_bus_v < IT_FLOOR_V then
    servers_lost_power = true;
  elsewhen v_bus_v > BBU_TAKEOVER_V and psu_enabled then
    servers_lost_power = false;
  end when;

  // ---------------- Grid-side totals ----------------
  p_grid_w = p_psu_w / PSU_EFF + p_cooling_w;
  // Constant-power behaviour: current rises as voltage falls.
  i_grid_pu = if v_sdp_pu > 0.01 then (p_grid_w / p_total_rated_w) / v_sdp_pu else 0.0;

  annotation(experiment(StartTime = 0, StopTime = 15, Tolerance = 1e-6, Interval = 1e-3));
end RideThroughCore;
