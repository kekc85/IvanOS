# 01b-spark - Mode B1/B2: ситуативный

Mode B. Два варианта:
- **B1 (expand):** пользователь даёт тему X («сделай видос про X»), скилл расширяет в 5-7 углов
- **B2 (generate):** пользователь говорит «дай идеи», скилл генерит 5-7 идей под JTBD/avatar

## Loaded by

- 01-router.md когда mode == "B1" или "B2"

## Input

Output 01-router.md.

## Output

Brief для 02-finalize.md:

```yaml
mode: "B1" | "B2"
source:
  type: "spark"
  raw_input: "<user input>"
  selected_angle_index: <0-based>
selected_angle:
  hook_seed: "<первичная зацепка>"
  body_seed: "<первичное тело>"
  payoff_seed: "<первичный пейофф>"
  archetype_recommended: "<...>"
target_audience_segment: "<...>"
length_tier: "<inherited>"
lang: "<inherited>"
```

## Шаги - Mode B1 (expand)

### Шаг B1.1: Extract topic

Из user input извлечь тему X (всё после «про» / «about» / «на тему»).

### Шаг B1.2: Read context

```
Read: <config.paths.avatar>
Read: <config.paths.brand_dna>   # для архетипов и tone
Read: <config.paths.business_index>  # для текущих продуктов и фокусов
```

### Шаг B1.3: Generate 5-7 angles

Для темы X - 5-7 углов из списка:

1. **Contrarian** - общепринятое мнение vs авторское
2. **Build-in-public** - что автор делает сейчас вокруг X
3. **Method reveal** - конкретный механизм / workflow по X
4. **Personal story** - личный эпизод связанный с X
5. **Audience pain → solution** - конкретная боль из avatar решённая через X
6. **Numbers** - конкретные метрики / времена / результаты вокруг X
7. **Tool stack** - что использует автор для X

Каждый угол:
- Hook seed (1 строка)
- Why this angle works (1 строка обоснование)

### Шаг B1.4: Present to user

Plain text список (Telegram-friendly):

```
5-7 углов на тему "X":

1. Contrarian - "{hook_seed}"
   Логика: {why}

2. Build-in-public - "{hook_seed}"
   Логика: {why}

...

Выбери номер или дай свой angle.
```

### Шаг B1.5: User selection

Ждать выбор. Если выбран свой angle - добавить в track-record.

### Шаг B1.6: Build brief

Сформировать output YAML на основе выбранного угла. Body_seed = 2-3 строки skeleton, не текст.

## Шаги - Mode B2 (generate)

### Шаг B2.1: Read context

```
Read: <config.paths.avatar>
Read: <config.paths.objections>
Read: <config.paths.journey>
Read: <config.paths.brand_dna>
Read: <config.paths.business_index>
```

### Шаг B2.2: Read recent (no-repeat hard)

Прочитать последние 30 видео из track-record:

```
Read: <config.track_record_path>
```

Извлечь темы и углы последних 30. Любая тема которая там есть - banned для этой сессии.

### Шаг B2.3: Generate 5-7 ideas

Идеи генерятся по комбинаторике:
- JTBD из avatar.md (что зритель пытается сделать)
- Возражение из objections.md (что мешает)
- Этап journey (где зритель сейчас)
- Текущий продукт / focus из business_index

Каждая идея:
- Topic (1 строка)
- Hook seed (1 строка)
- Why this works now (1 строка)
- Recommended archetype

### Шаг B2.4: Present to user

Plain text список (Telegram-friendly):

```
5-7 идей на сегодня:

1. {topic}
   Hook: "{hook_seed}"
   Архетип: {archetype}
   Почему сейчас: {why_now}

...

Выбери 1-3 номера или дай свой angle.
```

### Шаг B2.5: User selection

Ждать выбор. 1 идея = один скрипт. 2-3 = серия (тогда output = массив briefs).

### Шаг B2.6: Build brief(s)

Сформировать output YAML(s).

## Hard rules

- B2: проверить no-repeat HARD по последним 30 видео из track-record. Дублирование темы = fail.
- B1: tема пользователя - source of truth, не расширять её на смежные темы без согласия.
- Никаких generic углов («10 советов про X», «секреты X») - конкретика обязательна.
- Каждый angle / idea должна пройти первичный тест: «может ли автор это снять за 30 минут / есть ли у него factual basis».

## Anti-patterns

- Generic AI «5 советов про X» / «топ-3 ошибки в X» - generic AI artifact (memory `feedback_no_generic_ai_artifacts`)
- Повтор темы из последних 30 без явной новой грани
- Игнор JTBD языка плательщика (memory `feedback_jtbd_language_of_payer`)
- Шаблонные hook seeds без контекста («Знаешь что 99% людей делают неправильно?»)
- Идеи которые требуют production за пределами текущего стека автора (например, серия с live-съёмкой со студии - out of scope)