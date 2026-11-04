"""Builds the stylised contacts map (inline SVG) from OpenStreetMap data in assets/raw."""
import heapq, json, math, pathlib, sys

RAW = pathlib.Path("assets/raw")
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/map.svg")
STUDIO = (53.914059, 27.433938)
METRO_ENTRANCE = 263061831       # nearest entrance of «Каменная Горка»
BUS_STOP = 340775855              # «ДС Кунцевщина»
STUDIO_BUILDING = 74095466
LAT0, LAT1, LON0, LON1 = 53.9056, 53.9184, 27.4272, 27.4428
W = 600
KX = math.cos(math.radians((LAT0 + LAT1) / 2))
H = round(W * (LAT1 - LAT0) / ((LON1 - LON0) * KX))


def xy(lat, lon):
    return ((lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H)


def inside(lat, lon, m=0.002):
    return LAT0 - m < lat < LAT1 + m and LON0 - m < lon < LON1 + m


def meters(a, b):
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * KX)


osm = json.load(open(RAW / "osm.json"))["elements"]
bld = json.load(open(RAW / "osm-buildings.json"))["elements"]
nodes = {e["id"]: e for e in osm if e["type"] == "node"}

# --- walking graph -----------------------------------------------------------
graph = {}
walkable = {"footway", "path", "steps", "pedestrian", "service", "residential", "living_street",
            "unclassified", "tertiary", "secondary", "primary", "crossing", "cycleway", "track"}
for e in osm:
    if e["type"] != "way" or e.get("tags", {}).get("highway") not in walkable:
        continue
    pts = [(p["lat"], p["lon"]) for p in e["geometry"]]
    for a, b in zip(pts, pts[1:]):
        d = meters(a, b)
        graph.setdefault(a, []).append((b, d))
        graph.setdefault(b, []).append((a, d))


def nearest(pt):
    return min(graph, key=lambda q: meters(q, pt))


def route(src, dst):
    s, t = nearest(src), nearest(dst)
    dist, prev, pq = {s: 0}, {}, [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t:
            break
        if d > dist[u]:
            continue
        for v, w in graph[u]:
            if d + w < dist.get(v, 1e18):
                dist[v], prev[v] = d + w, u
                heapq.heappush(pq, (d + w, v))
    path, u = [t], t
    while u != s:
        u = prev[u]
        path.append(u)
    return [src] + path[::-1] + [dst], dist[t]


studio_door = STUDIO
metro = (nodes[METRO_ENTRANCE]["lat"], nodes[METRO_ENTRANCE]["lon"])
stop = (nodes[BUS_STOP]["lat"], nodes[BUS_STOP]["lon"])
r_metro, d_metro = route(metro, studio_door)
r_stop, d_stop = route(stop, studio_door)
print(f"metro route {d_metro:.0f} m, stop route {d_stop:.0f} m", file=sys.stderr)


def path_d(pts, close=False):
    s = "M" + " L".join("%.1f %.1f" % xy(*p) for p in pts)
    return s + ("Z" if close else "")


# --- layers ------------------------------------------------------------------
green, water, roads, minor, rail, labels = [], [], {}, [], [], {}
for e in osm:
    if e["type"] != "way":
        continue
    t = e.get("tags", {})
    pts = [(p["lat"], p["lon"]) for p in e["geometry"]]
    if not any(inside(*p) for p in pts):
        continue
    hw = t.get("highway")
    if t.get("leisure") or t.get("landuse") or t.get("natural") in ("wood", "scrub"):
        if pts[0] == pts[-1]:
            green.append(path_d(pts, True))
    elif t.get("natural") == "water":
        water.append(path_d(pts, True))
    elif hw in ("trunk", "primary", "secondary", "tertiary", "trunk_link", "primary_link", "secondary_link"):
        roads.setdefault("major", []).append(path_d(pts))
    elif hw in ("residential", "unclassified", "living_street", "pedestrian"):
        roads.setdefault("street", []).append(path_d(pts))
    elif hw == "service":
        minor.append(path_d(pts))
    if hw and t.get("name") and hw not in ("footway", "service", "path"):
        name = t.get("name:ru") or t["name"]
        labels.setdefault(name, []).append(pts)

buildings, studio_b = [], None
for e in bld:
    pts = [(p["lat"], p["lon"]) for p in e.get("geometry", [])]
    if len(pts) < 3 or not any(inside(*p, 0) for p in pts):
        continue
    if e["id"] == STUDIO_BUILDING:
        studio_b = path_d(pts, True)
    else:
        buildings.append(path_d(pts, True))

# street labels: middle of the longest way of each named street
SHORT = {"улица Кунцевщина": "ул. Кунцевщина", "улица Матусевича": "ул. Матусевича",
         "улица Колесникова": "ул. Колесникова", "Казимировская улица": "Казимировская ул.",
         "Нёманская улица": "Нёманская ул.", "улица Притыцкого": "ул. Притыцкого",
         "Каменногорская улица": "Каменногорская ул.", "улица Лещинского": "ул. Лещинского"}
label_svg = []
for name, ways in labels.items():
    if name not in SHORT:
        continue
    segs = [(a, b) for w in ways for a, b in zip(w, w[1:])
            if 40 < (xy(*a)[0] + xy(*b)[0]) / 2 < W - 40 and 40 < (xy(*a)[1] + xy(*b)[1]) / 2 < H - 40]
    if not segs:
        continue
    a, b = max(segs, key=lambda s: meters(*s))
    if meters(a, b) < 90:
        continue
    (x1, y1), (x2, y2) = xy(*a), xy(*b)
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    label_svg.append(f'<text class="m-street" transform="translate({(x1+x2)/2:.0f} {(y1+y2)/2:.0f}) rotate({ang:.0f})" dy="-6">{SHORT[name]}</text>')

mx, my = xy(*metro); sx, sy = xy(*stop); px, py = xy(*STUDIO)
svg = f'''<svg class="map-svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="map-title">
<title id="map-title">Схема проезда: студия Dofamin на улице Кунцевщина, 31, пешком от станции метро «Каменная Горка» и от остановки «ДС Кунцевщина»</title>
<rect width="{W}" height="{H}" class="m-bg"/>
<g class="m-green">{"".join(f'<path d="{d}"/>' for d in green)}</g>
<g class="m-bld">{"".join(f'<path d="{d}"/>' for d in buildings)}</g>
<g class="m-minor">{"".join(f'<path d="{d}"/>' for d in minor)}</g>
<g class="m-street-line">{"".join(f'<path d="{d}"/>' for d in roads.get("street", []))}</g>
<g class="m-major">{"".join(f'<path d="{d}"/>' for d in roads.get("major", []))}</g>
{"".join(label_svg)}
<path class="m-route" d="{path_d(r_metro)}"/>
<path class="m-route m-route--stop" d="{path_d(r_stop)}"/>
{f'<path class="m-studio-b" d="{studio_b}"/>' if studio_b else ''}
<g class="m-metro" transform="translate({mx:.0f} {my:.0f})"><circle r="15"/><text dy="5">М</text></g>
<text class="m-label" x="{mx+22:.0f}" y="{my+5:.0f}">Каменная Горка</text>
<g class="m-stop" transform="translate({sx:.0f} {sy:.0f})"><rect x="-8" y="-8" width="16" height="16" rx="3"/></g>
<text class="m-label" x="{sx+16:.0f}" y="{sy+5:.0f}">ДС Кунцевщина</text>
<g class="m-pin" transform="translate({px:.0f} {py:.0f})"><path d="M-17 0 L-8.5 -15 L8.5 -15 L17 0 L8.5 15 L-8.5 15Z"/><path class="m-pin-in" d="M-8 0 L-4 -7 L4 -7 L8 0 L4 7 L-4 7Z"/></g>
<text class="m-label m-label--studio" x="{px-26:.0f}" y="{py+5:.0f}" text-anchor="end">Dofamin</text>
</svg>'''
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg)
print(f"{OUT}: {len(svg)//1024} KB, {W}x{H}", file=sys.stderr)
