# 01-router - Auto-detect Mode + Lang + Length tier + Subject

Первая стадия workflow. Определяет режим обработки по сигналам в user input и грузит правильный mode-файл следующим.

## Loaded by

- Триггер из SKILL.md description
- Любой явный `/video` или производный вызов

## Input

Сырой user input (строка). Может содержать:
- Команду `/video` с аргументами
- Описание задачи на естественном языке
- URL ингеста (Mode C)
- Длинную надиктовку (Mode D)
- Флаги override

## Output

YAML-структура:

```yaml
mode: "A" | "B1" | "B2" | "C" | "D"
lang: "ru" | "en" | "both"
length_tier: "short-15-30s" | "short-30-60s" | "short-60-180s" | "mid-3-10min" | "long-10-60min" | "auto"
subject: "ivan" | "student"
flags:
  dry_run: false
  with_voice: false
  with_avatar: false
  override_handoff: null  # string или null
next_stage: "01a-plan.md" | "01b-spark.md" | "01c-replication.md" | "01d-transcript.md"
```

## Шаги

### Шаг 1: Load config

```
Read: ~/.claude/skills/video/config.md
```

Извлечь `subject.name`, `paths.*`. Без config дальше не идти.

### Шаг 2: Detect Mode

Применить decision tree по input:

| Сигнал | Mode |
|---|---|
| Голая ссылка `instagram.com/reel/` / `tiktok.com/.../video/` / `youtube.com/shorts/` + intent «replicate» | C |
| `/video replicate <id>` | C |
| `<video_id>` (видно как hash 11+ chars) после слова «такое же» / «в моём голосе» | C |
| `/video` без аргументов | A |
| `/video` + явная дата | A |
| «по плану», «смысл дня», «из карты смыслов» | A |
| `/video про X` / «напиши скрипт про X» / «сделай видос про X» | B1 |
| «дай идеи на видосы» / «что снять сегодня» / «5 идей для шортов» | B2 |
| Сырой текст >500 знаков + пометка «для видео» / «надиктовал» / «вот мысли для шорта» | D |
| Override флаги `--plan` / `--spark` / `--replicate <id>` / `--transcript` | Соответствующий |

Если несколько триггеров - приоритет: C → A (если есть дата) → B1 (если есть «про X») → B2 → D → A (fallback).

Если ничего не сработало - спросить пользователя одним явным вопросом «какой режим: Plan / Spark / Replication / Transcript».

### Шаг 3: Detect Lang

| Сигнал | Lang |
|---|---|
| `--lang ru` или явное «на русском» / «RU версия» | ru |
| `--lang en` или явное «in English» / «EN version» | en |
| `--lang both` или явное «обе версии» / «и RU и EN» | both |
| Mode C + card.md `language: en` | en (но output RU если не сказано) |
| Default | ru (автор primary RU 2026) |

### Шаг 4: Detect Length tier

| Сигнал | Tier |
|---|---|
| `--length short-15-30s` | short-15-30s |
| `--length short-30-60s` | short-30-60s |
| `--length short-60-180s` | short-60-180s |
| `--length mid-3-10min` | mid-3-10min |
| `--length long-10-60min` | long-10-60min |
| Mode C → из card.md `duration_sec` | соответствующий tier |
| Платформа в запросе («reel» / «short» / «tiktok») без указания | short-30-60s default |
| «YouTube» + «длинное» / «long-form» | mid-3-10min default |
| «YouTube» + «10 минут» / «полчаса» / явная цифра >180 sec | mid или long соответственно |
| Default | auto (резолвится в 02-finalize.md) |

Маппинг card.md `duration_sec` → tier:
- ≤30s → short-15-30s
- 31-60s → short-30-60s
- 61-180s → short-60-180s
- 181-600s → mid-3-10min
- 601+s → long-10-60min

### Шаг 5: Detect Subject

В v1.0:
- Default: ivan (config.md hardcoded)
- В v1.1: detect через `config.subject.name` vs unknown

### Шаг 6: Detect Flags

Парсить из input:
- `--dry-run` → flags.dry_run = true
- `--with-voice` → flags.with_voice = true (для downstream replicate-reel)
- `--with-avatar` → flags.with_avatar = true
- `--handoff <skill>` → flags.override_handoff = "<skill>"

### Шаг 7: Route to next stage

| Mode | next_stage |
|---|---|
| A | `01a-plan.md` |
| B1 / B2 | `01b-spark.md` |
| C | `01c-replication.md` |
| D | `01d-transcript.md` |

### Шаг 8: Validate output

Проверить:
- mode != null
- next_stage существует на диске
- Если Mode C: ingest-папка существует (`ls ~/.business/growth/ingest/ | grep <id>`)
- Если Mode A: путь к Карте смыслов из config существует

При fail - explicit error message пользователю с фиксом.

## Hard rules

- Никогда не угадывать mode. Если ambiguous (>1 strong сигнал и они конфликтуют) - спросить.
- Никогда не пропускать config Read - он source of truth для путей и lexicon.
- Никогда не запускать Mode C без проверки что ingest-папка действительно существует (анти-паттерн ingest-reel skill).

## Output handoff

После Шага 8 - передать YAML-структуру в `next_stage` файл. Он использует поля как inputs.

## Anti-patterns

- Запуск 01a-plan.md когда нет Карты смыслов в config.paths.sense_map_launches_dir
- Запуск 01c-replication.md по голому `video_id` без проверки `ls` ingest-папки
- Detect lang по содержимому надиктовки (автор часто пишет RU/EN миксом - приоритет user flag или config default)
- Auto-выбор length tier по длине надиктовки (надиктовка ≠ target длительность видео; tier выбирается по платформе и intent)