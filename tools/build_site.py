"""Assembles the Dofamin one-page site from src/index.html.

Outputs:
  site/index.html      full HTML document for any static hosting (images in site/img)
  build/dofamin.html   the same page as a body fragment for the claude.ai artifact

Run from the repository root:  python3 tools/build_site.py
(build_images.py and build_map.py must have been run before.)
"""
import json, math, pathlib, re, subprocess, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
G = json.load(open(TOOLS / "hero-glyphs.json"))
TOP, VB_H = -735, 750          # glyph box in font units (cap height 714 + overshoot)

# ---------------------------------------------------------------- hero word --

def offset_poly(pts, ts):
    n = len(pts); lines = []
    cx = sum(p[0] for p in pts) / n; cy = sum(p[1] for p in pts) / n
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        if (cx - (x1 + x2) / 2) * nx + (cy - (y1 + y2) / 2) * ny < 0:
            nx, ny = -nx, -ny
        lines.append(((x1 + nx * ts[i], y1 + ny * ts[i]), (dx, dy)))
    res = []
    for i in range(n):
        (p, d), (q, e) = lines[i - 1], lines[i]
        t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / (d[0] * e[1] - d[1] * e[0])
        res.append((p[0] + d[0] * t, p[1] + d[1] * t))
    return res


def hexagon_d(x0, x1, top, bot, thick=140, thin=40, inset=.2):
    """The "O" of the logo: a hexagon ring with thick sides and hairline top and bottom."""
    w = x1 - x0; ym = (top + bot) / 2
    outer = [(x0, ym), (x0 + w * inset, top), (x1 - w * inset, top), (x1, ym), (x1 - w * inset, bot), (x0 + w * inset, bot)]
    inner = offset_poly(outer, [thick, thin, thick, thick, thin, thick])
    f = lambda P: "M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in P) + "Z"
    return f(outer) + f(inner[::-1])


def glyph(ch):
    """Path of one letter in its own box: x 0..advance, y TOP..TOP+VB_H."""
    g = G["O" if ch == "O" else ch]
    if ch == "O":
        b = g["bounds"]
        return hexagon_d(b[0], g["adv"] - b[0], -b[3], -b[1]), g["adv"]
    return g["d"], g["adv"]


TRACK = 12
LETTER_PHOTO = {"D": "h-d", "O": "h-o", "F": "h-f", "A": "h-a", "M": "h-m", "I": "h-i", "N": "h-n"}
DEPTH = {"D": .9, "O": -.7, "F": 1.1, "A": -.5, "M": .8, "I": -.9, "N": .6}


def layout(word):
    x, out = 0, []
    for ch in word:
        d, adv = glyph(ch)
        out.append((ch, d, x, adv)); x += adv + TRACK
    return out, x - TRACK


def mask_uri(d, adv):
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 {TOP} {adv} {VB_H}' preserveAspectRatio='none'><path fill-rule='evenodd' d='{d}'/></svg>"
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe=" ='/:,.-")


def hero_word(word, cls, idx0=0):
    parts, W = layout(word)
    spans, outline = [], []
    for i, (ch, d, x, adv) in enumerate(parts):
        style = (f"left:{x / W * 100:.3f}%;width:{adv / W * 100:.3f}%;--i:{idx0 + i};"
                 f"--m:url(&quot;{mask_uri(d, adv)}&quot;)")
        spans.append(f'<span class="hw__l" style="{style}"><img src="img/{LETTER_PHOTO[ch]}.webp" alt="" '
                     f'data-depth="{DEPTH[ch]}" decoding="async" fetchpriority="high"></span>')
        outline.append(f'<path transform="translate({x} 0)" fill-rule="evenodd" d="{d}"/>')
    return (f'<div class="hw {cls}" style="aspect-ratio:{W}/{VB_H}" aria-hidden="true">{"".join(spans)}'
            f'<svg class="hw__outline" viewBox="0 {TOP} {W} {VB_H}" preserveAspectRatio="none">{"".join(outline)}</svg></div>'), W


def footer_word():
    parts, W = layout("DOFAMIN")
    gs = []
    for i, (ch, d, x, adv) in enumerate(parts):
        cls = ' class="fw__o"' if ch == "O" else ""
        gs.append(f'<g class="fw__l" data-i="{i}"><path{cls} transform="translate({x} 0)" fill-rule="evenodd" d="{d}"/></g>')
    return f'<svg class="fw" viewBox="-40 {TOP - 60} {W + 80} {VB_H + 120}" aria-hidden="true">{"".join(gs)}</svg>'


line_html, _ = hero_word("DOFAMIN", "hw--line")
dofa_html, w_dofa = hero_word("DOFA", "hw--top", 0)
min_html, w_min = hero_word("MIN", "hw--bottom", 4)
stack_html = (f'<div class="hw-stack" style="--min-w:{w_min / w_dofa * 100:.3f}%">{dofa_html}{min_html}</div>')

# ------------------------------------------------------------------ gallery --
MASTER = {"marina": ("Марина", "Работа Марины"), "darya": ("Дарья", "Работа Дарьи"),
          "svetlana": ("Светлана", "Работа Светланы"), "natalya": ("Наталья", "Работа Натальи"),
          "studio": ("Студия", "Работа мастеров студии")}
ALT = {
    "marina-1": "Красный маникюр на коротких ногтях, один ноготь зелёный",
    "marina-2": "Красный маникюр средней длины с одним белым ногтем",
    "marina-3": "Красный маникюр с серебристым акцентным ногтем",
    "marina-4": "Ярко-красный гель-лак на ногтях средней длины",
    "marina-5": "Красный глянцевый маникюр овальной формы",
    "marina-6": "Тёмно-красный маникюр с зелёным акцентом",
    "marina-7": "Чёрный маникюр с золотой сеткой и мраморным дизайном",
    "marina-8": "Нежно-розовые миндальные ногти с серебром на кончиках",
    "darya-1": "Длинные молочные ногти с объёмным декором: бантик и сердечко",
    "darya-2": "Длинное белое наращивание с градиентом",
    "darya-3": "Длинные квадратные ногти: розовый с блёстками и белый градиент",
    "darya-4": "Длинные молочные ногти с сердечками из страз",
    "darya-5": "Короткий маникюр в нюдовых оттенках: розовый, бежевый, белый",
    "darya-6": "Нюдовый маникюр с серебряным декором на одном ногте",
    "darya-7": "Нюдовый маникюр с серебристым дизайном на безымянном пальце",
    "darya-8": "Молочные миндальные ногти средней длины",
    "svetlana-1": "Френч с фиолетовым контуром и блёстками, квадратная форма",
    "svetlana-2": "Квадратные ногти с серебряным френчем и фиолетовой линией",
    "natalya-1": "Тёмный маникюр с эффектом кошачьего глаза на коротких ногтях",
    "studio-1": "Длинные квадратные ногти: чёрный с красным мраморным рисунком",
    "studio-2": "Разноцветный маникюр: розовый, чёрный матовый и коралловый",
    "studio-3": "Нюдовый френч с фиолетовой линией, квадратная форма",
    "studio-4": "Молочные ногти с дымчатым рисунком и серебряными линиями",
    "studio-5": "Серебряный глиттер и белые ногти с волнами",
    "studio-6": "Неоново-зелёный и чёрный маникюр с графичным дизайном",
    "studio-7": "Молочный маникюр с ручной росписью: розы на двух ногтях",
    "studio-8": "Нюдовый маникюр с росписью: синие васильки",
    "studio-9": "Красный гель-лак и красный тюльпан в руке",
    "studio-10": "Белые миндальные ногти, два с крапинками",
}
ORDER = ["marina-7", "darya-3", "svetlana-2", "studio-7", "darya-1", "marina-8", "studio-1", "natalya-1",
         "studio-8", "darya-4", "marina-5", "svetlana-1", "studio-4", "darya-8", "studio-10", "marina-1",
         "darya-2", "studio-3", "studio-5", "marina-4", "darya-5", "studio-2", "marina-2", "darya-6",
         "studio-6", "marina-3", "darya-7", "studio-9", "marina-6"]
assert sorted(ORDER) == sorted(ALT), set(ALT) ^ set(ORDER)


def photo_btn(name, cls, set_name, extra=""):
    m = name.split("-")[0]
    who, cap = MASTER[m]
    return (f'<button class="{cls}" type="button" data-set="{set_name}" data-m="{m}" data-full="img/{name}.webp" '
            f'data-cap="{cap}"{extra}><img src="img/{name}-t.webp" alt="{ALT[name]}. {cap}" width="480" height="640" '
            f'loading="lazy" decoding="async"></button>')


works = "\n".join(photo_btn(n, "wk", "works", f' data-who="{MASTER[n.split("-")[0]][0]}"') for n in ORDER)


def fan(names, set_name, empty=0):
    items = [photo_btn(n, "fan__p", set_name) for n in names]
    items += ['<div class="fan__p fan__p--ph" aria-hidden="true"><span class="todo">уточнить: фото работ</span></div>'] * empty
    items = [it.replace(' class="fan__p', f' style="--i:{i}" class="fan__p', 1) for i, it in enumerate(items)]
    return f'<div class="fan" style="--n:{len(items)}">{"".join(items)}</div>'


FANS = {
    "marina": fan(["marina-7", "marina-8", "marina-5", "marina-1"], "marina"),
    "darya": fan(["darya-1", "darya-3", "darya-4", "darya-8"], "darya"),
    "natalya": fan(["natalya-1"], "natalya", 2),
    "svetlana": fan(["svetlana-2", "svetlana-1"], "svetlana", 1),
}
# hidden members of each master's set, so the lightbox shows all of her photos
MORE = {
    "marina": ["marina-4", "marina-2", "marina-3", "marina-6"],
    "darya": ["darya-2", "darya-5", "darya-6", "darya-7"],
}
for m, names in MORE.items():
    FANS[m] += '<div hidden>' + "".join(photo_btn(n, "fan__more", m) for n in names) + "</div>"

# ---------------------------------------------------------------- assemble --
src = (ROOT / "src" / "index.html").read_text()
map_svg = (ROOT / "build" / "map.svg").read_text()
repl = {
    "<!-- @HERO_LINE -->": line_html, "<!-- @HERO_STACK -->": stack_html, "<!-- @WORKS -->": works,
    "<!-- @MAP -->": map_svg, "<!-- @FOOTER_WORD -->": footer_word(),
    **{f"<!-- @FAN_{k.upper()} -->": v for k, v in FANS.items()},
}
for k, v in repl.items():
    assert k in src, k
    src = src.replace(k, v)
left = [m for m in re.findall(r"<!-- @[A-Z_]+ -->", src) if m != "<!-- @BODY -->"]
assert not left, left

head, body = src.split("<!-- @BODY -->")
(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "build" / "dofamin.html").write_text(head + body)
full = ('<!doctype html>\n<html lang="ru" data-embed="1">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
        + '</head>\n<body>\n' + body + '</body>\n</html>\n')
(ROOT / "site" / "index.html").write_text(full)
print("built", len(full) // 1024, "KB", file=sys.stderr)
