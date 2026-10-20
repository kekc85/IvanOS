# 01-finalize.md - Brief finalization

Принимает handoff от 01a/01b/01c. Финализирует brief перед structure stage.

## Step 1 - Validate handoff

Все обязательные поля заполнены:
- `mode` (plan / spark-b1 / spark-b2 / transcript)
- `platform_target` (x / threads / both)
- `language` (ru / en)
- `recommended_type` (1 of 7)
- `recommended_format` (single / mini-thread / mega-thread)
- `char_zone_target` (A / B)
- `archetype` (Magician / Sage / Outlaw)

Если что-то отсутствует - derive из defaults или ask user.

## Step 2 - Confirm archetype rotation

Read last 3 posts (если есть):
- Если proposed archetype == one of last 3 → switch (Magician → Sage → Outlaw)

## Step 3 - Confirm voice cluster

Cross-check: chosen type vs voice register из `config.voice.primary_register`.

| Type | Compatible registers |
|---|---|
| Single punchline | aphorism / spiky |
| PAIPS story | paips-story |
| Spiky one-liner | spiky |
| Numbered list mini-thread | idea-drop |
| Story / news mega-thread | paips-story / idea-drop |
| Contrarian take | spiky / aphorism |
| How-I-did demo | build-in-public |

Если type не compatible с primary register → ask user, или swap type на compatible.

## Step 4 - Determine cross-post strategy

| platform_target | X output | Threads output |
|---|---|---|
| x-only | Yes | No |
| threads-only | No | Yes |
| both | Yes (primary) | Yes (adapt: 280 → 500 chars expansion если есть room) |

## Step 4.5 - Перенос полей формы из роутера (HARD, канон формы v2)

Цель формы рождается в `01-router.md` **Step 5.5 FORM-GOAL ROUTER** и здесь только ПЕРЕНОСИТСЯ в `brief_final`. Пересчитывать её на этом шаге запрещено: `02-structure.md`, `03-write.md` и профильные гейты `04-review.md` (включая `form_mode`) читают `brief.form_goal` / `brief.form_profile`, и если поля не доехали до финального brief, весь профильный слой канона молча уходит в fallback.

Переносить поле в поле, как есть, из handoff роутера:

| поле роутера | поле `brief_final` | правило переноса |
|---|---|---|
| `form_goal` | `form_goal` | слово `reactions` / `forwards` / `sales`; `gate` в этом скилле не выставляется. Только слово сравнивают гейты |
| `form_goal_letter` | `form_goal_letter` | буква `R` / `F` / `S`, ТОЛЬКО для печати улики `form_mode`, сравнивать по ней запрещено |
| `form_class` | `form_class` | `narrative` / `razbor` / `sales` |
| `form_topic` | `form_topic` | тема одной фразой |
| `form_scope` | `form_scope` | `unit+thread` (профиль и к твит-единице, и к треду целиком) |
| `form_profile` | `form_profile` | объект целиком, без пересчёта; `length_unit_max` внутри остаётся HARD-лимитом платформы |
| `form_evidence_line` | `form_evidence_line` | строка-улика формы, пробрасывается дословно |

Поле в роутере пустое → переносить пустым (`null`), значение по догадке («тред же про продукт») не подставлять.

**Одно имя объекта.** `brief_final` этого шага и есть тот `brief`, из которого `02-structure.md`, `03-write.md` и `04-review.md` читают `brief.form_goal` / `brief.form_profile`. Второго объекта с полями формы в конвейере нет, копий не заводить.

**Проверка переноса (печатается всегда, одной строкой):**

```
форма (перенос в brief): цель=<reactions|forwards|sales> буква=<R|F|S> класс=<...> профиль=<есть|нет> scope=unit+thread
```

Если `form_goal` пуст, печатается ровно это, умолчать нельзя:

```
форма (перенос в brief): цель=не объявлена -> профиль не перенесён, output запрещён. Починка: 01-router.md Step 5.5 FORM-GOAL ROUTER, дерево канона §2.1
```

Пустая цель - НЕ легальное состояние и не повод писать по старым порогам: это HARD FAIL (Гейт 0, канон §9), пайплайн останавливается здесь же, `02-structure.md` и `03-write.md` за этим brief_final не запускать. `form_mode` в `04-review.md` на том же основании даёт FAIL с тем же адресом починки - это подтверждение, а не вторая точка входа. Ту же строку печатать, когда цель объявлена, а `form_profile` пуст: это разрыв проводки, тоже HARD FAIL, а не fallback.

## Step 5 - Build final brief

```yaml
brief_final:
  mode: <from handoff>
  platform_target: <from handoff>
  language: <from handoff>
  type: <1 of 7>
  format: <single | mini-thread N tweets | mega-thread N tweets>
  hook_pattern: <1 of 15 from viral-hooks-2026-x.md>
  char_zone_target: A | B
  archetype: <chosen>
  voice_cluster: <derived>
  proof_assets: [<from 01a/01b/01c>]
  cta: <newsletter | community | reply | null>
  cross_post: x | threads | both
  # --- форма (канон v2), перенос из роутера без пересчёта, см. Step 4.5 ---
  form_goal: <reactions | forwards | sales | null>      # слово, значение для гейтов
  form_goal_letter: <R | F | S | null>                  # буква, только для печати улики
  form_class: <narrative | razbor | sales | null>
  form_topic: "<тема одной фразой | null>"
  form_scope: unit+thread
  form_profile: {<объект из роутера Step 5.5.7>} | null
  form_evidence_line: "<строка-улика формы из роутера | null>"
```

→ Hand off to `02-structure.md`.

## Anti-patterns

- НЕ proceed без confirmation type vs register compatibility
- НЕ skip archetype rotation check
- НЕ default proof_assets - null если из mode нет
- НЕ assume cross_post = both - explicit decision required
- НЕ терять и НЕ пересчитывать поля формы (`form_goal` / `form_goal_letter` / `form_class` / `form_profile`): они рождаются в роутере, здесь только переносятся. Потеря = молчаливый fallback всех профильных гейтов
- НЕ сравнивать ни один гейт с буквой `form_goal_letter`: буква живёт только в печати улики, значение для сравнений - слово `form_goal`
---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.
