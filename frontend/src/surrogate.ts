/**
 * Runs the ride-through surrogate in the browser.
 *
 * The real simulator needs OpenModelica, so every live answer costs a server round trip. This
 * evaluates the trained ensemble (surrogate/models/v1, exported by `python -m surrogate.web`)
 * directly: the forward pass is a few small matrix products per member, so there is no
 * inference runtime to load and no network call after the weights arrive.
 *
 * The same JSON is evaluated by the API (`POST /predict`, numpy) and checked against the
 * PyTorch model it came from, so the browser, the backend and the training code agree.
 *
 * The ensemble's spread is the useful part: where members disagree the surrogate is guessing,
 * and `outsideTraining` names inputs beyond anything it was trained on. The UI should say so
 * rather than presenting a confident number.
 */

export type Layer = { w: number[][]; b: number[] };

export type SurrogateModel = {
  format: 'gr1d-surrogate-ensemble/2';
  activation: 'silu';
  continuous: { name: string; mean: number; std: number; low: number | null; high: number | null }[];
  categorical: { name: string; levels: number[] }[];
  excluded: string[];
  ood_margin_frac: number;
  heads: string[];
  targets: Record<string, { mean: number; std: number; log1p: boolean; std_scale: number; lower: number | null; upper: number | null }>;
  classes: string[];
  presets: Record<'grid_friendly' | 'legacy_ups', Record<string, number>>;
  members: { layers: Layer[]; scalar: Layer; classes: Layer }[];
  /** Real sampler draws (values in `background_fields` order) for marginal estimates. */
  background: number[][];
  background_fields: string[];
  metrics: { test: Record<string, number>; edge: Record<string, number>; n_rows: number };
  provenance: { simulator_commit: string | null; dirty: boolean | null; rows: number | null; model_dir: string };
};

export type Estimate = { mean: number; std: number };

export type Prediction = {
  passProbability: number;
  /** Spread of the members' pass probabilities. High means the surrogate is guessing. */
  uncertainty: number;
  /** Seconds of slack against the 2.0 s recovery deadline; negative means missed. Capped at 2.0. */
  recoveryMargin: number;
  /** Mean and calibrated spread (about 95% of test errors fall within +/- 2 std) for each output. */
  outputs: {
    recovery_margin_s: Estimate;
    min_power: Estimate;
    peak_current_pu: Estimate;
    floor_violation_s: Estimate;
  };
  failureMode: string;
  modeProbabilities: Record<string, number>;
  /** Inputs outside the training data: the prediction there is an extrapolation. */
  outsideTraining: string[];
};

const silu = (v: number): number => v / (1 + Math.exp(-v));
const sigmoid = (v: number): number => 1 / (1 + Math.exp(-v));

const dense = (x: number[], layer: Layer): number[] => {
  const out = layer.b.slice();
  for (let i = 0; i < x.length; i++) {
    const xi = x[i];
    if (xi === 0) continue;
    const row = layer.w[i];
    for (let j = 0; j < out.length; j++) out[j] += xi * row[j];
  }
  return out;
};

const softmax = (x: number[]): number[] => {
  const max = Math.max(...x);
  const exp = x.map((v) => Math.exp(v - max));
  const sum = exp.reduce((a, b) => a + b, 0);
  return exp.map((v) => v / sum);
};

const meanStd = (xs: number[]): Estimate => {
  const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
  return { mean, std: Math.sqrt(xs.reduce((a, b) => a + (b - mean) ** 2, 0) / xs.length) };
};

const close = (a: number, b: number) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));

export async function loadSurrogate(url = '/data/surrogate.json'): Promise<SurrogateModel> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`surrogate failed to load: ${res.status}`);
  const model = (await res.json()) as SurrogateModel;
  if (model.format !== 'gr1d-surrogate-ensemble/2') throw new Error(`unsupported surrogate format ${model.format}`);
  return model;
}

/** Features in the order the network expects, plus the inputs outside the training range. */
function encode(model: SurrogateModel, s: Record<string, number>): { x: number[]; outside: string[] } {
  const x: number[] = [];
  const outside: string[] = [];
  for (const c of model.continuous) {
    const v = s[c.name];
    x.push((v - c.mean) / c.std);
    if (c.low !== null && c.high !== null) {
      const tol = model.ood_margin_frac * (c.high - c.low) + 1e-9 * Math.max(1, Math.abs(c.low), Math.abs(c.high));
      if (v < c.low - tol || v > c.high + tol) outside.push(c.name);
    }
  }
  for (const c of model.categorical) {
    const v = s[c.name];
    const hits = c.levels.map((lv) => close(v, lv));
    if (!hits.some(Boolean)) outside.push(c.name);
    hits.forEach((h) => x.push(h ? 1 : 0));
  }
  return { x, outside };
}

export type Marginal = {
  /** Share of background scenarios passing with `fixed` held, averaged over members. */
  passRate: number;
  /** Spread of that share across ensemble members. */
  passRateStd: number;
  /** Most common predicted failure mode among the background scenarios (null if all pass). */
  mode: string | null;
  modeShare: number;
  /** Fixed inputs outside the training range. */
  outsideTraining: string[];
};

/**
 * Hold the inputs in `fixed` and vary everything else over the shipped background scenarios (real
 * sampler draws): "under these conditions, what share of runs pass?". Same rule as the API's
 * WebSurrogate.marginal(). About 300 x members forward passes, a few tens of ms.
 */
export function marginal(model: SurrogateModel, fixed: Record<string, number>): Marginal {
  const perMember = new Array<number>(model.members.length).fill(0);
  const modes: Record<string, number> = {};
  for (const row of model.background) {
    const s: Record<string, number> = {};
    model.background_fields.forEach((f, i) => (s[f] = row[i]));
    Object.assign(s, fixed);
    const { x } = encode(model, s);
    const sums = new Array<number>(model.classes.length).fill(0);
    model.members.forEach((m, k) => {
      let h = x;
      for (const layer of m.layers) h = dense(h, layer).map(silu);
      perMember[k] += sigmoid(dense(h, m.scalar)[0]);
      softmax(dense(h, m.classes)).forEach((p, i) => (sums[i] += p));
    });
    const best = model.classes[sums.indexOf(Math.max(...sums))];
    if (best !== 'passed') modes[best] = (modes[best] ?? 0) + 1;
  }
  const n = model.background.length;
  const rate = meanStd(perMember.map((v) => v / n));
  const top = Object.entries(modes).sort((a, b) => b[1] - a[1])[0];
  const { outside } = encode(model, { ...model.presets.grid_friendly, ...fixed });
  return {
    passRate: rate.mean,
    passRateStd: rate.std,
    mode: top ? top[0] : null,
    modeShare: top ? top[1] / n : 0,
    outsideTraining: outside.filter((f) => f in fixed),
  };
}

/**
 * Scenario values keyed by Scenario field name. Anything omitted is taken from the preset
 * (the same rule as the API's /simulate and /predict), so a UI exposing four sliders does not
 * have to supply all fifty-odd inputs.
 */
export function predict(
  model: SurrogateModel,
  scenario: Record<string, number>,
  preset: 'grid_friendly' | 'legacy_ups' = 'grid_friendly'
): Prediction {
  const full: Record<string, number> = { ...model.presets[preset] };
  for (const [k, v] of Object.entries(scenario)) if (v !== undefined && !Number.isNaN(v)) full[k] = v;
  const { x, outside } = encode(model, full);

  const regNames = model.heads.slice(1);
  const passes: number[] = [];
  const reg: Record<string, number[]> = Object.fromEntries(regNames.map((t) => [t, []]));
  const modeSums = new Array<number>(model.classes.length).fill(0);

  for (const m of model.members) {
    let h = x;
    for (const layer of m.layers) h = dense(h, layer).map(silu);
    const sc = dense(h, m.scalar);
    passes.push(sigmoid(sc[0]));
    regNames.forEach((t, i) => {
      const spec = model.targets[t];
      let y = sc[i + 1] * spec.std + spec.mean;
      if (spec.log1p) y = Math.expm1(y);
      if (spec.lower !== null && spec.lower !== undefined) y = Math.max(y, spec.lower);
      reg[t].push(spec.upper !== null ? Math.min(y, spec.upper) : y);
    });
    softmax(dense(h, m.classes)).forEach((p, i) => (modeSums[i] += p));
  }

  const n = model.members.length;
  const pass = meanStd(passes);
  const outputs = Object.fromEntries(
    regNames.map((t) => {
      const e = meanStd(reg[t]);
      return [t, { mean: e.mean, std: e.std * model.targets[t].std_scale }];
    })
  ) as Prediction['outputs'];
  const modeProbabilities: Record<string, number> = {};
  model.classes.forEach((c, i) => (modeProbabilities[c] = modeSums[i] / n));
  const failureMode = model.classes.reduce((a, b) => (modeProbabilities[a] >= modeProbabilities[b] ? a : b));

  return {
    passProbability: pass.mean,
    uncertainty: pass.std,
    recoveryMargin: outputs.recovery_margin_s.mean,
    outputs,
    failureMode,
    modeProbabilities,
    outsideTraining: outside,
  };
}
