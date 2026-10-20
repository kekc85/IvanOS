# workflow/01a-plan.md

> Mode A: Plan. Берёт смысл / позицию из карты воронки или launch sequence map.

## Inputs

- `config` (из router)
- `user_input` (опционально содержит «day N» / дата / название письма из карты)

## Steps

### Step 1 - Detect Plan source

```
IF "sequence day N" OR "launch day N" OR active launch context:
    source = launch_sequence
    map_path = config.paths.launch_sequence_map
ELSE IF "по карте воронки" OR no specific position:
    source = funnel_map
    map_path = config.paths.funnel_map
```

### Step 2 - Read map

```
map = Read(map_path)

IF NOT exists(map_path) OR map empty:
    → fallback to Mode B2 (Spark-B2)
    return brief with note: "карта воронки пустая, fallback на Spark"
```

### Step 3 - Extract position

**Для launch sequence:**

```
IF "day N" in input:
    position = N
ELSE:
    ask: "Какая позиция в sequence? Pre-launch (-7d / -3d / -1d) / Launch day (Day 0) / Open cart (Day 1-4) / Close (Day 5 / last call)?"
```

→ Читаем строку из launch-sequence map для этой позиции:

```yaml
sequence_day_N:
  theme: "<тема письма>"
  big_idea: "<главная мысль>"
  cta_goal: "<куда ведём>"
  pre_email_context: "<что было до>"
  post_email_context: "<что после>"
  sequence_position_type: "pre-launch | launch-day | open-cart | close-cart"
```

**Для funnel map:**

```
position = current_funnel_stage из user_input или config
section = "nurture" | "welcome" | "winback" | etc. из funnel map
```

→ Читаем строку funnel map для этой позиции.

### Step 4 - Build brief

```yaml
brief:
  mode: plan
  language: <из router>
  source: launch_sequence | funnel_map
  topic_or_meaning: "<theme или big_idea>"
  audience_hint: "<из map или config.paths.avatar>"
  cta_goal_hint: "<cta_goal из map>"
  sequence_position: "<N или null>"
  sequence_context:
    pre: "<pre_email_context>"
    post: "<post_email_context>"
    type: "<sequence_position_type>"
  source_quotes: []   # не применимо для Mode A
```

### Step 5 - Validate brief

- ✓ `topic_or_meaning` не пустой
- ✓ `cta_goal_hint` не пустой
- ✓ Если launch sequence - `sequence_position` set + sequence_context.type set
- ✓ Brief не дублирует одно из последних 20 писем (check `config.paths.recent_emails_dir`)

Если duplicate → warning + предложить ротацию angle.

### Step 6 - Hand-off

→ `workflow/01-finalize.md` с brief.

## Anti-patterns

- НЕ выдумывать смысл если карта пустая → fallback на Mode B2, не творчество
- НЕ дополнять theme / big_idea / cta_goal от себя - Source of Truth = карта (`[[feedback-no-inventing-facts]]`)
- НЕ менять `cta_goal` если в карте указано «X» а тебе кажется что «Y» лучше - это решение автора при заполнении карты
- НЕ запускать generate без `sequence_position` для launch sequence email - это hard fail (см. EMAIL-G8)