# Platform specs

Технические specs платформ: длительности / aspects / captions / posting cadence.

Грузится в `workflow/02-finalize.md` и `workflow/06-output.md` для finalization decisions.

## Нельзяграм Reels (Instagram)

| Параметр | Значение |
|---|---|
| Min duration | 0 sec (фактический минимум - 1 sec) |
| Max duration | 90 sec (как Reel) / 15 min (как «Video» feed post) |
| Aspect ratio | 9:16 (vertical) primary; 1:1 OK; 16:9 NOT recommended |
| Resolution | 1080×1920 (vertical) |
| Frame rate | 30 fps standard; 60 fps OK |
| File format | MP4 H.264 |
| Captions | Hormozi-style word-by-word bold OR auto-captions Нельзяграм |
| Hook critical first | 1.5 sec |
| AI labeling | Required для AI-generated content (с 2024) |
| Posting time RU | 9:00-11:00 / 19:00-22:00 MSK |
| Posting time EN | 6:00-9:00 / 18:00-21:00 EST |
| Cadence | 1-3 per day для growth |

**Tier mapping:**
- short-15-30s: optimal для feed-based discovery
- short-30-60s: standard, highest engagement
- short-60-180s: longer storytelling, нижнее retention но higher saves

## YouTube Shorts

| Параметр | Значение |
|---|---|
| Min duration | 0 sec |
| Max duration | 60 sec (strict - иначе становится long-form) |
| Aspect ratio | 9:16 strict |
| Resolution | 1080×1920 |
| Frame rate | 30 fps standard |
| File format | MP4 H.264 |
| Captions | Auto-captions YouTube + optional burned-in Hormozi |
| Hook critical first | 1-3 sec |
| Title | up to 100 chars but short = better CTR |
| Description | up to 5000 chars but первые 100 chars важны |
| Cadence | 1-3 per day |
| AI labeling | Required для realistic AI content |
| Discovery | Through Shorts shelf + main feed |

**Tier mapping:**
- short-15-30s: best для virality (loop-friendly)
- short-30-60s: standard
- short-60-180s: NOT applicable (> 60s = becomes long-form)

## TikTok

| Параметр | Значение |
|---|---|
| Min duration | 0 sec |
| Max duration | 10 min (но практический cutoff 3 min для standard format) |
| Aspect ratio | 9:16 strict |
| Resolution | 1080×1920 |
| Frame rate | 30 fps standard; 60 fps OK |
| File format | MP4 H.264 |
| Captions | TikTok auto-captions + Hormozi burned-in |
| Hook critical first | 1.5-2 sec |
| Title (description) | up to 2200 chars |
| Cadence | 1-5 per day для growth |
| AI labeling | Required (since 2024) |
| Discovery | Through For You algorithm |

**Tier mapping:**
- short-15-30s: optimal
- short-30-60s: standard
- short-60-180s: longer storytelling, OK для TikTok (более tolerant к длине чем Reels)

## YouTube long-form

| Параметр | Значение |
|---|---|
| Min duration | 0 sec (но short-form < 60s = автоматически Shorts) |
| Max duration | 12h (но практический optimal 8-25 min для retention) |
| Aspect ratio | 16:9 standard (1920×1080) |
| Resolution | 1080p минимум, 4K если есть |
| Frame rate | 30 fps standard; 60 fps OK для tutorial |
| File format | MP4 H.264 |
| Captions | YouTube auto + optional .srt upload |
| Hook critical first | 15-30 sec |
| Title | 70 chars optimal (<60 = mobile preview не cuts) |
| Description | 5000 chars; первые 150 critical для SEO |
| Thumbnail | 1280×720 minimum, vibrant, face/text |
| Chapters | YouTube auto-detects from description timestamps |
| Cadence | 1-2 per week для quality long-form |

**Tier mapping:**
- mid-3-10min: standard YouTube mid-form
- long-10-60min: deep dives, courses, case studies

**Mini-hooks обязательны** каждые 60-90 sec для retention.

## Platform-tier compatibility (HARD GATE)

В `workflow/02-finalize.md` Шаг 3.5 - проверка совместимости. Reels / Shorts / TikTok НЕ принимают tier mid/long (кроме TikTok который теоретически до 10 min - но это уже out of автор scope).

| Tier | Reels | Shorts | TikTok | YouTube long |
|---|---|---|---|---|
| short-15-30s | ✓ | ✓ | ✓ | ✗ (slep up |
| short-30-60s | ✓ | ✓ | ✓ | ✗ |
| short-60-180s | ✓ | ✗ (> 60s) | ✓ | ✗ |
| mid-3-10min | ✗ | ✗ | * (technical OK, не стандарт) | ✓ |
| long-10-60min | ✗ | ✗ | ✗ | ✓ |

`*` - теоретически возможно но автор этим не пользуется (out of scope).

## Aspect ratio matrix

| Aspect | Платформы | Tier compatibility |
|---|---|---|
| 9:16 vertical | Reels / Shorts / TikTok | short tiers |
| 16:9 horizontal | YouTube long | mid / long tiers |
| 1:1 square | Reels (но не optimal) | short tiers |

## Caption style по платформе

| Платформа | Caption style |
|---|---|
| Reels | Hormozi-style word-by-word bold yellow/white outlined; auto-captions tail только |
| Shorts | Hormozi OR YouTube auto-captions (вкл в render) |
| TikTok | Hormozi OR TikTok auto-captions stylized |
| YouTube long | Audio-first, captions secondary (auto-captions + optional .srt) |

## Cross-distribution rules

Один script может публиковаться на нескольких платформах одновременно. Правила:

| From platform | To platform | Adaptation |
|---|---|---|
| Reels original | YouTube Shorts | Same file, change aspect check |
| Reels original | TikTok | Same file, тестировать через Uniqalizer (memory `feedback_multi_account_instagram_reality`) |
| YouTube long original | YouTube Shorts | Через `cut-from-long-form` (Reap MCP) extract 5-7 cuts |
| TikTok original | Reels | Same file через Uniqalizer |
| Any short | LinkedIn | Possible но low priority (LinkedIn = text > video) |

## Posting cadence автор (target 2026)

| Платформа | Daily target | Weekly target |
|---|---|---|
| Нельзяграм Reels | 2-3 | 14-21 |
| YouTube Shorts | 2-3 (cross-post) | 14-21 |
| TikTok | 2-3 (cross-post) | 14-21 |
| YouTube long | 0 | 1-2 per week |
| YouTube long → Shorts cuts | (auto от long-form) | 10-14 cuts/week |

## Maintenance

Platform specs меняются - review каждые 6 месяцев:
- Нельзяграм Reel max duration изменился несколько раз
- TikTok max length регулярно увеличивается
- YouTube Shorts duration cap может расширяться

## Cross-refs

- `references/structure-by-length.md` - tier definitions
- `references/production-handoff-map.md` - production specs по skill
- Memory `project_viral_hook_library_2026` - hook patterns по платформам