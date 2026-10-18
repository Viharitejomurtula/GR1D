/**
 * Gets a verdict for a scenario: the live simulator when it is reachable, the precomputed
 * grid when it is not.
 *
 * The live path runs the real OpenModelica model per request (~0.3 s) and accepts any
 * input. The grid holds exact simulator output for every slider position, so a failed API
 * call degrades the demo rather than ending it.
 *
 * `source` says which answered. Show it — a viewer should be able to tell whether they are
 * seeing a fresh run or a stored one.
 */

import { loadGrid, lookup, type Grid } from './grid';

/** Time series for the replay panel, downsampled by the API. */
export type ApiTrace = {
  t: number[];
  voltage_pu: number[];
  facility_pct: number[];
  battery_pct: number[];
  t0: number;
  t1: number;
  back: number | null;
  deadline: number | null;
  reached90: number | null;
  min_pct: number;
};

export type Verdict = {
  passed: boolean;
  failureMode: string;
  recoveryMargin: number;
  peakCurrent: number;
  minPower?: number;
  finalPowerFrac?: number;
  storageLeft?: number;
  trips?: string[];
  source: 'simulator' | 'precomputed';
  /** Set when the scenario was snapped to grid points. */
  snapped?: Record<string, number>;
  /** Only present on a live run that asked for it; the grid stores no time series. */
  trace?: ApiTrace;
};

export type SimulateOptions = {
  apiUrl?: string;
  preset?: 'grid_friendly' | 'legacy_ups';
  /** Give up on the API after this long and use the grid. */
  timeoutMs?: number;
  /** Ask for the time series as well as the verdict. Live path only. */
  includeTrace?: boolean;
};

const DEFAULT_API = import.meta.env?.VITE_API_URL ?? '/api';

let gridPromise: Promise<Grid> | null = null;
const grid = () => (gridPromise ??= loadGrid());

/** True when the API answered a health check. Worth calling once on mount. */
export async function apiAvailable(apiUrl = DEFAULT_API, timeoutMs = 3000): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(`${apiUrl}/health`, { signal: ctrl.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

export async function simulate(
  scenario: Record<string, number>,
  opts: SimulateOptions = {}
): Promise<Verdict> {
  const {
    apiUrl = DEFAULT_API,
    preset = 'grid_friendly',
    timeoutMs = 8000,
    includeTrace = false,
  } = opts;

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(`${apiUrl}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset, overrides: scenario, include_trace: includeTrace }),
      signal: ctrl.signal,
    });
    clearTimeout(timer);

    if (res.ok) {
      const d = await res.json();
      return {
        passed: d.passed,
        failureMode: d.failure_mode,
        recoveryMargin: d.recovery_margin_s,
        peakCurrent: d.peak_current_pu,
        minPower: d.min_power,
        finalPowerFrac: d.final_power_frac,
        storageLeft: d.storage_left,
        trips: d.trips,
        source: 'simulator',
        trace: d.trace ?? undefined,
      };
    }

    // 422 means the solver could not converge for this combination. That is a real answer
    // about this scenario, not a transport failure, so the grid will not do better --
    // its cell is null for the same reason.
    if (res.status === 422) {
      const d = await res.json().catch(() => ({}));
      throw new NoResult(d.detail ?? 'simulation did not converge');
    }
  } catch (err) {
    if (err instanceof NoResult) throw err;
    // Anything else — offline, timeout, CORS, cold start — falls through to the grid.
  }

  const g = await grid();
  const cell = lookup(g, scenario);
  if (!cell) throw new NoResult('no precomputed result for this combination');

  return {
    passed: cell.passed,
    failureMode: cell.failureMode,
    recoveryMargin: cell.recoveryMargin,
    peakCurrent: cell.peakCurrent,
    source: 'precomputed',
    snapped: cell.snapped,
  };
}

/** The scenario has no answer — the solver did not converge. Not a transport error. */
export class NoResult extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NoResult';
  }
}
