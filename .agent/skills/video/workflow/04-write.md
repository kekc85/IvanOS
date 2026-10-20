# 04-write - Mandatory Reads + Draft + Voice Injection + Living Language

Стадия 4. Сердце скилла. Пишет финальный script в голосе автора. 4 pass'а: Mandatory Reads (0) → Draft (1) → Voice Injection (2) → Living Language (2.5).

## Loaded by

- 03-structure.md по завершении

## Input

Structured skeleton из 03-structure.md + finalized brief из 02.

## Output

Draft script для 05-review.md:

```yaml
draft:
  beats:
    - id: "hook"
      text: "<final text>"
      caption_lines: ["<line 1>", "<line 2>", ...]
      duration_sec_actual: <number>
      words_actual: <number>
    - id: "setup"
      text: "<...>"
      ...
  
  script_full: "<concatenated text для voice-generate>"
  captions_full: [<всё в один массив для overlay>]
  
  headline_chosen: "<from structure>"
  
  passes_log:
    pass_0: ["read_path", "read_path", "read_path"]
    pass_1: "drafted from placeholders"
    pass_2: "voice injection applied"
    pass_2_5: "living language injection applied"
```

## Pass 0: Mandatory Reads (анти-«generic AI text»)

**Без Pass 0 - Voice Fidelity Gate в 05-review.md fail'ит. Нет shortcut.**

Прочитать ВСЕ файлы из config.mandatory_reads:

```
Read: <config.paths.examples _TEMPLATE-shorts>
Read: ~/.claude/skills/video/references/_voice-TEMPLATE.md
Read: ~/.claude/skills/video/references/_voice-TEMPLATE.md
Read: ~/.claude/skills/video/config.md
Read: ~/.business/products/sticky-offers.md  # NEW 2026-05-28 — sticky source-of-truth по продуктам/ценам/дисклеймерам, если файл существует и subject=ivan
```

Дополнительно по контексту:
- Mode C: Read card.md, transcript.txt из ингеста (грид уже прочитан в 01c)
- Mode D: Read raw_text из транскрипта
- Если lang en: Read EN-секцию _voice-TEMPLATE.md
- Если tier mid/long: Read templates/<tier>.md (deep - там headline formula и chapter pacing)
- Если Mode A: Read sense map full body

Записать в passes_log.pass_0 все прочитанные пути для audit.

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`.
- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.


## Pass 1: Draft по placeholders

Идти beat-by-beat. Для каждого beat:
1. Прочитать placeholder из structure
2. Прочитать duration_words target
3. Прочитать voice_register из finalize
4. Сгенерировать текст:
   - Длина = target words ±10%
   - Содержание следует placeholder direction
   - Voice register воплощается в тон (Sage = explanation, Outlaw = contrarian, Magician = reveal)

**Для shorts** - текст каждого beat сразу режется на caption_lines (2-6 слов each, ALL CAPS для shorts).

**Для mid/long** - текст beat как paragraph (без caption breakdown - это для voice-generate, не для overlay).

**Mode C особое:** не парафразить оригинал, а переписывать. RU = история→вывод, EN = тезис→аргументы (см. ru-en-adaptation-rules.md).

## Pass 2: Voice Injection (regex + semantic)

Прогнать draft через:

### 2.1: Forced replacements (auto)

Из config.lexicon_force:
- Instagram → Нельзяграм
- Инстаграм → Нельзяграм
- контент-фабрика → контент-завод
- контент-машина → контент-завод
- вайб-кодинг → вайбкодинг
- vibe coding → вайбкодинг
- Дубай → Дубайск (в лексическом контексте)

### 2.2: Banned terms (fail на review, но catch here)

Из config.lexicon_banned. Если присутствуют:
- артефакт / контур / фасилитация
- digital twin / digital-twin
- Grand Slam Offer / Grand Slam
- КЭВ / связки
- fast-action
- без опыта в коде / не программист / программирование

Заменить на эквивалент или переписать beat.

### 2.3: Voice rules check

Из config.voice_rules:
- Audience descriptor: «эксперт» → «ты» / «тех у кого» / «один человек»
- Объекция: «не программист» → «не маркетолог» (если объекция аудитории релевантна)
- Враг: имя конкурента → «явление» (конструкторы / продюсерская модель / курсомания)
- Claude: «только Claude» → «Claude в ядре, 90%»
- Em-dash «-» внутри строки → «-» или ", "
- Негативная стат → удалить или переформулировать в positive

### 2.4: Native lexicon injection

Из config.lexicon_native - где natural, inject:
- залетает / гоняешь / пилишь / соберёшь / вкатишься / перегон

Тест: «звучит ли это как автор или как generic AI tone». Если последнее - добавить native слово.

## Pass 2.5: Living Language Injection

Read: `~/.claude/skills/video/references/_voice-TEMPLATE.md`

Применить 26 классов banned AI-конструкций (A-Z). Самые частые:
- «не просто X, а Y» (AI-tell)
- «давайте разберём» / «давайте посмотрим»
- «важно понимать»
- «стоит отметить»
- «не секрет, что»
- generic тройки («быстро, легко и эффективно»)
- метафоры там, где есть термин автора

Заменить на живые глаголы:
- «залетает» / «гоняешь» / «пилишь» / «соберёшь»

Self-Discovery Method (из living-language.md): «прочитать draft вслух - какие фразы зацепили как ненастоящие». Каждую такую - переписать или удалить.

## Pass 2.6: Mode-specific finals

**Mode C:** проверить что captions из оригинала НЕ перенесены (memory `feedback_strip_competitor_captions`). Каждая caption строка - 100% авторская или 100% оригинала (никаких смешанных).

**Mode D:** проверить что raw_verbatim фрагменты сохранены или явно переписаны. Не прятать «не подходящие» цитаты - лучше явно сказать в чат «эту часть пропустил, причина X».

**Mode A:** проверить что body смысла из Карты смыслов не приписан расширением.

## Pass 3: Sum/length check

Подсчитать total words и total duration (по темпу 2.5 слов/сек RU, 2.7 EN).

Если total_duration выходит за [floor_sec, ceiling_sec] tier'а:
- Сократить (Hormozi-style cut) или расширить (добавить body beat)
- Не выпускать out-of-range в 05-review (gate failит и придётся перепереписывать)

## Pass 4: Concatenate

- `script_full` = beats[].text joined (для voice-generate)
- `captions_full` = beats[].caption_lines flattened (для overlay)
- `headline_chosen` = headline_primary из 03 (или alternative если primary провалил Voice rules)

## Strategy paragraph в чат

```
Draft готов:
- Beats: <N> штук, total duration ~<X>s (target <Y>s)
- Words: ~<N>
- Passes: 0 ✓ Mandatory Reads / 1 ✓ Draft / 2 ✓ Voice / 2.5 ✓ Living Language / 3 ✓ Length
- Banned terms detected: <N> (исправлены) | none
- Voice rules violations: <N> (исправлены) | none
```

## Handoff к 05-review.md

Передать draft YAML.

## Hard rules

- НИКОГДА не пропускать Pass 0 Mandatory Reads. Без них Voice Fidelity Gate в 05 fail.
- Mode C - captions конкурента strip обязательно.
- Mode D - verbatim сохранение или explicit dropped с reason.
- Em-dash внутри строки - hard fail в Pass 2.3.
- Length out of tier range - fix в Pass 3, не передавать в 05.

## Anti-patterns

- Drafting без Mandatory Reads (получается generic AI tone - основная причина voice fidelity fails в даты запуска.2026)
- Парафраз verbatim в Mode D
- «На красивее переформулировать» оригинал в Mode C
- Игнор Living Language Pass 2.5 (получается формально правильно но «не автор»)
- Caption lines >6 слов в шорте
- Длинные предложения в шорте (>12 слов = темп Hormozi failит)
