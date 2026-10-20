# 01a-plan - Mode A: видео из Карты смыслов

Mode A. Берёт смысл дня из активной Карты смыслов запуска и формирует brief для следующих стадий.

## Loaded by

- 01-router.md когда mode == "A"

## Input

Output 01-router.md (YAML с mode/lang/length_tier/subject/flags).

## Output

Brief для 02-finalize.md:

```yaml
mode: "A"
source:
  type: "sense_map"
  launch_id: "<launch_name>"
  date: "<YYYY-MM-DD>"
  meaning_id: "<X.Y>"
meaning:
  title: "<заголовок смысла>"
  body: "<текст смысла>"
  triggers: ["<психо-триггер 1>", "..."]
  archetype_recommended: "<Magician/Sage/Outlaw>"
target_audience_segment: "<сегмент из карты или avatar.md>"
length_tier: "<inherited from router>"
lang: "<inherited from router>"
```

## Шаги

### Шаг 1: Determine launch context

Опции (по приоритету):

1. **Явная дата от пользователя** (`/video 2026-05-28`) → искать смысл с этой датой в активных запусках
2. **Активный запуск из tasks/projects/** - найти открытый launch project, взять его sense map
3. **Fallback: brand-level sense map** - `config.paths.sense_map_brand`

```bash
ls ~/.business/запуски/ 2>/dev/null
```

Если папка не существует - fallback на brand-level.

### Шаг 2: Read Карта смыслов

```
Read: <sense_map_path>
```

Если файла нет - output error «Нет активной Карты смыслов, проверьте config.paths.sense_map_launches_dir» + suggestion переключиться на Mode B2 (Spark).

### Шаг 3: Extract meaning of the day

Sense map имеет структуру: разделы 1.x Личность / 2.x Тема / 3.x Экспертность / 4.x Метод / 5.x Продукт + 6.x Психо-триггеры. У каждого смысла должна быть дата (если sense map календарный).

Алгоритм выбора:
1. Найти запись с `date: <target_date>` (target_date = сегодня или явная дата от пользователя)
2. Если нет - найти ближайшую upcoming
3. Если sense map не календарный - взять следующий неиспользованный смысл (трекинг через track-record)

Извлечь:
- title (заголовок смысла)
- body (тело смысла, полный текст)
- meaning_id (X.Y координата)
- triggers (если указаны)
- archetype_recommended (если указан, иначе nil)

### Шаг 4: Validate meaning

Если body пустое или meaning состоит из «TBD» / «заполнить» - escape на Mode B2 с warning «смысл не заполнен, переключаюсь на Spark».

### Шаг 5: Lookup audience segment

```
Read: <config.paths.avatar>
```

Найти audience segment, который best match для этого смысла (по теме / по уровню осведомлённости). В простом случае - default segment.

### Шаг 6: Determine length tier (если auto)

Если length_tier == "auto":
- Карта смыслов часто помечает «для шорта» / «для long-form» - взять оттуда
- Default: short-30-60s (автор primary cadence)
- Глубокая тема (несколько psycho-triggers, 4 архетипа) → short-60-180s
- Исторический разбор / методология → mid-3-10min

### Шаг 7: Strategy paragraph для пользователя

Перед выходом - короткое сообщение в чат:

```
Стратегия Mode A:
- Источник: <launch_id> / <meaning_id> / <date>
- Смысл: <title>
- Сегмент: <segment>
- Длина: <length_tier>
- Архетип: <archetype или «не назначен - выберу в 02»>
```

### Шаг 8: Handoff к 02-finalize.md

Передать brief YAML в 02-finalize.

## Hard rules

- Source of truth = Карта смыслов. Не дополнять, не выдумывать тело смысла.
- Пустая запись = fallback на Mode B2, НЕ вымысел из контекста.
- Archetype rotation - нельзя 4 видео подряд одним архетипом. Если track-record показывает что последние 3 уже один - взять второй из recommended списка config.archetypes_allowed.

## Anti-patterns

- Расширение body смысла своими формулировками («сегодня хочу рассказать про вайбкодинг» → AI-tell)
- Перенос двух смыслов в один видос (split на серию)
- Использование brand-level sense map когда есть активный запуск (запуск > brand)
- Игнорирование `archetype_recommended` из Карты смыслов («он сильнее текущей ротации»)