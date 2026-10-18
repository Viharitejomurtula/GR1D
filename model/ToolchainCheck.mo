model ToolchainCheck
  "Minimal stand-in for the real model: a battery discharging into a load, with a
   voltage-threshold trip. Exercises the exact Modelica features the physics model
   needs (continuous states, der(), a when-clause event, a time-varying input) so the
   OpenModelica -> FMU -> FMPy path can be proven before the full model is written."

  // --- Parameters (these become FMU inputs we set per scenario) ---
  parameter Real capacity_Ah = 9.0 "Pack capacity";
  parameter Real r0_Ohm = 0.055 "Pack series resistance";
  parameter Real ocv_full_V = 44.0 "Open-circuit voltage at SOC = 1";
  parameter Real ocv_empty_V = 30.0 "Open-circuit voltage at SOC = 0";
  parameter Real load_W = 3000.0 "Constant-power load";
  parameter Real trip_V = 32.0 "Terminal voltage at which the load trips";
  parameter Real soc_start = 0.95 "Initial state of charge";

  // --- States ---
  Real soc(start = soc_start, fixed = true) "State of charge, 0..1";

  // --- Algebraic ---
  Real ocv_V "Open-circuit voltage";
  Real current_A "Discharge current, positive out";
  Real terminal_V "Terminal voltage under load";
  Real power_W "Power actually delivered";
  Boolean tripped(start = false, fixed = true);

equation
  // Linear OCV(SOC). The real model replaces this with a fitted curve.
  ocv_V = ocv_empty_V + (ocv_full_V - ocv_empty_V) * soc;

  // Constant-power load until the trip latches, then nothing.
  power_W = if tripped then 0.0 else load_W;

  // Solve the constant-power/series-resistance node for current.
  current_A = if power_W <= 0.0 then 0.0 else power_W / terminal_V;
  terminal_V = ocv_V - current_A * r0_Ohm;

  der(soc) = -current_A / (3600.0 * capacity_Ah);

algorithm
  // Latching undervoltage trip. The solver finds the exact crossing instant, which is
  // the behaviour we want for BBU takeover and PSU/VFD trips in the real model.
  when terminal_V < trip_V then
    tripped := true;
  end when;

  annotation(experiment(StartTime = 0, StopTime = 15, Tolerance = 1e-6, Interval = 1e-3));
end ToolchainCheck;
