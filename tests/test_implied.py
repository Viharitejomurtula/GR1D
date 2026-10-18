"""Tests for Part B of the external-driver task (ridethrough/drivers/implied.py).

What this file is
    Checks every implied covariance and correlation matrix (all 216 cases x 5 groups): symmetry,
    positive semi-definiteness, valid correlations, and that factors with no driver response stay
    uncorrelated. Also checks that the written nominal-case files match a fresh computation.

Reads (read-only)
    data_bayesian-network/network/s_matrix/ (S, noise), master.csv, and the fit.py outputs in
    network/drivers/ (run fit.py first; the file check also needs implied.py's outputs)

Writes
    nothing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ridethrough.drivers import fit, implied


@pytest.fixture(scope="module")
def inp() -> dict:
    """implied.load_inputs()."""
    return implied.load_inputs()


@pytest.fixture(scope="module")
def res(inp) -> dict:
    """implied.run_cases() over every case and group (samples Sigma_D: about a minute)."""
    return implied.run_cases(inp)


def _matrices(res):
    """Yield (case_id, group, S, cov, corr) for every case and group."""
    for case in implied.case_grid():
        cid = implied.case_id(case)
        s, _ = res["s"][cid]
        noise = res["noise"][(case["noise_mult"], case["dclink_n"])]["sd"]
        for g in fit.GROUPS:
            cov, corr = implied.implied_cov(s, res["sigma_d"][(g, case["coupling"], case["age_sd"])], noise)
            yield cid, g, s, cov, corr


def test_covariance_symmetric_and_psd(res):
    """Every implied covariance matrix is symmetric and positive semi-definite."""
    for cid, g, _, cov, _ in _matrices(res):
        c = cov.to_numpy()
        assert np.allclose(c, c.T), f"{cid} {g}: not symmetric"
        assert np.linalg.eigvalsh(c).min() >= -1e-10 * np.abs(c).max(), f"{cid} {g}: not PSD"


def test_correlation_unit_diagonal_and_bounded(res):
    """Every correlation matrix has 1s on the diagonal and all values in [-1, 1]."""
    for cid, g, _, _, corr in _matrices(res):
        r = corr.to_numpy()
        assert np.allclose(np.diag(r), 1.0), f"{cid} {g}: diagonal"
        assert (np.abs(r) <= 1.0 + 1e-12).all(), f"{cid} {g}: outside [-1, 1]"


def test_zero_s_row_means_zero_covariance(res):
    """A factor whose S row is all zero has zero covariance with every other factor."""
    checked = 0
    for cid, g, s, cov, _ in _matrices(res):
        for f in s.index[(s == 0).all(axis=1)]:
            assert np.allclose(cov.loc[f].drop(f), 0.0), f"{cid} {g}: {f}"
            checked += 1
    assert checked > 0


def test_workload_factors_have_no_driver_response(res):
    """osc_amp and osc_freq_hz respond only to workload_type (a mean shift), so their S rows are
    zero and Cov(X) is the same within every workload category."""
    for s, _ in res["s"].values():
        assert (s.loc[["osc_amp", "osc_freq_hz"]] == 0).all().all()


@pytest.mark.parametrize("group", fit.GROUPS)
def test_written_nominal_correlation_matches(res, group):
    """implied_correlation_nominal_<group>.csv matches a fresh computation of the nominal case."""
    written = pd.read_csv(fit.OUT_DIR / f"implied_correlation_nominal_{group}.csv", index_col="factor")
    fresh = res["nominal"][group][1]
    np.testing.assert_allclose(written.loc[fresh.index, fresh.columns].to_numpy(), fresh.to_numpy(),
                               atol=1e-5)
