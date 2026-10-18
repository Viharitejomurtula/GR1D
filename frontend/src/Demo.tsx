import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import GridDemo from './GridDemo'

// Scrollytelling demo for the Results tab: sample the world, hunt for failures, crash-test one.
// The runs are real graded simulator output (data/runs.csv). The network draws and the replay
// curves are illustrative: the stage says so. Hardcoded for now; swap `pickRun` for a live call later.

export type Run = { depth: number; duration: number; temp: number; age: number; mode: string }
export type ModeInfo = { name: string; color: string; what: string }

const GOLD = '#d9b24c', GREEN = '#5dbb7a', INK = '#f6f1e2', MUTE = '#8d8670', LINE = 'rgba(255,255,255,0.14)', RED = '#ff6a55'
const MONO = { fontFamily: '"IBM Plex Mono", monospace' } as const
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
function rng(seed: number) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 } }

const RANGE = { depth: [0, 0.9], duration: [50, 320], temp: [-20, 45], age: [0, 10] } as const
const nrm = (k: keyof typeof RANGE, v: number) => (v - RANGE[k][0]) / (RANGE[k][1] - RANGE[k][0])

const ACTS = [
  { n: '01', kicker: 'Sample the world', title: 'No two dips hit the same site.',
    body: 'Temperature, battery age, site load and workload are linked. We draw scenarios from a network that keeps those links, so a cold morning and an old battery show up together.' },
  { n: '02', kicker: 'Hunt for failures', title: 'Search the conditions for the ways it breaks.',
    body: 'Every dot is one graded simulator run. Failures pull together into distinct modes instead of a pile of near-copies. Click a dot or a mode.' },
  { n: '03', kicker: 'Crash test', title: 'Replay a failure, second by second.',
    body: 'Pick a mode and watch the dip travel to the site, the battery carry the load, and the verdict land.' },
]

export default function Demo({ runs, modes, order }: { runs: Run[]; modes: Record<string, ModeInfo>; order: string[] }) {
  const [act, setAct] = useState(0)
  const refs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) setAct(Number((e.target as HTMLElement).dataset.act)) }), { rootMargin: '-45% 0px -45% 0px' })
    refs.current.forEach((r) => r && io.observe(r))
    return () => io.disconnect()
  }, [])

  // one representative run per mode (nearest the mode's centroid), used when a mode is picked
  const rep = useMemo(() => {
    const out: Record<string, Run> = {}
    for (const m of ['pass', ...order]) {
      let pool = runs.filter((r) => r.mode === m)
      if (m === 'pass') pool = pool.filter((r) => r.depth < 0.65).length ? pool.filter((r) => r.depth < 0.65) : pool
      if (!pool.length) continue
      const K = ['depth', 'duration', 'temp', 'age'] as const
      const c = K.map((k) => pool.reduce((a, r) => a + nrm(k, r[k]), 0) / pool.length)
      out[m] = pool.reduce((best, r) => {
        const d = K.reduce((a, k, i) => a + (nrm(k, r[k]) - c[i]) ** 2, 0)
        return d < best.d ? { d, r } : best
      }, { d: Infinity, r: pool[0] }).r
    }
    return out
  }, [runs, order])

  const topMode = useMemo(() => [...order].sort((a, b) => runs.filter((r) => r.mode === b).length - runs.filter((r) => r.mode === a).length)[0], [runs, order])
  const [picked, setPicked] = useState<Run | null>(null)
  const run = picked ?? rep[topMode] ?? runs[0]

  return (
    <div className="mt-24 grid gap-x-14 md:grid-cols-[360px_1fr]">
      <div>
        {ACTS.map((a, i) => (
          <div key={a.n} ref={(el) => { refs.current[i] = el }} data-act={i} className="flex min-h-[92vh] items-center">
            <div className="transition-opacity duration-500" style={{ opacity: act === i ? 1 : 0.28 }}>
              <p className="mono text-[12px] font-medium tracking-[0.14em] text-[#d9b24c] uppercase">{a.n} · {a.kicker}</p>
              <h2 className="display mt-3 text-[38px] leading-[1.05] font-semibold tracking-[-0.035em] text-[#f6f1e2]">{a.title}</h2>
              <p className="mt-4 text-[16.5px] leading-[1.6] text-[#c4bca7]">{a.body}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="relative">
        <div className="sticky top-4 h-[min(680px,calc(100vh-56px))] overflow-hidden border border-white/12 bg-[#09090d]">
          <AnimatePresence mode="wait">
            <motion.div key={act} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
              {act === 0 && <NetworkStage />}
              {act === 1 && <HuntStage runs={runs} modes={modes} order={order} rep={rep} run={run} onPick={setPicked} />}
              {act === 2 && <CrashStage modes={modes} order={order} rep={rep} run={run} onPick={setPicked} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

function Foot({ children }: { children: ReactNode }) {
  return <p className="mono absolute right-5 bottom-3 left-5 text-[10.5px] leading-[1.5] tracking-[0.05em] text-[#8d8670]">{children}</p>
}

/* ------------------------------------------------------------------ 01: network ------------------------------------------------------------------ */

type Draw = { temp: number; age: number; load: number; work: number; f: number[] } // f: factor values 0..1
const DRIVERS = [['Outdoor temperature', 80], ['Equipment age', 190], ['Site load', 300], ['AI workload', 410]] as const
const FACTORS = ['Battery resistance', 'Usable energy', 'Converter limit', 'Capacitor health', 'PSU hold-up', 'AI swing size'] as const
const FY = (i: number) => 60 + i * 68
const EDGES: [number, number][] = [[0, 0], [0, 1], [0, 2], [1, 0], [1, 3], [1, 4], [2, 4], [3, 5]] // driver -> factor

const DRAWS: Draw[] = (() => {
  const R = rng(17), g = () => (R() + R() + R()) / 3
  return Array.from({ length: 150 }, () => {
    const temp = g(), age = R(), load = g(), work = R(), n = () => (R() - 0.5) * 0.12
    return {
      temp, age, load, work,
      f: [
        clamp(0.5 + (0.5 - temp) * 0.8 + (age - 0.5) * 0.35 + n(), 0.03, 0.97),
        clamp(0.55 + (temp - 0.5) * 0.55 - (age - 0.5) * 0.3 + n(), 0.03, 0.97),
        clamp(0.95 - Math.max(0, temp - 0.6) * 1.3 + n(), 0.03, 0.97),
        clamp(0.9 - age * 0.55 + n(), 0.03, 0.97),
        clamp(0.9 - age * 0.3 - load * 0.45 + n(), 0.03, 0.97),
        clamp(0.2 + work * 0.7 + n(), 0.03, 0.97),
      ],
    }
  })
})()

function NetworkStage() {
  const [n, setN] = useState(1)
  const [linked, setLinked] = useState(true)
  useEffect(() => {
    const id = setInterval(() => setN((k) => (k >= DRAWS.length ? k : k + 1)), 340)
    return () => clearInterval(id)
  }, [])
  const cur = DRAWS[n - 1]
  const dv = [cur.temp, cur.age, cur.load, cur.work]
  const PX = (v: number) => 470 + v * 190, PY = (v: number) => 420 - v * 300
  return (
    <div className="absolute inset-0 flex flex-col">
      <svg viewBox="0 0 700 540" className="min-h-0 w-full flex-1" role="img" aria-label="A network linking outdoor temperature, equipment age, site load and workload to equipment factors, with each sampled scenario plotted on the right.">
        {EDGES.map(([d, f], i) => {
          const y1 = DRIVERS[d][1] + 40, y2 = FY(f) + 12
          return <path key={i} d={`M150,${y1} C240,${y1} 240,${y2} 330,${y2}`} fill="none" stroke={GOLD} strokeWidth={1.4}
            style={{ opacity: 0.12 + 0.8 * dv[d], transition: 'opacity 0.3s' }} />
        })}
        {DRIVERS.map(([name, y], i) => (
          <g key={name} transform={`translate(10,${y})`}>
            <rect width={140} height={52} fill="#0e0e13" stroke={GOLD} strokeOpacity={0.5} />
            <rect width={140 * dv[i]} height={3} y={49} fill={GOLD} style={{ transition: 'width 0.3s' }} />
            <text x={10} y={22} fontSize={11} fill={INK} style={MONO}>{name}</text>
            <text x={10} y={39} fontSize={10} fill={MUTE} style={MONO}>driver</text>
          </g>
        ))}
        {FACTORS.map((name, i) => (
          <g key={name} transform={`translate(330,${FY(i)})`}>
            <rect width={130} height={26} fill="#0e0e13" stroke={LINE} />
            <rect width={130 * cur.f[i]} height={26} fill={GOLD} opacity={0.22} style={{ transition: 'width 0.3s' }} />
            <text x={8} y={17} fontSize={10.5} fill={INK} style={MONO}>{name}</text>
          </g>
        ))}
        <text x={10} y={40} fontSize={10.5} fill={MUTE} style={MONO}>DRIVERS</text>
        <text x={330} y={40} fontSize={10.5} fill={MUTE} style={MONO}>EQUIPMENT FACTORS</text>
        <text x={470} y={40} fontSize={10.5} fill={MUTE} style={MONO}>SCENARIOS DRAWN</text>
        <text x={470} y={58} fontSize={22} fill={INK} style={{ ...MONO, fontWeight: 600 }}>{n}</text>
        <rect x={470} y={120} width={190} height={300} fill="none" stroke={LINE} />
        {Array.from({ length: n }, (_, i) => {
          const u = linked ? DRAWS[i].f[1] : DRAWS[(i * 37 + 11) % DRAWS.length].f[1]
          const last = i === n - 1
          return <circle key={i} cx={PX(DRAWS[i].f[0])} cy={PY(u)} r={last ? 4.5 : 2.4} fill={last ? INK : GOLD} opacity={last ? 1 : 0.55} style={{ transition: 'cx 0.5s, cy 0.5s' }} />
        })}
        <text x={565} y={440} textAnchor="middle" fontSize={10} fill={MUTE} style={MONO}>battery resistance →</text>
        <text x={462} y={270} textAnchor="middle" fontSize={10} fill={MUTE} transform="rotate(-90 462 270)" style={MONO}>usable energy →</text>
      </svg>
      <div className="flex items-center justify-between px-5 pb-12">
        <div className="flex gap-0 border border-white/14">
          {([[true, 'Linked (our network)'], [false, 'Independent']] as const).map(([v, t]) => (
            <button key={t} onClick={() => setLinked(v)} className={`mono cursor-pointer px-3.5 py-2 text-[11px] tracking-[0.1em] uppercase transition ${linked === v ? 'bg-[#d9b24c] text-[#07070a]' : 'text-[#c4bca7] hover:text-white'}`}>{t}</button>
          ))}
        </div>
        <p className="mono max-w-[300px] text-right text-[11px] leading-[1.5] text-[#c4bca7]">
          {linked ? 'Cold weather raises resistance and cuts usable energy together, so bad combinations are common.' : 'Treated as independent, the bad combinations disappear from the picture.'}
        </p>
      </div>
      <Foot>Illustrative draws. The links shown are the ones with evidence behind them.</Foot>
    </div>
  )
}

/* ------------------------------------------------------------------ 02: hunt ------------------------------------------------------------------ */

function HuntStage({ runs, modes, order, rep, run, onPick }: { runs: Run[]; modes: Record<string, ModeInfo>; order: string[]; rep: Record<string, Run>; run: Run; onPick: (r: Run) => void }) {
  const [scan, setScan] = useState(0)
  const [grouped, setGrouped] = useState(false)
  useEffect(() => {
    let raf = 0, t0 = performance.now(), to: ReturnType<typeof setTimeout>
    const tick = (now: number) => {
      const s = clamp((now - t0) / 2800, 0, 1)
      setScan(s)
      if (s < 1) raf = requestAnimationFrame(tick)
      else to = setTimeout(() => setGrouped(true), 700)
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); clearTimeout(to) }
  }, [])

  const W = 700, H = 540, L = 56, T = 52, B = 70, Rg = 24
  const mapX = (d: number) => L + (1 - nrm('depth', d)) * (W - L - Rg)
  const mapY = (t: number) => T + (1 - nrm('temp', t)) * (H - T - B)
  const counts = useMemo(() => Object.fromEntries(order.map((m) => [m, runs.filter((r) => r.mode === m).length])), [runs, order])
  const active = order.filter((m) => counts[m] > 0)
  const centers = useMemo(() => {
    const out: Record<string, [number, number]> = {}
    const cx = W / 2, cy = (T + H - B) / 2 + 6
    const by = [...active].sort((a, b) => counts[b] - counts[a])
    by.forEach((m, i) => {
      if (i === 0) out[m] = [cx, cy]
      else { const a = -Math.PI / 2 + ((i - 1) / Math.max(by.length - 1, 1)) * Math.PI * 2; out[m] = [cx + Math.cos(a) * 215, cy + Math.sin(a) * 165] }
    })
    return out
  }, [active, counts])
  const idxInMode = useMemo(() => { const c: Record<string, number> = {}; return runs.map((r) => (c[r.mode] = (c[r.mode] ?? -1) + 1)) }, [runs])
  const fails = runs.filter((r) => r.mode !== 'pass').length

  const pos = (r: Run, i: number): [number, number] => {
    if (grouped && r.mode !== 'pass' && centers[r.mode]) {
      const k = idxInMode[i], a = k * 2.399963, rad = 5.2 * Math.sqrt(k + 0.5)
      return [centers[r.mode][0] + Math.cos(a) * rad, centers[r.mode][1] + Math.sin(a) * rad]
    }
    return [mapX(r.depth), mapY(r.temp)]
  }
  const shown = (r: Run) => (1 - nrm('depth', r.depth)) <= scan

  return (
    <div className="absolute inset-0">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Simulator runs plotted by dip depth and temperature, then grouped into failure modes.">
        <g style={{ opacity: grouped ? 0 : 1, transition: 'opacity 0.5s' }}>
          <rect x={L} y={T} width={W - L - Rg} height={H - T - B} fill="none" stroke={LINE} />
          {[0, 0.3, 0.6, 0.9].map((d) => <text key={d} x={mapX(d)} y={H - B + 18} textAnchor="middle" fontSize={10} fill={MUTE} style={MONO}>{d.toFixed(1)}</text>)}
          {[-20, 0, 20, 40].map((t) => <text key={t} x={L - 8} y={mapY(t) + 3} textAnchor="end" fontSize={10} fill={MUTE} style={MONO}>{t}°</text>)}
          <text x={(L + W - Rg) / 2} y={H - B + 38} textAnchor="middle" fontSize={10} fill={MUTE} style={MONO}>← deeper dip        dip depth (pu)        shallower →</text>
          <text x={14} y={(T + H - B) / 2} textAnchor="middle" fontSize={10} fill={MUTE} transform={`rotate(-90 14 ${(T + H - B) / 2})`} style={MONO}>temperature</text>
        </g>
        {!grouped && scan < 1 && <line x1={L + scan * (W - L - Rg)} x2={L + scan * (W - L - Rg)} y1={T} y2={H - B} stroke={GOLD} strokeWidth={1.5} opacity={0.8} />}
        {runs.map((r, i) => {
          const [x, y] = pos(r, i), fail = r.mode !== 'pass'
          const color = fail ? modes[r.mode]?.color ?? RED : GREEN
          const sel = r === run
          return (
            <g key={i} style={{ transform: `translate(${x}px, ${y}px)`, transition: `transform 1.1s cubic-bezier(.3,.9,.3,1) ${(i % 25) * 0.012}s`, cursor: 'pointer' }} onClick={() => onPick(r)}>
              <circle r={sel ? 6 : fail ? 3.6 : 2.6} fill={color} opacity={!shown(r) ? 0 : grouped && !fail ? 0.1 : fail ? 0.95 : 0.5} style={{ transition: 'opacity 0.5s' }} />
              {sel && <circle r={11} fill="none" stroke={INK} strokeWidth={1.5} />}
            </g>
          )
        })}
        {grouped && active.map((m) => {
          const [cx, cy] = centers[m], R = 5.2 * Math.sqrt(counts[m] + 0.5) + 12
          const ly = cy + R + 16
          return (
            <g key={m} style={{ cursor: 'pointer' }} onClick={() => rep[m] && onPick(rep[m])}>
              <text x={cx} y={ly} textAnchor="middle" fontSize={12} fill={INK} style={{ ...MONO, fontWeight: 600 }}>{modes[m].name}</text>
              <text x={cx} y={ly + 15} textAnchor="middle" fontSize={10.5} fill={modes[m].color} style={MONO}>{((counts[m] / runs.length) * 100).toFixed(1)}% of runs</text>
            </g>
          )
        })}
      </svg>
      <div className="absolute top-3 right-5 left-5 flex items-baseline justify-between">
        <p className="mono text-[11px] tracking-[0.12em] text-[#8d8670] uppercase">Runs scanned <span className="text-[#f6f1e2]">{Math.round(scan * runs.length)}</span> / {runs.length}</p>
        <p className="mono text-[11px] tracking-[0.12em] uppercase" style={{ color: grouped ? GOLD : MUTE }}>{grouped ? `${active.length} failure modes · ${((fails / runs.length) * 100).toFixed(0)}% of runs fail` : 'searching…'}</p>
      </div>
      <button onClick={() => setGrouped((g) => !g)} className="mono absolute bottom-9 left-5 cursor-pointer text-[11px] tracking-[0.12em] text-[#f0c85a] uppercase underline-offset-[6px] transition hover:text-white hover:underline">
        {grouped ? '← Back to the map' : 'Group by failure mode →'}
      </button>
      <Foot>400 real graded simulator runs. The million-scenario surrogate search is not built yet.</Foot>
    </div>
  )
}

/* ------------------------------------------------------------------ 03: crash test ------------------------------------------------------------------ */

type Curve = { cur: (t: number) => number; t0: number; t1: number; back: number; deadline: number; T: number; facility: (t: number) => number; volt: (t: number) => number; peakCur: number; minP: number }

function makeCurve(r: Run): Curve {
  const t0 = 1, t1 = t0 + r.duration / 1000, back = t1 + 0.08, deadline = back + 2, T = 8
  const floor = r.mode === 'below power floor'
  const minP = floor ? 8 : clamp(15 + r.depth * 33, 12, 55)
  const knee = t0 + 0.06
  const x = (t: number) => t - knee
  let rec: (t: number) => number
  switch (r.mode) {
    case 'storage hand-back too slow': {
      const tau = (deadline + 0.9 - knee) / -Math.log(1 - (90 - minP) / (98 - minP))
      rec = (t) => minP + (98 - minP) * (1 - Math.exp(-x(t) / tau)); break
    }
    case 'cooling tripped': rec = (t) => minP + (64 - minP) * (1 - Math.exp(-x(t) / 0.5)); break
    case 'PSU shutdown and restart delay': {
      const ts = deadline + 1.4
      rec = (t) => (t < ts ? minP : minP + (98 - minP) * clamp((t - ts) / 0.4, 0, 1)); break
    }
    case 'below power floor': rec = (t) => minP + (98 - minP) * (1 - Math.exp(-x(t) / 0.8)); break
    default: rec = (t) => minP + (98 - minP) * (1 - Math.exp(-x(t) / 0.45))
  }
  const facility = (t: number) => (t < t0 ? 100 : t < knee ? 100 - ((100 - minP) * (t - t0)) / 0.06 : rec(t))
  const volt = (t: number) => (t < t0 ? 1 : t < t1 ? r.depth : 1 - (1 - r.depth) * Math.exp(-(t - t1) / 0.05))
  const peakCur = r.mode === 'exceeded 125% current cap' ? 1.6 : 1 + (1 - r.depth) * 0.2
  // facility current in x normal: constant-power draw rises as voltage falls
  const cur = (t: number) => 1 + (peakCur - 1) * clamp((100 - facility(t)) / (100 - minP), 0, 1) * (t < t0 ? 0 : t < t1 + 0.4 ? 1 : Math.exp(-(t - t1 - 0.4) / 0.35))
  return { cur, t0, t1, back, deadline, T, facility, volt, peakCur, minP }
}

function CrashStage({ modes, order, rep, run, onPick }: { modes: Record<string, ModeInfo>; order: string[]; rep: Record<string, Run>; run: Run; onPick: (r: Run) => void }) {
  const c = useMemo(() => makeCurve(run), [run])
  const [trig, setTrig] = useState(0)
  const [t, setT] = useState(0)
  // start the map event shortly after the stage appears, and again whenever the run changes
  useEffect(() => {
    setT(0)
    const id = setTimeout(() => setTrig((n) => n + 1), 700)
    return () => clearTimeout(id)
  }, [run])
  const onClock = useMemo(() => (x: number, active: boolean) => { if (active || x > 0) setT(clamp(x + c.t0, 0, c.T)) }, [c])

  const pass = run.mode === 'pass'
  const done = t >= c.T - 0.05
  const m = pass ? null : modes[run.mode]
  const CH = { x: 60, y: 34, w: 590, h: 118 }
  const X = (s: number) => CH.x + (s / c.T) * CH.w, Y = (val: number) => CH.y + CH.h - (val / 100) * CH.h
  const CY = (x: number) => CH.y + CH.h - (clamp(x, 0, 2) / 2) * CH.h
  const line = (f: (s: number) => number, to: number, yf: (v: number) => number) => {
    const pts: string[] = []
    for (let s = 0; s <= to; s += 0.05) pts.push(`${X(s).toFixed(1)},${yf(f(s)).toFixed(1)}`)
    return pts.length ? 'M' + pts.join(' L') : ''
  }
  const path = useMemo(() => line(c.facility, c.T, Y), [c]) // eslint-disable-line react-hooks/exhaustive-deps
  const drawn = line(c.facility, t, Y)
  const curDrawn = line(c.cur, t, CY)

  return (
    <div className="absolute inset-0 flex flex-col">
      <div className="relative h-[47%] shrink-0 overflow-hidden border-b border-white/10">
        <GridDemo embedded trigger={trig} rideThrough={pass} hold={6} zoom={7.7} onClock={onClock} />
        <p className="mono pointer-events-none absolute top-3 left-4 text-[10.5px] tracking-[0.1em] text-[#d3ccb8] uppercase [text-shadow:0_0_6px_#000]">
          {`Dip ${run.depth.toFixed(2)} pu · ${Math.round(run.duration)} ms · ${Math.round(run.temp)} °C · battery ${run.age.toFixed(1)} yr`}
        </p>
        <AnimatePresence>
          {done && (
            <motion.div key={`${run.depth}-${run.mode}-${trig}`} className="pointer-events-none absolute top-[40px] right-6 text-right"
              initial={{ opacity: 0, scale: 2.3, rotate: -22, y: -30 }} animate={{ opacity: 1, scale: 1, rotate: -8, y: 0 }}
              transition={{ type: 'spring', stiffness: 520, damping: 22 }}>
              <p className="display border-[3px] px-4 py-1 text-[44px] leading-none font-bold tracking-[-0.02em]"
                style={{ color: pass ? GREEN : RED, borderColor: pass ? GREEN : RED, background: 'rgba(7,7,10,0.9)' }}>{pass ? 'PASS' : 'FAIL'}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <svg viewBox="0 0 700 176" className="w-full shrink-0" role="img" aria-label="Power drawn from the grid and facility current over time against the 2 second deadline.">
        <rect x={CH.x} y={CH.y} width={CH.w} height={CH.h} fill="none" stroke={LINE} />
        <line x1={CH.x} x2={CH.x + CH.w} y1={Y(90)} y2={Y(90)} stroke={INK} strokeOpacity={0.45} strokeDasharray="3 4" />
        <text x={CH.x - 6} y={Y(90) + 3} textAnchor="end" fontSize={10} fill={MUTE} style={MONO}>90%</text>
        <line x1={X(c.deadline)} x2={X(c.deadline)} y1={CH.y} y2={CH.y + CH.h} stroke={GOLD} strokeDasharray="4 3" />
        <text x={X(c.deadline) + 5} y={CH.y + 12} fontSize={10} fill={GOLD} style={MONO}>2 s deadline</text>
        <line x1={CH.x} x2={CH.x + CH.w} y1={CY(1.25)} y2={CY(1.25)} stroke="#ff8a3d" strokeOpacity={0.5} strokeDasharray="2 4" />
        <text x={CH.x + CH.w - 4} y={CY(1.25) - 4} textAnchor="end" fontSize={9.5} fill="#ff8a3d" style={MONO}>125% current cap</text>
        <path d={path} fill="none" stroke={INK} strokeOpacity={0.12} strokeWidth={2} />
        <path d={curDrawn} fill="none" stroke="#ff8a3d" strokeWidth={1.6} />
        <path d={drawn} fill="none" stroke={pass || !done ? GREEN : RED} strokeWidth={2.4} />
        <text x={CH.x} y={CH.y - 10} fontSize={10.5} fill={MUTE} style={MONO}>POWER DRAWN (GREEN, % OF PRE-FAULT) AND CURRENT (ORANGE)</text>
        {[0, 2, 4, 6].map((s) => <text key={s} x={X(s)} y={CH.y + CH.h + 16} textAnchor="middle" fontSize={10} fill={MUTE} style={MONO}>{s} s</text>)}
      </svg>

      <div className="px-5 pb-11">
        <div className="min-h-[40px]">
          <p className="text-[13.5px] leading-[1.45] text-[#d3ccb8]">
            {pass ? <><span className="text-[#5dbb7a]">Passed.</span> Power is back above 90% before the deadline.</>
              : <><span style={{ color: m?.color }}>{m?.name}.</span> {m?.what}</>}
            {run.mode === 'exceeded 125% current cap' && done ? <span className="text-[#ff8a3d]"> Peak current here: {c.peakCur.toFixed(2)}× normal.</span> : null}
          </p>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {['pass', ...order].filter((k) => rep[k]).map((k) => (
            <button key={k} onClick={() => onPick(rep[k])}
              className="mono cursor-pointer border px-2.5 py-1.5 text-[10.5px] tracking-[0.08em] uppercase transition"
              style={{ borderColor: run.mode === k ? (k === 'pass' ? GREEN : modes[k].color) : 'rgba(255,255,255,0.14)', color: run.mode === k ? INK : '#a8a089' }}>
              <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: k === 'pass' ? GREEN : modes[k].color }} />
              {k === 'pass' ? 'Passes' : modes[k].name}
            </button>
          ))}
          <button onClick={() => { setT(0); setTrig((n) => n + 1) }} className="mono ml-auto cursor-pointer text-[11px] tracking-[0.12em] text-[#f0c85a] uppercase underline-offset-[6px] transition hover:text-white hover:underline">▸ Replay</button>
        </div>
      </div>
      <Foot>Map and verdict: the same replay as The Problem page, graded by the simulator for this run. Curve shape is illustrative.</Foot>
    </div>
  )
}
