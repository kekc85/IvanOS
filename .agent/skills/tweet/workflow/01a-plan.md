# 01a-plan.md - Mode A: Plan из Карты смыслов

Берёт смысл дня из `config.paths.launch_sense_map`.

## Step 1 - Read Карта смыслов

Read `<paths.launch_sense_map>` (e.g., `.business/запуски/<твоя-папка-запуска>/5.2-Карта-смыслов.md`).

Extract смысл соответствующий **сегодняшней дате**:
- Найти секцию с датой (формат «День N - DD.MM» или «YYYY-MM-DD»)
- Если нет - взять следующую free запись
- Если карта пуста или нет matching entry → fallback to `01b-spark.md` Spark-B2

## Step 2 - Extract content brief

Из найденной записи извлечь:

```yaml
content_brief:
  date: YYYY-MM-DD
  meaning_level: Личность | Тема | Экспертность | Метод | Продукт  # 5 уровней Карты смыслов
  big_idea: <one line>
  supporting_points: [<3-5 bullets>]
  proof_assets: [<verbatim quotes / stories / numbers from .business/>]
  cta_intent: <newsletter | community | reply | null>
```

## Step 3 - Decide format based on meaning_level

| Meaning level | Recommended type | Format |
|---|---|---|
| Личность | Single punchline OR PAIPS story | aphorism OR story |
| Тема | Numbered list mini-thread | 5-9 tweets |
| Экспертность | Story / news mega-thread | 8-15 tweets |
| Метод | How-I-did demo | 8-12 tweets |
| Продукт | PAIPS story OR Spiky one-liner | depends на воронка stage |

## Step 4 - Validate against archetype rotation

Read last 3 posts из `config.paths.x_recent_posts` (если != null).
- Если последние 3 архетипа = same as proposed → switch архетип
- Magician / Sage / Outlaw (автор primary) - rotate
- Banned: Caregiver / Lover / Innocent

## Output (handoff к 01-finalize)

```yaml
mode: plan
content_brief: <from Step 2>
recommended_type: <from Step 3>
recommended_format: <single | mini-thread | mega-thread>
archetype: <Magician | Sage | Outlaw>
char_zone_target: <A 40-100 | B 200-280>
proof_required: true | false
```

## Anti-patterns

- НЕ дополнять `content_brief.proof_assets` outside sources - verbatim из `.business/` или null
- НЕ guess дату - если today не в Карте → fallback Spark-B2
- НЕ повторять archetype последние 3 поста