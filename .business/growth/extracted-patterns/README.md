# Extracted patterns — empirical data layer

Создан 2026-05-28 как response на root cause finding: 10 content-skills семейства (post / longform / email / bot-message / video / carousel / single-image / paips-post / spiky-one-liner / tweet) генерили output на базе моей ТЕОРИИ виральности, а не extracted patterns из реального corpus.

Этот слой = единственный источник истины для всех content-skills. Skills должны ссылаться сюда, не зашивать свои hook patterns / structures / CTA forms.

## Что внутри

- `corpus-snapshot/raw-corpus-top30.md` — сырой dump 30 top-virality шортов в авторской нише (Greg Isenberg / Riley Brown / Sabrina Ramonov / Cleo Abram / etc.)
- `hook-patterns-empirical.md` — 9 реальных hook patterns с verbatim examples + virality data
- `body-structure-empirical.md` — walkthrough patterns, step distributions
- `cta-patterns-empirical.md` — 5 типов CTA с funnel mechanics
- `voice-markers-empirical.md` — verbatim phrases per creator (Greg / Riley / Sabrina)
- `authority-namedrop-pattern.md` — отдельный класс ссылок на authority как proof mechanic
- `funnel-awareness.md` — куда ведёт шорт + checklist для авторской воронки
- `visual-formats-empirical.md` — 4 visual format archetypes observed
- `audience-glossary.md` — agent-jargon → язык авторской ЦА (RU маркетологи)
- `benchmark-corpus-index.md` — index 30 шортов с metadata (views/likes/duration/tool stack/format)

## Источник corpus

`~/.business/growth/ingest/` — 104 ingested viral шорта (mainly 2026-05-23 to 2026-05-26 batch). Топ 30 by virality, exclusing brand-launches (Replit / Notion / Cursor / Lovable official) = 30 personal creator шортов.

Виральность calibrated by views from `info.json`. Range 15K-565K views. Likes range 421-32K.

## Maintenance

- Add new patterns когда новый виральный шорт ingested и passes virality threshold (>100K views)
- Re-extract раз в квартал
- При major shift в platform algorithm (Reels / Shorts / TikTok) — re-run pattern-extraction skill полностью

## Как используют content-skills

Каждый skill в семействе должен:

1. В Pass 0 Mandatory Reads — Read relevant files отсюда (минимум hook-patterns-empirical + voice-markers-empirical + audience-glossary)
2. В review stage — Benchmark Gate: сравнить output vs top-3 nearest patterns
3. При генерации новых вариаций — извлечь паттерн отсюда + apply voice rules автора

Без этого слоя skill = rule engine на моей теории.

## Cultural adaptation note

Corpus EN. авторская audience primary RU. Patterns переносятся (hook structures, body walkthroughs, CTA mechanics), но требуют cultural adaptation per `multi-language-localization` skill:
- Authority name-drops: «Anthropic CEO» → «Карпатый» / «Бенгио»
- Tool names: stay (Claude, Cursor, Lovable global brands)
- Numeric examples: $ → ₽ at 100x rough rate
- Idioms: «I'd bet my life on it» → «гарантирую» (понятная RU фраза)
