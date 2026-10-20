# 05-publish - POSSE distribution map + A/B subject + derivatives plan

> Принимает APPROVED draft из `04-review.md`. Производит финальный output: canonical version + cross-post versions + distribution checklist + A/B subject lines + derivatives plan.

## Step 1 - определить canonical

Из `config.platforms.canonical.type` определяется куда идёт canonical version:

| Canonical type | Canonical URL pattern | Format |
|---|---|---|
| personal_blog | `<url>/blog/<slug>` | Markdown / HTML |
| newsletter (Kit) | `<url>/posts/<slug>` | Kit-blocks HTML |
| newsletter (Beehiiv) | `<url>/p/<slug>` | Beehiiv-blocks HTML |
| newsletter (Substack) | `<url>/p/<slug>` | Substack rich text |
| linkedin | `linkedin.com/pulse/<slug>` | LinkedIn editor format |

## Step 2 - slug generation

Slug = transliterated kebab-case headline (RU → translit, EN → kebab).

```
"Как контент-завод заменил мне отдел маркетинга"
→ "kak-kontent-zavod-zamenil-mne-otdel-marketinga"

"Why I Stopped Writing Daily"
→ "why-i-stopped-writing-daily"
```

Длина slug ≤ 60 chars (SEO-friendly).

## Step 3 - canonical output

Сгенерировать canonical version в format соответствующем `platforms.canonical.type`.

### Personal blog (Markdown)

```markdown
---
title: "<headline>"
slug: "<slug>"
date: <YYYY-MM-DD>
language: "<ru | en>"
type: "<teaching | story | framework>"
canonical: true
---

# <headline>

<introduction>

## <subhead INSIGHT>

<insight body>

## <subhead PROCESS>

<process body>

<cta>
```

### Newsletter (Kit)

HTML с Kit-блоками. Subject + preheader сверху. Тело с inline styles.

### Newsletter (Beehiiv)

Beehiiv editor: text-block / quote-block / divider / image-block / cta-button.

### LinkedIn article

Plain text format c bold для подзаголовков (LinkedIn editor не уважает H2/H3). Короткие абзацы (1-3 строки). Headline + body.

## Step 4 - cross-post versions

Из `config.platforms.cross_post_targets[]` - для каждого target сгенерировать version с:
- `rel="canonical"` указанием canonical URL
- Минимальная адаптация формата (Substack → import markdown, Medium → import markdown, LinkedIn → manual adapt)
- Тот же content, не переписывать

### LinkedIn article (если не canonical)

LinkedIn audience требует свой headline. Сгенерировать LinkedIn-specific headline через `references/hook-patterns-longform.md#linkedin-headlines`:
- 90-110 chars
- Curiosity gap
- Без clickbait но с tension

## Step 5 - A/B subject lines (для newsletter)

Из draft 3 subject lines + 1 preheader. Дополнительно:
- Гипотеза каждой subject (что тестируется: specificity / curiosity / personal)
- Рекомендация для A/B test setup (50/50 на 10% list первые 2 часа, потом winner на остаток)

Output:

```
Subject A: "<>"           - гипотеза: <>
Subject B: "<>"           - гипотеза: <>
Subject C: "<>"           - гипотеза: <>
Preheader: "<>"            - same для всех
A/B test setup: 33/33/33 на 10% list первые 2 часа, winner на 90%
```

## Step 6 - derivatives plan

Long-form pillar feeds 6-12 derivatives. План:

| Derivative | Skill | Source |
|---|---|---|
| X-thread (Hormozi style summary) | `paips-post` | INSIGHT section + main_aha |
| LinkedIn carousel (5-8 slides) | `visual-concept-square` | 3-section outline → каждая section = 2-3 slides |
| TG-posts (2-4 posts из statti) | `post` | personal_anchor + один из INSIGHT examples |
| Spiky one-liners (5-7) | `spiky-one-liner` | контр-интуитивные claims из INSIGHT |
| YouTube long-form (если type=teaching/framework) | manual | весь outline становится video script |
| Shorts cuts (5-7) | `cut-from-long-form` | если есть видео-версия |

Записать в output как plan, не запускать автоматически.

## Step 7 - distribution checklist

```
PUBLISH CHECKLIST для статьи "<headline>"

[ ] Canonical published на <url>
[ ] Newsletter sent (Subject: <A/B winner>)
[ ] LinkedIn article published with rel="canonical"
[ ] Substack cross-post with rel="canonical"
[ ] Medium cross-post with rel="canonical"

DERIVATIVES (next 5-7 дней):
[ ] X-thread (через `paips-post`)
[ ] LinkedIn carousel (через `visual-concept-square`)
[ ] 2-4 TG-posts (через `post`)
[ ] 5-7 spiky-one-liners
[ ] YouTube long-form script (если применимо)

TRACK:
[ ] Newsletter open rate per subject variant
[ ] Blog page views / time on page
[ ] LinkedIn impressions / reactions / comments
[ ] Substack/Medium reads / claps
```

## Step 8 - финальный output для пользователя

Plain text (Telegram-friendly), без таблиц:

```
ГОТОВО. Статья «<headline>».

Тип: <teaching | story | framework>
Платформа canonical: <type> @ <url>
Длина: <word count> слов
Язык: <ru | en>

CANONICAL VERSION:
<полный текст в формате canonical platform>

NEWSLETTER VERSION (если applicable):
Subject A: <>
Subject B: <>
Subject C: <>
Preheader: <>

CROSS-POST URLs:
<list>

DERIVATIVES PLAN (next 5-7 дней):
<list>

PUBLISH CHECKLIST:
<list>

КАК ПИСАЛ:
- Mode: <A | B1 | B2 | C>
- Type rotation: <last N статей были такие-то, выбран этот>
- Hook chosen: <hook + reason>
- Section pacing: <introduction X% / insight Y% / process Z%>
- Voice quirks applied: <list>
- Что отброшено: <если есть alt versions which were dismissed>
```

## Шаг 9 - сохранить в track-record

Append запись в `examples/track-record-longform.md`:

```markdown
## YYYY-MM-DD - <headline> (<type>, <platform>)
- Mode: <A | B1 | B2 | C>
- Word count: <N>
- Subject A/B winner: <если был test>
- Open rate / page views: <fill after publish>
- Catch rate (review issues caught): <after publish reflection>
- Lessons: <fill after publish>
```

## Memory cross-refs

- - plain text output
- - открывать артефакты через `open <path>`
- - без процесса, только финальный output
- - переработка / cross-distribution
- - same-format reproduction для derivatives
---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
