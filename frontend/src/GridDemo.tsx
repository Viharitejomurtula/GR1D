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
const INITIAL_VIEW_STATE: MapViewState = { longitude: -98.05, latitude: 29.3, zoom: 8.9, pitch: 12, bearing: 0, maxZoom: 14, maxPitch: 80 }

// scroll-zoom is off so the mouse wheel scrolls the page down to "Why it matters"
const FONT = '"IBM Plex Mono", monospace'
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

function eventState(e: number, tHit: number, hold = HOLD) {
  if (e < 0) return { s: 0, r: 0, dropAge: -1, end: tHit + hold + 2.4 }
  // s: share of the data center's load that has left the grid. r: grid strain.
  const back = e - (tHit + hold)
  const s = clamp01((e - tHit) / 0.3) * (1 - clamp01(back / 1.8))
  const pulse = e > tHit && back < 0 ? 0.9 + 0.1 * Math.sin(e * 5) : 1
  const r = clamp01((e - tHit) / 1.0) * (1 - clamp01(back / 2.2)) * pulse
  return { s, r, dropAge: e - tHit, end: tHit + hold + 2.4 }
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

const DC_HW = 0.2 // half-width and half-height of the campus, in degrees
const DC_HH = 0.125
// three by two server halls with an aisle between them; heights vary a little so it reads as buildings
function dcHalls(p: number[]) {
  const out: { polygon: number[][]; h: number }[] = []
  const w = (2 * DC_HW) / 3, h = (2 * DC_HH) / 2
  for (let c = 0; c < 3; c++) for (let r = 0; r < 2; r++) {
    const cx = p[0] - DC_HW + w * (c + 0.5), cy = p[1] - DC_HH + h * (r + 0.5)
    out.push({ polygon: box(cx, cy, w * 0.4, h * 0.38), h: [9000, 13000, 8000, 11000, 14000, 9500][c * 2 + r] })
  }
  return out
}

const box = (x: number, y: number, hw: number, hh: number) => [[x - hw, y - hh], [x + hw, y - hh], [x + hw, y + hh], [x - hw, y + hh]]

type DemoProps = {
  onFinished?: () => void; onNext?: () => void
  // embedded in another page: no header, counters or buttons; the event is started by changing `trigger`
  embedded?: boolean; trigger?: number
  rideThrough?: boolean // the site rides through the dip instead of dropping off the grid
  hold?: number; zoom?: number
  onClock?: (secondsSinceDipArrived: number, active: boolean) => void
  // Driven by simulator output instead of the scripted event (Results tab): the parent maps the clock to a simulated
  // trace and passes the state for this frame. s: share of the site's pre-fault load off the grid; r: grid strain;
  // bbu: battery output, 0-1. Held after the event ends, so the final state stays on screen.
  drive?: { s: number; r: number; bbu: number; dcText: string; status: string; strained: boolean }
}

export default function GridDemo({ onFinished, onNext, embedded, trigger, rideThrough, hold = HOLD, zoom, onClock, drive }: DemoProps) {
  const [grid, setGrid] = useState<Grid>()
  const [now, setNow] = useState(0)
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [fk, setFk] = useState(0) // bumps once Plex Mono has loaded, so deck's text atlas is rebuilt with it
  useEffect(() => { document.fonts.load('500 14px "IBM Plex Mono"').then(() => setFk(1)).catch(() => {}) }, [])
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
  const battery = useMemo<[number, number] | undefined>(() => (dc ? [dc.p[0], dc.p[1] - 0.31] : undefined), [dc])
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

  useEffect(() => { if (trigger) setStartedAt(performance.now() / 1000) }, [trigger])
  const fixed = new URLSearchParams(location.search).get('t') // ?t=8 freezes the replay 8 s after the press
  const { end } = eventState(0, tHit, hold)
  const e = fixed !== null ? Number(fixed) : startedAt === null ? -1 : now - startedAt
  const active = e >= 0 && e < end
  useEffect(() => { onClock?.(e - tHit, active) }, [now]) // eslint-disable-line react-hooks/exhaustive-deps
  const ev = eventState(active ? e : -1, tHit, hold)
  const s = drive ? drive.s : rideThrough ? 0 : ev.s, r = drive ? drive.r : rideThrough ? 0 : ev.r
  const dropAge = drive ? (active && e > tHit && drive.s > 0.5 ? e - tHit : -1) : rideThrough ? -1 : ev.dropAge
  // the recession: after the drop, a dark zone spreads out from the data center. Nothing flows inside it.
  const back = e - (tHit + hold)
  const sFlow = drive ? drive.s : clamp01((dropAge - 0.4) / 1.4) * (1 - clamp01(back / 1.8))
  const deadR = drive ? DEAD_R * clamp01((drive.s - 0.2) / 0.8)
    : active && dropAge > 0 ? DEAD_R * (1 - Math.pow(1 - clamp01(dropAge / 2.4), 3)) * (1 - clamp01(back / 1.8)) : 0
  const cometTime = now % PERIOD
  const wasActive = useRef(false)
  const ran = useRef(false)
  if (active && s > 0.5) ran.current = true
  useEffect(() => {
    if (wasActive.current && !active && fixed === null) { const t = setTimeout(() => onFinished?.(), 900); return () => clearTimeout(t) }
    wasActive.current = active
  }, [active]) // eslint-disable-line react-hooks/exhaustive-deps
  const onBattery = drive ? drive.bbu > 0.5 : s > 0.5
  const bbuGlow = drive ? drive.bbu : s

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

  const dcText = drive ? drive.dcText : rideThrough && active && e > tHit ? `DATA CENTER\nRIDING THROUGH  ·  ${dc?.mw} MW` : onBattery ? 'DATA CENTER\n0 MW FROM GRID  ·  ON BATTERY' : s > 0 ? 'DATA CENTER\nRECONNECTING' : `DATA CENTER\n${dc?.mw} MW`

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
    trip('battery-glow', cometsBattery, 2.8, 90, TRAIL, CYAN, bbuGlow, true),
    trip('battery', cometsBattery, 1, 240, TRAIL, CYAN, bbuGlow),
    trip('battery-core', cometsBattery, 0.38, 255, TRAIL * 0.4, [235, 250, 255], bbuGlow),
    new ScatterplotLayer<Substation>({
      id: 'substations', data: grid?.substations.filter((d) => hv(d.kv) || d.deg >= 3), parameters: { depthCompare: 'always' },
      getPosition: (d) => d.p, radiusUnits: 'pixels', getRadius: (d) => (hv(d.kv) ? 5 : 3),
      getFillColor: (d) => (hv(d.kv) ? [255, 244, 214, 255] : [255, 196, 120, 255]) as never,
      stroked: true, getLineColor: [20, 14, 4, 255], getLineWidth: 1, lineWidthUnits: 'pixels',
    }),
    new TextLayer<Label, CollisionFilterExtensionProps>({
      id: `labels${fk}`, data: labels, extensions: [collision], billboard: false, background: true,
      parameters: { cullMode: 'none', depthCompare: 'always' },
      getPosition: (d) => d.position as never, getText: (d) => d.text, getAngle: (d) => d.angle,
      getSize: (d) => (d.priority >= 150 ? 13 : 11), getColor: [30, 20, 4], getBackgroundColor: [255, 232, 170],
      getBorderColor: [255, 170, 40], getBorderWidth: 1, backgroundPadding: [4, 1], characterSet: 'auto', fontFamily: FONT,
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
    // the data center: a campus of server halls on a pad, lit gold (cyan while it runs on battery)
    new ScatterplotLayer({
      id: 'dc-glow', data: dc ? [0, 1] : [], getPosition: () => dc!.p as never, radiusUnits: 'meters',
      getRadius: (i: number) => 24000 + i * 14000, getFillColor: (i: number) => (onBattery ? [...CYAN, 38 - i * 16] : [...GOLD, 46 - i * 20]) as never,
      parameters: ADD, updateTriggers: { getFillColor: onBattery },
    }),
    new PolygonLayer<{ polygon: number[][] }>({
      id: 'dc-pad', data: dc ? [{ polygon: box(dc.p[0], dc.p[1], DC_HW * 1.1, DC_HH * 1.16) }] : [], getPolygon: (d) => d.polygon as never,
      filled: true, stroked: true, getFillColor: [46, 42, 34, 255], getLineColor: (onBattery ? CYAN : GOLD).concat(255) as never,
      getLineWidth: 2.5, lineWidthUnits: 'pixels', updateTriggers: { getLineColor: onBattery },
    }),
    new PolygonLayer<{ polygon: number[][]; h: number }>({
      id: 'datacenter', data: dc ? dcHalls(dc.p) : [], getPolygon: (d) => d.polygon as never, getElevation: (d) => d.h,
      extruded: true, wireframe: true, getFillColor: (onBattery ? [52, 98, 118, 255] : [112, 100, 76, 255]) as never,
      getLineColor: (onBattery ? CYAN : GOLD).concat(255) as never, lineWidthMinPixels: 1.5,
      updateTriggers: { getFillColor: onBattery, getLineColor: onBattery },
      material: { ambient: 0.55, diffuse: 0.75, shininess: 24, specularColor: [255, 225, 150] },
    }),
    new PolygonLayer<{ polygon: number[][] }>({
      id: 'battery-block', data: battery ? [{ polygon: box(battery[0], battery[1], 0.05, 0.03) }] : [], getPolygon: (d) => d.polygon as never,
      extruded: true, wireframe: true, getElevation: 6000, getFillColor: (bbuGlow > 0.5 ? [52, 98, 118, 255] : [70, 80, 90, 255]) as never, lineWidthMinPixels: 2,
      material: { ambient: 0.55, diffuse: 0.75, shininess: 24, specularColor: [200, 230, 255] },
      getLineColor: (bbuGlow > 0.05 ? [...CYAN, 150 + 105 * bbuGlow] : [130, 160, 175, 220]) as never, updateTriggers: { getLineColor: bbuGlow, getFillColor: bbuGlow > 0.5 },
    }),
    new TextLayer<{ p: number[]; t: string; c: RGB; size: number }>({
      id: `dc-label${fk}`, data: dc ? [{ p: dc.p, t: dcText, c: onBattery ? CYAN : [255, 232, 170], size: 18 }] : [],
      getPosition: (d) => [d.p[0], d.p[1] - 0.2, 0] as never, getText: (d) => d.t, getSize: (d) => d.size, getColor: (d) => d.c as never,
      getPixelOffset: [0, 0], background: true, getBackgroundColor: [4, 4, 6, 235], getBorderColor: onBattery ? (CYAN as never) : ([255, 200, 74] as never),
      getBorderWidth: 1.5, backgroundPadding: [8, 4], lineHeight: 1.25, characterSet: 'auto', fontFamily: FONT, parameters: { depthCompare: 'always' },
      updateTriggers: { getText: dcText, getColor: onBattery, getBorderColor: onBattery },
    }),
    new TextLayer<{ p: number[] }>({
      id: `battery-label${fk}`, data: battery ? [{ p: battery }] : [], getPosition: (d) => [d.p[0], d.p[1], 9000] as never,
      getText: () => 'ON-SITE BATTERY + GENERATION', getSize: 13, getColor: bbuGlow > 0.05 ? (CYAN as never) : ([150, 160, 168] as never),
      getPixelOffset: [0, 30], characterSet: 'auto', fontFamily: FONT, parameters: { depthCompare: 'always' },
      updateTriggers: { getColor: bbuGlow > 0.05 },
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
      id: `fault-label${fk}`, data: faultOn ? [0] : [], getPosition: () => faultPt as never, getText: () => 'GRID FAULT', getSize: 16,
      getColor: [255, 120, 90], getPixelOffset: [0, -30], background: true, getBackgroundColor: [4, 4, 6, 235], backgroundPadding: [6, 3],
      characterSet: 'auto', fontFamily: FONT, parameters: { depthCompare: 'always' },
    }),
  ]

  const strained = drive ? drive.strained : s > 0.5
  const status = drive ? drive.status : !active ? 'NORMAL OPERATION'
    : e < tHit ? 'GRID FAULT  ·  DIP TRAVELLING TO THE DATA CENTER'
    : rideThrough ? 'DATA CENTER RIDES THROUGH THE DIP'
    : strained ? 'NO CURRENT REACHES THE DATA CENTER  ·  GRID STRAINED'
    : e < tHit + hold ? 'DATA CENTER LEAVING THE GRID' : 'DATA CENTER RECONNECTING'

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <DeckGL views={view} initialViewState={zoom ? { ...INITIAL_VIEW_STATE, zoom } : INITIAL_VIEW_STATE} controller={CONTROLLER} layers={layers} style={{ position: 'absolute', inset: '0' }}>
        <Map reuseMaps mapStyle={MAP_STYLE} />
      </DeckGL>

      {!embedded && (<>
      {/* soft fades so type can sit directly on the map, with no boxes */}
      <div className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(ellipse 900px 600px at 0% 0%, rgba(7,7,10,0.97) 0%, rgba(7,7,10,0.9) 45%, rgba(7,7,10,0.5) 72%, transparent 100%), radial-gradient(ellipse 420px 260px at 100% 0%, rgba(7,7,10,0.85), transparent 100%)' }} />

      <header className="pointer-events-none absolute top-8 left-10 max-w-[520px] [text-shadow:0_0_14px_rgba(7,7,10,0.95),0_0_3px_rgba(7,7,10,0.9)]">
        <p className="mono text-[11.5px] font-medium tracking-[0.14em] text-[#d9b24c] uppercase">December 2022 · West Texas</p>
        <h1 className="display mt-3 text-[38px] leading-[1.05] font-semibold tracking-[-0.035em] text-[#f6f1e2] [text-wrap:balance]">
          About 1,560 MW of large load dropped off the Texas grid at once.
        </h1>
        <p className="mt-4 max-w-[470px] text-[15.5px] leading-[1.55] text-[#d3ccb8]">
          A single grid fault was enough to trip hundreds of large loads together. Data centers could now do the same, at much larger scale.
        </p>
      </header>

      </>)}

      {/* live counters, beside the graphic */}
      {!embedded && (
      <div className="pointer-events-none absolute top-8 right-10 text-right">
        <p className="mono text-[11px] tracking-[0.14em] text-[#a8a089] uppercase">Draw from the grid</p>
        <p className="display text-[64px] leading-[0.95] font-semibold tracking-[-0.04em]" style={{ color: onBattery ? '#ff6a55' : '#f6f1e2' }}>
          {Math.round((dc?.mw ?? 800) * (1 - s))}<span className="ml-1.5 text-[22px] font-medium tracking-normal text-[#a8a089]">MW</span>
        </p>
        <p className="mono mt-2 text-[11px] tracking-[0.14em] uppercase" style={{ color: strained ? '#ff6a55' : '#a8a089' }}>
          Grid · {strained ? 'strained' : active && e < tHit ? 'fault' : 'normal'}
        </p>
      </div>
      )}

      <div className="pointer-events-none absolute bottom-6 left-10 mono max-w-[300px] text-[11.5px] leading-snug font-medium tracking-[0.1em]" style={{ color: strained ? '#ff6a55' : '#a8a089' }}>
        <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: strained ? '#ff4a3a' : '#d9b24c' }} />
        {status}
      </div>

      {!embedded && (
      <div style={{ position: 'absolute', left: '50%', bottom: 22, transform: 'translateX(-50%)' }} className="flex items-baseline gap-9">
        <button
          onClick={() => { if (!active) setStartedAt(performance.now() / 1000) }}
          disabled={active}
          className={`mono text-[13px] font-medium tracking-[0.12em] uppercase underline-offset-[7px] transition ${
            active ? 'cursor-default text-[#6f6958]' : 'cursor-pointer text-[#f0c85a] hover:text-white hover:underline'}`}>
          {active ? 'Fault in progress' : ran.current ? '▸ Replay grid fault' : '▸ Trigger a grid fault'}
        </button>
        {(ran.current || strained) && (
          <button onClick={onNext} className="mono cursor-pointer text-[13px] font-medium tracking-[0.12em] text-[#bdb5a0] uppercase underline-offset-[7px] transition hover:text-white hover:underline">
            Why it matters ↓
          </button>
        )}
      </div>
      )}
    </div>
  )
}
