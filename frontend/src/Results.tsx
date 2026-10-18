import type { ReactNode } from 'react'

// ILLUSTRATIVE VALUES: the pipeline does not produce these outputs yet. Replace with real model output.
const PASS = { p: 0.918, lo: 0.906, hi: 0.929 }

const MODES = [
  {
    id: 'A', name: 'Power-supply trip', color: '#ff8a3d', p: 0.039, lo: 0.032, hi: 0.047,
    what: 'Server power supplies drop out on dips below 0.43 pu, at any temperature.',
    fix: 'Lower the power-supply trip point from 0.60 to 0.50 pu.', fixNote: 'Firmware only · removes 94%',
    setting: 'PSU trip delay = 10 ms', settingNote: 'Factory default on 38% of racks.',
  },
  {
    id: 'B', name: 'Cold battery stall', color: '#ff4a3a', p: 0.027, lo: 0.021, hi: 0.034,
    what: 'Below −3 °C a cold battery cannot deliver full current into a 0.45–0.60 pu dip.',
    fix: 'Raise the battery heater setpoint from 5 °C to 12 °C.', fixNote: 'Setting change · removes 88%',
    setting: 'Minimum charge = 20%', settingNote: 'At −10 °C this leaves 9 s of support.',
  },
  {
    id: 'C', name: 'Heat-derated recovery', color: '#ffd873', p: 0.016, lo: 0.011, hi: 0.022,
    what: 'Above 33 °C the inverter throttles itself and the site misses the 2 s deadline.',
    fix: 'Speed up the power ramp from 0.8 to 1.4 pu per second.', fixNote: 'Control tuning · removes 97%',
    setting: 'Derate onset = 35 °C', settingNote: 'Exceeded about 140 hours a year in Abilene.',
  },
] as const

const EVENTS = [
  { pu: '0.535', tag: 'Deepest · winter morning', note: 'Legacy sheds 186 MW', legacy: 38, product: 93 },
  { pu: '0.670', tag: 'Mid · summer peak', note: 'Legacy sheds 83 MW', legacy: 71, product: 96 },
  { pu: '0.844', tag: 'Shallow · shoulder season', note: 'Both hold', legacy: 92, product: 99 },
]

const PASS_GREEN = '#5dbb7a'
const GOLD = '#d9b24c'
const label = 'mono text-[12px] font-medium tracking-[0.14em] uppercase'
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`

// deterministic noise so the map is stable between renders
function rng(seed: number) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 } }
function gauss(R: () => number) { return Math.sqrt(-2 * Math.log(R() || 1e-9)) * Math.cos(2 * Math.PI * R()) }

// an even grid of conditions (not weighted by likelihood), each classified by the mode that breaks it
const MAP_POINTS = (() => {
  const R = rng(7)
  const pts: { t: number; v: number; mode: 'pass' | 'A' | 'B' | 'C' }[] = []
  for (let i = 0; i < 26; i++) for (let j = 0; j < 17; j++) {
    const t = -20 + (65 * (i + R())) / 26
    const v = 0.3 + (0.65 * (j + R())) / 17
    const vn = v + 0.025 * gauss(R)
    const mode = vn < 0.43 ? 'A' : t < -3 + 3 * gauss(R) && vn < 0.6 ? 'B' : t > 33 + 2.5 * gauss(R) && vn < 0.73 ? 'C' : 'pass'
    pts.push({ t, v, mode })
  }
  return pts
})()

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

function FailureMap() {
  const W = 1100, H = 500, L = 64, R = 24, T = 20, B = 52
  const x = (t: number) => L + ((t + 20) / 65) * (W - L - R)
  const y = (v: number) => T + ((0.95 - v) / 0.65) * (H - T - B)
  const color = { A: MODES[0].color, B: MODES[1].color, C: MODES[2].color }
  return (
    <div className="mt-12">
      <div className="flex flex-wrap gap-x-8 gap-y-2 md:pl-[68px]">
        {[{ name: 'Pass', c: PASS_GREEN }, ...MODES.map((m) => ({ name: `${m.id} · ${m.name}`, c: m.color }))].map((k) => (
          <span key={k.name} className="mono flex items-center gap-2 text-[11.5px] tracking-[0.1em] text-[#c4bca7] uppercase">
            <span className="h-2 w-2 rounded-full" style={{ background: k.c }} />{k.name}
          </span>
        ))}
      </div>
      <div className="mono mt-7 flex justify-between text-[11.5px] tracking-[0.12em] text-[#a8a089] uppercase">
        <span>Lowest voltage during the dip, pu ↓ deeper</span>
        <span className="hidden sm:inline">{MAP_POINTS.length} scenarios shown of 1,000,000</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label="Scatter of dip depth against outdoor temperature. Green dots pass; colored dots fail by mode.">
        {[0.4, 0.5, 0.6, 0.7, 0.8, 0.9].map((v) => <text key={v} x={L - 12} y={y(v) + 4} textAnchor="end" className="mono" fontSize={11} fill="#8d8670">{v.toFixed(1)}</text>)}
        {[-20, -10, 0, 10, 20, 30, 40].map((t) => <text key={t} x={x(t)} y={H - B + 22} textAnchor="middle" className="mono" fontSize={11} fill="#8d8670">{t}°C</text>)}
        <text x={W - R} y={H - 8} textAnchor="end" className="mono" fontSize={11} letterSpacing="1.4" fill="#a8a089">OUTDOOR TEMPERATURE →</text>
        <line x1={L} y1={H - B} x2={W - R} y2={H - B} stroke="#5a5444" />
        <line x1={L} y1={T} x2={L} y2={H - B} stroke="#5a5444" />
        {EVENTS.map((e) => <line key={e.pu} x1={L} y1={y(+e.pu)} x2={W - R} y2={y(+e.pu)} stroke="#f6f1e2" strokeOpacity={0.35} strokeDasharray="3 4" />)}
        {MAP_POINTS.filter((p) => p.mode === 'pass').map((p, i) => <circle key={`p${i}`} cx={x(p.t)} cy={y(p.v)} r={3} fill={PASS_GREEN} />)}
        {MAP_POINTS.filter((p) => p.mode !== 'pass').map((p, i) => (
          <circle key={`f${i}`} cx={x(p.t)} cy={y(p.v)} r={4.5} fill={color[p.mode as 'A' | 'B' | 'C']} stroke="#07070a" />
        ))}
        {EVENTS.map((e) => (
          <g key={`l${e.pu}`}>
            <rect x={700} y={y(+e.pu) - 12} width={72} height={18} fill="#07070a" />
            <text x={736} y={y(+e.pu) + 1} textAnchor="middle" className="mono" fontSize={11} fill="#f6f1e2">TX {e.pu}</text>
          </g>
        ))}
      </svg>
      <p className="mono mt-3 text-[11px] tracking-[0.06em] text-[#8d8670]">
        An even grid of conditions, not weighted by how likely each is. Dashed lines mark the three Texas events in section 04. Illustrative values.
      </p>
    </div>
  )
}

// one failure: 0.62 pu dip for 120 ms on a 41 °C afternoon; the battery derates and recovery misses the deadline
const FAULT = { start: 1.0, end: 1.12 }
const DEADLINE = FAULT.end + 2
const volt = (t: number) =>
  t < FAULT.start ? 1 : t < FAULT.end ? 0.62
    : 1 - 0.38 * Math.exp(-(t - FAULT.end) / 0.05) + 0.03 * Math.exp(-(t - FAULT.end) / 0.25) * Math.sin((t - FAULT.end) * 25)
const facility = (t: number) => t < 1 ? 100 : t < 1.06 ? 100 - (66 * (t - 1)) / 0.06 : 34 + 64 * (1 - Math.exp(-(t - 1.06) / 1.55))
const battery = (t: number) =>
  t < 1 ? 0 : t < 1.03 ? (186 * (t - 1)) / 0.03 : t < 1.35 ? 186 + (14 * (t - 1.03)) / 0.32 : t < 2.2 ? 200 - (72 * (t - 1.35)) / 0.85 : 128 * Math.exp(-(t - 2.2) / 1.1)
const REACHED_90 = 1.06 - 1.55 * Math.log(1 - (90 - 34) / 64)

function Replay() {
  const W = 1100, L = 64, R = 24, PH = 112, STEP = 168, TOP = 56
  const X = (t: number) => L + (t / 6) * (W - L - R)
  const bottom = TOP + 2 * STEP + PH
  const ts = Array.from({ length: 601 }, (_, i) => i / 100)
  const panels = [
    { name: 'VOLTAGE AT INTERCONNECTION, pu', lo: 0.45, hi: 1.08, ticks: [[0.5, '0.50'], [0.75, '0.75'], [1, '1.00']], f: volt, c: '#f6f1e2' },
    { name: 'FACILITY POWER FROM GRID, % OF PRE-FAULT', lo: 0, hi: 108, ticks: [[0, '0'], [50, '50'], [100, '100']], f: facility, c: GOLD },
    { name: 'BATTERY OUTPUT, MW', lo: 0, hi: 225, ticks: [[0, '0'], [100, '100'], [200, '200']], f: battery, c: '#78d7ff' },
  ] as const
  const scenario = [
    ['Mode', 'C · Heat-derated recovery'], ['Dip', '0.62 pu for 120 ms'], ['Outdoor', '41 °C'], ['Battery charge', '64%'], ['AI load', '286 MW, training burst'],
  ]
  return (
    <div className="mt-10">
      <div className="flex flex-wrap gap-x-10 gap-y-4 md:pl-[68px]">
        {scenario.map(([k, v], i) => (
          <div key={k}>
            <p className="mono text-[11px] tracking-[0.14em] text-[#8d8670] uppercase">{k}</p>
            <p className="mono mt-1 text-[13px]" style={{ color: i === 0 ? MODES[2].color : '#f6f1e2' }}>{v}</p>
          </div>
        ))}
      </div>
      <svg viewBox={`0 0 ${W} ${bottom + 30}`} className="mt-10 w-full" role="img" aria-label="Voltage, facility power and battery output over six seconds, with the 90% line and the 2 second recovery deadline.">
        <rect x={X(FAULT.start)} y={18} width={X(FAULT.end) - X(FAULT.start)} height={bottom - 18} fill="#ff4a3a" fillOpacity={0.12} />
        <text x={X(FAULT.start) - 6} y={12} textAnchor="end" className="mono" fontSize={10.5} fill="#ff8a63">FAULT 1.00–1.12 s</text>
        <line x1={X(DEADLINE)} y1={18} x2={X(DEADLINE)} y2={bottom} stroke="#ff6a55" strokeDasharray="3 4" />
        <text x={X(DEADLINE) + 8} y={12} className="mono" fontSize={10.5} fill="#ff6a55">2 s RECOVERY DEADLINE · {DEADLINE.toFixed(2)} s</text>
        {panels.map((p, k) => {
          const y0 = TOP + k * STEP
          const Y = (v: number) => y0 + ((p.hi - v) / (p.hi - p.lo)) * PH
          return (
            <g key={p.name}>
              <text x={L} y={y0 - 16} className="mono" fontSize={11} letterSpacing="1.5" fill="#a8a089">{p.name}</text>
              {p.ticks.map(([v, s]) => <text key={s} x={L - 12} y={Y(v) + 4} textAnchor="end" className="mono" fontSize={11} fill="#8d8670">{s}</text>)}
              <line x1={L} y1={y0 + PH} x2={W - R} y2={y0 + PH} stroke="#5a5444" />
              {k === 1 && (
                <>
                  <line x1={L} y1={Y(90)} x2={W - R} y2={Y(90)} stroke="#f6f1e2" strokeDasharray="3 4" />
                  <text x={W - R} y={Y(90) + 18} textAnchor="end" className="mono" fontSize={11} fill="#f6f1e2">ERCOT: 90%</text>
                </>
              )}
              <polyline points={ts.map((t) => `${X(t).toFixed(1)},${Y(p.f(t)).toFixed(1)}`).join(' ')} fill="none" stroke={p.c} strokeWidth={2.2} strokeLinejoin="round" />
              {k === 0 && <text x={X(FAULT.end) + 8} y={Y(0.62) + 4} className="mono" fontSize={11} fill="#c4bca7">0.62 pu</text>}
              {k === 1 && (
                <>
                  <text x={X(FAULT.end) + 8} y={Y(34) + 14} className="mono" fontSize={11} fill="#c4bca7">falls to 34%</text>
                  <circle cx={X(DEADLINE)} cy={Y(facility(DEADLINE))} r={5} fill="#ff4a3a" stroke="#07070a" strokeWidth={2} />
                  <text x={X(DEADLINE) + 10} y={Y(facility(DEADLINE)) + 22} className="mono" fontSize={11.5} fill="#ff8a63">{Math.round(facility(DEADLINE))}% at the deadline · FAIL</text>
                  <circle cx={X(REACHED_90)} cy={Y(90)} r={4} fill={GOLD} stroke="#07070a" strokeWidth={2} />
                  <text x={X(REACHED_90) + 8} y={Y(90) - 10} className="mono" fontSize={11.5} fill="#c4bca7">
                    90% at {REACHED_90.toFixed(2)} s, {(REACHED_90 - DEADLINE).toFixed(2)} s late
                  </text>
                </>
              )}
              {k === 2 && <text x={X(1.35) + 10} y={Y(200) - 4} className="mono" fontSize={11} fill="#c4bca7">200 MW, then thermal derate at 41 °C</text>}
            </g>
          )
        })}
        {[0, 1, 2, 3, 4, 5, 6].map((t) => (
          <text key={t} x={X(t)} y={bottom + 20} textAnchor={t === 0 ? 'start' : t === 6 ? 'end' : 'middle'} className="mono" fontSize={11} fill="#8d8670">{t} s</text>
        ))}
      </svg>
    </div>
  )
}

function ReportCard() {
  const cols = 'md:grid-cols-[300px_140px_1fr_210px]'
  return (
    <div className="mt-12 md:pl-[68px]">
      <div className={`mono hidden gap-8 border-b border-[#4a4332] pb-3.5 text-[11px] tracking-[0.14em] text-[#8d8670] uppercase md:grid ${cols}`}>
        <span>Failure mode</span><span>Likelihood</span><span>Smallest fix</span><span>Most dangerous setting</span>
      </div>
      {MODES.map((m) => (
        <div key={m.id} className={`grid gap-x-8 gap-y-4 border-b border-[#2b2720] py-7 ${cols}`}>
          <div>
            <h3 className="display flex items-center gap-2.5 text-[22px] leading-[1.2] font-semibold tracking-[-0.02em] text-[#f6f1e2]">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: m.color }} />{m.id} · {m.name}
            </h3>
            <p className="mt-2 pl-5 text-[15px] leading-[1.55] text-[#c4bca7]">{m.what}</p>
          </div>
          <div>
            <p className="display text-[36px] leading-none font-semibold tracking-[-0.035em] text-[#f6f1e2]">{pct(m.p)}</p>
            <p className="mono mt-1.5 text-[11.5px] text-[#a8a089]">band {pct(m.lo)} to {pct(m.hi)}</p>
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
      ))}
    </div>
  )
}

function Comparison() {
  const X0 = 330, X1 = 1000, G = 128, TOP = 40
  const X = (v: number) => X0 + (v / 100) * (X1 - X0)
  return (
    <div className="mt-14">
      <svg viewBox={`0 0 1100 ${TOP + 3 * G - 4}`} className="w-full" role="img" aria-label="Power back at 2 seconds for legacy equipment and the product on three Texas events.">
        <text x={X0} y={16} className="mono" fontSize={11} letterSpacing="1.4" fill="#a8a089">POWER BACK AT 2 SECONDS, % OF PRE-FAULT</text>
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
      <p className="mono mt-3 text-[11px] tracking-[0.06em] text-[#8d8670]">Illustrative values. Event voltages are residual voltage at the point of interconnection.</p>
    </div>
  )
}

export default function Results() {
  return (
    <div className="mx-auto max-w-[1180px] px-10 pt-20 pb-40">
      <style>{`.disp { font-family: "Space Grotesk", sans-serif; }`}</style>
      <div className="flex flex-col gap-10 md:flex-row md:items-end md:justify-between">
        <div className="max-w-[720px]">
          <p className={`${label} text-[#d9b24c]`}>Results · Reference campus, 300 MW · 1,000,000 scenarios</p>
          <h1 className="display mt-4 text-[56px] leading-[1.02] font-semibold tracking-[-0.04em] text-[#f6f1e2]">
            This design holds in most dips. It fails three distinct ways.
          </h1>
          <p className="mt-7 max-w-[620px] text-[19px] leading-[1.55] text-[#d3ccb8]">
            Where it breaks, how a failure plays out second by second, the smallest fix for each, and how it compares with legacy equipment on three real Texas events.
          </p>
        </div>
        <div className="shrink-0 md:text-right">
          <p className="mono text-[11px] tracking-[0.14em] text-[#a8a089] uppercase">Pass probability</p>
          <p className="display text-[96px] leading-[0.95] font-semibold tracking-[-0.045em] text-[#f6f1e2]">
            {(PASS.p * 100).toFixed(1)}<span className="ml-1 text-[34px] font-medium tracking-normal text-[#a8a089]">%</span>
          </p>
          <p className="mono mt-2 text-[11.5px] text-[#c4bca7]">95% band  {pct(PASS.lo)} to {pct(PASS.hi)}</p>
          <p className="mono mt-1 text-[11.5px] text-[#ff8a63]">{pct(1 - PASS.p)} fail</p>
        </div>
      </div>

      <Section n="01" kicker="Failure map" title="Deep dips fail everywhere. Cold and heat widen the edge."
        lede="Each dot is one scenario: how far the voltage fell, and the outdoor temperature at the time. Green passed the ERCOT rule. The other colors mark how it failed.">
        <FailureMap />
      </Section>

      <Section n="02" kicker="One failure, second by second" title={`A hot afternoon and a 0.62 pu dip. Power comes back ${(REACHED_90 - DEADLINE).toFixed(2)} s too late.`}
        lede="The battery catches the dip, then throttles itself in the heat. The site keeps leaning on the grid, and recovery stalls below the line until after the deadline.">
        <Replay />
      </Section>

      <Section n="03" kicker="Report card" title="Three failure modes, three small fixes."
        lede="Ranked by how often each one happens. Each fix is the smallest change that removed the mode in re-testing.">
        <ReportCard />
      </Section>

      <Section n="04" kicker="Legacy vs product · Texas events" title="Legacy equipment fails two of three real dips. The product passes all three."
        lede="Three recorded ERCOT voltage events replayed against the same 300 MW reference campus, once with legacy double-conversion UPS and once with the product.">
        <Comparison />
      </Section>
    </div>
  )
}
