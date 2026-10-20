# workflow/01-finalize.md

> Доводка brief: detect type / длину / CTA-goal / archetype rotation. Общая часть после mode-handler.

## Inputs

- `brief` (из mode-handler)
- `config`

## Steps

### Step 1 - Detect letter type

Type из 8 типов (v1 = 3 типа):

| Сигнал | Type |
|---|---|
| brief.mode == "plan" AND sequence_position != null | **launch-sequence** |
| brief.mode == "plan" AND source == funnel_map AND cta_goal == "buy" / "checkout" | **sales-letter** |
| brief.mode == "plan" AND default funnel position | **nurture-letter** |
| brief.mode == "spark-b1" / "spark-b2" AND suggested_letter_type set | use suggested |
| brief.mode == "transcript" AND letter_type_fit set | use fit |
| else | default to **nurture-letter** |

**v2+ types (planned, не v1):** weekly-digest / re-engagement / welcome-email / abandoned-cart / announcement.

Если ученик попросил один из v2 типов - ответить: «Тип <X> планируется в v2. Сейчас доступны nurture / launch / sales. Какой использовать?»

### Step 2 - Determine length range

Из config.email:

```yaml
nurture: 600-900 words
launch: 500-1200 words
sales: 800-1500 words
```

Set `brief.target_words_min` + `brief.target_words_max`.

### Step 3 - Lock CTA goal

```
IF brief.cta_goal_hint == "<TBD>" OR not set:
    ask: "Какая цель письма? (clicker → лендинг / клик в клуб / клик в продукт checkout / клик на эфир / read more)"
ELSE:
    cta_goal = brief.cta_goal_hint
```

→ `brief.cta_goal` (locked).

**Правило:** ровно 1 цель письма. Если ученик хочет «и туда и сюда» - fail + split на 2 письма.

### Step 4 - Archetype rotation

```
recent_archetypes = read last config.voice.rotation_window emails from config.paths.recent_emails_dir
allowed_archetypes = config.voice.archetypes_allowed
banned_archetypes = config.voice.archetypes_banned
available_archetypes = allowed_archetypes - recent_archetypes  # exclude recently used
```

Если `available_archetypes` пустой (все archetypes использованы недавно):
- expand rotation_window (e.g. config.voice.rotation_window + 2) и пересчитать

Lock `brief.archetype`.

### Step 5 - Sequence-position validation (только для launch-sequence)

```
IF brief.type == "launch-sequence":
    require brief.sequence_position != null
    require brief.sequence_context.type in ["pre-launch", "launch-day", "open-cart", "close-cart"]
    require brief.sequence_context.pre + post exist
```

Если что-то отсутствует → fail с подсказкой «дозаполни launch-sequence-map».

### Step 5.5 - Перенос полей формы из роутера (HARD, канон формы v2)

Цель формы рождается в `01-router.md` **Step 5.5 FORM-GOAL ROUTER** и здесь только ПЕРЕНОСИТСЯ в финальный brief. Пересчитывать и доопределять её на этом шаге запрещено: `02-structure.md`, `03-write.md` и гейты `04-review.md` (`1.5 Body length`, `1.9 Bullet count`, `EMAIL-G12`) читают `brief.form_goal` / `brief.form_profile`, и если поля не доехали до финального brief, письмо выпускать нельзя - `EMAIL-G12` даёт FAIL с возвратом в роутер.

Переносить поле в поле, как есть, из output роутера:

| поле роутера | поле финального brief | правило переноса |
|---|---|---|
| `form_goal` | `form_goal` | слово `reactions` / `forwards` / `sales`; в email `gate` не бывает (роутер, «режим A недоступен в email»). Только это значение сравнивают гейты |
| `form_goal_letter` | `form_goal_letter` | буква `R` / `F` / `S`, ТОЛЬКО для печати улики `EMAIL-G12`, сравнивать по ней запрещено |
| `form_class` | `form_class` | `narrative` / `razbor` / `sales` |
| `form_topic` | `form_topic` | тема одной фразой |
| `form_scope` | `form_scope` | `body` (профиль -> тело письма, хук профиля -> Subject) |
| `form_profile` | `form_profile` | объект целиком, без пересчёта порогов |
| `form_evidence_line` | `form_evidence_line` | строка-улика формы в формате `цель=<слово> (<буква>) класс=<латиница>`, пробрасывается дословно |

Поле в роутере пустое → переносить пустым (`null`), значение по догадке («тип письма же sales») не подставлять.

**Проверка переноса (печатается всегда, одной строкой):**

```
форма (перенос в brief): цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> профиль=<есть/нет> scope=body
```

Если `form_goal` пуст, печатается ровно это, умолчать нельзя:

```
форма (перенос в brief): цель=не объявлена -> профиль не перенесён, конвейер остановлен. Возврат: 01-router.md Step 5.5 FORM-GOAL ROUTER, дерево канона §2.1
```

Пустая цель - не рабочий режим, а остановка: brief в таком виде дальше не идёт, `EMAIL-G12` на том же основании даёт FAIL с адресом возврата. Ту же строку печатать, когда цель объявлена, а `form_profile` пуст: это разрыв проводки, чинится там же.

### Step 6 - Output brief

Финальный brief:

```yaml
brief:
  mode: plan | spark-b1 | spark-b2 | transcript
  type: nurture-letter | launch-sequence | sales-letter
  language: ru | en | both
  topic_or_meaning: "<тема / смысл>"
  cta_goal: "<conversion goal - locked>"
  target_words_min: N
  target_words_max: M
  archetype: "Magician | Sage | Outlaw"
  sequence_position: "<N или null>"
  sequence_context: {...}
  audience_hint: "<из avatar>"
  source_quotes: []
  source_hook_verbatim: "<или null>"
  # --- форма (канон v2), перенос из роутера без пересчёта, см. Step 5.5 ---
  form_goal: "<reactions | forwards | sales | null>"     # слово, значение для гейтов
  form_goal_letter: "<R | F | S | null>"                 # буква, только для печати улики
  form_class: "<narrative | razbor | sales | null>"
  form_topic: "<тема одной фразой | null>"
  form_scope: "body"
  form_profile: {<объект из роутера Step 5.5 п.6>} | null
  form_evidence_line: "<строка-улика формы из роутера | null>"
```

→ `workflow/02-structure.md`.

## Anti-patterns

- НЕ менять `cta_goal` после Step 3 - locked. Если ученик после write хочет другой CTA - re-run pipeline с новым brief
- НЕ выходить за `target_words_max` без user re-approval - длина = договор
- НЕ повторять archetype из rotation_window - это убивает разнообразие feed
- НЕ запускать `workflow/02-structure.md` без всех required fields в brief - это fail
- НЕ терять и НЕ пересчитывать поля формы (`form_goal` / `form_goal_letter` / `form_class` / `form_profile`): они рождаются в роутере, здесь только переносятся. Потеря = `EMAIL-G12: FAIL` и возврат в `01-router.md` Step 5.5, а не работа на старых порогах
- НЕ сравнивать ни один гейт с буквой `form_goal_letter`: буква живёт только в печати улики, значение для сравнений - слово `form_goal`
---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.
