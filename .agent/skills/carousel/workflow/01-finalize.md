# Workflow 01-finalize - Brief доводка перед structure

**Назначение:** доводка brief после mode-ideate перед `02-structure.md`. Family финал, slide count, platform spec, archetype check.
**Вход:** `brief` после Mode A/B/C/D
**Выход:** финальный `brief` с заполненными family + slide_count + platform_spec → `02-structure.md`

---

## Шаг 1 - Family final

Если `brief.family != null` → пропустить.

Иначе - задать family по правилам:

| Triger | Family |
|---|---|
| `topic` содержит «N инструментов / способов / ошибок» | listicle |
| `topic` содержит «N шагов / методология / фреймворк» | framework-breakdown |
| `topic` содержит «как я / кейс / история ученика» | story-case |
| `topic` содержит «революция / больше не нужен / новая категория» | panorama |
| `mode = reel-to-carousel` | reel-to-carousel (autoset) |
| Иначе | spawn 3 family-candidates, user выбирает |

---

## Шаг 2 - Slide count target

Из `config.family_specs.<family>.slide_count`:

- framework-breakdown: 8-12
- listicle: 8-10
- story-case: 10-12
- panorama: 3-8 (sweet spot 5)
- reel-to-carousel: зависит от длины Reel (см. conversion_table в `01d-reel-to-carousel.md`)

Установить `brief.slide_count_target = <среднее или Reel-derived>`.

---

## Шаг 3 - Platform spec

Из `config.platforms.<platform>`:

- IG: 1080×1350 / ≤10 slides / caption 2200 / hashtags 3-5 / CTA = comment→DM
- LinkedIn: 1080×1350 PDF / ≤20 / caption 3000 / hashtags 0-2 / CTA = newsletter|comment
- Both: cross-distribute (адаптировать caption per platform)

Установить `brief.platform_spec = {...}`.

---

## Шаг 4 - Archetype rotation check

Если `brief.archetype_hint` не выставлен:

1. Прочитать `config.voice.archetypes_allowed` (default: Magician / Sage / Outlaw для автора)
2. Прочитать last 3 carousels archetype если log есть
3. Выбрать archetype который НЕ повторялся последние `config.voice.rotation_window` (default 3)
4. Установить `brief.archetype = <chosen>`

---

## Шаг 5 - Length budget per slide

Из `config.family_specs.<family>.slide_text_budget`:

```yaml
brief.slide_text_budget:
  hook: [3, 12]              # words
  value: [5, 25]
  cta: [5, 15]
```

Для panorama:
```yaml
brief.slide_text_budget:
  leading: [3, 15]
  middle: [0, 10]
  payoff: [3, 15]
```

---

## Шаг 6 - Hook seed final

Если `brief.hook_seed` пустой → сгенерировать на основе topic + archetype + source_quotes:

**Hook formula:** number + outcome + timeframe (если данные есть)
- «<твоя выручка> за 12 месяцев. Без рекламного бюджета. История:»
- «8 ходов вайбмаркетинга. <число учеников> позже:»
- «Карусель про X. Если X - выходи листай:»

3 варианта hook → User choose (или auto top-1 если confidence high).

---

## Шаг 6.5 - Перенос полей формы из роутера (HARD, канон формы v2)

Цель формы рождается в `01-router.md` **Шаг 4.5 FORM-GOAL ROUTER** и здесь только ПЕРЕНОСИТСЯ в финальный brief. Пересчитывать её на этом шаге запрещено: `02-structure.md`, `03-write.md` и профильные ветки `04-review.md` (HV5/HV6 длины, HV8 нумерация, ссылки в caption, `form_mode`) читают `brief.form_goal` / `brief.form_profile`, и если поля не доехали до финального brief, весь профильный слой канона молча уходит в fallback.

Переносить поле в поле, как есть, из brief роутера:

| поле роутера (Шаг 4.5.7) | поле финального brief | правило переноса |
|---|---|---|
| `form_goal` | `form_goal` | слово `reactions` / `forwards` / `sales`; `gate` в карусели не выставляется (Шаг 4.5.6). Только слово сравнивают гейты |
| `form_goal_letter` | `form_goal_letter` | буква `R` / `F` / `S`, ТОЛЬКО для печати улики `form_mode`, сравнивать по ней запрещено |
| `form_class` | `form_class` | `narrative` / `razbor` / `sales` |
| `form_topic` | `form_topic` | тема одной фразой |
| `form_scope` | `form_scope` | `caption` (профиль -> caption; слайды -> `carousel-anatomy.md`) |
| `form_profile` | `form_profile` | объект целиком, без пересчёта порогов в слайды |
| `slides_source` | `slides_source` | `references/carousel-anatomy.md`, анатомия слайдов каноном не переопределяется |
| строка-улика Шага 4.5.8 | `form_evidence_line` | пробрасывается дословно |

Поле в роутере пустое → переносить пустым (`null`), значение по догадке («family же listicle») не подставлять: family на цель не влияет.

**Проверка переноса (печатается всегда, одной строкой):**

```
форма (перенос в brief): цель=<reactions|forwards|sales> буква=<R|F|S> класс=<...> профиль=<есть|нет> scope=caption
```

Если `form_goal` пуст, печатается ровно это, умолчать нельзя:

```
форма (перенос в brief): цель=не объявлена -> профиль не перенесён, output запрещён. Починка: 01-router.md Шаг 4.5 FORM-GOAL ROUTER, дерево канона §2.1
```

Пустая цель - НЕ легальное состояние и не повод писать по старым порогам: это HARD FAIL (Гейт 0, канон §9), пайплайн останавливается здесь же, `02-structure.md` и `03-write.md` за этим brief не запускать. `form_mode` в `04-review.md` на том же основании даёт FAIL с тем же адресом починки - это подтверждение, а не вторая точка входа. Ту же строку печатать, когда цель объявлена, а `form_profile` пуст: это разрыв проводки, тоже HARD FAIL, а не fallback.

---

## Шаг 7 - Передача в structure

Полный финальный brief:

```yaml
brief:
  mode: ...
  topic: "<final>"
  family: "<one of 5>"
  slide_count_target: <number>
  platform: "<ig | li | both>"
  platform_spec: {...}
  archetype: "<chosen>"
  slide_text_budget: {...}
  hook_seed: "<final>"
  source_quotes: [...]
  proof_elements: [...]
  mandatory_reads: {...}
  # --- форма (канон v2), перенос из роутера без пересчёта, см. Шаг 6.5 ---
  form_goal: "<reactions | forwards | sales | null>"     # слово, значение для гейтов
  form_goal_letter: "<R | F | S | null>"                 # буква, только для печати улики
  form_class: "<narrative | razbor | sales | null>"
  form_topic: "<тема одной фразой | null>"
  form_scope: "caption"
  form_profile: {<объект из роутера Шаг 4.5.7>} | null
  slides_source: "references/carousel-anatomy.md"
  form_evidence_line: "<строка-улика формы из роутера | null>"
```

Перейти в `workflow/02-structure.md`.

---

## Принципы

1. **Family final BEFORE structure.** Без family - structure не знает какой template применять.
2. **Slide count derived from family + platform.** Не выдумывать произвольно.
3. **Archetype rotation hard.** Через config.voice.rotation_window.
4. **Hook seed verifiable.** Числа / timeframes / outcomes - только из `.business/`.
5. **One platform primary.** Если both - pick primary для slide count budget, secondary получит cross-adapt в publish.
6. **Поля формы переносятся, а не рождаются.** `form_goal` / `form_goal_letter` / `form_class` / `form_profile` приходят из роутера и уходят дальше без пересчёта; потеря поля = молчаливый fallback всех профильных гейтов, поэтому перенос печатается строкой (Шаг 6.5).
7. **Сравнение только по слову.** Значение цели для любых сравнений - слово `form_goal`; буква `form_goal_letter` живёт исключительно в печати улики человеку.
---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.
