# 01d-transcript - Mode D: надиктовка → script

Mode D. Берёт длинную надиктовку (≥500 знаков от Wispr Flow / любого voice-to-text) и извлекает 3-10 атомарных смыслов. Пользователь выбирает top-1-3, скилл генерит brief на их основе.

## Loaded by

- 01-router.md когда mode == "D"

## Input

Output 01-router.md + raw transcript text (≥500 знаков).

## Output

Brief для 02-finalize.md (один или несколько в виде массива если выбрано 2-3):

```yaml
mode: "D"
source:
  type: "transcript"
  raw_text: "<full надиктовка>"
  word_count: <number>
  extracted_meanings: [<3-10 atoms>]
  selected_meaning_index: <0-based>
selected_meaning:
  title: "<заголовок смысла>"
  raw_verbatim: "<точная цитата из транскрипта>"
  rough_arc: ["<beat 1>", "<beat 2>", "..."]
  archetype_recommended: "<...>"
target_audience_segment: "<...>"
length_tier: "<inherited>"
lang: "<inherited>"
```

## Шаги

### Шаг 1: Validate input length

Если raw_text < 500 знаков - escape на Mode B1 «текста мало для transcript-режима, переключаюсь на Spark».

### Шаг 2: Read context

```
Read: <config.paths.avatar>
Read: <config.paths.brand_dna>
```

### Шаг 3: Detect language от транскрипта

- Если >70% слов кириллица → ru
- Если >70% слов латиница → en
- Микс → mark mixed, output следует router.lang

### Шаг 4: Extract атомарные смыслы

Один атомарный смысл = one self-contained тезис, который может стать одним видео. Критерии:
- Имеет ясную главную мысль
- Может быть рассказан в 30-180 sec
- Содержит конкретику (числа / имена / факты)
- Имеет тон автора (не generic)

Алгоритм:
1. Прочитать всю надиктовку
2. Найти разрывы темы (transitional phrases типа «кстати», «другое», «вот ещё что», «теперь о»)
3. Каждый сегмент проверить на «может ли стать самостоятельным видео»
4. Извлечь 3-10 атомов

Для каждого атома:
- title (заголовок в 1 строку)
- raw_verbatim (точная цитата из транскрипта, не парафраз)
- rough_arc (предполагаемые beats hook/setup/body/payoff/cta)
- recommended archetype

### Шаг 5: Present to user

Plain text список (Telegram-friendly):

```
Из надиктовки извлёк <N> атомарных смыслов:

1. <title>
   Цитата: "<verbatim 1-2 строки>"
   Архетип: <archetype>

2. <title>
   ...

Выбери 1-3 номера или дай свой angle.
```

### Шаг 6: User selection

Ждать выбор. 1 = один скрипт. 2-3 = серия (output = массив briefs).

### Шаг 7: Determine length tier

Если router сказал tier - использовать. Если auto:
- Атом содержит 1 главную мысль + 1 пример → short-30-60s
- Атом содержит 1 главную мысль + 2-3 примера → short-60-180s
- Атом содержит развёрнутую методологию → mid-3-10min

### Шаг 8: Build brief(s)

Сформировать output YAML(s) с **verbatim quote** в `raw_verbatim`. Это критично - 04-write.md будет использовать verbatim как seed для voice fidelity.

### Шаг 9: Strategy paragraph в чат

```
Стратегия Mode D:
- Источник: надиктовка <word_count> слов
- Извлечено атомов: <N>
- Выбрано: <selected_indexes>
- Tier: <length_tier>
- Язык: <lang>
```

### Шаг 10: Handoff к 02-finalize.md

## Hard rules

- Verbatim quote - обязательно дословно. Не парафразить «на красиво».
- Не приписывать смыслы которых в транскрипте нет. Атом базируется ТОЛЬКО на тексте.
- Не объединять 2 разных атома в один скрипт без явного согласия пользователя.
- Если в надиктовке автор говорит «не записывай / не используй» - флаг и спросить.

## Anti-patterns

- Парафраз «причёсаное» вместо verbatim (memory `feedback_verbatim_quote_transfer`)
- Generic AI «вы хотели поделиться 5 мыслями» - нет, автор надиктовал конкретное
- Извлечение 1 атома когда в надиктовке явно 3-4 разных темы
- Игнор «не записывай» отметок
- Перенос атома без проверки что в нём есть конкретика (атом без числа/имени/факта = generic потенциал, переспросить)

## Связано

- Tool: Wispr Flow (как автор надиктовывает)
- Memory: `feedback_verbatim_quote_transfer`, `feedback_research_methodology`
- Sister mode in `post` skill: тот же паттерн для TG-постов