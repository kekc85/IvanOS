# 01-finalize - общая доводка brief

> Принимает `mode_<a|b|c>_brief` из mode-файла. Доводит до полного brief для `02-structure.md`. Тип + hook + target length + platform spec.

## Step 1 - type detection / confirmation

Если в brief уже есть `type_preferred` / `type_chosen` - берём его. Если нет - auto-detect:

| Сигнал в brief | Type |
|---|---|
| `main_thesis` содержит «механизм», «как работает», step-by-step intent | Teaching |
| `personal_anchor` сильнее `main_thesis`, есть story arc | Story |
| `main_thesis` = новый mental model / переопределение | Framework |
| `main_thesis` = myth vs reality | Contrarian (v1.1) |
| `main_thesis` = «кейс ученика / клиента» | Case study (v1.1) |
| `main_thesis` = «N принципов» (где N ≤ 7) | Listicle anti-generic (v1.1) |
| `main_thesis` = research-heavy multi-layer | Deep-dive (v1.2) |

**v1.0:** если detected type не teaching/story/framework - fallback на ближайший из трёх с warning. v1.1 + раскроет полный список.

## Step 2 - type rotation gate

Прочитать `paths.recent_articles_*` (последние N статей, по умолчанию 5).

Если выбранный type использовался в последних `voice.type_rotation_window` статей подряд - предложить альтернативу:

```
Последние 3 статьи были teaching. Этот тоже teaching.
Альтернативы: story (личная история про эту тему) / framework (новый mental model).
Оставить teaching или switch?
```

Override: `--type=<type>` в input игнорирует rotation gate.

## Step 2.5 - topic recency check (v1.0 fix L4.2)

Защита от повторов одной темы дважды за короткое время (idempotency / repeat detection).

### Read recent articles

Read `paths.recent_articles_*` (последние 30 дней или последние 10 статей, whichever меньше).

Для каждой recent article извлечь:
- topic (одна-две главные сущности)
- main_thesis (если есть в metadata)
- date

### Similarity check

Сравнить `brief.topic` с topic'ами recent articles по 3 dimensions:

| Dimension | Threshold | Severity |
|---|---|---|
| Exact topic match | identical phrase | FAIL (block) |
| Lemma overlap >70% | substring match of normalized lemmas | WARN (proceed с предупреждением) |
| Same JTBD / audience pain | semantic similarity (через прочтение recent article main_thesis) | WARN |
| Same type + same topic family | teaching про X + teaching про X' | WARN |

### Resolution per severity

**FAIL (exact topic match in last 30 days):**
```
Точный повтор темы: "X" уже опубликована DD.MM (<canonical_url>).
Варианты:
1. Сменить angle (теперь story вместо teaching про ту же тему)
2. Сделать part 2 / follow-up (явно ссылается на первую)
3. Отказаться (block)

Выбери 1/2/3 или --force чтобы пропустить gate.
```

**WARN (lemma overlap или same JTBD):**
```
Похожая тема была недавно: "Y" (DD.MM, <type>).
Текущая тема "X" частично пересекается.
Продолжаем? (y/n/show-previous)
```

### Override

`--force-topic` флаг в input игнорирует topic recency gate.

### Memory cross-ref

 - идемпотентность как системное правило.

## Step 3 - target length

Базируется на `platforms.<platform>.length_floor` + `length_ceiling`.

| Platform | Floor | Ceiling | Default target |
|---|---|---|---|
| Personal blog | 1200 | 3000 | 1800 |
| Newsletter (Kit / Beehiiv) | 1000 | 2200 | 1500 |
| LinkedIn article | 800 | 1800 | 1300 |
| Substack cross-post | inherit canonical | inherit canonical | inherit canonical |

Type modifier:
- Story essay → ниже target (1000-1600)
- Teaching essay → средний target (1300-1800)
- Framework essay → выше target (1500-2000)
- Deep-dive → ceiling-1000 до ceiling (для v1.2)

Финальный target = baseline + type modifier. Записать в brief.

**Приоритет при объявленной цели формы (канон v2, §3 и §8.2).** Таблица выше не удалена и работает как раньше, но при объявленной `form_goal` коридор длины для гейтов берётся из `brief.form_profile` (`length_min` / `length_max`), а таблица платформ и типов даёт только `target` и пол выше профиля НЕ поднимает. Пока цель не объявлена, таблица работает без изменений, включая пол платформы, но статья в этом состоянии не выпускается: `L1-form-mode` даёт FAIL с возвратом в `01-router.md` Step 5.5 FORM-GOAL ROUTER

## Step 4 - hook crafting (3 варианта)

Сгенерировать 3 варианта hook (первая строка статьи + первая строка newsletter subject если platform=newsletter).

Источник паттернов - `references/hook-patterns-longform.md`. Базовые паттерны:

| Pattern | Применение |
|---|---|
| Counter-intuitive opener | «Most <niche> advice is wrong.» |
| Confession + pivot | «Я <time> делал X и заработал $0...» |
| Specific outcome + mystery | «Из $0 в $<N>/мес. Вот workflow.» |
| Quote-the-question | «Каждый день мне пишут: <exact question>» |
| Re-framing | «X - не <common belief>. X - это <new frame>.» |
| Personal moment | «Вчера ученик прислал скрин. На нём <observation>.» |

Hook должен:
- ≤ 12 слов
- Иметь либо counter-intuitive claim, либо personal anchor, либо specific outcome
- НЕ начинаться с «В этой статье я разберу» (banned, linked formulaic)
- НЕ содержать em-dash «-» внутри строки

Записать 3 hook варианта в brief. Финальный выбор делает `02-structure.md` или пользователь через `--hook=<n>`.

## Step 5 - platform-specific brief

Прочитать `references/platform-specs.md` для текущей платформы. Добавить в brief:

```yaml
platform_spec:
  platform: "<blog | newsletter | linkedin>"
  target_length: <N>
  subject_required: <bool>  # true для newsletter
  preheader_required: <bool>  # true для newsletter
  headline_strategy: "<seo_h1 | subject_ab | linkedin_friendly>"
  format_mode: "<markdown | html | linkedin_plain>"
  rel_canonical: "<true | false>"
```

## Step 6 - language pivot

Если `language = ru`:
- Структурный модификатор: story-first (личная история открывает, аргумент закрывает)
- Lexicon: применить `lexicon_required` replacements (Instagram → Нельзяграм)

Если `language = en`:
- Структурный модификатор: argument-first (тезис открывает, story илюстрирует)
- Lexicon: skip RU-replacements, применить EN-specific banned (`Now let me tell you`, etc.)

Если `language = both` или `bilingual_mode != single`:
- Сначала генерим canonical version (по `bilingual_mode`)
- Adapted version планируется отдельно (в v1.0 - заметка для пользователя что adapted надо запустить отдельной командой)

Details - `references/ru-en-adaptation.md`.

## Step 6.5 - перенос полей формы из роутера (HARD, канон формы v2)

Цель формы рождается в `01-router.md` **Step 5.5 FORM-GOAL ROUTER** и здесь только ПЕРЕНОСИТСЯ в финальный brief. Пересчитывать, доопределять или угадывать её на этом шаге запрещено: `02-structure.md`, `03-write.md` и `04-review.md` читают `brief.form_goal` / `brief.form_profile`, и если поля не доехали до `finalized_brief`, статью выпускать нельзя - `L1-form-mode` даёт FAIL с возвратом в роутер.

Переносить как есть, поле в поле, из `router_output`:

| поле в `router_output` | поле в `finalized_brief` | правило переноса |
|---|---|---|
| `form_goal` | `form_goal` | слово `reactions` / `forwards` / `sales`; в longform `gate` не бывает (роутер 5.5.4). Это единственное значение для сравнений в гейтах |
| `form_goal_letter` | `form_goal_letter` | буква `R` / `F` / `S`, ТОЛЬКО для печати улики человеку, сравнивать по ней запрещено |
| `form_class` | `form_class` | `narrative` / `razbor` / `sales` |
| `form_topic` | `form_topic` | тема одной фразой |
| `form_scope` | `form_scope` | `body` (профиль применяется к телу статьи) |
| `form_profile` | `form_profile` | объект целиком, без пересчёта; `length_min` внутри - число (`0` = пол снят), не `null` |
| `form_evidence_line` | `form_evidence_line` | строка-улика формы из роутера в формате `цель=<слово> (<буква>) класс=<латиница>`, пробрасывается дословно |

Поле в роутере пустое → переносить пустым (`null`). Подставлять значение по догадке, «по типу статьи» или «по платформе» запрещено.

**Одно имя объекта.** `finalized_brief` этого шага и есть тот `brief`, из которого `02-structure.md`, `03-write.md` и `04-review.md` читают `brief.form_goal` / `brief.form_profile`. Второго объекта с полями формы в конвейере нет, копий не заводить.

**Проверка переноса (печатается всегда, одной строкой).** После сборки brief финализация печатает:

```
форма (перенос в brief): цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> профиль=<есть/нет> scope=body
```

Если `form_goal` пуст, печатается ровно это, и умолчать нельзя:

```
форма (перенос в brief): цель=не объявлена -> профиль не перенесён, конвейер остановлен. Возврат: 01-router.md Step 5.5 FORM-GOAL ROUTER, дерево канона §2.1
```

Пустая цель - не рабочий режим, а остановка: brief в таком виде дальше не идёт, молчаливый пропуск запрещён, `L1-form-mode` в `04-review.md` на этом же основании даёт FAIL с адресом возврата.

Такую же строку печатать, если `form_goal` объявлена, а `form_profile` пуст: это разрыв проводки, чинится там же.

## Step 7 - финальный brief

```yaml
finalized_brief:
  mode: "<A | B1 | B2 | C>"
  type: "<teaching | story | framework | ...>"
  topic: "<>"
  main_thesis: "<>"
  audience_pain: "<>"
  outcome_shift: "<>"
  personal_anchor: "<>"
  language: "<ru | en | both>"
  platform: "<blog | newsletter | linkedin>"
  target_length: <N>
  hook_variants: ["<1>", "<2>", "<3>"]
  platform_spec:
    <...>
  voice_signals: [<>]  # если из Mode C
  type_rotation_warnings: [<>]
  # --- форма (канон v2), перенос из router_output без пересчёта, см. Step 6.5 ---
  form_goal: "<reactions | forwards | sales | null>"        # слово, значение для гейтов
  form_goal_letter: "<R | F | S | null>"                    # буква, только для печати улики
  form_class: "<narrative | razbor | sales | null>"
  form_topic: "<тема одной фразой | null>"
  form_scope: "body"
  form_profile: {<объект из роутера Step 5.5.5>} | null     # length_min - число (0 = пол снят)
  form_evidence_line: "<строка-улика формы из роутера | null>"
```

## Pass дальше

→ `02-structure.md` с `finalized_brief`.

## Memory cross-refs

- - финализация brief = strategy перед write
- - Шаг 1 видение, Шаг 2 предпосылки, Шаг 3 процесс
---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.
