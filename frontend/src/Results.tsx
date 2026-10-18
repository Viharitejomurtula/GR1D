import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import sampleRuns from './data/sample.json'
import eventRuns from './data/events.json'
import { simulate } from './simulate'
import { loadSurrogate, marginal, type SurrogateModel } from './surrogate'

// ILLUSTRATIVE VALUES: the pipeline does not produce these outputs yet. Every number on this tab comes from the
// placeholder dataset below, so the header, map, report card and scenario estimate agree with each other.
// Connected to the simulator. SAMPLE is real graded runs (scripts/export_sample.py from
// data/runs.csv); EVENTS is six replays of the documented ERCOT dips
// (scripts/export_events.py). Regenerate either and rebuild to refresh the page.

// ---- the variable list: every slider, axis and label reads its range from here (see the hookup notes) ----
type VarKey = 'depth' | 'duration' | 'temp' | 'age'
type Var = {
  column: string // column in data/runs.csv
  label: string
  help: string
  unit: string
  min: number
  max: number
  step: number
  ticks: number[]
  fmt: (v: number) => string
  low: string // plain words for the low end, used in the summary
  high: string
  bands?: { from: number; to: number; label: string }[] // where real data actually falls
  marks?: { v: number; label: string }[]
}

const VARS: Record<VarKey, Var> = {
  depth: {
    column: 'dip_depth_pu', label: 'Dip depth', help: 'Lowest voltage during the dip. Lower is deeper.', unit: 'pu',
    min: 0, max: 0.9, step: 0.01, ticks: [0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9], fmt: (v) => `${v.toFixed(2)} pu`,
    low: 'deep dips', high: 'shallow dips',
    marks: [{ v: 0.535, label: 'TX 0.535' }, { v: 0.67, label: 'TX 0.670' }, { v: 0.844, label: 'TX 0.844' }],
  },
  duration: {
    // stored in seconds (dip_duration_s); shown in ms
    column: 'dip_duration_s', label: 'Dip duration', help: 'How long the voltage stays low.', unit: 'ms',
    min: 50, max: 320, step: 1, ticks: [50, 100, 150, 200, 250, 300], fmt: (v) => `${Math.round(v)} ms`,
    low: 'short dips', high: 'long dips',
    bands: [{ from: 50, to: 67, label: 'normal clearing' }, { from: 167, to: 317, label: 'delayed clearing' }],
  },
  temp: {
    column: 'outdoor_temp_c', label: 'Outdoor temperature', help: 'Air temperature at the site when the dip hits.', unit: '°C',
    min: -20, max: 45, step: 1, ticks: [-20, -10, 0, 10, 20, 30, 40], fmt: (v) => `${Math.round(v)} °C`,
    low: 'cold days', high: 'hot days',
    marks: [{ v: 35, label: 'inverter derates above 35 °C' }],
  },
  age: {
    column: 'battery_age_yr', label: 'Battery age', help: 'Older batteries hold less charge and deliver less current.', unit: 'yr',
    min: 0, max: 10, step: 0.5, ticks: [0, 2, 4, 6, 8, 10], fmt: (v) => `${v % 1 ? v.toFixed(1) : v} yr`,
    low: 'new batteries', high: 'old batteries',
  },
}
const KEYS = Object.keys(VARS) as VarKey[]
type Scenario = Record<VarKey, number>
const PRESET: Scenario = { depth: 0.62, duration: 120, temp: 41, age: 2 }

const MODES = {
  'exceeded 125% current cap': {
    name: 'Current cap exceeded', color: '#ff8a3d',
    what: 'The site pulls more than 125% of its normal current during the dip. A constant-power load draws more amps as voltage falls, and NOGRR 282 section 2.14(2)(d) caps that at 125%.',
    fix: 'Not yet determined', fixNote: 'Needs a fix search',
    setting: 'Not yet determined', settingNote: 'Needs a sensitivity analysis',
  },
  'cooling tripped': {
    name: 'Cooling tripped', color: '#ffd873',
    what: 'Chiller motors drop out on undervoltage. Fans and pumps come back after 0.25 s, but compressors stay off for the rest of the event, so that share of load never returns.',
    fix: 'Not yet determined', fixNote: 'Needs a fix search',
    setting: 'Not yet determined', settingNote: 'Needs a sensitivity analysis',
  },
  'below power floor': {
    name: 'Below the power floor', color: '#ff4a3a',
    what: 'The site sheds more load than the rule allows. Between 0.80 and 0.50 pu the reduction has to stay proportional to the voltage drop.',
    fix: 'Not yet determined', fixNote: 'Needs a fix search',
    setting: 'Not yet determined', settingNote: 'Needs a sensitivity analysis',
  },
  'storage hand-back too slow': {
    name: 'Hand-back too slow', color: '#e0725c',
    what: 'The battery is still carrying the load when the 2 s deadline passes, so the grid never sees the demand return in time.',
    fix: 'Not yet determined', fixNote: 'Needs a fix search',
    setting: 'Not yet determined', settingNote: 'Needs a sensitivity analysis',
  },
  'PSU shutdown and restart delay': {
    name: 'Power-supply restart', color: '#c86fd4',
    what: 'Rack power supplies shut down and then wait to restart. After a battery discharge the Open Rack V3 spec allows 1 to 8.5 s, including a deliberate random delay, which is longer than the rule permits.',
    fix: 'Not yet determined', fixNote: 'Needs a fix search',
    setting: 'Not yet determined', settingNote: 'Needs a sensitivity analysis',
  },
} as const

// The fix and setting columns are the one part of this page with nothing behind them yet:
// naming the smallest change that removes a mode needs a search over the design space, and
// ranking the most dangerous setting needs a sensitivity analysis. Neither exists, so they
// say so rather than showing a number nobody computed.
type Mode = keyof typeof MODES | 'pass'
const MODE_KEYS = Object.keys(MODES) as (keyof typeof MODES)[]

const EVENTS = eventRuns as {
  pu: string; tag: string; note: string
  legacy: number; product: number; legacy_min: number; product_min: number
}[]

const PASS_GREEN = '#5dbb7a'
const GOLD = '#d9b24c'
const label = 'mono text-[12px] font-medium tracking-[0.14em] uppercase'
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
const frac = (k: VarKey, v: number) => (v - VARS[k].min) / (VARS[k].max - VARS[k].min)

const SAMPLE = sampleRuns as (Scenario & { mode: Mode })[]

function summarize(pts: { mode: Mode }[]) {
  const n = pts.length, fails = pts.filter((p) => p.mode !== 'pass').length
  const p = 1 - fails / n, se = Math.sqrt((p * (1 - p)) / n)
  const modes = MODE_KEYS.map((m) => {
    const q = pts.filter((x) => x.mode === m).length / n, e = Math.sqrt((q * (1 - q)) / n)
    return { id: m, p: q, lo: Math.max(0, q - 1.96 * e), hi: q + 1.96 * e }
  }).sort((a, b) => b.p - a.p)
  return { pass: p, lo: p - 1.96 * se, hi: p + 1.96 * se, modes }
}
const OVERALL = summarize(SAMPLE)

// estimate for one set of slider values: weight nearby runs (distance measured in each variable's range)
function localEstimate(s: Scenario) {
  let w = 0, wp = 0
  const wm: Record<string, number> = {}
  for (const p of SAMPLE) {
    const d2 = KEYS.reduce((a, k) => a + (frac(k, p[k]) - frac(k, s[k])) ** 2, 0)
    const wt = Math.exp(-d2 / (2 * 0.12 ** 2))
    w += wt
    if (p.mode === 'pass') wp += wt
    else wm[p.mode] = (wm[p.mode] ?? 0) + wt
  }
  const top = Object.entries(wm).sort((a, b) => b[1] - a[1])[0]
  return {
    pass: w > 1e-6 ? wp / w : 1,
    mode: (top && top[1] / Math.max(w, 1e-9) > 0.02 ? top[0] : null) as keyof typeof MODES | null,
    // Few simulated runs land near these settings, so the estimate is thin here.
    sparse: w < 3,
  }
}

// The slider estimate. With the neural surrogate loaded (public/data/surrogate.json, trained on 20,000
// simulator runs) it holds the four sliders and averages the ensemble over 300 real sampler draws of
// everything else; until then (or if it fails to load) it falls back to the sample-run neighbourhood above.
type Estimate = {
  pass: number
  band: number | null // +/- 2 std across ensemble members; null for the sample fallback
  mode: keyof typeof MODES | null
  sparse: boolean // sample fallback: few runs nearby; surrogate: a slider is outside the training data
  source: 'surrogate' | 'sample'
  outside: string[]
}

function surrogateEstimate(model: SurrogateModel, s: Scenario): Estimate {
  const m = marginal(model, {
    dip_depth_pu: s.depth,
    dip_duration_s: s.duration / 1000, // the page works in ms
    outdoor_temp_c: s.temp,
    battery_age_yr: s.age,
  })
  const outside = m.outsideTraining.map((f) => KEYS.find((k) => VARS[k].column === f) ?? f).map((k) => (k in VARS ? VARS[k as VarKey].label.toLowerCase() : k))
  return {
    pass: m.passRate,
    band: 2 * m.passRateStd,
    mode: m.mode && m.mode in MODES && m.modeShare > 0.02 ? (m.mode as keyof typeof MODES) : null,
    sparse: outside.length > 0,
    source: 'surrogate',
    outside,
  }
}

const sampleEstimate = (s: Scenario): Estimate => ({ ...localEstimate(s), band: null, source: 'sample', outside: [] })

// which pair of factors best separates failures: bin the plane and count failures that land in fail-majority bins
function separation(x: VarKey, y: VarKey) {
  const B = 6, bins = new Map<number, { f: number; n: number }>()
  for (const p of SAMPLE) {
    const id = Math.min(B - 1, Math.floor(frac(x, p[x]) * B)) * B + Math.min(B - 1, Math.floor(frac(y, p[y]) * B))
    const b = bins.get(id) ?? { f: 0, n: 0 }
    b.n++
    if (p.mode !== 'pass') b.f++
    bins.set(id, b)
  }
  const fails = SAMPLE.filter((p) => p.mode !== 'pass').length
  let caught = 0
  for (const b of bins.values()) if (b.f / b.n >= 0.5) caught += b.f
  return fails ? caught / fails : 0
}
const PAIRS = KEYS.flatMap((x, i) => KEYS.slice(i + 1).map((y) => ({ x, y, s: separation(x, y) })))
const BEST = PAIRS.reduce((a, b) => (b.s > a.s ? b : a))

// plain-language summary written from whatever pair is plotted
function describe(x: VarKey, y: VarKey, you: Scenario) {
  const failRate = (k: VarKey, part: 0 | 2) => {
    const sel = SAMPLE.filter((p) => Math.min(2, Math.floor(frac(k, p[k]) * 3)) === part)
    return sel.length ? sel.filter((p) => p.mode !== 'pass').length / sel.length : 0
  }
  const sentence = (k: VarKey) => {
    const lo = failRate(k, 0), hi = failRate(k, 2), V = VARS[k]
    if (Math.max(lo, hi) < 0.02 || Math.max(lo, hi) / Math.max(Math.min(lo, hi), 0.005) < 1.6)
      return `${V.label} on its own makes little difference (${pct(lo, 0)} vs ${pct(hi, 0)} failing across its range).`
    const [side, other, a, b] = hi > lo ? [V.high, V.low, hi, lo] : [V.low, V.high, lo, hi]
    return `Failures cluster in ${side}: ${pct(a, 0)} fail, against ${pct(b, 0)} in ${other}.`
  }
  const fails = SAMPLE.filter((p) => p.mode !== 'pass')
  const top = MODE_KEYS.map((m) => ({ m, n: fails.filter((p) => p.mode === m).length })).sort((a, b) => b.n - a.n)[0]
  const est = localEstimate(you)
  return `${sentence(x)} ${sentence(y)} Most failures are ${MODES[top.m].name.toLowerCase()} (${pct(top.n / Math.max(fails.length, 1), 0)} of them). Your scenario sits where about ${pct(est.pass, 0)} of runs pass.`
}

// ---- one illustrative trace for the slider values. Replace with the simulator's result CSV for that run ----
function trace(s: Scenario) {
  const t0 = 1, t1 = t0 + s.duration / 1000
  const back = t1 + 0.05 * Math.log(Math.max((1 - s.depth) / 0.1, 1)) // voltage back above 0.90 pu
  const deadline = back + 2
  const minP = clamp(15 + s.depth * 33, 12, 55)
  // Recovery is slow exactly when the nearby real runs failed, so the curve and the map agree.
  const mode = localEstimate(s).mode ?? 'pass'
  const tau = 0.35 + s.age * 0.03 + (mode === 'pass' ? 0 : mode === 'storage hand-back too slow' ? 1.2 : mode === 'PSU shutdown and restart delay' ? 1.1 : 0.9)
  const volt = (t: number) => (t < t0 ? 1 : t < t1 ? s.depth : 1 - (1 - s.depth) * Math.exp(-(t - t1) / 0.05))
  const facility = (t: number) =>
    t < t0 ? 100 : t < t0 + 0.06 ? 100 - ((100 - minP) * (t - t0)) / 0.06 : minP + (98 - minP) * (1 - Math.exp(-(t - t0 - 0.06) / tau))
  const reached90 = t0 + 0.06 - tau * Math.log(1 - (90 - minP) / (98 - minP))
  const peak = 200 * (1 - 0.03 * s.age) * (s.temp < -3 ? 0.7 : 1)
  const hot = s.temp > 35
  const battery = (t: number) =>
    t < t0 ? 0 : t < t0 + 0.03 ? (peak * (t - t0)) / 0.03 : t < 1.35 ? peak : hot && t < 2.2 ? peak - 0.36 * peak * ((t - 1.35) / 0.85)
      : (hot ? 0.64 * peak : peak) * Math.exp(-(t - (hot ? 2.2 : 1.35)) / (hot ? 1.1 : tau))
  const window = clamp(Math.ceil(reached90 + 1.5), 6, 15)
  return { t0, t1, back, deadline, minP, volt, facility, battery, peak, hot, reached90, window, mode, passed: reached90 <= deadline }
}

type TraceShape = ReturnType<typeof trace>

function traceFromApi(api: NonNullable<Awaited<ReturnType<typeof simulate>>['trace']>, s: Scenario, verdict: { passed: boolean; failureMode: string }): TraceShape {
  const ts = api.t
  // Linear interpolation between samples, so the chart can ask for any instant.
  const at = (ys: number[]) => (t: number) => {
    if (t <= ts[0]) return ys[0]
    if (t >= ts[ts.length - 1]) return ys[ys.length - 1]
    let lo = 0, hi = ts.length - 1
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (ts[mid] <= t) lo = mid; else hi = mid }
    const span = ts[hi] - ts[lo] || 1
    return ys[lo] + ((ys[hi] - ys[lo]) * (t - ts[lo])) / span
  }
  const back = api.back ?? api.t1
  return {
    t0: api.t0, t1: api.t1, back, deadline: api.deadline ?? back + 2,
    minP: api.min_pct, reached90: api.reached90 ?? ts[ts.length - 1],
    volt: at(api.voltage_pu), facility: at(api.facility_pct), battery: at(api.battery_pct),
    peak: Math.max(...api.battery_pct, 1),
    hot: s.temp > 35,
    window: clamp(Math.ceil((api.reached90 ?? ts[ts.length - 1]) + 1.5), 6, 15),
    mode: (verdict.passed ? 'pass' : verdict.failureMode) as Mode,
    passed: verdict.passed,
  }
}

function Section({ n, kicker, title, lede, children }: { n: string; kicker: string; title: string; lede: string; children: ReactNode }) {
  return (
    <section className="pt-36">
      <div className="grid gap-x-6 md:grid-cols-[44px_1fr]">
        <div className="mono pt-[7px] text-[12px] text-[#d9b24c]">{n}</div>
        <div>
          <p className={`${label} text-[#d9b24c]`}>{kicker}</p>
          <h2 className="display mt-3 max-w-[800px] text-[44px] leading-[1.05] font-semibold tracking-[-0.035em] text-[#f6f1e2]">{title}</h2>
          <p className="mt-4 max-w-[600px] text-[17px] leading-[1.6] text-[#c4bca7]">{lede}</p>
        </div>
      </div>
      {children}
    </section>
  )
}

const ChartTitle = ({ children }: { children: ReactNode }) => (
  <h3 className="display text-[22px] leading-[1.25] font-semibold tracking-[-0.02em] text-[#f6f1e2]">{children}</h3>
)
const AxisLabel = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <span className={`mono text-[11px] tracking-[0.14em] text-[#a8a089] uppercase ${className}`}>{children}</span>
)

// ---- scenario panel ----
function Slider({ k, value, prev, disabled, onChange }: { k: VarKey; value: number; prev: number; disabled: boolean; onChange: (v: number) => void }) {
  const V = VARS[k]
  const edited = value !== prev
  const at = (v: number) => `calc(9px + ${clamp(frac(k, v), 0, 1)} * (100% - 18px))`
  return (
    <div className={disabled ? 'opacity-50' : ''}>
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className={`mono text-[11px] tracking-[0.14em] uppercase ${edited ? 'text-[#f0c85a]' : 'text-[#8d8670]'}`}>
            {V.label}{edited && ` · edited, was ${V.fmt(prev)}`}
          </p>
          <p className="mt-1 text-[13px] text-[#a8a089]">{V.help}</p>
        </div>
        <p className={`display shrink-0 text-[26px] font-semibold tracking-[-0.02em] ${edited ? 'text-[#f0c85a]' : 'text-[#f6f1e2]'}`}>{V.fmt(value)}</p>
      </div>
      <div className="relative mt-3 h-6">
        <div className="absolute inset-x-0 top-[10px] h-1 bg-[#2b2720]" />
        <div className="absolute top-[10px] left-0 h-1 bg-[#d9b24c]" style={{ width: at(value) }} />
        {V.marks?.map((m) => <div key={m.label} className="absolute top-1 h-4 w-px bg-[#8d8670]" style={{ left: at(m.v) }} />)}
        {V.bands?.map((b) => (
          <div key={b.label} className="absolute top-[19px] h-1 bg-[#8d8670]" style={{ left: at(b.from), width: `calc(${frac(k, b.to) - frac(k, b.from)} * (100% - 18px))` }} />
        ))}
        {edited && <div className="absolute top-[5px] h-3.5 w-3.5 -translate-x-1/2 rounded-full border-[1.5px] border-dashed border-[#8d8670]" style={{ left: at(prev) }} />}
        <input
          type="range" min={V.min} max={V.max} step={V.step} value={value} disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={V.label} className={`gr-range absolute inset-0 w-full ${edited ? 'edited' : ''}`}
        />
      </div>
      <div className="mono mt-2 flex justify-between gap-3 text-[11px] text-[#8d8670]">
        <span>{V.fmt(V.min)}</span>
        <span className="truncate">
          {V.bands ? 'shaded: real clearing times' : V.marks ? (V.marks.length > 1 ? `ticks: Texas events ${V.marks.map((m) => m.label.replace('TX ', '')).join(' · ')}` : `tick: ${V.marks[0].label}`) : ''}
        </span>
        <span>{V.fmt(V.max)}</span>
      </div>
    </div>
  )
}

const STAGES = [
  { name: 'Sample realistic scenarios', end: 0.08 },
  { name: 'Screen them with the fast model', end: 0.78 },
  { name: 'Re-check failures in the simulator', end: 0.94 },
  { name: 'Group failures and find fixes', end: 1 },
]
const RUN_MS = 3200

function ScenarioPanel({ values, lastRun, onChange, onRun, onReset, estimate }: {
  values: Scenario; lastRun: Scenario; onChange: (k: VarKey, v: number) => void; onRun: () => void; onReset: () => void
  estimate: (s: Scenario) => Estimate
}) {
  const [progress, setProgress] = useState<number | null>(null)
  const timer = useRef<number | null>(null)
  const changed = KEYS.filter((k) => values[k] !== lastRun[k])
  // Memoised on the slider values: the progress bar re-renders every frame and a surrogate estimate is ~30 ms.
  const est = useMemo(() => estimate(lastRun), [estimate, lastRun])

  const stop = () => { if (timer.current) cancelAnimationFrame(timer.current); timer.current = null; setProgress(null) }
  const start = () => {
    const t0 = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / RUN_MS)
      setProgress(p)
      if (p < 1) timer.current = requestAnimationFrame(tick)
      else { timer.current = null; setProgress(null); onRun() }
    }
    timer.current = requestAnimationFrame(tick)
  }
  useEffect(() => () => { if (timer.current) cancelAnimationFrame(timer.current) }, [])

  const running = progress !== null
  const live = useMemo(() => estimate(values), [estimate, values])
  const sourceNote = est.source === 'surrogate'
    ? `Neural surrogate estimate${est.band !== null ? ` (± ${(est.band * 100).toFixed(1)} points across the ensemble)` : ''}; the stress test runs the real simulator.`
    : 'Estimated from nearby sample runs while the surrogate loads.'
  return (
    <section className="border-b border-[#2b2720] pb-10">
      <style>{`
        .gr-range { -webkit-appearance: none; appearance: none; background: transparent; cursor: pointer; margin: 0; }
        .gr-range:disabled { cursor: default; }
        .gr-range::-webkit-slider-runnable-track { height: 24px; background: transparent; }
        .gr-range::-moz-range-track { height: 24px; background: transparent; }
        .gr-range::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; margin-top: 3px; border-radius: 50%; background: #f6f1e2; border: 3px solid #07070a; }
        .gr-range::-moz-range-thumb { width: 12px; height: 12px; border-radius: 50%; background: #f6f1e2; border: 3px solid #07070a; }
        .gr-range.edited::-webkit-slider-thumb { background: #f0c85a; }
        .gr-range.edited::-moz-range-thumb { background: #f0c85a; }
        .gr-range:focus-visible { outline: none; }
        .gr-range:focus-visible::-webkit-slider-thumb { box-shadow: 0 0 0 2px #d9b24c; }
      `}</style>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className={`${label} text-[#d9b24c]`}>Data center scenario</p>
          <h2 className="display mt-2.5 text-[28px] leading-[1.15] font-semibold tracking-[-0.025em] text-[#f6f1e2]">Set the dip and the site conditions to test.</h2>
        </div>
        <button onClick={onReset} disabled={running} className="mono cursor-pointer text-[11.5px] text-[#8d8670] transition hover:text-white disabled:cursor-default">
          Preset · Abilene reference campus ↺
        </button>
      </div>

      <div className="mt-10 grid gap-x-10 gap-y-10 md:grid-cols-2">
        {KEYS.map((k) => <Slider key={k} k={k} value={values[k]} prev={lastRun[k]} disabled={running} onChange={(v) => onChange(k, v)} />)}
      </div>

      {!running ? (
        <div className="mt-10 flex flex-wrap items-center gap-x-7 gap-y-4">
          <button onClick={start} className="mono flex shrink-0 cursor-pointer items-center gap-2.5 bg-[#d9b24c] px-6 py-3.5 text-[13px] font-semibold tracking-[0.12em] text-[#07070a] uppercase transition hover:bg-[#f0c85a]">
            Run stress test <span>→</span>
          </button>
          <div className="min-w-0 flex-1">
            {changed.length ? (
              <p className="mono text-[12px] text-[#f0c85a]">
                {changed.length} setting{changed.length > 1 ? 's' : ''} changed since the last run. Results below are out of date.
              </p>
            ) : (
              <p className="mono text-[12px] text-[#c4bca7]">
                Under these conditions about <span className="text-[#f6f1e2]">{pct(est.pass, 0)}</span> of runs pass
                {est.mode ? `; the most likely failure is ${MODES[est.mode].name.toLowerCase()}.` : '.'}
                {est.sparse && (est.source === 'surrogate'
                  ? ` ${est.outside.join(' and ')} ${est.outside.length > 1 ? 'are' : 'is'} outside the training data, so treat it as rough.`
                  : ' Few runs look like this, so treat it as rough.')}
              </p>
            )}
            <p className="mono mt-1 text-[11.5px] text-[#8d8670]">Each run holds these four fixed and tests 1,000,000 variations of everything else. {sourceNote}</p>
          </div>
        </div>
      ) : (
        <div className="mt-10">
          <div className="flex flex-wrap items-center gap-x-7 gap-y-3">
            <span className="mono border border-[#4a4332] px-6 py-3 text-[13px] font-semibold tracking-[0.12em] text-[#a8a089] uppercase">Running…</span>
            <span className="mono flex-1 text-[12px] text-[#f0c85a]">
              {changed.length ? `Testing your change: ${changed.map((k) => `${VARS[k].label.toLowerCase()} ${VARS[k].fmt(lastRun[k])} → ${VARS[k].fmt(values[k])}`).join(', ')}` : 'Re-running the current settings'}
            </span>
            <button onClick={stop} className="mono cursor-pointer text-[12px] tracking-[0.12em] text-[#bdb5a0] uppercase transition hover:text-white">Cancel</button>
          </div>
          <div className="mono mt-5 flex justify-between text-[12px]">
            <span className="text-[#f6f1e2]">{Math.round(progress * 1_000_000).toLocaleString()} of 1,000,000 variations</span>
            <span className="text-[#8d8670]">about {Math.ceil(((1 - progress) * RUN_MS) / 1000)} s left</span>
          </div>
          <div className="mt-2.5 h-1.5 bg-[#1a1813]"><div className="h-full bg-[#d9b24c]" style={{ width: `${progress * 100}%` }} /></div>
          <div className="mt-8 grid gap-10 md:grid-cols-[400px_1fr]">
            <div>
              <p className="mono text-[11px] tracking-[0.14em] text-[#8d8670] uppercase">Pipeline</p>
              {STAGES.map((s, i) => {
                const startAt = i ? STAGES[i - 1].end : 0
                const state = progress >= s.end ? 'done' : progress >= startAt ? 'active' : 'waiting'
                return (
                  <div key={s.name} className="mt-3.5 flex items-center gap-3.5">
                    <span className="flex w-4 shrink-0 justify-center">
                      {state === 'done' ? <svg width="16" height="16" viewBox="0 0 16 16"><path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke={PASS_GREEN} strokeWidth="1.8" /></svg>
                        : <span className={`h-2 w-2 rounded-full ${state === 'active' ? 'bg-[#d9b24c]' : 'border border-[#6f6958]'}`} />}
                    </span>
                    <span className={`w-[260px] text-[15px] ${state === 'waiting' ? 'text-[#8d8670]' : state === 'active' ? 'text-[#f6f1e2]' : 'text-[#c4bca7]'}`}>{s.name}</span>
                    <span className={`mono text-[11.5px] ${state === 'active' ? 'text-[#d9b24c]' : 'text-[#6f6958]'}`}>
                      {state === 'active' ? `${Math.round(((progress - startAt) / (s.end - startAt)) * 100)}%` : state === 'done' ? 'done' : 'waiting'}
                    </span>
                  </div>
                )
              })}
            </div>
            <div>
              <p className="mono text-[11px] tracking-[0.14em] text-[#8d8670] uppercase">So far · updates as it runs</p>
              <div className="mt-3 flex flex-wrap items-baseline gap-5">
                <p className="display text-[56px] leading-none font-semibold tracking-[-0.04em] text-[#f6f1e2]">
                  {(live.pass * 100).toFixed(1)}<span className="ml-1 text-[22px] font-medium tracking-normal text-[#a8a089]">%</span>
                </p>
                <div className="mono text-[11.5px]">
                  <p className="text-[#c4bca7]">pass rate under these conditions</p>
                  <p className={live.pass < est.pass ? 'text-[#ff8a63]' : 'text-[#5dbb7a]'}>
                    {live.pass < est.pass ? '↓' : '↑'} {Math.abs((live.pass - est.pass) * 100).toFixed(1)} points from the last run ({pct(est.pass)})
                  </p>
                </div>
              </div>
              <p className="mt-4 text-[15px] leading-[1.55] text-[#d3ccb8]">
                {live.mode ? `The most likely failure here is ${MODES[live.mode].name.toLowerCase()}.` : 'No failure mode stands out under these conditions.'}
              </p>
              <p className="mono mt-2 text-[11.5px] text-[#8d8670]">
                {live.source === 'surrogate' ? 'Neural surrogate estimate.' : 'Sample-run estimate.'}
                {live.sparse && live.source === 'surrogate' ? ` Outside the training data: ${live.outside.join(', ')}.` : ''}
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

// ---- 01 failure map ----
function Picker({ axis, value, other, set }: { axis: string; value: VarKey; other: VarKey; set: (k: VarKey) => void }) {
  return (
    <label className="block w-[260px]">
      <span className="mono text-[11px] tracking-[0.14em] text-[#8d8670] uppercase">{axis}</span>
      <span className="relative mt-2 block">
        <select value={value} onChange={(e) => set(e.target.value as VarKey)}
          className="w-full cursor-pointer appearance-none border-b border-[#4a4332] bg-transparent pt-1 pr-6 pb-2.5 text-[15px] text-[#f6f1e2] outline-none focus-visible:border-[#d9b24c]">
          {KEYS.filter((k) => k !== other).map((k) => <option key={k} value={k} className="bg-[#07070a]">{VARS[k].label}</option>)}
        </select>
        <svg width="16" height="16" viewBox="0 0 16 16" className="pointer-events-none absolute top-1.5 right-0"><path d="M4 6l4 4 4-4" fill="none" stroke="#a8a089" strokeWidth="1.5" /></svg>
      </span>
    </label>
  )
}

function FailureMap({ you }: { you: Scenario }) {
  const [x, setX] = useState<VarKey>(BEST.x)
  const [y, setY] = useState<VarKey>(BEST.y)
  const W = 1100, H = 480, L = 64, R = 24, T = 16, B = 56
  const px = (v: number) => L + clamp(frac(x, v), 0, 1) * (W - L - R)
  const py = (v: number) => T + (1 - clamp(frac(y, v), 0, 1)) * (H - T - B)
  const sep = PAIRS.find((p) => (p.x === x && p.y === y) || (p.x === y && p.y === x))!.s
  const isBest = (x === BEST.x && y === BEST.y) || (x === BEST.y && y === BEST.x)
  const summary = useMemo(() => describe(x, y, you), [x, y, you])
  const axisBands = (k: VarKey, dir: 'x' | 'y') => VARS[k].bands?.map((b) => {
    const a = dir === 'x' ? px(b.from) : py(b.to), z = dir === 'x' ? px(b.to) : py(b.from)
    return dir === 'x'
      ? <rect key={`${dir}${b.label}`} x={a} y={T} width={z - a} height={H - T - B} fill="#f6f1e2" fillOpacity={0.04} />
      : <rect key={`${dir}${b.label}`} x={L} y={a} width={W - L - R} height={z - a} fill="#f6f1e2" fillOpacity={0.04} />
  })
  const axisMarks = (k: VarKey, dir: 'x' | 'y') => VARS[k].marks?.map((m) => dir === 'x'
    ? <line key={`${dir}${m.label}`} x1={px(m.v)} y1={T} x2={px(m.v)} y2={H - B} stroke="#f6f1e2" strokeOpacity={0.3} strokeDasharray="3 4" />
    : <line key={`${dir}${m.label}`} x1={L} y1={py(m.v)} x2={W - R} y2={py(m.v)} stroke="#f6f1e2" strokeOpacity={0.3} strokeDasharray="3 4" />)
  const yx = px(you[x]), yy = py(you[y])

  return (
    <div className="mt-10">
      <div className="flex flex-wrap items-end gap-x-7 gap-y-4">
        <Picker axis="X axis" value={x} other={y} set={setX} />
        <Picker axis="Y axis" value={y} other={x} set={setY} />
        <p className="mono flex items-center gap-2 pb-2.5 text-[11.5px] text-[#d9b24c]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#d9b24c]" />
          {isBest ? `Most informative pair · separates ${pct(sep, 0)} of failures` : (
            <>This pair separates {pct(sep, 0)} of failures ·{' '}
              <button onClick={() => { setX(BEST.x); setY(BEST.y) }} className="cursor-pointer underline underline-offset-4 hover:text-white">show the best pair</button>
            </>
          )}
        </p>
      </div>

      <div className="mt-11 grid gap-x-16 gap-y-6 md:grid-cols-[340px_1fr]">
        <ChartTitle>Pass or fail by {VARS[x].label.toLowerCase()} and {VARS[y].label.toLowerCase()}</ChartTitle>
        <div>
          <p className="mono text-[11px] tracking-[0.14em] text-[#d9b24c] uppercase">What this shows</p>
          <p className="mt-2 max-w-[640px] text-[16px] leading-[1.6] text-[#d3ccb8]">{summary}</p>
          <p className="mono mt-2 text-[11px] text-[#8d8670]">Written from the plotted runs; it changes with the axes and your scenario.</p>
        </div>
      </div>

      <div className="mt-9 flex flex-wrap gap-x-8 gap-y-2">
        {[{ name: 'Pass', c: PASS_GREEN }, ...MODE_KEYS.map((m) => ({ name: MODES[m].name, c: MODES[m].color })), { name: 'Your scenario', c: '' }].map((k) => (
          <span key={k.name} className="mono flex items-center gap-2 text-[11.5px] tracking-[0.1em] text-[#c4bca7] uppercase">
            {k.c ? <span className="h-2 w-2 rounded-full" style={{ background: k.c }} /> : <span className="h-3 w-3 rounded-full border-[1.5px] border-[#f6f1e2]" />}{k.name}
          </span>
        ))}
      </div>

      <div className="mt-7 flex justify-between gap-4">
        <AxisLabel>↑ {VARS[y].label}, {VARS[y].unit}</AxisLabel>
        <AxisLabel className="hidden sm:inline">{SAMPLE.length.toLocaleString()} runs shown</AxisLabel>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label={`Scatter of ${VARS[y].label} against ${VARS[x].label}. Green dots pass; colored dots fail by mode.`}>
        {axisBands(x, 'x')}{axisBands(y, 'y')}
        {VARS[y].ticks.map((v) => <text key={`y${v}`} x={L - 12} y={py(v) + 4} textAnchor="end" className="mono" fontSize={11} fill="#8d8670">{VARS[y].fmt(v).replace(` ${VARS[y].unit}`, '')}</text>)}
        {VARS[x].ticks.map((v) => <text key={`x${v}`} x={px(v)} y={H - B + 22} textAnchor="middle" className="mono" fontSize={11} fill="#8d8670">{VARS[x].fmt(v).replace(` ${VARS[x].unit}`, '')}</text>)}
        <text x={W - R} y={H - 8} textAnchor="end" className="mono" fontSize={11} letterSpacing="1.4" fill="#a8a089">{VARS[x].label.toUpperCase()}, {VARS[x].unit} →</text>
        <line x1={L} y1={H - B} x2={W - R} y2={H - B} stroke="#5a5444" />
        <line x1={L} y1={T} x2={L} y2={H - B} stroke="#5a5444" />
        {axisMarks(x, 'x')}{axisMarks(y, 'y')}
        {SAMPLE.filter((p) => p.mode === 'pass').map((p, i) => <circle key={`p${i}`} cx={px(p[x])} cy={py(p[y])} r={2.6} fill={PASS_GREEN} fillOpacity={0.75} />)}
        {SAMPLE.filter((p) => p.mode !== 'pass').map((p, i) => (
          <circle key={`f${i}`} cx={px(p[x])} cy={py(p[y])} r={4.2} fill={MODES[p.mode as keyof typeof MODES].color} stroke="#07070a" />
        ))}
        <circle cx={yx} cy={yy} r={10} fill="none" stroke="#f6f1e2" strokeWidth={1.8} />
        <line x1={yx - 16} y1={yy} x2={yx - 11} y2={yy} stroke="#f6f1e2" strokeWidth={1.5} />
        <line x1={yx + 11} y1={yy} x2={yx + 16} y2={yy} stroke="#f6f1e2" strokeWidth={1.5} />
        <rect x={yx > W - 200 ? yx - 132 : yx + 18} y={yy - 10} width={112} height={18} fill="#07070a" />
        <text x={yx > W - 200 ? yx - 128 : yx + 22} y={yy + 3} className="mono" fontSize={11} fill="#f6f1e2">YOUR SCENARIO</text>
      </svg>
      <p className="mono mt-3 text-[11px] tracking-[0.06em] text-[#8d8670]">
        Shaded strips mark where real values cluster. Dashed lines mark the Texas events and the 35 °C derate point when those axes are shown. Illustrative values.
      </p>
    </div>
  )
}

// ---- 02 replay ----
function Replay({ s, tr }: { s: Scenario; tr: TraceShape }) {
  const W = 1100, L = 64, R = 24, PH = 112, STEP = 168, TOP = 56
  const X = (t: number) => L + (t / tr.window) * (W - L - R)
  const bottom = TOP + 2 * STEP + PH
  const ts = Array.from({ length: 721 }, (_, i) => (i / 720) * tr.window)
  const bMax = Math.max(50, Math.ceil(tr.peak / 50) * 50 + 25) // the run's peak, rounded up
  const bStep = bMax > 150 ? 100 : 50
  const panels = [
    { name: 'VOLTAGE AT INTERCONNECTION, pu', lo: Math.min(0.45, Math.floor(s.depth * 10) / 10 - 0.05), hi: 1.08, ticks: [0.25, 0.5, 0.75, 1], f: tr.volt, c: '#f6f1e2', fmt: (v: number) => v.toFixed(2) },
    { name: 'FACILITY POWER FROM GRID, % OF PRE-FAULT', lo: 0, hi: 108, ticks: [0, 50, 100], f: tr.facility, c: GOLD, fmt: (v: number) => `${v}` },
    { name: 'BATTERY OUTPUT, MW', lo: 0, hi: bMax, ticks: Array.from({ length: Math.floor(bMax / bStep) + 1 }, (_, i) => i * bStep), f: tr.battery, c: '#78d7ff', fmt: (v: number) => `${v}` },
  ]
  const atDeadline = tr.facility(tr.deadline)
  const scenarioRow: [string, string][] = [
    ['Dip', `${VARS.depth.fmt(s.depth)} for ${VARS.duration.fmt(s.duration)}`], ['Outdoor', VARS.temp.fmt(s.temp)], ['Battery age', VARS.age.fmt(s.age)],
    ['Verdict', tr.passed ? 'Pass' : tr.mode === 'pass' ? 'Fail' : `Fail · ${MODES[tr.mode as keyof typeof MODES]?.name.toLowerCase() ?? tr.mode}`],
  ]
  return (
    <div className="mt-10">
      <div className="flex flex-wrap gap-x-10 gap-y-4 md:pl-[68px]">
        {scenarioRow.map(([k, v]) => (
          <div key={k}>
            <p className="mono text-[11px] tracking-[0.14em] text-[#8d8670] uppercase">{k}</p>
            <p className="mono mt-1 text-[13px]" style={{ color: k === 'Verdict' ? (tr.passed ? PASS_GREEN : '#ff8a63') : '#f6f1e2' }}>{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-10"><ChartTitle>How the site responds to the dip, over {tr.window} seconds</ChartTitle></div>
      <svg viewBox={`0 0 ${W} ${bottom + 30}`} className="mt-5 w-full" role="img" aria-label="Voltage, facility power and battery output over time, with the 90% line and the 2 second recovery deadline.">
        <rect x={X(tr.t0)} y={18} width={Math.max(2, X(tr.t1) - X(tr.t0))} height={bottom - 18} fill="#ff4a3a" fillOpacity={0.12} />
        <text x={X(tr.t0) - 6} y={12} textAnchor="end" className="mono" fontSize={10.5} fill="#ff8a63">FAULT {tr.t0.toFixed(2)}–{tr.t1.toFixed(2)} s</text>
        <line x1={X(tr.deadline)} y1={18} x2={X(tr.deadline)} y2={bottom} stroke="#ff6a55" strokeDasharray="3 4" />
        <text x={X(tr.deadline) + 8} y={12} className="mono" fontSize={10.5} fill="#ff6a55">2 s RECOVERY DEADLINE · {tr.deadline.toFixed(2)} s</text>
        {panels.map((p, k) => {
          const y0 = TOP + k * STEP
          const Y = (v: number) => y0 + ((p.hi - clamp(v, p.lo, p.hi)) / (p.hi - p.lo)) * PH
          return (
            <g key={p.name}>
              <text x={L} y={y0 - 16} className="mono" fontSize={11} letterSpacing="1.5" fill="#a8a089">{p.name}</text>
              {p.ticks.filter((v) => v >= p.lo).map((v) => <text key={v} x={L - 12} y={Y(v) + 4} textAnchor="end" className="mono" fontSize={11} fill="#8d8670">{p.fmt(v)}</text>)}
              <line x1={L} y1={y0 + PH} x2={W - R} y2={y0 + PH} stroke="#5a5444" />
              {k === 1 && (
                <>
                  <line x1={L} y1={Y(90)} x2={W - R} y2={Y(90)} stroke="#f6f1e2" strokeDasharray="3 4" />
                  <text x={W - R} y={Y(90) + 18} textAnchor="end" className="mono" fontSize={11} fill="#f6f1e2">ERCOT: 90%</text>
                </>
              )}
              <polyline points={ts.map((t) => `${X(t).toFixed(1)},${Y(p.f(t)).toFixed(1)}`).join(' ')} fill="none" stroke={p.c} strokeWidth={2.2} strokeLinejoin="round" />
              {k === 0 && <text x={X(tr.t1) + 8} y={Y(s.depth) + 4} className="mono" fontSize={11} fill="#c4bca7">{s.depth.toFixed(2)} pu</text>}
              {k === 1 && (
                <>
                  <text x={X(tr.t1) + 8} y={Y(tr.minP) + 14} className="mono" fontSize={11} fill="#c4bca7">falls to {Math.round(tr.minP)}%</text>
                  <circle cx={X(tr.deadline)} cy={Y(atDeadline)} r={5} fill={tr.passed ? PASS_GREEN : '#ff4a3a'} stroke="#07070a" strokeWidth={2} />
                  <text x={X(tr.deadline) + 10} y={Y(atDeadline) + 22} className="mono" fontSize={11.5} fill={tr.passed ? PASS_GREEN : '#ff8a63'}>
                    {Math.round(atDeadline)}% at the deadline · {tr.passed ? 'PASS' : 'FAIL'}
                  </text>
                  {tr.reached90 < tr.window && (
                    <>
                      <circle cx={X(tr.reached90)} cy={Y(90)} r={4} fill={GOLD} stroke="#07070a" strokeWidth={2} />
                      <text x={X(tr.reached90) + 8} y={Y(90) - 10} className="mono" fontSize={11.5} fill="#c4bca7">
                        90% at {tr.reached90.toFixed(2)} s, {Math.abs(tr.reached90 - tr.deadline).toFixed(2)} s {tr.passed ? 'early' : 'late'}
                      </text>
                    </>
                  )}
                </>
              )}
              {k === 2 && (
                <text x={X(1.35) + 10} y={Y(tr.peak) - 6} className="mono" fontSize={11} fill="#c4bca7">
                  {Math.round(tr.peak)} MW{tr.hot ? `, then thermal derate at ${Math.round(s.temp)} °C` : ''}
                </text>
              )}
            </g>
          )
        })}
        {Array.from({ length: tr.window + 1 }, (_, t) => t).filter((t) => tr.window <= 8 || t % 2 === 0).map((t) => (
          <text key={t} x={X(t)} y={bottom + 20} textAnchor={t === 0 ? 'start' : t === tr.window ? 'end' : 'middle'} className="mono" fontSize={11} fill="#8d8670">{t} s</text>
        ))}
      </svg>
      <div className="mt-1 flex justify-end"><AxisLabel>Time since the run started, seconds →</AxisLabel></div>
    </div>
  )
}

// ---- 03 report card ----
function ReportCard() {
  const cols = 'md:grid-cols-[300px_140px_1fr_210px]'
  return (
    <div className="mt-12 md:pl-[68px]">
      <div className={`mono hidden gap-8 border-b border-[#4a4332] pb-3.5 text-[11px] tracking-[0.14em] text-[#8d8670] uppercase md:grid ${cols}`}>
        <span>Failure mode</span><span>Likelihood</span><span>Smallest fix</span><span>Most dangerous setting</span>
      </div>
      {OVERALL.modes.map(({ id, p, lo, hi }) => {
        const m = MODES[id]
        return (
          <div key={id} className={`grid gap-x-8 gap-y-4 border-b border-[#2b2720] py-7 ${cols}`}>
            <div>
              <h3 className="display flex items-center gap-2.5 text-[22px] leading-[1.2] font-semibold tracking-[-0.02em] text-[#f6f1e2]">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: m.color }} />{m.name}
              </h3>
              <p className="mt-2 pl-5 text-[15px] leading-[1.55] text-[#c4bca7]">{m.what}</p>
            </div>
            <div>
              <p className="display text-[36px] leading-none font-semibold tracking-[-0.035em] text-[#f6f1e2]">{pct(p)}</p>
              <p className="mono mt-1.5 text-[11.5px] text-[#a8a089]">band {pct(lo)} to {pct(hi)}</p>
            </div>
            <div>
              <p className="text-[16px] leading-[1.5] text-[#f6f1e2]">{m.fix}</p>
              <p className="mono mt-1.5 text-[11.5px] text-[#d9b24c]">{m.fixNote}</p>
            </div>
            <div>
              <p className="mono text-[13px] text-[#ff8a63]">{m.setting}</p>
              <p className="mt-1.5 text-[14px] leading-[1.5] text-[#a8a089]">{m.settingNote}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---- 04 legacy vs product ----
function Comparison() {
  const X0 = 330, X1 = 1000, G = 128, TOP = 40
  const X = (v: number) => X0 + (v / 100) * (X1 - X0)
  return (
    <div className="mt-14">
      <ChartTitle>Power back 2 seconds after each Texas event, legacy vs product</ChartTitle>
      <svg viewBox={`0 0 1100 ${TOP + 3 * G - 4}`} className="mt-4 w-full" role="img" aria-label="Power back at 2 seconds for legacy equipment and the product on three Texas events.">
        {EVENTS.map((e, i) => {
          const t = TOP + i * G
          return (
            <g key={e.pu}>
              <text x={0} y={t + 30} className="disp" fontSize={34} fontWeight={600} letterSpacing="-1.2" fill="#f6f1e2">{e.pu}</text>
              <text x={103} y={t + 30} className="disp" fontSize={16} fontWeight={500} fill="#a8a089">pu</text>
              <text x={0} y={t + 54} className="mono" fontSize={11} letterSpacing="1" fill="#a8a089">{e.tag.toUpperCase()}</text>
              <text x={0} y={t + 74} className="mono" fontSize={11.5} fill={e.legacy < 90 ? '#ff8a63' : '#c4bca7'}>{e.note}</text>
              {([['LEGACY', e.legacy], ['PRODUCT', e.product]] as const).map(([name, v], j) => {
                const y = t + 8 + j * 36, ok = v >= 90
                return (
                  <g key={name}>
                    <text x={X0 - 14} y={y + 12} textAnchor="end" className="mono" fontSize={11} letterSpacing="1.2" fill={j ? '#f6f1e2' : '#a8a089'}>{name}</text>
                    <rect x={X0} y={y} width={X1 - X0} height={16} fill="#1a1813" />
                    <rect x={X0} y={y} width={X(v) - X0} height={16} fill={ok ? GOLD : '#ff6a3d'} />
                    <text x={X1 + 14} y={y + 12} className="mono" fontSize={12} fill="#f6f1e2">{v}%</text>
                    <text x={1100} y={y + 12} textAnchor="end" className="mono" fontSize={11} fontWeight={600} letterSpacing="1.4" fill={ok ? GOLD : '#ff6a55'}>{ok ? 'PASS' : 'FAIL'}</text>
                  </g>
                )
              })}
              {i < 2 && <line x1={0} y1={t + G - 22} x2={1100} y2={t + G - 22} stroke="#2b2720" />}
            </g>
          )
        })}
        <line x1={X(90)} y1={28} x2={X(90)} y2={TOP + 3 * G - 52} stroke="#f6f1e2" strokeWidth={1.4} strokeDasharray="3 4" />
        <text x={X(90) - 6} y={16} textAnchor="end" className="mono" fontSize={11} fill="#f6f1e2">ERCOT: 90%</text>
        {[0, 25, 50, 75, 100].map((v) => <text key={v} x={X(v)} y={TOP + 3 * G - 28} textAnchor="middle" className="mono" fontSize={11} fill="#8d8670">{v}%</text>)}
      </svg>
      <div className="mt-2 flex justify-between gap-4">
        <AxisLabel>↑ Event, by lowest voltage (pu)</AxisLabel>
        <AxisLabel>Power back at 2 s, % of pre-fault power →</AxisLabel>
      </div>
      <p className="mono mt-4 text-[11px] tracking-[0.06em] text-[#8d8670]">Illustrative values. Event voltages are residual voltage at the point of interconnection.</p>
    </div>
  )
}

export default function Results() {
  const [values, setValues] = useState<Scenario>(PRESET)
  const [lastRun, setLastRun] = useState<Scenario>(PRESET)
  // Set once the simulator has answered for lastRun. Until then the page draws the
  // illustrative curve and says so, rather than presenting a sketch as a result.
  const [simulated, setSimulated] = useState<TraceShape | null>(null)
  const illustrative = useMemo(() => trace(lastRun), [lastRun])
  const tr = simulated ?? illustrative
  const late = tr.reached90 - tr.deadline

  // The neural surrogate for the slider estimate; the sample-run estimate stands in until it loads.
  const [surrogate, setSurrogate] = useState<SurrogateModel | null>(null)
  useEffect(() => {
    loadSurrogate()
      .then(setSurrogate)
      .catch((err) => console.warn('surrogate failed to load, using the sample-run estimate:', err))
  }, [])
  const estimate = useCallback(
    (s: Scenario): Estimate => (surrogate ? surrogateEstimate(surrogate, s) : sampleEstimate(s)),
    [surrogate]
  )

  const run = async (next: Scenario) => {
    setLastRun(next)
    setSimulated(null)
    try {
      const r = await simulate(
        {
          dip_depth_pu: next.depth,
          dip_duration_s: next.duration / 1000,  // the page works in ms
          outdoor_temp_c: next.temp,
          battery_age_yr: next.age,
        },
        { includeTrace: true }
      )
      if (r.trace) setSimulated(traceFromApi(r.trace, next, r))
    } catch (err) {
      // Simulator unreachable, or the response could not be read: the illustrative curve
      // stays. Logged rather than swallowed -- a silent catch here hides real failures.
      console.warn('simulator run failed, keeping the illustrative curve:', err)
    }
  }

  return (
    <div className="mx-auto max-w-[1180px] px-10 pt-16 pb-40">
      <style>{`.disp { font-family: "Space Grotesk", sans-serif; }`}</style>
      <ScenarioPanel
        values={values} lastRun={lastRun}
        onChange={(k, v) => setValues((s) => ({ ...s, [k]: v }))}
        onRun={() => { void run(values) }}
        onReset={() => { setValues(PRESET); setLastRun(PRESET); setSimulated(null) }}
        estimate={estimate}
      />

      <div className="flex flex-col gap-10 pt-24 md:flex-row md:items-end md:justify-between">
        <div className="max-w-[720px]">
          <p className={`${label} text-[#d9b24c]`}>Results · Reference campus · {SAMPLE.length.toLocaleString()} sampled runs</p>
          <h1 className="display mt-4 text-[56px] leading-[1.02] font-semibold tracking-[-0.04em] text-[#f6f1e2]">
            This design holds in most dips. It fails three distinct ways.
          </h1>
          <p className="mt-7 max-w-[620px] text-[19px] leading-[1.55] text-[#d3ccb8]">
            Where it breaks, how a failure plays out second by second, the smallest fix for each, and how it compares with legacy equipment on three real Texas events.
          </p>
        </div>
        <div className="shrink-0 md:text-right">
          <p className="mono text-[11px] tracking-[0.14em] text-[#a8a089] uppercase">Pass probability · all conditions</p>
          <p className="display text-[96px] leading-[0.95] font-semibold tracking-[-0.045em] text-[#f6f1e2]">
            {(OVERALL.pass * 100).toFixed(1)}<span className="ml-1 text-[34px] font-medium tracking-normal text-[#a8a089]">%</span>
          </p>
          <p className="mono mt-2 text-[11.5px] text-[#c4bca7]">95% band  {pct(OVERALL.lo)} to {pct(OVERALL.hi)}</p>
          <p className="mono mt-1 text-[11.5px] text-[#ff8a63]">{pct(1 - OVERALL.pass)} fail</p>
        </div>
      </div>

      <Section n="01" kicker="Failure map" title="Pick two factors to see where the design breaks."
        lede="Each dot is one run. Green passed the ERCOT rule; the other colors mark how it failed. The map opens on the pair that separates the most failures, and the ring marks your scenario.">
        <FailureMap you={lastRun} />
      </Section>

      <Section n="02" kicker="Your scenario, second by second"
        title={tr.passed
          ? `A ${VARS.depth.fmt(lastRun.depth)} dip at ${VARS.temp.fmt(lastRun.temp)}. Power is back ${Math.abs(late).toFixed(2)} s before the deadline.`
          : `A ${VARS.depth.fmt(lastRun.depth)} dip at ${VARS.temp.fmt(lastRun.temp)}. Power comes back ${late.toFixed(2)} s too late.`}
        lede="One illustrative run with the slider settings: the voltage dip, how much power the site draws from the grid, and what the battery does. It updates each time you run the stress test.">
        <Replay s={lastRun} tr={tr} />
      </Section>

      <Section n="03" kicker="Report card" title="Five ways this design fails."
        lede="Ranked by how often each one happens across the simulated runs, with a 95% band. Naming the smallest fix needs a search over the design space, which is not built yet.">
        <ReportCard />
      </Section>

      <Section n="04" kicker="Legacy vs product · Texas events" title="Legacy equipment fails all three real dips. The product passes all three."
        lede="Three recorded ERCOT voltage events replayed against the same reference campus, once with legacy double-conversion UPS and once with the product.">
        <Comparison />
      </Section>
    </div>
  )
}
