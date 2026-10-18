"""Part A of the external-driver task: sample external drivers from the fitted model.

What this file is
    The driver sampler. sample_drivers() draws calendar, temp_c, dewpoint_c and load_index jointly,
    using the climatology, load model and Gaussian copula written by fit.py. to_load_fraction()
    maps the grid load_index to the site load_fraction used by the S matrix. Part B (implied.py)
    uses both for its Monte Carlo check.

Reads (read-only, written by fit.py; data_bayesian-network/network/drivers/)
    temp_by_month_hour.csv   month x hour mean and sd of temp_c and dewpoint_c
    load_model.json          load_index model ("model" key)
    driver_copula.json       copula correlation and marginal quantiles per season x daypart cell,
                             calendar counts

Writes
    nothing.

How a draw works
    1. Calendar: draw (month, hour, daytype) in proportion to how often it occurs in 2021-2025,
       optionally restricted to one season and/or one hour.
    2. Copula: draw (z_temp, z_dew, z_load) from the Gaussian copula of the draw's cell (season x
       6-hour daypart, e.g. "JJA|12-17"; see driver_copula.json "cells"). The load score is mixed
       with independent noise, z_load' = coupling * z_load + sqrt(1 - coupling^2) * e, so its
       correlation with the temperature and dewpoint scores is scaled by coupling and the matrix
       stays positive definite.
    3. Marginals: each score is mapped to its cell's empirical quantiles (temp_z, dew_z,
       load_resid). Draws are bounded by the 0.1% and 99.9% quantiles.
    4. temp_c = month-hour mean + sd * temp_z; dewpoint_c likewise, capped at temp_c.
    5. load_index = 1 + coupling * (model(calendar, temp_c) - 1 + cell_mean) + (load_resid - cell_mean),
       where model is the fitted load model (temperature curve + hour x daytype + month effects) and
       cell_mean is the mean of the cell's load_resid quantiles. The cell mean is a season x
       time-of-day effect the additive model leaves in the residual (e.g. +0.035 on summer
       afternoons), so it is scaled with the other calendar effects. coupling scales the
       temperature and calendar effects together; the centred residual is not scaled.
    coupling = 1 reproduces the fitted grid behaviour. coupling = 0 gives a flat load: it still
    varies (by the residual) but is independent of weather and time of day. The residual's spread
    comes from the grid fit, which is an assumption for a data center, and still differs by cell
    (interquartile range about 0.057-0.086), which affects its variance but not its correlation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from ridethrough.drivers import fit


def load_fitted(drivers_dir: Path | None = None) -> dict:
    """Read the fit.py outputs that the sampler needs.

    Inputs: drivers_dir, the folder holding fit.py outputs (default fit.OUT_DIR, read at call time).
    Output: {"tab": temp_by_month_hour DataFrame, "load_model": load_model.json "model" dict,
        "copula": driver_copula.json dict}.
    """
    d = fit.OUT_DIR if drivers_dir is None else Path(drivers_dir)
    tab = pd.read_csv(d / "temp_by_month_hour.csv")
    load_model = json.loads((d / "load_model.json").read_text())["model"]
    copula = json.loads((d / "driver_copula.json").read_text())
    return {"tab": tab, "load_model": load_model, "copula": copula}


def sample_drivers(n: int, seed: int, coupling: float = 1.0, season: str | None = None,
                   hour: int | None = None, fitted: dict | None = None) -> pd.DataFrame:
    """Draw n joint samples of the external drivers.

    Inputs:
        n         number of samples
        seed      random seed; the same seed and arguments give identical output
        coupling  0..1, scales the temperature and calendar effects on load (1 = fitted grid
                  load; 0 = flat load independent of weather and time of day)
        season    optional DJF | MAM | JJA | SON to restrict the calendar
        hour      optional 0-23 (Central) to restrict the calendar
        fitted    optional output of load_fitted(); read from fit.OUT_DIR if omitted
    Output: DataFrame with n rows: season, month, hour, daytype (weekday | weekend_holiday),
        temp_c (degC), dewpoint_c (degC), load_index (dimensionless).
    Assumptions: see the module docstring (calendar frequencies from 2021-2025, Gaussian copula by
        season x 6-hour daypart, empirical marginals bounded at the 0.1%/99.9% quantiles,
        dewpoint <= temperature).
    """
    if not 0.0 <= coupling <= 1.0:
        raise ValueError("coupling must be between 0 and 1")
    fitted = load_fitted() if fitted is None else fitted
    cop = fitted["copula"]
    rng = np.random.default_rng(seed)

    cal = pd.DataFrame(cop["calendar_counts"])
    cal["season"] = cal["month"].map(fit.SEASON_OF_MONTH)
    if season is not None:
        cal = cal[cal["season"] == season]
    if hour is not None:
        cal = cal[cal["hour"] == hour]
    if cal.empty:
        raise ValueError(f"no calendar cells for season={season!r}, hour={hour!r}")
    pick = rng.choice(len(cal), size=n, p=(cal["n"] / cal["n"].sum()).to_numpy())
    out = cal.iloc[pick][["season", "month", "hour", "daytype"]].reset_index(drop=True)

    probs = np.array(cop["quantile_probs"])
    scores = np.empty((n, 3))
    cell_mean = np.zeros(n)
    cell = fit.copula_cell(out["season"].to_numpy(), out["hour"].to_numpy())
    for c in fit.COPULA_CELLS:
        sel = cell == c
        if not sel.any():
            continue
        # method="cholesky": the Cholesky factor is unique, so the same seed gives the same draws on
        # every machine. numpy's default ("svd") depends on the LAPACK library (Accelerate, OpenBLAS),
        # which changed the implied correlations by up to ~5e-4 between machines.
        z = rng.multivariate_normal(np.zeros(3), np.array(cop["cells"][c]["corr"]), size=int(sel.sum()),
                                    method="cholesky")
        e = rng.standard_normal(int(sel.sum()))
        z[:, 2] = coupling * z[:, 2] + np.sqrt(1.0 - coupling ** 2) * e
        u = stats.norm.cdf(z)
        q = cop["cells"][c]["marginal_quantiles"]
        scores[sel] = np.column_stack([np.interp(u[:, i], probs, q[v])
                                       for i, v in enumerate(fit.COPULA_VARS)])
        # mean of the quantile function over its probability range: approximately the mean of this
        # cell's load residual draws (draws beyond the 0.1%/99.9% quantiles are clamped to the ends)
        cell_mean[sel] = np.trapezoid(q["load_resid"], probs) / (probs[-1] - probs[0])

    m = out[["month", "hour"]].merge(fitted["tab"], on=["month", "hour"], how="left")
    out["temp_c"] = m["mean_c"].to_numpy() + m["sd_c"].to_numpy() * scores[:, 0]
    dew = m["dew_mean_c"].to_numpy() + m["dew_sd_c"].to_numpy() * scores[:, 1]
    out["dewpoint_c"] = np.minimum(dew, out["temp_c"].to_numpy())
    model = fit.predict_load_index(fitted["load_model"], out["month"], out["hour"], out["daytype"],
                                   out["temp_c"])
    out["load_index"] = 1.0 + coupling * (model - 1.0 + cell_mean) + (scores[:, 2] - cell_mean)
    return out


def to_load_fraction(load_index, typical: float = 0.5, low: float = 0.2, high: float = 0.97) -> np.ndarray:
    """Map grid load_index to site load_fraction (fraction of rated site power).

    Inputs: load_index (dimensionless); typical, low, high from master.csv load_fraction
        (0.5, 0.2, 0.97).
    Output: clip(typical * load_index, low, high). The linear part (typical * load_index) is what
        Part B uses to convert load_index variance to load_fraction variance.
    """
    return np.clip(typical * np.asarray(load_index, dtype=float), low, high)
