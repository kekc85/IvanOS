# 04-review.md - Review (6-Pass + Maxwell Ross 9 + 3 слоя + Hook/Thread Gates)

Принимает draft от 03-write. Прогоняет через все validators. Output = clean text OR fail list.

## Stage 1 - Deterministic validators (regex / grep, auto-fail)

### G1 - Char limits
- X tweet >280 chars (без `--long` флага) → fail
- X Premium long >25000 chars → fail
- Threads post >500 chars → fail
- Thread hook tweet >220 chars → warning

### G2 - Em-dash / lexicon
- Em-dash «-» inside line (not bullet start) → fail (memory rule)
- "Instagram" (RU mode) → auto-correct "Нельзяграм"
- Banned terms (config.banned_terms.ru / en) → fail

### G3 - Hashtags / engagement bait
- Any hashtag in X output → fail (2026 algorithm penalty)
- Any "RT if you agree" / "Like if you" / "comment X" engagement bait → fail
- "🧵" в hook tweet OK (thread indicator); другие emoji в hook → warning

### G4 - Links
- Links в hook tweet → warning (move to thread closer)
- Multiple links в single tweet → warning

### G5 - Excessive punctuation
- >1 "!" → warning
- ">3 ?" → warning

### G6a - AI-tells EN (если language=en)
- "delve", "tapestry", "in conclusion", "moreover", "furthermore", "ensure" → fail
- Full list в `references/ai-tells-en.md`

### G6b - AI-tells RU (если language=ru) [NEW v1.1, расширено v1.2]
- Tier 1 риторические AI-фигуры → fail (auto-reject)
  - 1A Triple-negation reveals: "Не X. Не Y. Не Z. [W]." → fail
  - 1B Gravitas openers: "Что важно сделать первым", "Главное открытие", "В этом и заключается", "По сути" → fail
  - 1C Reveal markers: "Вот в чём дело", "Дело вот в чём", "Правда в том что", "На самом деле всё проще" → fail
  - 1D Inflated importance: "Стоит отметить что", "Важно понимать что", "Не случайно что" → fail
  - 1E AI generic openers: "В современном мире", "В сегодняшних реалиях", "В наше время", "В эпоху ИИ" → fail
  - **1F Bare-imperative staccato pairs/triples (v1.2)**: "Сначала X. Потом Y.", "X. Не Y.", "X. И всё.", "X. Точка.", "X. Без вариантов.", "Делай. Тестируй. Запускай." → fail
- Tier 2 → warning (manual review)
- Tier 4 автор-specific banned: "выстрелил", "не зашло", "закрывает боль", "полная картина", "комплексный подход", "глубоко погрузиться", "копнуть глубже", "разложить по полочкам" → fail
- Tier 5 structure tells (semantic): tri-parallel без оправдания / каждый абзац с reveal markers → manual fail
- Full list + alternatives в `references/ai-tells-ru.md`

**Важно:** Humaniser (финальная фаза этого файла) дополнительно ловит "Triple-X parallel emphasis" + "Voice-signature theft" + 10 других категорий. G6b = early catch, Humaniser = final gate.

### G6c - RU grammar russification (если language=ru) [NEW v1.1]
- Грамматические кальки с EN:
  - "делать результат" → fail, suggest "давать результат" / "приносить результат"
  - "иметь результат" → fail, suggest "получить результат"
  - "делать смысл" → fail, suggest "иметь смысл" / "логично"
  - "делать прогресс" → fail, suggest "продвигаться"
  - "построить экосистему" → fail (Tier 4 banned)
- Запрещённые англицизмы в RU narrative:
  - "shipped", "real", "mode", "platform", "feature", "update", "release" → fail
  - Voice corpus terms ОК: "Нельзяграм", "вайбкодинг", "вайбмаркетинг", "контент-завод", "Дубайск"
- Full list в `references/ru-grammar-russification.md`

### G7 - Hook Char Zone Gate (**понижен до WARN** каноном формы v2)
- Hook char count в 100-200 dead zone → **WARNING плюс одна строка обоснования** (было fail). Зоны заимствованы из чужого исследования Welsh/Bloom/Cole и с нашими данными не сверены: у нас измерена не длина хука, а состав
- Zone A (40-100) и Zone B (200-280) остаются ориентиром уровня 7 (плоский дефолт скилла)
- **Состав хука при объявленной цели (HARD-часть, канон §3 и §4.1):**
  - `form_goal = forwards` (F): цифра или валюта в хуке **обязательна** (63% верха против 20% низа), хук не короче 50 знаков, цель 64
  - `form_goal = reactions` (R): в первой строке нет числа ≥1000 и нет круглой метрики канала, `+` первым знаком - fail (чистое поле держат 93% верха); хук - сцена или парадокс, ориентир 60 знаков (WARN). FAIL по регексу `^(Как я |Как \w+ (заработать|разбогатеть)|\d+ (шагов|способов)|Антикризис)`
  - `form_goal = sales` (S): в самом хуке нет связки «ты/твой/вы + сумма дохода или число подписчиков» - **HARD** (0/34 в верхе против 3/34), цель 36 знаков, ориентир 50 - WARN (держат 62% верха)
  - `form_goal` пуст → это само по себе `form_mode: FAIL` (Гейт 0 ниже, HARD), а не WARNING по старым зонам: состав хука здесь не оценивается, пайплайн обязан был остановиться в `01-router.md` Step 5.5
- `formula_id` шаблона при объявленной цели - опциональное поле, не условие PASS

### G8 - Thread Length Gate (HARD)
- Thread total в 3-7 awkward middle → fail
- PASS если single OR 8-15 compact OR 18-34 mega

### G9 - Нумерация в теле (профильно, канон v2 §8.2)

Было: «Numbered list тип: "1." numbering ОК в beats, NOT в final tweet». Стало - по цели формы:

- `form_goal = sales` (S): **нумерация запрещена целиком**, любой `^\d+\.` и «Шаг N» → **FAIL** (88% верха держат; 12% против 21% - единственный класс, где нумерация действительно маркер низа)
- `form_goal = reactions` (R), класс нарратив: нумерация → **WARNING** (база пустая, 4% против 7%)
- `form_goal = reactions` (R), класс разбор: **разрешена** (25% против 17%, знак обратный, гейт снят)
- `form_goal = forwards` (F): **разрешён алгоритм 3-5 шагов** (25% против 10%) - единственное место, где нумерация желательна; больше 5 шагов → WARNING
- `form_goal` пуст → это само по себе `form_mode: FAIL` (Гейт 0 ниже, HARD): нумерация здесь не оценивается, пайплайн обязан был остановиться в `01-router.md` Step 5.5
- Шаблон `templates/numbered-list.md` - **условный**: вызывается только при цели «репосты» и только когда цифра работает обещанием в хуке. Вне этого условия тип не предлагать

## Stage 2 - 6-Pass Refinement (LLM)

Каждый pass = critical persona:

### Pass 1 - Skeptic
"Что слабого в hook? Почему пользователь прокрутит?"

### Pass 2 - Expert
"Что технически неточно? Что неверно по существу?"

### Pass 3 - Scroller
"Если я scroll'ю feed - почему остановлюсь именно тут?"

### Pass 4 - Competitor (Alex Finn / Welsh / Hormozi)
"Как бы я этот пост написал? Что автор упустил?"

### Pass 5 - Editor
"Что вырезать? Какие слова лишние?"

### Pass 6 - Thumbnail (first impression в feed)
"Hook line одна - что reader увидит без context?"

Каждый pass → list improvements. Apply.

## Stage 3 - Maxwell Ross 9-Item Checklist

| # | Question | Pass/Fail |
|---|---|---|
| 1 | Has a clear idea? | |
| 2 | Crystal clear writing? | |
| 3 | Clear payoff? | |
| 4 | Specifics over abstraction? | |
| 5 | Fresh angle? | |
| 6 | Strong hook? | |
| 7 | Right length? | |
| 8 | Right tone? | |
| 9 | CTA appropriate? | |

**9/9 required. Меньше - rewrite specific beat.**

## Stage 4 - 3 слоя финальный gate

### Слой 1 - Валидаторы
Already done в Stage 1.

### Слой 2 - 4 концепции
- Pre-mortem: 5 причин почему пост провалится? Mitigate каждый.
- Calibrate confidence 90%: «я уверен на 90% что hook сильный»?
- Multi-perspective: 3+ angles на single post?
- Adaptive: новый finding из last 5 posts intergrated?

### Слой 3 - 7 контуров
- Context (соответствует ли brief?)
- Соответствие предпосылкам (Карта смыслов / spark idea?)
- Целесообразность (правильный ли это тип / format?)
- Релевантность (для avatar?)
- Фактология (numbers / names verified?)
- Реализуемость (автор правда может зарелизить с этим content?)
- Достоверность (proof assets verified из `.business/`?)

## Stage 4.5 - 4 теста заголовка (SOLO `pisatel-*` canib)

Применяется к **first tweet** (для single tweet) или **opener tweet** (для thread). Gate перед утверждением, BLOCKING:

1. **Самодостаточность.** First tweet понятен холодному читателю без открытия thread / без знания автора. Если читатель должен «развернуть чтобы понять о чём» → FAIL для single. Для thread — opener должен заинтересовать настолько, чтобы кликнуть «show more».
2. **Конкретное действие.** В first tweet есть глагол / результат / цифра, не абстракция. «Сделал $10K за месяц через X» → PASS. «Думайте о вашем потенциале» → FAIL.
3. **Простой английский / русский.** Без жаргона ниши, без чрезмерных англицизмов в RU-tweet, без слов которые читатель не использует в своей речи. Тест: «Сказал бы avatar это вслух?» Нет → FAIL.
4. **Не сужает ширину.** Не отсекает читателей по узкой профессии если контент горизонтальный. «Для всех маркетологов» → FAIL если tweet про общую productivity. Допускается узкий target если это сознательное намерение автора.

Если хоть один FAIL → rewrite first tweet. После 2 ретраев → escalation.

## Stage 4.7 - Identity + Citations Gate (SOLO canib)

Read `~/.claude/skills/_shared/identity-citations-gate.md`, применяй Gate 1 (Identity-preservation) + Gate 2 (Verbatim citations) если в tweet есть цитаты ICP. Если FAIL → revision, не proceed на Stage 5.

## Stage 5 - Output verdict

```yaml
review_verdict:
  stage_1_deterministic: PASS | FAIL <details>
  stage_2_six_pass:
    skeptic: <improvements>
    expert: <improvements>
    scroller: <improvements>
    competitor: <improvements>
    editor: <improvements>
    thumbnail: <improvements>
  stage_3_maxwell_ross: <N>/9
  stage_4_three_layers: PASS | FAIL <which layer>
  form_mode: PASS | FAIL        # Гейт 0 канона формы v2 §9
  form:                         # улика режима; goal ОБЯЗАН быть одним из R|F|S|A - null это FAIL, не легальное значение
    goal: <R|F|S|A|null>
    class: <narrative|razbor|sales|gate|null>   # латиница, единый словарь с brief.form_class; русские слова только в человекочитаемой строке-улике ниже
    profile: <длина min-max / жирный N / списков N / ссылок N / цифра в хуке да-нет>
    conflicts: <строки «конфликт: A vs B -> взял A по уровню N»> | нет конфликтов
  final: PASS | FAIL
```

**form_mode (HARD, процедурный).** До первой строки должна быть зафиксирована цель (reactions / forwards / sales / gate), класс, тема и профиль, улика печатается строкой ровно в этом формате (цель - словом, буква - в скобках только для чтения человеком, значение для гейтов - слово):
`форма: цель=<reactions|forwards|sales|gate> (<R/F/S/A>) класс=<...> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>`

- Улики нет ИЛИ `brief.form_goal` пуст (в т.ч. если печатается строка с `goal: null` - такая строка не является уликой выбранной цели и FAIL не снимает) → `form_mode: FAIL`, маршрут возврата - 01-router.md Step 5.5 FORM-GOAL ROUTER, выбор цели по дереву канона §2.1, а не правка текста
- Две текстовые цели в одном посте = FAIL. Безусловная реакция-подпись (канон §7) второй целью не считается
- Пункт `conflicts` обязателен: его отсутствие = `form_mode: FAIL`. Блокирующий пункт канона снимается только строкой конфликта с дословной цитатой правила уровня N (§8.1)
- Каждый профильный пункт печатает покрытие (`жирный: 1 (ровно 1 у 48% верха, ≤2 у 56%)`); пункт без покрытия не может иметь статус HARD
- Метрика приёмки берётся только по объявленной цели (канон §5): пост цели R не оценивается по репостам, пост цели F не оценивается по реакциям
- `form_mode: FAIL` включается в критерии общего FAIL наравне с прочими hard-гейтами

Если FAIL - rewrite specific beats и re-run review.
Если PASS - hand off to `05-publish.md`.

## Anti-patterns review

- НЕ skip любую stage
- НЕ FAIL silently - каждый fail с подробным reason
- НЕ accept 8/9 Maxwell Ross - rewrite missing item
- НЕ proceed без явного «3 слоя пройдено» подтверждения
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
- `form_goal` пуст → до этой стадии доходить не должно: `form_mode: FAIL` (Гейт 0) останавливает пайплайн раньше, а не переводит эти три пункта на дефолт

