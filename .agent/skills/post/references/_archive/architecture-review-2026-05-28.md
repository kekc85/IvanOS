# Architecture Review v1→v18 - post skill

**Дата:** 2026-05-28
**Контекст:** 18 итераций в одной сессии в даты запуска.2026 не дали стабильного «нажал → готовый пост». Каждая итерация закрывала один класс ошибок, но новый класс появлялся уровнем выше.
**Цель документа:** решение - оставлять архитектуру A (one-shot), переходить на B (iterative co-creation) или строить hybrid.

---

## 1. Pattern analysis 18 итераций

### Хронология fail-классов

| Версии | Фокус правок | Класс ошибки | Тип gap |
|---|---|---|---|
| v1-v7 | AI-tells lexical (метафоры / несуществующие collocations / em-dash / точка в конце абзаца) | Лексический шум на уровне слова и фразы | Implementation gap (skill знает правила но не применяет) |
| v8-v11 | Sales pivot + длинные параграфы | Структура абзацев - длина и переходы | Process gap (нет stage rhythm-check) |
| v12-v13 | Микроабзацы overcorrection | Перекос компенсации | Process gap (правка предыдущей итерации перегнула) |
| v14-v17 | Voice + Imagery 0/13 параграфов | Imagery / sensory / emotion полностью отсутствуют | **Architectural gap** (skill не моделирует, что писатель - это присутствующий автор, а не argument-generator) |
| v18 | Character violation + implementation gap + value vacuum | Skill сгенерировал generic argument без insight который оправдывал бы публикацию | **Domain modeling gap** + **Architectural gap** |

### 4 типа gaps - сводно

**1. Implementation gap (v1-v7, частично v18).** Skill знает правило но не применяет. Решено через hard regex gates в `04-review.md` и Pass 0 mandatory reads. Это закрывается архитектурно. После v1.2 implementation gap почти не появлялся - gates ловят.

**2. Process gap (v8-v13).** Workflow stages в неправильном порядке или отсутствуют. Решено через добавление stages (rhythm-check, length floor+ceiling, paragraph connectivity). Это **закрывается** добавлением stage. Но каждая новая категория ошибок требует нового stage - bloat без верхней границы. `04-review.md` уже 995 строк.

**3. Domain modeling gap (v14-v17).** Skill моделирует пост как «argument с правильной лексикой», но авторский пост - это **присутствие автора в моменте**, где argument - лишь одна функция. Imagery / sensory / emotional beats - это не «добавить красочности», это **онтология жанра**. Решение через checklist (R1-R7 из post-v17-craft-audit) - это inject через rule. Работает на следующем посте только потому что Claude применил rule, не потому что понял жанр.

**4. Architectural gap (v18 и фундаментально через всю историю).** Skill пытается за один pass воспроизвести то, что автор делает за десятки micro-decisions: какой именно момент жизни выбрать как anchor, какой insight стоит публикации (а не «звучит ок»), какой именно глагол из 5 синонимов, какой именно meta-comment в скобках. **Эти решения требуют author judgement, а не правил**. Каждая дополнительная rule в skill закрывает один класс предсказуемых ошибок, но не закрывает класс «author would do something different / surprising here».

### Common pattern всех 18 итераций

После каждой итерации формат правки одинаковый: «автор заметил X → системный fix через memory + workflow gate + reference update». Это работает для классов **predictable errors** (formal lexicon / passive / participle). Это **не работает** для классов **judgement calls** (какой именно anchor / insight / нюанс - выбирает автор по контексту).

**Ключевой вывод:** 18 итераций показали асимптоту. Predictable error classes - closeable. Judgement-level decisions - не closeable никаким количеством rules, потому что они не decision tree, они authorial taste.

---

## 2. Architecture A - One-shot generation (current)

### Описание

Skill принимает тему/триггер → router → mode-ideate → finalize → structure → write → review → output. На выходе финальный пост, автор либо принимает либо правит.

### Pros

- Полная автоматизация. Triggered одним сообщением.
- Tiражируемо для учеников курса (запустил → получил пост).
- Voice фиксируется в правилах → ученик получает «автора в коробке».
- Каждая правка → системный rule → следующий пост лучше.

### Cons (наблюдаемые)

- 18 итераций на одном посте. Закрыли predictable errors, но не закрыли author judgement.
- `04-review.md` 995 строк, _voice-TEMPLATE.md 1317 строк. Rule bloat без верхней границы.
- Каждая правка добавляет gate. Gates конфликтуют (микроабзацы vs flow, length floor vs voice density).
- Skill даёт **structurally correct** posts, но без insight который оправдывает публикацию. v18 fail = «structurally compliant, semantically empty».
- Imagery / sensory / emotion gaps - не закрываются rule «inject метафору P5», потому что rule даёт **predictable метафору**, а автор делает **surprising метафору** в этом конкретном контексте.

### Failure mode

автор правит 18+ раз → класс «judgement-level decisions» в skill принципиально не закрываем добавлением rules. После v18 автор:
- тратит время на правки больше чем сэкономил на генерации
- или принимает structurally-OK пост, теряя качество канала
- или прекращает использовать skill

---

## 3. Architecture B - Iterative co-creation

### Описание

Skill выдаёт **не финальный пост**, а **5 компонентов** для сборки автором:

1. **Research summary** - что есть в Карте смыслов / corpus / последних 30 постах канала / 8/10 конкурентов по этой теме. Какие angle уже отработаны, какие свежие. (2-3 абзаца)
2. **Genre × value × JTBD tuple choice** - 3 варианта tuple (например: Narrative-разбор × «увидеть себя в кейсе» × «как начать») с обоснованием почему именно эта комбинация под текущий контент-план. автор выбирает 1.
3. **3 hook variants × 3 reveal variants × 3 close variants** - 9 components total для собранного tuple. Каждый - 2-4 предложения с design-memo «откуда» (verbatim post X / pattern Y).
4. **Value-injection points** - 3-5 конкретных insight из corpus / Карты с verbatim цитатой источника. Не «об этом можно сказать», а готовые insight-blocks которые автор может вставить.
5. **Sentence-level patterns** - 5-10 фраз / оборотов / переходов из corpus которые применимы к текущему tuple (verbatim source + контекст применения).

автор выбирает hook + reveal + close + 1-3 insight → собирает структуру. Skill полирует selected combination (применяет 8 hard gates / Living Language pass / etc).

### Pros

- Leverages Claude в его strengths - research / options generation / pattern matching / polishing. Не пытается заменить authorial taste.
- Author judgement остаётся за автором. Surprising choices (какой anchor / insight / нюанс) делает автор - машина не «угадывает», что бы он выбрал.
- Каждый компонент с design-memo → автор видит **откуда** компонент, может оценить fit без чтения 1300 строк rules.
- 18 итераций → 1-2 раунда (выбор tuple → выбор components → polish).
- Bloat rules не нужен - rules применяются только в финальный polish stage, не в generation. Skill короче.

### Cons

- Не «нажал → получил пост». Требует engagement автора на 2-3 решениях per post.
- Менее tiражируемо для учеников курса: ученик должен **уметь выбирать**, а не «получать готовое».
- Output на промежуточных стадиях большой (research + 9 components + 5 insights = ~3000-5000 chars экранного текста). Cognitive load растёт.
- Если автор хочет «просто пост сегодня без выбора» - этот mode принципиально это не даёт.

### Failure mode

автор закрывает skill потому что не хочет принимать 3 решения per post. Или ученик курса не понимает что выбирать, потому что нет authorial taste - компоненты выглядят все одинаково ОК.

---

## 4. Architecture C - Hybrid (proposed)

### Описание

Skill определяет жанр на стадии router. Маршрутизирует по двум веткам:

**Branch 1 - Fast lane (one-shot generation)** для 3 простых жанров:
- Lifestyle + brag с одной цифрой
- Alarm + reaction (crisis news + автор действие)
- Tool drop (короткий анонс)

Эти жанры:
- короткие (~1500 chars)
- value-load низкий (одна цифра / одна реакция / один tool)
- structure predictable
- author judgement сводится к выбору anchor (что Claude может сделать через few-shot из corpus)

Skill выдаёт финальный пост за один pass. Применяет 8 hard gates. автор либо публикует либо правит.

**Branch 2 - Co-creation lane (iterative)** для 2 сложных жанров:
- Narrative-разбор-кейса (story первого лица с insight delivery)
- Build-in-public с paradox-hook (длинный пост с reveal который должен удивить)
- Vulnerability + reveal (paradox-история без полного resolve)

Эти жанры:
- длинные (1500-2500 chars)
- value-load высокий (insight должен оправдать публикацию)
- structure varied (paradox / surprise / reveal - не predictable)
- author judgement критичен на каждом узле (какой anchor / какой reveal / какой close)

Skill выдаёт 5 компонентов (research + tuple choice + 9 components + insights + patterns). автор собирает. Skill полирует.

### Router signal

`02-structure.md` уже определяет тип поста (1 из 8). Mapping:

| Тип | Lane |
|---|---|
| 1. Short situational | Fast |
| 2. Long educational | Co-creation (если >2000 chars target) |
| 3. Tweet | Fast |
| 4. Story arc | Co-creation |
| 5. Personal/values | Co-creation |
| 6. Build-in-public | Co-creation |
| 7. Tool drop | Fast |
| 8. Sales/launch | Co-creation (high stakes) |

### Pros

- Закрывает оба сценария: «срочный простой пост» и «глубокий длинный с insight».
- Для tiражирования ученикам - fast lane работает «нажал → получил», co-creation lane обучает выбору (что и есть продукт курса вайбмаркетинга - научить выбирать).
- Не добавляет complexity в существующий skill: router уже есть, просто новая dimension routing.
- Rule bloat в fast lane = OK (predictable жанры, rules покрывают). Co-creation lane не накапливает rules - там judgement автора.

### Cons

- Требует honest classification «какие жанры реально простые». Если автор захочет «короткий build-in-public пост» - попадёт в fast lane и не получит co-creation. Нужен override.
- Two paths = two surfaces для багов. Скилл усложняется концептуально (хотя файлы могут быть короче).
- Co-creation lane менее tiражируема - ученик с низким author taste не сможет выбирать в Narrative-разбор-кейса.

### Failure mode

Mis-classification (router отправил complex пост в fast lane → класс v17 fails возвращается) или автор не пользуется co-creation потому что времени нет → degenerate к Architecture A.

---

## 5. Recommendation: Architecture C (Hybrid)

### Обоснование

**Reason 1 - Жанры реально разные по природе.** Lifestyle+brag и Narrative-кейс не должны проходить один pipeline. Первый - момент + цифра, второй - story + insight delivery. Попытка один skill применить ко всем = усреднение качества вниз.

**Reason 2 - 18 итераций показали где predictable, а где judgement.** Fast lane жанры в этой сессии не были основной проблемой. Главные fails (v14-v18) были на build-in-public + paradox-reveal - это co-creation territory. Hybrid разделяет проблемы.

**Reason 3 - Аргумент tiражируемости работает для обоих lanes.** Fast lane - это «обещание готового поста» для daily use case. Co-creation lane - это **учебный режим** который и есть продукт курса. Ученик учится выбирать tuple → выбирать hook → видеть design-memo. Это формирует author taste, а не заменяет его.

**Reason 4 - Минимальная миграция.** Router уже различает 8 типов постов. Просто добавить routing dimension `lane: fast | co-creation`. Существующие workflow files остаются - co-creation lane добавляет 2-3 новых stages (research-summary / tuple-choice / components-options), fast lane = существующий pipeline.

**Reason 5 - Honest about Claude limits.** Architecture A предполагала «Claude может за автора». 18 итераций показали - не может для judgement-heavy жанров. Architecture B предполагала «Claude никогда не может». Это неверно для жанров где judgement minimal. Hybrid признаёт обе границы.

### Anti-recommendation

Не рекомендую Architecture B полностью. Причина: lifestyle+brag и tool-drop посты в co-creation mode = overkill. автор не хочет выбирать tuple для поста про «бахнул сайт за вечер». Это убьёт даже remaining utility.

Не рекомендую Architecture A продолжать. Причина: 18 итераций - это асимптота. Следующие 18 не приведут к стабильному «нажал → готово» для длинных жанров. Rule bloat станет неподдерживаемым.

---

## 6. Migration path

### Phase 1 - Honest classification (1 сессия)

Прогнать последние 30 постов автора через жанровую классификацию. Для каждого:
- Какой из 8 типов
- Сколько author judgement потребовалось (анкеты / surprising choices / insight calls) - score 1-5
- Какой lane: fast / co-creation

Output: validated mapping таблица. Возможно `templates/` файлы переразбиваются.

### Phase 2 - Router upgrade (1 сессия)

В `01-router.md` добавить `lane` field в outline. Mapping table из Phase 1 определяет routing.

В `02-structure.md` после type-detection вставить lane-routing branch.

### Phase 3 - Co-creation pipeline (2-3 сессии)

Новые workflow files:
- `workflow/02b-research-summary.md` - собирает research из Карты / corpus / последних 30 / конкурентов
- `workflow/02c-tuple-choice.md` - выдаёт 3 tuple варианта (genre × value × JTBD), автор выбирает
- `workflow/02d-components-options.md` - выдаёт 3 hook × 3 reveal × 3 close с design-memo
- `workflow/02e-value-injection.md` - 3-5 insight-blocks с verbatim source
- `workflow/02f-polish.md` - автор собрал → skill полирует через существующие 8 hard gates

Существующие `01-finalize.md` / `03-write.md` остаются для fast lane.

### Phase 4 - Fast lane stays as-is

Lifestyle+brag / alarm+reaction / tool-drop / tweet используют существующий pipeline без изменений. Rule bloat там приемлем (predictable жанры).

### Phase 5 - Onboarding update (1 сессия)

`00-onboarding-student.md` объясняет 2 lanes. Ученик понимает: «короткий пост → запустил → получил», «длинный пост с insight → 2-3 минуты выбора».

### Phase 6 - Track-record метрика (continuous)

В `examples/track-record-post.md` добавить колонку `lane` + `iterations_to_publish`. Через 30 постов проверить: fast lane <2 iterations average, co-creation lane <3 iterations average. Если co-creation lane >5 iterations - co-creation не работает, нужен пересмотр.

### Migration cost (rough estimate)

- Phase 1-2: ~3 часа автор + skill (validated mapping + router upgrade)
- Phase 3: ~8 часов (4 новых workflow files + polish stage)
- Phase 5: ~2 часа (onboarding update)
- Total: ~13 часов на полную миграцию
- Backward compat: fast lane работает первый день, co-creation lane вводится постепенно

### Rollback path

Если co-creation lane не приживётся за 30 постов - router переключается на «всё в fast lane», новые workflow files остаются как опциональные через флаг `--co-create`. Никакая работа не выкидывается.

---

## 7. Самопроверка решения

**Pre-mortem 5 причин провала Hybrid:**

1. автор не пользуется co-creation lane потому что лень выбирать → degenerate к A. **Митигация:** track-record метрика lane usage. Если co-creation lane usage < 20% за 30 постов - пересмотр.
2. Mis-classification: build-in-public попадает в fast lane → v17 fails возвращаются. **Митигация:** жёсткий mapping типов в Phase 1, override через флаг `--co-create`.
3. Co-creation lane слишком много текста на output → автор закрывает не дочитав. **Митигация:** компоненты в табличной форме, не abstracts. Каждый компонент ≤4 строки.
4. Ученики курса не понимают что выбирать в co-creation. **Митигация:** onboarding объясняет «у тебя 2 mode - простой и обучающий». Обучающий - это часть продукта курса, не bug.
5. Migration cost 13 часов не окупается. **Митигация:** Phase 1-2 уже даёт value (validated mapping + router). Phase 3 можно делать инкрементально по одному жанру.

**Калибровка уверенности:** 70% что Hybrid лучше чем A или B чистый. 90% что A в текущем виде дальше не работает.

**Multi-perspective:**
- Маркетолог (автор-автор): «нужно чтобы посты выходили, не хочу 18 итераций» → Hybrid OK.
- Инвестор (продукт курса): «нужно тиражируемое решение для учеников» → Hybrid OK (fast lane = tiражируемая часть, co-creation = teaching part).
- Клиент (ученик курса вайбмаркетинга): «нужен инструмент который и обучает и работает» → Hybrid OK.

**Adaptive:** если через 30 постов co-creation lane не используется - переход на pure A с rule freeze (стоп добавлять rules, существующие 95% жанров покрывают). Если fast lane даёт > 30% reject rate - переход на pure B.

---

## 8. Итог

**Recommendation: Architecture C (Hybrid).**

3 жанра остаются в one-shot (lifestyle+brag / alarm+reaction / tool-drop / tweet). 4 жанра переходят на co-creation (narrative-кейс / build-in-public / vulnerability+reveal / sales-launch).

Migration cost ~13 часов, делается инкрементально, fast lane работает с первого дня.

Rollback path сохранён.

Главный сигнал что решение правильное: 18 итераций v1-v18 ВСЕ были на co-creation territory жанрах. Если бы skill сразу запросил автора выбрать tuple + hook variant + insight в этих 4 жанрах - итераций было бы 2-3, не 18.
