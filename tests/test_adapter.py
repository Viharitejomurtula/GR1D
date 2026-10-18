"""Tests for ridethrough.adapter: each conversion from factor-network quantities to simulator roots.

What this file is
    One test group per conversion (load, dip depth, age -> capacitance, temperature -> battery resistance,
    temperature -> converter derating). Expected values are read independently from the S-matrix and
    master.csv files or hand-computed from the numbers cited in the comments.

Reads:  data_bayesian-network/network/master.csv, s_matrix/s_matrix_long.csv (read-only).
Writes: nothing.
"""
import csv

import numpy as np
import pandas as pd
import pytest

from ridethrough import adapter as A
from ridethrough.drivers.sample import to_load_fraction


def _row(path, key, **match):
    with open(A.NETWORK_DIR / path, newline="") as f:
        return next(r for r in csv.DictReader(f) if all(r[k] == v for k, v in match.items()))


def test_load_capped_to_evidence_range():
    """clip(0.5 * load_index, 0.2, 0.85): 0.97 (to_load_fraction default) is not reachable."""
    li = np.array([0.1, 1.0, 1.6, 3.0])
    np.testing.assert_allclose(A.site_load_fraction(li), [0.2, 0.5, 0.8, 0.85])
    assert to_load_fraction(3.0) == pytest.approx(0.97)      # the default cap is higher: the adapter overrides it


def test_load_typical_override():
    assert A.site_load_fraction(1.0, typical=0.3) == pytest.approx(0.3)
    assert A.site_load_fraction(1.0, typical=0.9) == pytest.approx(0.85)


def test_dip_depth_converts_to_residual():
    np.testing.assert_allclose(A.dip_depth_pct_to_residual_pu([0, 50, 100]), [1.0, 0.5, 0.0])
    # master.csv notes: retained values 0.305 to 0.844 pu correspond to depth 69.5 and 15.6
    np.testing.assert_allclose(A.dip_depth_pct_to_residual_pu([15.6, 69.5]), [0.844, 0.305])
    for bad in (-1.0, 100.5):
        with pytest.raises(ValueError):
            A.dip_depth_pct_to_residual_pu(bad)


def test_dip_depth_draw_stays_in_master_range():
    c = A.load_constants()
    d = A.sample_dip_depth_pct(5000, np.random.default_rng(0), c)
    assert d.min() >= c.dip_depth_pct[0] and d.max() <= c.dip_depth_pct[2]
    assert d.mean() == pytest.approx(sum(c.dip_depth_pct) / 3, abs=1.0)    # triangular mean


def test_age_to_capacitance_uses_the_s_matrix_slope():
    slope = float(_row("s_matrix/s_matrix_long.csv", None, factor="dclink_capacitance_factor",
                       driver="equipment_age_years")["slope_at_typical_nominal"])
    assert slope == pytest.approx(-0.0132)
    assert A.load_constants().dclink_age_slope == slope
    np.testing.assert_allclose(A.dclink_capacitance_factor([0, 7.5, 15]), 1 + slope * np.array([0, 7.5, 15]))
    np.testing.assert_allclose(A.cap_loss_from_age([0, 15]), [0.0, 0.198])
    master_low = float(_row("master.csv", None, node="dclink_capacitance_factor")["low"])
    assert A.dclink_capacitance_factor(15.0) >= master_low                   # stays inside the master.csv range


def test_resistance_without_temperature_effect():
    """Conditioned room (attenuation 0): only age matters. Age slope 0.052 pu/yr."""
    np.testing.assert_allclose(A.battery_resistance_pu([0, 10, 15], [-20, 25, 45], 0.0), [1.0, 1.52, 1.78])


def _res_curve():
    """The storage_resistance_pu vs outdoor_temp_c curve, read directly from s_matrix_long.csv."""
    row = _row("s_matrix/s_matrix_long.csv", None, factor="storage_resistance_pu", driver="outdoor_temp_c")
    return [float(v) for v in row["x_points"].split(";")], [float(v) for v in row["y_points"].split(";")]


def test_resistance_cold_room_follows_the_curve():
    """Attenuation 1 and age 0: R follows the S-matrix curve (1 at 25 C, the measured ratio at -20 C), flat
    above 25 C and below -20 C, linear between measured points; attenuation scales the rise above 1."""
    xs, ys = _res_curve()
    r = lambda t, a=1.0: A.battery_resistance_pu(0.0, t, a)
    assert r(25) == pytest.approx(1.0) and r(40) == pytest.approx(1.0)
    assert r(-20) == pytest.approx(ys[0]) and r(-40) == pytest.approx(r(-20))
    mid = (xs[1] + xs[2]) / 2
    assert r(mid) == pytest.approx((ys[1] + ys[2]) / 2)                      # linear between measured points
    assert r(-20, 0.284) == pytest.approx(1 + 0.284 * (ys[0] - 1))          # upper-bound room attenuation
    t = np.linspace(-20, 45, 40)
    assert (np.diff(A.battery_resistance_pu(5.0, t, 0.284)) <= 1e-12).all()  # colder is never lower


def test_resistance_clipped_to_master_range():
    """Over the full age and temperature range the result stays inside master.csv's low-high. With the measured
    curve the worst case (15 years, -20 C, unconditioned room) is 1 + 15 x age slope + (ratio at -20 C - 1),
    below the 5 pu high, so the clip does not bind there."""
    m = _row("master.csv", None, node="storage_resistance_pu")
    lo, hi = float(m["low"]), float(m["high"])
    age_slope = float(_row("s_matrix/s_matrix_long.csv", None, factor="storage_resistance_pu",
                           driver="equipment_age_years")["slope_at_typical_nominal"])
    xs, ys = _res_curve()
    worst = 1 + age_slope * 15.0 + (ys[0] - 1)
    assert A.battery_resistance_pu(15.0, -20.0, 1.0) == pytest.approx(min(worst, hi))
    ages, temps = np.meshgrid(np.linspace(0, 15, 16), np.linspace(-40, 45, 18))
    r = A.battery_resistance_pu(ages, temps, 1.0)
    assert (r >= lo).all() and (r <= hi).all()


def test_converter_derate_follows_the_sma_curve():
    """SMA continuous rating vs ambient: 1.0 at 25 C, 0.91 at 40 C, 0.85 at 50 C; no derating below 25 C."""
    t = np.array([-10.0, 25.0, 40.0, 45.0, 50.0])
    np.testing.assert_allclose(A.converter_derate(t, True), [1.0, 1.0, 0.91, 0.88, 0.85])
    np.testing.assert_allclose(A.converter_derate(t, False), 1.0)            # indoors: conditioned, attenuation 0


def test_converter_outdoor_flag_is_per_scenario():
    d = A.converter_derate([40.0, 40.0], np.array([True, False]))
    np.testing.assert_allclose(d, [0.91, 1.0])


def test_drivers_to_sim_roots_end_to_end():
    df = pd.DataFrame({"temp_c": [-10.0, 30.0, 40.0], "load_index": [1.0, 2.5, 0.2]})
    roots = A.drivers_to_sim_roots(df, age_years=10.0, room_atten=0.284, converter_outdoor=True)
    np.testing.assert_allclose(roots["load_frac"], [0.5, 0.85, 0.2])
    np.testing.assert_allclose(roots["cap_loss"], 0.132)
    np.testing.assert_allclose(roots["age_years"], 10.0)
    np.testing.assert_allclose(roots["converter_derate"], [1.0, np.interp(30, [25, 40], [1.0, 0.91]), 0.91])
    assert roots["bat_resistance_pu"][0] > roots["bat_resistance_pu"][1] == pytest.approx(1.52)
