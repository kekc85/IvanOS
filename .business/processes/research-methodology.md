# Research Methodology — Industry-grade 12-step

**Назначение:** единая методология выполнения любого research-задания в проекте автор. Применяется ко всем типам: контент-завод (replication viral Reels), конкурентский анализ, market research, architecture decisions, viral pattern extraction, viral hook generation, проверка гипотез.

**Принцип:** 12 шагов выполняются **в порядке**, ни одного не пропуская. Прыжок на шаг 6 минуя 0-5 = бездумные действия → брак результата.

**Validation gates** между шагами 4 / 7 / 9 — обязательны. Финальный repro-test перед сохранением.

---

## Шаг 0 — Research question / Hypothesis

**Что:** Одно предложение в форме вопроса или гипотезы. Формулируется ДО любых действий.

**Примеры:**
- (Replication) «Какие 10 motion-patterns у топ-6 AI-creators применимы для replicate Reels автора в категории вайбкодинг?»
- (Decision) «Какой PMC-стек подойдёт для содержания запуска курса вайбкодинг RU июнь 2026?»
- (Exploratory) «Какие типы lead-магнитов работают в нише AI-инфобизнеса 2026?»
- (Validation) «Гипотеза: PAIPS-формат постов даёт higher engagement чем classical AIDA в TG-канале автора. Проверить.»

**Anti-pattern:** «Просто посмотри что есть у конкурентов» — не research question. Если нет — спросить автора пока не сформулирован.

---

## Шаг 1 — Methodology

**Что:** Тип исследования + глубина.

**4 типа:**

| Тип | Когда | Глубина |
|---|---|---|
| **Replication** | Воспроизводим находки (viral patterns, чужие воронки, чужие лендинги) | MAX (step-by-step, verbatim) |
| **Decision** | Выбираем между альтернативами (стек, цена, инструмент) | SUFFICIENT (сравнение по критериям) |
| **Exploratory** | Mapping landscape (что вообще есть) | BREADTH (широта вместо глубины) |
| **Validation** | Проверка конкретной гипотезы (да/нет) | TARGETED (минимально достаточно для решения) |

**Anti-pattern:** Делать Replication-research как Exploratory — описывать generic, без точных значений. Результат: невоспроизводимо.

---

## Шаг 2 — Strategy

**Что:** Как подходим к поиску данных.

**3 оси выбора:**

| Ось | Варианты | Когда какой |
|---|---|---|
| **Primary vs Secondary** | Сами получаем данные (ingest, опросы, тесты) vs Берём чужое (papers, articles, conversation history) | Primary — для своей ниши, Secondary — для общих стандартов |
| **Authority vs Convenience** | Top-of-field источники (Disney 12, Material, NN/g) vs Что под рукой попалось | Authority всегда предпочтительнее. Convenience маркировать явно как bias |
| **Deductive vs Inductive** | От first principles → predicted patterns → validation vs От observed → labels → rules | Deductive надёжнее (см. [[methodology-audit motion по решению автора]]) |

**Anti-pattern:** Convenience sample выдавать за authority. «Я ингестил 20 creators» = convenience. «Я ингестил top-20 motion studios по industry rankings» = authority.

---

## Шаг 3 — Scope

**Что:** Границы исследования.

**4 компонента:**

- **IN scope:** Что точно ищем (с примерами артефактов). Например: «motion-patterns в hook-сегментах первых 3 секунд Reels от 6 названных creators»
- **OUT of scope:** Что не ищем. Например: «не разбираем paid ads, не разбираем рекламу услуг, не лезем в long-form контент»
- **Time-box / Iteration-box:** Сколько часов или итераций максимум. Например: «2 часа на full pass, дальше escalate to автор»
- **Decision rights:** Что решаю сам (включить/исключить источник, group patterns), что спрашиваю у автора (если >7 patterns или ambiguous classification)

**Anti-pattern:** Scope раздут (нет OUT-списка, нет time-box). Заходит в зону другой задачи. См. для запусков курса.

---

## Шаг 4 — Targets (кого/что ищем)

**Что:** Конкретные сущности + критерии отбора.

**Структура:**

- **Список:** Поимённый список (creators / repos / источников / patterns), не «топ-аккаунты вайбкодинга»
- **Inclusion criteria:** Что включаем (>100K views? authority status? recent activity?)
- **Exclusion criteria:** Что отсеиваем (sponsored content? старше 6 месяцев? off-topic?)
- **Sample design:** Authority (top-N по industry rankings) / Convenience (что доступно) / Random / Systematic (каждый N-й)

**Validation gate после шага 4:** Sample biased? Если authority sample использован — какой ranking источник? Если convenience — указать явно «convenience sample, bias известен».

**Anti-pattern:** Targets без inclusion/exclusion → попадают случайные источники, разваливается коэрентность.

---

## Шаг 5 — Prior work check

**Что:** Что уже сделано до тебя.

**3 проверки:**

1. **`.business/processes/` + `skills/*/references/`** — `ls -la .business/processes/*.md skills/*/references/*.md` — есть ли релевантные research files? Если есть — read, extend, не reinvent.
2. **Memory** — `grep -i "<keyword>" memory/MEMORY.md` — есть ли relevant memories?
3. **Industry publications** — WebSearch на «<topic> framework site:medium.com OR site:scholar.google.com» — published industry standards?

**Anti-pattern:** Пропустить → повторно собирать то что уже есть. Жгёшь время и токены автора. Прецедент: motion catalog re-built несколько раз без проверки прошлых versions.

---

## Шаг 6 — Methods

**Что:** Конкретные инструменты + sequence + параллелизм.

**Инструменты:**

- **WebFetch / WebSearch** — для published material
- **ingest-reel** — для viral video content (контент-завод)
- **Agent Explore** — для codebase + большой ресёрч в проекте
- **grep / Read** — для локальных файлов
- **parallel Agent batch** — для N независимых независимых запросов одновременно
- **WebFetch + Playwright** — для динамических страниц

**Sequence:** Если есть зависимости (output одного = input другого) — sequential. Иначе — parallel batch.

**Anti-pattern:** Sequential execution когда возможен parallel. Жгутся часы и токены без пользы.

---

## Шаг 7 — Pilot test

**Что:** Прогнать pipeline на 1-2 примерах перед full-scale.

**Зачем:** Если на пилоте брак — корректируем methods/scope, не тратим часы на полноценный run.

**Чек-лист пилота:**
- Targets дают релевантные данные (не off-topic)?
- Format захвата работает (структура читаема, repro возможен)?
- Synthesis даёт meaningful patterns (не trivial)?

**Validation gate после шага 7:** Pilot прошёл? Если нет — вернуться на шаг 2/3/6 для корректировки.

**Anti-pattern:** Пропустить пилот → full-scale брак в конце, всё переделывать.

---

## Шаг 8 — Data capture standard

**Что:** Как фиксируем найденное.

**2 grade:**

### Repro-grade (Replication-research)

Достаточная детализация чтобы junior воссоздал без оригинала:

- **Точные значения:** timestamps, размеры в px, цвета HEX, шрифты с весом, тайминги в ms, тексты verbatim
- **Структура:** кадровый план, последовательность блоков, order операций
- **Контекст применения:** когда срабатывает, на каком этапе, при какой нагрузке
- **Verbatim quotes** для замены/адаптации

**Tест:** «Может ли junior воссоздать это только по моей записи без доступа к оригиналу?» Если нет — research не закончен.

### Summary-grade (Decision/Exploratory)

Достаточный summary для принятия решения:
- Comparison tables по критериям
- Pro/cons
- Recommendation

**Anti-pattern:** Generic описания («использует яркий цвет», «динамичный монтаж», «активный hook») в repro-grade. Это уровень exploratory, не replication.

---

## Шаг 9 — Synthesis

**Что:** Обработка raw findings.

**3 операции:**

1. **Группировка по systemic patterns** — не flat list. Pattern считается systemic если cross-refs ≥3 источников.
2. **Cross-checks между источниками** — расхождения подсветить
3. **Anti-patterns** — что НЕ работает / не применимо. Равно ценно как positive findings.

**Validation gate после шага 9:** Каждый pattern имеет authority cross-reference? Минимум 3 источника подтверждают?

**Anti-pattern:** Flat list patterns без grouping. Anti-patterns не зафиксированы (потом повторяем те же ошибки).

---

## Шаг 10 — Output

**Что:** Конечный артефакт.

**3 требования:**

- **Artefact-deliverable** — конкретный файл (`.business/research/<topic>-research.md`), не «summary в чат». Чтобы вернуться через месяц
- **Decision-ready** — автор должен понимать что решать на основе результата. «Вот N patterns, рекомендую T1/T2 — твоё решение»
- **Next steps** — что follow-up действия (например: contribute-catalog 3 patterns в HF blocks, ingest ещё N creators для validation, etc)

**Anti-pattern:** Output без decision-readiness — автор должен сам перечитывать чтобы понять что решать. Время автора потерял.

---

## Шаг 11 — Validation (continuous + final)

**Что:** Контроль качества.

**Continuous mini-gates** (уже встроены в шаги 4 / 7 / 9):
- После Targets: sample bias check
- После Pilot: pipeline working check
- После Synthesis: authority cross-references check

**Final validation перед сохранением:**

1. **3 слоя проверки** (см. шапку `CLAUDE.md`): валидаторы / 4 концепции / 7 контуров
2. **Repro-test:** «Junior воссоздаст без оригинала?» (только для Repro-grade)
3. **Authority cross-check:** Минимум 2 authority sources подтверждают ключевые claims
4. **Self-check checklist:** Все 12 шагов выполнены явно? Нет skip?

**Anti-pattern:** Validation только в финале → находишь bias/брак когда уже поздно. Continuous gates обязательны.

---

## Применение к типичным задачам автор

### Контент-завод (replication viral Reels)
Тип: **Replication, MAX-глубина**. Targets: 6 named creators. Capture: Repro-grade. Output: `creators-effects-research.md` + HF blocks contribute. Pilot: 1 creator × 1 reel.

### Конкурентский анализ для запуска курса
Тип: **Decision, SUFFICIENT**. Targets: 5-7 RU курсов по нейросетям + 3 EN. Capture: Summary-grade comparison. Output: `competitors.md` обновление.

### Market research для new SaaS niche
Тип: **Exploratory, BREADTH**. Sample design: top-3 в каждой sub-niche. Output: short-list для validation.

### Validation гипотезы по контент-форматам
Тип: **Validation, TARGETED**. Minimal sample достаточно для да/нет. Output: decision recommendation.

---

## Связь с другими процессами

- **Strategy перед tactics** — research = частный случай strategy-first. Шаг 0+1 выполняют strategy-paragraph.
- **Phase scope check** — Scope в шаге 3 = тот же что в фазах запуска курса.
- **Align before save** — Output шага 10 согласовать с автором до Write.
- **3 слоя проверки** (`CLAUDE.md`) — встроены в шаг 11.
- **Parallel agents** — в шаге 6 для N independent queries.

---

*Документ — single source of truth для research methodology в проекте. Обновляется через self-improvement routine когда находятся новые failure patterns.*

---

## 5 углов ресёрч для валидации идеи/продукта (тренинг Миллера, День 2)

При продумывании нового продукта/фичи (Фаза 0 `idea/`) запускать research по 5 параллельным углам + 6-й синтезатор.
Главная цель — **«найти что forkнуть из open source, не делать с нуля»** (кейс Миллера: нашёл LiveKit вместо платного Телемоста).

1. **LinkedIn-основатели/эксперты ниши** — как решают задачу профессионалы.
2. **Соцсети** (X / Reddit / YouTube / тематические каналы) — реальные боли и хаки пользователей.
3. **Web / готовые SaaS** — кто уже делает, цены, фичи, чего не хватает.
4. **YC / акселераторы** — какие стартапы в теме, их подход.
5. **Open source для форка** — что взять готовым кодом.
6. **Синтез** (отдельный агент): таблица аналогов · методологии (agent loops / ReAct / OODA / multi-agent) · что украсть · чего избегать · наша дельта.

Не путать с полноценным `resyorch-nishi` harness — это лёгкий фронт для ранней валидации идеи.
