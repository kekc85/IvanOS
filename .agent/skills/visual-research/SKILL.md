---
name: visual-research
description: Find public photos of persons, events, and news topics for content production. Triggers - "найди фото X", "сделай скрин фаундера Y", "нужны фото конференции Z", "что вышло в новостях за неделю", "скрин конкурента N", "найди визуал для поста". Output - folder with Wikimedia hi-res original + Google Images variety grid + official site screenshots + README.md with source + license + suggested use per file. Three modes - person (CEO / founder / expert / competitor), event (conference / launch), news (topic + recency window). Public figures only — never children, private individuals, or non-consensual imagery.
version: 1.0
created: 2026-05-29
last_reviewed: 2026-05-29
---

# Visual Research — публичные фото персон, событий, новостей

Browser automation + open-source intelligence для контент-завода. Заменяет ad-hoc Playwright-сессии для поиска визуалов.

## Когда применять

Триггеры:
- "найди фото <персона>" / "сделай скриншоты <фаундера>"
- "нужны фото конференции <event>"
- "что вышло в новостях <topic> за <неделю/день>"
- "найди визуал для поста про <X>"
- "скрин конкурента <N>"
- "fetch press photos for <company>"
- "give me imagery of <person/event>"
- `/visual-research <query>`

Не применять для:
- Создания новой картинки (это `single-image` или `higgsfield-generate`)
- Анализа видео-рилов конкурентов (это `ingest-reel`)
- Daily-watch конкурентов (это `competitors-daily-scan`)
- Поиска текстовых материалов без visuals (use WebSearch directly)

## 3 режима

### Mode A: person — фото публичной персоны

См. [prompts/mode-a-person.md](prompts/mode-a-person.md).

Использовать когда нужны photos конкретного человека: CEO, фаундер, инфлюенсер, спикер, конкурент-автор, журналист.

Output:
- `<slug>-wikipedia.png` — page screenshot (full context)
- `<slug>-hires.jpg` — original из Wikimedia Commons (если есть)
- `<slug>-google-grid.png` — variety grid из Google Images
- `<slug>-official.png` — company About/Team page screenshot

### Mode B: event — фото события

См. [prompts/mode-b-event.md](prompts/mode-b-event.md).

Использовать когда нужны photos конференции, launch event, news event, релиза продукта.

Output:
- `<event-slug>-google-grid.png` — общая выдача
- `<event-slug>-official.png` — официальный сайт события
- Top-5 individual conference photos
- News coverage screenshots (TechCrunch / Verge)

### Mode C: news — новости + visuals по теме

См. [prompts/mode-c-news.md](prompts/mode-c-news.md).

Использовать для контент-плана: «что произошло в AI за неделю, нужны идеи для постов».

Output:
- `summary.md` — топ-N новостей + headline + source + suggested content angle
- Visuals per news item
- Готовый brief для `single-image` / `carousel` / `video` skills

## Workflow (core)

1. **Парсинг запроса** → mode (A/B/C) + query + recency window (если есть)
2. **Disambiguation** — если имя/событие неоднозначное, спросить контекст (компания, год)
3. **Source hierarchy walk** — см. [knowledge/source-hierarchy.md](knowledge/source-hierarchy.md). Wikipedia/Commons first, Google Images last.
4. **Public figure gate** — проверить что объект попадает под `[[public-figure-policy]]` (см. knowledge/)
5. **Browser actions** через Playwright MCP — navigate / take_screenshot / evaluate (для extracting image URLs)
6. **Hi-res download** через `curl` от Wikimedia Commons / press kit originals
7. **README.md write** — что найдено / source / license / suggested use
8. **Open folder** в Finder через `open` (per)

## Output structure

```
~/Desktop/visual-research/<query-slug>-<YYYY-MM-DD>/
├── README.md
├── <files>.{png,jpg}
```

Где `<query-slug>` — kebab-case (например `dario-amodei`, `anthropic-claude-launch`, `ai-news-week-22`).

README.md template — см. [knowledge/readme-template.md](knowledge/readme-template.md).

## Core principles

1. **Wikipedia/Commons first** — free, hi-res, canonical, licensed. Не ходить в Google Images если есть Wikipedia.
2. **License на каждый файл** — в README.md явная строка license per file (CC-BY-SA / Public Domain / Editorial fair use / Press kit only).
3. **Public figures only** — gate ДО любого browser action. Сомневаешься — стоп, спросить.
4. **Open original sources** — Google Images grid это preview для variety, для production брать с upstream (Wikimedia / press kit / official article).
5. **Date в имени папки** — для traceability (фото устаревают, ракурсы меняются).
6. **No captcha bypass / no login scraping** — только public access endpoints.
7. **Disambiguation explicit** — `John Smith` без контекста = stop. `John Smith CEO Acme` = OK.

## Anti-patterns

- Не сохранять private profile screenshots (Instagram private, LinkedIn behind login)
- Не fabricate license info — если не уверен, пометить `License: UNKNOWN — verify before use`
- Не предлагать фото детей public figures
- Не доставать leaked / hacked imagery
- Не выдавать Google Images результат как "оригинал" — это thumbnail, всегда искать source

## Safety policy

Полная политика — [knowledge/public-figure-policy.md](knowledge/public-figure-policy.md).

Short form:
- CEO / фаундеры (Dario Amodei, Sam Altman, etc) — OK
- Публичные спикеры на конференциях — OK
- Авторы-конкуренты (Riley Brown, Nate Herk, Chris Cordero etc) — OK
- Журналисты с public bylines — OK
- Public political figures — OK
- Дети public figures — NO
- Private individuals (даже если photo есть в интернете) — NO
- Non-consensual / leaked / hacked imagery — NO
- Medical / legal sensitive contexts — NO

## Memory cross-refs

- — Wikipedia/Commons/Google Images = free. Не путать с `higgsfield-generate` (paid generation).
- — финал: открыть `<folder>` командой ОС (`open` macOS / `start ""` Windows / `xdg-open` Linux, либо `~/.claude/skills/_shared/bin/open-file <folder>`)
- — license + source = только реальные, не выдумывать
- — этот skill питает контент-завод визуалами для replication

## Skill family interactions

| Skill | Когда туда | Чем отличается |
|---|---|---|
| `visual-research` (этот) | Найти фото публичной персоны / события / новости | Поиск + download существующих visuals |
| `single-image` | Создать новую картинку-пост | Generation новой картинки (часто использует `visual-research` output как референс) |
| `higgsfield-generate` | AI-генерация image/video | Paid AI generation |
| `ingest-reel` | Разобрать вертикальный рил конкурента | Видео-анализ, не photo поиск |
| `competitors-daily-scan` | Daily watchlist конкурентов | Watchlist mode, не ad-hoc query |
| `resyorch-nishi` | Исследовать рыночную нишу | Текстовый ресёрч ниши, не visuals |

## Version history

- **v1.0** (2026-05-29) — initial release. 3 mode (person / event / news). Wikipedia-first source hierarchy. Public figure policy gate. Born из ad-hoc Playwright-сессии поиска Dario Amodei founders 2026-05-28.