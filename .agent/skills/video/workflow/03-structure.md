# 03-structure - Template по tier + headline + skeleton

Стадия 3. Берёт finalized brief, грузит соответствующий length-tier template, формирует skeleton + headline.

## Loaded by

- 02-finalize.md по завершении

## Input

Finalized brief из 02-finalize.md.

## Output

Structured skeleton для 04-write.md:

```yaml
structure:
  length_tier: "<inherited>"
  template_path: "<absolute path to templates/<tier>.md>"
  
  # Headline (для YouTube long / mid; для shorts caption overlay)
  headline_primary: "<text>"
  headline_alternatives: ["<...>", "<...>"]
  
  # Beats skeleton (placeholder text для каждого beat)
  beats:
    - id: "hook"
      duration_sec: <number>
      duration_words: <number>
      placeholder: "<seed text для writer>"
      hook_archetype: "<from finalize>"
    - id: "setup"
      duration_sec: <number>
      duration_words: <number>
      placeholder: "<seed>"
    - id: "body_<N>"      # один или несколько
      duration_sec: <number>
      duration_words: <number>
      placeholder: "<seed>"
      mini_hook: true | false   # для mid/long
    - id: "payoff"
      duration_sec: <number>
      duration_words: <number>
      placeholder: "<seed>"
    - id: "cta"
      duration_sec: <number>
      duration_words: <number>
      placeholder: "<seed or null>"
  
  # Caption overlay structure (для shorts)
  caption_overlay_lines: <number>      # рекомендуемое кол-во overlay lines
  caption_overlay_first_3s: "<text seed>"
  
  # Sum check
  total_duration_sec: <sum>
  total_words: <sum>
```

## Шаги

### Шаг 1: Load tier template

```
Read: ~/.claude/skills/video/templates/<length_tier>.md
```

Template содержит:
- Структуру beats для этого tier
- Распределение времени
- Рекомендации по pacing
- Headline формулу (для mid/long)
- Caption overlay рекомендации (для shorts)

### Шаг 2: Distribute time across beats

Используя template и `duration_sec_target` из finalize, распределить время:

**Short tiers** - фиксированные пропорции из template.

Example для short-30-60s (target 45 sec):
- hook: 3 sec (10 words)
- setup: 7 sec (18 words)
- body_1: 10 sec (25 words)
- body_2: 10 sec (25 words)
- body_3: 10 sec (25 words)
- payoff: 3 sec (8 words)
- cta: 2 sec (5 words)

**Mid tiers** - chapters:
- hook: 15 sec
- promise: 15 sec
- chapter_1...N: equal split с mini_hook каждые 60-90 sec
- synthesis: 30 sec
- cta: 15 sec

**Long tier** - sections с deep mini-hooks (experimental в v1.0).

### Шаг 3: Generate headline

Для tier mid/long - это title видео на YouTube.
Для tier short - это primary caption overlay (over first 3 sec).

Формула headline (универсальная):
- Specificity (число / имя / artefact)
- Promise (что зритель получит)
- Hook archetype-aware

Сгенерировать 3 варианта:
- Primary (best fit)
- Alternative A (более curiosity-driven)
- Alternative B (более concrete result-driven)

Validate headline:
- ≤70 chars для YouTube
- ≤50 chars для caption overlay
- Не содержит запретные термины из config.lexicon_banned
- Соответствует voice_register

### Шаг 4: Generate beat placeholders

Для каждого beat - placeholder text (seed для 04-write.md). Это не финальный текст, а «шаблон + направление»:

```
hook: "<archetype-aware seed: e.g. 'Конструкторы умирают. Вот что вместо.' для contrarian outlaw>"
setup: "<контекст: что было раньше / зачем зрителю слушать>"
body_1: "<первый beat - конкретная грань>"
body_2: "<второй beat - другая грань>"
body_3: "<третий beat>"
payoff: "<синтез + emotional resolution>"
cta: "<single specific action>"
```

Mode C - placeholders базируются на narrative_arc из card.md + voice rewrite seeds.
Mode A - placeholders базируются на meaning_body_seed из 01a.
Mode B - placeholders базируются на selected_angle из 01b.
Mode D - placeholders базируются на raw_verbatim из 01d (cite-friendly).

### Шаг 5: Generate caption overlay structure (для shorts)

```
caption_overlay_lines: 12-20 для short-30-60s
caption_overlay_first_3s: "<hook in caption form, ALL CAPS, ≤5 words>"
```

Hormozi-style каждая caption line = 2-6 слов.

### Шаг 6: Sum check

- `total_duration_sec` = sum of beat durations
- `total_words` = sum of beat words

Проверить: total_duration_sec в [floor_sec, ceiling_sec] из config tier. Если нет - re-distribute beats или escape с warning.

### Шаг 7: Strategy paragraph в чат

```
Структура:
- Tier: <length_tier>
- Headline primary: <headline_primary>
- Beats: <N штук, общая длительность ~<total_duration_sec>s>
- Caption overlay: <N lines>, first 3s = "<first 3s text>"
```

### Шаг 8: Handoff к 04-write.md

## Hard rules

- Не пропускать template Read. Skeleton hardcoded - антипаттерн.
- Sum check обязателен. Beat sum != tier target → re-distribute или escape.
- Headline проверяется на запретные термины ДО handoff.
- Mini-hooks обязательны для mid/long tiers каждые 60-90 sec (retention).

## Anti-patterns

- Generation skeleton без template Read
- Beats без duration_words (writer не знает сколько писать)
- Headline с em-dash «-» внутри строки
- Caption overlay >5 слов в одной line (читаемость в шорте теряется)
- Long-form template скопирован для mid (proportions неверные)