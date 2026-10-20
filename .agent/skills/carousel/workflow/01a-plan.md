# Workflow 01a - Mode A: Plan (из Карты смыслов)

**Назначение:** взять смысл дня из Карты смыслов запуска, превратить в carousel brief.
**Вход:** `brief.mode = "plan"` + `brief.subject_name` + `paths.content_map`
**Выход:** обогащённый `brief` с topic + target_segment + product_anchor + intent → передача в `01-finalize.md`

---

## Шаг 1 - Read Карта смыслов

Прочитать `paths.content_map` (с подстановкой `<active-launch>` из `config.active_launch.<lang>`).

Если файл не существует → fallback на Mode B2 (генерация идей), сообщить пользователю.

Извлечь:
- Запись на сегодняшнюю дату (или явно указанную пользователем)
- Если формат `thematic` - выбрать смысл из текущей темы дня
- Если формат `calendar` - взять запланированный смысл

Пометить в `brief.mandatory_reads.content_map = true`.

---

## Шаг 2 - Read контекст автора

Параллельно прочитать:

1. `paths.avatar` → primary segment для этого смысла
2. `paths.jtbd` → JTBD который смысл закрывает
3. `paths.brand_dna` → archetype + voice signals
4. `paths.products_dir/<relevant>.md` → продукт-якорь (если смысл связан с конкретным продуктом)
5. `paths.objections` → возражения которые смысл преодолевает (для CTA-формулировки)

Пометить соответствующие `mandatory_reads = true`.

---

## Шаг 3 - Read recent carousels (no-repeat check)

Если `paths.recent_carousels_source != none`:

- `webfetch` → последние N постов из IG канала (фильтр carousel posts по >1 image)
- `file` → читать `paths.recent_carousels_log` если есть
- `manual` → пропустить (ученик ещё не вёл архив)

Извлечь:
- Темы последних 5 carousels
- Family каждого (framework / listicle / story / panorama)
- Какие реальные продукты упоминались

**No-repeat rule:** если сегодняшний смысл уже был раскрыт за 7 дней - flag и предложить: сменить угол / перенести / force-override.

---

## Шаг 4 - Карта смысла → carousel brief

Из записи Карты смыслов извлечь:

```yaml
brief:
  topic: "<краткая формулировка смысла из карты>"
  target_segment: "<кому адресовано - из avatar>"
  product_anchor: "<продукт-якорь если есть - из products>"
  intent: "<top-funnel | mid-funnel | bottom-funnel>"
  source_quotes: ["<verbatim фразы из Карты смыслов>"]
  archetype_hint: "<из brand_dna - rotation_check>"
```

**Archetype rotation:** проверить что предложенный archetype не повторяется последние `config.voice.rotation_window` carousels (default 3). Если повторяется - выбрать другой из `archetypes_allowed`.

---

## Шаг 5 - Family hint (если очевидно)

Если router уже выставил `brief.family` → не трогать.

Иначе предложить family по характеру смысла:
- «N инструментов / N способов / N ошибок» → `family = listicle`
- «X шагов / Y фаз / методология» → `family = framework-breakdown`
- «как я / мой кейс / история ученика» → `family = story-case`
- «X больше не нужен / революция / новая категория» → `family = panorama`
- Иначе → `family = null` (определит `02-structure.md`)

---

## Шаг 6 - Передача в finalize

Перейти в `workflow/01-finalize.md`.

---

## Принципы

1. **Карта смыслов = source of truth.** Не дополнять, не выдумывать. Пустая запись = fallback на Mode B2.
2. **Дословный перенос смысла.** Verbatim quotes из Карты в `source_quotes`. Не пересказ.
3. **No-repeat hard.** Повтор темы за 7 дней - флаг.
4. **Archetype rotation strict.** Через `config.voice.rotation_window`.
5. **Single carousel per call.** Один смысл = одна карусель.