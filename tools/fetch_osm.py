"""Runs on GitHub Actions: OpenStreetMap streets + walking routes around the studio."""
import json, pathlib, urllib.parse, urllib.request

OUT = pathlib.Path("assets/raw")
OUT.mkdir(parents=True, exist_ok=True)
LAT, LON = 53.914059, 27.433938  # Yandex Maps coordinates of the studio
UA = {"User-Agent": "dofamin-site-builder/1.0 (github.com/mwxqzzz/Dofamin)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def overpass(query, name):
    errors = []
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": query}).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            json.loads(data)
            (OUT / name).write_bytes(data)
            return json.loads(data)
        except Exception as e:
            errors.append(f"{ep}: {e!r}")
    (OUT / (name + ".error.txt")).write_text("\n".join(errors))
    return None


big = f"{LAT-0.013},{LON-0.022},{LAT+0.013},{LON+0.022}"
small = f"{LAT-0.007},{LON-0.012},{LAT+0.007},{LON+0.012}"
streets = overpass(f"""[out:json][timeout:170];
(
  way["highway"]({big});
  way["railway"]({big});
  way["leisure"~"park|garden|pitch|stadium|sports_centre"]({big});
  way["landuse"~"grass|forest|recreation_ground|meadow"]({big});
  way["natural"~"water|wood|scrub"]({big});
  node["railway"="subway_entrance"]({big});
  node["station"="subway"]({big});
  node["highway"="bus_stop"]({big});
  node["public_transport"="platform"]({big});
);
out geom;""", "osm.json")
overpass(f"""[out:json][timeout:170];
( way["building"]({small}); );
out geom;""", "osm-buildings.json")

# Walking routes from the metro and from the bus stop
if streets:
    pts = {}
    for el in streets["elements"]:
        if el["type"] != "node":
            continue
        name = el.get("tags", {}).get("name", "")
        if "Каменная Горка" in name or "Каменная горка" in name:
            pts.setdefault("metro", []).append(el)
        if "Кунцевщина" in name:
            pts.setdefault("stop", []).append(el)
    (OUT / "osm-points.json").write_text(json.dumps(pts, ensure_ascii=False, indent=1))
    routes = {}
    for key, nodes in pts.items():
        for i, n in enumerate(nodes[:6]):
            url = ("https://routing.openstreetmap.de/routed-foot/route/v1/foot/"
                   f"{n['lon']},{n['lat']};{LON},{LAT}?overview=full&geometries=geojson")
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    routes[f"{key}-{i}-{n['id']}"] = json.loads(r.read())
            except Exception as e:
                routes[f"{key}-{i}-{n['id']}"] = repr(e)
    (OUT / "osm-routes.json").write_text(json.dumps(routes, ensure_ascii=False))
