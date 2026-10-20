# Source Hierarchy для visual-research

Приоритет источников при поиске визуалов. Всегда идти сверху вниз — не лезть в Google Images если Wikipedia покрывает запрос.

## Tier 1 — Wikimedia ecosystem (canonical, free, hi-res)

**Wikipedia** — `en.wikipedia.org/wiki/<Person>` или `<Event>`.
- Plus: контекст + infobox photo + cross-refs
- Screenshot всей страницы как `<slug>-wikipedia.png`

**Wikimedia Commons** — `commons.wikimedia.org`.
- Источник оригинала из Wikipedia infobox
- Hi-res, явная лицензия (CC-BY / CC-BY-SA / Public Domain / GFDL)
- Download через `curl` с прямого URL (snip `/thumb/` сегмент)

**Как извлечь original из thumbnail URL:**
```
thumbnail:  /wikipedia/commons/thumb/e/e4/Dario_Amodei_at_TechCrunch_Disrupt_2023_01_(cropped).jpg/250px-...jpg
original:   /wikipedia/commons/e/e4/Dario_Amodei_at_TechCrunch_Disrupt_2023_01_(cropped).jpg
```
Удалить `/thumb/` сегмент и `/Npx-...` суффикс.

## Tier 2 — Official press kits

Прямые pressroom-страницы:
- `anthropic.com/news` / `anthropic.com/company`
- `openai.com/news` / `openai.com/about`
- `deepmind.google/press`
- `<company>.com/press` / `<company>.com/newsroom`
- `<company>.com/media-kit`

Plus: editorial-grade фото, явный consent for press use.
Minus: ограничения «editorial use only» — нельзя в paid ads.

## Tier 3 — Official About/Team pages

`<company>.com/about` / `<company>.com/team` / `<company>.com/people`.

Plus: текущие фото, актуальная роль
Minus: часто identical с press kit; иногда low-res

## Tier 4 — Conference / event official sites

Для event mode:
- `techcrunch.com/events/disrupt-<year>`
- `web.summit.com/<year>`
- `<conference>.org/<year>/gallery`
- YouTube channel конференции (для скриншотов выступлений)

## Tier 5 — News coverage (TechCrunch / Verge / Bloomberg)

Для context + event coverage:
- `techcrunch.com/<topic>`
- `theverge.com/<topic>`
- `bloomberg.com/news/<topic>`
- `reuters.com/<topic>`
- `wired.com/<topic>`

Plus: editorial photos с подписями и датами
Minus: paywall у Bloomberg/WSJ

## Tier 6 — Google Images (variety + recency)

Когда использовать:
- Нужны разные ракурсы (для variety grid)
- Wikipedia photo устарел (>2 лет)
- Persona не в Wikipedia
- Event recent (нет в press kit yet)

URL: `https://www.google.com/search?q=<query>&tbm=isch`

⚠️ Google Images результаты — это thumbnails. Для production брать с upstream через клик на оригинал.

## Tier 7 — Twitter/X public posts

Когда:
- Свежие события сегодня/вчера
- Авторские посты конкурентов (Riley Brown, Nate Herk и т.д.) с self-portrait
- Live event coverage

URL: `https://twitter.com/search?q=<query>&f=image`

⚠️ Только public posts. Не trying to access logged-in views.

## Tier 8 — LinkedIn (последний resort)

Когда:
- Professional headshot нужен
- Persona only на LinkedIn (нет Wikipedia / Twitter / press kit)

⚠️ Login wall на большинстве страниц. Использовать только если профиль публичный.

## Decision tree

```
person?
├─ есть в Wikipedia → Tier 1 + Tier 6 для variety
├─ есть в company press kit → Tier 2 + Tier 6 для variety
├─ нет в #1/#2 → Tier 6 (Google) + Tier 7 (Twitter)
└─ только LinkedIn → Tier 8 (warn user: limited results)

event?
├─ recurring (TechCrunch Disrupt, Web Summit) → Tier 4 + Tier 5
├─ launch event (Anthropic Claude launch) → Tier 2 + Tier 5
├─ news event → Tier 5 + Tier 6
└─ live ongoing → Tier 7

news topic?
└─ Tier 5 → собрать топ-N headlines + visuals per item
```

## Anti-patterns

- Не начинать с Google Images если Wikipedia покрывает (free + hi-res лучше)
- Не отдавать thumbnail URL как "оригинал" — расширять до full-res
- Не использовать Pinterest как primary source (часто re-uploads без attribution)
- Не использовать GettyImages / Shutterstock как source (paid licensing требуется)