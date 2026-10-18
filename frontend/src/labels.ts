// Places rotated labels along lines, coarse levels first, so collision filtering keeps the important ones.
import type { Feature, LineString } from 'geojson'

type Pt = number[]
export interface Label { position: Pt; angle: number; priority: number; text: string }

const KM_LAT = 110.57
const kmLon = (lat: number) => 111.32 * Math.cos((lat * Math.PI) / 180)

function lineLengthKm(c: Pt[]) {
  let L = 0
  for (let i = 1; i < c.length; i++) L += Math.hypot((c[i][0] - c[i - 1][0]) * kmLon(c[i][1]), (c[i][1] - c[i - 1][1]) * KM_LAT)
  return L
}

function pointAlong(c: Pt[], d: number): { p: Pt; angle: number } {
  let acc = 0
  for (let i = 1; i < c.length; i++) {
    const dx = (c[i][0] - c[i - 1][0]) * kmLon(c[i][1])
    const dy = (c[i][1] - c[i - 1][1]) * KM_LAT
    const seg = Math.hypot(dx, dy)
    if (acc + seg >= d || i === c.length - 1) {
      const k = seg ? Math.min(1, (d - acc) / seg) : 0
      let angle = (Math.atan2(dy, dx) * 180) / Math.PI
      if (Math.abs(angle) > 90) angle += 180
      return { p: [c[i - 1][0] + (c[i][0] - c[i - 1][0]) * k, c[i - 1][1] + (c[i][1] - c[i - 1][1]) * k], angle }
    }
    acc += seg
  }
  return { p: c.at(-1)!, angle: 0 }
}

export const kmLonAt = kmLon
export const KM_PER_LAT = KM_LAT

export function calculateLabels(features: Feature<LineString, { kv: number }>[], spacingKm: number): Label[] {
  const out: Label[] = []
  for (const f of features) {
    const text = `${f.properties.kv} kV`
    const base = f.properties.kv >= 345 ? 200 : 100
    for (const c of [f.geometry.coordinates]) {
      const L = lineLengthKm(c)
      let delta = L / 2
      let depth = 1
      while (delta > spacingKm) {
        for (let i = 1; i < 2 ** depth; i += 2) {
          const { p, angle } = pointAlong(c, i * delta)
          out.push({ position: p, angle, priority: base - depth, text })
        }
        depth++
        delta /= 2
      }
    }
  }
  return out
}
