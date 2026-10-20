# 01a - Mode A (Plan)

> Берёт смысл недели из Карты смыслов запуска или контент-плана longform и превращает в brief для longform.

## Шаги

### Шаг 1 - определить источник

Приоритет источников (по config):
1. `paths.longform_content_plan` - если задан и существует
2. `paths.content_map` - Карта смыслов активного запуска
3. `paths.content_topics_extra[]` - дополнительные карты инфоповодов

Если ни один не доступен → fallback на Mode B2 (генерация под JTBD).

### Шаг 2 - найти запись на текущую неделю

#### Если `content_map_format = calendar`
- Найти строку с датой текущей недели (Mon-Sun)
- Один смысл = одна неделя для longform

#### Если `content_map_format = thematic`
- Найти текущую активную тему (помечена `[active]` / `[current]` / нет даты завершения)
- Если несколько активных - взять верхнюю

#### Если `content_map_format = hybrid`
- Сначала проверить calendar записи, затем thematic

### Шаг 3 - извлечь brief

Из найденной записи извлечь:
- **Topic** (один-два слова, главный смысл)
- **Main thesis** (центральный тезис, который раскрывается)
- **Audience pain** (какой pain закрывается)
- **Outcome shift** (как меняется представление читателя после)
- **Personal anchor** (чем автор лично связан с темой - из voice corpus / story bank)
- **Distribution hint** (если есть метка какой канал primary)

Если каких-то полей нет в Карте смыслов - попытаться извлечь из:
- `paths.brand_dna` раздел «15. Карта инфоповодов»
- `paths.story_bank_dir` (для personal anchor)
- `paths.objections` (для audience pain)

### Шаг 4 - проверить type rotation

Прочитать `paths.recent_articles_*` (последние N статей). Извлечь типы (teaching / story / framework / etc.). Проверить:
- Какой тип НЕ использовался последние `voice.type_rotation_window` (3 по умолчанию)
- Подсказать его как preferred для текущего brief

Если все типы уже использовались - выбрать тот, который лучше подходит под `Main thesis` и `Outcome shift`.

### Шаг 5 - собрать brief

```yaml
mode_a_brief:
  source: "<file path + section anchor>"
  topic: "<главный смысл>"
  main_thesis: "<центральный тезис>"
  audience_pain: "<pain>"
  outcome_shift: "<shift>"
  personal_anchor: "<story moment / quote из voice corpus>"
  type_preferred: "<teaching | story | framework>"  # по rotation rule
  distribution_hint: "<canonical | newsletter | linkedin>"
  language: "<from router>"
  platform: "<from router>"
```

### Шаг 6 - pass дальше

Передать `mode_a_brief` в `01-finalize.md`.

## Edge cases

- **Пустая запись на текущую неделю** → fallback на Mode B2 c пометкой «контент-план пуст, генерим под JTBD»
- **Запись есть, но без main_thesis / outcome_shift** → задать 1 уточняющий вопрос пользователю
- **Несколько активных тем** → показать список и спросить выбор (Telegram-friendly, plain text)

## Что НЕ делать

- НЕ выдумывать main_thesis если нет в Карте смыслов - Карта смыслов = source of truth
- НЕ парафразировать personal anchor - переносить дословно из story bank
- НЕ навязывать тип статьи если в Карте смыслов он явно указан

## Memory cross-refs

- - метод через логику, не кейсы
- - дословный перенос цитат
- - цитировать предпосылки
- - не выдумывать факты