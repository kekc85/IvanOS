# Workflow 01a: Mode A - Plan (из Карты смыслов)

Тянет смысл дня из Карты смыслов запуска. Если запись пустая - fallback на Mode B2.

## Шаги

### Step 1: Read content_map

```bash
content_map_path=$(yq '.paths.content_map' config.md)
```

Если `null` → нет активной Карты, fallback `01b-spark.md` Mode B2.

Прочитать `content_map_path`. Найти запись по:
- Сегодняшней дате (`config.content_map_format = "calendar"`)
- Активной тематике (`config.content_map_format = "thematic"`)
- Гибрид (`config.content_map_format = "hybrid"`) - сначала по дате, потом по теме если дата пустая

### Step 2: Extract topic

Из найденной записи извлечь:
- **Тема** дня - 1 предложение
- **Угол** - acceptable angles (если указаны)
- **Аватар-segment** (если запись targets конкретный segment)
- **Visual slot** - если в записи есть пометка «нужна картинка» / explicit image brief

Если visual slot НЕ упоминается, но тема image-friendly → продолжать (это нормально).

### Step 3: Suggest type per topic

На основе topic semantics:

| Семантика topic | Suggested type |
|---|---|
| Mental model / framework / how-it-works | concept-diagram |
| Number / result / milestone | dashboard-screenshot |
| Cultural moment / commentary | meme |
| Pocket-wisdom / aphorism | quote-card |
| Transformation / case / before-after | before-after |

Это suggestion для 02-finalize. Пользователь может override.

### Step 4: Recent images check

Если `config.recent_images_source != "none"`:
- Webfetch или прочитать локальный файл с историей картинок
- Сравнить: не был ли этот type использован в last 3 постах? (variety check)
- Если был - flag в hints, suggest альтернативный type

### Step 5: Output

```yaml
mode: "plan"
topic: "<extracted topic>"
hints:
  type_suggestion: "<один из 5>"
  platform_suggestion: "<из active_launch.primary_platform или null>"
  reference_creator: null  # выберется в 02-finalize
  visual_slot_explicit: true|false  # был ли явный image brief в Карте
  recent_variety_warning: "<какой type повторяется>"  # если есть
source_context: "Карта смыслов: <путь>, дата/тема: <запись>"
```

→ передать в `02-finalize.md`

## Fallback rules

**Если Карта пустая на эту дату/тему:**
1. Сообщить пользователю «Карта на <дата/тема> пустая»
2. Предложить:
   - Заполнить Карту вручную сейчас
   - Перейти на Mode B2 (генерация идей под avatar/JTBD)
   - Перейти на Mode B1 (если пользователь готов дать topic)

**Если Карта существует, но запись неясная:**
1. Показать запись пользователю
2. Спросить «расширить как X, Y или Z?» - предложить 3 интерпретации
3. С ответом продолжать в 02-finalize

## Принципы

1. **Карта = source of truth.** Не дополнять, не выдумывать. Пустое = fallback.
2. **Suggest только.** type / platform / reference - всё suggestions, не decisions. Пользователь решает в 02-finalize.
3. **Variety check soft.** Если повтор type подряд - warning, но не блок.