# Workflow 03 - Write (v2.2)

**Назначение:** tuple selection → value-vector lock → draft → voice → living language → sentence-pattern cross-check → hook calibration → reality check
**Входы:** outline из stage 02 (`workflow/02-structure.md`) или co-creation lane (`workflow/02b-02f-*.md`)
**Выходы:** финальный draft (subject to stage 04 review)
**Следующая стадия:** `workflow/04-review.md`

**Pass order:** 0.0 (КАНОН blueprint) → 0 → 0.45 (Mastery) → 0.5 → 0.7 → 0.6 → 1 → 2 → 2.5 → 2.7 → 3 → 4 → 5

**Project-aware (NEW, репликуемость):** пути голоса/JTBD/контента ниже = дефолт для `project=default`. При `--project <name>` читать `{active.*}` из `workflow/00-project-context.md` (напр. health → `post-pack/voice-canon.md` вместо ivan-voice, `post-pack/gold-standard.md`, `post-pack/jtbd-value-map.md`). Voice Fidelity Gate 4.6 сверяет с `{active.voice.canon}` + `{active.voice.gold_standard}`. Если `{active.content_model}=evergreen` — пропустить Pass 0.4 RESOLVE Карты/формулировок (нет запуска) и читать `{active.content_source}`.

**Mandatory reference reads:** _(дефолт project=default; иначе `{active.*}`)_
- **`references/_voice-TEMPLATE.md` — КАНОН поста (Pass 0.0, HARD — структура + блюпринт заголовков + блюпринт контекста + ценность + line-правило + чек-листы; без него Blueprint Gate 4.B failит)**
- **`references/criteria-library.md` — СЕМАНТИКА критериев (Pass 0.0, HARD для мягких критериев). Что КАЖДЫЙ критерий значит ПО СОДЕРЖАНИЮ + под-критерии + ✅/❌ примеры + метод проверки. Минимум прочитать группу «🔴 Мягкие критерии» (мощная идея / триггерность / нелинейная драматургия / 3 оси ценности / интрига / динамика / эмоция / твист) + карточки критериев, релевантных этому посту. Строить пост так, чтобы критерии имели СОДЕРЖАНИЕ, а не форму. Проверяется Gate 4.B.8.**
- `examples/_TEMPLATE.md` → `{active.voice.gold_standard}` (Pass 0.1)
- `references/_voice-TEMPLATE.md` → `{active.voice.canon}` (Pass 0.2, Pass 2.1)
- `references/_voice-TEMPLATE.md` → `{active.voice.living_language}` (Pass 0.2.1, Pass 2.5)
- `config.md` (Pass 0.3)
- **RESOLVE: `config.content_plan` (ячейка дня) → `config.content_map` 5.2 (тело кодов) + `config.formulations_bank` 5.0 (Pass 0.4, NEW 2026-05-31, HARD — прецедент слабого поста по решению автора)**
- `~/.business/products/sticky-offers.md` (Pass 0.35, NEW 2026-05-28 — sticky source-of-truth по продуктам/ценам/дисклеймерам, если файл существует и subject=ivan)
- `references/genre-value-jtbd-mapping.md` (Pass 0.5, NEW v2.2)
- `references/value-types-framework.md` (Pass 0.7, NEW v2.2)
- `references/atomic-essay-structure.md` (Pass 1.2)
- `references/corpus-pattern-index.md` (Pass 2.7, NEW v2.2)
- `references/hooks-15-templates.md` (Pass 3.1)
- **`mastery/copywriting/INDEX.md` + файлы выбранных авторов (Pass 0.45, NEW 2026-05-31, HARD — линза мастеров копирайтинга по `mastery/PROTOCOL.md`)**
- 💰 **`references/launch-money-layer.md` + `references/launch-warmup-devices.md` + `templates/sales-launch.md` (Pass 0.8, NEW v5.0 — ТОЛЬКО при `brief.launch_window=true`, HARD: тело пишется под боевую карточку `brief.money_card`, без неё Sales Gate 4.S failит). Для прогрев-поста-демонстрации (показ инструмента/результата) тело строится по комплекту приёмов `launch-warmup-devices.md`: заёмный авторитет/newsjack (Приём A) · стек автономности «сам/бесплатно/без рук» (C) · пруф+гандикап (D) · перевод в деньги читателя (B) · reveal механизма (E) · оффер отдаёт показанное (F). Проверяется Sales Gate 4.S.7.**
- `references/post-performance-log.md` (создаётся при первом логе; Pass 0.85, NEW v5.0 — петля метрик: если в журнале ≥3 строк с реальными цифрами, выписать топ-3/анти-3 паттерна по кликам/регам и учесть в построении; пустой журнал → пропустить молча, НЕ блокирует)

---

## Pass 0 - Mandatory Reads (HARD requirement)

Перед draft ОБЯЗАТЕЛЬНО выполнить Read'ы ниже. Без них review-стадии 4.B (Blueprint Gate) и 4.6 (Voice Fidelity) сразу failят. Введено после прецедентов по решению автора (generic без gold-standard) и по решению автора (КАНОН blueprint лежал мёртвым грузом, не читался конвейером).

### 0.0 - Read КАНОН (_voice-TEMPLATE.md) — HARD, ПЕРВЫМ

`Read(references/_voice-TEMPLATE.md)` (или `{active.voice.blueprint}` для других subject). Это ЯДРО. Загрузить и держать до конца write:
- **Раздел 1** — структура поста (тема / смысл / 5 частей)
- **Раздел 2** — блюпринт заголовков (~50 формул) — заголовок строится ТОЛЬКО отсюда (02-structure Шаг 6)
- **Раздел 3** — блюпринт контекста (7 типов захода) — контекст строится ТОЛЬКО отсюда (02-structure Шаг 5)
- **Раздел 4-5** — примеры/истории (60-70%) + ценность (24ч / «500₽»)
- **Раздел 7** — line-правило (vs последние 5 постов)
- **Разделы 8-10 + 13** — чек-листы + final gate

Переменные блюпринта заголовков (боль / желание / страх / портрет / враг) — из распаковки (`config.paths.avatar` + `objections`), НЕ выдумывать (раздел 0 канона).

🔴 **ЗАГОЛОВОК ПРИ ОБЪЯВЛЕННОЙ ЦЕЛИ ФОРМЫ (NEW, перекрывает «заголовок ТОЛЬКО по формуле блюпринта»).** `_voice-TEMPLATE.md` и Blueprint Gate 4.B стоят на **уровне 7** иерархии §8.1 канона формы, то есть ниже канона (уровень 5). Поэтому:
- `brief.form_goal` **заполнен** → хук строится по профилю канона (ветвление ТОЛЬКО по слову-цели, буква - не значение): **`reactions`** кадр (эпизод с временем, местом, бытовой деталью) или назывной ярлык 1-4 слова; **`forwards`** опись-анонс с цифрой и иконкой носителя первым символом; **`sales`** назывной ярлык или квитанция о случившемся факте; **`gate`** тело гейта. `formula_id` из раздела 2 блюпринта становится **опциональным полем** (записывается, если формула реально подошла), а не условием PASS гейта 4.B.1
- `brief.form_goal` **пуст** → это не ветка работы, а возврат: STOP и в `01-router.md` Шаг 0.49 за целью. Норма «заголовок ТОЛЬКО по формуле блюпринта, `formula_id` обязателен» остаётся плоским дефолтом уровня 7 и применяется после возврата - там, где профиль объявленной цели по заголовку молчит
- В обеих ветках остаются в силе: переменные из распаковки (не выдумывать), правило первой строки ≤10 слов RU (Pass 3.3), запрет метафоры-подмены

Если Read пропущен → STOP, draft запрещён, Blueprint Gate 4.B сразу FAIL.

### 0.1 - Read gold-standard examples

`Read(examples/_TEMPLATE.md)` (или соответствующий файл из `config.paths.voice_reference` для других subject).

Из mapping table выбрать 2-3 поста matching текущему `outline.type`. Прочитать verbatim первые абзацы + specific tricks. Это **few-shot context** для voice injection.

### 0.2 - Read voice profile

`Read(references/_voice-TEMPLATE.md)`. Загрузить:
- 16+ канонических терминов (must apply ≥2 для long, ≥1 для short)
- 5 главных приёмов (must apply ≥1 для short, ≥2 для long)
- 11 анти-паттернов (must avoid all)
- Tone of voice (ТЫ-форма, конкретные числа, brail-spacers, emoji-маркеры)

### 0.2.1 - Read living language (живые глаголы и обороты)

`Read(references/_voice-TEMPLATE.md)`. Загрузить:
- Раздел 1 - живые глаголы (допилил / прогнал / прокинул / бахнул / выкатил / etc.) - must apply ≥3 для long, ≥2 для short
- Раздел 2 - живые обороты («по зарубежке» / «прямо сейчас» / «у ребят» / etc.) - must apply ≥2
- Раздел 3 - запрещённые AI-обороты - must be 0 в выходе
- Раздел 4 - структурные паттерны живых постов

Без этого Read'а Sub-stage 4.7 (Living Language Gate) failит. Введено по решению автора после прецедента, когда пост с правильными терминами звучал роботизированно из-за formal глаголов («адаптирую», «настраиваю», «применяю»).

### 0.2.2 - Read канон формы под цель v2 (HARD для platform=telegram)

🔴 **ОБЯЗАТЕЛЬНЫЙ ВХОД (заменил v1 донор-канона):**

`Read(.business/voice-corpus/_format-canon-v2.md)` - канон **формы под цель** (296 постов чистого корпуса, окно 12 мес). Загрузить:
- §2 главное правило «цель выбирается ДО написания» + §2.1 дерево решений режима (выход дерева - СЛОВО: `reactions` реакции · `forwards` репосты · `sales` продажа · `gate` реакция-гейт; буквы улики R / F / S / A - только для печати человеку)
- §3 три профиля формы с числами (длина, строки, воздух, жирный, хук, списки, ссылки, финал) - пороги гейтов берутся ОТСЮДА, а не из плоских дефолтов скилла
- §4 кластеры приёмов с механизмами (хук кадр против витрины, вторая строка, архитектура, финал, разметка, тема)
- §5 тема выбирает метрику: пост не оценивается чужой метрикой
- §6 анти-паттерны по режимам · §8.1 иерархия источников · §9 чек-лист приёмки по режимам

**Профиль в работу:** брать `brief.form_profile`, записанный роутером (01-router Шаг 0.49) по дереву §2.1. Профиль пуст → см. fallback ниже.

**🔴 Приоритет при конфликте - трёхзвенный (заменил попарный «голос > донор»):**
1. **голос владельца** (`0.2` + корпус `A-telegram/`) - лексика, интонация, табу. Побеждает всегда
2. **канон формы v2** (`_format-canon-v2.md`, уровень 5 иерархии §8.1) - длина, архитектура, разметка, хук, финал, CTA-механики
3. **донор-канон v1** (`.business/voice-corpus/_donor-format-canon.md`) - **FALLBACK, отменён как источник норм.** Читается и применяется ТОЛЬКО там, где v2 молчит (наблюдения слоя «приёмы подачи»: скобка `))` вместо смайла, регистр начала строки, мат на пике эмоции, монтажная склейка, персонажи-иллюстрации). Эти наблюдения в v2 не измерялись, поэтому они гипотезы низкого ранга и не могут быть основанием гейта. Числовые нормы v1 (длина 500-1700, «жирный почти всегда», медиана 5-6 слов, скелет из 7 позиций, чек-лист 7 пунктов гейта 4.0.4) остаются в тех же значениях, но применяются **только там, где профиль объявленной цели §3 канона молчит**. Прежней ветки «`brief.form_goal` пуст → конвейер ведёт себя ровно как до внедрения канона v2» НЕТ: пустая цель - не режим работы, а возврат в `01-router.md` Шаг 0.49 за целью

Донор даёт форму, не лексику. Перенос сигнатур доноров («всем денег», «ПыСы», «Ладненько», их цифры и кейсы) - брак, гейт 4.0.4 такой пост валит (правило действует в обеих ветках).

**Медиана слов в предложении - пол, а не только потолок (NEW):** при цели R-разбор (класс C) медиана не ниже **5** при цели 5.5 (держат 11/12 верха), доля отрезков до 3 слов не выше 0.20 (WARN). В R-нарративе (класс B) признак **не различает** (6 против 6), нижней границы нет. Верхняя граница ритма из v1 сохраняется без изменений.

Для `platform=linkedin` читать по желанию и брать только слой В (ритм и абзацы) - механики реакций и типографика TG туда не переносятся.

### 0.3 - Read config

`Read(config.md)`. Подтвердить:
- `subject.content_factory_definition` - что значит «контент-завод» в данном проекте (для автора = рилсы, не TG-посты)
- `lexicon_banned_hard` - список auto-fail терминов
- `voice.archetypes_allowed` / `archetypes_banned`

### 0.4 - RESOLVE: коды смысла ячейки → ТЕЛО 5.2 + формулировки 5.0 (HARD, NEW 2026-05-31)

> **Прецедент:** слабый пост по решению автора (3/5). Корень — связка: ячейка контент-плана = голый код-указатель (`#1 Pattern A`, `2.1`, `3.5e`), а богатое тело смысла лежит в 5.2 (дословные цитаты ЦА, симптомы, сцены, COI-цифры) и **до поста не доезжало**. Скилл писал на абстракции + лендинг-копии из банка → generic.

Перед draft в Mode A (Plan) ОБЯЗАТЕЛЬНО:

1. `Read(config.content_plan)` — найти ячейку нужного дня/канала, выписать ВСЕ коды смысла + механику + CTA.
2. Для КАЖДОГО кода `Read(config.content_map)` (5.2) соответствующий entry и забрать **дословное сырьё**: цитаты ЦА (q7/q9), симптомы (язык эксперта), живые сцены, COI-цифры. Это и есть материал поста.
3. Если код = формулировка (#1-#8) — `Read(config.formulations_bank)` (5.0), взять каноничную формулировку. Проверить статус: `[АПРУВ 2×+]` = канон дословно; `[АПРУВ 1×]` = можно, пометить «валидация».
4. **Дословный перенос (правило банка 6.1), НЕ пересказ.** Банк/5.2 = СЕМЯ и сырьё, не скелет: пост строится на живой цитате ЦА + личном/live якоре («личный момент → метод», gold-standard приём №1), а не на абстрактном reframe.

Улика в чат: `resolve: <код> → <дословная цитата/сцена, что взял из 5.2/5.0>` по каждому коду. Без resolve-улик — draft запрещён.

**Если хоть один Read пропущен (включая 0.4 resolve) - STOP, не делать draft. Сначала прочитать.**

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`. Обязательные входы включают **`_voice-TEMPLATE.md` (КАНОН, Pass 0.0)** — улика: какую формулу заголовка (№), какой тип контекста (1 из 7), какую структуру тела (60/30) взял.

🔴 **ОБЯЗАТЕЛЬНАЯ СТРОКА-УЛИКА ПО КАНОНУ ФОРМЫ (NEW, HARD):** к списку улик добавляется строка ровно такого вида:

```
форма: цель=<reactions/forwards/sales/gate> (<R/F/S/A>) класс=<narrative/razbor/sales/gate> тема=<...> -> длина <min-max>, жирный <N>, перечислений <N>, ссылок <N>, цифра в хуке <да/нет>
```

- Строки нет → **output запрещён** (чтение без применения = ложная улика, §0 канона запрещает выводить «применён канон формы» без факта подключения)
- Значение цели в улике - всегда СЛОВО (`reactions | forwards | sales | gate`), буква в скобках берётся из `brief.form_goal_letter` и служит только печатью человеку. Формат строки совпадает с тем, что проверяет под-гейт **4.0.2b «Гейт 0»** в `04-review.md`
- `brief.form_goal` пуст → **STOP и возврат в `01-router.md` Шаг 0.49**: прогнать дерево §2.1, записать `form_goal`/`form_class`/`form_profile`, напечатать строку-улику. Ветки «роутер недоступен → работаем на плоских дефолтах скилла и донор-каноне v1» здесь НЕТ: роутер - файл того же скилла (`~/.claude/skills/post/workflow/01-router.md`), его недоступность физически невозможна, а прежняя формулировка снимала блокирующий гейт одной фразой. Плоские пороги ниже читаются в старых значениях только ПОСЛЕ возврата из роутера, там где профиль объявленной цели молчит
- Проверяется в 04-review под-гейтом **4.0.2 Гейт 0** (HARD, BLOCKING)

- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.


---

## Pass 0.45 - Mastery: линза мастеров копирайтинга (NEW 2026-05-31, HARD)

> **Зачем:** пост пишется не «как умею», а через методы признанных мастеров копирайтинга (`mastery/copywriting/`). Регламент — `mastery/PROTOCOL.md`. Защита от частичного/фиктивного применения: Inventory ВСЕХ → Select с обоснованием → Apply → (Evidence+верификатор в 04-review). Память `feedback_mastery_real_application_with_verification`.

### Шаг 1 - Inventory ВСЕХ авторов (HARD)
`Read(mastery/copywriting/INDEX.md)`. Выписать в чат **каждого** из 12 авторов + его методы (Огилви / Шугерман / Кэплз / Халберт / Шварц / Хопкинс / Кольер / Бенсивенга / Кеннеди / Райс-Траут / Бёрд / Шваб). Молча пропустить автора нельзя — это вход-гейт.

### Шаг 2 - Select с обоснованием (apply/skip по каждому)
По каждому автору/методу пометка `применяю / не применяю + одной строкой почему` относительно ЭТОГО поста (его жанр, JTBD, платформа). «Рассмотреть всех» ≠ «впихнуть всех»: метод, не служащий задаче, осознанно отсекается с причиной, не игнорируется. Минимум для поста: заголовок/хук (Огилви/Кэплз/Шваб) + удержание (Шугерман/Кольер) + доказательность где есть оффер (Хопкинс/Бенсивенга). Прочитать файлы выбранных авторов для точных шагов метода.

**🔴 Ильяхов — MUST-HAVE, вне select-выборки (нельзя пометить «не применяю»).** Информационный стиль применяется ВСЕГДА финальным проходом на RU-тексте: факт вместо оценки · чистка стоп-слов («просто/очень/реально/на самом деле») · схлоп синонимов-дублей · оценочные прилагательные → действие/цифра. Это не один из 13 на выбор — это обязательный фильтр поверх любого поста. Скип = нарушение PROTOCOL.

### Шаг 3 - Bind to draft
Каждый выбранный метод привязать к конкретному блоку поста (hook / story / offer) — применять по алгоритму из файла автора, не для галочки. Привязку держать для Evidence Report в 04-review.

**Вход-гейт:** нет полного inventory 12 авторов с пометками apply/skip → draft запрещён. Идемпотентно: уже прочитано в этой сессии → пометить `(reuse)`.

**Правило пруфа (NEW, пилот 2026-05-31):** методы, которым нужен факт — Хопкинс (reason-why) / Бенсивенга (пруф) / Огилви (конкретика) — обязаны тянуть **конкретный факт** из `config.story_bank` или `config.content_map` (реальная цифра, дословный вопрос аудитории, сцена). Нет факта в источниках → пометить `proof-gap: <метод>` и НЕ выдавать мягкий пруф «за вечер узнал больше» без опоры. Пилот показал: оба независимых прохода (верификатор + humaniser) ловят именно отсутствие конкретного факта.

---

## Pass 0.48 - POWER IDEA GATE (HARD, вход, NEW 2026-06-02)

> **Прецедент E2E по решению автора:** взял generic-идею «просмотры ≠ деньги, собери продукт» — её говорит ВСЯ ниша. Verifier зарубил 6/7 семантики: на generic-идее невозможна ни нелинейная драматургия (скатывается в линейный PAS «стена боли → стена решения»), ни триггерность, ни дефицит. Корень: слабая controlling idea НЕ даёт материала для качелей. Чинить НА ВХОДЕ, до написания тела.

ДО Pass 1 (написание тела) ОБЯЗАТЕЛЬНО:
1. `Read` отстроенный угол: `config.content_map` (5.2 - в ней же живёт БЛОК пар X→Y: «применение vs профессия», «100 правильных > 10К», «одна система вместо зоопарка» и т.д.). ⛔ Отдельного файла `3-Уникальный-механизм.md` в папке активного запуска НЕТ (проверено) - Read по нему падает посреди Pass 0.45; пары берутся из 5.2. Плюс для запуска ОБЯЗАТЕЛЬНА полная клетка дня `.business/запуски/<active-launch>/_rebuild-v4/day-NN-DDMM.md` - в ней угол, фактура с якорями, анти-чеклист и CTA конкретного носителя. Идея берётся ОТСЮДА, не из общего понимания темы.
2. Сформулировать **controlling-тезис одной строкой** в формате «ценность + причина» (Макки) — что финал доказывает и за счёт чего.
3. **ТЕСТ КОНКУРЕНТА (HARD):** «подписал бы этот тезис Палий / Замесин / Skillbox без вранья?» Да → **generic → STOP, не писать.** Вернуться к шагу 1, взять отстроенный угол из УМ (тот, что РЕЖЕТСЯ с дефолтом ниши). Идея проходит ТОЛЬКО если стоит против конкретного X ниши (назвать X).
4. Улика в чат: `power-idea: <controlling-тезис> | против X ниши: <конкретный дефолт> | источник: <УМ-пара/5.2>`. Без улики — draft запрещён.

Generic-идея на входе = гарантированный линейный PAS на выходе. Этот гейт отсекает её ДО траты цикла. Проверяется постфактум семантикой 4.B.8 + verifier 4.M.2.

---

## Pass 0.5 - Mandatory Tuple Selection: genre × value × JTBD (v2.2 EXPANDED, MANDATORY)

> **Прецедент по решению автора:** 22/22 robotic constructions из v3.1 audit пропустилось всеми gates потому что AI воспроизводил **жанр-template** на уровне всего поста. Текст звучал «нормально» fragment-by-fragment, но в целом был predictable AI-template. Введён mandatory genre selection BEFORE write.
>
> **v2.2 expansion (Fix 4):** Genre selection недостаточен - post может быть «правильного жанра» но без value для читателя и без JTBD-fit. Перешли с simple genre selection на **tuple selection (genre × value × JTBD)** с матрицей совместимости и hard-abort на invalid combinations.

BEFORE write - обязательно выбрать ОДНУ tuple `(genre, value_vector, target_JTBD)` и cross-check через matrix. Зафиксировать выбор явно.

### Шаг 1 - Read mapping matrix

`Read(references/genre-value-jtbd-mapping.md)`. Загрузить:
- Матрицу совместимости 5 жанров × 6 value vectors × 7 JTBD
- FIT classification per cell: **natural** (рекомендовано) / **forced** (требует усилия) / **invalid** (hard abort)
- Hard-abort combinations list

### Шаг 2 - Select genre (5 автор-жанров)

Выбрать ОДИН из 5 (из `references/_voice-TEMPLATE.md` v2.0 §4.2):

1. **G1 - Narrative-разбор-кейса**
   - Story первого/второго лица + конкретное имя+возраст+ниша героя
   - Нумерованные шаги - это narrative («сначала прокинул, потом допилил»), НЕ tutorial («Шаг 1: X. Шаг 2: Y»)
   - Verbatim Ivan-template: post 2271 (<имя ученика>, <возраст>, <профессия>)

2. **G2 - Vulnerability + reveal**
   - Paradox-история. «Раньше я думал X. Оказалось Y»
   - Без полного resolve - оставить нерешённое
   - Verbatim Ivan-template: post 2096 (personal-crisis)

3. **G3 - Alarm + reaction**
   - Crisis news + автор конкретное действие (НЕ generic advice readers)
   - «По всему миру сносят аккаунты. Я прямо сейчас допиливаю фермы»
   - Verbatim Ivan-template: post 2289 (бан-rant)

4. **G4 - Lifestyle + brag с конкретной цифрой**
   - Момент-сцена + одна цифра ($100K в мес / 25 тыс подписчиков)
   - БЕЗ third-act manifesto («новый образ жизни в 2026»)
   - Verbatim Ivan-template: post 2186 (1250 chars, простой формат)

5. **G5 - Build-in-public с paradox-hook**
   - «Допилил X - оказалось Y» с неожиданным поворотом
   - НЕ предсказуемый roadmap «допилил → описание → прогнал → метрика → roadmap»
   - Verbatim Ivan-template: post 2231 (build-in-public, 1591 chars)

### Шаг 3 - Select value_vector (V1-V6)

Выбрать primary value vector из `references/value-types-framework.md` (детали в Pass 0.7):
- **V1** - Insight / новая мысль читателя
- **V2** - Warning / предупреждение об угрозе
- **V3** - Permission / снятие блока «нельзя / не для меня»
- **V4** - Identity validation / зеркало «я такой же / могу так же»
- **V5** - Tactical how-to / actionable приём
- **V6** - Vulnerability bond / эмоциональная близость

### Шаг 4 - Select target_JTBD (J1-J7)

Выбрать ОДНУ job-to-be-done из стандартного списка читателя автора:
- **J1** - Понять что в мире меняется (orientation)
- **J2** - Поверить что мне можно/я могу (permission)
- **J3** - Получить конкретный приём для use cегодня (tactical)
- **J4** - Получить подтверждение что я не один (belonging)
- **J5** - Получить мотивацию двигаться дальше (energy)
- **J6** - Понять кто автор и стоит ли ему верить (trust-build)
- **J7** - Подумать о решении купить продукт автора (conversion-prep)

### Шаг 5 - Cross-check tuple через matrix

Открыть `references/genre-value-jtbd-mapping.md`. Найти ячейку `(selected_genre, selected_value, selected_jtbd)`. Прочитать FIT:

- **natural** → PASS, продолжать
- **forced** → WARNING, переоценить (либо менять одну координату, либо принять с явным обоснованием в outline)
- **invalid** → **HARD ABORT**, обязательно сменить координату

### Hard-abort combinations (genre × value)

Эти tuples invalid by design - даже если formal logic кажется ок, эмпирически provoking AI-template:

- **G1 × V2** (narrative-кейс × warning) - кейс становится fear-mongering
- **G2 × V2** (vulnerability × warning) - двойной негатив, читатель закрывает
- **G2 × V5** (vulnerability × tactical) - приём убивает emotional opening
- **G3 × V4** (alarm × identity-validation) - кризис не место для зеркала
- **G4 × V2** (lifestyle × warning) - брэг + угроза = bipolar
- **G4 × V5** (lifestyle × tactical) - брэг + how-to = humble-brag tutorial (AI-default)

Если выбранная tuple ∈ hard-abort list → re-select.

### HARD ABORT condition (genre-level)

Если draft НЕ влезает ни в один из 5 → **HARD ABORT** → re-select genre.

Если genre = **Tutorial** («N шагов + M ошибок» / «Сейчас разберу что я называю X» / «Топ-3 ошибки» / numbered steps as scaffolding) → **HARD ABORT**. Tutorial = AI-default жанр, автор НЕ структурирует кейсы через нумерованные шаги в TG-post.

### Output

Записать в memory:
```
outline.genre = "G1 narrative-кейс" | "G2 vulnerability+reveal" | "G3 alarm+reaction" | "G4 lifestyle+brag" | "G5 build-in-public+paradox"
outline.value_vector = "V1 insight" | "V2 warning" | "V3 permission" | "V4 identity-validation" | "V5 tactical" | "V6 vulnerability-bond"
outline.jtbd_target = "J1 orientation" | "J2 permission" | "J3 tactical" | "J4 belonging" | "J5 energy" | "J6 trust-build" | "J7 conversion-prep"
outline.tuple_fit = "natural" | "forced"
```

В review-стадии 4.8.6 происходит final check - если detected tutorial pattern, return ENTIRE post в Pass 0.5 для re-selection.

---

## Pass 0.7 - Mandatory Value-Vector Selection (NEW v2.2)

> **Прецедент по решению автора (Fix 3):** даже после tuple selection в Pass 0.5 драфты выходили value-less - primary vector выбран, но в тексте не реализован. Введён explicit second pass с per-genre mapping + hard requirement что mandatory value extractable из real fact.

### Шаг 1 - Read value framework

`Read(references/value-types-framework.md)`. Загрузить:
- 6 value vectors (V1-V6) с definitions, examples, anti-patterns
- Markers per vector (как detectable в тексте)
- Combination rules (compatible / incompatible)

### Шаг 2 - Apply per-genre mapping

Per `outline.genre` определить **mandatory** value + **optional** secondary:

| Genre | Mandatory value | Optional secondary (выбрать 1) |
|---|---|---|
| **G1 narrative-кейс** | **V4** identity-validation | V1 insight / V2 warning / V5 tactical |
| **G2 vulnerability+reveal** | **V1** insight ИЛИ **V6** vulnerability-bond | V3 permission / V5 tactical |
| **G3 alarm+reaction** | **V2** warning | V1 insight / V4 identity-validation / V6 vulnerability-bond |
| **G4 lifestyle+brag** | **V4** identity-validation | V1 insight / V5 tactical |
| **G5 build-in-public+paradox** | **V3** permission (verified Fix 4 via gold-standard post 4 - counter-intuitive, НЕ V1+V2) | V1 insight / V2 warning / V4 identity-validation / V5 tactical |

### Шаг 3 - Verify mandatory value extractable из real fact

Hard requirement: mandatory value vector ДОЛЖЕН быть извлекаем из реального факта автора / героя кейса / события.

- **V1 insight** → нужна реальная свежая мысль/наблюдение (не perevod common knowledge)
- **V2 warning** → нужна реальная угроза с verifiable trigger (бан, изменение алгоритма, кризис)
- **V3 permission** → нужно реальное «нельзя» которое автор снял своим опытом
- **V4 identity-validation** → нужно реальное «я такой же» зеркало
- **V5 tactical** → нужен реальный applicable приём, не abstraction
- **V6 vulnerability-bond** → нужно реальное эмоциональное переживание

### Шаг 4 - HARD ABORT condition

Если mandatory value НЕ извлекаем из real fact → **HARD ABORT**:
- Либо return в Pass 0.5 → сменить genre (которому подойдёт другой mandatory)
- Либо STOP draft → request real fact от автора (не выдумывать)

**НЕ выдумывать факты** ради заполнения value vector. Лучше abort чем sintetic post.

### Шаг 5 - Update outline

Записать в memory:
```
outline.value_vectors = [<mandatory>, <secondary>]
outline.value_mandatory_fact = "<verbatim real fact, на котором держится mandatory vector>"
```

`outline.value_mandatory_fact` будет проверяться в Pass 2.7 и review-стадии 4 - если в draft этот факт не озвучен, FAIL.

---

## Шаг 0.6 - Load outline

Загрузить из памяти:
```
outline.headline {formula_id, text, vars_source}   # Шаг 6 — по блюпринту заголовков (КАНОН раздел 2)
outline.context_plan {type, text}                  # 5.1 — 1 из 7 типов захода (КАНОН раздел 3)
outline.story_plan {examples, value}               # 5.2 — тело: примеры 60-70% + ценность 24ч
outline.offer_plan                                 # 5.3 — CTA (вопрос/тизер)
outline.template_path
outline.length_target
outline.archetype
outline.angle
outline.topic
outline.type
outline.genre              # from Pass 0.5 (G1..G5)
outline.value_vector            # from Pass 0.5 (primary, V1..V6)
outline.jtbd_target             # from Pass 0.5 (J1..J7)
outline.tuple_fit               # from Pass 0.5 (natural | forced)
outline.value_vectors           # from Pass 0.7 (list: [mandatory, secondary])
outline.value_mandatory_fact    # from Pass 0.7 (verbatim real fact)
```

---

## Pass 1 - Draft по outline и template

### 1.1 - Read template

`Read(outline.template_path)`. Запомнить:
- Структуру разделов
- Length guidelines per section
- Tone notes

### 1.2 - Read Atomic Essay 7-step

Собрать draft строго по КАНОН-структуре (_voice-TEMPLATE.md разделы 1-6), используя outline:
1. Одна главная идея (= `outline.angle`)
2. Заголовок (= `outline.headline.text`, формула блюпринта №`formula_id`)
3. Контекст — первый абзац (= `outline.context_plan.text`, тип захода 1 из 7)
4. Тело: примеры/истории 60-70% (= `outline.story_plan.examples`, нелинейно, с твистами) + Ценность 20-30% на 24ч (= `outline.story_plan.value`)
5. CTA (= `outline.offer_plan` — 1 вопрос с псих-триггером ИЛИ тизер)
6. Ритм абзацев: короткие ёмкие предложения (КАНОН раздел 10). `references/atomic-essay-structure.md` — только как вспомогательный ритм-ориентир, НЕ как driver структуры
7. Отшлифовать первую строку (заголовок)

### 1.3 - Apply 1/3/1 paragraph rhythm

Структура постa:
- **Параграф 1:** 1 строка (= headline + hook). Короткий, бьющий.
- **Параграфы 2-4:** 3 строки каждый (= story body). Чередование длины предложений.
- **Параграф 5:** 1 строка (= close / CTA / inference).

Для `long-educational` 2500 chars: вместо 3 средних параграфов - 5-6. Сохранить ритм: короткий → средний → длинный → средний → короткий.

Для `personal-reflection`: средняя часть может быть narrative (история в 2-3 параграфах), но всё равно 1/3/1 в overall shape.

### 1.4 - Single idea rule

Перечитать draft. Найти один главный тезис. Если есть второй сильный тезис - вырезать и сохранить для отдельного поста.

### 1.5 - First draft output

Записать в memory как `draft.v1 = <full text>`.

---

## Pass 2 - Voice injection (Ivan voice)

### 2.1 - Read Ivan voice reference

`Read(references/_voice-TEMPLATE.md)`. Загрузить:
- 16 уникальных терминов автора
- 11 anti-patterns
- 5 главных приёмов
- ТЫ-форма

### 2.2 - Inject уникальные термины

**Правило:** минимум 1 уникальный термин автора на пост. Предпочтительно 2-3.

Список (из _voice-TEMPLATE.md):
- вайбкодинг / вайбмаркетинг
- контент-завод / ферма
- Нельзяграм (ЖЁСТКО: не Instagram)
- перегнать (контент)
- пдп
- Дубайск
- эксперт (не «программист»)
- цифровой мини-продукт
- метод / методология (не «artifact»)

Просканировать draft.v1. Найти места где общий термин («Instagram» / «фабрика контента» / «приложение») можно заменить на термин автора. Заменить.

Записать `draft.v2 = <updated>`.

### 2.3 - ТЫ-форма check

Просканировать draft.v2 на «Вы / ваш». Везде заменить на «ты / твой». TG-канал автора - на ТЫ.

### 2.4 - Avoid 11 anti-patterns

Прогнать draft.v2 против 11 anti-patterns автора (из _voice-TEMPLATE.md):
1. Em-dash «-» внутри строк → заменить на «-» или запятую
2. «Instagram» → «Нельзяграм»
3. Технический жаргон («artifact», «КЭВ», «связки», «Grand Slam Offer», «digital-twin», «fast-action») → русский эквивалент
4. Негативные статистики («20% доходят», «80% бросают») → убрать или переформулировать в позитив
5. DM-only ценообразование («цена в личке») → конкретное число или убрать
6. Эзотерический регистр («девочки», «вахвахвах», «мур мур») → нейтрально
7. Мат как идентичность → убрать (изредка ОК как акцент)
8. Travel-флекс («40 стран», «Бали», «Golden Gate») → не использовать
9. «Архитектор ИИ-систем» / статусные titles → убрать
10. Списки/буллеты >1 в одном посте → объединить или убрать
11. >1 восклицательного знака → оставить максимум 1

Записать `draft.v3 = <fixed>`.

### 2.5 - Apply 5 главных приёмов (где применимо)

Из _voice-TEMPLATE.md 5 приёмов:
1. **Конкретные цифры** - где можно «много» / «несколько» заменить на конкретное число - сделать.
2. **Pivot strucутра** - «Раньше X. Сейчас Y. Поэтому Z.» Если в посте есть до/после - использовать.
3. **Прямое обращение** - фразы «ты сейчас думаешь / у тебя сейчас X» в нужных местах.
4. **Snap-statements** - короткие декларативные предложения как поворот.
5. **Open-loop в первой строке** - оставить open question / tension чтобы читатель прокрутил вниз.

Применить минимум 2 из 5. Записать `draft.v4 = <enriched>`.

---

## Pass 2.5 - Living Language Injection

После voice injection (Pass 2) - отдельный pass для замены formal AI-оборотов на живые конструкции автора.

### 2.5.1 - Scan против таблицы запрещённых AI-оборотов

`Read(references/_voice-TEMPLATE.md)` раздел 3 - таблица замен.

Просканировать `draft.v3` на match с любой формулировкой из левого столбца таблицы. Для каждого match - заменить на формулировку из правого столбца (или живую вариацию).

Примеры замен:
- «адаптирую под наши форматы» → «прокидываю под наши форматы»
- «через какое-то время выходит» → «через несколько минут получаю»
- «без участия в монтаже» → «без моих рук в монтаже»
- «протестировал на зарубежных аккаунтах» → «прогнал на зарубежке»

### 2.5.2 - Count живых глаголов

Подсчитать в draft глаголы из раздела 1 `_voice-TEMPLATE.md`.

- Long-educational / build-in-public / sales-launch: ≥3 живых глагола. Если меньше - добавить через rewrite.
- Short-situational: ≥2.

### 2.5.3 - Count живых оборотов

Подсчитать обороты из раздела 2 (по зарубежке / прямо сейчас / у ребят / прокидываю / таскал руками / etc.).

Минимум 2 для любого типа. Если меньше - добавить через rewrite.

### 2.5.4 - Check момента-времени

Для personal-reflection / build-in-public / news-jacking: первая треть поста должна содержать ≥1 момент-времени («Сегодня» / «Прямо сейчас» / «На неделе» / «За сутки» / «Через пару дней»).

Если нет - добавить в hook или первый абзац.

### 2.5.5 - Pre-output structural scan (NEW v2.0, MANDATORY)

> **Назначение:** ловить structural-level AI-tells (passive ratio / participle / tricolon / numbered scaffold) ДО Living Language Injection. Воспроизводит логику `04-review.md` 4.8 в reverse - если draft fails здесь, легче переписать чем после review.

Прогнать `draft.v3` через structured checklist из `references/_voice-TEMPLATE.md` v2.0 §4.1:

**Quantitative checks (mandatory):**
- [ ] Passive ratio < 15%
- [ ] Active participle phrases («решающий X», «работающий с Y») ≤ 2
- [ ] Tricolon count (3+ параллельных clause/noun/glagol) ≤ 1
- [ ] Section-headers через «:» («Что делает:», «Под капотом:») ≤ 1
- [ ] Numbered steps (Шаг 1 / Слой 1 / Неделя 1) - отсутствуют ИЛИ ≤ 3
- [ ] Numeric density ≤ 10 specific numbers
- [ ] Em-dash «-» внутри строк - 0
- [ ] BIG CAPS section headers в narrative - 0
- [ ] Reveal-headings («И вот к чему я веду» / «Что я хочу подчеркнуть») ≤ 1
- [ ] Double-emphasis («прямо сейчас, каждый день») - 0

**Genre check (mandatory, см. Pass 0.5):**
- [ ] Жанр поста = `outline.genre` (один из 5 авторских)
- [ ] НЕ tutorial-template
- [ ] НЕ predictable 5-act шаблон

**Lexical check:**
- [ ] 0 англицизмов-формализмов (workflow / pipeline / onboarding / engagement / retention / valid* / framework / etc.)
- [ ] 0 v1-галлюцинаций (бахнул / выкатил / вкатил / у ребят / обратно в найм поползли / вот как устроено / расписываю)
- [ ] 0 mortuary formals (ушли на найм / потеряли клиентов / лишились / дотянуть до)
- [ ] ≥3 verified глагола из §1.2 ЯДРО (завайбкодил / допилил / прокинул / закинул / поднял / сжёг / офигел / прогнал / etc.)
- [ ] ≥1 verified коннектор автора (Поэтому / Но / А также / Потому что / Кстати / Смотри / многоточие / И тут / Сейчас как раз / Короче)

**Если любой checkbox unchecked → переписать draft ДО Pass 2.5 final injection.**

### 2.5.6 - Self-Discovery v2 (replaces v1 §3.46)

После structural scan - прочесть свой draft как **посторонний человек, который ненавидит AI-тексты**, и спросить по каждой фразе:

1. **Test «звучит формально / литературно / pseudo-deep»?** - если да, это AI-tell, заменять
2. **Test «погугли»** - встречается ли фраза в реальной живой речи? Если нет - выдумано
3. **Test «вычитать вслух»** - звучит как «бот написал» или как «живой человек пишет»?
4. **Test «расширь до семантического класса»** - если конкретная фраза кажется подозрительной, обобщить шаблон и добавить в banned list

Записать `draft.v3.5 = <living-language-injected>`.

---

## Pass 2.7 - Sentence-Pattern Cross-Check (NEW v2.2)

> **Прецедент по решению автора (Fix 2):** Living language injection (Pass 2.5) ловит лексику, но не ловит **синтаксическую структуру предложений**. AI-tells проникают на уровне sentence pattern (subject-verb order, clause length, intent flow). Введён explicit sentence-by-sentence cross-check против corpus-extracted patterns.

### Шаг 2.7.1 - Read corpus pattern index

`Read(references/corpus-pattern-index.md)`. Загрузить:
- Sentence patterns по 9 intent categories (opener / verb-object / pivot / quoted / bracketed / negative / closer / sensory / emphasis)
- Match heuristics per category
- Banned shell phrases list (auto-fail)

### Шаг 2.7.2 - Split draft по sentence boundaries

Разбить `draft.v3.5` на отдельные sentences по `.!?…` (учитывая многоточия как один separator).

Для каждого sentence:
1. Identify intent (opener / verb-object / pivot / quoted / bracketed / negative / closer / sensory / emphasis)
2. Grep matching category в `corpus-pattern-index.md`
3. Mark **match** / **no-match**

### Шаг 2.7.3 - Density threshold

🔴 **ЕДИНСТВЕННОЕ МЕСТО ГЕЙТА (NEW, схлоп дубля).** Раньше тот же порог стоял дважды: здесь и в `04-review.md` (corpus pattern density). Считается он **один раз - здесь**, в 04-review результат только перечитывается из `draft.density`, повторный прогон запрещён (дубль давал двойной штраф за один и тот же сигнал).

🔴 **СТАТУС - WARN, а не FAIL (до появления разметки корпуса по целям).** Корпус `corpus-pattern-index.md` смешан по целям формы (R / F / S), поэтому «средний паттерн» не оптимален ни для одной из них: пост, написанный строго по профилю F, обязан расходиться с усреднённым паттерном, и FAIL за это - брак гейта. Как только корпус будет размечен по целям, density считается **по подкорпусу своей цели** (`brief.form_goal`) и порог возвращается в блокирующий.

Подсчитать % matched sentences:

- **≥70% matched** → **PASS**, продолжать
- **50-70% matched** → **WARNING**, log specific no-match sentences, рассмотреть rewrite
- **<50% matched** → **WARN (было FAIL)**: напечатать список no-match sentences + одну строку обоснования, почему они уместны в профиле цели. Возврат к Pass 1 (re-draft) - по решению, не автоматом
- `brief.form_goal` **пуст** → fallback, прежние статусы в силе: `<50%` = **FAIL** с возвратом к Pass 1

Записать `draft.density = <%>` и `draft.density_status = PASS|WARN|FAIL` - 04-review читает эти поля, не пересчитывает.

### Шаг 2.7.4 - Banned shell auto-fail

Любой match с следующими banned shells = automatic FAIL (не зависит от density):

- **Глаголы-галлюцинации:** бахнул / выкатил / вкатил / залип / уделал
- **Reveal-shells:** «вот как устроено» / «И это только начало»
- **Vibemarketing template:** «всё собрал за N дней. Без надрыва, по N часов»
- **Mortuary formals:** «потеряли клиентов» / «ушли на найм»

Эти shells - verified AI-hallucinations / robotic constructions из v3.1 audit. Auto-replace ИЛИ re-draft.

### Шаг 2.7.5 - Mandatory fact verification

Cross-check: `outline.value_mandatory_fact` (из Pass 0.7) ДОЛЖЕН быть verbatim или near-verbatim в `draft.v3.5`.

Если real fact отсутствует или растворён в abstraction → **FAIL** → return к Pass 1 для re-injection.

Записать `draft.v3.7 = <pattern-checked>`.

---

## Pass 3 - Hook calibration

### 3.1 - Read hook template

`Read(references/hooks-15-templates.md)`. Найти раздел для `outline.hook_type`.

### 3.2 - Compare draft hook vs template

Сравнить первые 2-3 строки `draft.v3.7` с canonical pattern для hook_type.

Если расхождение значимое → переписать hook строго по pattern.

### 3.3 - 8-10 word rule на первую строку

Правило Lara Acosta convergence: первая строка ≤ 10 слов (RU), ≤ 8 (EN).

Подсчитать слова в первой строке `draft.v3.7`. Если > 10 - сократить.

### 3.4 - Pattern interrupt для short-situational

Если `outline.type = short-situational`:
- Первая строка должна быть «прерывателем шаблона» - что-то неожиданное / провокативное / контрарианское.
- Test: «зацепит ли это случайного скроллера за 1 секунду?»
- Если первая строка слишком «описательная» - переписать на pattern interrupt.
- Cross-check с corpus-pattern-index opener category (Pass 2.7).

### 3.5 - Headline alignment

Убедиться что финальная первая строка соответствует `outline.headline` (или одной из alternatives, если по ходу work лучше прозвучала alt).

Записать `draft.v5 = <hook-calibrated>`.

---

## Pass 4 - Reality check

### 4.1 - Length check

Подсчитать chars в `draft.v5`.

Правила:
- short-situational → должно быть ≤ 1500 chars (target: 800-1300)
- long-educational → ≤ 2500 chars (target: 1800-2400)
- personal-reflection → ≤ 2500 chars (target: 1500-2300)
- tweet → ≤ 280 chars (target: 200-270)

Если over target:
- Удалить лишние слова (passive voice, hedge phrases, redundancy)
- Удалить второстепенные параграфы
- Сократить story unpack с 4 до 2-3 пунктов

Если under target (мало): добавить конкретику (числа / примеры) - но не воду.

### 4.2 - Single idea check

Перечитать `draft.v5`. Вопрос: «о чём этот пост в одном предложении?»

Если ответ = `outline.angle` → PASS.
Если ответ другой / расплывается → переработать (вернуть фокус на angle).

### 4.3 - Hook-Story-Offer check

Проверить:
- [ ] Hook на месте (первые 2-3 строки бьющие)
- [ ] Story в середине (есть narrative / framework / unpack)
- [ ] Offer/Close в конце (есть закрытие - soft или hard CTA)

Если хоть один из трёх отсутствует - добавить.

### 4.4 - Tone check

Перечитать draft.v5 «глазами автора»:
- Звучит ли как автор? (не как любой инфо-предприниматель)
- Есть ли минимум 1 уникальный термин? (контент-завод / вайбкодинг / Нельзяграм / перегнать)
- ТЫ-форма везде?
- Без em-dash «-» внутри строк?

Если хоть один FAIL → исправить.

Записать `draft.final = <ready for review>`.

---

## Output stage 03

Передаётся в stage 04:

```yaml
draft:
  text: "<полный текст готового черновика>"
  metadata:
    chars: <число>
    paragraphs: <число>
    type: "<short-situational | long-educational | personal-reflection | ...>"
    archetype: "<from outline>"
    hook_type: "<from outline>"
    angle: "<from outline>"
    genre: "<G1..G5 from Pass 0.5>"
    jtbd_target: "<J1..J7 from Pass 0.5>"
    tuple_fit: "<natural | forced from Pass 0.5>"
    value_vectors_planned: ["<mandatory V1..V6>", "<secondary V1..V6>"]  # from Pass 0.7
    value_mandatory_fact: "<verbatim real fact from Pass 0.7>"
    ivan_terms_used: ["вайбкодинг", "контент-завод"]  # список применённых терминов
    sentence_pattern_density: <0.0..1.0 from Pass 2.7>
    passes_completed:
      - "tuple-selection"             # Pass 0.5 expanded
      - "value-vector-selection"      # Pass 0.7 NEW
      - "draft"                       # Pass 1
      - "voice"                       # Pass 2
      - "living-language"             # Pass 2.5
      - "sentence-pattern-cross-check" # Pass 2.7 NEW
      - "hook-cal"                    # Pass 3
      - "reality-check"               # Pass 4
  headline_alternatives:  # carry-over from outline
    - {variant: "A", text: "..."}
    - {variant: "B", text: "..."}
    - {variant: "C", text: "..."}
```

**Передать в:** `workflow/04-review.md`.

---

## Pass 5 - Handoff в Spectrum A/B (если включено)

Если `config.output.ab_variants ≥ 2`:
→ перейти в `workflow/03b-spectrum-ab.md` для генерации двух архитектурно разных версий (A и B) через spectrum-then-choice по 4 структурным частям.

Не делать простую перестановку hook-типа. A и B = разные weighted pick по spectrum (hook / setup / mass / close), не diff одного параметра. Источник правила: memory `feedback_design_choices_not_just_stylization`.

Если `config.output.ab_variants < 2`:
→ пропустить, передать `draft.final` напрямую в `workflow/04-review.md`.

---

## Pass 0.9 - Platform-aware voice reference loading (NEW v3.0)

**Применяется когда `brief.combo` resolved router'ом (Шаг 0.47).**

Вместо hardcoded `examples/_TEMPLATE.md` / `references/_voice-TEMPLATE.md` / `references/_voice-TEMPLATE.md` (telegram-ru defaults) - загружать voice references из `brief.combo`:

```python
voice_reference_file = brief.combo.voice_reference         # examples/_TEMPLATE.md ИЛИ references/_voice-TEMPLATE.md
voice_canonical_file = brief.combo.voice_canonical         # references/_voice-TEMPLATE.md ИЛИ references/_voice-TEMPLATE.md
voice_living_language_file = brief.combo.voice_living_language  # references/_voice-TEMPLATE.md ИЛИ references/linkedin/en/ivan-voice-linkedin-en.md (TBD)
lexicon_file = brief.combo.lexicon_file                    # config-lexicon-ru.md ИЛИ config-lexicon-en.md
```

**Для combo=linkedin-en:**
- `voice_reference` → `references/_voice-TEMPLATE.md` (20 verbatim best posts от 29 EN LinkedIn авторов)
- `voice_synthesis` → `references/_voice-TEMPLATE.md` (10 sections cross-cut: hook formulas / structures / CTAs / formatting / voice signatures / AI-tells / anti-patterns / voice tracks)
- `lexicon_file` → `config-lexicon-en.md` (22 EN AI-tells + 12 anti-patterns + LinkedIn gates)

**Для combo=telegram-ru (default):**
- `voice_reference` → `examples/_TEMPLATE.md` (10 эталонных RU TG постов автора)
- `voice_canonical` → `references/_voice-TEMPLATE.md` (16 терминов + 11 анти-паттернов + 5 главных приёмов)
- `voice_living_language` → `references/_voice-TEMPLATE.md` (живые глаголы/обороты + 26 banned AI-конструкций)
- `lexicon_file` → `config-lexicon-ru.md` (RU lexicon Нельзяграм/em-dash/30+ banned)

**Hard requirement:** все 3 voice references прочитаны до Pass 1 draft. Если хоть один пропущен → STOP, fail Pass 0.

**Status placeholders:** для combo=linkedin-ru / telegram-en (placeholder в config.md) - voice_reference = TBD, выводить warning «output будет generic, нет накопленных данных».

---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL). Верификатор всегда полный (v4.2 — `--fast` устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
