---
name: ig-carousel-radar
version: "1.0"
created: 2026-05-29
last_reviewed: 2026-05-29
description: "Daily discovery viral IG-каруселей в EN рынке. Канон-бэкенд с этой редакции - Apify (radar_apify.py, аккаунт/IP владельца вне цепочки, без cookies); watchlist-режим главный, cookie-путь (Playwright+BYOA) депрекейт. Фильтр - type=carousel + recency < 7 days + likes >= threshold. Output - markdown digest в ~/Desktop/ig-digest/{date}.md + MANDATORY handoff финалистов в чат как нумерованные actionable варианты (approve/skip per item + downstream action) — НЕ закрывать на digest, НЕ говорить «готово/закрыт». Triggers - /radar, /carousel-radar, 'пройди по конкурентам IG', 'что виральное сегодня', daily cron 08:00. НЕ для Telegram-каналов и недельного снимка рынка - это konkurent-radar."
metadata:
  type: tool-wrapper
  artifact_type: action
  platform: instagram
  language: en-primary-ru-manual
  cost: zero
---

# IG Carousel Radar - daily viral IG carousel discovery

Утренний digest свежих виральных IG-каруселей в EN-нише + **mandatory handoff в чат для approve/skip per item**. автор не идёт в digest вручную — Claude приносит финалистов в чат как actionable список, автор approve по номерам, Claude triggers downstream skill (carousel / ingest-reel / save-to-bank) per approved item.

## Когда применять

Триггеры:
- `/radar`
- `/carousel-radar`
- "пройди по конкурентам IG"
- "что виральное сегодня"
- "ig digest"
- Daily cron 08:00 (auto через `schedule` skill)

НЕ применять:
- Если нужен анализ vertical video (Reels / TikTok / Shorts) → `competitors-daily-scan`
- Если нужен retroactive bulk скрап архива → `skraping-postov`
- Если нужен полный разбор одного поста → `ingest-reel`
- Если нужно создать carousel → `carousel`

## Что делает

3 mode параллельно за один прогон → merge → filter pipeline → digest.

| Mode | Source | Default volume |
|---|---|---|
| **A. Feed** | Logged-in IG feed timeline | 50 экранов scroll |
| **B. Watchlist** | Profile URLs из `watchlist-en.yml` | 10 постов / profile |
| **C. Hashtag** | `/explore/tags/{tag}` top + recent | 30 постов / tag |

Filter pipeline (после merge):
1. `type == carousel`
2. `age < 7 days`
3. `comments >= COMMENTS_THRESHOLD` (default 500, configurable)
4. Dedupe by post URL
5. **Topic-cluster classify** (zero-LLM keyword match по caption) → выкинуть `avoid`-формат, поднять `want`. Таксономия в `clusters-en.yml`
6. Sort: `want`-cluster first, затем comments DESC внутри тира

Output: `~/Desktop/ig-digest/{YYYY-MM-DD}.md` + опционально TG push.

## Workflow

## 🔴 БЭКЕНД-КАНОН с этой редакции: Apify, НЕ cookies

Основной бэкенд: `python3 .business/scripts/ig-fetch/radar_apify.py` (актор apify/instagram-scraper, токен `APIFY_TOKEN` в `~/.claude/.env`). Аккаунт и IP владельца ВНЕ цепочки - банов/checkpoint не бывает by design. Watchlist-режим (свежие посты хендлов из `watchlist-en.yml`) + фильтры recency/likes + дедуп против auto-uniqualize + те же кластеры `clusters-en.yml` (импортирует `scripts/cluster.py`). Cost ~$0.0023/пост, полный прогон ~$0.5. Флаги: `--handles a,b,c --limit 10 --recency 7 --min-likes 1000`.

Старый cookie-бэкенд `scripts/radar.py` (Playwright + `.ig-cookies.json`) = ДЕПРЕКЕЙТ после банов в даты запуска.2026. Только burner + явное «да» владельца (`IVAN_ALLOW_BURNER_IG=1`). Feed-режим жил только на cookies и в Apify-бэкенд не переносится; watchlist остаётся главным режимом, hashtag - позже.

См. `prompts/01-run-radar.md` - пошаговый алгоритм run (handoff-часть актуальна, discovery-часть - через Apify-бэкенд выше).
См. `prompts/03-tune-thresholds.md` - после первого прогона tune порогов.

Config: `config.md` (paths / discovery / filter / notification).
Seed lists: `~/.business/growth/watchlist-en.yml`, `~/.business/growth/hashtags-en.yml`.

## Core principles

1. **Discover + handoff** - skill discovers + MANDATORY handoff финалистов в чат как actionable нумерованный список с downstream options (adaptation / ingest-reel / carousel / save-to-bank). НЕ rewrites, НЕ publishes — но и НЕ обрывается на «digest opened». Approve flow закрывает gap до content factory.
2. **Zero AI cost** - Playwright + parse, без vision LLM, без OCR (фильтр темы через watchlist + hashtags на источнике).
3. **3 mode MECE** - feed / watchlist / hashtag покрывают весь surface IG discovery без пересечений по логике (URL dedupe закрывает физические пересечения).
4. **Two-layer relevance, both zero-LLM** - (a) source seed на входе (watchlist + hashtags = авторская курация ТЕМЫ); (b) topic-cluster keyword-classify на выходе (фильтр ФОРМАТА: want/avoid/neutral из `clusters-en.yml`). Keyword-match ≠ LLM → cost остаётся $0. Source-слой решает «про что», cluster-слой решает «какой формат берём».
5. **Slide-1 only** - thumb превью первого слайда. Полные carousels не качаем (cost / disk / out of scope).
6. **Headless / idempotent** - daily cron safe. При rerun одного и того же дня → перезаписывает digest.
7. **Configurable thresholds** - автор tune COMMENTS_THRESHOLD после первого прогона по реальной volume.
8. **EN only в v1** - RU = manual translate работающих карусели post-hoc.
9. **🔴 ТОЛЬКО НОВОЕ, не повторять сделанное (правило в даты запуска.2026)** - в handoff-шорт-лист несём ТОЛЬКО свежие карусели, которых автор ещё не делал. ЗАПРЕЩЕНО подсовывать уже выпущенные/старые карусели или повторять доноров/темы, что уже проходили. Перед выдачей финалистов - СВЕРИТЬ кандидатов с реестром сделанного (`~/.business/scripts/auto-uniqualize/used_codewords.md` + пакеты `~/Desktop/ig-carousel-slides-*` + доставленное в бот) и отфильтровать дубли донора/темы/shortcode. Прецедент в даты запуска: повтор сделанного = слив времени и доверия.

## Anti-patterns

- **OCR/vision LLM на slide content** - лишний cost, фильтр уже на входе через watchlist+hashtags
- **Скачивание полных слайдов всех carousels** - только slide-1 thumb
- **Image edit / publishing / rewrite** - out of scope, downstream workflow
- **Топик-классификация через LLM/vision** - формат-фильтр на выходе делается KEYWORD-match (substring/regex по caption), НЕ vision/LLM → cost $0. LLM-классификация запрещена (cost), keyword-кластеры — да
- **RU IG поддержка** - v1 only EN, RU manual после
- **Voice rewrite / brand adaptation** - другие skills
- **Hard-coded selectors без maintenance plan** - IG меняет HTML, нужен test + fallback в script
- **Закрывать run на «digest opened» без handoff в чат** - автор не пойдёт читать digest вручную, mandatory принести финалистов как actionable список с approve/skip per item + downstream skill choice

## 🔒 BYOA-гейт Instagram (ТОЛЬКО для депрекейт cookie-пути; Apify-канон куки не трогает)

Парс идёт за login-wall на cookies. Cookies должны быть ТВОИ (твоя IG-сессия), не автора курса. Поэтому ПЕРЕД тем как читать `~/.business/processes/.ig-cookies.json`:

```
1. python3 ~/.claude/skills/_shared/bin/account.py status instagram
2. если "missing" (файла куки нет / он пуст):
     - показать онбординг:  python3 ~/.claude/skills/_shared/bin/account.py onboard instagram
     - запустить интерактивный headed-login (он уже встроен):
         cd ~/.claude/skills/ig-carousel-radar && python3 scripts/setup.py
       откроется окно Chromium → ученик логинится в СВОЙ IG (вкл. 2FA) →
       скрипт сам сохранит ЕГО cookies в ~/.business/processes/.ig-cookies.json (chmod 600)
     - СТОП до завершения логина. НЕ продолжать парс без куки, НЕ падать.
3. только "connected" → дальше использовать ТВОИ cookies из ~/.business/processes/.ig-cookies.json
```

Канон гейта — `_shared/bring-your-own-account.md`. Cookies автора в дистрибутив не кладутся; ученик подключает свою сессию сам через этот шаг.

## Setup requirements (one-time, auto-bootstrap)

Запусти первый раз `python3 scripts/radar.py` - skill сам делегирует в `scripts/setup.py` если cookies / seeds отсутствуют:

1. **Seeds auto-bootstrap** - `watchlist-en.yml` + `hashtags-en.yml` создаются дефолтными значениями (ученик расширяет потом)
2. **IG cookies через headed Chromium login** - открывается Chromium → ученик логинится руками в СВОЙ IG (вкл. 2FA) → script сохраняет ЕГО cookies автоматически на landing
3. **Dry-run validation** - 1 sample per mode, проверка что parser работает
4. **Затем full run** → tune COMMENTS_THRESHOLD по результату

Cookie-Editor extension больше не нужен. BYOA-гейт выше + manual fallback и детали - в `prompts/02-setup-cookies.md`.

## Config

См. `config.md`. Portable - можно копировать skill + config в другой контекст.

## Cost

- Playwright headless Chromium: $0
- Compute на cron: ~2-5 минут CPU/day
- Disk: ~5MB/day (thumbs + digest)
- LLM: $0 (нет vision / OCR / rewrite)

## Memory cross-refs

- - не выдумывать метрики, парсить из IG
- - default config = safe (низкий volume scroll, не агрессивный rate)
- - E2E probe после первого setup (real run, не unit)
- - после run открыть digest командой ОС: `open <digest path>` (macOS) / `start "" "<digest path>"` (Windows) / `xdg-open <digest path>` (Linux), либо `~/.claude/skills/_shared/bin/open-file <digest path>`
- - digest format = plain markdown без таблиц
- - dash policy в digest
- - watchlist seed list через `.business/marketing/competitors.md`, не выдумывать handles

## Параллельные skills

- `competitors-daily-scan` - vertical video (Reels/TikTok/Shorts) discovery. Дополняет: Reels + IG carousels = полное покрытие IG-формата
- `skraping-postov` - retroactive bulk архив (90-365 дней). Разная задача (история vs daily fresh)
- `ingest-reel` - single URL deep ingest для replication. Downstream tool

## Maintenance

- **IG selectors fragile** - quarterly review `scripts/radar.py` + test prog один раз/месяц минимум
- **Cookie expiry** - IG sessions 1-3 месяца. Если script throws auth error - re-export
- **Anti-bot rate** - default 50 экранов scroll = ~10 минут. Если IG flags - reduce `feed_scroll_screens`
- **Watchlist drift** - quarterly review `watchlist-en.yml` (handles deactivate / pivot / drop quality)

## Версия

**1.1** (2026-06-12) - topic-cluster layer: zero-LLM keyword-классификатор формата на выходе (`clusters-en.yml`, want/avoid/neutral). Выкидывает avoid-формат (prompt-handout «забери промпт»), поднимает want (tool-onboarding, build-walkthrough). Дайджест: cluster-метка + breakdown + dropped-список (данные для прунинга watchlist). Зеркалится в threads-radar (shared `cluster.py`). Фидбэк автора: промпт-раздачи не цепляют, тестируем онбординг-форматы.

**1.0** (2026-05-29) - initial. 3 mode discovery + filter pipeline + markdown digest. EN only.

**Roadmap (не v1):**
- v1.1: TG push к Петрову chat если configured
- v1.2: RU mode (separate watchlist + hashtags + threshold)
- v1.3: Auto-tune COMMENTS_THRESHOLD от 7-day rolling median
- v2.0: Reels mode (merge с competitors-daily-scan если pattern идентичный)
