# 04-review - 6-Pass + Maxwell Ross 9 + 3 слоя + long-form regex gates

> Принимает `draft_v1`. Запускает review-стек. Auto-fail на hard regex, soft warnings на pattern checks, semantic gates через LLM-judge. Output = approved draft или revision request.

## Pass 0 - Mandatory reads (BLOCKING)

1. `config.md` - секции `lexicon_*`, `voice.*`
2. `post/config.md` - наследуемый `lexicon_banned_hard`
3. `references/maxwell-ross-9-checklist.md`
4. `references/6-pass-refinement.md`
5. `references/ai-tells-longform.md`

## Pass 0.5 - Load v1.1 extension (BLOCKING)

В дополнение к `config.md` ОБЯЗАТЕЛЬНО загрузить `config-v1.1-extension.md` (создан 2026-05-28 после test incident). Все gates ниже применяются как union обоих файлов.

## Pass 1 - Hard regex gates (auto-fail)

| Gate | Check | Action on fail |
|---|---|---|
| L1-em-dash | `-` внутри строки (не в начале буллета) | replace или restructure, NO PASS |
| L1-instagram | `[Ii]nstagram` / `[Ии]нстаграм` | replace на «Нельзяграм» (RU only) |
| L1-banned-hard | Term из `post/config#lexicon_banned_hard` + `longform/config#lexicon_banned_hard` + `config-v1.1-extension#lexicon_banned_hard_v1_1_extension` | replace или restructure |
| L1-banned-longform | Term из `longform/config#lexicon_banned_longform` | restructure параграф |
| L1-generic-listicle | «10 ways to», «5 reasons», «Top N» - если type != listicle **И `form_goal != forwards`** | rename headline |
| L1-length-floor | word_count вне `[length_min..length_max]` из `brief.form_profile` - **WARN + строка обоснования** (канон §3, длина не блокирует ни в одном режиме). Пока `form_goal` пуст, действует старое правило (word_count < platform.length_floor = EXTEND, NO PASS), но выдача заблокирована `L1-form-mode` | см. ячейку |
| L1-length-ceiling | word_count вне `[length_min..length_max]` из `brief.form_profile` - **WARN + строка обоснования** (канон §3, длина не блокирует ни в одном режиме). Пока `form_goal` пуст, действует старое правило (word_count > platform.length_ceiling = TRIM, NO PASS), но выдача заблокирована `L1-form-mode` | см. ячейку |
| L1-cta-absent | Нет CTA в process секции | ADD CTA, NO PASS |
| L1-no-personal-anchor | INTRODUCTION без personal moment | REWRITE intro, NO PASS |
| L1-multiple-aha | INSIGHT содержит >1 main thesis | SPLIT or pick one, NO PASS |
| L1-fake-precision | Regex `\b\d+\.\d\b` (3.4%, 2.3x) | replace на round или verifiable |
| L1-fake-percent-no-source (v1.1) | `fake_percent_without_source` из v1.1-extension | replace verifiable или delete |
| L1-em-dash-in-headline | em-dash в headline | restructure headline |
| L1-formulaic-transitions | Phrases из `lexicon_banned_longform` | restructure |
| L1-exclamation-density | >1 «!» в первых 200 словах | reduce |
| L1-bullet-density | >5 буллетов подряд (если не listicle **И `form_goal != forwards`**) | convert to prose |
| L1-section-colon (v1.1 hard) | ≥2 подзаголовка с «:» в одном тексте | restructure headers без двоеточия |
| L1-tutorial-pattern (v1.1) | `tutorial_genre_pattern_v1_1_extension` (Уровень N: × 4+, Component N: × 4+, Часть N. × 3+) | rewrite без enumeration |
| L1-anglicism-density (v1.1) | density > 5 per 1000 слов (catalog `references/anglicism-blocker-ru.md`) | revision с diff list |
| L1-techjarg-disclosure (v1.1) | term из `references/techjarg-explain-list.md` без disclosure в первом упоминании | add disclosure |
| L1-hyperbolic-no-proof (v1.1) | `hyperbolic_claims` patterns без specific proof в same параграфе | replace или delete |
| L1-subject-diversity (newsletter only, v1.1) | 3 subjects тестируют 1 axis (см. `subject_diversity`) | regenerate тестирующие 2-3 axes |
| L1-voice-fidelity (v1.1 hard) | gold-standard corpus отсутствует ИЛИ <3 examples ИЛИ <3000 слов | **STOP PIPELINE** с message «загрузи corpus» |
| L1-anti-self-eval (v1.1) | Pass 2/3 output = «PASS» без structured findings | FAIL pass + «simulated not executed» |

### Профильные условия Pass 1 (канон формы v2, §8.2)

Источник профиля - `brief.form_goal` / `brief.form_profile` (роутер, дерево канона §2.1). Сравнение идёт только со СЛОВОМ `reactions` / `forwards` / `sales` в `brief.form_goal` и латиницей `narrative` / `razbor` / `sales` в `brief.form_class`; буква `brief.form_goal_letter` в условиях не участвует. **Поле `form_goal` пусто → правила ниже действуют в исходном виде, но статья на них не выпускается: `L1-form-mode` даёт FAIL, возврат в `01-router.md` Step 5.5 FORM-GOAL ROUTER за целью.**

- **`L1-generic-listicle` и `L1-bullet-density`** не применяются при `form_goal = forwards` (F, репосты): для носителя перечисление от 4 пунктов и цифра в заголовке - рабочие признаки верха, а не дефект (список от 4 пунктов 25/59 против 7/59, цифра в хуке 63% против 20%). Вне цели forwards оба гейта прежние
- **`L1-length-floor` / `L1-length-ceiling`** при объявленной цели берут коридор из `brief.form_profile` и дают **WARN плюс одна строка обоснования**, а не NO PASS: длина не блокирует выдачу ни в одном режиме (канон §3, разброс верха B-TOP 268..2678). Таблица `platform.length_floor/ceiling` действует, пока цель не объявлена, и **не поднимает пол выше профиля**
- Улика длины печатается строкой: `длина: <N> слов, профиль <min-max> цели <reactions/forwards/sales> (<R/F/S>)`. Если `min` профиля 0 или не задан - печатать не голую цифру, а «нижний порог снят», иначе строка читается как жёсткий пол в 0 слов: `длина: <N> слов, профиль нижний порог снят - <max> цели <reactions/forwards/sales> (<R/F/S>)`
- **Метрика приёмки** берётся только по объявленной цели (канон §5): текст цели `reactions` не оценивается по репостам, текст цели `forwards` не оценивается по реакциям. Сводная «эффективность» по одной метрике на все тексты запрещена как основание правки формы

### L1-form-mode (HARD, процедурный - Гейт 0 канона §9)

Перед прогоном Pass 1 в отчёт выводится строка формы:
`форма: цель=<reactions/forwards/sales> (<R/F/S>) класс=<narrative/razbor/sales> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>`

- Цель в улике - СЛОВО из `brief.form_goal`, буква из `brief.form_goal_letter` идёт в скобках и нужна только человеку; класс печатается латиницей, тем же значением, что лежит в `brief.form_class`. Улика в другом формате гейтом не засчитывается
- Строки нет ИЛИ `brief.form_goal` пуст → `form_mode: FAIL`, маршрут возврата: 01-router.md Step 5.5 FORM-GOAL ROUTER (дерево канона §2.1). Выпуск статьи без объявленной цели не разрешён ни одной оговоркой этого файла: это не молчаливый пропуск и не рабочий fallback, а FAIL с адресом возврата
- Две текстовые цели в одном тексте = FAIL. Безусловная реакция-подпись (канон §7) второй целью не считается
- **Конфликты формы (обязательный пункт отчёта):** `конфликты формы: <строки вида «конфликт: A vs B -> взял A по уровню N»> | нет конфликтов`. Пункта нет = HARD FAIL. Блокирующий пункт канона снимается только такой строкой с дословной цитатой правила уровня N (§8.1)
- Каждый профильный пункт печатает своё покрытие: `жирный: 1 (ровно 1 у 48% верха, ≤2 у 56%)`. Пункт без напечатанного покрытия не может иметь статус HARD

## Pass 2 - 6-Pass Refinement (LLM-judge, EXECUTED не SIMULATED)

**v1.1 hard rule (по test incident 2026-05-28):** каждый Pass должен быть EXECUTED, не self-declared.

Execution requirements per Pass:
1. Load prompt template из `references/6-pass-refinement.md` для этого Pass
2. Apply prompt к draft с явным persona
3. Output = structured YAML (см. формат в `6-pass-refinement.md` каждого Pass)
4. **Запрещено писать «PASS» как self-declaration**. Только YAML output с конкретными findings.
5. Если findings list пустой И severity=low - это evidence PASS
6. Если severity ≥medium - revision request с конкретным fix prompt

**Anti-self-eval gate:** если output Pass = «PASS» / «9/9 PASS» / «all checks passed» без structured findings list → FAIL Pass целиком, revision request с message «Pass 2.X simulated not executed. Re-run with criterion checks.»

Каждый pass = отдельный LLM-judge с конкретным prompt'ом (см. `references/6-pass-refinement.md`).

### Pass 2.1 - Skeptic
Прочитать draft как skeptical reader. Найти:
- Утверждения без proof / numbers / examples
- Hyperbolic claims («revolutionary», «10x», «обалденный»)
- Логические дыры в main_aha

Output: список претензий + suggested fixes. Fail если ≥3 critical претензий.

### Pass 2.2 - Expert (domain)
Прочитать как эксперт в нише (вайбкодинг / маркетинг для соло-экспертов). Найти:
- Технические неточности
- Outdated references (платформы / инструменты / цены)
- Поверхностное раскрытие там где нужна глубина

Output: список + fixes. Fail если ≥2 critical inaccuracies.

### Pass 2.3 - Scroller (3-секундный hook test)
Прочитать только headline + первые 2 абзаца. Решить за 3 секунды: скроллю дальше или нет?

Decisions:
- Newsletter context - open rate test (subject + preheader + первая строка)
- LinkedIn context - стоп-скролл test
- Blog context - bounce rate test (первый экран)

Output: hook ставится или нет. Fail если «скроллю» - переработать hook.

### Pass 2.4 - Competitor (reference creator)
Сравнить draft с reference creator в той же нише:
- Dan Koe для teaching/framework
- Justin Welsh для story
- Sahil Bloom для listicle
- Tim Ferriss для deep-dive

Output: что у reference сильнее + чему научиться. Fail если 3+ существенных pattern reference'а не использованы (specific numbers / personal anchor / unique frame).

### Pass 2.5 - Editor (line-by-line)
Прочитать как editor:
- Удалить filler words
- Сократить длинные предложения (>30 слов)
- Замена пассивного на активный
- Удалить дублирующие мысли
- Сверка с lexicon_banned_*

Output: cleaned draft. Не fail-gate, просто cleanup.

### Pass 2.6 - Thumbnail / Subject (newsletter only)
Если platform = newsletter - отдельный pass для subject lines:
- 3 варианта subject (40-60 chars)
- 1 preheader (90-100 chars)
- A/B-able гипотезы

Fail если все 3 варианта одинаково слабые (no contrast, no curiosity, no specific).

## Pass 3 - Maxwell Ross 9-Item Checklist (yes/no через executable criteria)

**v1.1 hard rule:** каждый вопрос проходит МАТЕМАТИЧЕСКИЙ criterion check, не «yes intuitively».

См. `references/maxwell-ross-9-checklist.md` для полного списка с executable criteria.

9 yes/no вопросов с criteria:

1. **Idea (executable):** в INSIGHT секции есть ровно ОДНА явно declared main_aha (one sentence) и все examples/reasons её поддерживают?
   - PASS: count main_aha sentences == 1
   - FAIL: 0 или ≥2

2. **Clarity (executable):** main_aha sentence appears в первых 200 словах И в conclusion?
   - PASS: both yes
   - FAIL: any no

3. **Payoff (executable):** в PROCESS секции есть actionable next step (конкретное действие читателя на эту неделю)?
   - PASS: yes specific
   - FAIL: generic / absent

4. **Specificity (executable):** count specific numbers / names / dates ≥3 per 1000 слов И count vague claims (см. `abstract_claim_signals` в v1.1-extension) ≤2 per 1000 слов?
   - PASS: both conditions
   - FAIL: any violated

5. **Freshness (executable):** main_aha contains counter-intuitive claim против current consensus в нише, ИЛИ unique frame не виденный у reference creators?
   - PASS: yes verified через Competitor Pass 2.4 actual comparison
   - FAIL: generic re-framing existing consensus

6. **Hook (executable):** Scroller Pass 2.3 returns decision=continue?
   - PASS: continue
   - FAIL: scroll-past

7. **Length (executable):** length floor ≤ word_count ≤ length ceiling per platform?
   - PASS: in range
   - FAIL: outside range

8. **Tone (executable, v1.1 hardened):** Voice Fidelity Score из comparison к gold-standard corpus ≥ 70 (out of 100)?
   - PASS: ≥70 AND corpus exists (см. 03-write Pass 0)
   - FAIL: <70 OR corpus absent
   - **v1.1: если corpus absent → mandatory FAIL, не WARN**

9. **CTA (executable):** последние 100 слов содержат specific next-step action + specific destination?
   - PASS: both present
   - FAIL: either missing

**Gate:** 9/9 PASS обязательно через executable criteria. Каждый NO → revision request с конкретным fix prompt.

**v1.1 anti-self-eval gate:** если output Pass 3 = «9/9 PASS» без per-question criterion evidence → FAIL, revision с «Pass 3 simulated not executed. Re-run with criterion checks per question.»

## Pass 4 - 3 слоя (финальный gate)

### Слой 1 - Валидаторы (regex, auto)
Pass 1 уже отработал. Здесь снова прогон чтобы убедиться что fixes из Pass 2-3 не ввели новые нарушения.

### Слой 2 - 4 концепции (semantic)

1. **Pre-mortem 5 причин провала** - представь что эта статья провалилась (open rate < 20%, нет shares, отписки). 5 причин - какие?
2. **Calibration 90%+** - я готов поставить >90% уверенности что main_aha верен и читатель его поймёт?
3. **Multi-perspective** (Маркетолог / Эксперт / Читатель):
   - Маркетолог: эта статья двигает читателя по воронке к следующему шагу?
   - Эксперт: я бы поставил это под своим именем без стыда?
   - Читатель: получил ли я что-то конкретно новое?
4. **Adaptive** - если в этой статье найдётся новая ошибка (которой нет в banned list), добавляется ли она в config / `04-review.md` Pass 1 после правки?

### Слой 3 - 7 контуров

1. **Context** - статья вписана в контекст канала (предыдущие 5 статей не противоречат)?
2. **Соответствие предпосылкам** - premise из brief (Карта смыслов / Spark idea / Transcript) сохранён?
3. **Целесообразность** - эта статья на этой платформе сейчас оправдана?
4. **Релевантность** - главный pain аудитории закрывается?
5. **Фактология** - все цифры / имена / даты verifiable?
6. **Реализуемость** - CTA читатель может выполнить из своего контекста?
7. **Достоверность** - voice автора, а не generic AI?

**Gate:** Все 3 слоя проходят явное подтверждение в output. Если что-то не проходит - revision request с конкретным списком.

## Pass 4.5 - 4 теста заголовка (SOLO `pisatel-*` canib)

Применяется к **subject line** (для newsletter / email) + **article title** (для blog / LinkedIn article) + **first sentence** (opener). Gate перед утверждением, BLOCKING:

1. **Самодостаточность.** Subject / Title понятен холодному читателю без preview / без знания автора / без открытия full article. Если читатель должен «прочитать чтобы понять о чём» → FAIL.
2. **Конкретное действие.** В Subject / Title есть глагол / результат / цифра, не абстракция. «3 системы которые дали мне $50K за квартал» → PASS. «Думайте о вашей жизни иначе» → FAIL.
3. **Простой русский / английский.** Без жаргона ниши, без чрезмерных англицизмов в RU-longform, без слов которые читатель не использует в своей речи. Тест: «Сказал бы avatar это вслух?» Нет → FAIL.
4. **Не сужает ширину.** Не отсекает читателей по узкой профессии если контент горизонтальный. «Для всех маркетологов» в Subject → FAIL если статья про общую productivity. Допускается узкий target если это сознательное намерение автора (например newsletter про конкретную нишу).

Если хоть один FAIL → rewrite Subject / Title / first sentence. После 2 ретраев → escalation в чат.

## Pass 4.7 - Identity + Citations Gate (SOLO canib)

Read `~/.claude/skills/_shared/identity-citations-gate.md`, применяй Gate 1 (Identity-preservation) + Gate 2 (Verbatim citations) для всей longform статьи. Если FAIL → revision, не proceed на output.

## Output для `05-publish.md`

Если все gates прошли:

```yaml
review_output:
  status: "APPROVED"
  draft_final: <draft>
  passes_applied:
    pass_1_hard: PASS
    pass_2_six_pass: PASS
    pass_3_maxwell_ross: 9/9 PASS
    pass_4_three_layers: PASS
    form_mode: PASS            # L1-form-mode, Гейт 0 канона формы v2 §9
  form:                        # улика режима; goal: null = FAIL формы, статус APPROVED недостижим
    goal: <reactions|forwards|sales|null>       # слово, значение для сравнений
    goal_letter: <R|F|S|null>                   # буква, только печать человеку
    class: <narrative|razbor|sales|null>
    profile: <длина min-max / жирный N / списков N / ссылок N>
    conflicts: <строки «конфликт: A vs B -> взял A по уровню N»> | нет конфликтов
  fixes_applied: [<list of changes from Pass 2-3>]
  voice_fidelity_score: <subjective 0-100, just signal>
```

Если revision request:

```yaml
review_output:
  status: "REVISION_REQUESTED"
  draft_intermediate: <current>
  failures:
    - gate: "<gate name>"
      issue: "<>"
      suggested_fix: "<>"
  retry_from_pass: <number>
```

`form_mode: FAIL` (нет улики формы, две цели в одном тексте или отсутствует пункт «конфликты формы») входит в критерии REVISION_REQUESTED наравне с остальными hard-гейтами и возвращает в роутер за целью, а не в Pass 2/3.

`03-write.md` Pass 2/3 повторяется с конкретным fix prompt. Максимум 3 итерации, потом возврат пользователю с явным описанием что не получилось.

## Memory cross-refs

- - 3 слоя обязательно
- - не «всё ОК» без e2e теста
- - root cause + sweep похожих мест
- - без негативных статистик
- - конкретные числа
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
- `form_goal` пуст → все три пункта работают в исходном виде, но статья на них не выпускается: `L1-form-mode` даёт FAIL, маршрут возврата - `01-router.md` Step 5.5 FORM-GOAL ROUTER

