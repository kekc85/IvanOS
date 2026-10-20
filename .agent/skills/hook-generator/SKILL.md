---
name: "hook-generator"
description: "F.5 Hook + Title + Thumbnail generator. Generate 10 hook variations + 5 title variations + 3 thumbnail briefs per piece для A/B testing. Uses viral hook library 2026 paтterns per platform."
---

# Hook + Title + Thumbnail Generator (F.5)

## Когда использовать

Перед публикацией любого piece контента - generate variants для A/B testing.

Триггеры:
- "Generate hooks для Reel про X"
- "Hook + title + thumbnail для YouTube long-form Y"
- "X-thread hook variations"

## Background

First 1.5-3 sec decide 71-90% distribution (TikTok 1.5 sec gate, Reels similar). Hook = highest leverage в whole content piece.

Reference: viral hook library 2026 (memory `project_viral_hook_library_2026`) - 8 patterns на каждую из 6 платформ.

## Гвардрейлы

- Voice автора: тёплый-инженерный, на "ты"
- БЕЗ em-dash «—»
- БЕЗ выдуманных цифр / фактов
- БЕЗ имён конкурентов в attack
- Категория = вайбмаркетинг (если applicable)
- Lexicon: Нельзяграм / Дубайск / контент-завод
- Specificity wins (300% lift): exact numbers > vague claims

## Шаги генерации

### Шаг 1: Identify platform + format
По input - определить:
- Нельзяграм Reels (30-90 sec)
- YouTube Shorts (15-60 sec)
- TikTok (15-180 sec)
- X / Twitter (single tweet / thread / long-form Premium)
- LinkedIn (post / article / carousel)
- YouTube long-form (8-25 min)

### Шаг 2: Pick top 3 hook patterns
Из 8-9 patterns на выбранной платформе (см. memory `project_viral_hook_library_2026`):
- Patterns relevant к topic
- Patterns matching авторский voice
- Mix curiosity + specificity + authority

### Шаг 3: Generate 10 hook variations
3-4 variations × 3 patterns = 10 hooks total

Per hook:
- Apply авторский voice
- Include specific number / detail (300% specificity lift)
- Avoid em-dash в text
- Fit platform length constraint

### Шаг 4: Generate 5 title variations
Title = different from hook. Title для:
- YouTube long-form (60 char optimal)
- Newsletter subject line
- LinkedIn carousel cover slide
- Article H1

5 variations по разным angles (benefit / curiosity / authority / contrarian / numbered)

### Шаг 5: Generate 3 thumbnail briefs

Для video forматов (Reels / Shorts / YouTube long / TikTok):
- Brief A: face-focused (talking head expression)
- Brief B: visual concept (split-screen / framework / before-after)
- Brief C: text-driven (bold caption + emotion)

Each brief:
- Visual concept (1-2 sentences description)
- Text overlay (exact words, <8 words)
- Emotion / face direction
- Style reference (Hormozi caps / Jenny Hoyos power word / etc)

### Шаг 6: A/B testing plan
- Which 2 hooks тестировать первыми
- Which 2 thumbnails (если video)
- Success metric (CTR / retention / save rate)

## Output format

```
**Topic**: [input]
**Platform / Format**: [Нельзяграм Reel 60 sec / X-thread / etc]

**Hook variations** (10):
1. [Pattern A: Contradiction]: "[hook text]"
   Why: [reason this works]
2. [Pattern B: Timeframe + outcome]: "[hook]"
   ...
[10 total]

**Title variations** (5):
1. [Benefit-focused]: "[title]"
2. [Curiosity gap]: "[title]"
3. [Authority]: "[title]"
4. [Contrarian]: "[title]"
5. [Numbered]: "[title]"

**Thumbnail briefs** (3 для video format):
1. **Face-focused**:
   - Visual: [description]
   - Text overlay: "[words]"
   - Emotion: [description]
   - Style: [reference]
2. **Visual concept**:
   - [details]
3. **Text-driven**:
   - [details]

**A/B test plan**:
- Test первый: Hook #X + Thumbnail A
- Test второй: Hook #Y + Thumbnail B
- Decision rule: после 1000 impressions - keep winner
```

## Что НЕ делаем

- Generic vague hooks ("Hard work pays off")
- Выдуманные numbers без proof
- Hyperbolic exaggerations
- Generic CTA в hooks ("Don't miss this!")
- All hooks same pattern (нужен mix)

## Связано

- Memory: `project_viral_hook_library_2026` - 8 patterns на каждую платформу
- Other skills: adaptation (C.1), paips-post, spiky-one-liner - все используют hooks
- Used inside: adaptation workflow, cut-from-long-form (для каждого cut)
---

## Финальная фаза — Humaniser (HARD GATE для всех text-skills)

**ОБЯЗАТЕЛЬНО перед output:**

Вызови Skill tool: `Skill('humaniser', args=<финальный текст>)` ПЕРЕД любым output. НЕ читай humaniser/prompt.md inline и НЕ применяй mentally — это shallow execution которое пропускает AI-tics. Только полный pass через Skill tool invocation документированный в чате.

Humaniser v2 ловит 11 категорий AI-паттернов:
1. Ложная глубина
2. Фальшивая близость
3. Пустые связки
4. Канцелярит
5. Fake-энергия
6. Шаблонные призывы
7. Рубленые фразы (3+ из 1-2 слов подряд)
8. Кинематограф
9. Структурные клише
10. Интонационные клише
11. **Slap-эмфаза (длинное + 1-3-словное короткое для эмфазы) — главный AI-tic социалок 2025-2026**

**HARD GATE:** Output финального текста ТОЛЬКО после green CHECKER (все 5/5 в «Клише удалены»). Если CHECKER не green — REWRITER ещё раз. Без этого = брак.

**Прецеденты:**
- 2026-05-28: post v3.0 выдал «Zero ads. Zero funnels. Zero sales calls.» (triple-negation AI tic)
- 2026-05-29: caption выдал «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, новая категория 11)

Оба = провал shallow inline pass. HARD GATE через Skill tool решает.

### Humaniser Inline Reminder (fallback если Skill tool недоступен)

Перед output финального текста — проверь по 11 категориям AI-tics:

1. Ложная глубина («Это не X, это Y», «Секрет в том»)
2. Фальшивая близость («Знакомо?», «Представьте»)
3. Пустые связки («Давайте разберёмся», «Важно понимать»)
4. Канцелярит («В современном мире», «Является неотъемлемой»)
5. Fake-энергия («Спойлер», «Бонус», «Лайфхак»)
6. Шаблонные призывы («Хватит X», «Перестаньте X начните Y»)
7. Рубленые фразы (3+ предложения подряд из 1-2 слов: «Просто. Быстро. Эффективно.»)
8. Кинематограф («Воскресенье, 10 вечера», «Понедельник, 9 утра»)
9. Структурные клише (параллелизм X/Y/Z, всегда 3 пункта)
10. Интонационные клише («невероятно простой!», «истина в том»)
11. **Slap-эмфаза**: короткое standalone (1-3 слова) после длинного для эмфазы. SMELL TEST: «можно ли слить через запятую?». YES → SLAP, слить. Исключения: structural separator перед list / hook / punchline finale.

Прецеденты провала которые этот block ловит:
- post v3.0 2026-05-28: «Zero ads. Zero funnels. Zero sales calls.» (triple-negation, cat 7+9)
- caption 2026-05-29: «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, cat 11)

При нахождении любого pattern → REWRITER (переписать) → re-CHECKER → если clean → output.

