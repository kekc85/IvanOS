# Workflow 01 - Router (Mode + platform detection)

**Назначение:** определить mode (Plan / Spark / Transcript / Reel-to-carousel), platform (IG / LinkedIn / both), family (если очевидно), передать управление дальше.
**Входы:** raw user input + `config.md`
**Выходы:** `brief.{mode, platform, family?, subject, raw_input}` + переход в следующий workflow

---

## Шаг 0 - Read config

Прочитать `config.md` (рядом с SKILL.md). Извлечь:

- `subject.name`, `subject.language`, `subject.primary_platforms`
- `paths.content_map`, `paths.reel_ingest_dir`
- `active_launch.<lang>` для подстановки в `<active-launch>`
- `validation.banned_ai_imagery_last_review` + `refresh_days` (default 14)
- `validation.banned_lexicon_last_review` + `refresh_days` (default 7)

Если `config.md` отсутствует → перейти в `00-onboarding-student.md`.

---

## Шаг 0.5 - Refresh checks

Посчитать `days_since` для banned_ai_imagery и banned_lexicon. Если > refresh_days → warning в чат, не блокировать.

---

## Шаг 1 - Mode detection (auto-detect)

Проверять сигналы **в строгом порядке** (первый сработавший побеждает):

### Mode D - Reel-to-carousel

**Признаки:**
- User input содержит URL (instagram.com/reel/* | tiktok.com/* | youtube.com/shorts/*)
- ИЛИ phrases: «перегони рилз в карусель», «из этого ролика карусель», «карусель из видео», «reel to carousel»
- ИЛИ флаг `--reel <url>` или `--mode=reel-to-carousel`
- ИЛИ путь к существующему `card.md` от `ingest-reel`

→ `brief.mode = "reel-to-carousel"`, перейти в `01d-reel-to-carousel.md`.

**Если URL дан но card.md не существует:** сначала запустить `ingest-reel` chain, потом продолжить с готовым card.md.

### Mode C - Transcript

**Признаки:**
- Длина user-input > 500 символов
- ИЛИ phrases: «надиктовал», «надиктовка», «мои мысли», «вот текст», «расшифровка», «послушай, я сейчас расскажу»
- ИЛИ файл с длинным текстом

→ `brief.mode = "transcript"`, перейти в `01c-transcript.md`.

### Mode A - Plan

**Признаки:**
- `/carousel` БЕЗ аргументов
- ИЛИ phrases: «по плану», «по карте», «смысл дня», «сегодняшний смысл»
- ИЛИ упомянута дата

**Проверка:** прочитать `paths.content_map` (с подстановкой `<active-launch>`).
- Файл существует И содержит запись на дату → `brief.mode = "plan"`, перейти в `01a-plan.md`
- Файла нет ИЛИ нет записи → fallback на Mode B2, сообщить: «Карты смыслов на эту дату не нашёл, перехожу в режим генерации идей»

### Mode B1 - Spark с идеей

**Признаки:**
- User дал конкретную тему: «карусель про X», «/carousel про вайбкодинг», «сделай карусель про N8N»
- Короткая фраза (10-200 символов) с явным предметом

→ `brief.mode = "spark-b1"`, перейти в `01b-spark.md`.

### Mode B2 - Spark без идеи

**Признаки:**
- User: «дай идеи каруселей», «что в карусель», «варианты каруселей»
- ИЛИ fall-back из Mode A

→ `brief.mode = "spark-b2"`, перейти в `01b-spark.md`.

---

## Шаг 2 - Override flags

Если в input есть флаг - он побеждает auto-detect:

- `--plan` / `--mode=plan` → Mode A
- `--spark` / `--mode=spark` → Mode B
- `--transcript` / `--mode=transcript` → Mode C
- `--reel <url>` / `--mode=reel-to-carousel` → Mode D

---

## Шаг 3 - Platform detection

**Auto-detect platform по сигналам:**

- «для LinkedIn» / «карусель LinkedIn» / `--platform=li` → `platform = linkedin`
- «для нельзяграма» / «для IG» / «для инстаграм» / `--platform=ig` → `platform = instagram`
- «для обоих» / «крос-платформ» / `--platform=both` → `platform = both`
- **Default:** если `subject.primary_platforms` содержит обе → ask user (один вопрос) ИЛИ default на `instagram` (если subject = автор - primary = IG для RU)

---

## Шаг 4 - Family pre-hint (если ясно из input)

**Auto-hint family по сигналам (опционально, можно уточнить в `01-finalize.md`):**

- «панорама» / «панорамная карусель» / `--family=panorama` → `family = panorama` (hint)
- «N способов / N инструментов / N ошибок» → `family = listicle` (hint)
- «история» / «мой кейс» / «как я» → `family = story-case` (hint)
- «методология» / «N шагов» / «фреймворк» → `family = framework-breakdown` (hint)
- Mode D → `family = reel-to-carousel` (autoset)
- Иначе → `family = null` (определит `02-structure.md`)

---

## Шаг 4.5 - 🎯 FORM-GOAL ROUTER (HARD, канон формы v2)

> Место рождения цели формы для карусели. Выполняется ПОСЛЕ определения mode (Шаги 1-2), platform (Шаг 3) и family-хинта (Шаг 4), ДО записи brief и передачи в mode-файл. Family на решение НЕ влияет: цель определяется замыслом, а family - это скелет слайдов.

**Зачем шаг существует.** Пока `brief.form_goal` пуст, профильные ветки `04-review.md` (HV5/HV6 длины, HV8 нумерация, ссылки в caption, `form_mode`) не имеют цели для сравнения, а `form_mode` в `04-review.md` даёт HARD FAIL: без этого шага дальше пайплайна двигаться нельзя.

### Шаг 4.5.1 - Read канона (HARD)

Прочитать `~/.business/voice-corpus/_format-canon-v2.md`, разделы **§0-§4** (что канон отменяет, метод, ГЛАВНОЕ ПРАВИЛО «цель до написания», три профиля формы, кластеры приёмов) и **§9** (статусы HARD / WARN / SOFT). Пометить `mandatory_reads.form_canon_v2 = true`. Путь абсолютный и только этот: `~/.business` - симлинк на шаблон IvanOS, боевой канон живёт в твоём `~/IvanOS` (канон §8.2).

### Шаг 4.5.2 - Флаг launch_window

Источник - `~/.business/запуски/<активный запуск>/карточка-дня.md`, поле `launch_window` (канон §2.1). Файла нет или поле пусто → **false**. Угадывать флаг запрещено.

### Шаг 4.5.3 - Дерево решений §2.1 (адаптация под карусель)

По признакам ЗАМЫСЛА, не текста. Спрашивать «есть ли ссылка / список / сколько слайдов» на этом шаге запрещено: это следствие режима.

```
1. launch_window == true ?                                     -> S (продажа)
2. Есть внешний артефакт, который читатель может УНЕСТИ
   (видео, подкаст, статья, урок, практикум, гайд, чек-лист,
    промт, приложение, разбор), и я готов дать на него адрес ?  -> F (репосты)
3. [режим A в карусели НЕ ДОСТУПЕН - см. Шаг 4.5.6]            -> перейти к следующему пункту
4. Предмет = личный эпизод автора (место, время,
   физическое действие) ?                                      -> R-нарратив (family story-case)
5. Предмет = причинная механика без артефакта
   (почему это работает) ?                                     -> R-разбор (family framework-breakdown)
6. Ничего из перечисленного ?                                  -> правило выхода §2.1:
   (а) переупаковать в личный эпизод → R-нарратив
   (б) добавить артефакт и адрес → F
   (в) не публиковать
```

Family-хинт Шага 4 после этого **сверяется с целью**, а не наоборот: family вне профиля цели (например `listicle` при цели `reactions`-нарратив) даёт строку-предупреждение `family <X> вне профиля цели <Y>` и уточняется в `02-structure.md`. Шаблон `templates/listicle.md` условный: только цель `forwards` и только когда цифра работает обещанием в хуке (канон §8.2).

### Шаг 4.5.4 - Куда применяется профиль: CAPTION, не слайды

**Профиль формы §3 применяется к CAPTION.** Caption - это текстовое тело публикации, по нему считаются длина, выделения, списочные блоки, адреса и позиция адреса.

**Анатомия слайдов остаётся своя** и берётся из `references/carousel-anatomy.md`: число слайдов, скелет (3-act / 5-beat), роли слайдов, кривая внимания, бюджеты знаков на слайд, визуальный слой. Канон формы их не переопределяет и не отменяет - он измерен на TG-постах, слайдов там нет. Пересчитывать пороги каноном в слайды запрещено.

Граница слоёв в одну строку: **текст caption живёт по канону формы, слайд живёт по `carousel-anatomy.md`**. Визуальная нумерация на слайде (номер-плашка, счётчик 3/10, цифра как элемент макета) под правило нумерации §9 не подпадает вовсе - это подтверждает `04-review.md` HV8 (`scope: только текстовый слой`).

### Шаг 4.5.5 - Хук слайда 1 строится по профилю цели

Слайд 1 - точка, где встречаются оба слоя: его **роль и место** задаёт `carousel-anatomy.md` (HOOK, стоп-скролл, первый в кривой внимания), а его **конструкцию** задаёт профиль цели (канон §4.1, кадр против витрины):

- `reactions` (R): хук - сцена или парадокс, ориентир 60 знаков (≤60 у 70% верха, WARN). **HARD**: в первой строке нет числа ≥1000 и нет круглой метрики канала (подписчики, просмотры, выручка), `+` первым знаком - блок (чистое поле у 93% верха, §9 R-6). Бытовое число и сумма меньше 1000 разрешены вместе с символом валюты
- `forwards` (F): цифра или валюта в хуке желательна (63% против 20%), хук не короче 50 знаков при цели 64 (WARN, §9 F-6); первый эмодзи - иконка носителя (18/59 против 0/59, §3.2)
- `sales` (S): назывной ярлык, цель 36 знаков, ориентир 50 (держат 62% верха, WARN). **HARD**: в самом хуке нет связки «ты / твой / вы + сумма дохода или число подписчиков» (0/34 в верхе против 3/34, §9 S-3)

Формулы хуков из `carousel-anatomy.md` остаются доступны, но при объявленной цели **выбирается только та формула, которая профилю не противоречит**; конфликт разрешается вслух строкой `конфликт: формула <X> vs профиль цели <Y> -> взял <...> по уровню N` (§8.1).

### Шаг 4.5.6 - Режим A недоступен в карусели

Реакция-гейт §7 - TG-механика (числовая просьба о реакции эмодзи, приз-контент, срок выдачи, закрытие гейта выдачей). В IG / LinkedIn каруселях её нет. `form_goal = gate` этот скилл не выставляет никогда, чек-лист §9 «Режим A» помечается `N/A`.

### Шаг 4.5.7 - Записать в brief

```yaml
brief:
  form_goal: "reactions | forwards | sales"   # значения-слова: их сравнивают гейты 04-review
  form_goal_letter: "R | F | S"               # та же цель буквой, для улики form_mode
  form_class: "narrative | razbor | sales"
  form_topic: "<тема одной фразой>"
  form_scope: "caption"                       # профиль -> CAPTION; слайды -> carousel-anatomy.md
  form_profile:
    caption_len_min: <R-нарратив 362 | R-разбор 402 | F 838 | S 759>        # §3.1-3.3, знаки
    caption_len_max: <R-нарратив 1242 | R-разбор 990 | F 1695 | S 2248>
    caption_len_target: <R-нарратив 671 | R-разбор 542 | F 1159 | S 1489>
    caption_len_status: "WARNING"   # §3: длина не блокирует выдачу ни в одном режиме
    caption_hard_ceiling: <platform.caption_max из config, старое правило без изменений>
                                    # физический лимит площадки, HARD, каноном не снимается
    bold_target: <R-нарратив 1 | R-разбор 1-2 | F 3 (ориентир 4) | S 4-5>   # §3, все WARN
    list_blocks_max: <R-нарратив 0 HARD | R-разбор 1 до 3 предикативных пунктов | F 1-2 опись 5-8 пунктов | S 1, оглавление ≤5 буллетов>
    numbered_list_allowed: <S нет (HARD, 88% верха) | R-нарратив WARNING | R-разбор да | F да, алгоритм 3-5 шагов>   # только текстовый слой
    links_rule: <R 0 ссылок в caption HARD (89% верха) | F адрес обязателен HARD и стоит в последних 250 знаках caption (92% и 80%), повтор разрешён | S 0 или 1 адрес HARD (91%), финал caption не URL и не команда (85%), повтор WARNING>
    hook_slide1_rule: <см. Шаг 4.5.5>
    sentence_median_min: <5 только в R-разборе (цель 5.5, 11/12 верха) | null>
    final_rule: <R вывод или жест | F адрес в последних 250 знаках caption | S живая реплика, не URL>
  slides_source: "references/carousel-anatomy.md"   # анатомия слайдов каноном НЕ переопределяется
```

### Шаг 4.5.8 - Улика одной строкой (обязательна)

Формат ровно тот, что ждёт `form_mode` в `04-review.md`. Цель печатается словом (значение для гейтов), буква - в скобках только для быстрого чтения человеком; тот же порядок, что в `01-finalize.md` Шаг 6.5:

```
форма: цель=<reactions|forwards|sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=<...> -> длина caption <min-max>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>
```

Печатается ДО передачи в mode-файл и прокидывается в `brief`.

### Шаг 4.5.9 - Что перекрыто и что остаётся fallback

Ни одно старое правило не удалено:

| старое правило carousel | чем перекрыто при объявленной цели | справочно: как было ДО канона (недостижимо - Гейт 0 блокирует раньше) |
|---|---|---|
| HV6 `len(caption) ≤ platform.caption_max` как блок | WARNING + строка обоснования, коридор из `form_profile` (§3); сам `platform.caption_max` остаётся HARD-потолком площадки | было без изменений |
| HV5 бюджеты `config.family_specs` | пол выше профиля не поднимают (§8.2) | было без изменений |
| HV8 нумерация как общий WARNING | профильно: S FAIL, R-нарратив WARNING, R-разбор разрешена, F алгоритм 3-5 шагов | было WARNING всегда |
| `templates/listicle.md` без условий | шаблон условный: только цель `forwards` (§8.2) | было доступен всегда |
| «≥4 приёма форматирования» / «4-6 жирных» (шаред-слой) | `bold_target` из профиля, WARN с печатью покрытия | было без изменений |
| анатомия слайдов `carousel-anatomy.md` | **не перекрыта ничем** - канон слайды не измерял | действует всегда (канон слайды не измеряет, цели не касается) |

**Если шаг пропущен (процедурная ошибка, не легальный режим).** `brief.form_goal` пуст → `form_mode` в `04-review.md` даёт HARD FAIL (Гейт 0, канон §9), выдача текста запрещена целиком, а не переходит на старые пороги. Единственный маршрут починки: вернуться в `01-router.md` **Шаг 4.5 FORM-GOAL ROUTER** и прогнать дерево канона §2.1 до появления одного из `reactions | forwards | sales`. Столбец справа показывает, какие пороги действовали ДО подключения канона - это справка для починки, а не рабочее состояние, в которое можно уйти вместо выбора цели.

---

## Шаг 5 - Записать brief и перейти

```yaml
brief:
  mode: "<plan | spark-b1 | spark-b2 | transcript | reel-to-carousel>"
  platform: "<instagram | linkedin | both>"
  family: "<framework-breakdown | listicle | story-case | panorama | reel-to-carousel | null>"
  subject_name: "<config.subject.name>"
  subject_language: "<config.subject.language>"
  raw_input: "<original user input>"
  reel_url: "<если Mode D - URL рилза>"
  card_md_path: "<если Mode D - путь к card.md>"
  form_goal: "<reactions | forwards | sales | null>"     # Шаг 4.5; null = HARD FAIL ниже, не рабочее значение
  form_goal_letter: "<R | F | S | null>"                 # буква только для печати улики, null тем же образом блокирует
  form_class: "<narrative | razbor | sales | null>"
  form_topic: "<тема одной фразой>"
  form_scope: "caption"
  form_profile: {<см. Шаг 4.5.7>} | null
  form_evidence_line: "форма: цель=... класс=... тема=... -> длина caption ..., перечислений ..., ссылок ..., цифра в хуке ..."
  slides_source: "references/carousel-anatomy.md"
  mandatory_reads:
    form_canon_v2: false
    avatar: false
    jtbd: false
    brand_dna: false
    products_dir: false
    objections: false
    content_map: false
    recent_carousels: false
    voice_reference: false
    config: false
```

Передать управление:

| Mode | Next file |
|---|---|
| plan | `workflow/01a-plan.md` |
| spark-b1 | `workflow/01b-spark.md` (sub-flow B1) |
| spark-b2 | `workflow/01b-spark.md` (sub-flow B2) |
| transcript | `workflow/01c-transcript.md` |
| reel-to-carousel | `workflow/01d-reel-to-carousel.md` |

Каждый из этих файлов в конце вызывает `workflow/01-finalize.md`.

---

## Принципы router

1. **Тихий detect.** Не задавать вопросы пользователю - определять по сигналам.
2. **Override > auto.** Явный флаг всегда побеждает.
3. **Fallback цепочка.** Mode A без карты → Mode B2.
4. **One mode per run.** Не смешивать modes.
5. **Mandatory reads tracking.** state-объект пробрасывается через все стадии для де-дупликации Read calls.
6. **Цель формы рождается здесь и только здесь** (Шаг 4.5). Пропуск шага = `brief.form_goal` пуст = `form_mode: FAIL` в `04-review.md` и весь профильный слой канона в fallback. Цель определяется по замыслу (дерево §2.1), а не по признакам текста.
7. **Два слоя не смешивать.** Текст caption - канон формы v2; слайды - `references/carousel-anatomy.md`.