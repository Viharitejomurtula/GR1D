/**
 * Results: pick a voltage dip, watch it hit the grid from the Problem tab, and see whether the site's grid connection
 * rides through.
 *
 * Nothing here is predicted. Every depth the slider reaches (0.00-1.00 pu, steps of 0.01) is a real simulator run of the
 * grid-friendly design, graded against the ride-through rule and exported with its traces by
 * `python scripts/export_depth_sweep.py` to /data/depth_sweep.json. The map replays that run: the grid power, current
 * and battery output on screen are the simulated values at that instant.
 */
import { useEffect, useMemo, useState } from 'react'
import GridDemo from './GridDemo'

type Run = {
  depth: number; in_scope: boolean; ok: boolean; error?: string
  numerics_ok?: boolean; numerics_note?: string; passed?: boolean; failure_mode?: string
  peak_current_pu?: number; min_power?: number; recovery_margin_s?: number; floor_violation_s?: number; trips?: string[]
  t?: number[]; v?: number[]; i?: number[]; p?: number[]; bbu?: number[]; srv?: number[]; psu?: number[]
}
type Sweep = {
  design: string; simulator_commit: string; dip: { start_s: number; duration_s: number }
  valid_dip_depth_pu: [number, number]; current_cap_pu: number; runs: Run[]
}

// Playback: the dip lasts ~80 ms, so the first SLOW_A seconds after it arrives play the simulation at SLOW x real time;
// the rest of the 15 s window then plays at FAST x.
const SLOW = 0.15, SLOW_A = 4, FAST = 1.5
const PRE_A = -1.2 // chart starts this many animation seconds before the dip arrives
const label = 'mono text-[11.5px] font-medium tracking-[0.14em] uppercase'
const clamp01 = (x: number) => Math.max(0, Math.min(1, x))

const MODE_TEXT: Record<string, string> = {
  passed: 'Stays connected, keeps current under the cap and has power back within 2.0 s.',
  'exceeded 125% current cap': 'Pulls more current than the rule allows while the voltage is low. Constant-power loads draw more amps as voltage falls.',
  'exceeded current cap': 'Pulls more current than the rule allows while the voltage is low. Constant-power loads draw more amps as voltage falls.',
  'below power floor': 'Sheds more load than the rule allows during the dip.',
  'cooling tripped': 'Chiller motors drop out on undervoltage, so part of the load never comes back.',
  'PSU shutdown and restart delay': 'Server power supplies shut off and take too long to restart.',
  'storage hand-back too slow': 'The battery takes too long to hand the load back to the grid.',
  'disconnected inside envelope': 'Protection disconnects the site at a voltage the rule says it must ride through.',
  'missed 2.0 s recovery': 'Power is not back to 90% within 2.0 s of the voltage recovering.',
  'voltage collapse': 'No stable operating point exists: the grid connection cannot hold voltage.',
  'no disturbance': 'No dip: the voltage never leaves normal range.',
}

function at(r: Run, key: 'v' | 'i' | 'p' | 'bbu', t: number): number {
  const ts = r.t!, ys = r[key]!
  if (t <= ts[0]) return ys[0]
  if (t >= ts[ts.length - 1]) return ys[ys.length - 1]
  let lo = 0, hi = ts.length - 1
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (ts[m] <= t) lo = m; else hi = m }
  const f = (t - ts[lo]) / (ts[hi] - ts[lo])
  return ys[lo] + f * (ys[hi] - ys[lo])
}

export default function Results() {
  const [sweep, setSweep] = useState<Sweep | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [mw, setMw] = useState(800)
  const [depth, setDepth] = useState(0.6)
  const [played, setPlayed] = useState<number | null>(null) // depth of the run on screen
  const [trigger, setTrigger] = useState(0)
  const [clock, setClock] = useState<{ a: number; active: boolean }>({ a: -99, active: false })

  useEffect(() => {
    fetch('/data/depth_sweep.json').then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setSweep).catch((err) => { console.warn('depth sweep failed to load:', err); setLoadError(true) })
    fetch('/data/grid.json').then((r) => r.json()).then((g) => g?.dc?.mw && setMw(g.dc.mw)).catch(() => {})
  }, [])

  const runFor = (d: number) => sweep?.runs.reduce((a, b) => (Math.abs(b.depth - d) < Math.abs(a.depth - d) ? b : a))
  const selected = runFor(depth)
  const run = played !== null ? runFor(played) : undefined
  // Runs with no valid operating point sit on a collapsed solution: their traces are not physical, so they are not replayed.
  const usable = !!run && run.ok && !!run.t && run.numerics_ok !== false
  const invalid = !!run && !usable
  const start = sweep?.dip.start_s ?? 1
  const tEnd = usable ? run!.t![run!.t!.length - 1] : 15
  const aEnd = SLOW_A + Math.max(0, tEnd - start - SLOW * SLOW_A) / FAST // animation seconds from dip arrival to end of window
  const hold = Math.max(1, aEnd - 2.4) // GridDemo ends the event at tHit + hold + 2.4

  // animation clock (seconds since the dip reached the site) -> simulated time
  const simT = (a: number) => (a < 0 ? start - 0.05 : a < SLOW_A ? start + a * SLOW : start + SLOW * SLOW_A + (a - SLOW_A) * FAST)
  const a = played === null ? -99 : clock.active ? clock.a : clock.a > 0 ? aEnd : -99 // after playback, hold the last frame
  const t = simT(a)
  const cap = sweep?.current_cap_pu ?? 1.5

  const frame = useMemo(() => {
    if (!usable) return null
    const v = at(run!, 'v', t), i = at(run!, 'i', t), p = at(run!, 'p', t), bbu = run!.bbu ? at(run!, 'bbu', t) : 0
    return { v, i, p, bbu }
  }, [run, usable, t])

  const drive = useMemo(() => {
    if (invalid) return { s: 0, r: 0, bbu: 0, dcText: 'DATA CENTER\nNO VALID RESULT',
      status: a < 0 && a > -50 ? 'GRID FAULT  ·  DIP TRAVELLING TO THE DATA CENTER' : 'NO STABLE OPERATING POINT AT THIS DEPTH', strained: false }
    if (!frame) return undefined
    const s = clamp01(1 - frame.p)
    const over = clamp01((frame.i - 1) / Math.max(cap - 1, 0.05))
    const strained = s > 0.5 || frame.i > cap
    const gridMw = Math.max(0, Math.round(mw * frame.p))
    const onBattery = frame.bbu > 0.5
    const dcText = `DATA CENTER\n${gridMw} MW FROM GRID${onBattery ? '  ·  ON BATTERY' : ''}`
    const inDip = t >= start && t <= start + (sweep?.dip.duration_s ?? 0.083)
    const status = played === null || a < -50 ? 'NORMAL OPERATION'
      : a < 0 ? 'GRID FAULT  ·  DIP TRAVELLING TO THE DATA CENTER'
      : s > 0.5 ? 'LOAD OFF THE GRID  ·  GRID STRAINED'
      : frame.i > cap ? 'CURRENT ABOVE THE CAP  ·  GRID STRAINED'
      : inDip || frame.v < 0.9 ? 'DIP AT THE SITE  ·  RIDING THROUGH'
      : clock.active ? 'VOLTAGE RECOVERED' : 'END OF SIMULATION'
    return { s, r: Math.max(s, over), bbu: clamp01(frame.bbu), dcText, status, strained }
  }, [frame, invalid, cap, mw, t, start, sweep, played, a, clock.active])

  const simulate = () => { setPlayed(depth); setTrigger((n) => n + 1) }
  const verdictShown = played !== null && (invalid ? a >= 0 : usable && a >= SLOW_A * 0.75)
  const pending = played !== null && clock.active && !verdictShown

  return (
    <div className="relative h-full min-h-[640px]">
      <GridDemo embedded trigger={trigger} hold={hold} drive={drive}
        onClock={(secs, active) => setClock((c) => (c.a === secs && c.active === active ? c : { a: secs, active }))} />

      <div className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(ellipse 760px 720px at 0% 0%, rgba(7,7,10,0.97) 0%, rgba(7,7,10,0.9) 48%, rgba(7,7,10,0.45) 75%, transparent 100%), radial-gradient(ellipse 420px 300px at 100% 0%, rgba(7,7,10,0.85), transparent 100%)' }} />

      {/* controls and verdict */}
      <div className="absolute top-8 left-10 w-[420px] [text-shadow:0_0_14px_rgba(7,7,10,0.95)]">
        <p className={`${label} text-[#d9b24c]`}>Results · grid-friendly design · simulator</p>
        <h1 className="display mt-3 text-[34px] leading-[1.06] font-semibold tracking-[-0.035em] text-[#f6f1e2]">Pick a voltage dip. See if the connection holds.</h1>
        <p className="mt-3 text-[14.5px] leading-[1.55] text-[#d3ccb8]">
          A fault on the grid sends a voltage dip to the data center. Choose how deep it goes, then run it.
        </p>

        <div className="mt-6">
          <div className="flex items-baseline justify-between">
            <span className={`${label} text-[#a8a089]`}>Voltage left during the dip</span>
            <span className="display text-[28px] font-semibold tracking-[-0.03em] text-[#f6f1e2]">{depth.toFixed(2)}<span className="ml-1 text-[14px] font-medium text-[#a8a089]">pu</span></span>
          </div>
          <input type="range" min={0} max={1} step={0.01} value={depth} onChange={(e) => setDepth(Number(e.target.value))}
            aria-label="Voltage left during the dip, per unit" className="mt-2 w-full cursor-pointer accent-[#d9b24c]" />
          <div className="mono mt-1 flex justify-between text-[10.5px] text-[#8d8670]">
            <span>0.00 · total collapse</span><span>1.00 · no dip</span>
          </div>
          {sweep && selected && !selected.in_scope && (
            <p className="mono mt-2 text-[11px] leading-snug text-[#ff8a63]">
              Outside {sweep.valid_dip_depth_pu[0].toFixed(2)}–{sweep.valid_dip_depth_pu[1].toFixed(2)} pu, the range the simulator is validated for. Treat as indicative.
            </p>
          )}
          <button onClick={simulate} disabled={!sweep || pending}
            className={`mono mt-5 rounded-full px-5 py-2 text-[12.5px] font-medium tracking-[0.12em] uppercase transition ${!sweep || pending ? 'cursor-default bg-[#2b2720] text-[#6f6958]' : 'cursor-pointer bg-[#d9b24c] text-[#14120e] hover:bg-[#f0c85a]'}`}>
            {pending ? 'Simulating…' : played === null ? '▸ Simulate the fault' : '▸ Simulate again'}
          </button>
          {loadError && <p className="mono mt-3 text-[11.5px] text-[#ff8a63]">No simulator results found. Run python scripts/export_depth_sweep.py.</p>}
        </div>

        {played !== null && run && <Verdict run={run} shown={verdictShown} />}
      </div>

      {/* live readouts */}
      {frame && (
        <div className="pointer-events-none absolute top-8 right-10 space-y-4 text-right">
          <Readout name="Voltage at the site" value={frame.v.toFixed(2)} unit="pu" warn={frame.v < 0.9} />
          <Readout name="Draw from the grid" value={String(Math.max(0, Math.round(mw * frame.p)))} unit="MW" warn={frame.p < 0.5} />
          <Readout name="Current" value={String(Math.round(frame.i * 100))} unit={`% · cap ${Math.round(cap * 100)}%`} warn={frame.i > cap} />
          <Readout name="Battery" value={String(Math.round(clamp01(frame.bbu) * 100))} unit="% of load" warn={false} />
        </div>
      )}

      {usable && <Timeline run={run!} a={a} aEnd={aEnd} simT={simT} cap={cap} />}
    </div>
  )
}

function Readout({ name, value, unit, warn }: { name: string; value: string; unit: string; warn: boolean }) {
  return (
    <div>
      <p className="mono text-[10.5px] tracking-[0.14em] text-[#a8a089] uppercase">{name}</p>
      <p className="display text-[36px] leading-[1] font-semibold tracking-[-0.035em]" style={{ color: warn ? '#ff6a55' : '#f6f1e2' }}>
        {value}<span className="ml-1.5 text-[13px] font-medium tracking-normal text-[#a8a089]">{unit}</span>
      </p>
    </div>
  )
}

function Verdict({ run, shown }: { run: Run; shown: boolean }) {
  if (!shown) return null
  const noResult = !run.ok || run.numerics_ok === false
  const mode = run.failure_mode ?? ''
  const pass = !noResult && !!run.passed
  const color = noResult ? '#a8a089' : pass ? '#5dbb7a' : '#ff6a55'
  return (
    <div className="mt-7 border-l-2 bg-[rgba(7,7,10,0.75)] px-5 py-4" style={{ borderColor: color }}>
      <p className={`${label}`} style={{ color }}>{noResult ? 'No valid result' : pass ? 'Connection rides through' : 'Connection fails the rule'}</p>
      <p className="mt-2 text-[14.5px] leading-[1.5] text-[#f6f1e2]">
        {noResult ? (run.numerics_note ? `${MODE_TEXT[mode] ?? run.numerics_note}` : 'The simulator did not produce a result at this depth.')
          : MODE_TEXT[pass ? 'passed' : mode] ?? mode}
      </p>
      {!noResult && (
        <p className="mono mt-3 text-[11px] leading-[1.6] text-[#a8a089]">
          peak current {Math.round((run.peak_current_pu ?? 0) * 100)}% · lowest grid power {Math.round((run.min_power ?? 0) * 100)}%
          {run.recovery_margin_s !== undefined && ` · recovery ${run.recovery_margin_s >= 0 ? `${run.recovery_margin_s.toFixed(2)} s early` : `${(-run.recovery_margin_s).toFixed(2)} s late`}`}
        </p>
      )}
    </div>
  )
}

function Timeline({ run, a, aEnd, simT, cap }: { run: Run; a: number; aEnd: number; simT: (a: number) => number; cap: number }) {
  const W = 600, H = 132, L = 34, R = 10, T = 10, B = 22, YMAX = 2
  const X = (aa: number) => L + ((aa - PRE_A) / (aEnd - PRE_A)) * (W - L - R)
  const Y = (v: number) => T + (1 - Math.min(v, YMAX) / YMAX) * (H - T - B)
  const n = 260
  const path = (key: 'v' | 'i' | 'p') => Array.from({ length: n + 1 }, (_, k) => {
    const aa = PRE_A + (k / n) * (aEnd - PRE_A)
    return `${k ? 'L' : 'M'}${X(aa).toFixed(1)},${Y(at(run, key, simT(aa))).toFixed(1)}`
  }).join('')
  const ticks = [0, 0.3, 0.6, 2, 5, 10, 14].filter((dt) => dt <= simT(aEnd) - simT(0))
  const aOf = (dt: number) => (dt <= SLOW * SLOW_A ? dt / SLOW : SLOW_A + (dt - SLOW * SLOW_A) / FAST)
  const showHead = a > -50
  return (
    <div className="pointer-events-none absolute right-10 bottom-6 rounded bg-[rgba(7,7,10,0.82)] px-4 pt-3 pb-2">
      <div className="mono flex gap-4 text-[10.5px] tracking-[0.1em] uppercase">
        <span className="text-[#d9b24c]">— voltage</span><span className="text-[#f6f1e2]">— grid power</span><span className="text-[#ff8a63]">— current</span>
        <span className="text-[#8d8670]">slow motion ×{SLOW} for the first {(SLOW * SLOW_A).toFixed(1)} s</span>
      </div>
      <svg width={W} height={H} className="mt-1 block">
        {[0, 1, 2].map((v) => <g key={v}><line x1={L} x2={W - R} y1={Y(v)} y2={Y(v)} stroke="#2b2720" /><text x={L - 6} y={Y(v) + 4} textAnchor="end" className="mono" fontSize={10} fill="#8d8670">{v}</text></g>)}
        <line x1={L} x2={W - R} y1={Y(cap)} y2={Y(cap)} stroke="#ff8a63" strokeDasharray="3 4" strokeOpacity={0.7} />
        <text x={W - R} y={Y(cap) - 4} textAnchor="end" className="mono" fontSize={10} fill="#ff8a63">current cap</text>
        <rect x={L} y={T} width={X(SLOW_A) - L} height={H - T - B} fill="#d9b24c" fillOpacity={0.04} />
        <path d={path('v')} fill="none" stroke="#d9b24c" strokeWidth={1.8} />
        <path d={path('p')} fill="none" stroke="#f6f1e2" strokeWidth={1.5} />
        <path d={path('i')} fill="none" stroke="#ff8a63" strokeWidth={1.3} />
        {ticks.map((dt) => <text key={dt} x={X(aOf(dt))} y={H - 6} textAnchor="middle" className="mono" fontSize={10} fill="#8d8670">{dt === 0 ? 'dip' : `+${dt}s`}</text>)}
        {showHead && <line x1={X(Math.max(PRE_A, Math.min(a, aEnd)))} x2={X(Math.max(PRE_A, Math.min(a, aEnd)))} y1={T} y2={H - B} stroke="#f6f1e2" strokeWidth={1} />}
      </svg>
    </div>
  )
}
