import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

// ILLUSTRATIVE VALUES: the pipeline does not produce these outputs yet. They show the shape of what each audience gets.
const GOLD = '#d9b24c', RED = '#ff6a55', GREEN = '#7bc47f', INK = '#f6f1e2', MUTE = '#8d8670', LINE = 'rgba(255,255,255,0.14)'
const MONO = { fontFamily: '"IBM Plex Mono", monospace' } as const

function rng(seed: number) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 } }

// failure pockets in a (dip depth, temperature) plane, both 0..1
const inPocket = (x: number, y: number) =>
  (x - 0.78) ** 2 + (y - 0.2) ** 2 < 0.018 || (x - 0.42) ** 2 + (y - 0.82) ** 2 < 0.012 || (Math.abs(x - 0.6 - (y - 0.5) * 0.4) < 0.025 && y > 0.3 && y < 0.7)

const SCATTER = (() => {
  const R = rng(5)
  return Array.from({ length: 260 }, () => { const x = R(), y = R(); return { x, y, bad: inPocket(x, y) } })
})()
const LAB = [[0.2, 0.3], [0.35, 0.65], [0.5, 0.4], [0.62, 0.78], [0.3, 0.12]]

function Card({ n, who, title, line, children }: { n: string; who: string; title: string; line: string; children: ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-60px' }} transition={{ duration: 0.5 }}
      className="flex flex-col border border-white/12 bg-[#0c0c10] p-6">
      <div className="flex items-baseline justify-between">
        <span className="mono text-[12px] text-[#d9b24c]">{n}</span>
        <span className="mono text-[10.5px] tracking-[0.14em] text-[#8d8670] uppercase">{who}</span>
      </div>
      <div className="mt-5 flex-1">{children}</div>
      <h3 className="display mt-6 text-[22px] leading-[1.15] font-semibold tracking-[-0.02em] text-[#f6f1e2]">{title}</h3>
      <p className="mt-2 text-[15px] leading-[1.55] text-[#c4bca7]">{line}</p>
    </motion.div>
  )
}

function Panel({ x, title, sub, children }: { x: number; title: string; sub: string; children: ReactNode }) {
  return (
    <g transform={`translate(${x},0)`}>
      <text x={0} y={12} fontSize={11} fill={INK} style={MONO}>{title}</text>
      <text x={0} y={27} fontSize={10} fill={MUTE} style={MONO}>{sub}</text>
      <rect x={0} y={38} width={190} height={150} fill="none" stroke={LINE} />
      {children}
    </g>
  )
}

// 1. developers find failures
function FindFailures() {
  const px = (v: number) => 8 + v * 174, py = (v: number) => 42 + (1 - v) * 142
  return (
    <svg viewBox="0 0 400 214" className="w-full" role="img" aria-label="A few lab tests all pass, while a dense search finds three failure pockets between them.">
      <Panel x={0} title="Lab tests" sub="5 fixed scenarios · all pass">
        {LAB.map(([x, y], i) => <rect key={i} x={px(x) - 5} y={py(y) - 5} width={10} height={10} fill={GREEN} />)}
      </Panel>
      <Panel x={210} title="Our search" sub="thousands of scenarios">
        {SCATTER.map((d, i) => (
          <motion.circle key={i} cx={px(d.x)} cy={py(d.y)} r={d.bad ? 2.6 : 1.7} fill={d.bad ? RED : GREEN} opacity={d.bad ? 1 : 0.45}
            initial={{ opacity: 0 }} whileInView={{ opacity: d.bad ? 1 : 0.45 }} viewport={{ once: true }} transition={{ delay: i * 0.004 }} />
        ))}
      </Panel>
      <text x={0} y={206} fontSize={10} fill={MUTE} style={MONO}>↑ temperature   → dip depth</text>
    </svg>
  )
}

// 2. developers prove the product under natural variance
function ProveIt() {
  const xs = Array.from({ length: 61 }, (_, i) => i / 60)
  const f = (t: number) => Math.exp(-((t - 0.78) ** 2) / 0.02) + 0.12 * Math.exp(-((t - 0.35) ** 2) / 0.03)
  const X = (t: number) => 10 + t * 380, Y = (v: number) => 150 - v * 100
  const area = (from: number, to: number) => {
    const pts = xs.filter((t) => t >= from && t <= to)
    return `M${X(pts[0])},150 ` + pts.map((t) => `L${X(t)},${Y(f(t))}`).join(' ') + ` L${X(pts[pts.length - 1])},150 Z`
  }
  const line = 'M' + xs.map((t) => `${X(t)},${Y(f(t))}`).join(' L')
  return (
    <svg viewBox="0 0 400 214" className="w-full" role="img" aria-label="A distribution of outcomes over varied conditions with the passing share shaded and an uncertainty band.">
      <path d={area(0, 0.9)} fill={RED} opacity={0.35} />
      <motion.path d={area(0.9, 1)} fill={GREEN} opacity={0.5} initial={{ opacity: 0 }} whileInView={{ opacity: 0.5 }} viewport={{ once: true }} transition={{ delay: 0.3 }} />
      <path d={line} fill="none" stroke={INK} strokeWidth={1.4} />
      <line x1={X(0.9)} x2={X(0.9)} y1={36} y2={150} stroke={GOLD} strokeDasharray="4 3" />
      <text x={X(0.9) - 6} y={32} fontSize={10} fill={GOLD} textAnchor="end" style={MONO}>grid rule: 90% power back</text>
      <line x1={10} x2={390} y1={150} y2={150} stroke={LINE} />
      <text x={10} y={166} fontSize={10} fill={MUTE} style={MONO}>0%</text>
      <text x={390} y={166} fontSize={10} fill={MUTE} textAnchor="end" style={MONO}>100% of prior power</text>
      <text x={10} y={198} fontSize={22} fill={INK} style={{ ...MONO, fontWeight: 600 }}>87%</text>
      <text x={64} y={198} fontSize={11} fill={MUTE} style={MONO}>pass · range 81–92%</text>
      <g transform="translate(250,186)"><line x1={0} x2={140} y1={4} y2={4} stroke={LINE} />
        <rect x={140 * 0.81 / 1} y={0} width={140 * 0.11} height={8} fill={GOLD} /><line x1={140 * 0.87} x2={140 * 0.87} y1={-3} y2={11} stroke={INK} strokeWidth={2} /></g>
    </svg>
  )
}

// 3. the owner quantifies value for their site
function OwnerCost() {
  const D = [
    { name: 'Design A', pass: 0.87, cap: 40, color: GOLD },
    { name: 'Design B', pass: 0.96, cap: 78, color: GREEN },
  ]
  const loss = (p: number) => (1 - p) * 520
  const sx = 2.0
  return (
    <svg viewBox="0 0 400 214" className="w-full" role="img" aria-label="Two designs compared on price plus expected outage loss for one site.">
      <text x={0} y={12} fontSize={11} fill={INK} style={MONO}>Your site, 10-year cost</text>
      <text x={0} y={27} fontSize={10} fill={MUTE} style={MONO}>price + expected outage loss</text>
      {D.map((d, i) => {
        const y = 52 + i * 62, l = loss(d.pass)
        return (
          <g key={d.name}>
            <text x={0} y={y + 14} fontSize={11} fill={INK} style={MONO}>{d.name}</text>
            <text x={0} y={y + 29} fontSize={10} fill={MUTE} style={MONO}>{Math.round(d.pass * 100)}% pass</text>
            <rect x={86} y={y} width={d.cap * sx} height={26} fill={d.color} opacity={0.85} />
            <motion.rect x={86 + d.cap * sx} y={y} height={26} fill={RED} opacity={0.8} initial={{ width: 0 }} whileInView={{ width: l * sx * 0.5 }} viewport={{ once: true }} transition={{ duration: 0.8, delay: 0.2 + i * 0.1 }} />
            <text x={86 + d.cap * sx + l * sx * 0.5 + 8} y={y + 17} fontSize={10} fill={MUTE} style={MONO}>{Math.round(d.cap + l * 0.5)}</text>
          </g>
        )
      })}
      <g transform="translate(86,180)"><rect width={10} height={8} y={1} fill={GOLD} /><text x={15} y={9} fontSize={10} fill={MUTE} style={MONO}>price</text>
        <rect x={70} width={10} height={8} y={1} fill={RED} /><text x={85} y={9} fontSize={10} fill={MUTE} style={MONO}>expected loss = P(fail) × events × cost</text></g>
      <text x={0} y={208} fontSize={10} fill={MUTE} style={MONO}>Units illustrative</text>
    </svg>
  )
}

// 4. financiers compare products on one scale
function Financiers() {
  const rows = [
    { name: 'Product X', p: 0.87, lo: 0.81, hi: 0.92, modes: 3 },
    { name: 'Product Y', p: 0.74, lo: 0.52, hi: 0.9, modes: 5 },
    { name: 'Product Z', p: 0.95, lo: 0.9, hi: 0.98, modes: 1 },
  ]
  const X = (v: number) => 92 + v * 230
  return (
    <svg viewBox="0 0 400 214" className="w-full" role="img" aria-label="Three products compared by pass probability with uncertainty ranges on a common scale.">
      <text x={0} y={12} fontSize={11} fill={INK} style={MONO}>Same test, same scale</text>
      <text x={0} y={27} fontSize={10} fill={MUTE} style={MONO}>pass probability and its range</text>
      {[0.5, 0.75, 1].map((t) => <g key={t}><line x1={X(t)} x2={X(t)} y1={40} y2={160} stroke={LINE} /><text x={X(t)} y={174} fontSize={10} fill={MUTE} textAnchor="middle" style={MONO}>{t * 100}%</text></g>)}
      {rows.map((r, i) => {
        const y = 62 + i * 38
        return (
          <g key={r.name}>
            <text x={0} y={y + 4} fontSize={11} fill={INK} style={MONO}>{r.name}</text>
            <motion.rect x={X(r.lo)} y={y - 7} height={14} fill={GOLD} opacity={0.35} initial={{ width: 0 }} whileInView={{ width: X(r.hi) - X(r.lo) }} viewport={{ once: true }} transition={{ duration: 0.6, delay: i * 0.12 }} />
            <circle cx={X(r.p)} cy={y} r={5} fill={INK} />
            <text x={X(r.hi) + 8} y={y + 4} fontSize={10} fill={MUTE} style={MONO}>{r.modes} modes</text>
          </g>
        )
      })}
      <text x={0} y={204} fontSize={10} fill={MUTE} style={MONO}>A wide band means unproven, not bad.</text>
    </svg>
  )
}

export default function UseCases() {
  return (
    <div>
      <p className="mono text-[12px] font-medium tracking-[0.14em] text-[#d9b24c] uppercase">Who uses it</p>
      <div className="mt-6 grid gap-px overflow-hidden border border-white/12 bg-white/12 md:grid-cols-3">
        {[
          ['Developers', 'Companies that build ride-through technology, such as backup power, converters and power supplies.'],
          ['Data center owners', 'Operators who choose, buy and connect that technology to the grid.'],
          ['Financiers', 'Lenders, investors and insurers who back the companies building it.'],
        ].map(([t, d]) => (
          <div key={t} className="bg-[#07070a] px-5 py-5">
            <p className="display text-[19px] font-semibold tracking-[-0.015em] text-[#f6f1e2]">{t}</p>
            <p className="mt-1.5 text-[14.5px] leading-[1.5] text-[#c4bca7]">{d}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <Card n="01" who="Developers" title="Find failures that fixed tests miss." line="A handful of lab tests can all pass while a search over thousands of realistic conditions finds the pockets where the design breaks.">
          <FindFailures />
        </Card>
        <Card n="02" who="Developers" title="Prove it holds up across natural variance." line="Temperature, battery age and load all vary. The result is a pass probability with an uncertainty range, not one lucky run.">
          <ProveIt />
        </Card>
        <Card n="03" who="Data center owners" title="Put a number on how it works for your site." line="Enter your site and compare designs on price plus the expected cost of an outage, so the cheaper option is not chosen blind.">
          <OwnerCost />
        </Card>
        <Card n="04" who="Financiers" title="Understand how the product really behaves." line="Every product gets the same test and the same scale, with its range and its failure modes shown, so risk can be compared across companies.">
          <Financiers />
        </Card>
      </div>
      <p className="mono mt-4 text-[11px] tracking-[0.06em] text-[#8d8670]">Illustrative values. The pipeline does not produce these outputs yet.</p>
    </div>
  )
}
