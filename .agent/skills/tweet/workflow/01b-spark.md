# 01b-spark.md - Mode B1 (idea expansion) / B2 (idea generation under JTBD)

## Mode B1 - Idea expansion

Триггер: «`/tweet про X`», «напиши твит про X», «тред про X».

### Step 1 - Extract topic
Из input выделить ядро topic. Example:
- «напиши тред про вайбкодинг для психологов» → topic = "вайбкодинг для психологов"

### Step 2 - Generate 5-7 angles

Для topic - сгенерировать 5-7 разных углов. Каждый angle:
- Hook pattern (из 15 в `references/viral-hooks-2026-x.md`)
- Voice cluster (build-in-public / paips / spiky / aphorism / idea-drop)
- Format hint (single / mini-thread / mega-thread)
- Char zone target (A 40-100 / B 200-280)

Output → 5-7 numbered angles в чат для user select.

### Step 3 - User selects → handoff

```yaml
mode: spark-b1
topic: <user topic>
selected_angle: <user choice>
recommended_type: <derived>
recommended_format: <derived>
archetype: <derived>
char_zone_target: A | B
```

## Mode B2 - Idea generation under JTBD

Триггер: «дай идеи твитов», «что писать на X сегодня».

### Step 1 - Read context

Read:
- `<paths.avatar>` → avatar profile
- `<paths.products_dir>` → current products
- `<paths.x_recent_posts>` если есть → last 30 posts (для no-repeat check)

### Step 2 - Generate 5-7 ideas под JTBD

5-7 ideas matching avatar's JTBD. Каждая:
- Hook (verbatim, ready to use)
- Recommended type
- Voice cluster
- Char zone

**No-repeat hard:** проверить против last 30 posts - топик / угол не повторяет недавнее.

Output → 5-7 numbered ideas в чат для user select.

### Step 3 - User selects → handoff

```yaml
mode: spark-b2
selected_idea: <user choice>
recommended_type: <derived>
recommended_format: <derived>
archetype: <derived>
char_zone_target: A | B
```

## Anti-patterns

- НЕ generate ideas без чтения avatar / products (generic = брак)
- НЕ повторять topic last 30 posts (no-repeat hard)
- НЕ нагружать user 20+ ideas - 5-7 max
- НЕ описывать ideas общими словами - каждая идея = ready-to-write hook + format + char zone

## Memory cross-refs

- `[[feedback-no-generic-ai-artifacts]]` - sophistication 4-5 видела всё, ideas должны быть specific
- `[[feedback-30-options-when-decline-loop]]` - если 2-3 declines подряд → 20-30 alternatives
- `[[feedback-strategy-copy-faster-more-better]]` - same-format reproduction from research