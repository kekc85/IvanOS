# Maxwell Ross 9-Item Pre-Publish Checklist

## Source
- Автор: Maxwell Ross (классический direct-response копирайтер, 1960-70-е)
- Виральный re-discovery: Sieva Kozinsky, LinkedIn 2024
- URL: https://www.linkedin.com/posts/skozinsky_i-found-this-incredible-copywriting-checklist-activity-7157734144632905728-z71V
- Цитата Sieva (verbatim): *"The ability to send a compelling, short message to elicit a response from a stranger is a world class skill. It's a learnable skill that takes some guidance and lots of practice, so anyone can do it."*

## Применение
Mandatory gate в `workflow/04-review.md` перед output поста. Skill ОБЯЗАН автоматически прогонять каждый драфт через 9 yes/no вопросов. Минимум 8/9 PASS (пункт 9 не применим к non-sales постам) - иначе iteration. 3 use cases (per Ross): (1) Quick evaluation новой copy; (2) Re-ordering existing pieces by quality; (3) Overcoming inertia в writing process.

## Чек-лист (verbatim 9 пунктов)

### 1. Lead step-with-reader
**Question (EN verbatim):** "Does the lead sentence get in step with your reader at once?"
**RU:** Первая строка совпадает с интересом / болью читателя сразу?
**PASS:** Hook бьёт по конкретной боли / интересу аудитории. Примеры из gold-standard автора:
- «🆘 Завтра Telegрам может быть заблокирован!» (Пост 2195) - общая тревога рынка, попадает в страх блокировки
- «💰Ученик ищет сотрудников в свой ИИ контент-завод с оплатой до [твоя цифра]/мес» (2199) - деньги + работа = первичный интерес
- «У меня все деды воевали» (2295) - общечеловеческое, попадает в эмоциональный пласт сразу
**FAIL:** «Я хочу рассказать…» / «Сегодня мы поговорим о…» / vague generalities / «things you want» (per Ross)
**Auto-detect:** regex `^(Я хочу|Сегодня я|Хочу поделиться|Сегодня мы)` → fail

### 2. Lead length ≤ 2 lines
**Question (EN verbatim):** "Is your lead sentence more than two lines long?"
**RU:** Первое предложение / абзац короче 2 строк?
**PASS:** Lead = 1-2 строки, preview-zone TG-уведомления хватает. Best letters (per Ross) = one-or-two-line opening ideas. Примеры:
- «Как я вышел на такой результат на самом деле» (2227) - 7 слов
- «У меня все деды воевали» (2295) - 5 слов
- «📍 УНИКАЛИЗАТОР РОЛИКОВ + ВЫХОД ИЗ БАНА» (2293) - заголовок на одну строку
**FAIL:** Lead >180 символов или >2 строки. Tester: TG preview-уведомление обрезает long lead → читатель не дочитывает до hook.
**Auto-detect:** count chars первой строки / abzac, `lead_chars > 180` → fail

### 3. Opening promises benefit
**Question (EN verbatim):** "Do your opening paragraphs promise a benefit to the reader?"
**RU:** Открывающие абзацы обещают конкретную выгоду читателю?
**PASS:** В первом или втором абзаце - explicit benefit. Lead с most important benefit. Примеры:
- «Поездка к морю или плюс 25.000 подписчиков за 3 дня через ИИ контент-завод» (2186) - benefit «25.000 подписчиков за 3 дня» в headline
- «Разбор монетизации на [твоя цифра] в месяц на ИИ-блогере» (2314) - benefit «как заработать $100K/мес»
- «Я решил, что хочу помочь рынку пройти эту временную, но общую проблему» (2293) - benefit «выход из бана»
**FAIL:** Open описывает контекст / автора / процесс без обещания читателю.
**Auto-detect:** manual review - есть ли конкретное «ты получишь» / «вы сможете» / результат / решение проблемы в первых 200 символах.

### 4. Biggest gun first
**Question (EN verbatim):** "Have you fired your biggest gun first?"
**RU:** Самый сильный аргумент / результат / цифра поставлен в начало?
**PASS:** Сильнейший proof / claim / число - в первых строках, не в финале. Emphasize how offering brings pleasure / saves money / improves quality of life. Примеры:
- «100 тыс за 40 минут» - цифра в первой строке
- «Меня уволили со СВОЕГО контент-завода…» (2231) - paradox-hook самый сильный, в заголовке
- «+330 000 охватов с высокой конверсией в подписку» - цифра-якорь в lead
**FAIL:** Strong number / claim спрятан в P.S. или последнем абзаце. «У меня тут такая статья, в конце поделюсь цифрой…» - отложенная пуля.
**Auto-detect:** есть ли цифра / metric / claim в первых 30% длины поста; если только в последних 30% → flag.

### 5. Big idea
**Question (EN verbatim):** "Is there a big idea behind your letter?"
**RU:** Есть один главный смысл поста (single idea)?
**PASS:** Single-idea принцип (Bush + Cole atomic essay). Один пост = одна мысль. Distinguish core concept от introductory offer. Примеры:
- 2305 «5 сдвигов на рынке ИИ» - big idea «рынок поменялся, статья даст ответ»
- 2295 «Деды воевали» - big idea «жертва прошлого = долг ломать трудности»
- 2231 «Меня уволили со СВОЕГО контент-завода» - big idea «Claude автоматизировал всё»
**FAIL:** «Кстати, ещё…» / два разных смысла в одном посте / пост про X и про Y одновременно.
**Auto-detect:** считать «И ещё», «А кстати», «Между прочим» >0 → flag «возможно две идеи»

### 6. Logical order
**Question (EN verbatim):** "Are your thoughts arranged in a logical order?"
**RU:** Структура поста: hook → setup → reveal → application?
**PASS:** Guide reader smoothly через argument. Логика: проблема → причина → решение → действие. Или: hook → context → 3-act story → CTA. Примеры:
- 2195 (Telegram block): тревога → СМИ → личная верификация → план 1/2/3 → сопоставление притока и потерь в цифрах → разворот → CTA (в исходнике 2195 этот такт шёл образом «дырка в ванной»; такт работает сопоставлением двух потоков, не картинкой - канон п.49, замены в `references/metaphor-to-literal.md`)
- 2314 ($100K): money-headline → дисклеймер → 3 пронумерованных секции → FAQ → бинарный fork → reaction-vote
**FAIL:** Скачет между темами / финал не связан с заходом / CTA не следует из тела.
**Auto-detect:** manual review - пройти пост абзац-за-абзацем, проверить логическую связь «потому что» / «поэтому» между ними.

### 7. Believable
**Question (EN verbatim):** "Is what you say believable?"
**RU:** Что говоришь - звучит правдоподобно? Есть proof?
**PASS:** Use proof + testimonials. Конкретные цифры (не «много», а «25 000»), личные experiences, конкретные имена / даты / места. Примеры:
- «У меня в <город> он уже не работает ночью даже с VPN, в центре Москвы с мобильного интернета также ничего не работает» (2195) - personal verification
- «20+ аккаунтов по РФ» (2186) - конкретное число
- «Я провёл уже 3 шикарнейших дня в пригородах Геленджика» (2186) - конкретная локация + срок
- «*ученик по зарубежке не разрешил показывать полный никнейм аккаунта» (2314) - disclaimer создаёт trust через mystery
**FAIL:** Круглые цифры (1000 / 10000 / 100К без объяснения) / абстракции «все» / «всегда» / claim без proof. Memory правило: «Не выдумывать факты» - без proof число = fail.
**Auto-detect:** flag круглых чисел без context (`\b(100|1000|10000|100000|1000000)\b` без рядом «примерно», «около», конкретного дня).

### 8. Clear CTA
**Question (EN verbatim):** "Is it clear how the reader is to order – and did you ask for the order?"
**RU:** Есть конкретное действие в конце? Прямо попросили его?
**PASS:** Explicit CTA. Может быть:
- Hard: «Запись на <твоё событие> по ссылке» (sales)
- Mini: «Сохрани этот пост» / «Ставь 🔥» (engagement)
- Soft: «Что думаешь? напиши» (comment)
- Linker: «Завтра разберём X, не пропусти» (retention)
Примеры из gold-standard:
- «👉🏻 Успеть забрать место и окунуться в вайбкодинг» (2228) - hard sales
- «PS делитесь с товарищами» (2293) - share-CTA
- «🔥/⚡️» dual-reaction vote (2314) - engagement poll
**FAIL:** Пост заканчивается без чёткого действия / читатель не знает что делать дальше / 2 CTA одновременно (sales + share) → reader confused.
**Auto-detect:** в последних 200 символах поста должно быть minimum один из: ссылка (`http`, `t.me`, `👉🏻`, `->`), reaction-call (`🔥`, `❤️`, `ставь`), action verb (`сохрани`, `делись`, `пиши`, `забери`).

### 9. Tie with order form / next step
**Question (EN verbatim):** "Does the copy tie in with the order form – and have you directed attention to the order form?"
**RU:** CTA связан с содержанием поста? Внимание направлено на форму / следующий шаг?
**PASS:** ТОЛЬКО для sales / launch постов. CTA должен быть смыслово связан с темой поста. Пример мастерского pivot: «деды воевали → я обязан ломать трудности → а вот мой скромный вклад в нашу борьбу против алгоритмов и блокировок -> здесь» (2295) - слово «борьба» переходит из патриотического narrative в анти-бан tool. Pivot встроен в логику, не разрушает narrative.
**FAIL:** CTA торчит, не связан с темой поста («Кстати, у меня курс. Покупай.»). Vendor-style P.S. без mostro связи.
**Применимость:** Пункт 9 = только sales-постов. Для personal / story / build-in-public постов = N/A, можно skip.
**Auto-detect:** flag если CTA-ссылка ведёт на лендинг продукта, а в теле поста продукт не упомянут / не отрабатывается соответствующая боль.

## Применение в workflow

Skill `post` запускает 9-item check как **mandatory pre-publish gate** в `04-review.md`:
1. Каждый пункт прогоняется как yes/no.
2. Минимум 8/9 PASS (для non-sales - 7/8 без п.9).
3. На FAIL: skill автоматически переписывает соответствующую часть поста + повторно прогоняет.
4. Финальный отчёт: список PASS / FAIL с правками.

3 sub-режима применения:
- `/check` - eval одного драфта против 9 пунктов
- `/rank` - ранжирование нескольких драфтов по числу passes
- `/start` - overcoming inertia: пройти пункты как чек-лист в обратную сторону (от 9 к 1), используя их как brainstorm-prompt

## Sources
- https://www.linkedin.com/posts/skozinsky_i-found-this-incredible-copywriting-checklist-activity-7157734144632905728-z71V
- Historical: Maxwell Ross direct-response copywriting (1960s-70s)
