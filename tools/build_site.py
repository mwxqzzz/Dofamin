"""Assembles the Dofamin one-page site from src/index.html.

Outputs:
  site/index.html      full HTML document for any static hosting (images in site/img)
  build/dofamin.html   the same page as a body fragment for the claude.ai artifact

Run from the repository root:  python3 tools/build_site.py
(build_images.py and build_map.py must have been run before.)
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

MASTER = {"marina": ("Марина", "Работа Марины"), "darya": ("Дарья", "Работа Дарьи"),
          "svetlana": ("Светлана", "Работа Светланы"), "natalya": ("Наталья", "Работа Натальи"),
          "studio": ("Мастер студии", "Работа мастеров студии")}
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
# calm, light works first; brighter ones further down
ORDER = ["darya-8", "svetlana-2", "studio-7", "marina-8", "studio-3", "darya-5", "studio-10", "marina-7",
         "darya-3", "svetlana-1", "studio-8", "natalya-1", "studio-4", "darya-1", "marina-5", "darya-4",
         "studio-5", "marina-4", "darya-2", "studio-1", "darya-6", "marina-1", "studio-2", "darya-7",
         "marina-2", "studio-6", "marina-3", "studio-9", "marina-6"]
assert sorted(ORDER) == sorted(ALT), set(ALT) ^ set(ORDER)


def who(name):
    return name.split("-")[0]


def photo_btn(name, cls, set_name, inner=""):
    m = who(name)
    cap = MASTER[m][1]
    return (f'<button class="{cls}" type="button" data-set="{set_name}" data-m="{m}" data-full="img/{name}.webp" '
            f'data-cap="{cap}"><img src="img/{name}-t.webp" alt="{ALT[name]}. {cap}" width="480" height="640" '
            f'loading="lazy" decoding="async">{inner}</button>')


works = "\n".join(photo_btn(n, "wk", "works", f'<span class="wk__who">{MASTER[who(n)][0]}</span>') for n in ORDER)


def master_photos(m):
    names = [n for n in ORDER if who(n) == m]
    shown, rest = names[:3], names[3:]
    tiles = [photo_btn(n, "mp", m) for n in shown]
    if rest:
        tiles.append(photo_btn(rest[0], "mp mp--more", m, f'<span class="mp__more">ещё {len(rest)}</span>'))
        tiles.append('<div hidden>' + "".join(photo_btn(n, "mp", m) for n in rest[1:]) + '</div>')
    for _ in range(max(0, 3 - len(shown))):
        tiles.append('<div class="mp mp--ph" aria-hidden="true"><svg viewBox="0 0 24 24"><use href="#i-cam"/></svg></div>')
    return f'<div class="mphotos">{"".join(tiles)}</div>'


src = (ROOT / "src" / "index.html").read_text()
repl = {"<!-- @WORKS -->": works, "<!-- @MAP -->": (ROOT / "build" / "map.svg").read_text(),
        **{f"<!-- @M_{m.upper()} -->": master_photos(m) for m in ("marina", "darya", "natalya", "svetlana")}}
for k, v in repl.items():
    assert k in src, k
    src = src.replace(k, v)
left = [m for m in re.findall(r"<!-- @[A-Z_]+ -->", src) if m != "<!-- @BODY -->"]
assert not left, left

head, body = src.split("<!-- @BODY -->")

# glue short words and units to the next word so they never hang at a line end
SHORT = r"(?:в|во|на|с|со|к|ко|а|и|но|не|о|об|от|по|у|за|из|до|для|без|при|про|или|да|же|ли|её|ее|вы|мы)"
UNITS = r"(?:BYN|м|мин|минут|недел[ьи]|отзыв\w*|оценок|мастер\w*|работ|час\w*|фото|дней|вопрос\w*|ногт\w*)"


def glue(text):
    for _ in range(2):
        text = re.sub(r"(^|[\s(«„>])(" + SHORT + r") (?=\S)", r"\1\2&nbsp;", text, flags=re.I)
        text = re.sub(r"(\d) (" + UNITS + r")(?=[\s,.:»<)]|$)", r"\1&nbsp;\2", text)
    return text


parts, skip = re.split(r"(<[^>]+>)", body), None
for i, part in enumerate(parts):
    if part.startswith("<"):
        tag = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
        name = tag.group(1).lower() if tag else ""
        if name in ("script", "style", "svg"):
            skip = None if part.startswith("</") else name
        continue
    if skip is None:
        parts[i] = glue(part)
body = "".join(parts)
(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "build" / "dofamin.html").write_text(head + body)
full = ('<!doctype html>\n<html lang="ru" data-embed="1">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
        + '</head>\n<body>\n' + body + '</body>\n</html>\n')
(ROOT / "site" / "index.html").write_text(full)

STUB = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Dofamin</title>
<style>body{{margin:0;padding:48px 20px;background:#F8F5F8;color:#2B2130;font:16px/1.6 system-ui,sans-serif}}main{{max-width:640px;margin:0 auto}}h1{{font-weight:500;font-size:28px;line-height:1.2}}a{{color:#8B3FA6;text-decoration:none}}</style>
</head><body><main><h1>{title}</h1><p>Студия маникюра и педикюра Dofamin, Минск, ул. Кунцевщина, 31</p>
<p>Текст документа готовится к запуску сайта. По вопросам обработки данных: +375 29 562-70-48, Instagram @dofamin.tut</p>
<p><a href="index.html">Вернуться на сайт</a></p></main></body></html>
"""
for fname, title in (("policy.html", "Политика конфиденциальности"), ("consent.html", "Согласие на обработку персональных данных")):
    (ROOT / "site" / fname).write_text(STUB.format(title=title))
print("built", len(full) // 1024, "KB", file=sys.stderr)
