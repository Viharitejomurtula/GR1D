"""Fetch real transmission lines (HIFLD via ArcGIS) for the Texas Hill Country, add a data-center node,
solve a DC power flow on the real topology, and write public/data/grid.json.

Output: {lines: FeatureCollection<LineString> (props kv, owner, mw, mw_off, feeder?, synthetic?), substations: [{p, kv, deg}],
         dc: {p, mw}, stats: {...}}
`mw` is signed (positive flows from the first coordinate to the last); `mw_off` is the same after the data center\nhas dropped its 800 MW off the grid and generation has backed off.
The injections (where generation sits, how load is spread) are illustrative. The 100+ kV topology is real (HIFLD);
the 69 kV sub-transmission mesh (`synthetic: true`) is generated: each substation is tied to its nearest neighbours.
Usage: python3 scripts/build_grid_data.py   (needs numpy + scipy)
"""
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

SERVICE = "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0/query"
BBOX = "-100.5,28.6,-96.3,31.8"
OUT = Path(__file__).resolve().parent.parent / "public" / "data" / "grid.json"
CLASS_KV = {"100-161": 138, "220-287": 230, "345": 345, "500": 500, "735 AND ABOVE": 765, "UNDER 100": 69}
DC_MW = 800.0
CITY_LOAD_MW = 2600.0
CITIES = [(29.42, -98.49, 60), (30.27, -97.74, 50), (29.70, -98.12, 8), (29.88, -97.94, 6), (29.89, -97.94, 4), (30.50, -97.68, 6)]
GEN_SITES = [(30.3, -100.2), (28.75, -98.0), (29.5, -96.5), (30.9, -96.6), (31.55, -98.4)]  # west wind, south gas, coast, east, north
KM_LAT = 110.57


def km_lon(lat):
    return 111.32 * math.cos(math.radians(lat))


def dist_km(a, b):
    return math.hypot((a[0] - b[0]) * km_lon((a[1] + b[1]) / 2), (a[1] - b[1]) * KM_LAT)


def length_km(c):
    return sum(dist_km(c[i - 1], c[i]) for i in range(1, len(c)))


def fetch():
    q = urllib.parse.urlencode({
        "where": "1=1", "geometry": BBOX, "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "outFields": "ID,TYPE,STATUS,OWNER,VOLTAGE,VOLT_CLASS", "outSR": 4326, "f": "geojson",
    })
    for i in range(6):
        try:
            with urllib.request.urlopen(f"{SERVICE}?{q}", timeout=120) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i + 1, e)
            time.sleep(3)
    raise SystemExit("fetch failed")


def simplify(c, eps=0.0006):
    """Ramer-Douglas-Peucker in degrees (about 60 m): keeps lines light enough to animate."""
    if len(c) < 3:
        return c
    (x1, y1), (x2, y2) = c[0], c[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0.0, 0
    for i in range(1, len(c) - 1):
        d = abs(dy * c[i][0] - dx * c[i][1] + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            dmax, idx = d, i
    if dmax <= eps:
        return [c[0], c[-1]]
    return simplify(c[: idx + 1], eps)[:-1] + simplify(c[idx:], eps)


def tidy(s):
    return None if not s or s.upper() in ("NOT AVAILABLE", "UNKNOWN") else s.title()


def main():
    src = fetch()
    parts = []  # {kv, owner, coords}
    for f in src["features"]:
        p = f["properties"]
        kv = p["VOLTAGE"] if p["VOLTAGE"] and p["VOLTAGE"] > 0 else CLASS_KV.get(p["VOLT_CLASS"], 0)
        if kv < 100:
            continue
        g = f["geometry"]
        for part in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
            coords = [[round(x, 5), round(y, 5)] for x, y, *_ in part]
            coords = simplify(coords)
            if len(coords) > 1:
                parts.append({"kv": kv, "owner": tidy(p["OWNER"]), "coords": coords})

    # graph nodes: snapped endpoints
    snap = lambda c: (round(c[0], 3), round(c[1], 3))
    ids, pos, kvmax, deg = {}, [], [], []

    def node(c, kv):
        k = snap(c)
        if k not in ids:
            ids[k] = len(pos)
            pos.append(c)
            kvmax.append(0)
            deg.append(0)
        i = ids[k]
        kvmax[i] = max(kvmax[i], kv)
        deg[i] += 1
        return i

    edges = []  # (u, v, length_km, kv, feature index)
    for k, pt in enumerate(parts):
        u, v = node(pt["coords"][0], pt["kv"]), node(pt["coords"][-1], pt["kv"])
        edges.append((u, v, max(length_km(pt["coords"]), 0.5), pt["kv"], k))

    real_deg = list(deg)

    # synthetic 69 kV sub-transmission: tie every substation to its 3 nearest neighbours (kinked so lines overlap, not coincide)
    have = {(min(u, v), max(u, v)) for u, v, *_ in edges}
    synth = []  # (u, v, coords)
    for i in range(len(pos)):
        near_i = sorted((j for j in range(len(pos)) if j != i), key=lambda j: dist_km(pos[i], pos[j]))[:3]
        for j in near_i:
            key = (min(i, j), max(i, j))
            d = dist_km(pos[i], pos[j])
            if key in have or d > 40 or d < 1:
                continue
            have.add(key)
            a, b = pos[i], pos[j]
            bend = (0.12 if (i * 7 + j * 13) % 2 else -0.12) * (0.6 + ((i * 31 + j * 17) % 10) / 12)
            mid = [(a[0] + b[0]) / 2 - (b[1] - a[1]) * bend, (a[1] + b[1]) / 2 + (b[0] - a[0]) * bend]
            synth.append((i, j, [a, [round(mid[0], 5), round(mid[1], 5)], b]))
    for u, v, coords in synth:
        edges.append((u, v, max(length_km(coords), 0.5), 69, -2 - len(parts)))
        parts.append({"kv": 69, "owner": None, "coords": coords, "synthetic": True})
        edges[-1] = (u, v, edges[-1][2], 69, len(parts) - 1)

    # data center east of San Antonio, fed by the two nearest 345 kV substations
    hv = [i for i in range(len(pos)) if kvmax[i] >= 345]
    east = min(hv, key=lambda i: dist_km(pos[i], (-97.95, 29.40)))
    dc_pos = [round(pos[east][0] + 0.2, 5), round(pos[east][1] - 0.07, 5)]
    near = sorted(hv, key=lambda i: dist_km(pos[i], dc_pos))[:2]
    dc = len(pos)
    pos.append(dc_pos)
    kvmax.append(345)
    deg.append(2)
    feeders = []
    for i in near:
        edges.append((dc, i, max(dist_km(dc_pos, pos[i]), 0.5), 345, -1))
        feeders.append([dc_pos, pos[i]])

    n = len(pos)
    comp_n, label = connected_components(coo_matrix(([1] * len(edges), ([e[0] for e in edges], [e[1] for e in edges])), shape=(n, n)), directed=False)

    # injections: +gen / -load, balanced per connected component
    P = np.zeros(n)
    main_c = np.bincount(label).argmax()
    in_main = np.where(label == main_c)[0]
    w = np.array([0.3 + sum(pop * math.exp(-dist_km(pos[i], (cx, cy)) / 30) for cy, cx, pop in CITIES) for i in in_main])
    P[in_main] -= CITY_LOAD_MW * w / w.sum()
    P[dc] -= DC_MW
    gens = []
    for gy, gx in GEN_SITES:
        gens.append(min(in_main, key=lambda i: dist_km(pos[i], (gx, gy))))
    gens = list(dict.fromkeys(gens))
    P[gens] += -P[in_main].sum() / len(gens)
    for c in range(comp_n):
        if c == main_c:
            continue
        idx = np.where(label == c)[0]
        if len(idx) < 2:
            continue
        a, b = max(idx, key=lambda i: -pos[i][0]), max(idx, key=lambda i: pos[i][0])  # west gen, east load
        P[a] += 60
        P[b] -= 60

    # DC power flow per component. drop_dc=True solves the grid after the data center has left it (feeders removed).
    b_of = lambda e: (e[3] / 138) ** 2 / e[2]

    def solve_theta(P, drop_dc):
        theta = np.zeros(n)
        use = [e for e in edges if e[0] != e[1] and not (drop_dc and dc in (e[0], e[1]))]
        cn, lab = connected_components(coo_matrix(([1] * len(use), ([e[0] for e in use], [e[1] for e in use])), shape=(n, n)), directed=False)
        for c in range(cn):
            idx = np.where(lab == c)[0]
            if len(idx) < 2:
                continue
            loc = {g: k for k, g in enumerate(idx)}
            m = len(idx)
            rows, cols, vals = [], [], []
            for e in use:
                if lab[e[0]] != c:
                    continue
                a, b = loc[e[0]], loc[e[1]]
                sv = b_of(e)
                rows += [a, b, a, b]
                cols += [a, b, b, a]
                vals += [sv, sv, -sv, -sv]
            L = coo_matrix((vals, (rows, cols)), shape=(m, m)).tocsr()
            keep = np.arange(1, m)  # node 0 is the slack
            theta[idx[1:]] = spsolve(L[keep][:, keep].tocsc(), P[idx][keep])
        return theta

    theta = solve_theta(P, False)
    P_off = P.copy()
    P_off[dc] = 0
    P_off[gens] -= DC_MW / len(gens)  # generation backs off by the lost demand
    theta_off = solve_theta(P_off, True)

    feats = []
    for u, v, ln, kv, k in edges:
        mw = float(b_of((u, v, ln, kv, k)) * (theta[u] - theta[v])) if u != v else 0.0
        off_ = 0.0 if (u == dc or v == dc or u == v) else float(b_of((u, v, ln, kv, k)) * (theta_off[u] - theta_off[v]))
        if k >= 0:
            pt = parts[k]
            props = {"kv": kv, "owner": pt["owner"], "mw": round(mw, 1), "mw_off": round(off_, 1)}
            if pt.get("synthetic"):
                props["synthetic"] = True
            feats.append({"type": "Feature", "properties": props,
                          "geometry": {"type": "LineString", "coordinates": pt["coords"]}})
        else:  # DC feeder: u is the DC node, flow u->v is negative when power flows into the DC
            fe = feeders[len([f for f in feats if f["properties"].get("feeder")])]
            feats.append({"type": "Feature", "properties": {"kv": 345, "owner": None, "mw": round(mw, 1), "mw_off": 0.0, "feeder": True},
                          "geometry": {"type": "LineString", "coordinates": fe}})
    subs = [{"p": pos[i], "kv": kvmax[i], "deg": real_deg[i]} for i in range(n) if i != dc]
    subs.sort(key=lambda s: -s["kv"])
    mws = [abs(f["properties"]["mw"]) for f in feats]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"lines": {"type": "FeatureCollection", "features": feats}, "substations": subs, "dc": {"p": dc_pos, "mw": DC_MW},
               "stats": {"lines": len(feats), "main_component_nodes": int(len(in_main)), "components": int(comp_n), "max_mw": max(mws)}},
              open(OUT, "w"), separators=(",", ":"))
    print(f"{len(feats)} lines, {len(subs)} substations, {comp_n} components, max |flow| {max(mws):.0f} MW; "
          f"dc at {dc_pos}, feeders carry {[f['properties']['mw'] for f in feats if f['properties'].get('feeder')]} MW -> {OUT}")


main()
