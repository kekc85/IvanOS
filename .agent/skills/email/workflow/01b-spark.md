# workflow/01b-spark.md

> Mode B1: расширение темы пользователя в 3-5 углов. Mode B2: генерация 5-7 идей под JTBD/avatar/CJM stage.

## Sub-modes

| Sub-mode | Триггер | Что делает |
|---|---|---|
| **B1** | «напиши письмо про X» / `/email про X` / `--spark X` | Расширяет тему X в 3-5 углов → выбираешь |
| **B2** | «дай идеи письма» / «что отправить базе» | Генерит 5-7 идей под JTBD/avatar → выбираешь |

## Mode B1 - Spark / Topic expansion

### Step B1.1 - Read context

```
avatar = Read(config.paths.avatar)
jtbd = Read(config.paths.jtbd)
objections = Read(config.paths.objections)
journey = Read(config.paths.journey)
```

### Step B1.2 - Expand topic X into 3-5 углов

Для темы X сгенерировать 3-5 углов через прохождение по матрице:

| Угол | Вопрос |
|---|---|
| Pain | Какая боль читателя связана с X? Что злит / пугает / стопит? |
| Aspiration | К какому состоянию читатель хочет прийти через X? |
| Contrarian | Что общепринятое мнение про X - bullshit? |
| Personal story | Какой твой опыт с X? (история-крючок) |
| Tactical / How-I | Конкретный шаг 1-2-3 как ТЫ делаешь X |

Из 5 матриц выбрать 3-5 наиболее релевантных под avatar/jtbd.

**Output:**

```
Тема: X
3-5 углов под рассылку:
1. [Pain] <угол с pain framing>
2. [Aspiration] <угол с aspiration framing>
3. [Contrarian] <угол>
4. [Personal] <угол>
5. [Tactical] <угол>

Какой берём? (отвечай номером или подробнее)
```

→ Дождаться выбора.

### Step B1.3 - Build brief

```yaml
brief:
  mode: spark-b1
  language: <из router>
  topic_or_meaning: "X с выбранным углом"
  selected_angle: "<pain | aspiration | contrarian | personal | tactical>"
  audience_hint: "<из avatar>"
  cta_goal_hint: "<TBD в finalize или из user_input>"
  sequence_position: null
  source_quotes: []
```

## Mode B2 - Spark / JTBD-driven idea generation

### Step B2.1 - Read context

```
avatar = Read(config.paths.avatar)
jtbd = Read(config.paths.jtbd)
objections = Read(config.paths.objections)
journey = Read(config.paths.journey)
recent_emails = Read(config.paths.recent_emails_dir, last 20)  # для no-repeat
```

### Step B2.2 - Generate 5-7 идей под JTBD stage

Для каждой JTBD stage (Awareness / Consideration / Decision / Retention) выбрать 1-2 идеи:

| Stage | Letter-type fit | Идея |
|---|---|---|
| Awareness | nurture | Edutainment про важность темы |
| Consideration | nurture / launch | Сравнение подходов / переломный момент |
| Decision | launch / sales | Снятие возражения / proof |
| Retention | re-engagement / weekly digest | Ценность подписки |

**Output:**

```
5-7 идей письма под твою аудиторию:

1. [Awareness] <идея 1> - letter-type: nurture
2. [Awareness] <идея 2> - letter-type: nurture
3. [Consideration] <идея 3> - letter-type: nurture
4. [Consideration] <идея 4> - letter-type: launch
5. [Decision] <идея 5> - letter-type: sales
6. [Retention] <идея 6> - letter-type: weekly-digest
7. [Retention] <идея 7> - letter-type: re-engagement

Какую берём? (номер или подробнее)
```

### Step B2.3 - Build brief

```yaml
brief:
  mode: spark-b2
  language: <из router>
  topic_or_meaning: "<выбранная идея>"
  selected_jtbd_stage: "<Awareness | Consideration | Decision | Retention>"
  suggested_letter_type: "<nurture | launch | sales | re-engagement | etc.>"
  audience_hint: "<из avatar>"
  cta_goal_hint: "<TBD в finalize>"
  sequence_position: null
  source_quotes: []
```

## Common Anti-patterns (B1 + B2)

- НЕ генерировать идеи которые уже были в последних 20 письмах (no-repeat hard rule per config)
- НЕ выдумывать факты про avatar / jtbd - Source = config.paths.avatar / jtbd. Если поле пустое - спросить автора / fallback
- НЕ генерировать 10+ углов / идей - cognitive overload. 3-5 углов / 5-7 идей max
- НЕ навязывать угол / идею - после выдачи списка дождаться выбора, не идти сразу в finalize
- НЕ повторять чужие хуки конкурентов дословно - adaptation, не plagiarism