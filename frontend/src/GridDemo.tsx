import { useEffect, useMemo, useRef, useState } from 'react'
import { Map } from 'react-map-gl/maplibre'
import { setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { DeckGL, GeoJsonLayer, MapView, PolygonLayer, ScatterplotLayer, TextLayer, TripsLayer } from 'deck.gl'
import { CollisionFilterExtension, type CollisionFilterExtensionProps } from '@deck.gl/extensions'
import type { MapViewState } from 'deck.gl'
import type { Feature, FeatureCollection, LineString } from 'geojson'
import { KM_PER_LAT, calculateLabels, kmLonAt, type Label } from './labels'

setWorkerUrl('/maplibre/maplibre-gl-worker.mjs') // copied into public/ by the predev/prebuild scripts

interface Substation { p: [number, number]; kv: number; deg: number }
interface Props { kv: number; owner: string | null; mw: number; mw_off: number; feeder?: boolean; synthetic?: boolean }
type Line = Feature<LineString, Props>
interface Grid { lines: FeatureCollection<LineString, Props>; substations: Substation[]; dc: { p: [number, number]; mw: number } }

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json'
const INITIAL_VIEW_STATE: MapViewState = { longitude: -98.12, latitude: 29.42, zoom: 9.0, pitch: 12, bearing: 0, maxZoom: 14, maxPitch: 80 }

// scroll-zoom is off so the mouse wheel scrolls the page down to "Why it matters"
const CONTROLLER = { scrollZoom: false }
const view = new MapView({ id: 'map', controller: CONTROLLER })
const collision = new CollisionFilterExtension()

type RGB = number[]
const GOLD: RGB = [255, 200, 74]
const AMBER: RGB = [255, 138, 40]
const COPPER: RGB = [230, 120, 70]
const RED: RGB = [255, 52, 44]
const CYAN: RGB = [120, 215, 255]
const WHITE_HOT: RGB = [255, 247, 224]
const ADD = { depthCompare: 'always', blend: true, blendColorSrcFactor: 'src-alpha', blendColorDstFactor: 'one', blendAlphaSrcFactor: 'one', blendAlphaDstFactor: 'one' } as never
const hv = (kv: number) => kv >= 345
const synth = (f: { properties: Props }) => !!f.properties.synthetic

// ---- the event, started by the button -----------------------------------------------------------
// e = seconds since the press. A fault happens far from the data center; the voltage dip travels out at WAVE_KM_S.
// When it reaches the data center (tHit) the site drops its load off the grid and runs on battery. The red current is
// the change in flow that causes, which moves away from the data center. Later the site reconnects.
const WAVE_KM_S = 35
const HOLD = 10
const DEAD_R = 34000 // metres: radius of the zone that goes without current
const clamp01 = (x: number) => Math.max(0, Math.min(1, x))

function eventState(e: number, tHit: number) {
  if (e < 0) return { s: 0, r: 0, dropAge: -1, end: tHit + HOLD + 2.4 }
  // s: share of the data center's load that has left the grid. r: grid strain.
  const back = e - (tHit + HOLD)
  const s = clamp01((e - tHit) / 0.3) * (1 - clamp01(back / 1.8))
  const pulse = e > tHit && back < 0 ? 0.9 + 0.1 * Math.sin(e * 5) : 1
  const r = clamp01((e - tHit) / 1.0) * (1 - clamp01(back / 2.2)) * pulse
  return { s, r, dropAge: e - tHit, end: tHit + HOLD + 2.4 }
}

// ---- current: comets that travel along each line in the direction of its power flow ----
// Timestamps are in seconds; a comet's head is at distance v*(T - offset) along the line, so heavier lines get
// faster, longer comets. Copies are phase-shifted so the loop over PERIOD is seamless.
const PERIOD = 12
const TRAIL = 1.8
const SPACING = 4
const speedKmS = (mw: number) => 4 + 10 * Math.min(1, Math.abs(mw) / 450)

interface Comet { path: number[][]; ts: number[]; w: number }

function buildComets(lines: Line[], pick: (p: Props) => number, minMw = 4): Comet[] {
  const out: Comet[] = []
  for (const f of lines) {
    const mw = pick(f.properties)
    if (Math.abs(mw) < minMw) continue
    const path = mw >= 0 ? f.geometry.coordinates : [...f.geometry.coordinates].reverse()
    const km = [0]
    for (let i = 1; i < path.length; i++) {
      km.push(km[i - 1] + Math.hypot((path[i][0] - path[i - 1][0]) * kmLonAt(path[i][1]), (path[i][1] - path[i - 1][1]) * KM_PER_LAT))
    }
    const v = speedKmS(mw)
    const base = km.map((d) => d / v)
    const tau = base[base.length - 1]
    const w = (f.properties.synthetic ? 1.2 : 1.6) + Math.sqrt(Math.abs(mw)) * 0.3
    const copies = Math.ceil(PERIOD / SPACING)
    const laps = Math.ceil((tau + TRAIL) / PERIOD)
    for (let j = 0; j < copies; j++) for (let m = 0; m <= laps; m++) {
      out.push({ path, ts: base.map((t) => t + j * SPACING - m * PERIOD), w })
    }
  }
  return out
}

const box = (x: number, y: number, hw: number, hh: number) => [[x - hw, y - hh], [x + hw, y - hh], [x + hw, y + hh], [x - hw, y + hh]]

export default function GridDemo({ onFinished, onNext }: { onFinished?: () => void; onNext?: () => void }) {
  const [grid, setGrid] = useState<Grid>()
  const [now, setNow] = useState(0)
  const [startedAt, setStartedAt] = useState<number | null>(null)
  useEffect(() => { fetch('/data/grid.json').then((r) => r.json()).then(setGrid) }, [])
  useEffect(() => {
    let raf = 0
    const loop = (t: number) => { setNow(t / 1000); raf = requestAnimationFrame(loop) }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [])

  const lines = (grid?.lines.features ?? []) as Line[]
  const labels = useMemo(() => calculateLabels(lines.filter((f) => !f.properties.synthetic), 6), [grid]) // eslint-disable-line react-hooks/exhaustive-deps
  const dc = grid?.dc
  const battery = useMemo<[number, number] | undefined>(() => (dc ? [dc.p[0], dc.p[1] - 0.24] : undefined), [dc])
  const cometsNormal = useMemo(() => buildComets(lines, (p) => p.mw), [grid]) // eslint-disable-line react-hooks/exhaustive-deps
  const cometsPost = useMemo(() => buildComets(lines, (p) => p.mw_off), [grid]) // eslint-disable-line react-hooks/exhaustive-deps
  const cometsBattery = useMemo(() => {
    if (!dc || !battery) return []
    return buildComets([{ type: 'Feature', properties: { kv: 345, owner: null, mw: 800, mw_off: 800 }, geometry: { type: 'LineString', coordinates: [battery, dc.p] } }], (p) => p.mw)
  }, [dc, battery])
  // the fault: the most heavily loaded 345 kV line 40-70 km from the data center that is on screen (south-west of it)
  const fault = useMemo(() => {
    if (!dc) return undefined
    const km = (p: number[]) => Math.hypot((p[0] - dc.p[0]) * kmLonAt(p[1]), (p[1] - dc.p[1]) * KM_PER_LAT)
    let best: { pt: number[]; km: number; mw: number } | undefined
    for (const f of lines) {
      if (f.properties.kv < 345 || f.properties.feeder || f.properties.synthetic) continue
      const c = f.geometry.coordinates
      const pt = c[Math.floor(c.length / 2)]
      const d = km(pt)
      if (d < 40 || d > 70 || pt[1] < 29.0 || pt[1] > 29.5 || pt[0] < -98.7 || pt[0] > -98.0) continue
      if (!best || Math.abs(f.properties.mw) > best.mw) best = { pt, km: d, mw: Math.abs(f.properties.mw) }
    }
    return best
  }, [grid]) // eslint-disable-line react-hooks/exhaustive-deps
  const faultPt = fault?.pt
  const tHit = fault ? fault.km / WAVE_KM_S : 2

  const fixed = new URLSearchParams(location.search).get('t') // ?t=8 freezes the replay 8 s after the press
  const { end } = eventState(0, tHit)
  const e = fixed !== null ? Number(fixed) : startedAt === null ? -1 : now - startedAt
  const active = e >= 0 && e < end
  const { s, r, dropAge } = eventState(active ? e : -1, tHit)
  // the recession: after the drop, a dark zone spreads out from the data center. Nothing flows inside it.
  const back = e - (tHit + HOLD)
  const sFlow = clamp01((dropAge - 0.4) / 1.4) * (1 - clamp01(back / 1.8))
  const deadR = active && dropAge > 0 ? DEAD_R * (1 - Math.pow(1 - clamp01(dropAge / 2.4), 3)) * (1 - clamp01(back / 1.8)) : 0
  const cometTime = now % PERIOD
  const wasActive = useRef(false)
  const ran = useRef(false)
  if (active && s > 0.5) ran.current = true
  useEffect(() => {
    if (wasActive.current && !active && fixed === null) { const t = setTimeout(() => onFinished?.(), 900); return () => clearTimeout(t) }
    wasActive.current = active
  }, [active]) // eslint-disable-line react-hooks/exhaustive-deps
  const onBattery = s > 0.5

  const trip = (id: string, data: Comet[], widthMul: number, alpha: number, trail: number, color: RGB, opacity: number, blend = false) =>
    new TripsLayer<Comet>({
      id, data, visible: opacity > 0.01, opacity, getPath: (d) => d.path as never, getTimestamps: (d) => d.ts,
      getColor: [...color, alpha] as never, getWidth: (d) => d.w * widthMul, widthUnits: 'pixels', capRounded: true, jointRounded: true,
      currentTime: cometTime, trailLength: trail, fadeTrail: true, parameters: blend ? ADD : ({ depthCompare: 'always' } as never),
    })
  const gold = (key: string, data: Comet[], opacity: number) => [
    trip(`${key}-glow`, data, 2.8, 70, TRAIL, GOLD, opacity, true),
    trip(`${key}-body`, data, 1, 235, TRAIL, GOLD, opacity),
    trip(`${key}-core`, data, 0.38, 255, TRAIL * 0.4, WHITE_HOT, opacity),
  ]
  const red = (key: string, data: Comet[], opacity: number) => [
    trip(`${key}-glow`, data, 3.6, 140, TRAIL * 1.3, RED, opacity, true),
    trip(`${key}-body`, data, 1.6, 255, TRAIL * 1.3, RED, opacity),
    trip(`${key}-core`, data, 0.55, 255, TRAIL * 0.5, [255, 225, 215], opacity),
  ]

  const rings = dropAge > 0 && dropAge < 5 ? [0, 0.7, 1.4].map((o) => ({ age: dropAge - o })).filter((x) => x.age > 0 && x.age < 3.4) : []
  const faultOn = !!faultPt && active && e < tHit + 2.5
  const pulse = (e * 2.2) % 1
  const waveR = e * WAVE_KM_S * 1000 // metres: the dip travelling out from the fault

  const dcText = onBattery ? 'DATA CENTER\n0 MW FROM GRID  ·  ON BATTERY' : s > 0 ? 'DATA CENTER\nRECONNECTING' : `DATA CENTER\n${dc?.mw} MW`

  const layers = [
    // the wires, dim; the current is what glows
    new GeoJsonLayer<Props>({
      id: 'lines-glow', data: grid?.lines as never,
      getLineColor: (f) => [...(hv(f.properties.kv) ? GOLD : synth(f) ? COPPER : AMBER), hv(f.properties.kv) ? 70 : synth(f) ? 26 : 40] as never,
      getLineWidth: (f) => (hv(f.properties.kv) ? 12 : synth(f) ? 4 : 6), lineWidthUnits: 'pixels', lineWidthMinPixels: 2, parameters: ADD,
    }),
    new GeoJsonLayer<Props>({
      id: 'lines-glow-red', data: grid?.lines as never, visible: r > 0.01, opacity: r * 0.4,
      getLineColor: (f) => [...RED, hv(f.properties.kv) ? 150 : synth(f) ? 60 : 100] as never,
      getLineWidth: (f) => (hv(f.properties.kv) ? 14 : synth(f) ? 5 : 8), lineWidthUnits: 'pixels', lineWidthMinPixels: 2, parameters: ADD,
    }),
    new GeoJsonLayer<Props>({
      id: 'lines', data: grid?.lines as never, parameters: { depthCompare: 'always' },
      getLineColor: (f) => (hv(f.properties.kv) ? [200, 170, 100, 230] : synth(f) ? [170, 105, 60, 150] : [190, 130, 60, 200]) as never,
      getLineWidth: (f) => (hv(f.properties.kv) ? 2.5 : synth(f) ? 0.9 : 1.2), lineWidthUnits: 'pixels', lineWidthMinPixels: 1,
    }),
    ...gold('normal', cometsNormal, 1 - sFlow),
    ...red('post', cometsPost, sFlow),
    trip('battery-glow', cometsBattery, 2.8, 90, TRAIL, CYAN, s, true),
    trip('battery', cometsBattery, 1, 240, TRAIL, CYAN, s),
    trip('battery-core', cometsBattery, 0.38, 255, TRAIL * 0.4, [235, 250, 255], s),
    new ScatterplotLayer<Substation>({
      id: 'substations', data: grid?.substations.filter((d) => hv(d.kv) || d.deg >= 3), parameters: { depthCompare: 'always' },
      getPosition: (d) => d.p, radiusUnits: 'pixels', getRadius: (d) => (hv(d.kv) ? 5 : 3),
      getFillColor: (d) => (hv(d.kv) ? [255, 244, 214, 255] : [255, 196, 120, 255]) as never,
      stroked: true, getLineColor: [20, 14, 4, 255], getLineWidth: 1, lineWidthUnits: 'pixels',
    }),
    new TextLayer<Label, CollisionFilterExtensionProps>({
      id: 'labels', data: labels, extensions: [collision], billboard: false, background: true,
      parameters: { cullMode: 'none', depthCompare: 'always' },
      getPosition: (d) => d.position as never, getText: (d) => d.text, getAngle: (d) => d.angle,
      getSize: (d) => (d.priority >= 150 ? 13 : 11), getColor: [30, 20, 4], getBackgroundColor: [255, 232, 170],
      getBorderColor: [255, 170, 40], getBorderWidth: 1, backgroundPadding: [4, 1], characterSet: 'auto', fontFamily: 'monospace',
      collisionEnabled: true, getCollisionPriority: (d) => d.priority, collisionTestProps: { sizeScale: 10 },
    }),
    // the blackout: nothing flows inside, so the grid goes dark there
    new ScatterplotLayer({
      id: 'dead-zone', data: deadR > 0 && dc ? [0] : [], getPosition: () => dc!.p as never, radiusUnits: 'meters',
      getRadius: deadR, getFillColor: [6, 6, 8, 244] as never, parameters: { depthCompare: 'always' }, updateTriggers: { getRadius: deadR },
    }),
    // the edge of the dark zone
    new ScatterplotLayer({
      id: 'dead-zone-edge', data: deadR > 0 && dc ? [0] : [], getPosition: () => dc!.p as never, radiusUnits: 'meters', filled: false, stroked: true,
      getRadius: deadR, getLineWidth: 3, lineWidthUnits: 'pixels', getLineColor: [255, 70, 55, 230] as never, parameters: { depthCompare: 'always' },
      updateTriggers: { getRadius: deadR },
    }),
    // red halo and shockwaves leaving the data center when it drops off
    new ScatterplotLayer({
      id: 'dc-halo', data: dc && r > 0.01 ? [0, 1, 2] : [], getPosition: () => dc!.p as never, radiusUnits: 'meters',
      getRadius: (i: number) => 14000 + i * 9000, getFillColor: (i: number) => [...RED, (60 - i * 17) * r] as never, parameters: ADD,
      updateTriggers: { getFillColor: r },
    }),
    new ScatterplotLayer<{ age: number }>({
      id: 'shockwave', data: dc ? rings : [], getPosition: () => dc!.p as never, radiusUnits: 'meters', filled: false, stroked: true,
      getRadius: (d) => d.age * 38000, getLineWidth: (d) => 6 * (1 - d.age / 3.4) + 1.5, lineWidthUnits: 'pixels',
      getLineColor: (d) => [...RED, 255 * (1 - d.age / 3.4)] as never, parameters: { depthCompare: 'always' },
      updateTriggers: { getRadius: dropAge, getLineWidth: dropAge, getLineColor: dropAge },
    }),
    // the data center: a black monolith; edges go cyan while it runs on battery
    new PolygonLayer<{ polygon: number[][] }>({
      id: 'datacenter', data: dc ? [{ polygon: box(dc.p[0], dc.p[1], 0.13, 0.085) }] : [], getPolygon: (d) => d.polygon as never,
      extruded: true, wireframe: true, getElevation: 9000, getFillColor: [4, 4, 6, 255], lineWidthMinPixels: 2.5,
      getLineColor: (onBattery ? CYAN : GOLD).concat(255) as never, updateTriggers: { getLineColor: onBattery },
      material: { ambient: 0.15, diffuse: 0.25, shininess: 60, specularColor: [255, 200, 90] },
    }),
    new PolygonLayer<{ polygon: number[][] }>({
      id: 'battery-block', data: battery ? [{ polygon: box(battery[0], battery[1], 0.05, 0.03) }] : [], getPolygon: (d) => d.polygon as never,
      extruded: true, wireframe: true, getElevation: 4000, getFillColor: [4, 4, 6, 255], lineWidthMinPixels: 2,
      getLineColor: (s > 0.05 ? [...CYAN, 150 + 105 * s] : [90, 120, 135, 200]) as never, updateTriggers: { getLineColor: s },
    }),
    new TextLayer<{ p: number[]; t: string; c: RGB; size: number }>({
      id: 'dc-label', data: dc ? [{ p: dc.p, t: dcText, c: onBattery ? CYAN : [255, 232, 170], size: 18 }] : [],
      getPosition: (d) => [d.p[0], d.p[1] - 0.15, 0] as never, getText: (d) => d.t, getSize: (d) => d.size, getColor: (d) => d.c as never,
      getPixelOffset: [0, 0], background: true, getBackgroundColor: [4, 4, 6, 235], getBorderColor: onBattery ? (CYAN as never) : ([255, 200, 74] as never),
      getBorderWidth: 1.5, backgroundPadding: [8, 4], lineHeight: 1.25, characterSet: 'auto', fontFamily: 'monospace', parameters: { depthCompare: 'always' },
      updateTriggers: { getText: dcText, getColor: onBattery, getBorderColor: onBattery },
    }),
    new TextLayer<{ p: number[] }>({
      id: 'battery-label', data: battery ? [{ p: battery }] : [], getPosition: (d) => [d.p[0], d.p[1], 9000] as never,
      getText: () => 'ON-SITE BATTERY + GENERATION', getSize: 13, getColor: s > 0.05 ? (CYAN as never) : ([150, 160, 168] as never),
      getPixelOffset: [0, 30], characterSet: 'auto', fontFamily: 'monospace', parameters: { depthCompare: 'always' },
      updateTriggers: { getColor: s > 0.05 },
    }),
    // the fault, and the voltage dip travelling out from it
    new ScatterplotLayer({
      id: 'dip-wave', data: faultOn && waveR < 140000 ? [0] : [], getPosition: () => faultPt as never, radiusUnits: 'meters', filled: false, stroked: true,
      getRadius: waveR, getLineWidth: 3, lineWidthUnits: 'pixels', getLineColor: [255, 170, 60, 220 * (1 - waveR / 140000)] as never,
      parameters: { depthCompare: 'always' }, updateTriggers: { getRadius: e, getLineColor: e },
    }),
    new ScatterplotLayer({
      id: 'fault-ring', data: faultOn ? [0] : [], getPosition: () => faultPt as never, radiusUnits: 'pixels', filled: false, stroked: true,
      getRadius: 10 + pulse * 40, getLineWidth: 3, lineWidthUnits: 'pixels', getLineColor: [255, 90, 60, 255 * (1 - pulse)] as never,
      parameters: { depthCompare: 'always' }, updateTriggers: { getRadius: e, getLineColor: e },
    }),
    new ScatterplotLayer({
      id: 'fault-dot', data: faultOn ? [0] : [], getPosition: () => faultPt as never, radiusUnits: 'pixels', getRadius: 7,
      getFillColor: [255, 90, 60, 255], parameters: { depthCompare: 'always' },
    }),
    new TextLayer({
      id: 'fault-label', data: faultOn ? [0] : [], getPosition: () => faultPt as never, getText: () => 'GRID FAULT', getSize: 16,
      getColor: [255, 120, 90], getPixelOffset: [0, -30], background: true, getBackgroundColor: [4, 4, 6, 235], backgroundPadding: [6, 3],
      characterSet: 'auto', fontFamily: 'monospace', parameters: { depthCompare: 'always' },
    }),
  ]

  const strained = s > 0.5
  const status = !active ? 'NORMAL OPERATION'
    : e < tHit ? 'GRID FAULT  ·  DIP TRAVELLING TO THE DATA CENTER'
    : strained ? 'NO CURRENT REACHES THE DATA CENTER  ·  GRID STRAINED'
    : e < tHit + HOLD ? 'DATA CENTER LEAVING THE GRID' : 'DATA CENTER RECONNECTING'

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <DeckGL views={view} initialViewState={INITIAL_VIEW_STATE} controller={CONTROLLER} layers={layers} style={{ position: 'absolute', inset: '0' }}>
        <Map reuseMaps mapStyle={MAP_STYLE} />
      </DeckGL>

      <header style={{ position: 'absolute', top: 20, left: 20, width: 'min(440px, calc(100% - 40px))' }}
        className="border border-[#26231b] bg-[#08080ad9] p-5 backdrop-blur-md">
        <p className="mono text-[10.5px] tracking-[0.14em] text-[#d9b24c] uppercase">July 2026 · Northern Virginia</p>
        <h1 className="mt-2.5 text-[19px] leading-[1.3] font-medium tracking-[-0.012em] text-[#ece6d6]">
          Nearly 3,800 MW of data center demand shifted to on-site generation at once.
        </h1>
        <p className="mt-2.5 text-[13px] leading-[1.6] text-[#a29b86]">
          A mechanical failure on a 230 kV line set it off, about 2.5 times the 2024 event. On August 11, PJM said it is considering
          ride-through, backup generation behavior and reconnection requirements for data centers.
        </p>
        <p className="mono mt-3 border-t border-[#1f1d17] pt-2.5 text-[10px] leading-[1.55] text-[#6b6555]">
          Secondhand: Data Center Dispatch, citing Utility Dive. No dip depth or grid impact given; primary source unchecked.
          The replay is illustrative: a Texas grid and an 800 MW site.
        </p>
      </header>

      <div style={{ position: 'absolute', left: 20, bottom: 20, pointerEvents: 'none' }}
        className={`mono text-[11px] tracking-[0.12em] ${strained ? 'text-[#ff6a55]' : 'text-[#8a8472]'}`}>
        <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: strained ? '#ff4a3a' : '#d9b24c' }} />
        {status}
        {strained && <div className="mt-1 text-[10.5px] tracking-[0.08em] text-[#a8584c]">Nothing flows inside the red ring</div>}
      </div>

      <div style={{ position: 'absolute', left: '50%', bottom: 20, transform: 'translateX(-50%)' }} className="flex items-center gap-3">
        <button
          onClick={() => { if (!active) setStartedAt(performance.now() / 1000) }}
          disabled={active}
          className={`mono border px-5 py-2.5 text-[11px] tracking-[0.14em] uppercase backdrop-blur-md transition ${
            active ? 'cursor-default border-[#26231b] bg-[#08080acc] text-[#6b6555]' : 'cursor-pointer border-[#d9b24c] bg-[#08080acc] text-[#e8d9ac] hover:bg-[#d9b24c] hover:text-[#120d02]'}`}>
          {active ? 'Fault in progress' : ran.current ? 'Replay grid fault' : 'Trigger grid fault'}
        </button>
        {(ran.current || strained) && (
          <button onClick={onNext}
            className="mono cursor-pointer border border-[#3a362a] bg-[#08080acc] px-5 py-2.5 text-[11px] tracking-[0.14em] text-[#a29b86] uppercase backdrop-blur-md transition hover:border-[#6b6555] hover:text-[#e8e2d2]">
            Why it matters ↓
          </button>
        )}
      </div>
    </div>
  )
}
