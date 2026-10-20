# Workflow 04-review - 6-Pass + Maxwell Ross 9 + 3 слоя + 9 carousel gates

**Назначение:** финальная валидация carousel object перед publish. Auto-fail если любой hard gate fails.
**Вход:** `carousel` от `03-write.md`
**Выход:** PASS-report или FAIL-list с required fixes → `03-write.md` re-pass / `05-publish.md`

---

## Шаг 1 - Hard validators (regex auto-fail)

Прогнать через детерминистические проверки. ЛЮБОЙ fail = блок.

```yaml
hard_validators:
  - id: HV1
    name: em-dash inline
    check: "regex `-` внутри строк (только начало bullet ОК)"
    auto_fix: replace `-` → `-` в slide text + caption
    
  - id: HV2
    name: Instagram literal
    check: "regex 'Instagram' | 'инстаграм' / case-insensitive"
    auto_fix: replace на «Нельзяграм»
    
  - id: HV3
    name: banned англицизмы
    check: "match against config.lexicon_banned_hard"
    auto_fix: flag для author, не auto-replace
    
  - id: HV4
    name: slide count vs family
    check: "len(carousel.slides) ∈ config.family_specs[family].slide_count"
    fail_action: split/merge slides + re-write
    
  - id: HV5
    name: per-slide length
    check: "word_count(slide.text) ∈ config.family_specs[family].slide_text_budget[role]"
    fail_action: re-write slide text
    
  - id: HV6
    name: caption length
    check: "len(caption[lang]) ≤ platform.caption_max"
    fail_action: trim caption
    
  - id: HV7
    name: hashtags count
    check: "count(hashtags) ∈ platform.hashtags_optimal"
    fail_action: adjust hashtags

  - id: HV8
    name: нумерация в тексте (канон формы v2 §8.2)
    check: "regex `^\\s*\\d+[.)]\\s` ИЛИ «Шаг \\d+» в slide.text ИЛИ в caption[lang]"
    scope: "ТОЛЬКО текстовый слой - текст слайда и caption. Визуальная нумерация на слайде (номер-плашка, счётчик 3/10, цифра как графический элемент макета) НЕ трогается: визуальный слой живёт по своей анатомии"
    profile_rules: |
      form_goal = sales (S)      → FAIL всегда (88% верха держат ноль нумерации;
                                    12% против 21% - единственный класс, где нумерация маркер низа)
      form_goal = reactions (R), нарратив → WARNING (база пустая, 4% против 7%)
      form_goal = reactions (R), разбор   → разрешена (25% против 17%, знак обратный, гейт снят)
      form_goal = forwards (F)   → разрешён алгоритм 3-5 шагов (25% против 10%);
                                    больше 5 шагов → WARNING
      form_goal пуст             → это само по себе form_mode: FAIL (Гейт 0 ниже, HARD),
                                    а не WARNING по старым правилам; пайплайн обязан был
                                    остановиться в 01-router.md Шаг 4.5
    fail_action: переписать пункты в предикативные строки (каждый пункт содержит глагол или является вопросом) либо развернуть в причинную цепь
```

**Профильные условия Шага 1 (канон формы v2).** Источник - `brief.form_goal` / `brief.form_profile`. **Поле пусто → до этого шага доходить не должно: `form_mode: FAIL` (Гейт 0, см. ниже) останавливает пайплайн в `01-router.md` Шаг 4.5 раньше, HV1-HV8 по старым правилам здесь не запускать.** При объявленной цели:

- **HV5 и HV6 (длины)** при объявленной цели дают **WARNING плюс строку обоснования**, а не блок: длина не блокирует выдачу ни в одном режиме (канон §3, разброс верха огромен). Бюджеты `config.family_specs` и `platform.caption_max` остаются fallback и **не поднимают пол выше профиля**. Улика: `длина caption: <N> в профиле <min-max> цели <R/F/S>`
- **Ссылки в caption:** `form_goal = reactions` - ноль ссылок (любой `http`, `t.me/`, `](` - FAIL, ноль у 89% верха); `form_goal = forwards` - ссылка обязательна и стоит в последних 250 знаках caption (92% и 80% верха), повтор адреса разрешён; `form_goal = sales` - якорей 0 или 1 адрес (91% верха), финал caption не URL и не команда действия (85% верха), повтор адреса - WARNING
- **Метрика приёмки** берётся только по объявленной цели (канон §5): карусель цели R не оценивается по репостам, карусель цели F не оценивается по реакциям

---

## Шаг 2 - 9 carousel-specific gates (LLM judges)

```yaml
carousel_gates:
  CR-G1:
    name: Slide count optimal
    check: "len ∈ [8,12] для IG / [7,20] для LI / [3,8] для panorama"
    severity: FAIL
    
  CR-G2:
    name: Per-slide length OK
    check: "hook 3-12 слов / value 5-25 / CTA 5-15"
    severity: FAIL
    
  CR-G3:
    name: Hook ≠ cover
    check: "slide 1 содержит number + outcome + timeframe, не просто title"
    severity: FAIL
    test: "Если убрать slide 1 - теряется ли promise? Если нет - fail."
    
  CR-G3.5:
    name: Headline 4 tests (NEW 2026-05-28, from SOLO pisatel-karuseli)
    check: "headline проходит все 4 теста — самодостаточность / конкретный предмет / простой русский / не сужает ширину"
    severity: FAIL
    tests:
      - test_1_self_sufficient: "Заголовок читается без знания темы/контекста? (ICP-новичок проснулся в 3 ночи — поймёт за 1 сек?)"
      - test_2_concrete_subject: "В заголовке конкретный предмет/действие, не абстракция? Запрет: «продукт» (общо), «работает», «получится», «изощрённый»"
      - test_3_plain_russian: "Произнести вслух — звучит как речь, не как академический текст?"
      - test_4_keeps_breadth: "Применимо к разным нишам ICP (психология / нутрициология / коучинг / эзотерика)? Не сужает воронку?"
    fail_action: "Заголовок переписать. Если 3+ из 4 fail — переформулировать тему."
    
  CR-G4:
    name: Real elements floor ≥40%
    check: "≥40% slides содержат конкретный UI/product/number в real_elements"
    severity: FAIL
    
  CR-G5:
    name: Banned AI imagery scan
    check: "ни один visual_brief не попал в config.banned_ai_imagery"
    severity: FAIL
    examples_to_catch:
      - "generic gradient blob background"
      - "AI-illustrated person at laptop"
      - "robot hand typing"
      - "abstract 3D shapes без identity"
    
  CR-G6:
    name: Pacing chain
    check: "каждый slide N tease'ит N+1 ИЛИ закрывает loop"
    severity: WARN
    test: "Reader входит на slide N - может ли он понять надо ли свайпать?"
    
  CR-G7:
    name: Caption ≠ slides duplication
    check: "caption даёт доп. layer, не пересказывает slides"
    severity: FAIL
    test: "Удалить caption - теряется ли value? Если нет (caption = пересказ) - fail."
    
  CR-G8:
    name: Platform constraint
    check: "IG ≤10 optimal, LI ≤20 PDF pages"
    severity: WARN
    
  CR-G9:
    name: Panorama integrity (только family=panorama)
    check: "leading slide работает isolated + cut lines не на лицах/key text + areas of interest distributed"
    severity: FAIL
```

---

## Шаг 3 - 6-Pass Refinement (LLM)

Прогнать carousel через 6 ролей:

```yaml
six_pass:
  - Skeptic: "Каждый slide стоит ли быть отдельным? Можно убрать без потери смысла?"
  - Expert: "Visual brief достаточно конкретный для дизайнера / AI? real_elements типизированы?"
  - Scroller: "Hook slide тянет ли свайп? 0.25s test - стоп scroll?"
  - Competitor: "Отличается ли carousel от типичной AI-карусели в нише? Не выглядит generic?"
  - Editor: "Лексика чистая? Лишние слова? Wall of text где не нужно?"
  - Thumbnail: "Hook slide читается ли в feed preview (small size)?"
```

Каждый pass → notes + suggested fixes.

---

## Шаг 4 - Maxwell Ross 9-checklist

9 yes/no pre-publish (carousel-адаптировано):

1. Идея ясная и одна?
2. Hook slide тянет свайп?
3. Payoff slides доставляют обещанное?
4. Specificity вместо vagueness (real numbers / real names)?
5. Freshness - не повтор за 7 дней?
6. CTA action-specific, не «follow me»?
7. Length OK per slide / per carousel?
8. Voice consistent с автором?
9. Real elements ≥40%?

9/9 PASS обязательно. Любой no → fix.

---

## Шаг 5 - 3 слоя финальный gate

**Слой 1 валидаторы (deterministic):** HV1-HV8 прогнаны выше (HV8 - нумерация в тексте, профильно по цели формы).

**Слой 2 4 концепции (LLM):**
- Pre-mortem: 5 причин почему carousel может не сработать в feed
- Calibrate confidence: 90% уверены что engagement > median?
- Multi-perspective: маркетолог / scroller / клиент - у всех 3 ок?
- Adaptive: новая ошибка детектена → добавить в banned patterns / lexicon

**Слой 3 7 контуров:** Context / Соответствие предпосылкам / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность - каждый PASS.

---

## Шаг 6 - Результат

Если все hard validators + 9 gates + 6-pass + Maxwell Ross + 3 слоя PASS:

```yaml
review_status: PASS
findings: []
form_mode: PASS          # Гейт 0 канона формы v2 §9
form:                    # улика режима; goal ОБЯЗАН быть одним из R|F|S|A - null это FAIL, не легальное значение
  goal: <R|F|S|A|null>
  class: <narrative|razbor|sales|gate|null>   # латиница, единый словарь с brief.form_class; русские слова только в человекочитаемой строке-улике ниже
  profile: <длина caption min-max / списков N / ссылок N / цифра в хуке да-нет>
  conflicts: <строки «конфликт: A vs B -> взял A по уровню N»> | нет конфликтов
proceed_to: "workflow/05-publish.md"
```

**form_mode (HARD, процедурный).** До первого слайда фиксируется цель (reactions / forwards / sales / gate), класс, тема и профиль; улика печатается строкой ровно в этом формате (цель - словом, буква - в скобках только для чтения человеком, значение для гейтов - слово):
`форма: цель=<reactions|forwards|sales|gate> (<R/F/S/A>) класс=<...> тема=<...> -> длина caption <min-max>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>`

- Улики нет ИЛИ `brief.form_goal` пуст (в т.ч. если печатается строка с `goal: null` - такая строка не является уликой выбранной цели и FAIL не снимает) → `form_mode: FAIL`, маршрут возврата - 01-router.md Шаг 4.5 FORM-GOAL ROUTER, выбор цели по дереву канона §2.1, а не правка слайдов
- Две текстовые цели в одной карусели = FAIL. Безусловная реакция-подпись (канон §7) второй целью не считается
- Пункт `conflicts` обязателен: его отсутствие = `form_mode: FAIL`. Блокирующий пункт канона снимается только строкой конфликта с дословной цитатой правила уровня N (§8.1)
- Каждый профильный пункт печатает покрытие; пункт без напечатанного покрытия не может иметь статус HARD
- `form_mode: FAIL` входит в критерии `review_status: FAIL` наравне с прочими hard-гейтами

Если есть failures:

```yaml
review_status: FAIL
findings:
  - gate: CR-G3
    issue: "Hook = title без promise"
    fix: "Re-write slide 1 с number + outcome + timeframe"
proceed_to: "workflow/03-write.md re-pass"
```

Max 2 re-pass loops. Если 3rd loop fails - escalate to user.

---

## Принципы

1. **Hard gates auto-fail.** Без обхода.
2. **9 gates carousel-specific.** Не пропускать ради скорости.
3. **6-Pass LLM thorough.** Каждая роль выявляет свой класс багов.
4. **Maxwell Ross 9 - pre-publish gate.** Все 9 yes.
5. **3 слоя финальный.** Без явного «3 слоя пройдено» в output - не proceed.
6. **Max 2 re-pass.** Иначе escalate.
---

## Шаг 5.5 - Identity + Citations Gate (SOLO canib)

Read `~/.claude/skills/_shared/identity-citations-gate.md`, применяй Gate 1 (Identity-preservation) + Gate 2 (Verbatim citations) если в карусели есть цитаты ICP. Если FAIL → revision, не proceed на Humaniser.

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

