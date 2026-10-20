# RU-EN adaptation rules

Правила адаптации между RU и EN для скрипта video. НЕ дословный перевод. Культурная адаптация.

Применяется в:
- Mode C (Replication) - EN ингест переписывается в RU voice
- `lang: both` - двойной output

Sister skill: `multi-language-localization` (C.3) - общая методология для контент-завода, video skill грузит local rules.

## Главный принцип

**Дословно переносится:**
- Hook archetype (механика)
- Visual structure (beats / B-roll / split)
- Timing / pacing
- CTA mechanic (single action call)

**Переписывается полностью:**
- Narrative arc (RU vs EN structural differences см. ниже)
- Examples / references (англоязычные имена / сервисы → русские эквиваленты)
- Cultural touchpoints
- Voice / tone (RU = авторский, EN = авторский в EN-tone)

## RU vs EN narrative arc

### RU: история → вывод

Русская модель: ставит зрителя в историю, потом делает вывод.

```
1. Setup ситуации (что было)
2. Конфликт / поворот
3. Personal insight
4. Generalized conclusion
```

Пример: «Вчера продюсер попросил TG-бот. Любой разраб посчитал - три дня, 50К. Я открыл Claude. Через 18 минут бот ответил. Вывод: маркетологам больше не нужны разрабы.»

### EN: тезис → аргументы

English модель: ставит тезис в начале, потом доказывает.

```
1. Big claim / outcome promise
2. Setup (как достигли)
3. Evidence (number / demo / before-after)
4. Re-state claim with twist
```

Пример: «You can build a TG bot in 18 minutes. Yesterday a producer asked me. Devs quoted 3 days, $500. I opened Claude. One prompt. Done.»

### Practical rule

Mode C из EN ингеста в RU output:
- Сохранить hook (механика) дословно
- Reorder beats: тезис → история (история → вывод)
- Examples: $500 → ₽50К / Lovable → Lovable (международные tools оставить)

Mode C из RU в EN:
- Hook дословно
- Reorder: история → тезис
- Examples: ₽50К → $500 / GetCourse → Kajabi (Western equivalent)

## Numbers / currency adaptation

| RU original | EN equivalent (примерно) |
|---|---|
| ₽50 000 | $500 |
| ₽100 000 | $1 000 |
| ₽1М | $10 000 |
| ₽43К (автор tier 1) | $497 |
| ₽199К (автор fantom) | $1 997-2997 |

EN никогда не использовать «₽», всегда «$». RU всегда «₽» (автор primary market RU 2026).

## Service name adaptation

Большинство современных AI tools - global brands, не переводятся:
- Claude / Claude Code / Cursor / Lovable / Bolt / Tella / HeyGen / ElevenLabs / Kling / Higgsfield → as is

Локальные сервисы переводятся / заменяются:

| RU | EN equivalent |
|---|---|
| Нельзяграм | Instagram (в EN - restricted в Россия context не релевантно) |
| Дубайск | Dubai |
| GetCourse | Kajabi / Skool / Circle |
| Skillbox | Coursera / MasterClass |
| <конкурент> | Tony Robbins / Tai Lopez (similar archetype но не дословный equivalent) |
| Telegram | Telegram (global) |
| TG-бот | TG bot or Telegram bot |
| Skool (автора club) | Skool (global) |

## Cultural touchpoints

### RU specific (НЕ переносить в EN):
- Ссылки на «вайбкодинг» / «вайбмаркетинг» как RU термины автора - переводить как «vibe coding» / «vibe marketing»
- «Курсомания» - переводить как «course addiction» / «info-marketing carousel»
- «Продюсерская модель» - как «launch model» / «info-product business» (Western equivalent)
- «Перегон» - как «conversion» или «adaptation»
- «Контент-завод» - как «content factory» (Western analog существует)

### EN specific (НЕ переносить в RU):
- US-specific brand references (Whole Foods, Starbucks, etc) → general
- US-specific cultural moments → general
- Hormozi-specific tone → adapted to авторское но не дословный

## Length adjustments

EN темп ~2.7 слов/sec, RU ~2.5 слов/sec.

Поэтому при адаптации:
- RU script того же tier (например short-30-60s) → ~5-7% меньше слов чем EN
- При replication: если EN видео 45 sec - RU оригинал должен быть ~42 sec для visual sync

## Hook adaptation patterns

### Pattern 1 (Timeframe + outcome)

- EN: «Built [X] in [N] [unit]»
- RU: «Собрал [X] за [N] [unit]»

Word order - авторский: «За 11 минут собрал лендинг» (numeric outlier first) или «Собрал лендинг за 11 минут» (action first). Оба валидны.

### Pattern 6 (Contrarian)

- EN: «Everyone thinks X. Truth is Y»
- RU: «Все думают X. А на деле Y»

авторская версия: «Все думают X. Я говорю Y» (более assertive).

## CTA adaptation

CTA must be 1 single action в обоих lang.

| RU CTA | EN CTA |
|---|---|
| «Коммент СБОРКА» | «Comment BUILD» |
| «Ссылка в био» | «Link in bio» |
| «Подпишись если про вайбкодинг» | «Follow for more vibe coding» |
| «DM "ZAVOD"» | «DM "FACTORY"» |

## Voice rules across languages

**Same across RU/EN:**
- Action verbs > nouns
- Concreteness > abstraction
- No filler words / hedge phrases
- Em-dash banned inside lines
- No enemy by name
- No negative public stats
- Single CTA in finale

**Different across RU/EN:**
- RU = «ты» direct / EN = «you» direct
- RU specific lexicon (Нельзяграм / контент-завод / вайбкодинг) ↔ EN equivalents
- Cultural references swap

## Both-lang output (config.lang = both)

Когда `--lang both`:
1. Сгенерировать RU first (primary market)
2. Адаптировать → EN с учётом narrative arc swap
3. Не дословный translation - full rewrite в EN voice
4. Output: 2 separate scripts + 2 separate caption arrays + same production handoff (B-roll / hook visual универсальны)

Не публиковать оба в одно время. EN - на 7-14 дней позже (allow для EN-niche audience digestion).

## EN voice - placeholder

В v1.0 - gold-standard EN корпус автора ещё не зафиксирован. Пока используем RU voice rules → mechanical apply к EN:
- «you» direct
- short rhythms 4-8 words
- action verbs
- Hormozi-style captions

Когда появятся 10 реальных EN-видео автора - заменить эту секцию на verified gold-standard analysis (`examples/_TEMPLATE-en-shorts.md`).