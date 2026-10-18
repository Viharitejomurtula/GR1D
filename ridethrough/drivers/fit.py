"""Part A of the external-driver task: fit the joint model of the external drivers.

What this file is
    The driver fit for the ride-through dependency network. It estimates how outdoor temperature,
    dewpoint and the grid load index behave together at DFW, so that Part B (implied.py) can turn
    the S matrix into factor covariances: Cov(X) = S Sigma_D S^T + diag(noise^2).

Reads (read-only)
    data_bayesian-network/dfw_hourly_temp_clean.csv        NOAA LCD, DFW airport, hourly
    data_bayesian-network/ercot_native_load_2021_2026.csv  ERCOT hourly native load by weather zone

Writes (data_bayesian-network/network/drivers/)
    temp_by_month_hour.csv   temperature and dewpoint climatology by month x hour (Model 1)
    load_model.json          load_index model: temperature curve + hour x daytype + month (Model 2)
    driver_covariance.csv    Sigma_D for [temp_c, load_index, dewpoint_c] with bootstrap CIs (Model 3)
    driver_copula.json       Gaussian copula and marginals by season, used by sample.py
    driver_fit_report.md     results, 2026 holdout validation and figure links
    fig_*.png                five figures referenced by the report

Run
    python -m ridethrough.drivers.fit

Key choices (also stated in the report)
    - Join on hour_utc. temp_c is an instantaneous top-of-hour reading; load is the mean over the
      hour that begins at hour_utc, so temperature leads the load average by about 30 minutes.
    - NCENT (covers Dallas-Fort Worth) is the main load series; ERCOT total is a cross-check.
    - Fit on 2021-2025, hold out 2026. Winter Storm Uri load-shed days (Central dates 2021-02-14
      to 2021-02-20) are dropped.
    - load_index = hourly load / 365-day rolling mean of daily mean load. Centered window where
      available, trailing window where it is not (the last ~5 months of record). At the start of
      the record neither window is full, so the first full centered value is carried back.
    - The load model's temperature curve is a hinge or a natural cubic spline, whichever has the
      lower 2026 holdout RMSE. The spline's knot count (5-7) is chosen by leave-one-year-out
      within 2021-2025.
    - Every output is built in memory first and written only after all of them succeed.
"""
from __future__ import annotations

import io
import json
import math
from datetime import date
from pathlib import Path

import holidays
import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data_bayesian-network"
TEMP_CSV = DATA_DIR / "dfw_hourly_temp_clean.csv"
LOAD_CSV = DATA_DIR / "ercot_native_load_2021_2026.csv"
OUT_DIR = DATA_DIR / "network" / "drivers"

URI_FIRST = pd.Timestamp("2021-02-14")
URI_LAST = pd.Timestamp("2021-02-20")
FIT_YEARS = (2021, 2022, 2023, 2024, 2025)
HOLDOUT_YEAR = 2026

SEASON_OF_MONTH = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                   6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
SEASONS = ("DJF", "MAM", "JJA", "SON")
GROUPS = ("overall",) + SEASONS
DRIVER_VARS = ("temp_c", "load_index", "dewpoint_c")
PAIRS = tuple((DRIVER_VARS[i], DRIVER_VARS[j]) for i in range(3) for j in range(i, 3))
COPULA_VARS = ("temp_z", "dew_z", "load_resid")
DAYPART_HOURS = 6
DAYPARTS = tuple(f"{h:02d}-{h + DAYPART_HOURS - 1:02d}" for h in range(0, 24, DAYPART_HOURS))
COPULA_CELLS = tuple(f"{s}|{d}" for s in SEASONS for d in DAYPARTS)

ROLL_DAYS = 365
ROLL_MIN_DAYS = 330          # allows for the dropped Uri week and scattered missing days
BLOCK_DAYS = 7
N_BOOT = 500
SEED = 20261017
HINGE_HEAT_GRID = np.arange(5.0, 22.01, 0.5)    # candidate heating balance points, degC
HINGE_COOL_GRID = np.arange(12.0, 30.01, 0.5)   # candidate cooling balance points, degC
SPLINE_KNOT_COUNTS = (5, 6, 7)
QUANTILE_PROBS = np.round(np.concatenate([[0.001, 0.005], np.arange(0.01, 0.995, 0.01),
                                          [0.995, 0.999]]), 3)
FIGURES = ("fig_load_vs_temp.png", "fig_load_by_hour.png", "fig_temp_heatmap.png",
           "fig_residuals.png", "fig_holdout_2026.png")


# ----------------------------------------------------------------------------- data

def load_joined() -> pd.DataFrame:
    """Read, clean and join the temperature and load files.

    Inputs: none (reads TEMP_CSV and LOAD_CSV).
    Output: one row per hour present in both files, sorted by hour_utc, with columns
        hour_utc (UTC timestamp), local_time (Central wall-clock, naive), date (Central date),
        year, month, hour (0-23 Central), season, daytype (weekday | weekend_holiday),
        temp_c (degC), dewpoint_c (degC), temp_flag (observed | interpolated),
        ncent_mw (MW), ercot_mw (MW).
    Cleaning: drops temp flag "missing", load flag "zones_do_not_sum_to_total", and the Uri
        load-shed Central dates 2021-02-14..2021-02-20. Inner join on hour_utc.
    """
    temp = pd.read_csv(TEMP_CSV)
    load = pd.read_csv(LOAD_CSV)
    temp = temp[temp["flag"] != "missing"].dropna(subset=["temp_c", "dewpoint_c"])
    load = load[load["flag"] != "zones_do_not_sum_to_total"]
    df = (temp[["hour_utc", "hour_central", "temp_c", "dewpoint_c", "flag"]]
          .rename(columns={"flag": "temp_flag"})
          .merge(load[["hour_utc", "NCENT", "ERCOT"]]
                 .rename(columns={"NCENT": "ncent_mw", "ERCOT": "ercot_mw"}),
                 on="hour_utc", how="inner", validate="one_to_one"))
    df["hour_utc"] = pd.to_datetime(df["hour_utc"], utc=True)
    df["local_time"] = pd.to_datetime(df["hour_central"].str[:16])
    df["date"] = df["local_time"].dt.normalize()
    df = df[(df["date"] < URI_FIRST) | (df["date"] > URI_LAST)]
    df = add_calendar(df.drop(columns="hour_central"))
    return df.sort_values("hour_utc").reset_index(drop=True)


def cleaning_counts() -> dict[str, int]:
    """Row counts at each cleaning step, for the report.

    Output: temp_rows, temp_missing, load_rows, load_zone_mismatch, joined (before the Uri drop),
        uri_dropped, final.
    """
    temp = pd.read_csv(TEMP_CSV, usecols=["hour_utc", "hour_central", "flag"])
    load = pd.read_csv(LOAD_CSV, usecols=["hour_utc", "flag"])
    t_ok = temp[temp["flag"] != "missing"]
    l_ok = load[load["flag"] != "zones_do_not_sum_to_total"]
    j = t_ok.merge(l_ok[["hour_utc"]], on="hour_utc")
    d = pd.to_datetime(j["hour_central"].str[:10])
    uri = int(((d >= URI_FIRST) & (d <= URI_LAST)).sum())
    return {"temp_rows": len(temp), "temp_missing": int((temp["flag"] == "missing").sum()),
            "load_rows": len(load),
            "load_zone_mismatch": int((load["flag"] == "zones_do_not_sum_to_total").sum()),
            "joined": len(j), "uri_dropped": uri, "final": len(j) - uri}


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar columns derived from Central wall-clock time.

    Inputs: df with local_time and date (Central).
    Output: copy of df with year, month, hour, season (DJF | MAM | JJA | SON) and
        daytype (weekday | weekend_holiday). Holidays are US federal holidays, including
        observed dates, from the `holidays` package.
    """
    df = df.copy()
    years = range(int(df["date"].dt.year.min()), int(df["date"].dt.year.max()) + 1)
    us = holidays.country_holidays("US", years=years)
    df["year"] = df["date"].dt.year
    df["month"] = df["local_time"].dt.month
    df["hour"] = df["local_time"].dt.hour
    df["season"] = df["month"].map(SEASON_OF_MONTH)
    is_holiday = df["date"].dt.date.map(lambda d: d in us)
    off = (df["date"].dt.dayofweek >= 5) | is_holiday
    df["daytype"] = np.where(off, "weekend_holiday", "weekday")
    return df


def add_load_index(df: pd.DataFrame, load_col: str, out_col: str) -> pd.DataFrame:
    """Remove load growth: load_index = hourly load / 365-day rolling mean of daily mean load.

    Inputs: df with date and load_col (MW).
    Output: copy of df with out_col (dimensionless, about 1.0 on average over a full year) and
        out_col + "_basis" (centered | trailing | first_full_window), the window used per date.
    Window rule: centered 365-day window where it has at least ROLL_MIN_DAYS days of data;
        otherwise trailing 365-day window; at the start of the record, where neither is full,
        the first full centered value is carried back.
    """
    df = df.copy()
    daily = df.groupby("date")[load_col].mean()
    days = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(days)
    centered = daily.rolling(ROLL_DAYS, center=True, min_periods=ROLL_MIN_DAYS).mean()
    trailing = daily.rolling(ROLL_DAYS, min_periods=ROLL_MIN_DAYS).mean()
    level = centered.copy()
    basis = pd.Series(np.where(centered.notna(), "centered", ""), index=days, dtype=object)
    late = centered.isna() & (days > centered.first_valid_index())
    level[late] = trailing[late]
    basis[late] = "trailing"
    early = level.isna()
    level = level.bfill()
    basis[early] = "first_full_window"
    df[out_col] = df[load_col].to_numpy() / df["date"].map(level).to_numpy()
    df[out_col + "_basis"] = df["date"].map(basis).to_numpy()
    return df


def prepare_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Joined data with load_index (NCENT) and ercot_load_index, split into all, fit and holdout.

    Output: (all rows, fit rows 2021-2025, holdout rows 2026), each with a fresh 0..n-1 index.
    """
    df = add_load_index(load_joined(), "ncent_mw", "load_index")
    df = add_load_index(df, "ercot_mw", "ercot_load_index")
    fit = df[df["year"].isin(FIT_YEARS)].reset_index(drop=True)
    hold = df[df["year"] == HOLDOUT_YEAR].reset_index(drop=True)
    return df, fit, hold


# ----------------------------------------------------------------------------- model 1

def fit_temp_month_hour(fit: pd.DataFrame) -> pd.DataFrame:
    """Model 1: temperature and dewpoint climatology by month x hour.

    Inputs: fit-period rows with month, hour, temp_c, dewpoint_c.
    Output: 288 rows: month, hour, mean_c, sd_c, n, q05_c, q95_c (temp_c, degC),
        dew_mean_c, dew_sd_c (dewpoint_c, degC).
    """
    g = fit.groupby(["month", "hour"])
    tab = g["temp_c"].agg(mean_c="mean", sd_c="std", n="size")
    q = g["temp_c"].quantile([0.05, 0.95]).unstack()
    tab["q05_c"] = q[0.05]
    tab["q95_c"] = q[0.95]
    tab = tab.join(g["dewpoint_c"].agg(dew_mean_c="mean", dew_sd_c="std"))
    return tab.reset_index()


def standardized_residuals(df: pd.DataFrame, tab: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Standardize temp_c and dewpoint_c against the month x hour climatology.

    Inputs: df with month, hour, temp_c, dewpoint_c; tab from fit_temp_month_hour.
    Output: (temp_z, dew_z), each (value - month-hour mean) / month-hour sd, dimensionless.
    """
    m = df[["month", "hour"]].merge(tab, on=["month", "hour"], how="left")
    temp_z = (df["temp_c"].to_numpy() - m["mean_c"].to_numpy()) / m["sd_c"].to_numpy()
    dew_z = (df["dewpoint_c"].to_numpy() - m["dew_mean_c"].to_numpy()) / m["dew_sd_c"].to_numpy()
    return temp_z, dew_z


def residual_autocorrelation(hour_utc: pd.Series, resid: np.ndarray,
                             lags: tuple[int, ...] = (1, 24, 168)) -> dict[str, float]:
    """Autocorrelation of an hourly residual series at the given lags (hours).

    Inputs: hour_utc timestamps and residuals aligned with them.
    Output: {"lag_<k>h": autocorrelation}. Gaps are reindexed to NaN, so pairs that span a
        dropped hour are skipped rather than treated as adjacent.
    """
    s = pd.Series(resid, index=pd.DatetimeIndex(hour_utc))
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="h"))
    return {f"lag_{k}h": float(s.autocorr(k)) for k in lags}


# ----------------------------------------------------------------------------- model 2

def calendar_design(df: pd.DataFrame) -> np.ndarray:
    """Design matrix for the calendar part of the load model.

    Inputs: df with hour, daytype, month.
    Output: (n, 59) array: intercept, 47 hour x daytype dummies (reference weekday hour 0),
        11 month dummies (reference January).
    """
    hd = df["hour"].to_numpy() + 24 * (df["daytype"].to_numpy() == "weekend_holiday")
    x_hd = np.eye(48)[hd][:, 1:]
    x_m = np.eye(12)[df["month"].to_numpy() - 1][:, 1:]
    return np.hstack([np.ones((len(df), 1)), x_hd, x_m])


def hinge_basis(temp_c: np.ndarray, heat_c: float, cool_c: float) -> np.ndarray:
    """Piecewise-linear hinge basis: columns max(heat_c - T, 0) and max(T - cool_c, 0), degC."""
    t = np.asarray(temp_c, dtype=float)
    return np.column_stack([np.maximum(heat_c - t, 0.0), np.maximum(t - cool_c, 0.0)])


def ncs_basis(temp_c: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Natural cubic spline basis (Hastie, Tibshirani & Friedman, Elements of Statistical Learning, eqs. 5.4-5.5).

    Inputs: temperatures (degC) and K increasing knots (degC).
    Output: (n, K-1) array; the constant term is left to the model intercept. Linear beyond
        the outer knots.
    """
    t = np.asarray(temp_c, dtype=float)
    k = np.asarray(knots, dtype=float)

    def d(j: int) -> np.ndarray:
        return (np.maximum(t - k[j], 0.0) ** 3 - np.maximum(t - k[-1], 0.0) ** 3) / (k[-1] - k[j])

    return np.column_stack([t] + [d(j) - d(len(k) - 2) for j in range(len(k) - 2)])


def eval_temp_curve(curve: dict, temp_c) -> np.ndarray:
    """Evaluate the fitted temperature curve f(T), in load_index units.

    Inputs: curve dict from load_model.json ("hinge" or "spline"); temperatures in degC.
    Output: f(T). Its level is arbitrary (the calendar terms carry the mean); only differences matter.
    """
    t = np.atleast_1d(np.asarray(temp_c, dtype=float))
    if curve["type"] == "hinge":
        return hinge_basis(t, curve["heat_balance_c"], curve["cool_balance_c"]) @ np.array(
            [curve["heat_slope_per_c"], curve["cool_slope_per_c"]])
    return ncs_basis(t, np.array(curve["knots_c"])) @ np.array(curve["coef"])


def fit_hinge(xc: np.ndarray, y: np.ndarray, temp_c: np.ndarray) -> tuple[dict, np.ndarray]:
    """Fit load_index = calendar + hinge f(T) by grid search over the two balance points.

    Inputs: calendar design xc, load_index y, temperatures (degC).
    Output: (curve dict, calendar coefficients). The curve holds heat_balance_c and cool_balance_c
        (degC) and heat_slope_per_c and cool_slope_per_c (load_index per degC away from the balance
        point; positive means load rises). Search: heating point on HINGE_HEAT_GRID, cooling point
        on HINGE_COOL_GRID, heating <= cooling, minimum residual sum of squares (solved from the
        normal equations, so each grid point costs only a small solve).
    """
    g = xc.T @ xc
    xcy = xc.T @ y
    yy = float(y @ y)
    best = None
    for heat in HINGE_HEAT_GRID:
        for cool in HINGE_COOL_GRID:
            if cool < heat:
                continue
            h = hinge_basis(temp_c, heat, cool)
            xh = xc.T @ h
            a = np.block([[g, xh], [xh.T, h.T @ h]])
            b = np.concatenate([xcy, h.T @ y])
            coef = np.linalg.lstsq(a, b, rcond=None)[0]
            sse = yy - float(coef @ b)
            if best is None or sse < best[0]:
                best = (sse, heat, cool, coef)
    _, heat, cool, coef = best
    curve = {"type": "hinge", "heat_balance_c": float(heat), "cool_balance_c": float(cool),
             "heat_slope_per_c": float(coef[-2]), "cool_slope_per_c": float(coef[-1])}
    return curve, coef[:-2]


def spline_knots(temp_c: np.ndarray, k: int) -> np.ndarray:
    """K knots at evenly spaced quantiles (5th to 95th percentile) of temperature, degC."""
    return np.quantile(temp_c, np.linspace(0.05, 0.95, k))


def fit_spline(xc: np.ndarray, y: np.ndarray, temp_c: np.ndarray, knots: np.ndarray) -> tuple[dict, np.ndarray]:
    """Fit load_index = calendar + natural cubic spline f(T) with the given knots.

    Inputs: calendar design xc, load_index y, temperatures (degC), knots (degC).
    Output: (curve dict with knots_c and coef, calendar coefficients).
    """
    basis = ncs_basis(temp_c, knots)
    coef = np.linalg.lstsq(np.hstack([xc, basis]), y, rcond=None)[0]
    n_cal = xc.shape[1]
    return {"type": "spline", "knots_c": [float(v) for v in knots],
            "coef": [float(v) for v in coef[n_cal:]]}, coef[:n_cal]


def choose_spline_knots(fit: pd.DataFrame, y: np.ndarray) -> tuple[int, dict[int, float]]:
    """Pick the spline knot count by leave-one-year-out RMSE within the fit years.

    Inputs: fit-period rows and their load_index y.
    Output: (chosen K, {K: RMSE}). Knots come from the fit-period temperatures (no load data),
        so they are the same in every fold. The 2026 holdout is not used here.
    """
    xc = calendar_design(fit)
    t = fit["temp_c"].to_numpy()
    years = fit["year"].to_numpy()
    scores = {}
    for k in SPLINE_KNOT_COUNTS:
        knots = spline_knots(t, k)
        sse = 0.0
        for yr in FIT_YEARS:
            tr, te = years != yr, years == yr
            curve, cal = fit_spline(xc[tr], y[tr], t[tr], knots)
            pred = xc[te] @ cal + eval_temp_curve(curve, t[te])
            sse += float(((y[te] - pred) ** 2).sum())
        scores[k] = math.sqrt(sse / len(y))
    return min(scores, key=scores.get), scores


def package_load_model(curve: dict, cal_coef: np.ndarray, fit: pd.DataFrame) -> dict:
    """Turn fitted coefficients into the load-model dict stored in load_model.json.

    Inputs: temperature curve, calendar coefficients (layout from calendar_design), fit rows.
    Output: dict with intercept; hour_daytype_effect {weekday: 24, weekend_holiday: 24};
        month_effect (12, January = 0); curve; fbar_month_hour (12 x 24 mean of f(T) over the fit
        rows in that month-hour, used by the sampler's coupling); all in load_index units.
    """
    hd = np.concatenate([[0.0], cal_coef[1:48]])
    month = np.concatenate([[0.0], cal_coef[48:59]])
    f = eval_temp_curve(curve, fit["temp_c"].to_numpy())
    fbar = (pd.Series(f).groupby([fit["month"].to_numpy(), fit["hour"].to_numpy()]).mean()
            .unstack().reindex(index=range(1, 13), columns=range(24)))
    return {"intercept": float(cal_coef[0]),
            "hour_daytype_effect": {"weekday": hd[:24].tolist(), "weekend_holiday": hd[24:].tolist()},
            "month_effect": month.tolist(),
            "curve": curve,
            "fbar_month_hour": fbar.to_numpy().tolist()}


def predict_load_index(model: dict, month, hour, daytype, temp_c, coupling: float = 1.0) -> np.ndarray:
    """Predicted load_index from calendar and temperature.

    Inputs: model dict (load_model.json "model"); month (1-12), hour (0-23), daytype
        (weekday | weekend_holiday), temp_c (degC), as arrays of equal length; coupling (0-1).
    Output: intercept + hour x daytype + month + fbar[month, hour] + coupling * (f(T) - fbar[month, hour]).
        coupling = 1 is the fitted model; coupling = 0 keeps the calendar shape and removes
        the within-month-hour temperature effect.
    """
    month = np.asarray(month)
    hour = np.asarray(hour)
    weekend = np.asarray(daytype) == "weekend_holiday"
    hd = np.where(weekend, np.array(model["hour_daytype_effect"]["weekend_holiday"])[hour],
                  np.array(model["hour_daytype_effect"]["weekday"])[hour])
    fbar = np.array(model["fbar_month_hour"])[month - 1, hour]
    f = eval_temp_curve(model["curve"], temp_c)
    return (model["intercept"] + hd + np.array(model["month_effect"])[month - 1]
            + fbar + coupling * (f - fbar))


def curve_shape(curve: dict, temp_lo: float, temp_hi: float) -> dict:
    """Balance points and end slopes of a fitted curve over [temp_lo, temp_hi] degC.

    Output: heat_balance_c and cool_balance_c (for a spline both are the minimum of f), and the
        slope of f at temp_lo and temp_hi (load_index per degC; negative at the cold end means
        load rises as it gets colder). For a hinge these are -heat_slope and +cool_slope.
    """
    if curve["type"] == "hinge":
        return {"heat_balance_c": curve["heat_balance_c"], "cool_balance_c": curve["cool_balance_c"],
                "slope_at_low_per_c": -curve["heat_slope_per_c"],
                "slope_at_high_per_c": curve["cool_slope_per_c"]}
    grid = np.arange(temp_lo, temp_hi + 0.01, 0.1)
    f = eval_temp_curve(curve, grid)
    tmin = float(grid[np.argmin(f)])
    slope = np.gradient(f, grid)
    return {"heat_balance_c": tmin, "cool_balance_c": tmin,
            "slope_at_low_per_c": float(slope[0]), "slope_at_high_per_c": float(slope[-1])}


def fit_load_model(fit: pd.DataFrame, hold: pd.DataFrame, col: str = "load_index") -> dict:
    """Model 2: fit hinge and spline load models; keep the one with lower 2026 holdout RMSE.

    Inputs: fit rows and holdout rows with calendar columns, temp_c and col.
    Output: dict with chosen ("hinge" | "spline"), candidates (per model: model dict, curve shape
        over the fit 1st-99th temperature percentiles, fit R2, holdout RMSE, fit and holdout
        residuals and predictions), spline_knots and spline_knot_cv_rmse.
    Note: because the holdout picks between the two models, the reported holdout RMSE of the
        chosen model is slightly optimistic.
    """
    y = fit[col].to_numpy()
    yh = hold[col].to_numpy()
    xc = calendar_design(fit)
    t = fit["temp_c"].to_numpy()
    k, knot_cv = choose_spline_knots(fit, y)
    fits = {"hinge": fit_hinge(xc, y, t), "spline": fit_spline(xc, y, t, spline_knots(t, k))}
    out = {"candidates": {}, "spline_knots": k,
           "spline_knot_cv_rmse": {str(kk): v for kk, v in knot_cv.items()}}
    lo, hi = np.quantile(t, [0.01, 0.99])
    for name, (curve, cal) in fits.items():
        model = package_load_model(curve, cal, fit)
        pred = predict_load_index(model, fit["month"], fit["hour"], fit["daytype"], t)
        pred_h = predict_load_index(model, hold["month"], hold["hour"], hold["daytype"], hold["temp_c"])
        out["candidates"][name] = {
            "model": model, "shape": curve_shape(curve, lo, hi),
            "r2_fit": float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()),
            "holdout_rmse": float(np.sqrt(((yh - pred_h) ** 2).mean())),
            "pred_fit": pred, "pred_hold": pred_h, "resid_fit": y - pred, "resid_hold": yh - pred_h}
    out["chosen"] = min(out["candidates"], key=lambda n: out["candidates"][n]["holdout_rmse"])
    return out


# ----------------------------------------------------------------------------- model 3

def _pair_stats(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """(Pearson, Spearman, covariance with ddof=1) of two equal-length arrays."""
    pear = float(np.corrcoef(a, b)[0, 1])
    spear = float(np.corrcoef(stats.rankdata(a), stats.rankdata(b))[0, 1])
    return pear, spear, float(np.cov(a, b)[0, 1])


def _normal_scores(x: np.ndarray) -> np.ndarray:
    """Normal scores Phi^-1(rank / (n + 1))."""
    return stats.norm.ppf(stats.rankdata(x) / (len(x) + 1))


def sigma_d_stats(v: dict[str, np.ndarray], season: np.ndarray) -> np.ndarray:
    """Pearson, Spearman and covariance for every pair (variances included) of DRIVER_VARS.

    Inputs: v maps each DRIVER_VARS name to an array (temp_c degC, load_index, dewpoint_c degC);
        season labels aligned with them.
    Output: array (len(GROUPS), len(PAIRS), 3) ordered GROUPS x PAIRS x (pearson, spearman, cov).
        Variance rows carry pearson = spearman = 1.
    """
    out = np.empty((len(GROUPS), len(PAIRS), 3))
    for gi, grp in enumerate(GROUPS):
        sel = np.ones(len(season), bool) if grp == "overall" else season == grp
        for pi, (a, b) in enumerate(PAIRS):
            if a == b:
                out[gi, pi] = (1.0, 1.0, float(np.var(v[a][sel], ddof=1)))
            else:
                out[gi, pi] = _pair_stats(v[a][sel], v[b][sel])
    return out


def copula_cell(season, hour) -> np.ndarray:
    """Copula cell label "<season>|<daypart>" (e.g. "JJA|12-17") from season and hour (0-23 Central)."""
    start = (np.asarray(hour) // DAYPART_HOURS) * DAYPART_HOURS
    part = np.char.add(np.char.zfill(start.astype(str), 2),
                       np.char.add("-", np.char.zfill((start + DAYPART_HOURS - 1).astype(str), 2)))
    return np.char.add(np.char.add(np.asarray(season).astype(str), "|"), part)


def copula_corr(r: dict[str, np.ndarray], key: np.ndarray, groups: tuple[str, ...]) -> np.ndarray:
    """Gaussian-copula correlation of COPULA_VARS (normal scores) within each group.

    Inputs: r maps each COPULA_VARS name to an array; key labels aligned with them (a season, or a
        copula cell from copula_cell); groups, the labels to compute (SEASONS or COPULA_CELLS).
    Output: array (len(groups), 3, 3) in COPULA_VARS order.
    """
    out = np.empty((len(groups), 3, 3))
    for gi, g in enumerate(groups):
        sel = key == g
        z = np.column_stack([_normal_scores(r[c][sel]) for c in COPULA_VARS])
        out[gi] = np.corrcoef(z, rowvar=False)
    return out


def block_bootstrap_indices(dates: np.ndarray, rng: np.random.Generator,
                            block_days: int = BLOCK_DAYS) -> np.ndarray:
    """Row indices for one moving-block bootstrap resample built from whole-day blocks.

    Inputs: Central date per row; random generator; block length in days.
    Output: index array. A block is block_days consecutive days that have data (it can span a
        dropped day such as the Uri week). The resample has about as many days as the original.
    """
    _, inv = np.unique(dates, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    rows_by_day = np.split(order, np.cumsum(np.bincount(inv))[:-1])
    n_days = len(rows_by_day)
    starts = rng.integers(0, n_days - block_days + 1, math.ceil(n_days / block_days))
    return np.concatenate([rows_by_day[s + k] for s in starts for k in range(block_days)])


def bootstrap_ci(fit: pd.DataFrame, resid: dict[str, np.ndarray], n_boot: int = N_BOOT,
                 seed: int = SEED) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """95% moving-block bootstrap CIs (7-day blocks) for sigma_d_stats and copula_corr.

    Inputs: fit rows (with DRIVER_VARS, season, hour, date); copula residuals aligned with fit rows.
    Output: (sigma CI, seasonal copula CI, cell copula CI), each with a leading axis of 2 holding
        the 2.5th and 97.5th percentiles over n_boot resamples.
    """
    rng = np.random.default_rng(seed)
    dates = fit["date"].to_numpy()
    v = {c: fit[c].to_numpy() for c in DRIVER_VARS}
    season = fit["season"].to_numpy()
    cell = copula_cell(season, fit["hour"].to_numpy())
    sig, cop_s, cop_c = [], [], []
    for _ in range(n_boot):
        idx = block_bootstrap_indices(dates, rng)
        rb = {c: a[idx] for c, a in resid.items()}
        sig.append(sigma_d_stats({c: a[idx] for c, a in v.items()}, season[idx]))
        cop_s.append(copula_corr(rb, season[idx], SEASONS))
        cop_c.append(copula_corr(rb, cell[idx], COPULA_CELLS))
    return tuple(np.percentile(x, [2.5, 97.5], axis=0) for x in (sig, cop_s, cop_c))


# ----------------------------------------------------------------------------- holdout

def holdout_validation(hold: pd.DataFrame, tab: pd.DataFrame, lm: dict) -> dict:
    """2026 holdout: load_index RMSE and bias for the chosen model; coverage of the 5-95% temp band.

    Inputs: holdout rows; Model 1 table; fit_load_model output.
    Output: {"load": {group: {n, rmse, bias}}, "temp_band_coverage": {group: share}} for
        overall and each season present. bias = mean(observed - predicted), load_index units.
        Coverage is the share of hours with q05_c <= temp_c <= q95_c of their month-hour; 0.90
        is the target.
    """
    resid = lm["candidates"][lm["chosen"]]["resid_hold"]
    m = hold[["month", "hour"]].merge(tab, on=["month", "hour"], how="left")
    inside = ((hold["temp_c"].to_numpy() >= m["q05_c"].to_numpy())
              & (hold["temp_c"].to_numpy() <= m["q95_c"].to_numpy()))
    out = {"load": {}, "temp_band_coverage": {}}
    for grp in GROUPS:
        sel = np.ones(len(hold), bool) if grp == "overall" else (hold["season"] == grp).to_numpy()
        if sel.sum() == 0:
            continue
        out["load"][grp] = {"n": int(sel.sum()), "rmse": float(np.sqrt((resid[sel] ** 2).mean())),
                            "bias": float(resid[sel].mean())}
        out["temp_band_coverage"][grp] = float(inside[sel].mean())
    return out


# ----------------------------------------------------------------------------- run

def run_fit(n_boot: int = N_BOOT) -> dict:
    """Run Models 1-3, the ERCOT cross-check and the holdout validation. Writes nothing.

    Inputs: n_boot, the number of bootstrap resamples.
    Output: dict with the data frames (df, fit, hold), Model 1 table (tab), load-model results
        (lm for NCENT, lm_ercot), copula residuals, Sigma_D statistics and CIs, copula correlations
        and CIs, residual autocorrelations, residual sd by group, holdout results and data checks.
    """
    df, fit, hold = prepare_data()
    tab = fit_temp_month_hour(fit)
    temp_z, dew_z = standardized_residuals(fit, tab)
    lm = fit_load_model(fit, hold, "load_index")
    lm_ercot = fit_load_model(fit, hold, "ercot_load_index")
    resid_l = lm["candidates"][lm["chosen"]]["resid_fit"]
    resid = {"temp_z": temp_z, "dew_z": dew_z, "load_resid": resid_l}
    season = fit["season"].to_numpy()
    sig = sigma_d_stats({c: fit[c].to_numpy() for c in DRIVER_VARS}, season)
    cell = copula_cell(season, fit["hour"].to_numpy())
    cop = copula_corr(resid, season, SEASONS)
    cop_cell = copula_corr(resid, cell, COPULA_CELLS)
    sig_ci, cop_ci, cop_cell_ci = bootstrap_ci(fit, resid, n_boot)
    resid_sd = {g: float(np.std(resid_l if g == "overall" else resid_l[season == g], ddof=1))
                for g in GROUPS}
    return {"df": df, "fit": fit, "hold": hold, "tab": tab, "lm": lm, "lm_ercot": lm_ercot,
            "resid": resid, "sigma": sig, "sigma_ci": sig_ci, "copula": cop, "copula_ci": cop_ci,
            "copula_cell": cop_cell, "copula_cell_ci": cop_cell_ci, "cell": cell,
            "resid_sd": resid_sd, "n_boot": n_boot, "cleaning": cleaning_counts(),
            "autocorr": {"temp_z": residual_autocorrelation(fit["hour_utc"], temp_z),
                         "load_resid": residual_autocorrelation(fit["hour_utc"], resid_l)},
            "holdout": holdout_validation(hold, tab, lm),
            "ncent_ercot_index_corr": float(np.corrcoef(df["load_index"], df["ercot_load_index"])[0, 1]),
            "load_index_year_mean": {int(k): float(v) for k, v in
                                     df.groupby("year")["load_index"].mean().items()},
            "load_index_basis_dates": {b: [str(g["date"].min().date()), str(g["date"].max().date())]
                                       for b, g in df.groupby("load_index_basis")}}


# ----------------------------------------------------------------------------- outputs

def load_model_json(r: dict) -> dict:
    """Content of load_model.json: the chosen NCENT load model plus fit diagnostics.

    Inputs: run_fit output.
    Output: JSON-ready dict. "model" is what predict_load_index and sample.py consume.
    """
    lm = r["lm"]
    c = lm["candidates"][lm["chosen"]]
    ercot = r["lm_ercot"]
    return {
        "description": ("NCENT load_index model. load_index = intercept + hour_daytype_effect[daytype][hour]"
                        " + month_effect[month-1] + fbar_month_hour[month-1][hour]"
                        " + coupling * (f(temp_c) - fbar_month_hour[month-1][hour]); f is the curve."
                        " Produced by ridethrough/drivers/fit.py."),
        "units": {"load_index": "dimensionless (hourly load / 365-day rolling mean of daily mean load)",
                  "temp_c": "degC", "slopes": "load_index per degC", "effects": "load_index"},
        "load_index_definition": {"window_days": ROLL_DAYS, "min_days": ROLL_MIN_DAYS,
                                  "basis_dates": r["load_index_basis_dates"],
                                  "year_mean": r["load_index_year_mean"]},
        "fit_years": list(FIT_YEARS), "holdout_year": HOLDOUT_YEAR,
        "n_fit": len(r["fit"]), "n_holdout": len(r["hold"]),
        "chosen": lm["chosen"], "model": c["model"], "shape": c["shape"], "r2_fit": c["r2_fit"],
        "residual_sd": r["resid_sd"], "residual_autocorrelation": r["autocorr"]["load_resid"],
        "holdout_2026": r["holdout"]["load"],
        "candidates": {n: {"shape": v["shape"], "r2_fit": v["r2_fit"], "holdout_rmse": v["holdout_rmse"]}
                       for n, v in lm["candidates"].items()},
        "spline_knots": lm["spline_knots"], "spline_knot_cv_rmse": lm["spline_knot_cv_rmse"],
        "ercot_crosscheck": {"chosen": ercot["chosen"],
                             "shape": ercot["candidates"][ercot["chosen"]]["shape"],
                             "r2_fit": ercot["candidates"][ercot["chosen"]]["r2_fit"],
                             "holdout_rmse": ercot["candidates"][ercot["chosen"]]["holdout_rmse"],
                             "ncent_ercot_index_corr": r["ncent_ercot_index_corr"]},
    }


def driver_covariance_table(r: dict) -> pd.DataFrame:
    """Content of driver_covariance.csv: Sigma_D in long format with 95% block-bootstrap CIs.

    Inputs: run_fit output.
    Output: one row per group (overall | DJF | MAM | JJA | SON) x pair, with group, var_i, var_j,
        n, pearson, pearson_lo, pearson_hi, spearman, spearman_lo, spearman_hi, covariance,
        covariance_lo, covariance_hi. Covariance units are the product of the two variables' units
        (temp_c and dewpoint_c in degC, load_index dimensionless); a variance row has var_i = var_j.
    """
    season = r["fit"]["season"].to_numpy()
    rows = []
    for gi, grp in enumerate(GROUPS):
        n = len(season) if grp == "overall" else int((season == grp).sum())
        for pi, (a, b) in enumerate(PAIRS):
            row = {"group": grp, "var_i": a, "var_j": b, "n": n}
            for si, name in enumerate(("pearson", "spearman", "covariance")):
                row[name] = r["sigma"][gi, pi, si]
                row[name + "_lo"] = r["sigma_ci"][0, gi, pi, si]
                row[name + "_hi"] = r["sigma_ci"][1, gi, pi, si]
            rows.append(row)
    return pd.DataFrame(rows)


def copula_json(r: dict) -> dict:
    """Content of driver_copula.json: Gaussian copula by season and by cell, marginals, calendar counts.

    Inputs: run_fit output.
    Output: JSON-ready dict.
        seasons: per season, n and corr (3 x 3 in COPULA_VARS order) with 95% CI bounds. Reported
            as the task's seasonal copula; the sampler does not use it.
        cells: per season x 6-hour daypart (COPULA_CELLS, e.g. "JJA|12-17"), n, corr with 95% CI
            bounds, and marginal quantiles of each copula variable at QUANTILE_PROBS. sample.py draws
            from these, because the temperature-load residual link varies by time of day (a single
            seasonal copula put the sampled JJA temp-load Spearman outside the data's CI).
        calendar_counts: fit-period (month, hour, daytype, n) that sample.py draws calendars from.
    """
    fit = r["fit"]
    season = fit["season"].to_numpy()
    seasons, cells = {}, {}
    for si, s in enumerate(SEASONS):
        seasons[s] = {"n": int((season == s).sum()),
                      "corr": r["copula"][si].tolist(),
                      "corr_lo": r["copula_ci"][0, si].tolist(),
                      "corr_hi": r["copula_ci"][1, si].tolist()}
    for ci, c in enumerate(COPULA_CELLS):
        sel = r["cell"] == c
        cells[c] = {
            "n": int(sel.sum()),
            "corr": r["copula_cell"][ci].tolist(),
            "corr_lo": r["copula_cell_ci"][0, ci].tolist(),
            "corr_hi": r["copula_cell_ci"][1, ci].tolist(),
            "marginal_quantiles": {v: np.quantile(r["resid"][v][sel], QUANTILE_PROBS).tolist()
                                   for v in COPULA_VARS}}
    cal = fit.groupby(["month", "hour", "daytype"]).size().rename("n").reset_index()
    return {
        "description": ("Gaussian copula of the driver residuals by season and by season x 6-hour"
                        " daypart (cells, used by sample.py). Produced by ridethrough/drivers/fit.py."),
        "daypart_hours": DAYPART_HOURS,
        "variables": list(COPULA_VARS),
        "variable_definitions": {
            "temp_z": "(temp_c - month-hour mean) / month-hour sd, from temp_by_month_hour.csv",
            "dew_z": "(dewpoint_c - month-hour mean) / month-hour sd, from temp_by_month_hour.csv",
            "load_resid": "load_index minus the chosen load model (load_model.json), load_index units"},
        "quantile_probs": QUANTILE_PROBS.tolist(),
        "seasons": seasons,
        "cells": cells,
        "calendar_counts": cal.to_dict(orient="records"),
        "n_boot": r["n_boot"], "block_days": BLOCK_DAYS, "seed": SEED,
    }


def make_figures(r: dict) -> dict[str, bytes]:
    """Draw the five report figures as PNG bytes (nothing is written here).

    Inputs: run_fit output.
    Output: {file name: PNG bytes} for FIGURES:
        fig_load_vs_temp.png   partial residual of load_index vs temp_c with both fitted curves
        fig_load_by_hour.png   mean load_index by hour, weekday vs weekend/holiday, observed and fitted
        fig_temp_heatmap.png   mean temp_c by month x hour
        fig_residuals.png      load residual by season; temp_z against a standard normal
        fig_holdout_2026.png   daily mean load_index in 2026, observed vs predicted
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fit, hold, lm = r["fit"], r["hold"], r["lm"]
    chosen = lm["candidates"][lm["chosen"]]
    t = fit["temp_c"].to_numpy()
    f_chosen = eval_temp_curve(chosen["model"]["curve"], t)
    partial = chosen["resid_fit"] + f_chosen
    out = {}

    def save(fig) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hexbin(t, partial, gridsize=70, mincnt=1, cmap="Greys", bins="log")
    grid = np.linspace(np.quantile(t, 0.001), np.quantile(t, 0.999), 300)
    for name, cand in lm["candidates"].items():
        f = eval_temp_curve(cand["model"]["curve"], grid)
        f = f - eval_temp_curve(cand["model"]["curve"], t).mean() + f_chosen.mean()
        ax.plot(grid, f, lw=2, label=f"{name}{' (chosen)' if name == lm['chosen'] else ''}")
    ax.set(xlabel="temp_c (degC)", ylabel="load_index partial residual",
           title="NCENT load_index vs temperature, calendar effects removed (2021-2025)")
    ax.legend()
    out["fig_load_vs_temp.png"] = save(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for dt, style in (("weekday", "-"), ("weekend_holiday", "--")):
        sel = (fit["daytype"] == dt).to_numpy()
        obs = pd.Series(fit["load_index"].to_numpy()[sel]).groupby(fit["hour"].to_numpy()[sel]).mean()
        pred = pd.Series(chosen["pred_fit"][sel]).groupby(fit["hour"].to_numpy()[sel]).mean()
        ax.plot(obs.index, obs.to_numpy(), style, color="k", label=f"{dt} observed")
        ax.plot(pred.index, pred.to_numpy(), style, color="tab:orange", label=f"{dt} fitted")
    ax.set(xlabel="hour (Central)", ylabel="mean load_index", title="Load by hour (2021-2025)")
    ax.legend()
    out["fig_load_by_hour.png"] = save(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    mat = r["tab"].pivot(index="month", columns="hour", values="mean_c")
    im = ax.imshow(mat.to_numpy(), aspect="auto", cmap="RdYlBu_r", origin="upper",
                   extent=(-0.5, 23.5, 12.5, 0.5))
    fig.colorbar(im, ax=ax, label="mean temp_c (degC)")
    ax.set(xlabel="hour (Central)", ylabel="month", title="DFW mean temperature by month x hour (2021-2025)")
    out["fig_temp_heatmap.png"] = save(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    season = fit["season"].to_numpy()
    for s in SEASONS:
        axes[0].hist(chosen["resid_fit"][season == s], bins=80, histtype="step", density=True, label=s)
    axes[0].set(xlabel="load_index residual", ylabel="density", title="Load residual by season")
    axes[0].legend()
    z = r["resid"]["temp_z"]
    axes[1].hist(z, bins=80, density=True, color="0.7", label="temp_z")
    zz = np.linspace(-4, 4, 200)
    axes[1].plot(zz, stats.norm.pdf(zz), "k", label="standard normal")
    axes[1].set(xlabel="temp_z", ylabel="density", title="Standardized temperature residual")
    axes[1].legend()
    out["fig_residuals.png"] = save(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    daily = pd.DataFrame({"date": hold["date"], "obs": hold["load_index"].to_numpy(),
                          "pred": chosen["pred_hold"]}).groupby("date").mean()
    ax.plot(daily.index, daily["obs"], "k", lw=1, label="observed")
    ax.plot(daily.index, daily["pred"], color="tab:orange", lw=1, label="predicted")
    ax.set(xlabel="date (2026)", ylabel="daily mean load_index", title="2026 holdout")
    ax.legend()
    fig.autofmt_xdate()
    out["fig_holdout_2026.png"] = save(fig)
    return out


def _fmt(x: float, nd: int = 3) -> str:
    """Format a number with nd decimals for the report."""
    return f"{x:.{nd}f}"


def build_report(r: dict) -> str:
    """Content of driver_fit_report.md, built only from run_fit results.

    Inputs: run_fit output.
    Output: Markdown text: data and cleaning, Models 1-3, ERCOT cross-check, 2026 holdout,
        figures and caveats.
    """
    lm, c, h = r["lm"], r["cleaning"], r["holdout"]
    L = ["# Driver fit report (Part A)", "",
         f"Produced by `ridethrough/drivers/fit.py` on {date.today().isoformat()}. "
         f"Fit years {FIT_YEARS[0]}-{FIT_YEARS[-1]}; holdout {HOLDOUT_YEAR}.", "",
         "## Data and cleaning", "",
         "| step | rows |", "|---|---|",
         f"| temperature file rows | {c['temp_rows']} |",
         f"| temperature flag `missing` dropped | {c['temp_missing']} |",
         f"| load file rows | {c['load_rows']} |",
         f"| load flag `zones_do_not_sum_to_total` dropped | {c['load_zone_mismatch']} |",
         f"| hours in both files (join on hour_utc) | {c['joined']} |",
         f"| Uri load-shed hours dropped (2021-02-14 to 2021-02-20 Central) | {c['uri_dropped']} |",
         f"| final | {c['final']} (fit {len(r['fit'])}, holdout {len(r['hold'])}) |", "",
         "Timing: temp_c is an instantaneous top-of-hour reading; load is the mean over the hour that "
         "begins at hour_utc, so each temperature leads its load average by about 30 minutes.", "",
         "load_index = hourly NCENT load / 365-day rolling mean of daily mean load. Window used by date:", ""]
    for b, (d0, d1) in r["load_index_basis_dates"].items():
        L.append(f"- {b}: {d0} to {d1}")
    L += ["", "Mean load_index by year (complete years should be close to 1.0):", "",
          "| year | mean |", "|---|---|"]
    L += [f"| {y} | {_fmt(v)} |" for y, v in r["load_index_year_mean"].items()]
    L += ["", f"{HOLDOUT_YEAR} covers January to September only and uses the trailing window, so its "
              "mean is not expected to be 1.0.", "",
          "## Model 1: temperature by month x hour", "",
          "Mean, sd, n, 5th and 95th percentiles of temp_c and the dewpoint mean and sd for each "
          "month x hour: `temp_by_month_hour.csv`. Standardized residual (temp_z) autocorrelation:", "",
          "| lag | temp_z | load residual |", "|---|---|---|"]
    for k in r["autocorr"]["temp_z"]:
        L.append(f"| {k.replace('lag_', '')} | {_fmt(r['autocorr']['temp_z'][k])} | "
                 f"{_fmt(r['autocorr']['load_resid'][k])} |")
    L += ["", "Residuals are strongly autocorrelated hour to hour, so CIs below use a 7-day block bootstrap.", "",
          "## Model 2: load_index ~ f(temp) + hour x daytype + month", "",
          "| model | heating balance (degC) | cooling balance (degC) | slope at cold end (per degC) | "
          "slope at hot end (per degC) | R2 fit | holdout RMSE |", "|---|---|---|---|---|---|---|"]
    for n, v in lm["candidates"].items():
        s = v["shape"]
        L.append(f"| {n}{' (chosen)' if n == lm['chosen'] else ''} | {_fmt(s['heat_balance_c'], 1)} | "
                 f"{_fmt(s['cool_balance_c'], 1)} | {_fmt(s['slope_at_low_per_c'], 4)} | "
                 f"{_fmt(s['slope_at_high_per_c'], 4)} | {_fmt(v['r2_fit'])} | {_fmt(v['holdout_rmse'], 4)} |")
    L += ["", f"Spline knots: {lm['spline_knots']}, chosen by leave-one-year-out RMSE "
              f"({', '.join(f'{k}: {_fmt(v, 4)}' for k, v in lm['spline_knot_cv_rmse'].items())}). "
              "For the spline, the balance point is the minimum of the curve; slopes are at the 1st and "
              "99th temperature percentiles. The holdout picked between hinge and spline, so the chosen "
              "model's holdout RMSE is slightly optimistic.", "",
          "Residual sd of the chosen model (load_index):", "",
          "| group | sd |", "|---|---|"]
    L += [f"| {g} | {_fmt(v, 4)} |" for g, v in r["resid_sd"].items()]
    e = r["lm_ercot"]
    es = e["candidates"][e["chosen"]]
    L += ["", f"ERCOT cross-check ({e['chosen']}): balance {_fmt(es['shape']['heat_balance_c'], 1)} / "
              f"{_fmt(es['shape']['cool_balance_c'], 1)} degC, end slopes {_fmt(es['shape']['slope_at_low_per_c'], 4)}"
              f" / {_fmt(es['shape']['slope_at_high_per_c'], 4)} per degC, R2 {_fmt(es['r2_fit'])}. "
              f"Correlation of NCENT and ERCOT load_index: {_fmt(r['ncent_ercot_index_corr'])}.", "",
          f"## Model 3: Sigma_D for temp_c, load_index, dewpoint_c", "",
          f"95% CIs from a moving-block bootstrap with {BLOCK_DAYS}-day blocks, {r['n_boot']} resamples. "
          "Full table with covariances: `driver_covariance.csv`.", "",
          "| group | pair | Pearson [CI] | Spearman [CI] | covariance [CI] |", "|---|---|---|---|---|"]
    tab = driver_covariance_table(r)
    for _, row in tab[tab["var_i"] != tab["var_j"]].iterrows():
        L.append(f"| {row['group']} | {row['var_i']}-{row['var_j']} | {_fmt(row['pearson'])} "
                 f"[{_fmt(row['pearson_lo'])}, {_fmt(row['pearson_hi'])}] | {_fmt(row['spearman'])} "
                 f"[{_fmt(row['spearman_lo'])}, {_fmt(row['spearman_hi'])}] | {_fmt(row['covariance'])} "
                 f"[{_fmt(row['covariance_lo'])}, {_fmt(row['covariance_hi'])}] |")
    L += ["", "Gaussian copula correlation of the residuals (temp_z, dew_z, load_resid) by season, and by "
              f"season x {DAYPART_HOURS}-hour daypart (Central). The sampler uses the daypart cells: with one "
              "copula per season, the sampled JJA temp-load Spearman fell below the data's CI, because "
              "the temperature-load residual link differs by time of day.", "",
          "| season or cell | temp_z-dew_z [CI] | temp_z-load_resid [CI] | dew_z-load_resid [CI] |",
          "|---|---|---|---|"]
    rows = [(s, r["copula"][si], r["copula_ci"][:, si]) for si, s in enumerate(SEASONS)]
    rows += [(c, r["copula_cell"][ci], r["copula_cell_ci"][:, ci]) for ci, c in enumerate(COPULA_CELLS)]
    for label, corr, ci in rows:
        cells = [f"{_fmt(corr[i, j])} [{_fmt(ci[0, i, j])}, {_fmt(ci[1, i, j])}]"
                 for i, j in ((0, 1), (0, 2), (1, 2))]
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L += ["", f"## Holdout {HOLDOUT_YEAR}", "",
          "| group | hours | load_index RMSE | bias (observed - predicted) | temp 5-95% band coverage |",
          "|---|---|---|---|---|"]
    for g, v in h["load"].items():
        L.append(f"| {g} | {v['n']} | {_fmt(v['rmse'], 4)} | {_fmt(v['bias'], 4)} | "
                 f"{_fmt(h['temp_band_coverage'][g])} |")
    L += ["", "Band coverage target is 0.90. SON in 2026 contains September only.", "",
          "## Figures", ""]
    L += [f"![{f}]({f})" for f in FIGURES]
    L += ["", "## Caveats", "",
          "- Temperature leads the load average by about 30 minutes (join as specified).",
          "- The holdout was used to choose between hinge and spline.",
          f"- {HOLDOUT_YEAR} load_index uses the trailing window from "
          f"{r['load_index_basis_dates'].get('trailing', ['?'])[0]} and is a partial year.",
          "- Bootstrap blocks may span the dropped Uri week.",
          "- Grid load (NCENT) is far more temperature-sensitive than a data center's load; Part B "
          "scales the temperature-load link by `coupling` (0, 0.5, 1.0).", ""]
    return "\n".join(L)


def build_outputs(r: dict) -> dict[str, str | bytes]:
    """Build every output file's content in memory.

    Inputs: run_fit output.
    Output: {file name: content}; text for CSV/JSON/MD, bytes for PNG.
    """
    files: dict[str, str | bytes] = {
        "temp_by_month_hour.csv": r["tab"].to_csv(index=False, float_format="%.4f"),
        "load_model.json": json.dumps(load_model_json(r), indent=2),
        "driver_covariance.csv": driver_covariance_table(r).to_csv(index=False, float_format="%.6g"),
        "driver_copula.json": json.dumps(copula_json(r), indent=2),
    }
    files.update(make_figures(r))
    files["driver_fit_report.md"] = build_report(r)
    return files


def write_outputs(files: dict[str, str | bytes], out_dir: Path | None = None) -> list[Path]:
    """Write the built outputs into out_dir (default OUT_DIR, read at call time; created if needed).

    Returns the written paths.
    """
    out_dir = OUT_DIR if out_dir is None else out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, content in files.items():
        p = out_dir / name
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content)
        paths.append(p)
    return paths


def main() -> None:
    """Run the fit, write all outputs to OUT_DIR, and print the headline results."""
    r = run_fit()
    files = build_outputs(r)
    for p in write_outputs(files):
        print("wrote", p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p)
    ch = r["lm"]["candidates"][r["lm"]["chosen"]]
    s = ch["shape"]
    print(f"load model: {r['lm']['chosen']}, balance {s['heat_balance_c']:.1f} / {s['cool_balance_c']:.1f} degC, "
          f"end slopes {s['slope_at_low_per_c']:.4f} / {s['slope_at_high_per_c']:.4f} per degC, "
          f"R2 {ch['r2_fit']:.3f}, holdout RMSE {r['holdout']['load']['overall']['rmse']:.4f}")
    pi = PAIRS.index(("temp_c", "load_index"))
    for gi, g in enumerate(GROUPS):
        print(f"temp-load Spearman {g}: {r['sigma'][gi, pi, 1]:.3f} "
              f"[{r['sigma_ci'][0, gi, pi, 1]:.3f}, {r['sigma_ci'][1, gi, pi, 1]:.3f}]")


if __name__ == "__main__":
    main()
