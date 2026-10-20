# Reference - Platform Specs

> Спецификация форматирования / длины / headline / subject / canonical для 4 поддерживаемых платформ. Loaded в `02-structure.md` Step 6 и `05-publish.md` Step 3.

## Сводка

| Platform | Длина | Headline strategy | Subject A/B | Preheader | Canonical role | Format |
|---|---|---|---|---|---|---|
| Personal blog | 1200-3000 | SEO H1 (60-70 chars) | - | - | Primary POSSE | Markdown / HTML |
| Newsletter (Kit) | 1000-2200 | Subject A/B (40-60 chars) | 3 варианта | 90-100 chars | Может быть canonical (если нет своего блога) | Kit-blocks HTML |
| Newsletter (Beehiiv) | 1000-2200 | Subject A/B (40-60 chars) | 3 варианта | 90-100 chars | Может быть canonical | Beehiiv blocks |
| LinkedIn article | 800-1800 | LinkedIn-friendly (90-110 chars) | - | - | Distribution wedge | LinkedIn editor plain text + bold |

---

## Personal Blog (canonical primary)

**URL pattern:** `<blog-url>/blog/<slug>` или `<blog-url>/posts/<slug>`

**Length floor:** 1200 слов
**Length ceiling:** 3000 слов
**Default target:** 1800 слов

**Headline:** SEO-friendly H1
- Длина: 60-70 chars
- Включает primary keyword
- Curiosity gap но без clickbait

**Body format:** Markdown с frontmatter
```markdown
---
title: "<headline>"
slug: "<slug>"
date: <YYYY-MM-DD>
language: "<ru | en>"
type: "<teaching | story | framework>"
canonical: true
description: "<150-160 chars для SEO meta>"
---
```

**Structure:** H1 → INTRODUCTION → H2 INSIGHT → optional H3 для подразделов → H2 PROCESS → CTA.

**Images:** опционально 1 hero image сверху, 1-2 inline для INSIGHT examples.

**Canonical:** rel="canonical" на cross-post targets ссылается СЮДА.

---

## Newsletter - Kit (ConvertKit)

**Provider focus:** tag automations + landing pages + product launches. Better для funnel-driven setups.

**Length floor:** 1000 слов
**Length ceiling:** 2200 слов
**Default target:** 1500 слов

**Subject lines (3 варианта):**
- 40-60 chars каждая
- Patterns:
  - Curiosity: «<тема>: одна штука которую я раньше не замечал»
  - Personal: «как я поменял <thing> и не пожалел»
  - Specific outcome: «$<N>/мес от одной правки - вот что было»
- Гипотезы для A/B каждой: что тестируется

**Preheader:** 90-100 chars. Дополняет subject, не повторяет.

**Body format:** Kit HTML с inline styles. Структурные блоки:
- Заголовок H1
- Paragraph blocks
- Quote blocks для main_aha
- CTA button (link to canonical если есть свой blog, или к продукту / клубу)
- Footer с unsubscribe link

**Tag automations:**
- Subscribers получают tag на основе кликов (next steps)
- Если есть segmented audience → разные CTA блоки

**Distribution:** Kit primary delivery, cross-post в blog (если есть) с rel="canonical" → newsletter primary.

---

## Newsletter - Beehiiv

**Provider focus:** ad network monetization + paid subscriptions + recommendations network. Better для journalists / news-driven creators.

**Length floor:** 1000 слов
**Length ceiling:** 2200 слов
**Default target:** 1500 слов

**Subject lines (3 варианта):** same as Kit.

**Preheader:** 90-100 chars.

**Body format:** Beehiiv editor blocks:
- text-block
- quote-block
- divider
- image-block
- cta-button (Beehiiv-native)
- recommendation-block (если используются recommendations)

**Beehiiv-specific:**
- **Recommendations** на bottom - другие newsletter'ы (rev share при подписке)
- **Boosts** - paid subscriptions через Beehiiv ad network
- **Polls** - embedded survey blocks

**Distribution:** Beehiiv primary delivery, cross-post в blog с rel="canonical" → newsletter primary.

---

## LinkedIn article (distribution wedge)

**URL pattern:** `linkedin.com/pulse/<slug>` или `linkedin.com/in/<profile>/recent-activity/articles`

**Length floor:** 800 слов
**Length ceiling:** 1800 слов
**Default target:** 1300 слов

**Headline strategy:** different_from_blog
- LinkedIn audience ≠ blog audience (B2B-биас, longer attention)
- 90-110 chars
- Pattern: «I <did X> for <time>. Here's what <surprising outcome>.»
- Avoid SEO keywords - LinkedIn algorithm не SEO-based

**Body format:** LinkedIn editor
- Plain text с line breaks
- Bold для подзаголовков (НЕ H2/H3 - LinkedIn editor их не уважает)
- Короткие абзацы (1-3 строки максимум) - mobile reader friendly
- Без images inline (LinkedIn ограничивает rich media в article body)
- 1 hero image сверху (Cover image)

**Structure for LinkedIn:**
```
<Hook line - 1 строка>

<Setup - 2-3 короткие абзаца>

**<Bold subheader для INSIGHT>**

<Insight body - короткие абзацы>

**<Bold subheader для PROCESS>**

<Process body>

---

<CTA: Follow / Comment / DM>
```

**Canonical:** rel="canonical" → blog (если есть свой blog). LinkedIn НЕ канонический, чтобы Google не индексировал LinkedIn url выше своего сайта.

**Distribution:**
- Cross-post 24-72 часа ПОСЛЕ canonical (даёт Google time to crawl canonical first)
- Не ranking signal - LinkedIn закрытая система
- Поднимает algorithm в LinkedIn feed на 2-3 дня

---

## Substack / Medium (cross-post targets)

**Substack:**
- Import markdown через editor
- Sub-newsletter с paid tier option
- Notes (short-form Twitter-like) - separate flow
- rel="canonical" → blog (если есть)

**Medium:**
- Import markdown через editor
- Membership program - read-time bonuses
- rel="canonical" → blog (если есть)
- Boost через publications если есть

---

## Bilingual considerations

Если `bilingual_mode = mirror` - оба language versions имеют свои canonical URLs:
- RU canonical: `<blog>/blog/<slug-ru>` или `<blog>/blog/ru/<slug>`
- EN canonical: `<blog>/blog/<slug-en>` или `<blog>/blog/en/<slug>`
- Hreflang tags для SEO

Если `bilingual_mode = ru_canonical` или `en_canonical` - один canonical, второй язык как translation cross-post с rel="canonical" → primary language version.

---

## Memory cross-refs

- - Beehiiv ad network vs Kit tag automations
- - RU и EN разные направления
- - дословно vs переписать
- - 4 core channels включают newsletter + LinkedIn