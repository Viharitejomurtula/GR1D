"""Tests for Part A of the external-driver task (ridethrough/drivers/fit.py and sample.py).

What this file is
    Checks the data join, the load_index definition, the shape of the fitted load curve, and the
    driver sampler (reproducibility and the coupling definition).

Reads (read-only)
    data_bayesian-network/dfw_hourly_temp_clean.csv, data_bayesian-network/ercot_native_load_2021_2026.csv
    data_bayesian-network/network/drivers/load_model.json, driver_covariance.csv and the other
    fit.py outputs that sample.py reads (run `python -m ridethrough.drivers.fit` first)

Writes
    nothing.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from ridethrough.drivers import fit, sample


@pytest.fixture(scope="module")
def joined() -> pd.DataFrame:
    """Joined, cleaned hourly data from fit.load_joined()."""
    return fit.load_joined()


@pytest.fixture(scope="module")
def prepared() -> pd.DataFrame:
    """Joined data with load_index (fit.prepare_data(), all years)."""
    return fit.prepare_data()[0]


@pytest.fixture(scope="module")
def fitted() -> dict:
    """fit.py outputs as read by the sampler (sample.load_fitted())."""
    return sample.load_fitted()


@pytest.fixture(scope="module")
def driver_cov() -> pd.DataFrame:
    """driver_covariance.csv written by fit.py."""
    return pd.read_csv(fit.OUT_DIR / "driver_covariance.csv")


def test_join_excludes_uri_days(joined):
    """No hour from the Uri load-shed Central dates 2021-02-14..2021-02-20 survives the join."""
    uri = (joined["date"] >= fit.URI_FIRST) & (joined["date"] <= fit.URI_LAST)
    assert not uri.any()


def test_join_contains_only_hours_in_both_files(joined):
    """The join holds exactly the hours present in both cleaned files (minus the Uri days)."""
    temp = pd.read_csv(fit.TEMP_CSV)
    load = pd.read_csv(fit.LOAD_CSV)
    temp_ok = set(temp.loc[temp["flag"] != "missing", "hour_utc"])
    load_ok = set(load.loc[load["flag"] != "zones_do_not_sum_to_total", "hour_utc"])
    got = set(joined["hour_utc"].dt.strftime("%Y-%m-%dT%H:%MZ"))
    assert got <= temp_ok & load_ok
    central_date = temp.set_index("hour_utc")["hour_central"].str[:10]
    expected = {h for h in temp_ok & load_ok
                if not ("2021-02-14" <= central_date[h] <= "2021-02-20")}
    assert got == expected


def test_load_index_averages_one_per_complete_year(prepared):
    """load_index averages 1.0 within 0.02 in every complete year (2021-2025).

    2026 is excluded: it covers January-September only (a hot summer without October-December)
    and uses the trailing window, so its mean is about 1.08 by construction.
    """
    means = prepared.groupby("year")["load_index"].mean()
    for year in fit.FIT_YEARS:
        assert abs(means[year] - 1.0) < 0.02, f"{year}: {means[year]:.4f}"


def test_fitted_curve_rises_outside_balance_points():
    """The chosen temperature curve rises above the cooling balance point and below the heating one."""
    lm = json.loads((fit.OUT_DIR / "load_model.json").read_text())
    curve, shape = lm["model"]["curve"], lm["shape"]
    heat, cool = shape["heat_balance_c"], shape["cool_balance_c"]
    f = lambda t: float(fit.eval_temp_curve(curve, t)[0])  # noqa: E731
    assert f(cool + 5.0) > f(cool) and f(cool + 10.0) > f(cool + 5.0)
    assert f(heat - 5.0) > f(heat) and f(heat - 10.0) > f(heat - 5.0)


def test_sample_drivers_reproducible(fitted):
    """Same seed and arguments give an identical frame; a different seed does not."""
    a = sample.sample_drivers(5_000, seed=7, fitted=fitted)
    b = sample.sample_drivers(5_000, seed=7, fitted=fitted)
    c = sample.sample_drivers(5_000, seed=8, fitted=fitted)
    pd.testing.assert_frame_equal(a, b)
    assert not a.equals(c)


def test_coupling_zero_is_independent_of_temperature_overall(fitted):
    """coupling = 0 (flat data-center load): load_index is independent of temperature overall,
    not only within calendar strata. |Spearman(temp_c, load_index)| < 0.05 on 20,000 samples."""
    d = sample.sample_drivers(20_000, seed=3, coupling=0.0, fitted=fitted)
    rho = stats.spearmanr(d["temp_c"], d["load_index"])[0]
    assert abs(rho) < 0.05


@pytest.mark.parametrize("season", fit.SEASONS)
def test_coupling_one_matches_fit(fitted, driver_cov, season):
    """coupling = 1 (fitted grid behaviour): the sampled temp/load_index Spearman for each season
    falls inside the fit's 95% block-bootstrap CI from driver_covariance.csv (20,000 samples)."""
    d = sample.sample_drivers(20_000, seed=11, coupling=1.0, season=season, fitted=fitted)
    rho = stats.spearmanr(d["temp_c"], d["load_index"])[0]
    row = driver_cov[(driver_cov["group"] == season) & (driver_cov["var_i"] == "temp_c")
                     & (driver_cov["var_j"] == "load_index")].iloc[0]
    assert row["spearman_lo"] <= rho <= row["spearman_hi"]


def test_to_load_fraction_clips_to_master_range():
    """to_load_fraction = clip(0.5 x load_index, 0.2, 0.97)."""
    got = sample.to_load_fraction(np.array([0.1, 1.0, 1.5, 3.0]))
    np.testing.assert_allclose(got, [0.2, 0.5, 0.75, 0.97])
