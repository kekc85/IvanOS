# 01 - Router

> Главная точка входа `/longform`. Auto-detect mode + platform + subject. Грузит соответствующий `01a/01b/01c.md`.

## Step 1 - load config

1. Read `config.md`. Если отсутствует или неполный - переход к `00-onboarding-student.md`.
2. Read `subject.*`, `platforms.*`, `paths.*`, `voice.*` в память.

## Step 2 - detect override flags

Если в input есть явные флаги - они выигрывают:

| Flag | Effect |
|---|---|
| `--plan` | Force Mode A (даже если input короткий) |
| `--spark` | Force Mode B (даже если есть транскрипт >500 знаков) |
| `--transcript` | Force Mode C |
| `--platform=blog` / `=newsletter` / `=linkedin` | Force platform для финала |
| `--type=teaching` / `=story` / `=framework` | Force тип longform (skip detect-type в `02-structure.md`) |
| `--ru` / `--en` | Force язык (override `subject.language` для этого запуска) |

## Step 3 - auto-detect mode

Если флага нет - определить по сигналам в input.

### Сигналы Mode A (Plan)

- Input пустой или только `/longform`
- Слова: «по плану», «смысл недели», «контент-план», «из карты», конкретная дата
- Любое упоминание `5.2-Карта-смыслов` / `longform-plan`

→ Грузить `01a-plan.md`

### Сигналы Mode B (Spark)

- Input содержит «про X», «о X», «напиши статью», «эссе про», «расскажи как»
- Input содержит просьбу идей: «дай идеи», «что писать», «темы для newsletter»
- Длина input < 500 знаков и не пустой

→ Грузить `01b-spark.md`

**Внутри Mode B различать B1 vs B2:**
- Если есть конкретная тема X (`про X`, `о X`) → B1 (расширение темы)
- Если запрос идей без темы (`дай идеи`, `что писать`) → B2 (генерация под JTBD)

### Сигналы Mode C (Transcript)

- Input длиннее 500 знаков
- Phrases: «надиктовал», «вот мои мысли», «разверни это», «сделай статью из этого»
- Структура input похожа на raw monologue (предложения склеены, повторы, оговорки)

→ Грузить `01c-transcript.md`

## Step 4 - detect platform

Default = `platforms.canonical.type` (из config).

Override сигналы:
- «newsletter» / «выпуск» / «рассылка» → `newsletter`
- «LinkedIn article» / «для LinkedIn» / «LI article» → `linkedin`
- «блог» / «статья на сайте» → `personal_blog` (или canonical)
- «substack» / «medium» → cross-post target (но canonical всё равно = config.canonical)

## Step 5 - detect subject

Subject = автор для которого пишем. По умолчанию `config.subject.name`.

Override: если в input есть «для ученика <name>» / «не моё, а X» - switch subject. В v1.0 поддерживаем только default subject.

## Step 5.5 - FORM-GOAL ROUTER (HARD, канон формы v2)

> Место рождения цели формы для longform. Выполняется ПОСЛЕ того, как определены mode (Step 3), platform (Step 4), subject (Step 5) и до загрузки mode-файла. Тип longform (teaching / story / framework) на этом шаге ещё может быть не определён - цель формы от типа не зависит и определяется раньше него (тип уточняется в `02-structure.md`, а при флаге `--type=` известен уже здесь; при известном типе он в решение всё равно не входит, решает ЗАМЫСЕЛ).

**Зачем шаг существует.** Цель формы выбирается ДО первой строки текста. Пока `brief.form_goal` пуст, профильные пороги канона §3 не к чему привязать: `03-write.md` не начинает draft, а в `04-review.md` профильные ветки Pass 1 (`L1-generic-listicle`, `L1-bullet-density`, `L1-length-floor`) сравнивать не с чем и `L1-form-mode` даёт FAIL. Без этого шага конвейер не движется дальше.

### 5.5.1 Read канона (HARD)

Прочитать `~/.business/voice-corpus/_format-canon-v2.md`, разделы **§0-§4** (что канон отменяет, метод и границы, ГЛАВНОЕ ПРАВИЛО «цель до написания», три профиля формы, кластеры приёмов) и **§9** (статусы HARD / WARN / SOFT по режимам). Пометить `mandatory_reads.form_canon_v2 = true`.

Путь абсолютный и только этот: `~/.business` - симлинк на шаблон IvanOS, боевой канон живёт в твоём `~/IvanOS` (канон §8.2, строка «пути эмпирического слоя»).

### 5.5.2 Флаг launch_window

Источник - `~/.business/запуски/<активный запуск>/карточка-дня.md`, поле `launch_window` (канон §2.1, врезка «Флаг launch_window»). Файла нет или поле пусто → **false**, режим S не выбирается, дерево идёт по пунктам 2-6. Угадывать флаг запрещено.

### 5.5.3 Дерево решений §2.1 (адаптация под длинную форму)

Решение по признакам **ЗАМЫСЛА**, не по признакам текста. Спрашивать «есть ли ссылка / список / сколько знаков» на этом шаге запрещено: это следствие режима, а не его признак (канон §2.1).

```
1. launch_window == true ?                                     -> S (продажа)
2. Есть внешний артефакт, который читатель может УНЕСТИ
   (видео, подкаст, урок, практикум, гайд, чек-лист, промт,
    приложение, разбор, сама статья как переносимая выжимка),
   и я готов дать на него адрес ?                              -> F (репосты)   ← основной режим longform
3. [режим A в longform НЕ ДОСТУПЕН - см. 5.5.4]               -> перейти к п.4
4. Предмет = личный эпизод автора (место, время,
   физическое действие) ?                                      -> R-нарратив (эссе / story)
5. Предмет = причинная механика без артефакта
   (почему это работает) ?                                     -> R-разбор (teaching / framework без адреса)
6. Ничего из перечисленного ?                                  -> правило выхода §2.1:
   (а) переупаковать в личный эпизод → R-нарратив
   (б) добавить артефакт и адрес → F
   (в) не публиковать
```

**F - основной режим longform, и это следует из канона, а не из удобства.** Канон §2.1, врезка «Маршрутизация длинного разбора»: разбор с внешним артефактом и адресом идёт в **F независимо от длины** (эталон #371, C-TOP, 1831 знак, er_idx 1.37 - рассуждение плюс одна ссылка в конце). Статья, newsletter-выпуск и LinkedIn article по природе публикуются как носитель: у них есть canonical-адрес, POSSE-дистрибуция и переносимая выжимка. В R-разборе остаётся разбор **без** адреса наружу. Дефолт не автоматический: п.1 (launch_window) и п.4 (личный эпизод) перебивают его.

### 5.5.4 Режим A недоступен в longform

Режим A (реакция-гейт) - это TG-инструмент CTA, а не текстовая цель (канон §2, §7: числовая просьба о реакции, приз-контент, срок выдачи). В блоге, newsletter и LinkedIn article механики реакций нет: нечего просить и нечем закрывать гейт. Поэтому п.3 дерева в longform пропускается, `form_goal = gate` в этом скилле не выставляется никогда, а весь чек-лист §9 «Режим A» помечается `N/A`. Безусловная реакция-подпись (§7) второй целью не считается и здесь тоже.

### 5.5.5 Записать в brief

```yaml
brief:
  form_goal: "reactions | forwards | sales"   # значения-слова: их сравнивают гейты 04-review
  form_goal_letter: "R | F | S"               # та же цель буквой, для улики Гейта 0 §9
  form_class: "narrative | razbor | sales"    # narrative / razbor только внутри reactions
  form_topic: "<тема одной фразой, для улики и для _form-log.md>"
  form_scope: "body"                          # профиль применяется к ТЕЛУ статьи
  form_profile:
    # длина (единицы - СЛОВА, так их считает 04-review L1-length-floor/ceiling)
    length_min: 0               # пол снят при объявленной цели, но записан ЧИСЛОМ, не null:
                                # гейт L1-length-floor сравнивает word_count с коридором
                                # [length_min..length_max], а сравнение с null не определено.
                                # 0 = «нижней границы нет», то есть гейт по факту проверяет
                                # только верхний порог length_max. Основание: канон §3 «длина
                                # не блокирует выдачу ни в одном режиме» + §8.2 «floor по типам»
                                # -> length_min из профиля. Пол платформы/типа остаётся ТОЛЬКО
                                # при пустой цели. 0 - это не измеренный каноном порог, а явная
                                # запись снятого пола; выдумывать сюда число запрещено
    length_max: <platform.length_ceiling из config, старое правило без изменений>
    length_status: "WARN"       # выход за коридор = WARN + одна строка обоснования, не NO PASS
    canon_len_chars_ref: "<R-нарратив 362-1242 цель 671 | R-разбор 402-990 цель 542 | F 838-1695 цель 1159 | S 759-2248 цель 1489>"
                                # §3.1-3.3, измерено в ЗНАКАХ на TG-постах. Для длинной формы
                                # это справочный ориентир плотности, НЕ порог: пересчёт знаков
                                # в слова каноном не измерялся, выдумывать коэффициент запрещено
    bold_target: <R-нарратив 1 | R-разбор 1-2 | F 3 (ориентир 4) | S 4-5>   # §3, все WARN
    list_blocks_max: <R-нарратив 0 HARD | R-разбор 1 (до 3 предикативных пунктов) | F 1-2 опись | S 1>
    numbered_list_allowed: <R-нарратив нет (WARN) | R-разбор да | F да, алгоритм 3-5 шагов | S нет (HARD)>
    links_rule: <R-нарратив 0 HARD | R-разбор WARN-0 | F ссылка обязательна HARD + в последних 250 знаках | S 0 или 1 адрес HARD>
    hook_digit_required: <R допустима бытовая и сумма <1000 | F желательна (63% против 20%) | S не про доход читателя>
    sentence_median_min: <5 только в R-разборе (цель 5.5, держат 11/12 верха) | null в остальных>
    final_rule: <R вывод или жест | F ссылка в последних 250 знаках | S живая реплика, не URL>
```

**Покрытия печатать рядом с каждым профильным пунктом** (канон §9, «гейт без напечатанного покрытия»): пункт без покрытия не может иметь статус HARD.

**Нижняя граница длины - всегда число, никогда null.** `length_min` уходит дальше по конвейеру только как число: при объявленной цели это `0` (пол снят), пока цель не объявлена, профиля нет вообще и действует старый пол платформы из `config` (выдача при этом заблокирована `L1-form-mode`). В улике длины `04-review.md` (`длина: <N> слов, профиль <min-max> цели <reactions/forwards/sales> (<R/F/S>)`) ноль печатается как есть: `профиль 0-<length_max>` и читается «пола нет, проверяется только верх». Fallback совместимости: если в старом state-файле или в чужом brief пришло `length_min: null`, читать его как `0` и печатать в отчёте строку `length_min пришёл null -> прочитан как 0 (пол снят)`, сравнение с null не выполнять никогда

### 5.5.6 Улика одной строкой (обязательна)

Формат ровно такой, его ждут `03-write.md` (вход-гейт «прочитал→взял») и `04-review.md` (`L1-form-mode`):

```
форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>
```

Цель в улике печатается СЛОВОМ из `brief.form_goal`, буква из `brief.form_goal_letter` идёт следом в скобках и нужна только человеку. Класс печатается латиницей - тем же значением, что лежит в `brief.form_class`.

Строка печатается ДО загрузки mode-файла и прокидывается в `router_output`.

### 5.5.7 Что перекрыто и что остаётся старым порогом

Ни одно старое правило не удалено. При **объявленной** цели его перекрывает профиль, пока цель НЕ объявлена - оно действует в прежнем виде, но текст в этом состоянии не выпускается:

| старое правило longform | чем перекрыто при объявленной цели | статус, пока цель не объявлена (выдача заблокирована) |
|---|---|---|
| `L1-length-floor`: `word_count < platform.length_floor` = EXTEND, NO PASS | `length_min: 0` (пол снят числом) + WARN (канон §3, §8.2 «floor по типам») | действует без изменений |
| `L1-generic-listicle` («10 ways», «Top N») | не применяется при `forwards` (цифра в хуке 63% против 20%) | действует без изменений |
| `L1-bullet-density` (>5 буллетов подряд) | не применяется при `forwards` (список от 4 пунктов 25/59 против 7/59) | действует без изменений |
| таблица длин по типам (`01-finalize.md` Step 3 «target length») | `length_min`/`length_max` из `brief.form_profile`; таблица типов даёт только target и пол выше профиля не поднимает | действует без изменений |
| «≥4 приёма форматирования» / «4-6 жирных» (шаред-слой) | `bold_target` из профиля, WARN с печатью покрытия | действует без изменений |

**Пропуск шага не даёт права выпустить текст.** `01-router.md` - файл этого же скилла (`~/.claude/skills/longform/workflow/01-router.md`), поэтому «роутер недоступен» физически не бывает. `brief.form_goal` остался пустым → ЕДИНСТВЕННАЯ законная ветка: `03-write.md` не начинает draft, `L1-form-mode` даёт FAIL, возврат сюда, в **Step 5.5 FORM-GOAL ROUTER**, прогнать дерево канона §2.1 и напечатать строку-улику. Ветки «работаем в старом виде и публикуем как до канона» нет: статья без объявленной цели не выпускается. Колонка таблицы выше и оговорки «при пустой цели» в `04-review.md` описывают, какие пороги действуют ПОСЛЕ возврата из роутера в осознанно выбранном режиме, а не разрешение обойти выбор цели.

## Step 6 - load mode file

После определения mode (A/B1/B2/C) грузить соответствующий `01a/01b/01c.md`.

## Step 7 - pass context дальше

После работы mode-файла → грузить `01-finalize.md` с:
- mode (A / B1 / B2 / C)
- platform (blog / newsletter / linkedin)
- subject (config.subject)
- language (config.language + override)
- raw_brief (output из mode файла)
- form_goal / form_goal_letter / form_class / form_topic / form_profile (Step 5.5) + строка-улика формы

## Fallback / edge cases - explicit decision tree (v1.0 fix L4.1)

Каждая ветка имеет deterministic ответ. Никакой ambiguity.

### Empty input chain

```
INPUT == empty + флагов нет
├─ config.paths.content_map exists & not empty
│   └─ → Mode A (Plan) через 01a-plan.md
├─ config.paths.longform_content_plan exists & not empty
│   └─ → Mode A (Plan) через 01a-plan.md
├─ config.paths.jtbd exists & not empty
│   └─ → Mode B2 (Spark generation under JTBD) через 01b-spark.md
└─ none of above
    └─ → 00-onboarding-student.md (config incomplete)
```

### Ambiguous input (короткий, не про тему, не команда)

INPUT длина <50 chars + нет ключевых триггеров «про X» / «дай идеи» / «надиктовал»:

```
1. Read config.paths.content_map. Если есть active entry на текущую неделю → Mode A.
2. Если нет - Mode B2 с пометкой «inferred from short input, switching to JTBD generation».
3. НЕ задаём AskUserQuestion (memory feedback_no_askuserquestion_in_cli).
```

### Конфликтующие флаги

| Конфликт | Resolution |
|---|---|
| `--plan --spark` | Первый по позиции в input выигрывает, второй → warning «ignored» |
| `--plan --transcript` | То же |
| `--spark --transcript` | То же |
| `--type=teaching --type=story` | Last-wins (последний по позиции) с warning |
| `--platform=blog --platform=linkedin` | Last-wins |
| `--ru --en` | Last-wins, warning «bilingual через --bilingual flag вместо conflicting language flags» |

### Невалидные значения флагов

| Флаг | Невалидное value | Resolution |
|---|---|---|
| `--platform=X` | X не в [blog, newsletter, linkedin] | FAIL с подсказкой допустимых |
| `--type=X` | X не в [teaching, story, framework, contrarian, case_study, listicle, deep_dive] | FAIL с подсказкой v1.0 supported (teaching/story/framework) |
| `--hook=N` | N > len(hook_variants) | FAIL с подсказкой N range |
| `--platform=blog` | `config.platforms.canonical.url is null` | FAIL «настрой platforms.canonical в config сначала» |

### Empty config / нет critical paths

```
NO config.md exists
└─ → 00-onboarding-student.md

config.md exists но subject.name == null или platforms.canonical.url == null
└─ → 00-onboarding-student.md с pre-fill из existing fields

config.md exists но critical paths (avatar / brand_dna) don't exist on disk
└─ → warning + продолжаем (Voice Fidelity Gate будет weak, об этом скажем в final output)
```

### Pre-structured input в Mode C

Если transcript >500 знаков содержит структурные markers (H1 / H2 / numbered list / explicit «introduction», «conclusion») - это уже draft, не raw transcript.

Resolution: переход в Mode C с пометкой «pre-structured input detected, preserving structure», skip Step 1 normalisation в `01c-transcript.md` (filler removal).

### Topic recency check pre-mode

Перед grouping в mode files - read `paths.recent_articles_*` и если в input/topic есть match с topic из последних 5 статей → warning «недавно писал про X (DD.MM)», но НЕ block (это финальное решение автора). Детальная логика - в `01-finalize.md` Step 2.5.

## Step 8 - state save для resume after crash (v1.0 fix L4.3)

После определения mode + platform + subject - записать state snapshot в `/tmp/longform-state-<session-hash>.yaml`:

```yaml
session_id: <uuid>
timestamp: <iso8601>
mode: A | B1 | B2 | C
platform: blog | newsletter | linkedin
subject_name: <from config>
language: ru | en | both
raw_input: <original user input>
flags_applied: [<list>]
form_goal: reactions | forwards | sales | null
form_goal_letter: R | F | S | null      # только для печати улики, не для сравнений
form_class: narrative | razbor | sales | null
form_profile: {<см. Step 5.5.5>} | null   # length_min внутри - число (0 = пол снят), не null
phase_completed: "router"
next_file: "01a-plan.md | 01b-spark.md | 01c-transcript.md"
```

Каждый workflow file (`01a/01b/01c`, `01-finalize`, `02-structure`, `03-write`, `04-review`, `05-publish`) обновляет `phase_completed` и пишет свой output в тот же state file.

**Resume after crash:** при повторном запуске `/longform --resume <session-id>` - read state file + skip уже completed phases. Если `--resume` без id - найти latest state file в `/tmp/longform-state-*.yaml` и предложить resume.

State file удаляется после успешного `05-publish.md` или через 24 часа TTL.

## Output формат для следующего файла

```yaml
router_output:
  mode: "A | B1 | B2 | C"
  platform: "blog | newsletter | linkedin"
  subject_name: <from config>
  language: "ru | en | both"
  raw_input: <original user input>
  flags_applied: [<list>]
  next_file: "01a-plan.md | 01b-spark.md | 01c-transcript.md"
  form_goal: "reactions | forwards | sales | null"
  form_goal_letter: "R | F | S | null"
  form_class: "narrative | razbor | sales | null"
  form_topic: "<тема одной фразой>"
  form_scope: "body"
  form_profile: {<см. Step 5.5.5>} | null
  form_evidence_line: "форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=... -> длина ..., жирный ..., перечислений ..., ссылок ..., цифра в хуке ..."
```

`null` во всех form-полях - не рабочий режим, а остановка конвейера: `03-write.md` не начинает draft, `04-review.md` `L1-form-mode` даёт FAIL, маршрут возврата один - Step 5.5 FORM-GOAL ROUTER за целью.

## Memory cross-refs

- - router определяет стратегию ДО любого write
- - output в plain text, без таблиц при выводе пользователю