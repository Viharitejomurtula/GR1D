import { useState } from 'react'
import { motion } from 'framer-motion'

// ILLUSTRATIVE VALUES: the pipeline does not produce these two outputs yet. Replace with real model output.
const FACTORS = [
  { name: 'Dip duration', v: 0.31 },
  { name: 'Dip depth', v: 0.24 },
  { name: 'Battery charge level', v: 0.15 },
  { name: 'Repeated dips', v: 0.11 },
  { name: 'Converter response time', v: 0.08 },
  { name: 'AI load swing', v: 0.06 },
  { name: 'Temperature', v: 0.03 },
  { name: 'Battery aging', v: 0.02 },
]
const N_SCENARIOS = 48000
const PASS = { p: 0.873, lo: 0.81, hi: 0.92 }

// output distribution: share of prior power back at 2 s, in 2% bins. Built to sum to the pass probability above.
const BINS = (() => {
  const step = 2, n = 50
  const w = Array.from({ length: n }, (_, i) => {
    const x = i * step // bin [x, x+step)
    if (x >= 90) return Math.exp(-((100 - x - step / 2) ** 2) / 14) + 0.25 // piled up near full recovery
    if (i === 0) return 9 // sites that trip off and never come back inside the window
    return 0.6 * Math.exp(-((90 - x) / 55)) + (x > 40 && x < 70 ? 0.35 : 0) // a thin tail of partial recoveries
  })
  const pass = w.filter((_, i) => i * step >= 90), fail = w.filter((_, i) => i * step < 90)
  const sp = pass.reduce((a, b) => a + b, 0), sf = fail.reduce((a, b) => a + b, 0)
  return w.map((v, i) => ({ x: i * step, p: i * step >= 90 ? (v / sp) * PASS.p : (v / sf) * (1 - PASS.p) }))
})()

// a small deterministic grid, drawn flat
function rng(seed: number) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 } }
const GRID = (() => {
  const R = rng(9)
  const nodes: [number, number][] = []
  for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) nodes.push([56 + c * 80 + (R() - 0.5) * 30, 168 + r * 82 + (R() - 0.5) * 30])
  const edges: [number, number][] = []
  for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) {
    const i = r * 5 + c
    if (c < 4 && R() < 0.9) edges.push([i, i + 1])
    if (r < 4 && R() < 0.85) edges.push([i, i + 5])
    if (r < 4 && c < 4 && R() < 0.3) edges.push([i, i + 6])
  }
  return { nodes, edges }
})()

const GOLD = '#d9b24c'
const BOX = { x: 480, y: 270, w: 240, h: 180 }

export default function SolutionDiagram() {
  const [hover, setHover] = useState<number | null>(null)
  const maxBar = 340
  const hist = { x0: 404, x1: 856, base: 662, h: 124 }
  const maxP = Math.sqrt(Math.max(...BINS.map((b) => b.p)))
  const bw = (hist.x1 - hist.x0) / BINS.length
  const hx = (pct: number) => hist.x0 + (pct / 100) * (hist.x1 - hist.x0)

  return (
    <svg viewBox="0 0 1200 720" className="w-full" role="img" aria-label="Diagram: the grid on the left, the data center on the right, and The Connection between them. Factor sensitivity rises from the box and the output distribution hangs below it.">
      <style>{`
        .flow { stroke-dasharray: 5 11; animation: flow 1.1s linear infinite; }
        @keyframes flow { to { stroke-dashoffset: -16; } }
        .mono { font-family: "IBM Plex Mono", ui-monospace, monospace; }
        .disp { font-family: "Space Grotesk", sans-serif; }
      `}</style>

      {/* ---- the grid, flat ---- */}
      <g>
        {GRID.edges.map(([a, b], i) => (
          <line key={i} x1={GRID.nodes[a][0]} y1={GRID.nodes[a][1]} x2={GRID.nodes[b][0]} y2={GRID.nodes[b][1]} stroke={GOLD} strokeOpacity={0.4} strokeWidth={1.4} />
        ))}
        {GRID.nodes.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={3} fill="#f0d98a" />)}
        {/* trunk lines into the box */}
        {[1, 3].map((r, k) => {
          const [x, y] = GRID.nodes[r * 5 + 4]
          const ty = BOX.y + 56 + k * 68
          return <polyline key={r} points={`${x},${y} ${x + 40},${y} ${x + 40},${ty} ${BOX.x},${ty}`} fill="none" stroke={GOLD} strokeWidth={3.2} strokeLinejoin="round" className="flow" />
        })}
        <text x={216} y={568} textAnchor="middle" className="mono" fontSize={12} letterSpacing="2" fill="#a8a089">THE GRID</text>
      </g>

      {/* ---- the data center, flat ---- */}
      <g>
        <rect x={790} y={246} width={370} height={226} fill="#2b2720" stroke={GOLD} strokeWidth={1.6} />
        {[0, 1, 2].flatMap((c) => [0, 1].map((r) => (
          <g key={`${c}${r}`}>
            <rect x={808 + c * 118} y={262 + r * 100} width={102} height={84} fill="#6d6249" stroke={GOLD} strokeWidth={1.4} />
            {[0, 1, 2, 3].map((k) => <rect key={k} x={818 + c * 118 + k * 22} y={274 + r * 100} width={14} height={60} fill="#ffcf5a" fillOpacity={0.22 + 0.1 * ((c + r + k) % 3)} />)}
          </g>
        )))}
        {[0, 1].map((k) => <line key={k} x1={BOX.x + BOX.w} y1={BOX.y + 56 + k * 68} x2={790} y2={BOX.y + 56 + k * 68} stroke={GOLD} strokeWidth={3.2} className="flow" />)}
        <text x={975} y={496} textAnchor="middle" className="mono" fontSize={12} letterSpacing="2" fill="#a8a089">THE DATA CENTER</text>
      </g>

      {/* ---- sensitivity: grows out of the top of the box ---- */}
      <text x={612} y={26} className="mono" fontSize={11.5} letterSpacing="1.6" fill="#a8a089">WHAT MOVES THE RESULT, RANKED</text>
      <line x1={600} y1={BOX.y} x2={600} y2={38} stroke={GOLD} strokeWidth={1.6} />
      {FACTORS.map((f, i) => {
        const y = 56 + i * 26
        const len = (f.v / FACTORS[0].v) * maxBar
        const on = hover === i
        return (
          <g key={f.name} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} style={{ cursor: 'default' }}>
            <rect x={300} y={y - 12} width={620} height={24} fill="transparent" />
            <text x={588} y={y + 4.5} textAnchor="end" className="disp" fontSize={14.5} fontWeight={600} fill={on ? '#fff6dc' : '#e8e2d2'}>
              <tspan className="mono" fontSize={11} fontWeight={400} fill="#8d8670">{String(i + 1).padStart(2, '0')}  </tspan>{f.name}
            </text>
            <motion.rect
              x={600} y={y - 7} height={14} width={len} fill={on ? '#ffd873' : GOLD} fillOpacity={i === 0 ? 1 : 0.9 - i * 0.07}
              style={{ transformBox: 'fill-box', transformOrigin: '0% 50%' }}
              initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: i * 0.06, ease: 'easeOut' }}
            />
            <text x={600 + len + 10} y={y + 4} className="mono" fontSize={12} fill={on ? '#fff6dc' : '#c4bca7'}>{Math.round(f.v * 100)}%</text>
          </g>
        )
      })}

      {/* ---- the connection ---- */}
      <rect x={BOX.x} y={BOX.y} width={BOX.w} height={BOX.h} fill="#000" stroke="#4a4332" strokeWidth={1.4} />
      <text x={BOX.x + BOX.w / 2} y={BOX.y + 84} textAnchor="middle" className="disp" fontSize={25} fontWeight={600} fill="#f6f1e2" letterSpacing="-0.5">The Connection</text>
      <text x={BOX.x + BOX.w / 2} y={BOX.y + 112} textAnchor="middle" className="mono" fontSize={11} fill="#8d8670">ride-through technology</text>
      <text x={BOX.x + BOX.w / 2} y={BOX.y + 128} textAnchor="middle" className="mono" fontSize={11} fill="#8d8670">under test</text>

      {/* ---- output distribution: projected out of the bottom of the box ---- */}
      <polygon points={`${BOX.x},${BOX.y + BOX.h} ${BOX.x + BOX.w},${BOX.y + BOX.h} ${hist.x1},500 ${hist.x0},500`} fill={GOLD} fillOpacity={0.06} stroke={GOLD} strokeOpacity={0.25} />
      <text x={hist.x0 + 8} y={520} className="mono" fontSize={11.5} letterSpacing="1.4" fill="#a8a089">POWER BACK AT 2 SECONDS, {N_SCENARIOS.toLocaleString()} SCENARIOS</text>
      {BINS.map((b, i) => {
        const h = (Math.sqrt(b.p) / maxP) * hist.h
        return (
          <motion.rect
            key={b.x} x={hist.x0 + i * bw + 0.8} y={hist.base - h} width={bw - 1.6} height={h} fill={b.x >= 90 ? GOLD : '#ff6a3d'} fillOpacity={0.92}
            style={{ transformBox: 'fill-box', transformOrigin: '50% 100%' }}
            initial={{ scaleY: 0 }} whileInView={{ scaleY: 1 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.3 + i * 0.012, ease: 'easeOut' }}
          />
        )
      })}
      <line x1={hist.x0} y1={hist.base} x2={hist.x1} y2={hist.base} stroke="#5a5444" />
      <line x1={hx(90)} y1={540} x2={hx(90)} y2={hist.base + 6} stroke="#f6f1e2" strokeDasharray="3 4" />
      <text x={hx(90) - 6} y={552} textAnchor="end" className="mono" fontSize={11} fill="#f6f1e2">ERCOT: 90%</text>
      {[0, 25, 50, 75, 100].map((t) => <text key={t} x={hx(t)} y={hist.base + 20} textAnchor="middle" className="mono" fontSize={11} fill="#8d8670">{t}%</text>)}
      <text x={hist.x1} y={hist.base + 38} textAnchor="end" className="mono" fontSize={10} fill="#6f6958">bar height on a square-root scale</text>

      {/* ---- the headline number ---- */}
      <text x={890} y={578} className="disp" fontSize={64} fontWeight={600} letterSpacing="-2.5" fill="#f6f1e2">{(PASS.p * 100).toFixed(1)}<tspan fontSize={26} fill="#a8a089">%</tspan></text>
      <text x={892} y={604} className="mono" fontSize={11.5} letterSpacing="1.2" fill="#a8a089">OF SCENARIOS PASS THE RULE</text>
      <text x={892} y={626} className="mono" fontSize={11.5} fill="#c4bca7">95% band  {(PASS.lo * 100).toFixed(0)} to {(PASS.hi * 100).toFixed(0)}%</text>
      <text x={892} y={646} className="mono" fontSize={11.5} fill="#ff8a63">{((1 - PASS.p) * 100).toFixed(1)}% fail</text>
    </svg>
  )
}
