# Audit gaps v3.1 - 22 robotic constructions vs существующие gates

> **Контекст:** по решению автора скилл post v3.1 выдал длинный пост, который автор назвал «пиздец, роботизированный». Claude сам обнаружил 22+ robotic constructions по 8 категориям. Все они прошли существующие 8 hard gates в `04-review.md` + 26 семантических классов AI-tells (A-Z) в `_voice-TEMPLATE.md` раздел 3.45.
>
> **Цель audit'а:** найти structural gaps, которые позволили этим constructions пройти все gates. Файл = input для v2.0 правил скилла.
>
> **Не вносит изменения в существующие файлы.** Только рекомендации.

---

## Раздел 1 - Прогон 22 constructions через существующие gates

Для каждой construction: какой gate **должен был** ловить (если есть), какой **поймал** (если поймал), почему **пропустилось** (если пропустилось).

### Категория 1: Formal subject naming (3 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 1 | «эксперт с 20К подписчиков» (вместо «один пацан с 20К») | 4.2.4 Competitor Pass / 4.6.4 Anti-water check | НЕ ПОЙМАЛ | Competitor Pass проверяет «отличает ли автора от конкурентов» но не семантику subject naming. Anti-water проверяет первый/последний абзац качественно, без правила про живое именование |
| 2 | «У ребят та же логика» (норм формула) - но в контексте «эксперт» формальный subject уже задан | 4.7.3 Живые обороты count | ЧАСТИЧНО | «у ребят» засчитан как живой оборот, но он не компенсирует formal subject в предыдущем абзаце |
| 3 | «У эксперта с 20К это не работает» (повтор formal subject в pivot) | MISSING | НЕ ПОЙМАЛ | Нет правила «subject именуется одинаково через весь пост - formal или живой, не mix» |

**Семантика:** «эксперт» - generic noun, описание-роль. автор в постах называет конкретных людей по-другому: «один пацан», «у ребят», «у одного моего», «ученик», «один из» (post 2199 «Ученик ищет сотрудников»). «Эксперт» = англицизм-формализм когда речь про человека, а не про экспертность.

---

### Категория 2: Passive voice (3 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 4 | «Воронка была собрана ДО первого поста» (вместо «воронку собрал ДО») | 4.2.5 Editor Pass | НЕ ПОЙМАЛ | Editor Pass упоминает passive voice в списке, но это soft scan, без quantitative threshold. Прошло потому что other findings были ≤ 2 |
| 5 | «Сайт для <твой-хэндл> собран через Claude Code» (passive «собран») | 4.2.5 Editor Pass | НЕ ПОЙМАЛ | Same - soft scan |
| 6 | «Оплата прикручивается через ЮKassa» (passive reflexive «прикручивается») | 4.2.5 Editor Pass | НЕ ПОЙМАЛ | Same |

**Семантика:** passive voice = AI-default. У автора везде активный залог + личное Я: «бахнул», «собрал», «прокинул», «настроил». Конкретный субъект всегда виден.

**Что есть:** упоминание в 4.2.5 без metric.
**Чего нет:** quantitative rule (passive ratio > X% = FAIL).

---

### Категория 3: Participle phrases (2 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 7 | «продукт, решающий одну боль» (participle phrase = формальная конструкция) | MISSING | НЕ ПОЙМАЛ | Нет правила про participle phrases вообще. Класс A-Z не покрывает |
| 8 | «Минимальный продукт за 1-5К, решающий одну боль» (повтор той же конструкции) | MISSING | НЕ ПОЙМАЛ | Same |

**Семантика:** причастные обороты («решающий», «работающий», «помогающий») = formal AI-default. Живой автор говорит «продукт под боль» / «продукт который решает одну боль» (relative clause) / «продукт на одну боль».

**Что есть:** ничего.
**Чего нет:** правило «participle phrases (active participle + noun) = warning. >2 в посте = FAIL».

---

### Категория 4: Англицизмы-формализмы (5 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 9 | «Продукт не валидируется» (валидировать = англицизм) | 4.1.3 Banned terms / 2.4 anti-pattern 3 | НЕ ПОЙМАЛ | В banned list нет «валидируется/валидация». Anti-pattern 3 в _voice-TEMPLATE.md перечисляет только specific terms (artifact, КЭВ, связки, Grand Slam Offer, digital-twin, fast-action) |
| 10 | «Минимальный продукт за 1-5К... валидируется за неделю» (повтор) | Same | НЕ ПОЙМАЛ | Same |
| 11 | «Webhook отправляет покупателя в TG-бот» (webhook = англицизм без объяснения) | MISSING | НЕ ПОЙМАЛ | Тех-термин-англицизм. У автора было бы «бот ловит оплату» / «по оплате срабатывает» |
| 12 | «7 дней onboarding» (англицизм) | MISSING | НЕ ПОЙМАЛ | автор бы написал «прогревочная цепочка на 7 дней» / «бот ведёт 7 дней» |
| 13 | «Бот-дожим» (норм) vs «текстовая автоворонка» (норм)/ «onboarding» в одном посте - несогласован регистр | MISSING | НЕ ПОЙМАЛ | Нет правила «register consistency check» |

**Семантика:** «валидируется» - корпоративный жаргон стартапов, в живой речи автора этого нет. «Onboarding», «webhook» - тех-термины-англицизмы, прокидываются без локализации.

**Что есть:** 4.1.3 banned list (7 terms hard-fail) + anti-pattern 3 в _voice-TEMPLATE.md.
**Чего нет:** расширенный banned list для англицизмов-формализмов: «валидируется», «валидация», «onboarding», «прогревочная воронка» допустимо но «onboarding» - нет, «релевантность», «engagement», «конверсия» (если в narrative-контексте, не в метрик), «таргетинг», «бенчмарк», «фидбэк», «нетворк», «pipeline», «workflow».

---

### Категория 5: AI-poetic (2 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 14 | «охват ради охвата» (поэтичный AI-оборот) | 3.45 Класс A-Z | НЕ ПОЙМАЛ | Это «X ради X» паттерн - повтор слова с предлогом для эффекта. Класс A («не X, это Y») близко, но не покрывает. Это новый класс - самозамкнутая риторическая конструкция |
| 15 | «не охват ради охвата» (та же конструкция в pivot) | Same | НЕ ПОЙМАЛ | Same. Дважды в одном посте - должно было удвоить вес detection |

**Семантика:** «X ради X» = pseudo-deep AI-оборот, имитирует афоризм. В живой речи автора не встречается. Близкий ban: «контент ради контента» (если применить тест «погугли» - встречается в инфобиз-блогах но не в речи автора конкретно).

**Что есть:** Класс B (Pseudo-deep AI-summary) близок но не покрывает structure «X ради X».
**Чего нет:** новый класс AA «Self-referential rhetorical loop» - «X ради X», «работа ради работы», «не отчёт ради отчёта». Любое повторение noun через «ради» / «для» / «во имя» / «во благо».

---

### Категория 6: Двойные emphasis (1 instance, но критичный)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 16 | «прямо сейчас, каждый день» (двойной акцент на одну мысль) | 4.2.5 Editor Pass (redundancy) | НЕ ПОЙМАЛ | Editor Pass упоминает «совершенно идеальный», «прямо сейчас в данный момент» как redundancy, но «прямо сейчас, каждый день» - два РАЗНЫХ time anchor'а соединённых запятой, что создаёт двойной emphasis на одну мысль |

**Семантика:** «прямо сейчас» = момент / «каждый день» = регулярность. Это две разные семантические рамки. Соединение через запятую = AI-default «ускоряет ритм через дублирование без добавления смысла». автор бы написал просто «прямо сейчас» или просто «каждый день», но не оба.

**Что есть:** 4.2.5 mentions redundancy.
**Чего нет:** правило «два time-anchor'а / два intensifier'а через запятую без новой информации = redundancy → FAIL».

---

### Категория 7: Linking phrases-связки (4 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 17 | «Вот как устроено:» (linking) | 4.7.6 Paragraph connectivity / 3.4.5 коннекторы автора | ЧАСТИЧНО | 3.4.5 даёт список pro-коннекторов («Сейчас как раз», «И тут», «Короче»). «Вот как устроено» не в списке pro, не в списке anti. Прошло потому что не явный AI-tell, но и не Ivan |
| 18 | «Не из-за контента.» (короткая formal-связка) | MISSING | НЕ ПОЙМАЛ | Same - нейтральная связка не в списке pro/anti |
| 19 | «потому что воронки нет» (formal causation linker) | MISSING | НЕ ПОЙМАЛ | «потому что» = formal explanatory. автор бы написал «там воронки нет» / «у него воронки нет» - implicit causation через context |
| 20 | «У эксперта с 20К это не работает потому что воронки нет, и каждый его просмотр это охват ради охвата» - длинная formal subordinate clause | MISSING | НЕ ПОЙМАЛ | Нет правила про длину subordinate clauses или сложноподчинённых предложений |

**Семантика:** автор пишет короткими прямыми предложениями. «Потому что» / «вот как устроено» / «не из-за X» - formal explanatory linkers, AI-default для structured exposition. Живой автор объясняет через **последовательность фактов** без явных linkers: «У него воронки нет. Каждый просмотр просто охват. Денег нет.»

**Что есть:** 3.4.5 список pro-коннекторов. 4.7.6 paragraph connectivity check.
**Чего нет:** anti-list formal linkers («потому что», «вот как», «не из-за», «именно поэтому», «так как», «в результате чего», «по причине», «вследствие», «таким образом», «следовательно»).

---

### Категория 8: Mortuary formals (2 instances)

| # | Construction | Gate-candidate | Поймал? | Reason |
|---|---|---|---|---|
| 21 | «Через год выгорели и ушли на найм» (formal «ушли на найм») | 4.1.7 метафоры / 4.7.1 AI-обороты | НЕ ПОЙМАЛ | «Ушли на найм» - формальная биографическая формулировка из резюме / интервью. В живой речи автора было бы «обратно в найм поползли», «снова на дядю работают», «вернулись в офис», «опять зарплату ждут» |
| 22 | «До первой продажи дотянуть сложно» (formal «дотянуть») | MISSING | НЕ ПОЙМАЛ | «Дотянуть» в context «до результата» = formal-biographical. автор бы написал «не дойдут» / «сольются» / «забьют» |

**Семантика:** mortuary formals = formulaic biographical exposition language. Типа некролог или intro к интервью. В живой речи автора это вульгаризировано: «обратно в найм поползли», «отвалились», «сольются», «забили», «вылетели», «бросили».

**Что есть:** ничего specific. 4.1.7 metaphors не покрывает потому что это НЕ метафоры - это formal lexicon.
**Чего нет:** правило про mortuary/biographical formal expressions.

---

## Раздел 2 - Сводная таблица 22 constructions

| # | Construction | Категория | Где должен был ловить | Поймал? | Status |
|---|---|---|---|---|---|
| 1 | эксперт с 20К | Subject naming | 4.6.4 Anti-water | НЕТ | MISSING rule |
| 2 | У ребят та же логика | Subject naming | 4.7.3 (но в плохом контексте) | OK как oborot, NO как corrective | PARTIAL |
| 3 | У эксперта с 20К это не работает | Subject naming | MISSING | НЕТ | MISSING rule (consistency) |
| 4 | Воронка была собрана | Passive | 4.2.5 Editor Pass | НЕТ | WEAK enforce |
| 5 | Сайт собран через Claude Code | Passive | 4.2.5 | НЕТ | WEAK enforce |
| 6 | Оплата прикручивается | Passive | 4.2.5 | НЕТ | WEAK enforce |
| 7 | продукт, решающий одну боль | Participle | MISSING | НЕТ | MISSING rule |
| 8 | продукт ... решающий одну боль | Participle | MISSING | НЕТ | MISSING rule |
| 9 | продукт не валидируется | Англицизм | 4.1.3 / 2.4 | НЕТ | MISSING in banned list |
| 10 | валидируется за неделю | Англицизм | Same | НЕТ | MISSING |
| 11 | Webhook отправляет | Англицизм | MISSING | НЕТ | MISSING |
| 12 | 7 дней onboarding | Англицизм | MISSING | НЕТ | MISSING |
| 13 | register mix (бот-дожим + onboarding) | Англицизм | MISSING | НЕТ | MISSING |
| 14 | охват ради охвата | AI-poetic | 3.45 Class B (близко) | НЕТ | MISSING (new Class AA) |
| 15 | не охват ради охвата | AI-poetic | Same | НЕТ | MISSING |
| 16 | прямо сейчас, каждый день | Double emphasis | 4.2.5 redundancy | НЕТ | WEAK enforce |
| 17 | Вот как устроено: | Linker | 3.4.5 коннекторы | NEUTRAL (не в pro, не в anti) | MISSING anti-list |
| 18 | Не из-за контента. | Linker | MISSING | НЕТ | MISSING |
| 19 | потому что воронки нет | Linker | MISSING | НЕТ | MISSING |
| 20 | длинная subordinate clause «потому что ... и каждый ...» | Linker / sentence structure | MISSING | НЕТ | MISSING |
| 21 | ушли на найм | Mortuary | 4.1.7 metaphors (not match) | НЕТ | MISSING |
| 22 | дотянуть сложно | Mortuary | MISSING | НЕТ | MISSING |

**Итог: 22 из 22 пропустились всеми gates. 0 caught.**

---

## Раздел 3 - Анализ по 8 категориям

### Категория 1: Subject naming

**Что есть:**
- 4.6.4 Anti-water check (качественный, без правила про subject именование)
- _voice-TEMPLATE.md приём 1 «Гибрид личный момент → метод» - упоминает personal moment но не правило про именование третьих лиц

**Чего нет:**
- Правило «третьи лица именуются живо: «один пацан» / «у ребят» / «один из учеников» / «у моего» / «у одного». НЕ formal noun («эксперт», «специалист», «человек», «предприниматель»)»
- Consistency check: subject именован одинаково через весь пост

**Куда добавить:**
- `references/_voice-TEMPLATE.md` → новый раздел **3.47 Subject naming rules** с списком pro/anti
- `workflow/04-review.md` → расширить **4.7.6** или новый **4.7.7 Subject Living Naming Check**: regex scan на formal subject nouns в контекстах «один + noun» / «у noun с +число»
- `config.md` → `lexicon_banned_patterns` добавить formal subject nouns

---

### Категория 2: Passive voice

**Что есть:**
- 4.2.5 Editor Pass mentions passive voice в списке findings - soft scan, без metric
- _voice-TEMPLATE.md раздел 1 «Действия с инструментом / кодом» - все глаголы активные

**Чего нет:**
- Quantitative rule: passive ratio > 15% = WARNING, > 25% = FAIL
- Regex detection: `был(а|и|о)? + причастие прошедшего времени на -н/-т`, `глагол + -ся` reflexive в context работы

**Куда добавить:**
- `workflow/04-review.md` → новый **sub-stage 4.8 Structural Pass**, раздел 4.8.1 Passive voice quantitative check
- `references/_voice-TEMPLATE.md` → раздел **3.48 Passive ratio threshold**

---

### Категория 3: Participle phrases

**Что есть:**
- ничего

**Чего нет:**
- Правило про активные причастия: «решающий», «работающий», «помогающий», «делающий» + noun = formal AI construction
- Замена через relative clause «который X» или через preposition «под X» / «на X»

**Куда добавить:**
- `references/_voice-TEMPLATE.md` → раздел **3.49 Participle phrase ban**
- `workflow/04-review.md` → **4.8.2 Participle phrase check**

---

### Категория 4: Англицизмы-формализмы

**Что есть:**
- 4.1.3 banned terms hard list (7 items: artifact, digital-twin, fast-action, КЭВ, связки, Grand Slam Offer, pain points)
- _voice-TEMPLATE.md anti-pattern 3 - same list

**Чего нет:**
- Расширенный banned list для англицизмов-формализмов корпоративного лексикона:
  - «валидируется» / «валидация» / «валидировать» (в смысле «проверить продукт на рынке»)
  - «onboarding» (вместо «прогревочная цепочка» / «прогрев»)
  - «webhook» (вместо «по оплате срабатывает» / «бот ловит» - допустимо в чисто-технических контекстах но не в narrative)
  - «engagement» (вместо «вовлечение» / «реакции»)
  - «релевантность» (вместо «подходит» / «попадает»)
  - «таргетинг», «бенчмарк», «фидбэк», «нетворк», «pipeline», «workflow» (в narrative)
  - «iteration» (вместо «итерация» - допустимо)

**Куда добавить:**
- `config.md` → `lexicon_banned_hard` расширить
- `references/_voice-TEMPLATE.md` → раздел **3 запрещённые AI-обороты** расширить таблицу замен

---

### Категория 5: AI-poetic

**Что есть:**
- Класс B Pseudo-deep AI-summary
- Класс H Filler intensifiers

**Чего нет:**
- Класс AA «Self-referential rhetorical loop» - «X ради X», «работа ради работы», «контент ради контента», «деньги ради денег», «успех ради успеха»
- Класс AB «Pseudo-aphorism»: любая short formulation которая претендует на афоризм, но в реальности - pseudo-deep AI-смысл

**Куда добавить:**
- `references/_voice-TEMPLATE.md` → расширить **3.45 Семантические классы** до A-AB

---

### Категория 6: Двойные emphasis

**Что есть:**
- 4.2.5 Editor Pass mentions «прямо сейчас в данный момент» как redundancy

**Чего нет:**
- Правило про два разных intensifier'а / two time anchors через запятую: «прямо сейчас, каждый день» / «всегда и везде» / «постоянно, регулярно»

**Куда добавить:**
- `references/_voice-TEMPLATE.md` → новый раздел **3.50 Double emphasis ban**
- `workflow/04-review.md` → **4.8.3 Double emphasis check**

---

### Категория 7: Linking phrases-связки

**Что есть:**
- 3.4.5 коннекторы автора (pro-list): «Сейчас как раз», «И тут», «И теперь», «Короче»
- 3.4.5 anti-list (минимальный): «Также», «Кроме того», «Более того», «В заключение», «С другой стороны»

**Чего нет:**
- Расширенный anti-list formal explanatory linkers:
  - «потому что» (если используется в structured exposition, не в живой речи)
  - «вот как устроено» / «вот как это работает»
  - «не из-за X»
  - «именно поэтому»
  - «так как»
  - «в результате чего»
  - «по причине»
  - «вследствие»
  - «таким образом»
  - «следовательно»
- Правило про длину subordinate clauses: «придаточное предложение длиннее главного = AI-tell»

**Куда добавить:**
- `references/_voice-TEMPLATE.md` раздел 3.4.5 → расширить anti-list
- Новый раздел **3.51 Sentence structure: subordinate clauses**
- `workflow/04-review.md` → **4.8.4 Linker anti-list check**

---

### Категория 8: Mortuary formals

**Что есть:**
- 4.1.7 метафоры (не покрывает потому что «ушли на найм» не метафора)
- ничего specific

**Чего нет:**
- Правило про biographical/mortuary formal expressions:
  - «ушли на найм» → «обратно в найм поползли», «снова на дядю»
  - «дотянуть до X» → «дойти», «не сольются»
  - «достичь результата» → «получить деньги», «получить оплаты»
  - «реализовать себя» → «начать делать»
  - «обрести опыт» → «попробовать»
  - «принять решение» → «решиться»
  - «осуществить переход» → «перейти»
  - «совершить покупку» → «купить»

**Куда добавить:**
- `references/_voice-TEMPLATE.md` → новый раздел **3.52 Mortuary formals / biographical lexicon**
- `workflow/04-review.md` → **4.8.5 Mortuary check**

---

## Раздел 4 - Главные структурные gaps

### Gap 1 (топ важности): Нет Structural Pass

8 категорий - это **структурные паттерны**, не точечные фразы. Все 26 классов A-Z в 3.45 - semantic classes на уровне фразы. Но 8 категорий robotic - это:
- Subject naming (повторение через весь пост)
- Passive voice (ratio через весь пост)
- Participle phrases (повторение конструкции)
- Sentence structure (длина subordinate clauses)

Это требует **structural-level analysis**, не fragment-level. Существующие gates сканируют фразы. Нужен Pass который смотрит на пост как на **структуру**: каков ratio активных глаголов к passive, какова средняя длина предложения, сколько subject именований, сколько formal nouns vs живые.

### Gap 2 (топ важности): banned-list для англицизмов-формализмов слишком узкий

Текущий list (7 items) - это специфические термины автора. Но AI-default корпоративный лексикон («валидируется», «onboarding», «engagement», «релевантность») широко проникает в любой длинный пост про продукт/маркетинг. Нужен расширенный list (30+).

### Gap 3 (средне-высокий): self-discovery method не сработал в пре-output

В 3.46 описан Self-Discovery Method («pre-output semantic scan через persona "человек ненавидящий AI-тексты"»). Это **должно было** поймать большую часть 22 constructions качественным review. Но **процедура была пропущена в run'е** или применена formally.

Это указывает на проблему **enforcement**: self-discovery - qualitative gate, легко skip'ается. Нужно либо превратить его в structured checklist (с явными yes/no вопросами по каждой категории), либо вынести в отдельный Pass с output'ом.

---

## Раздел 5 - Рекомендации для v2.0

### A. В `references/_voice-TEMPLATE.md`

Добавить новые разделы:

- **3.47 Subject naming rules** - pro/anti list для именования третьих лиц
- **3.48 Passive ratio threshold** - quantitative rule по passive
- **3.49 Participle phrase ban** - anti active participle constructions
- **3.50 Double emphasis ban** - два intensifier'а через запятую
- **3.51 Sentence structure: subordinate clauses** - длина придаточных
- **3.52 Mortuary formals** - biographical lexicon anti-list

Расширить существующие:

- **3 запрещённые AI-обороты** - добавить англицизмы-формализмы (валидируется, onboarding, webhook, engagement, релевантность, таргетинг, бенчмарк, фидбэк, нетворк, pipeline, workflow)
- **3.4.5 коннекторы** - расширить anti-list formal linkers (потому что в structured exposition, вот как устроено, не из-за X, именно поэтому, так как, в результате чего, по причине, вследствие, таким образом, следовательно)
- **3.45 Семантические классы** - добавить:
  - **Класс AA** - Self-referential rhetorical loop (X ради X)
  - **Класс AB** - Pseudo-aphorism

### B. В `workflow/04-review.md`

Новый **Sub-stage 4.8 - Structural Pass** (HARD GATE) после 4.7:

- **4.8.1** Passive ratio quantitative check (passive count / total verbs > 15% = WARNING, > 25% = FAIL)
- **4.8.2** Participle phrase check (count active participle + noun constructions; > 2 = WARNING, > 4 = FAIL)
- **4.8.3** Double emphasis check (regex: two time anchors / two intensifiers через запятую без новой информации)
- **4.8.4** Linker anti-list check (regex scan на formal explanatory linkers; ≥ 2 = FAIL)
- **4.8.5** Mortuary formals check (regex + lexicon match на biographical formal expressions; ≥ 1 = FAIL)
- **4.8.6** Subject naming consistency check (если в посте есть «эксперт» / «специалист» / «предприниматель» в контексте конкретного третьего лица - FAIL, должно быть «пацан» / «один из» / «у ребят»)
- **4.8.7** Subordinate clause length check (если придаточное длиннее главного > 1.5x - WARNING)

### C. В `workflow/03-write.md`

Расширить **Pass 2.5 Living Language Injection**:

- **2.5.5** Subject naming pass - scan на formal subject nouns, заменить на живые
- **2.5.6** Passive → Active conversion pass - переписать passive в active с явным субъектом
- **2.5.7** Participle → relative clause / preposition rewrite
- **2.5.8** Formal linker removal - удалить formal linkers, оставить смысл через sequence фактов
- **2.5.9** Mortuary formal removal - заменить biographical formals на живые vulgar variants

Превратить **Self-Discovery 3.46** в structured pre-output checklist с явными yes/no вопросами по каждой из 8 категорий (вместо generic «прочитай как человек, ненавидящий AI»).

### D. В `config.md`

Расширить `lexicon_banned_hard`:

```yaml
lexicon_banned_hard:
  # Existing
  - "-"
  - "artifact"
  - "digital-twin"
  - "fast-action"
  - "Grand Slam Offer"
  - "КЭВ"
  - "связки"
  # New (англицизмы-формализмы)
  - "валидируется"
  - "валидация"
  - "валидировать"
  - "onboarding"
  - "engagement"
  - "релевантность"
  - "таргетинг"
  - "бенчмарк"
  - "фидбэк"
  - "нетворк"
  - "pipeline"
  - "workflow"
```

Добавить `lexicon_banned_patterns`:

```yaml
lexicon_banned_patterns:
  # Existing metaphors / invented collocations
  ...
  # New (structural)
  - passive_voice_ratio_threshold: 0.15  # > 15% = WARNING, > 25% = FAIL
  - participle_phrase_count_threshold: 2  # > 2 = WARNING, > 4 = FAIL
  - formal_subject_nouns:
      - "эксперт"  # в context «один + эксперт» / «эксперт с +число»
      - "специалист"
      - "предприниматель"
      - "автор"  # как описание третьего лица, не автора
      - "пользователь"
      - "человек"  # в context «один человек с»
  - formal_linkers_anti:
      - "потому что"  # в structured exposition context
      - "вот как устроено"
      - "вот как это работает"
      - "не из-за"
      - "именно поэтому"
      - "так как"
      - "в результате чего"
      - "по причине"
      - "вследствие"
      - "таким образом"
      - "следовательно"
  - mortuary_formals:
      - "ушли на найм"
      - "дотянуть до"
      - "достичь результата"
      - "реализовать себя"
      - "обрести опыт"
      - "принять решение"
      - "осуществить переход"
      - "совершить покупку"
  - double_emphasis_patterns:
      - regex: "(прямо сейчас|сейчас|сегодня),\\s+(каждый день|постоянно|регулярно|всегда)"
      - regex: "(всегда|везде|всюду),\\s+(всегда|везде|всюду)"
```

---

## Раздел 6 - Итог

**22 из 22 constructions пропустились всеми существующими gates.** 0 caught.

**Главные причины:**

1. **Structural gap** - существующие gates сканируют фразы (semantic classes A-Z = fragment-level), но не структуру (passive ratio, participle frequency, sentence length, subject consistency).
2. **Narrow banned list** - banned list для англицизмов слишком специфичный (7 items от автора), не покрывает корпоративный AI-default лексикон.
3. **Soft enforcement в Editor Pass** - 4.2.5 mentions passive / redundancy в списке, но без quantitative thresholds, поэтому findings ≤ 2 → PASS даже когда passive constructions есть.
4. **Self-discovery 3.46 не enforced** - qualitative review без structured checklist легко skip'ается.
5. **Subject naming MISSING** - нет правила про живое именование третьих лиц.
6. **Mortuary formals MISSING** - нет правила про biographical formal lexicon.
7. **Linker anti-list узкий** - 5 items, не покрывает formal explanatory linkers.
8. **Participle phrases MISSING** - нет правила вообще.

**Решение в v2.0:**

- Новый **Sub-stage 4.8 Structural Pass** с 7 quantitative / regex checks.
- Расширение **3.45** до A-AB (28 классов).
- Новые разделы **3.47-3.52** в _voice-TEMPLATE.md (subject / passive / participle / double emphasis / subordinate clauses / mortuary).
- Расширенный **lexicon_banned_hard** + **lexicon_banned_patterns** в config.md.
- Structured pre-output checklist в Pass 2.5 (8 yes/no вопросов по категориям) вместо generic Self-Discovery.

**Дата audit:** 2026-05-27
**Source:** прогон v3.1 поста через все существующие gates вручную
**Прецедент:** автор «пиздец, роботизированный» по решению автора
