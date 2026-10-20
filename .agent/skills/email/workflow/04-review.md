# workflow/04-review.md

> ⚠️ В ПАКЕТ НЕ ВХОДЯТ: `cell-text-required-axes.py`. Команды с этими именами даны как ОПИСАНИЕ: инструмент либо приходит из внешнего пакета, который ставится отдельно, либо собирается на твоём проекте по этой же инструкции. Внутри поставки такого файла нет

> 6-Pass Refinement + Maxwell Ross 9-checklist + EMAIL-G1-10 + 3 слоя. Final gate перед publish.

## Layer 1 - Hard regex validators (deterministic)

### 1.1 Em-dash check

```regex
"-"  inside any line (Subject / Preheader / Body / CTA)
```
→ auto-replace «-» на «-» в bullet list start position; FAIL inside строки.

### 1.2 Spam-trigger scan

Прочитать `config-lexicon.md` + `references/spam-triggers-list.md`.

Применить regex по каждому banned слову / pattern:

```
RU: "бесплатно" / "срочно" / "только сегодня" / "ОФИЦИАЛЬНО" / "100%" / "недорого"
EN: "free" / "urgent" / "guaranteed" / "ACT NOW" / "100%"
patterns: "[A-ZА-Я]{4,}" / "!{2,}" / "\\${1,}\\d"
```

Subject → hard fail если найдено.
Body → contextual: если "бесплатно" в Subject = fail; если в body «бесплатный гайд внутри письма» = OK.

### 1.3 Subject length

```
Subject length > 60 chars → FAIL
Subject length > 50 chars → WARNING
Subject length < 15 chars → WARNING
```

### 1.4 Preheader length

```
Preheader > 90 chars → FAIL
Preheader < 50 chars → WARNING
```

### 1.5 Body length

**Профильно по цели формы (канон v2 §3, приоритет над таблицей типов).**

```
если brief.form_goal объявлена:
    words_count outside brief.form_profile.length_min .. length_max
        → WARNING + одна строка обоснования (длина НЕ блокирует ни в одном режиме)
    улика: «длина: <N> в профиле <min-max> цели <reactions/forwards/sales> (<R/F/S>)»
    таблица типов не поднимает пол выше профиля

brief.form_goal пуст - НЕ рабочий режим: EMAIL-G12 даёт FAIL и возвращает
в 01-router.md Step 5.5 FORM-GOAL ROUTER за целью. Старое правило не удалено
и действует, пока цель не объявлена, но письмо в этом состоянии не выпускается:
    words_count outside config.email.body_min_words_<type> .. body_max_words_<type> → FAIL
```

Причина понижения: коридор верха огромен (эталонные посты верхнего квартиля 268..2678 знаков), жёсткий пол заставляет дописывать ровно ту обвязку, которая отличает слабый текст от сильного (канон §4.3). Гейты качества (ценность, конкретика, EMAIL-G3) остаются HARD и держат «огрызок» без порога знаков.

### 1.6 Banned lexicon scan

Прочитать `config-lexicon.md` banned section. Применить regex по Body + Subject + Preheader.

→ FAIL если найдено.

### 1.7 Метафоры check (mild AI-tell)

Прочитать `~/.claude/skills/post/references/_voice-TEMPLATE.md` anti-patterns. Применить regex по common metaphors:

```
"ломает", "закрывает", "выстрелил", "вынесли мозг", "прокачать", "зайдёт", "разорвал"
```

→ FAIL если найдено в небуквальном значении.

### 1.8 Несуществующие словосочетания

«склеивать рилсы руками», «писать письма на коленке», прочее из `config-lexicon.md` Несуществующие.

→ FAIL.

### 1.9 Bullet count

**Профильно по цели формы (канон v2 §3 и §8.2).** Источник - `brief.form_goal` / `brief.form_profile`.

```
brief.form_goal = reactions, form_class = narrative → списочных блоков 0 (FAIL при ≥1)
                                  держат 93% верха, тире-перечисление 7% против 37%
brief.form_goal = reactions, form_class = razbor    → ≤1 блок до 3 предикативных пунктов (>1 → WARNING)
                                  каждый пункт содержит глагол или является вопросом, иначе FAIL
brief.form_goal = forwards                          → опись 1-2 блока маркерами тире, целевое 5-8 пунктов
                                  список от 4 пунктов - признак верха (25/59 против 7/59), не дефект
brief.form_goal = sales                             → ≤1 блок, оглавление максимум 5 буллетов (WARNING сверх)

нумерация (^\d+\. и «Шаг N»): запрещена ВСЕГДА, кроме form_goal = forwards,
где допустим алгоритм 3-5 шагов
```

Сравнение идёт только со СЛОВОМ в `brief.form_goal` и `brief.form_class`. Буква `brief.form_goal_letter` (`R` / `F` / `S`) в условиях гейта не участвует - она печатается человеку в улике.

`brief.form_goal` пуст - НЕ рабочий режим: `EMAIL-G12` даёт FAIL и возвращает в `01-router.md` Step 5.5 FORM-GOAL ROUTER за целью. Старое правило не удалено и действует, пока цель не объявлена, но письмо в этом состоянии не выпускается:

```
bullet list count > 1 в nurture/launch → WARNING
bullet list count > 2 в sales-letter → WARNING
bullet list count > 2 в любом → FAIL
```

Тире-строки (`^-`) считаются списочным блоком наравне с `*` и `1.`: без этого перечисление доноров линтеру не видно.

### 1.10 Восклицательные знаки

```
Subject "!" count > 1 → FAIL
Body "!" count > 5 → WARNING
```

---

## Layer 2 - EMAIL-G1-10 Gates

### EMAIL-G1 - Subject A/B count

- Subject ровно ОДИН (варианты списком = брак, правка автора)
- Каждый <50 chars
- Каждый на разном hook framework (no 2× curiosity подряд)
- Все проходят Layer 1 валидаторы

→ FAIL если <3 или одинаковые frameworks.

### EMAIL-G2 - Preheader synergy

Compute similarity (token Jaccard or LCS ratio) между Subject (выбранный winner) и Preheader.

- similarity > 0.7 → FAIL (parafraz)
- similarity < 0.3 → WARNING (disconnected, может быть OK для contrast strategy)
- 0.3-0.7 → PASS

### EMAIL-G3 - CTA clarity (Action-skill Gate D)

- Ровно 1 цель письма (один CTA goal)
- CTA-link count в body соответствует config.email.cta_link_min_count_<type>
- Все CTA-link ведут на ОДНУ страницу
- CTA-text actionable verb+object pair (regex `^\S+\s+\S+`)

**Banned одиночные глаголы в CTA (hard fail):**
- «Узнать», «Подробнее», «Подробности», «Click here», «Тык», «Сюда»
- «Записаться», «Подать», «Заявка», «Начать» (одиночные без объекта)
- «Открыть», «Получить», «Забрать», «Войти», «Перейти», «Забронировать», «Прочитать» (одиночные без объекта)

**Whitelist одиночных (PASS):**
- «Иду», «I'm in», «Join», «Pay» - семантически self-contained, контекст раскрыт в Subject + первой строке Body.

**Verb-object pair test:**
- 2+ слов в CTA → regex `^[A-ZА-Я][а-яё]+\s+[А-Яа-яё]+\b` (RU) / `^[A-Z][a-z]+\s+[a-z]+\b` (EN)
- Pass если есть глагол и объект.

Примеры PASS: «Получить разбор», «Открыть пост», «Иду на эфир», «Read article», «Get template»
Примеры FAIL: «Записаться», «Открыть», «Подробнее»

→ FAIL при нарушении.

### EMAIL-G4 - Mobile preview

- Первые 40 chars Subject читабельны как самостоятельный смысл (truncation safety)
- Preheader первые 40 chars читабельны
- Первый параграф Body ≤200 chars (above-fold)

→ FAIL при нарушении.

### EMAIL-G5 - Spam trigger scan

Уже в Layer 1 (1.2). Дублируется в EMAIL-G5 для consolidate report.

### EMAIL-G6 - No-image-dependency

- Письмо читабельно если все картинки отключены (Kit users часто блокируют)
- НЕТ фраз типа «как видно на картинке выше» / «смотри изображение»
- Все изображения имеют alt-text (если HTML/Beehiiv)

→ FAIL при нарушении.

### EMAIL-G7 - Length range

Уже в Layer 1 (1.5). Дублируется для consolidate.

### EMAIL-G8 - Sequence-consistency (launch-sequence only)

Для type=launch-sequence:

- brief.sequence_position set
- brief.sequence_context.pre / post / type set
- Body содержит callback на pre_email_context (если sequence_position > 1)
- Body содержит teaser для post_email_context (если sequence_position < total)

→ FAIL при нарушении (только для launch-sequence type).

### EMAIL-G8b - Обязательные ОСИ клетки (Mode Plan, HARD)

🔴 **Позитивный гейт: проверяет не «чего нет», а «что обязано быть».** Остальные гейты ловят запреты, поэтому пустое письмо на одном смысле проходит их зелёным. Класс дефекта по решению автора: письмо прошло все запреты, несло один смысл и не раскрывало скилл = вода, автор забраковал.

Применять ВСЕГДА, когда mode=plan и смысл взят из клетки карты смыслов:

```bash
python3 ~/.claude/hooks/cell-text-required-axes.py <текст.md> \
  --cell <путь к day-NN.md> --channel <EMAIL|ОСН|ЗАКР|...> \
  --matrix <путь к МАТРИЦА-инструментов-скиллов.json> --day "День N"
```

Гейт требует наличия в теле:

- **каждый подсмысл** клетки (поле ПОДСМЫСЛЫ-ГРАНИ) физически звучит, не только несущий
- **скилл канала** из матрицы назван ПО-ЧЕЛОВЕЧЕСКИ («Линейка продуктов и оффер»), тех-имя (`setka-produktov-i-offera`) в публичный текст НЕ попало
- **механика скилла** раскрыта связкой вход→делает→выход, а не ярлыком-упоминанием
- **конкретика-цифра** есть и привязана к сущности («990 рублей за её продукт»), не голая пропись

exit 2 → FAIL, письмо не выдавать. Цифры, которых нет в ФАКТ-БАЗЕ дня, не выдумывать: нет числа → описывать механику без чисел.

Если клетки/матрицы нет (mode=spark / transcript) - гейт пропускается.

### EMAIL-G9 - Compliance check

См. `references/compliance.md` для полного reference.

Для каждого письма перед publish:

- IF config.esp.default in [kit, beehiiv]: auto-compliance, PASS (ESP handles unsubscribe footer + sender ID)
- IF config.esp.default == custom: check body contains unsubscribe link + sender legal entity + commercial identification
- IF sales-letter type: гарантия возврата 14 дней присутствует (152-ФЗ ЗоЗПП ст. 25, ст. 26.1)
- Subject accuracy: не вводит в заблуждение vs body promise (CAN-SPAM)

FAIL при нарушении. Auto-handled для Kit/Beehiiv. Для custom ESP - footer injection в 05-publish.md.


### EMAIL-G10 - AI-tells regex scan (98 классов)

См. `~/.claude/skills/post/references/_voice-TEMPLATE.md` для полного списка 98 классов AI-tells.

**Hard regex patterns (мгновенный fail):**

```regex
PH-1 «Не X, а Y»:     "Не [А-Яа-я]+.*?[--].*?это [А-Яа-я]+\."
PH-1 mirror-double:    "Я не [А-Яа-я]+\. Я [А-Яа-я]+"
PH-3 Reveal-headings:  "(Первое|Второе|Третье|Четвёртое)\s*[--]"
PH-7 AI-meta:          "(И тут самое важное|И самое смешное|И вот что интересно)"
PH-9 AI-conditional:   "Если [^.]+[--]\s*то"
PH-20 Faux humility:   "(Я не утверждаю|Может это не для всех|Не претендую на)"
PH-25 Hollywood:       "(И тогда я (понял|начал|увидел|осознал))"
ST-1 Tricolon parade:  3+ короткие симметричные предложения подряд (manual visual check)
S-5 Mirror parallelism: "X не [verb] Y\. X [verb] Z" (mirror structure)
L-7 Метафоры:          "(галерный|потолок ручного|упёрся в|выстрелил|разорвал|закрывает направление)"
PH-14 AI-summary:      "Всё остальное [--]"
L-5 Enumerator:        "[А-Яа-я]+, [А-Яа-я]+, [А-Яа-я]+ и [А-Яа-я]+" (4+ в линию)
```

**Quota rules:**

- PH-1: max 0 (главный AI-tell)
- PH-3: max 0
- PH-7: max 1 на письмо (автор иногда использует, 2+ = fail)
- PH-9: max 1 в structured exposition (в conversational P.S. OK)
- ST-1 Tricolon: max 1 группа на письмо
- L-7 метафоры: max 0 в небуквальном значении

**Process:**

1. Грепнуть body по каждому regex
2. Если найдено - идентифицировать класс + строка + конкретный hit
3. Решить: переписать строку через verified Ivan structure (sequence фактов, без mirror, без reveal, без «не X а Y»)
4. Re-scan после fix

**Output:**

Явный список в Внутрянке: «AI-tells scan: N hits / M scrubbed». Если N>3 - re-run Pass 2 в `03-write.md` с явной инструкцией «перепиши без AI-tells».

→ FAIL при >3 hits после scrub.

### EMAIL-G11 - No-anglicisms (RU чистый русский, EN чистый английский)

См. memory `[[feedback-no-anglicisms-pure-language]]` для полной таблицы замен.

**Regex scan для RU output (config.language=ru):**

```regex
\b(newsletter|workflow|pipeline|content|AI[- ]|X-thread|viral|talking points|rich контекст|review-стек|source of truth|skill|broadcast|hook|CTA|subject|above-fold|open rate|click rate|nurture letter|sales letter|launch sequence|Q&A|TG)\b
```

**Action при hit:**

1. Заменить по таблице из memory `feedback-no-anglicisms-pure-language.md`
2. Если англицизм - имя собственное бренда (X, Skool, Kit, Beehiiv, Telegram, ChatGPT, Claude) - оставить
3. Если нет русского эквивалента (preheader) - оставить или перевести по контексту

**Quota:** 0 англицизмов в чистом RU тексте кроме явных исключений (имена брендов / методологий с расшифровкой).

→ FAIL при любом hit без обоснования (бренд / нет эквивалента).

**Зеркально для EN output (config.language=en):** запрет русизмов / транслитераций (Нельзяграм → Instagram только в EN; вайбкодинг → vibe-coding с пометкой переводимое имя метода).

---

### EMAIL-G12 - Form mode (HARD, процедурный; Гейт 0 канона формы v2 §9)

Проверяет не текст, а то, что форма была выбрана под цель ДО написания. Новый гейт, ни один старый не отменяет.

**1. Улика формы обязательна.** В отчёт выводится строка:

```
форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>
```

- Цель в улике - СЛОВО из `brief.form_goal`, буква из `brief.form_goal_letter` идёт в скобках и нужна только человеку; класс печатается латиницей, тем же значением, что лежит в `brief.form_class`. Улика в другом формате гейтом не засчитывается
- Строки нет ИЛИ `brief.form_goal` пуст → `EMAIL-G12: FAIL`, маршрут возврата - 01-router.md Step 5.5 FORM-GOAL ROUTER, выбор цели по дереву канона §2.1, а не правка текста. Выпуск письма без объявленной цели не разрешён ни одной оговоркой этого файла
- Две текстовые цели в одном письме = FAIL: сигналы не коррелируют, признаки противоположны по знаку (канон §2). Безусловная реакция-подпись (§7) второй целью не считается

**2. Конфликты формы (обязательный пункт отчёта):**

```
конфликты формы: <строки вида «конфликт: A vs B -> взял A по уровню N»> | нет конфликтов
```

Пункта нет = HARD FAIL. Блокирующий пункт канона снимается ровно одним способом - такой строкой плюс дословная цитата правила уровня N (иерархия §8.1: факты > указание автора > голос > Слой 0 «Деньги» при `launch_window=true` > **канон формы** > донор-канон v1 > плоские дефолты скилла > generic-каркасы). Ссылка на уровень ниже канона override не даёт.

**3. Покрытие рядом с каждым профильным пунктом.** Формат: `жирный: 1 (ровно 1 у 48% верха, ≤2 у 56%)`. Пункт без напечатанного покрытия не может иметь статус HARD - только WARNING.

**4. Метрика приёмки только по объявленной цели** (канон §5). Письмо цели `reactions` не оценивается по пересылаемости, письмо цели `forwards` не оценивается по реакциям. Сводная «эффективность» по одной метрике на все письма запрещена как основание правки формы.

→ FAIL при отсутствии улики формы, при двух целях в одном письме или при отсутствующем пункте «конфликты формы».

## Layer 3 - 6-Pass Refinement (LLM-based)

Прочитать draft и выполнить 6 проходов:

### Pass 5.1 - Skeptic

«Я подписчик, я скептичен. Что в этом письме звучит как hype, обман, AI-генерация, generic copywriting?»

→ Список проблем + fix recommendations.

### Pass 5.2 - Expert

«Я эксперт в нише автора. Есть ли в письме technical inaccuracies, выдумка, faking expertise?»

→ Список проблем.

### Pass 5.3 - Inbox Scanner (= TG Scroller для email)

«Я сканю inbox за 3 секунды. Стопит ли Subject? Preheader дополняет? Open-rate prediction?»

→ Skor 1-10 + fix recommendations.

### Pass 5.4 - Competitor

«Я конкурент автора. Что в этом письме я бы скопировал? Что есть оригинального? Что generic?»

→ Originality skor 1-10.

### Pass 5.5 - Editor

«Я редактор. Cut 20% слов без потери смысла. Что бы я вырезал?»

→ Список cuts.

### Pass 5.6 - Preview Pane (= TG Thumbnail для email)

«Я вижу только Subject + Preheader + первые 100 chars Body в Preview Pane (mobile Gmail / iOS Mail). Хочу ли открыть?»

→ Open-prediction Yes/No + fix.

После 6 passes - сводный список fixes. Если >5 critical fixes → re-run Pass 1 (re-draft).

---

## Layer 4 - Maxwell Ross 9-Item Checklist (адаптация под email)

Yes/No per item:

| # | Item | Yes/No | Описание |
|---|---|---|---|
| 1 | Idea | Y/N | Одна большая идея в письме? |
| 2 | Clarity | Y/N | Понятно с первого прочтения? |
| 3 | Payoff | Y/N | Subject обещание выполнено в body? |
| 4 | Specificity | Y/N | Конкретика, не abstractions? |
| 5 | Freshness | Y/N | Не клише inbox'а? |
| 6 | Hook | Y/N | Subject-hook + first line зацепляют? |
| 7 | Length | Y/N | В диапазоне типа? |
| 8 | Tone | Y/N | 1:1 personal, не corporate? |
| 9 | CTA | Y/N | Clear single goal? |

→ 9/9 Y required. Любое N → fix.

---

## Layer 5 - 3 слоя финальный gate

### Слой 1 - Валидаторы

Все pas Layer 1-2 → 9/9 + 8/8 PASS.

Отдельной строкой в вердикт Layer 5:

```
form_mode: PASS | FAIL      # EMAIL-G12, Гейт 0 канона формы v2 §9
form: goal=<reactions|forwards|sales|null> goal_letter=<R|F|S|null> class=<narrative|razbor|sales|null> profile=<длина min-max / жирный N / списков N / ссылок N>
конфликты формы: <строки «конфликт: A vs B -> взял A по уровню N»> | нет конфликтов
```

Значения `goal` и `class` в вердикте - слово и латиница, ровно те, что лежат в `brief.form_goal` / `brief.form_class`. `goal_letter` - печать для человека, сравнивать по ней запрещено.

`form_mode: FAIL` блокирует publish наравне с остальными hard-гейтами и возвращает к выбору цели (дерево канона §2.1), а не к правке текста. `goal=null` - не рабочее состояние, а причина FAIL: письмо с пустой целью не публикуется, строка печатается и маршрут возврата один - `01-router.md` Step 5.5 FORM-GOAL ROUTER.

Пункт 7 чек-листа Maxwell Ross («Length - в диапазоне типа?») при объявленной цели читается как «в коридоре профиля цели», а не таблицы типов, и не может дать N в одиночку: длина не блокирует (канон §3).

### Слой 2 - 4 концепции

- **Pre-mortem**: 5 причин почему это письмо может провалиться. Митигированы ли?
- **Calibration**: уверенность 90%+ что это сработает на ICP?
- **Multi-perspective**: маркетолог (CTR) / subscriber (value) / deliverability (spam-score). Все 3 view PASS?
- **Adaptive**: если новая ошибка обнаружена → новый валидатор в Layer 1

### Слой 3 - 7 контуров

- **Context**: совпадает с brief.audience_hint?
- **Premise compliance**: не дублирует последние 20 писем?
- **Целесообразность**: CTA-goal оправдан для этой позиции в funnel?
- **Релевантность**: для ICP это must-read или nice-to-have?
- **Фактология**: цифры / факты / цитаты ВЕРНЫЕ (не выдумка)?
- **Реализуемость**: link работает? CTA-button рабочая?
- **Достоверность**: voice = автора, не AI?

→ Все 7 PASS required.

---

## Layer 5.5 - Self-Review Cross-Check (Action-skill Gate E)

Перед финальным «3 слоя пройдено» обязательно произвести fact-list:

1. Перечислить все utterances в Subject + Preheader + Body + CTA содержащие: числа / даты / именованные события / суммы / brand mentions / personal facts.

2. Для каждой указать source verification:
   - ✓ verified in `<file>` (paths.products / paths.avatar / paths.business_index / paths.testimonials / raw_transcript)
   - ✓ confirmed by user в этой сессии
   - ✗ UNVERIFIED

3. Если хотя бы один ✗ UNVERIFIED → НЕ писать «3 слоя пройдено». Вместо этого:

```
3 слоя ПОЛУПРОЙДЕНО - flag UNVERIFIED:
- «<quote>» (UNVERIFIED, причина: не найден в SOURCES)
- ...
ACTION: вернуться в Pass 0.7 ИЛИ переписать draft без unverified фактов.
```

4. Если все ✓ → выдать fact-list и далее «3 слоя пройдено».

## Layer 5.7 - 4 теста заголовка (SOLO `pisatel-*` canib)

Применяется к **Subject** (главный driver open rate) + **Preheader** + **first body line** (после opener). Gate перед утверждением, BLOCKING:

1. **Самодостаточность.** Subject понятен holding-mailbox читателю без open / без знания автора. Если читатель должен «открыть чтобы понять о чём» → FAIL. Subject = решает «открыть или удалить» за 0.5 сек.
2. **Конкретное действие.** В Subject + Preheader есть глагол / результат / цифра, не абстракция. «Как я закрыл $30K за 7 дней» → PASS. «Думайте о вашем мышлении» → FAIL.
3. **Простой русский / английский.** Без жаргона ниши, без чрезмерных англицизмов в RU-email. Тест: «Сказал бы avatar Subject вслух?» Нет → FAIL.
4. **Не сужает ширину.** Не отсекает подписчиков по узкой профессии если контент горизонтальный. «Маркетологи, открой!» → FAIL если email для всей базы. Допускается узкий target если segment-send (например только VIP сегмент).

Если хоть один FAIL → rewrite Subject / Preheader / first line. После 2 ретраев → escalation. Critical для email — Subject = 80% open rate impact.

## Layer 5.8 - Identity + Citations Gate (SOLO canib)

Read `~/.claude/skills/_shared/identity-citations-gate.md`, применяй Gate 1 (Identity-preservation) + Gate 2 (Verbatim citations) для body + Subject если содержат цитаты ICP. Если FAIL → revision, не proceed на Output Layer 5.

## Output Layer 5

В чат подтверждение (после Gate E PASS):

```
Fact list:
- «<utterance 1>» → verified in <source>
- «<utterance 2>» → confirmed by user
- ...

3 слоя пройдено: Layer 1 (regex) 12/12 PASS / Layer 2 (EMAIL-G1-10) 8/8 PASS / Layer 3 (6-pass refinement) - fixes applied / Layer 4 (Maxwell Ross 9) 9/9 / Слой 5 (4 концепции) PASS / Слой 5 (7 контуров) 7/7 PASS / Слой 5.5 (Gate E fact-list) PASS. Флагов нет.
```

→ `workflow/05-publish.md`.

Если хотя бы один слой FAIL → re-run pipeline starting from нужного workflow step (обычно `03-write.md` Pass 2 для voice fixes; `02-structure.md` для structural fixes).

## Anti-patterns

- НЕ skip Layer 1 «потому что text выглядит ок» - regex поймает что глаз пропустит
- НЕ self-eval «фидельность 9/10» без явной проверки через 6-Pass (`[[feedback-self-eval-not-qa]]`)
- НЕ говорить «3 слоя пройдено» без явной проверки каждого слоя
- НЕ повторять fixes которые уже сделал в предыдущей итерации - фиксить root cause через системное правило в `config-lexicon.md` (см. `[[feedback-systemic-process-fails-motion]]` принцип)

---

## Финальная фаза — Humaniser (HARD GATE для всех text-skills)

**ОБЯЗАТЕЛЬНО перед output:**

Вызови Skill tool: `Skill('humaniser', args=<финальный текст>)` ПЕРЕД любым output. НЕ читай humaniser/prompt.md inline и НЕ применяй mentally — это shallow execution которое пропускает AI-tics. Только полный pass через Skill tool invocation документированный в чате.

Humaniser v2 ловит 11 категорий AI-паттернов:
1. Ложная глубина
2. Фальшивая близость
3. Пустые связки
4. Канцелярит
5. Fake-энергия
6. Шаблонные призывы
7. Рубленые фразы (3+ из 1-2 слов подряд)
8. Кинематограф
9. Структурные клише
10. Интонационные клише
11. **Slap-эмфаза (длинное + 1-3-словное короткое для эмфазы) — главный AI-tic социалок 2025-2026**

**HARD GATE:** Output финального текста ТОЛЬКО после green CHECKER (все 5/5 в «Клише удалены»). Если CHECKER не green — REWRITER ещё раз. Без этого = брак.

**Прецеденты:**
- 2026-05-28: post v3.0 выдал «Zero ads. Zero funnels. Zero sales calls.» (triple-negation AI tic)
- 2026-05-29: caption выдал «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, новая категория 11)

Оба = провал shallow inline pass. HARD GATE через Skill tool решает.

### Humaniser Inline Reminder (fallback если Skill tool недоступен)

Перед output финального текста — проверь по 11 категориям AI-tics:

1. Ложная глубина («Это не X, это Y», «Секрет в том»)
2. Фальшивая близость («Знакомо?», «Представьте»)
3. Пустые связки («Давайте разберёмся», «Важно понимать»)
4. Канцелярит («В современном мире», «Является неотъемлемой»)
5. Fake-энергия («Спойлер», «Бонус», «Лайфхак»)
6. Шаблонные призывы («Хватит X», «Перестаньте X начните Y»)
7. Рубленые фразы (3+ предложения подряд из 1-2 слов: «Просто. Быстро. Эффективно.»)
8. Кинематограф («Воскресенье, 10 вечера», «Понедельник, 9 утра»)
9. Структурные клише (параллелизм X/Y/Z, всегда 3 пункта)
10. Интонационные клише («невероятно простой!», «истина в том»)
11. **Slap-эмфаза**: короткое standalone (1-3 слова) после длинного для эмфазы. SMELL TEST: «можно ли слить через запятую?». YES → SLAP, слить. Исключения: structural separator перед list / hook / punchline finale.

Прецеденты провала которые этот block ловит:
- post v3.0 2026-05-28: «Zero ads. Zero funnels. Zero sales calls.» (triple-negation, cat 7+9)
- caption 2026-05-29: «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, cat 11)

При нахождении любого pattern → REWRITER (переписать) → re-CHECKER → если clean → output.


---

## VALUE-DELIVERY GATE (shared, injected)

> Обязательный гейт «что текст ОБЯЗАН доставить» (вещество, не форма). Источник истины — `~/.claude/skills/_shared/value-delivery-gate.md`. Прецедент по решению автора: пост-«огрызок» без пользы + диагностическое действие.

`Read(~/.claude/skills/_shared/value-delivery-gate.md)` и примени на стадии ценности и на ревью:

1. **Действие ГЕНЕРАТИВНОЕ, не диагностическое (HARD).** Actionable-шаг даёт на руки новый результат/артефакт, а не подтверждает известное («посчитай свою цифру» = диагностика = FAIL; «собери первый продукт через нейросеть» = генеративное). Тест: появился ли у читателя НОВЫЙ результат?
2. **Реальная ценность ≥2 value-types (HARD).** Текст несёт ≥2 из: V1 инсайт / V5 модель «почему» / V2 генеративное действие / пруф-кейс с цифрой. Только «было плохо → стало хорошо + призыв» = бот-сообщение = FAIL «ноль пользы».
3. **Объём+формат — ТОЛЬКО длинные форматы** (educational/story/longform): ~2300-2500 символов, богатое форматирование ≥4 типов (<2 = брак). НЕ применять к микроформатам (tweet ≤280 / bot-message / IG-caption) — там только правила 1-2 по сути.

Независимый верификатор обязан проверить: действие генеративное? ≥2 value-types? не огрызок? Память.
**Профильный оверрайд (канон формы v2 §8.2, уровень 5 иерархии).** Ни один пункт выше не удаляется, но при объявленной цели читается так:

- **Правило 2 (≥2 value-types).** При `form_goal = reactions` и теме из белого списка канона §4.6 (быт и отдых с близкими, уязвимость и провал, ценностная поддержка читателя, праздник) требование ≥2 value-types **снимается**: носителем ценности объявляются близость, разрешение и прожитая слабость. Для целей `forwards` и `sales` правило остаётся HARD без изменений. Причина: белый список R value-types не несёт по определению, эталон верхнего квартиля («Бодрый зальчик сделали с утра») падал бы на этом гейте
- **Правило 3 (объём и «богатое форматирование ≥4 типов»).** Квота «≥4 типов» **отменена** каноном: сильный нарратив несёт 1 выделение жирным против 3 у слабого, квота заставляет добирать капсом и курсивом там, где эмпирика говорит не ставить. Вместо неё две разведённые метрики: `dev_types` (типов приёмов минимум 2, верхнего порога нет) и число выделений жирным из профиля цели (R-нарратив 1, R-разбор 1-2, F 3, S 4-5) - всё как WARN с печатью покрытия. Объём «~2300-2500 символов» заменяется коридором профиля цели (канон §3) и **не блокирует выдачу**
- **Порог «огрызка» по числу знаков** применяется только когда цель не объявлена. Ценность проверяется всегда: конъюнкция «мало знаков И нет пользы» разводится на два независимых чека, потому что сильный нарратив держится на 671 знаке, а сильный разбор на 542
- `form_goal` пуст → все три пункта работают в исходном виде, но письмо на них не выпускается: `EMAIL-G12` даёт FAIL, маршрут возврата - `01-router.md` Step 5.5 FORM-GOAL ROUTER

