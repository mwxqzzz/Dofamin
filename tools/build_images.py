"""Converts raw photos from assets/raw into compressed WebP files in site/img."""
import pathlib
from PIL import Image

RAW, OUT = pathlib.Path("assets/raw"), pathlib.Path("site/img")
OUT.mkdir(parents=True, exist_ok=True)

# vertical centre of the nails (0..1) for photos that need a 3:4 crop
FOCUS_Y = {"marina-1": .6, "marina-2": .58, "marina-3": .55, "marina-4": .61, "marina-5": .45,
           "marina-6": .59, "marina-8": .42}
FOCUS_X = {"studio-10": .58, "darya-6": .5}
PHOTOS = ([f"marina-{i}" for i in range(1, 9)] + [f"darya-{i}" for i in range(1, 9)] +
          ["svetlana-1", "svetlana-2", "natalya-1"] + [f"studio-{i}" for i in range(1, 11)])

def crop34(im, fx=.5, fy=.5):
    w, h = im.size
    if w / h > .75:
        nw = round(h * .75); x = min(max(round(w * fx - nw / 2), 0), w - nw)
        return im.crop((x, 0, x + nw, h))
    nh = round(w / .75); y = min(max(round(h * fy - nh / 2), 0), h - nh)
    return im.crop((0, y, w, y + nh))


for name in PHOTOS:
    im = Image.open(RAW / f"{name}.jpg").convert("RGB")
    full = im.copy(); full.thumbnail((1080, 1080))
    full.save(OUT / f"{name}.webp", quality=80, method=6)
    t = crop34(im, FOCUS_X.get(name, .5), FOCUS_Y.get(name, .5)); t.thumbnail((480, 640))
    t.save(OUT / f"{name}-t.webp", quality=74, method=6)

cover = Image.open(RAW / "cover.jpg").convert("RGB"); cover.thumbnail((900, 1100))
cover.save(OUT / "entrance.webp", quality=78, method=6)

# logo: crop the wordmark and turn the black background into transparency
logo = Image.open(RAW / "logo.jpg").convert("RGB").crop((40, 322, 984, 700))
px = logo.load(); rgba = Image.new("RGBA", logo.size); out = rgba.load()
for y in range(logo.size[1]):
    for x in range(logo.size[0]):
        r, g, b = px[x, y]; a = max(r, g, b)
        out[x, y] = (0, 0, 0, 0) if a < 14 else (min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a), a)
rgba.thumbnail((480, 200))
rgba.save(OUT / "logo.webp", quality=90, method=6)
rgba.save(OUT / "logo.png", optimize=True)

# the same logo for light backgrounds: light parts become aubergine, violet parts stay violet
AUB, VIO = (0x2B, 0x21, 0x30), (0x8B, 0x3F, 0xA6)
light = Image.new("RGBA", logo.size); lo = light.load()
for y in range(logo.size[1]):
    for x in range(logo.size[0]):
        r, g, b = px[x, y]; mx, mn = max(r, g, b), min(r, g, b)
        if mx < 14:
            lo[x, y] = (0, 0, 0, 0); continue
        t = min(1, max(0, ((mx - mn) / mx - .12) * 2.2))
        lo[x, y] = tuple(round(AUB[i] + (VIO[i] - AUB[i]) * t) for i in range(3)) + (min(255, round(mx * 1.05)),)
light.thumbnail((480, 200))
light.save(OUT / "logo-light.webp", quality=90, method=6)
print("done", sum(f.stat().st_size for f in OUT.iterdir()) // 1024, "KB total")
