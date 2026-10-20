# 01c-replication - Mode C: card.md → script в voice автора

Mode C. Берёт `card.md` из `ingest-reel` и формирует brief для переписывания в голосе автора. Заменяет/дополняет Шаг 4 `replicate-reel` skill (в v1.0 сосуществуют, в v1.1 replicate-reel будет вызывать этот workflow).

## Loaded by

- 01-router.md когда mode == "C"

## Input

Output 01-router.md + один из:
- `INGEST_DIR` (полный путь к ingest-папке)
- `VIDEO_ID` (резолвится через `ls`)

## Output

Brief для 02-finalize.md:

```yaml
mode: "C"
source:
  type: "card_md"
  ingest_dir: "<absolute path>"
  video_id: "<id>"
  original_url: "<URL>"
  original_author: "<creator handle>"
  original_lang: "ru" | "en"
  original_duration_sec: <number>
  original_format: "<NN-slug from format-library>"
replication_brief:
  voice_script_brief: "<from card.md>"
  narrative_arc: [<beats from card.md>]
  main_insight: "<from card.md>"
  hook_original: "<original hook text>"
  applicability_for_ivan: "<from card.md applicability section>"
target_audience_segment: "<inferred from card.md + Ivan's avatar>"
length_tier: "<from original_duration_sec >"
lang: "<inherited from router, default ru>"
```

## Шаги

### Шаг 1: Resolve INGEST_DIR

Если уже полный путь - использовать. Если только VIDEO_ID:

```bash
ls ~/.business/growth/ingest/ | grep "<VIDEO_ID>"
```

Если найдено 0 совпадений - error «Нет ингеста для <VIDEO_ID>. Запусти сначала /ingest <URL>».
Если найдено >1 - взять самое свежее по дате в имени папки.

### Шаг 2: Read card.md

```
Read: <INGEST_DIR>/card.md
```

Если файла нет - error «card.md не существует в <INGEST_DIR>. Скорее всего ingest упал - перезапусти /ingest <URL>».

### Шаг 3: Extract YAML frontmatter

Извлечь:
- `url`
- `author`
- `duration_sec` → определяет length_tier
- `language`
- `format_classification.primary` (NN-slug)
- `format_classification.confidence`

### Шаг 4: Extract narrative sections

Из card.md взять:
- Секцию «Транскрипт» - оригинальный текст
- Секцию «Структура» - narrative beats с timestamps
- Секцию «Spec для replication» - JSON блок (если есть)
  - `voice_script_brief`
  - `narrative_arc`
  - `format_type`
  - `visual_layers`
  - `captions`
- Секцию «Главный insight»
- Секцию «Применимость для контент-завода автора»

### Шаг 5: Map original_duration_sec → length_tier

| duration_sec | tier |
|---|---|
| ≤30 | short-15-30s |
| 31-60 | short-30-60s |
| 61-180 | short-60-180s |
| 181-600 | mid-3-10min |
| 601+ | long-10-60min |

### Шаг 6: Read grid.jpg (visual context)

```
Read: <INGEST_DIR>/grid.jpg
```

Внутреннее использование - для самопроверки voice_script_brief. Если grid содержит элементы, которых нет в brief (например, специфический визуал-объект) - отметить в `visual_hints[]`.

### Шаг 7: Infer audience segment

Из card.md applicability section взять Ivan-specific сегмент. Если не указан - Default из avatar.md.

### Шаг 8: Determine lang

Default: ru (автор primary RU). Если router явно сказал en - оставить en. Если original_lang == ru и user не сказал иначе - output ru (нет точки переключения).

### Шаг 9: Validate readiness

Перед handoff:
- voice_script_brief существует и не пустой
- narrative_arc содержит ≥2 beats
- main_insight существует
- duration_sec > 0

Если что-то отсутствует - explicit warning пользователю с предложением «дополнить card.md руками или re-ingest».

### Шаг 10: Strategy paragraph в чат

```
Стратегия Mode C:
- Исходник: <original_author> / <original_url> / <original_duration_sec>s
- Формат: <format_classification.primary>
- Главный insight: <main_insight 1 строкой>
- Целевой tier для replication: <length_tier>
- Язык: <lang>
- Сегмент аудитории: <segment>
```

### Шаг 11: Handoff к 02-finalize.md

Передать brief YAML.

## Hard rules

- Никогда не угадывать оригинал. card.md = source of truth. Если поля нет - спросить или escape.
- Дословный перенос цитат, не парафраз. Терминология автора важнее переформулирования.
- Не атаковать автора оригинала по имени. Враг = явление, оригинал = inspiration.
- Длительность replication = original_duration_sec ± 20%. Не растягивать 30-sec ролик в 90-sec без явного intent.

## Anti-patterns

- Inline переписывание скрипта здесь (это работа 04-write.md, тут только brief)
- Игнор card.md visual_layers (важно для production handoff - потом передать в 06-output.md)
- Перевод дословный (RU = история→вывод, EN = тезис→аргументы - см. `references/ru-en-adaptation-rules.md`)
- Сохранение оригинальных captions автора в captions[] (memory `feedback_strip_competitor_captions` - strip)
- Использование «Instagram» если в card.md так написано - auto-correct в «Нельзяграм» уже на этом этапе

## Связано

- Upstream skill: `ingest-reel` (создаёт card.md)
- Parallel skill: `replicate-reel` (в v1.0 имеет свой inline Шаг 4 - дублирование, рефакторинг в v1.1)
- Downstream production: `replicate-reel` (Remotion render по spec) или `screen-record-face-cam` если formit_type = build-with-me и автор хочет переснять руками
