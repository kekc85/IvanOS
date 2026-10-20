# Workflow 01b: Mode B1/B2 - Spark (ситуативный)

Два под-режима:
- **B1:** Пользователь дал конкретный topic → расширить в 5-7 визуальных углов
- **B2:** Пользователь просит «дай идеи» → сгенерировать 5-7 идей под avatar+JTBD

---

## Mode B1: расширение идеи

### Step 1: Extract topic

Из user input выделить core topic. Если topic нечёткий - clarify question.

### Step 2: Generate 5-7 visual angles

Для одного topic - 5-7 разных визуальных углов, по каждому привязка к типу:

**Шаблон output:**
```
Topic: «<extracted topic>»

5 визуальных углов:

1. [type: concept-diagram] <угол 1>
   - Geometry: <2x2 / spectrum / iceberg / etc>
   - Ключевая идея: <1 строка>
   - Hook: <почему scroll-stop>

2. [type: dashboard-screenshot] <угол 2>
   - Real metric: <какое>
   - Crop: <что в кадре>
   - Hook: ...

3. [type: meme] <угол 3>
   - Format: <Drake / Galaxy Brain / etc>
   - Twist: <связь template ↔ topic>
   - Hook: ...

4. [type: quote-card] <угол 4>
   - Quote: «<draft quote>»
   - Attribution: <кто>
   - Hook: ...

5. [type: before-after] <угол 5>
   - Before: <что>
   - After: <что>
   - Hook: ...
```

### Step 3: Diversity check

5-7 углов должны cover минимум 3 разных типов. Не выдавать 5 concept-diagrams - audience устаёт.

### Step 4: User selects 1

Спросить «который угол берём?». User отвечает номером или «другой».

Если «другой» - спросить direction (другой type / другой угол того же type) и regenerate.

### Step 5: Output

```yaml
mode: "spark-b1"
topic: "<extracted topic>"
chosen_angle: "<selected angle full description>"
hints:
  type_suggestion: "<from chosen angle>"
  platform_suggestion: null  # выберется в 02-finalize
  reference_creator: null
source_context: "User input: <verbatim>"
```

→ `02-finalize.md`

---

## Mode B2: генерация идей под JTBD

### Step 1: Read avatar + JTBD

```bash
avatar=$(cat $config.paths.avatar)
jtbd=$(cat $config.paths.jtbd)  # обычно внутри avatar.md
journey=$(cat $config.paths.journey)
```

### Step 2: Read recent images history

Если `config.recent_images_source != "none"`:
- Прочитать last 10 опубликованных картинок
- Извлечь темы / типы / hooks

### Step 3: Generate 5-7 идей

Идеи должны:
- Cover разные стадии journey
- Не повторять последние 10 опубликованных
- Cover минимум 3 разных типов из 5
- Привязаны к JTBD авторские segment

**Шаблон:**
```
5 идей картинок-постов под твою аудиторию:

1. [type: <type>] <idea title>
   - JTBD connection: <какой job-to-be-done закрывает>
   - Угол: <конкретный угол>
   - Hook: <почему scroll-stop>

2. ...

... (5-7 идей)

Какую берём? (номер / «другой» / «дай ещё»)
```

### Step 4: User selects 1

Аналогично B1.

### Step 5: Output

```yaml
mode: "spark-b2"
topic: "<chosen idea title + expanded>"
chosen_angle: "<full description>"
hints:
  type_suggestion: "<from chosen>"
  platform_suggestion: null
  reference_creator: null
  jtbd_connection: "<какой JTBD>"
source_context: "Generated from avatar+JTBD"
```

→ `02-finalize.md`

---

## Принципы

1. **5-7 углов / идей это minimum для choice.** Меньше = не достаточно diversity. Больше = paralysis.
2. **Diversity типов.** Минимум 3 из 5 types в любом spark output.
3. **Recent posts no-repeat.** Если есть история - фильтруй повторы.
4. **JTBD anchor в B2.** Каждая идея должна явно cover JTBD.
5. **User selection - mandatory step.** Не выбирай за пользователя, выкатывай 5-7 и жди choice.