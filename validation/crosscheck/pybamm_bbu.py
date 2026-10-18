"""Cross-check the model's BBU temperature derating against PyBaMM cell models.

The Modelica BBU is an energy bucket: usable energy = 200 Wh x (1 - 0.025*age) x temp_derate(T), with temp_derate taken from Sandia's LFP
table (0.74 at 0 C, 1.06 at 35 C) and applied to NMC packs (Parameter_Table.md flags this as a proxy). This compares that curve with the
delivered-energy ratio vs 25 C from PyBaMM parameter sets: Ecker2015 (Kokam NMC pouch), Marquis2019, NCA_Kim2011 (NCA). Chen2020 (NMC) and
Prada2013 (A123 LFP) are run too, but they show <=3% change from -10 to 35 C at every rate, i.e. they carry no usable temperature response
(an empirical observation from this output, not a claim about their parameter files).
Constant-current discharge to the set's own lower cut-off, isothermal at the stated temperature, SPMe.
LIMITS: not the BBU's cell; max rate 3C (the BBU runs ~8-9C: 3 kW from a 333 Wh nominal pack), where these sets fail to solve or collapse.
Usage: .venv/bin/python validation/crosscheck/pybamm_bbu.py
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pybamm

OUT = pathlib.Path(__file__).with_name("pybamm_bbu.json")
SETS = ("Ecker2015", "Marquis2019", "NCA_Kim2011", "Chen2020", "Prada2013")
TEMPS = (-10.0, 0.0, 10.0, 25.0, 35.0)
RATES = (1.0, 2.0, 3.0)


def model_derate(temp_c: float) -> float:
    """RideThroughCore.mo bat_temp_derate."""
    return 1.0 + 0.006 * (temp_c - 25.0) if temp_c >= 25.0 else 0.74 + 0.0104 * temp_c


def delivered_wh(name: str, temp_c: float, c_rate: float) -> float:
    pv = pybamm.ParameterValues(name)
    tk = temp_c + 273.15
    pv.update({"Ambient temperature [K]": tk, "Initial temperature [K]": tk}, check_already_exists=False)
    vlo = pv["Lower voltage cut-off [V]"]
    sim = pybamm.Simulation(pybamm.lithium_ion.SPMe(options={"thermal": "isothermal"}), parameter_values=pv,
                            experiment=pybamm.Experiment([f"Discharge at {c_rate} C until {vlo} V"]))
    s = sim.solve(initial_soc=1.0)
    return float(np.trapezoid(s["Current [A]"].entries * s["Terminal voltage [V]"].entries, s["Time [s]"].entries) / 3600.0)


def main() -> None:
    rows = []
    for name in SETS:
        for c in RATES:
            wh = {}
            for T in TEMPS:
                try:
                    wh[T] = delivered_wh(name, T, c)
                except Exception:  # noqa: BLE001 -- a failed solve is recorded as missing
                    wh[T] = float("nan")
            ref = wh[25.0]
            rows.append({"set": name, "c_rate": c,
                         "ratio_vs_25c": {str(T): wh[T] / ref for T in TEMPS}})
    OUT.write_text(json.dumps(rows, indent=1))
    print(f"{'set':<12} {'C':>3} | " + " ".join(f"{int(T):>6}C" for T in TEMPS))
    print(f"{'MODEL':<12} {'':>3} | " + " ".join(f"{model_derate(T):7.2f}" for T in TEMPS))
    for r in rows:
        print(f"{r['set']:<12} {r['c_rate']:3.0f} | "
              + " ".join(f"{r['ratio_vs_25c'][str(T)]:7.2f}" for T in TEMPS))


if __name__ == "__main__":
    main()
