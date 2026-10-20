# Value-Types Framework - Positive Constraint Layer для post v2.2

> **Назначение:** перевести skill из режима «как НЕ писать AI» (negative constraints - 98 banned classes, 11 anti-patterns, AI-tells catalog) в режим «что ОБЯЗАН доставить пост» (positive constraint).
>
> **Прецедент по решению автора:** пост v2.1 прошёл все banned-gates (4.1 / 4.6 / 4.7 / 4.8 / 4.9) - но автор: «бесполезный, не даёт ни insight, ни actionable plan, ни вау так можно было». Skill знал что НЕ делать, но не знал что должен ДОСТАВИТЬ.
>
> **Ключевой принцип:** жанр (Pass 0.5) определяет ФОРМУ. Value-vector (Pass 0.7) определяет ЧТО доставить читателю. Это разные оси. Пост может быть structurally чистым (форма ОК) и при этом useless (ноль value).
>
> **Hard rule:** каждый пост обязан доставлять **≥2 из 6 value-types**. 0-1 detected → FAIL → return в 03-write для inject.

---

## V1 - Specific insight unknown to reader (с proof)

### Definition
Non-obvious observation которое читатель не имел до прочтения поста. Снабжено proof (число / case / source) что это не personal opinion.

### Сигналы что value доставлено
- Читатель после поста может сказать: «не знал что N → теперь знаю»
- Insight не выводится из общих знаний за 5 секунд («подписчики ≠ покупатели» - частично insight но банально без proof)
- Привязан к verifiable factor (цифра, случай, источник)

### автор-template
> «У одного парня недавно 20К подписчиков и копейки в продажах»
>
> insight = «подписчики ≠ покупатели», proof = «20К vs копейки» (конкретное сравнение)

### Detection (regex / heuristic) для review 4.12

**Признак 1.1 - Numerical proof present**
- Regex: `\d+[Кк]?\b` (число + опциональный К) - ≥1 occurrence
- Examples: «20К подписчиков», «3 месяца», «$100K», «<результат>/мес»
- Min: ≥1 numerical proof attached to claim

**Признак 1.2 - Non-obvious claim marker**
- Phrases: «оказалось» / «выяснилось» / «а на самом деле» / «никто не пишет» / «мало кто видит» / «на самом деле»
- ИЛИ: явное противопоставление через «vs / а / но» c числовым контрастом
- Min: ≥1 marker

**Признак 1.3 - Concrete example**
- Не abstract claim («подписчики не равны покупателям» - слабо)
- Привязан к specific случаю («у парня 20К → копейки» - strong)

### Когда применять
- Educational / build-in-public / case posts
- Любой пост который претендует на «полезный»

---

## V2 - Concrete actionable step (что делать через 5 минут)

### Definition
Прямая инструкция читателю с конкретным первым шагом который можно сделать в ближайшие 24 часа (предпочтительно в ближайшие 5 минут).

### Сигналы что value доставлено
- Читатель закрывает пост и идёт делать X
- Не «попробуй когда-нибудь подумать о» - конкретный action с конкретным input
- Указан tool / место / запрос - не голое «открой что-то»

### автор-template
> «Открой Claude, спроси у него: какие 3 мини-продукта решают одну боль в моей нише за 1-5К ₽. Получи 3 варианта. Выбери один»

### Detection для review 4.12

**Признак 2.1 - Imperative verb in 2nd person**
- Regex: `(открой|спроси|сделай|напиши|зайди|поставь|включи|скопируй|вставь|запиши|посчитай|посмотри|возьми|задай|прокинь|допили)`
- Min: ≥1 imperative

**Признак 2.2 - Concrete object / tool**
- Imperative + named tool («Claude», «Cursor», «канал», «таблица», «calendar», «Telegram»)
- Min: ≥1 imperative attached to concrete object

**Признак 2.3 - Time-bounded**
- Phrases: «сейчас» / «через 5 минут» / «прямо сегодня» / «до конца дня» / «в ближайший час»
- Min: ≥1 time bound в actionable block

### Когда применять
- Tool-drop / educational / build-in-public с methodology
- ОБЯЗАТЕЛЬНО в любом посте который заявляет «полезный»

---

## V3 - Counter-intuitive frame (shock через факт)

### Definition
Переворачивает массовое мнение через verifiable factor. Не голый contrarian («все дураки, а я умный»), а аргумент через measurable thing.

### Сигналы что value доставлено
- Reader реагирует «погоди, я думал наоборот»
- Frame inverted на конкретном основании, не на authority
- Аргумент проверяем (можно проверить factor)

### автор-template
> «80% сил на контент / 20% на воронку - это и есть причина почему ты не продаёшь»
>
> массовое мнение = «надо больше контента», counter = «контент без воронки = ноль продаж», factor = пропорция 80/20

### Detection для review 4.12

**Признак 3.1 - Mass opinion stated**
- Phrases: «все думают / большинство пишет / принято считать / стандартный совет / массовое мнение / на курсах учат»
- ИЛИ: имплицитное предположение которое автор переворачивает

**Признак 3.2 - Inversion marker**
- Phrases: «а на деле / а реально / а по факту / на самом деле / оказывается / на практике / в реальности»
- Min: ≥1 marker

**Признак 3.3 - Factor / число обосновывающее переворот**
- Не голое «это не работает», а «не работает потому что [конкретная причина с числом / механизмом]»
- Min: ≥1 measurable factor в обосновании

### Когда применять
- Контрарианские посты (Outlaw архетип) - раз в 2-3 недели
- Category creation
- Любой post где можно перевернуть default reader assumption

---

## V4 - Verifiable case study (имя + цифра + результат)

### Definition
Конкретный человек, конкретные числа, конкретный результат. Не «один парень что-то сделал и теперь зарабатывает».

### Сигналы что value доставлено
- Reader может представить кейс детально (видит человека, понимает что он сделал, видит куда пришёл)
- Включает 3 элемента: имя / возраст / ниша + конкретная цифра + конкретный результат

### автор-template
> «<имя ученика>, <возраст>. Бывший <профессия>. За 3 месяца через систему вышла на <результат>/мес»
>
> имя = <имя ученика>, возраст = <возраст>, ниша = <профессия>, время = 3 месяца, результат = <результат>/мес

### Detection для review 4.12

**Признак 4.1 - Named subject**
- Regex: `\b[А-Я][а-я]+\s+[А-Я][а-я]+\b` (Имя Фамилия)
- ИЛИ: имя + возраст (`\bимя,?\s+\d+\s+(лет|года)\b`)
- ИЛИ: «ученик по [конкретная ниша]» (НЕ голое «один парень»)
- Min: ≥1 named subject

**Признак 4.2 - Concrete number**
- Regex: `\d+[Кк]?\s*[/в]?\s*(мес|месяц|год|нед)|₽|\$\d+|\d+%`
- Min: ≥1 result-number attached to subject

**Признак 4.3 - Time-to-result**
- Phrases: «за 3 месяца / за полгода / за 2 недели / через месяц»
- Min: ≥1 time bound

**Признак 4.4 - Banned vague subject**
- НЕ должно быть в одиночестве: «один парень», «одна девушка», «один эксперт», «одна моя ученица» (без имени/ниши/возраста)
- Если detected → V4 НЕ засчитан, downgrade до placeholder

### Когда применять
- Narrative-кейс жанр (mandatory если genre = narrative-кейс)
- Sales-launch (social proof)
- Любой educational пост где можно опереть claim на конкретный кейс

---

## V5 - Strategic clarity (big picture model)

### Definition
Фреймворк / model statement который объясняет ПОЧЕМУ механика работает. Не tactical step, а strategic frame который даёт reader новое умственное cleavage.

### Сигналы что value доставлено
- Reader получает новый способ думать о проблеме
- Pattern explanation: «X работает потому что [structural reason]»
- Не «делай Y», а «вот почему Y вообще работает»

### автор-template
> «Воронка собирается раньше первого поста - это и есть отличие системного бизнеса от блога»
>
> model = «системный бизнес vs блог», ключевой factor = «момент сборки воронки относительно контента»

### Detection для review 4.12

**Признак 5.1 - Frame statement**
- Phrases: «это и есть отличие / это и есть причина / здесь и зарыто / разница в / суть в том что / именно поэтому»
- Min: ≥1 frame statement

**Признак 5.2 - Causal mechanism**
- Не голый claim, а explanation механизма: «потому что [X влияет на Y через Z]»
- Connectives: «потому что / так как / за счёт того что / из-за того что»

**Признак 5.3 - Generalizable insight**
- Не one-off observation, а pattern применимый к классу ситуаций
- Reader может применить frame к своему случаю

### Когда применять
- Long-educational
- Build-in-public с reflection
- Любой пост где есть risk остаться на уровне tactics без strategy

---

## V6 - Original thinking (не regurgitation)

### Definition
Своя intellectual claim которая идёт против consensus или формирует новую category. Не пересказ чужих фреймворков, а своя позиция с обоснованием.

### Сигналы что value доставлено
- Reader не мог прочитать эту мысль у других экспертов
- Claim формулирована как position автора, а не как neutral observation
- Есть обоснование (не голый opinion)

### автор-template
> «Контент-завод 2025 умер. Работает только система разных форматов через Claude Code с фокусом на монетизацию»
>
> claim = «контент-завод 2025 устарел», своя категория = «система разных форматов через Claude Code», обоснование имплицитное (рынок сдвинулся)

### Detection для review 4.12

**Признак 6.1 - First-person intellectual claim**
- Phrases: «я считаю / моя позиция / я вижу / на мой взгляд / по моим наблюдениям / я этому учу / я это называю»
- ИЛИ: declarative claim без hedge («X умер», «работает только Y»)
- Min: ≥1 claim with author voice

**Признак 6.2 - Against-consensus marker**
- Phrases: «вопреки / в отличие от / большинство / все пишут что / обычно говорят / стандарт» + inversion
- ИЛИ: declarative inversion («X не работает», «нет такого что Y», «это уже не Z»)
- Min: ≥1 contrarian marker

**Признак 6.3 - Reasoning / supporting argument**
- Не голый opinion, а обоснование (хотя бы 1 reason)
- Connectives: «потому что / так как / за счёт того что / опираясь на»

**Признак 6.4 - Category-naming**
- Опционально: автор именует новую category («контент-завод», «вайбмаркетинг», «вайбкодинг», «система разных форматов»)
- Bonus для V6 score

### Когда применять
- Manifesto / values posts
- Category-creation
- Любой пост где можно сместить с «обзор индустрии» на «моя позиция»

---

## Genre → Value-Vector Mapping

| автор-жанр (Pass 0.5) | Mandatory value-types | Optional value-types | Min count |
|---|---|---|---|
| **Narrative-разбор-кейса** | V4 (кейс) | V1, V2, V5 | ≥2 |
| **Vulnerability + reveal** | V1 (insight), V6 (original) | V3, V5 | ≥2 |
| **Alarm + reaction** | V2 (actionable) | V1, V4, V6 | ≥2 |
| **Lifestyle + brag** | V4 (имя+цифра+результат) | V1, V5 | ≥2 |
| **Build-in-public + paradox** | V1 (insight), V2 (actionable) | V3, V4, V5 | ≥2 |

**Rule:** mandatory value-type обязан присутствовать. Если genre = narrative-кейс и V4 не detected → FAIL независимо от других value-types.

---

## Detection Summary Table (для 04-review Sub-stage 4.12)

| V# | Type | Regex / heuristic ключевой сигнал | Min count |
|---|---|---|---|
| V1 | Insight + proof | numerical (`\d+[Кк]?`) + `(оказалось\|выяснилось\|на самом деле)` | proof≥1 + claim≥1 |
| V2 | Actionable step | `(открой\|спроси\|сделай\|напиши)` + named tool + time bound | imp≥1 + obj≥1 |
| V3 | Counter-intuitive | mass-opinion marker + inversion + factor | 3 elements |
| V4 | Case study | Имя Фамилия / имя+возраст + число + время | 3 elements |
| V5 | Strategic clarity | `(это и есть отличие\|причина\|именно поэтому)` + причинность | frame≥1 + mech≥1 |
| V6 | Original thinking | first-person claim + contrarian marker + reasoning | 3 elements |

---

## Anti-patterns (что НЕ считается value)

- **Vague affirmation:** «контент важен», «надо думать о монетизации» - нет proof, не actionable, не contrarian
- **Generic советы которые знает любой:** «снимайте больше рилсов» - нулевой insight
- **Pseudo-insight без proof:** «многие не понимают что подписчики не покупатели» (без числа / кейса)
- **Self-evident truisms:** «без действий нет результата» - value=0
- **Claim без обоснования:** «вайбкодинг - это будущее» (без mechanism / case / number)
- **Quote-dropping без contextual application:** «как говорил Хормози» без своей claim
- **Recap чужого знания:** пересказ известного fрейм без своей claim - это V6 FAIL

---

## Cross-reference

- **Pass 0.5 (genre):** `workflow/03-write.md`
- **Pass 0.7 (value-vector selection, NEW v2.2):** `workflow/03-write.md`
- **Sub-stage 4.12 (value delivery check, NEW v2.2):** `workflow/04-review.md`
- **Memory:** `feedback_value_injection_framework.md`
- **Genres:** `references/_voice-TEMPLATE.md` §4.2
- **Positive craft patterns:** Sub-stage 4.9 в `workflow/04-review.md`
