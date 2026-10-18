/**
 * Runs the ride-through surrogate in the browser.
 *
 * The real simulator needs OpenModelica, so exposing it to a user would mean standing up
 * a server. This evaluates a small trained network directly — the whole forward pass is
 * matrix multiplication, so there is no inference runtime to load and no network call.
 *
 * The ensemble's spread is the useful part: where members disagree the surrogate is
 * guessing, and the UI should say so rather than presenting a confident number.
 */

export type Layer = { w: number[][]; b: number[] };
export type Member = {
  trunk: Layer[];
  heads: { pass: Layer; margin: Layer; mode: Layer };
};

export type SurrogateModel = {
  inputs: string[];
  modes: string[];
  mu: number[];
  sd: number[];
  members: Member[];
  accuracy: {
    ensemble: number;
    boundary: number;
    n_train: number;
    n_test: number;
  };
};

export type Prediction = {
  passProbability: number;
  /** Spread across ensemble members. High means the surrogate is guessing. */
  uncertainty: number;
  /** Seconds of slack against the 2.0 s recovery deadline; negative means missed. */
  recoveryMargin: number;
  failureMode: string;
  modeProbabilities: Record<string, number>;
};

const dense = (x: number[], layer: Layer): number[] => {
  const out = new Array<number>(layer.b.length);
  for (let j = 0; j < layer.b.length; j++) {
    let s = layer.b[j];
    for (let i = 0; i < x.length; i++) s += x[i] * layer.w[i][j];
    out[j] = s;
  }
  return out;
};

const relu = (x: number[]): number[] => x.map((v) => (v > 0 ? v : 0));
const sigmoid = (v: number): number => 1 / (1 + Math.exp(-v));

const softmax = (x: number[]): number[] => {
  const max = Math.max(...x);
  const exp = x.map((v) => Math.exp(v - max));
  const sum = exp.reduce((a, b) => a + b, 0);
  return exp.map((v) => v / sum);
};

export async function loadSurrogate(url = '/data/surrogate.json'): Promise<SurrogateModel> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`surrogate failed to load: ${res.status}`);
  return res.json();
}

/**
 * Scenario values keyed by the names in `model.inputs`. Anything omitted falls back to the
 * training-set mean, which is the neutral choice: a UI exposing six sliders does not have
 * to supply all thirty-six inputs.
 */
export function predict(model: SurrogateModel, scenario: Record<string, number>): Prediction {
  const x = model.inputs.map((name, i) => {
    const raw = scenario[name];
    const v = raw === undefined || Number.isNaN(raw) ? model.mu[i] : raw;
    return (v - model.mu[i]) / model.sd[i];
  });

  const passes: number[] = [];
  const margins: number[] = [];
  const modeSums = new Array<number>(model.modes.length).fill(0);

  for (const member of model.members) {
    let h = x;
    for (const layer of member.trunk) h = relu(dense(h, layer));
    passes.push(sigmoid(dense(h, member.heads.pass)[0]));
    margins.push(dense(h, member.heads.margin)[0]);
    softmax(dense(h, member.heads.mode)).forEach((p, i) => (modeSums[i] += p));
  }

  const n = model.members.length;
  const mean = passes.reduce((a, b) => a + b, 0) / n;
  const variance = passes.reduce((a, b) => a + (b - mean) ** 2, 0) / n;

  const modeProbabilities: Record<string, number> = {};
  model.modes.forEach((m, i) => (modeProbabilities[m] = modeSums[i] / n));
  const best = model.modes.reduce((a, b) =>
    modeProbabilities[a] >= modeProbabilities[b] ? a : b
  );

  return {
    passProbability: mean,
    uncertainty: Math.sqrt(variance),
    recoveryMargin: margins.reduce((a, b) => a + b, 0) / n,
    failureMode: best,
    modeProbabilities,
  };
}
