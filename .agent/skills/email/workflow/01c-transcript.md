# workflow/01c-transcript.md

> Mode C: Transcript. Разбор надиктовки в атомарные смыслы → top-1-3 в письма.

## Inputs

- `user_input` = transcript (длинный текст >500 знаков)

## Steps

### Step C.1 - Validate transcript

```
IF len(transcript) < 500 chars:
    return error: "Слишком короткий transcript. Для Mode C нужно >500 знаков. Если короткий - используй Spark B1."
```

### Step C.2 - Extract atomic meanings

Прочитать transcript и извлечь 3-10 атомарных смыслов через структуру:

```yaml
meaning_N:
  hook: "<одна фраза-крючок дословно из transcript>"
  тезис: "<главный тезис мысли - пересказ>"
  evidence: ["<цитата 1 дословно>", "<цитата 2 дословно>"]
  audience_relevance: "<кому это полезно из avatar>"
  letter_type_fit: "nurture | launch | sales | etc."
  cta_hint: "<какой CTA подойдёт>"
```

**Правила извлечения:**

- Hook + evidence - **дословно** из transcript (`[[feedback-verbatim-quote-transfer]]`). Не парафраз.
- Тезис - может быть пересказом, но в лексике автора.
- Каждый meaning - **атомарный** (1 тезис). Если в transcript смешано «A и B» - split на 2 meanings.

### Step C.3 - Filter for no-repeat

Прочитать `config.paths.recent_emails_dir` (последние 20 писем) и отфильтровать meanings которые дублируют темы прошлых писем.

### Step C.4 - Output top-N

Показать ученику 3-10 meanings (после фильтра) с пометкой letter_type_fit + audience_relevance.

```
Из надиктовки извлёк N смыслов:

1. [letter-type: nurture] "<hook>" - тезис: <тезис>. Аудитория: <relevance>.
2. [letter-type: sales] "<hook>" - тезис: <тезис>. Аудитория: <relevance>.
...

Какие 1-3 берём в письма? (номера через запятую)
```

→ Дождаться выбора.

### Step C.5 - Build brief(s)

Для каждого выбранного meaning - отдельный brief:

```yaml
brief:
  mode: transcript
  language: <из router>
  topic_or_meaning: "<тезис>"
  audience_hint: "<audience_relevance>"
  cta_goal_hint: "<cta_hint>"
  sequence_position: null
  source_quotes: ["<evidence 1 дословно>", "<evidence 2 дословно>"]
  source_hook_verbatim: "<hook дословно>"
```

### Step C.6 - Iteration

Если ученик выбрал 1 meaning → один brief → finalize → write → review → publish.

Если выбрал 2-3 meaning → выдать ему N писем. Можно последовательно (по одному, итерируя через весь pipeline N раз) или параллельно (через Agent batch - если writes независимые).

**Default:** последовательно (чтобы автор мог дать feedback после каждого, не делая N писем сразу).

## Anti-patterns

- НЕ парафразить hook / evidence - дословный перенос обязательный
- НЕ выдумывать smysl которых в transcript нет - Source of Truth = transcript
- НЕ извлекать >10 meanings - cognitive overload
- НЕ объединять атомарные meanings в один email - Single idea per email (принцип №1)
- НЕ переводить EN надиктовку в RU email если language=ru без явной просьбы (или наоборот) - нужно сохранить язык транскрипта по умолчанию