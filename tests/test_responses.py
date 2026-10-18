"""Tests for ridethrough.responses: Arrhenius helpers, the data fits, and the S/noise replacement.

What this file is
    Pure-math tests run always. Tests that read the downloaded datasets (data_bayesian-network/drivers_raw/) are
    skipped when the data is not present (it is not in git).

Reads:  drivers_raw/ (read-only), implied.load_inputs() files.
Writes: nothing.
"""
import numpy as np
import pandas as pd
import pytest

from ridethrough.drivers import implied
from ridethrough.responses import apply_to_implied as ap
from ridethrough.responses import battery_resistance as br

HAVE_DATA = (br.RAW / "battery_sandia_eis" / "EIS_Data.zip").exists() and (br.RAW / "battery_panasonic_18650pf" / "dataset.zip").exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="drivers_raw datasets not downloaded")


def test_arrhenius_recovers_activation_energy():
    t = np.array([-20.0, -10.0, 0.0, 10.0, 25.0])
    r = br.ratio_at(0.25, 25.0) * np.array([br.ratio_at(0.25, x) for x in t])
    assert br.arrhenius(t, r) == pytest.approx(0.25, rel=1e-6)


def test_ratio_is_one_at_25c_and_grows_when_cold():
    assert br.ratio_at(0.2, 25.0) == pytest.approx(1.0)
    assert br.ratio_at(0.2, -20.0) > br.ratio_at(0.2, 0.0) > 1.0 > br.ratio_at(0.2, 40.0)


def test_local_slope_matches_finite_difference():
    ea, h = 0.2, 1e-4
    fd = (br.ratio_at(ea, 25 + h) - br.ratio_at(ea, 25 - h)) / (2 * h)
    assert br.local_slope(ea) == pytest.approx(fd, rel=1e-5) and br.local_slope(ea) < 0


@needs_data
def test_fits_are_consistent_with_each_other():
    f = br.fit_table()
    sand, p1, p10 = f.iloc[0], f.iloc[1], f.iloc[2]
    assert 0.05 < sand.ea_ev < 0.15 and sand.n_units == 12
    assert p10.ea_ev > p1.ea_ev > sand.ea_ev                      # slower processes are more temperature-sensitive
    for r in (sand, p1, p10):
        assert r.ea_lo <= r.ea_ev <= r.ea_hi
        assert r.local_slope_near25_pu_per_C < 0
    assert abs(p1.local_slope_near25_pu_per_C) < abs(p1.local_slope_25C_pu_per_C)   # nearer room temperature the response is flatter
    assert p1.ratio_minus20 > 3.0 and p10.ratio_minus20 > 8.0   # measured median ratio R(-20 C)/R(25 C)


@needs_data
def test_replicate_spread_is_positive_and_larger_than_the_new_cell_value():
    sp = br.spread_table().iloc[0]
    assert all(sp[c] > 0 for c in ("LCO", "LFP", "NCA", "NMC"))
    assert np.median([sp.LCO, sp.LFP, sp.NCA]) > 0.0072        # noise.csv's 1100-cell new-cell spread


def test_variant_inputs_replace_only_the_resistance_rows_and_do_not_mutate():
    base = implied.load_inputs(); before = base["s_long"].copy(); noise_before = base["noise"].copy()
    v = ap.variant_inputs(base, slope=-0.03, noise_rel=0.04)
    m = (v["s_long"].factor == ap.FACTOR) & (v["s_long"].driver == "outdoor_temp_c")
    att = float(v["s_long"].loc[m, "attenuation_upper"].iloc[0])
    assert v["s_long"].loc[m, "slope_at_typical_upper"].iloc[0] == pytest.approx(-0.03 * att)
    assert v["s_long"].loc[m, "slope_at_typical_nominal"].iloc[0] == 0.0
    pd.testing.assert_frame_equal(v["s_long"].loc[~m], before.loc[~m])
    assert v["noise"].set_index("factor").loc[ap.FACTOR, "sd"] == pytest.approx(0.04)
    pd.testing.assert_frame_equal(base["s_long"], before); pd.testing.assert_frame_equal(base["noise"], noise_before)


def test_no_replacement_returns_the_same_values():
    base = implied.load_inputs(); v = ap.variant_inputs(base, None, None)
    pd.testing.assert_frame_equal(v["s_long"], base["s_long"]); pd.testing.assert_frame_equal(v["noise"], base["noise"])


# ---- workload swings ---------------------------------------------------------------------------------------------
from ridethrough.responses import workload_swings as ws

HAVE_NLR = (ws.NLR / "training" / "results").exists()


def test_resample_handles_float_timestamps():
    """Regression: 0.6 / 0.2 = 2.9999999999999996 once put samples in the wrong bin and left empty bins that read as 0 W."""
    t = 0.2 * np.arange(1000); p = np.full(1000, 100.0)
    out = ws.resample(t, p)
    assert len(out) == 1000 and np.allclose(out, 100.0)


def test_resample_refuses_traces_with_gaps():
    with pytest.raises(ValueError):
        ws.resample(np.array([0.0, 0.2, 1.0]), np.ones(3))


def test_swing_metrics_recover_a_known_sine():
    t = np.arange(0, 600, ws.DT); p = 3000 + 1000 * np.sin(2 * np.pi * 0.5 * t)
    m = ws.swing_metrics(p, trim=0.0)
    assert m["f_peak_hz"] == pytest.approx(0.5, abs=0.02)
    assert m["amp_2s_p99"] == pytest.approx(np.ptp(p[:ws.WIN]) / np.percentile(p, 99.9), rel=0.02)   # one full period in the window


def test_class_stats_total_is_between_plus_within_and_zero_between_for_equal_means():
    rng = np.random.default_rng(0)
    a = pd.DataFrame({"workload": "training", "amp_2s_p99": rng.normal(0.5, 0.1, 400), "f_peak_hz": rng.normal(0.3, 0.05, 400)})
    b = pd.DataFrame({"workload": "inference", "amp_2s_p99": rng.normal(0.2, 0.1, 400), "f_peak_hz": rng.normal(0.3, 0.05, 400)})
    s = ws.class_stats(pd.concat([a, b]), {"training": 0.4, "inference": 0.6})
    np.testing.assert_allclose(s["total"], s["between"] + s["within_mix"])
    assert s["between"][0, 0] == pytest.approx(0.4 * 0.6 * 0.3 ** 2, rel=0.1)       # p(1-p)(delta)^2
    assert s["between"][1, 1] < 1e-3 * s["total"][1, 1] * 10                        # equal frequency means: nothing explained


@pytest.mark.skipif(not HAVE_NLR, reason="NLR GenAI traces not present")
def test_measured_training_swings_larger_than_inference_but_frequency_not_separated():
    r = ws.run_table(); g = r.groupby("workload")
    assert g.amp_2s_p99.mean()["training"] > 1.5 * g.amp_2s_p99.mean()["inference"]
    assert abs(g.f_peak_hz.median()["training"] - g.f_peak_hz.median()["inference"]) < 0.1
    assert r.f_peak_hz.between(ws.F_LO, ws.F_HI).all() and (r.amp_2s_p99 <= 1.0 + 1e-9).all()
