/**
 * Results of the full pipeline: Bayesian-network scenario sampler -> neural surrogate -> outcome distribution and ranked
 * failure drivers. Reads the report written by `python -m ridethrough.pipeline.run --design <d> --web` from
 * /data/pipeline_<design>.json, so swapping the surrogate (surrogate/models/ACTIVE) and re-running that command is all it
 * takes to refresh this section; the model that produced the numbers is named on the page.
 */
import { useEffect, useState } from 'react'

type Design = 'grid_friendly' | 'legacy_ups'
const DESIGNS: { id: Design; name: string }[] = [
  { id: 'grid_friendly', name: 'Product (grid-friendly)' },
  { id: 'legacy_ups', name: 'Legacy UPS' },
]

type Ranked = { rank: number; block: string; label: string; share: number; importance: number; rank_90ci: [number, number]; rank_resolved: boolean }
type Level = { level: string; share_of_events: number; [k: string]: number | string }
type Report = {
  design: Design
  n_events: number
  headline_output: string
  saturated: boolean
  performance: {
    fail_probability: { mean: number; mc_95ci: [number, number]; by_ensemble_member: number[] }
    failure_mode_share: Record<string, number>
    continuous: Record<string, { quantiles: Record<string, number> }>
    share_inputs_outside_training: number
  }
  rankings: Record<'A' | 'B', { by_output: Record<string, Ranked[]> }>
  group_split: { output: string; A_share: number }[]
  lifts: Record<string, { levels: Level[] }>
  surrogate?: { name?: string; format?: string; simulator_commit?: string | null; trained_rows?: number }
  scope?: { dip_depth_pu: [number, number]; share_of_sags: number; note: string }
  caveats: string[]
}

export type ModeStyle = Record<string, { name: string; color: string }>

const label = 'mono text-[12px] font-medium tracking-[0.14em] uppercase'
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`
const MEASURES: Record<string, { name: string; fmt: (v: number) => string }> = {
  min_power: { name: 'Lowest grid power', fmt: (v) => `${v.toFixed(2)} pu` },
  peak_current_pu: { name: 'Peak current', fmt: (v) => `${v.toFixed(2)} pu` },
  floor_violation_s: { name: 'Time below power floor', fmt: (v) => `${v.toFixed(2)} s` },
  recovery_margin_s: { name: 'Recovery margin', fmt: (v) => `${v.toFixed(2)} s` },
}
const OUTPUT_NAME: Record<string, string> = { p_fail: 'probability of failing', ...Object.fromEntries(Object.entries(MEASURES).map(([k, m]) => [k, m.name.toLowerCase()])) }

/** Worst level of a driver on an output, as the markdown report computes it ('' when the levels barely differ). */
function worstLevel(r: Report, block: string, output: string): string {
  const levels = r.lifts[block]?.levels ?? []
  const key = output === 'p_fail' ? 'p_fail' : `mean_${output}`
  if (!levels.length || !(key in levels[0])) return ''
  const vals = levels.map((l) => Number(l[key]))
  const mean = levels.reduce((s, l) => s + l.share_of_events * Number(l[key]), 0)
  if (mean === 0 || (Math.max(...vals) - Math.min(...vals)) / Math.abs(mean) < 0.1) return 'no clear difference'
  return String(levels[vals.indexOf(Math.max(...vals))].level)
}

function Drivers({ r, group, title }: { r: Report; group: 'A' | 'B'; title: string }) {
  const rows = (r.rankings[group]?.by_output[r.headline_output] ?? []).slice(0, 6)
  const top = Math.max(...rows.map((x) => x.share), 1e-9)
  return (
    <div>
      <p className={`${label} text-[#a8a089]`}>{title}</p>
      <div className="mt-4 space-y-3.5">
        {rows.map((x) => (
          <div key={x.block}>
            <div className="flex items-baseline justify-between gap-4">
              <span className="text-[15px] text-[#f6f1e2]">{x.rank}. {x.label}</span>
              <span className="mono text-[12px] text-[#c4bca7]">{pct(x.share, 0)}</span>
            </div>
            <div className="mt-1.5 h-[6px] bg-[#1a1813]"><div className="h-full bg-[#d9b24c]" style={{ width: `${(x.share / top) * 100}%` }} /></div>
            <p className="mono mt-1 text-[11px] text-[#8d8670]">
              worst: {worstLevel(r, x.block, r.headline_output) || '—'} · rank {x.rank_90ci[0]}–{x.rank_90ci[1]}{x.rank_resolved ? '' : ' (unresolved)'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Pipeline({ modes }: { modes: ModeStyle }) {
  const [design, setDesign] = useState<Design>('grid_friendly')
  const [reports, setReports] = useState<Partial<Record<Design, Report | 'missing'>>>({})

  useEffect(() => {
    if (reports[design]) return
    fetch(`/data/pipeline_${design}.json`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((r: Report) => setReports((s) => ({ ...s, [design]: r })))
      .catch((err) => {
        console.warn(`pipeline report for ${design} failed to load:`, err)
        setReports((s) => ({ ...s, [design]: 'missing' }))
      })
  }, [design, reports])

  const r = reports[design]
  return (
    <div className="mt-12 md:pl-[68px]">
      <div className="flex flex-wrap gap-2">
        {DESIGNS.map((d) => (
          <button key={d.id} onClick={() => setDesign(d.id)}
            className={`mono rounded-full border px-4 py-1.5 text-[12px] tracking-[0.08em] uppercase transition-colors ${design === d.id ? 'border-[#d9b24c] bg-[#d9b24c] text-[#14120e]' : 'border-[#4a4332] text-[#c4bca7] hover:border-[#8d8670]'}`}>
            {d.name}
          </button>
        ))}
      </div>

      {!r && <p className="mono mt-10 text-[13px] text-[#8d8670]">Loading the pipeline report…</p>}
      {r === 'missing' && (
        <p className="mono mt-10 text-[13px] text-[#ff8a63]">
          No pipeline report for this design yet. Run <span className="text-[#f6f1e2]">python -m ridethrough.pipeline.run --design {design} --web</span> and reload.
        </p>
      )}
      {r && r !== 'missing' && <Body r={r} modes={modes} />}
    </div>
  )
}

function Body({ r, modes }: { r: Report; modes: ModeStyle }) {
  const p = r.performance
  const fp = p.fail_probability
  const members = fp.by_ensemble_member
  const shares = Object.entries(p.failure_mode_share).filter(([, v]) => v >= 0.0005).sort((a, b) => b[1] - a[1])
  const split = r.group_split.find((s) => s.output === r.headline_output)
  const sur = r.surrogate
  return (
    <>
      {r.scope && (
        <div className="mt-8 border-l-2 border-[#d9b24c] bg-[#1a1813] px-5 py-4">
          <p className={`${label} text-[#d9b24c]`}>Scope</p>
          <p className="mt-2 text-[15px] leading-[1.55] text-[#d3ccb8]">
            Covers dips that keep {r.scope.dip_depth_pu[0].toFixed(2)}–{r.scope.dip_depth_pu[1].toFixed(2)} pu of normal voltage, about {pct(r.scope.share_of_sags, 0)} of real sags.
            Every figure here assumes such a dip. Deeper sags are not assessed yet: they are not counted as passes or as failures.
          </p>
        </div>
      )}

      <div className="mt-10 grid gap-10 md:grid-cols-[280px_1fr]">
        <div>
          <p className={`${label} text-[#a8a089]`}>Chance an event fails</p>
          <p className="display mt-2 text-[72px] leading-[0.95] font-semibold tracking-[-0.045em] text-[#f6f1e2]">
            {(fp.mean * 100).toFixed(1)}<span className="ml-1 text-[28px] font-medium tracking-normal text-[#a8a089]">%</span>
          </p>
          <p className="mono mt-2 text-[11.5px] text-[#c4bca7]">95% band {pct(fp.mc_95ci[0])} to {pct(fp.mc_95ci[1])}</p>
          <p className="mono mt-1 text-[11.5px] text-[#a8a089]">ensemble members {pct(Math.min(...members))} to {pct(Math.max(...members))}</p>
          <p className="mono mt-1 text-[11.5px] text-[#a8a089]">{r.n_events.toLocaleString()} sampled grid events</p>
          {p.share_inputs_outside_training > 0.05 && (
            <p className="mono mt-3 text-[11.5px] text-[#ff8a63]">{pct(p.share_inputs_outside_training, 0)} of events have an input beyond the surrogate's training data</p>
          )}
        </div>
        <div>
          <p className={`${label} text-[#a8a089]`}>How events fail · share of all events</p>
          <div className="mt-4 space-y-3">
            {shares.map(([m, v]) => {
              const s = modes[m] ?? { name: m, color: '#8d8670' }
              return (
                <div key={m} className="grid grid-cols-[200px_1fr_56px] items-center gap-4">
                  <span className="flex items-center gap-2 text-[14px] text-[#f6f1e2]"><span className="h-2 w-2 shrink-0 rounded-full" style={{ background: s.color }} />{s.name}</span>
                  <div className="h-[10px] bg-[#1a1813]"><div className="h-full" style={{ width: `${v * 100}%`, background: s.color }} /></div>
                  <span className="mono text-right text-[12px] text-[#c4bca7]">{pct(v)}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="mt-12 overflow-x-auto">
        <table className="w-full min-w-[560px] text-left">
          <thead>
            <tr className="mono border-b border-[#4a4332] text-[11px] tracking-[0.14em] text-[#8d8670] uppercase">
              <th className="pb-3 font-medium">Measure</th>
              {['5%', '25%', 'median', '75%', '95%'].map((h) => <th key={h} className="pb-3 text-right font-medium">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {Object.entries(MEASURES).map(([k, m]) => {
              const q = p.continuous[k]?.quantiles
              if (!q) return null
              return (
                <tr key={k} className="border-b border-[#2b2720]">
                  <td className="py-3 text-[14px] text-[#f6f1e2]">{m.name}</td>
                  {['0.05', '0.25', '0.5', '0.75', '0.95'].map((qk) => <td key={qk} className="mono py-3 text-right text-[12.5px] text-[#c4bca7]">{m.fmt(q[qk])}</td>)}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-12 max-w-[760px] text-[15px] leading-[1.55] text-[#c4bca7]">
        What moves the {OUTPUT_NAME[r.headline_output] ?? r.headline_output} most, by Shapley share.
        {r.saturated && ' Almost every event fails, so a chance of failing cannot be ranked; the ranking uses this measure instead.'}
        {split && ` Grid and weather conditions explain ${pct(split.A_share, 0)} of it, site state ${pct(1 - split.A_share, 0)}.`}
      </p>
      <div className="mt-6 grid gap-12 md:grid-cols-2">
        <Drivers r={r} group="A" title="Conditions · what the grid and weather do" />
        <Drivers r={r} group="B" title="Site state · what the equipment is like" />
      </div>

      <details className="mt-12 border-t border-[#2b2720] pt-5">
        <summary className={`${label} cursor-pointer text-[#a8a089]`}>Caveats and model</summary>
        {sur && (
          <p className="mono mt-4 text-[12px] text-[#c4bca7]">
            Surrogate {sur.name ?? '?'} ({sur.format ?? '?'}), {sur.trained_rows?.toLocaleString() ?? '?'} training runs, simulator commit {sur.simulator_commit?.slice(0, 7) ?? 'unknown'}.
          </p>
        )}
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[14px] leading-[1.5] text-[#a8a089]">
          {r.caveats.map((c) => <li key={c}>{c}</li>)}
        </ul>
      </details>
    </>
  )
}
