"""Runs on GitHub Actions: saves Yandex Maps reviews and map data for the Dofamin site."""
import json, pathlib, time, urllib.parse, urllib.request

OUT = pathlib.Path("assets/raw")
OUT.mkdir(parents=True, exist_ok=True)
ORG = "https://yandex.by/maps/org/dofamin/225603981549/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


# 1. Map data from OpenStreetMap (geocode + streets around the studio)
try:
    q = urllib.parse.quote("улица Кунцевщина 31, Минск")
    geo = json.loads(get(f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=3",
                         {"User-Agent": "dofamin-site-builder/1.0"}))
    (OUT / "geocode.json").write_text(json.dumps(geo, ensure_ascii=False, indent=1))
    lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
    bbox = f"{lat-0.011},{lon-0.019},{lat+0.011},{lon+0.019}"
    query = f"""[out:json][timeout:90];
(
  way["highway"]({bbox});
  way["building"]({bbox});
  way["leisure"~"park|garden|pitch|stadium|sports_centre"]({bbox});
  way["landuse"~"grass|forest|recreation_ground|meadow"]({bbox});
  way["natural"~"water|wood|scrub"]({bbox});
  way["railway"]({bbox});
  node["railway"="subway_entrance"]({bbox});
  node["station"="subway"]({bbox});
  node["highway"="bus_stop"]({bbox});
  node["public_transport"~"platform|stop_position"]({bbox});
);
out geom;"""
    data = get("https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query),
               {"User-Agent": "dofamin-site-builder/1.0"})
    (OUT / "osm.json").write_bytes(data)
except Exception as e:  # keep going, reviews matter more
    (OUT / "osm-error.txt").write_text(repr(e))

# 2. Raw HTML of the Yandex pages (may contain an embedded state with reviews)
for name, url in [("org.html", ORG), ("reviews.html", ORG + "reviews/")]:
    try:
        (OUT / name).write_bytes(get(url, {"Accept-Language": "ru-RU,ru;q=0.9"}))
    except Exception as e:
        (OUT / (name + ".error.txt")).write_text(repr(e))

# 3. Rendered reviews via a headless browser
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(locale="ru-RU", user_agent=UA, viewport={"width": 1280, "height": 1000})
    page.goto(ORG + "reviews/", wait_until="domcontentloaded", timeout=90000)
    time.sleep(8)
    page.screenshot(path=str(OUT / "reviews-shot-1.png"))
    for _ in range(25):
        page.evaluate("""() => {
          document.querySelectorAll('.scroll__container').forEach(s => s.scrollTop = s.scrollHeight);
          window.scrollTo(0, document.body.scrollHeight);
        }""")
        time.sleep(1.2)
    page.evaluate("""() => document.querySelectorAll(
        '.business-review-view__expand, .spoiler-view__button, [class*=expand]'
      ).forEach(e => { try { e.click() } catch (_) {} })""")
    time.sleep(2)
    reviews = page.evaluate("""() => [...document.querySelectorAll('.business-review-view')].map(r => ({
        author: (r.querySelector('.business-review-view__author-name, [itemprop=author] [itemprop=name]') || {}).innerText || '',
        date: (r.querySelector('.business-review-view__date') || {}).innerText || '',
        datePublished: (r.querySelector('meta[itemprop=datePublished]') || {}).content || '',
        rating: r.querySelectorAll('.business-rating-badge-view__stars ._full, .business-rating-badge-view__star._full').length,
        text: (r.querySelector('.business-review-view__body-text, .spoiler-view__text-container, [itemprop=reviewBody]') || {}).innerText || '',
        answer: (r.querySelector('.business-review-comment-content__bubble, .business-review-view__comment') || {}).innerText || ''
      }))""")
    (OUT / "reviews.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=1))
    (OUT / "reviews-page.txt").write_text(page.evaluate("() => document.body.innerText"))
    page.screenshot(path=str(OUT / "reviews-shot-2.png"))
    (OUT / "reviews-url.txt").write_text(page.url)
    b.close()
