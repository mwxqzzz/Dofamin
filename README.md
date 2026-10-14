# Dofamin

Одностраничный сайт-концепт студии маникюра и педикюра Dofamin (Минск, ул. Кунцевщина, 31).

## Где что лежит

- `site/` — готовый сайт для любого статического хостинга: `index.html` и папка `img/`. Здесь кнопка «Интерактивная карта» подгружает карту Яндекса.
- `src/index.html` — исходник страницы (стили, разметка, скрипт).
- `tools/` — сборка:
  - `build_images.py` — сжимает фото из `assets/raw` в WebP (`site/img`);
  - `build_map.py` — рисует схему проезда по данным OpenStreetMap (`build/map.svg`);
  - `build_site.py` — собирает `site/index.html` и `build/dofamin.html` (версия для ссылки claude.ai).
- `assets/raw/` — исходные фото, отзывы и данные карты, скачанные workflow `.github/workflows/fetch-*.yml`.

Сборка из корня репозитория:

```
python3 tools/build_images.py
python3 tools/build_map.py build/map.svg
python3 tools/build_site.py
```

## Пометки «уточнить»

Всё, что нужно уточнить у владелицы, отмечено жёлтыми плашками с классом `todo` (найти: `class="todo"`). Кнопка «Пометки» у правого края экрана прячет и показывает их.
