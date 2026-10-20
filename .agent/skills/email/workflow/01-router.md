# workflow/01-router.md

> Auto-detect mode + language + subject. Load config. Route to correct mode-handler.

## Inputs

- `user_input` (string) - raw user query
- `flags` (optional) - `--plan` | `--spark` | `--transcript` | `--en` | `--ru` | `--both` | `--type=<type>` | `--esp=<kit|beehiiv>`

## Steps

### Step 1 - Check config existence

```
IF NOT exists("config.md") OR config.md incomplete (missing subject.name / paths / esp):
    → invoke workflow/00-onboarding-student.md
    → after onboarding: re-read config.md
ELSE:
    → continue
```

### Step 2 - Load config

```
config = Read("config.md")
lexicon = Read("config-lexicon.md")
```

### Step 3 - Detect language

```
IF flag --en: language = "en"
ELSE IF flag --ru: language = "ru"
ELSE IF flag --both: language = "both"
ELSE: language = config.subject.language
```

### Step 4 - Detect mode

Priority: explicit flag > pattern match > default.

```python
if "--plan" in flags or "по плану" in input or "sequence day" in input or "launch day" in input:
    mode = "plan"
elif "--spark" in flags or "напиши письмо про" in input or "/email про" in input or "email про" in input:
    mode = "spark-b1"
elif "дай идеи" in input or "что отправить" in input or "что писать базе" in input:
    mode = "spark-b2"
elif "--transcript" in flags or len(input) > 500 and ("надиктовал" in input or "вот мои мысли" in input or "в email" in input):
    mode = "transcript"
elif "/email" with no args:
    mode = "plan"  # default to Plan from active launch sequence
else:
    # Show choice - single question per memory feedback_no_askuserquestion_in_cli (если CLI/мобиль)
    if vscode_context:
        ask: "Какой mode? Plan (из карты воронки) / Spark (тема) / Transcript (надиктовка)"
    else:
        # CLI mobile - plain text list
        return "Выбери: 1) plan 2) spark 3) transcript"
```

### Step 5 - Detect subject (для onboarding'нутого ученика)

```
subject_name = config.subject.name
subject_voice_path_ru = config.paths.voice_reference_ru
subject_voice_path_en = config.paths.voice_reference_en
```

### Step 5.5 - FORM-GOAL ROUTER (HARD, канон формы v2)

> Место рождения цели формы для email. Выполняется ПОСЛЕ определения mode (Step 4) и subject (Step 5), ДО передачи в mode-handler. Тип письма (nurture / launch-sequence / sales-letter) на решение не влияет: решает ЗАМЫСЕЛ, а не тип.

**Зачем шаг существует.** Пока `brief.form_goal` пуст, профильные пороги канона §3 не к чему привязать: `1.5 Body length` и `1.9 Bullet count` в `04-review.md` сравнивать не с чем, а `EMAIL-G12` даёт FAIL. Без этого шага конвейер не движется дальше.

**1. Read канона (HARD).** Прочитать `~/.business/voice-corpus/_format-canon-v2.md`, разделы **§0-§4** (что канон отменяет, метод, ГЛАВНОЕ ПРАВИЛО «цель до написания», три профиля формы, кластеры приёмов) и **§9** (статусы HARD / WARN / SOFT). Пометить `mandatory_reads.form_canon_v2 = true`. Путь абсолютный и только этот: `~/.business` - симлинк на шаблон IvanOS, боевой канон живёт в твоём `~/IvanOS` (канон §8.2).

**2. Флаг launch_window.** Источник - `~/.business/запуски/<активный запуск>/карточка-дня.md`, поле `launch_window` (канон §2.1). Файла нет или поле пусто → **false**. Угадывать флаг запрещено. Отдельно: `mode = plan` из launch-sequence сам по себе флаг НЕ поднимает - решает карточка дня.

**3. Дерево решений §2.1 (адаптация под письмо).** По признакам ЗАМЫСЛА, не текста. Спрашивать «есть ли ссылка / список / сколько знаков» на этом шаге запрещено.

```
1. launch_window == true ?                                     -> S (продажа)
2. Есть внешний артефакт, который читатель может УНЕСТИ
   (видео, подкаст, статья, урок, практикум, гайд, чек-лист,
    промт, приложение, разбор), и я готов дать на него адрес ?  -> F (репосты / носитель)
3. [режим A в email НЕ ДОСТУПЕН - см. п.4 ниже]                -> перейти к следующему пункту
4. Предмет письма = личный эпизод автора (место, время,
   физическое действие) ?                                      -> R-нарратив
5. Предмет письма = причинная механика без артефакта
   (почему это работает) ?                                     -> R-разбор
6. Ничего из перечисленного ?                                  -> правило выхода §2.1:
   (а) переупаковать в личный эпизод → R-нарратив
   (б) добавить артефакт и адрес → F
   (в) не отправлять
```

**Режим A недоступен в email.** Реакция-гейт - TG-инструмент CTA (числовая просьба о реакции, приз-контент, срок выдачи, канон §7), в почте механики реакций нет. Поэтому `form_goal = gate` этот скилл не выставляет никогда, чек-лист §9 «Режим A» помечается `N/A`.

**4. Куда именно применяется профиль.**

- `form_profile` целиком применяется к **телу письма (Body)**
- **конструкция хука §4.1 применяется к Subject**, а не к первой строке Body: Subject - это то, что читатель видит первым, и именно он несёт кадр против витрины. Отсюда в Subject идут профильные требования хука: R - сцена или парадокс, длина ориентир 60 знаков (WARN), в первой строке нет числа ≥1000 и нет круглой метрики канала (HARD, §9 R-6); F - число или валюта желательны (63% против 20%), ориентир 50 знаков при цели 64 (WARN); S - назывной ярлык, цель 36 знаков, ориентир 50 (WARN), связка «ты/твой/вы + сумма дохода или число подписчиков» в самом Subject запрещена (HARD, 0/34 в верхе, §9 S-3)
- Preheader профилем канона **не управляется**: своих измерений по нему в каноне нет, старые пороги `04-review.md` 1.4 (>90 FAIL, <50 WARNING) остаются в силе при любой цели

**5. Ссылки: правило носителя, а не порог канона.**

Порог «ссылок 0 / 1» из §3 буквально в письмо **не переносится**: он измерен на TG-постах, где ссылка - редкое событие, а для письма ссылка нормальна по природе носителя (кнопка, адрес выдачи, футер ESP, отписка). Из канона в email берётся **только правило одного адреса и его позиция**:

- **один целевой адрес на письмо** (канон §9 S-4: якорей 0 или 1 адрес держат 91% верха; §9 F-3: запрещены разные адреса, ведущие в разные места). Служебные ссылки ESP (отписка, веб-версия, соцсети в футере) в счёт целевых адресов не входят
- **позиция:** при `forwards` адрес стоит в хвосте письма, в последних 250 знаках тела (§9 F-3, 80% верха); при `sales` последняя строка тела - не URL и не команда действия, после ссылки идут 1-3 строки живой речи (§9 S-5 HARD, S-6 WARN); при `reactions` целевого адреса наружу нет - письмо с адресом уходит в F по дереву §2.1
- повтор одного и того же адреса: при F разрешён (§9 F-3), при S - WARN (2/34 против 7/34)

**6. Записать в brief:**

```yaml
brief:
  form_goal: "reactions | forwards | sales"   # значения-слова: их сравнивают гейты 04-review 1.9
  form_goal_letter: "R | F | S"               # та же цель буквой, для улики EMAIL-G12
  form_class: "narrative | razbor | sales"
  form_topic: "<тема одной фразой>"
  form_scope: "body"                          # профиль -> Body; хук профиля -> Subject
  form_profile:
    # длина (единицы - СЛОВА: так её считает 04-review 1.5 words_count)
    length_min: null            # пол снят при объявленной цели (канон §3: длина не блокирует
                                # ни в одном режиме; §8.2 - floor заставляет дописывать обвязку).
                                # config.email.body_min_words_<type> действует ТОЛЬКО при пустой цели
    length_max: <config.email.body_max_words_<type>, старое правило без изменений>
    length_status: "WARNING"
    canon_len_chars_ref: "<R-нарратив 362-1242 цель 671 | R-разбор 402-990 цель 542 | F 838-1695 цель 1159 | S 759-2248 цель 1489>"
                                # §3.1-3.3, в ЗНАКАХ. Справочный ориентир плотности; пересчёт
                                # знаков в слова каноном не измерялся, коэффициент не выдумывать
    bold_target: <R-нарратив 1 | R-разбор 1-2 | F 3 (ориентир 4) | S 4-5>   # §3, все WARN
    list_blocks_max: <R-нарратив 0 (FAIL при ≥1) | R-разбор 1 до 3 предикативных пунктов | F 1-2 опись 5-8 пунктов | S 1, оглавление ≤5 буллетов>
    numbered_list_allowed: <только F (алгоритм 3-5 шагов); R-нарратив WARN; R-разбор да; S нет (HARD)>
    links_rule: "один целевой адрес (§9 S-4, F-3); позиция по цели (см. п.5); служебные ссылки ESP не в счёт"
    subject_hook_rule: <R сцена/парадокс, ориентир 60, без числа ≥1000 (HARD) | F число или валюта, ориентир 50 цель 64 | S ярлык, цель 36, без «ты+сумма» (HARD)>
    sentence_median_min: <5 только в R-разборе (цель 5.5, 11/12 верха) | null>
    final_rule: <R вывод или жест | F адрес в последних 250 знаках | S живая реплика, не URL>
```

**7. Улика одной строкой (обязательна).** Формат ровно тот, что ждёт `EMAIL-G12` в `04-review.md`:

```
форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>
```

Цель в улике печатается СЛОВОМ из `brief.form_goal`, буква из `brief.form_goal_letter` идёт следом в скобках и нужна только человеку. Класс печатается латиницей - тем же значением, что лежит в `brief.form_class`.

Печатается ДО передачи в mode-handler и прокидывается дальше в `brief`.

**8. Что перекрыто и что остаётся fallback.** Ни одно старое правило не удалено:

| старое правило email | чем перекрыто при объявленной цели | статус, пока цель не объявлена (выдача заблокирована) |
|---|---|---|
| `1.5 Body length`: words вне `body_min/max_words_<type>` → FAIL | `length_min: null` + `length_max` из профиля, WARNING + строка обоснования (§3) | действует без изменений |
| `1.9 Bullet count`: >1 в nurture/launch WARNING, >2 FAIL | профильно: R-нарратив 0, R-разбор ≤1, F 1-2 опись, S ≤1 (§3, §8.2) | действует без изменений |
| `config.email.bullet_count_max: 1` | тот же профиль (§8.2, строка про `email/config.md:212`) | действует без изменений |
| нумерация в списках | запрещена всегда, кроме F (алгоритм 3-5 шагов) - §9 S-13, F-8 | действует без изменений |
| пороги Preheader (1.4) | **не перекрыты**: канон Preheader не измерял | действуют всегда |

**Пропуск шага не даёт права выпустить письмо.** `01-router.md` - файл этого же скилла (`~/.claude/skills/email/workflow/01-router.md`), поэтому «роутер недоступен» физически не бывает. `brief.form_goal` пуст → ЕДИНСТВЕННАЯ законная ветка: `EMAIL-G12` даёт FAIL и возвращает сюда, в **Step 5.5 FORM-GOAL ROUTER**, прогнать дерево канона §2.1 и напечатать строку-улику. Ветки «работаем на старых плоских порогах и выпускаем как до канона» нет: письмо без объявленной цели не выпускается. Колонка таблицы выше и оговорки «при пустой цели» в `04-review.md` описывают, какие пороги действуют ПОСЛЕ возврата из роутера в осознанно выбранном режиме, а не разрешение обойти выбор цели.

### Step 6 - Route to mode handler

| Mode | Next file |
|---|---|
| plan | `workflow/01a-plan.md` |
| spark-b1 / spark-b2 | `workflow/01b-spark.md` |
| transcript | `workflow/01c-transcript.md` |

### Step 7 - После mode-handler: route to finalize

После любого mode-handler возвращается `brief` объект с минимумом полей:

```yaml
brief:
  mode: plan | spark-b1 | spark-b2 | transcript
  language: ru | en | both
  topic_or_meaning: "<тема письма или смысл из карты>"
  audience_hint: "<кто читатель>"
  cta_goal_hint: "<какая цель письма>"
  sequence_position: "<day N / null>"  # только для launch sequence
  source_quotes: []                     # только для Mode C (transcript)
  form_goal: "reactions | forwards | sales | null"   # Step 5.5, слово - значение для гейтов;
                                                     # null = цель не объявлена, выдача заблокирована EMAIL-G12
  form_goal_letter: "R | F | S | null"               # буква, только для печати улики
  form_class: "narrative | razbor | sales | null"
  form_topic: "<тема одной фразой>"
  form_scope: "body"
  form_profile: {<см. Step 5.5 п.6>} | null
  form_evidence_line: "форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=... -> длина ..., жирный ..., перечислений ..., ссылок ..., цифра в хуке ..."
```

→ затем `workflow/01-finalize.md`.

## Output контракт

Router возвращает в чат пользователю одну строку:

```
Mode: <mode> | Language: <language> | Subject: <name> | ESP: <esp>
форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>
→ переходим в <next-file>
```

Вторая строка - улика Step 5.5, она обязательна (её ждёт `EMAIL-G12`). Цель не объявлена → печатать `форма: цель=не объявлена -> возврат в 01-router.md Step 5.5 FORM-GOAL ROUTER, дерево канона §2.1` и не идти в mode-handler, пока цель не выбрана.

Без verbose'а. Без обсуждения. Если mode неоднозначен - задаём одну точную question с 2-3 опциями (не более), но НЕ AskUserQuestion в CLI/mobile (см. `[[feedback-no-askuserquestion-in-cli]]`).

## Fallback

- Если `funnel_map` пустой → Mode Plan недоступен → fallback на Spark-B2
- Если `launch_sequence_map` пустой и input просит launch sequence → плотно спросить «нет активного launch sequence map. Создать или использовать nurture?»
- Если config.md missing → onboarding (Step 1)

## Anti-patterns

- НЕ генерировать письмо в самом router'е - router только маршрутизирует
- НЕ изобретать новые modes на лету - только 4 mode (plan / spark-b1 / spark-b2 / transcript)
- НЕ задавать >1 уточняющий вопрос на этапе routing'а - оптимально 0 вопросов через детекцию паттернов