/**
 * Looks up precomputed simulator results for the interactive explorer.
 *
 * Every combination the sliders can reach was simulated ahead of time, so this returns
 * exact simulator output rather than a prediction — no server, no inference, and nothing
 * that can be wrong at the pass/fail boundary.
 *
 * Cells are null where the solver did not converge. Show that as "no result" rather than
 * inventing one; a missing answer is honest and a wrong one is not.
 */

export type GridCell = {
  /** 1 = meets the ERCOT rule */
  p: 0 | 1;
  /** index into `modes` */
  m: number;
  /** seconds of slack against the 2.0 s recovery deadline; negative means missed */
  r: number;
  /** peak current, per unit of normal operating current */
  c: number;
};

export type Annotation = {
  /** Shaded regions, e.g. real fault-clearing times. */
  bands?: { from: number; to: number; label: string }[];
  /** Single ticks, e.g. the documented ERCOT events. */
  marks?: { v: number; label: string }[];
  /** One line explaining what the shading means. */
  note?: string;
};

export type Grid = {
  axes: Record<string, number[]>;
  annotations: Record<string, Annotation>;
  order: string[];
  shape: number[];
  modes: string[];
  design: string;
  cells: (GridCell | null)[];
};

export type GridResult = {
  passed: boolean;
  failureMode: string;
  recoveryMargin: number;
  peakCurrent: number;
  /** Values actually used, after snapping to the nearest grid point. */
  snapped: Record<string, number>;
};

export async function loadGrid(url = '/data/ridethrough_grid.json'): Promise<Grid> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`grid failed to load: ${res.status}`);
  return res.json();
}

const nearestIndex = (values: number[], target: number): number => {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < values.length; i++) {
    const d = Math.abs(values[i] - target);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  }
  return best;
};

/**
 * Snaps each slider to its nearest grid point and returns that cell. Null when the
 * combination did not converge.
 */
export function lookup(grid: Grid, scenario: Record<string, number>): GridResult | null {
  const indices: number[] = [];
  const snapped: Record<string, number> = {};

  for (const name of grid.order) {
    const values = grid.axes[name];
    const i = nearestIndex(values, scenario[name] ?? values[Math.floor(values.length / 2)]);
    indices.push(i);
    snapped[name] = values[i];
  }

  // Row-major over `order`, matching itertools.product in make_grid.py.
  let flat = 0;
  for (let d = 0; d < indices.length; d++) flat = flat * grid.shape[d] + indices[d];

  const cell = grid.cells[flat];
  if (!cell) return null;

  return {
    passed: cell.p === 1,
    failureMode: grid.modes[cell.m] ?? 'unknown',
    recoveryMargin: cell.r,
    peakCurrent: cell.c,
    snapped,
  };
}

/** Shading and ticks for a slider, empty when the axis has none. */
export function annotations(grid: Grid, name: string): Annotation {
  return grid.annotations?.[name] ?? {};
}

/** Slider bounds, read from the grid so the UI cannot offer a value that was not computed. */
export function bounds(grid: Grid, name: string): { min: number; max: number; step: number } {
  const v = grid.axes[name];
  return {
    min: v[0],
    max: v[v.length - 1],
    step: v.length > 1 ? (v[v.length - 1] - v[0]) / (v.length - 1) : 1,
  };
}
