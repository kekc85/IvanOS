# Hook patterns 8 - Viral hook library 2026

Первые 1.5-3 sec = 71-90% distribution. 8 проверенных hook patterns под video. Грузится в 02-finalize.md (выбор archetype) и 04-write.md (генерация hook текста).

## Pattern 1: Timeframe + outcome (Riley Brown signature)

**Структура:** «[Действие] за [tiny window]» с конкретным числом.

**Когда работает:** Demo / build-with-me / before-after / transformation.

**Примеры:**
- «Собрал лендинг за 11 минут»
- «Запилил Telegram-бот за вечер»
- «Поднял app за 40 минут с нуля»
- «Built this in 3 days while my friends slept»

**Iвана-specific:**
- «Контент-завод собрал за выходные»
- «Воронка вайбмаркетинга за 2 часа»
- «Vibe-coded SaaS за 90 минут»

**Production-fit:** screen-record-face-cam, before-after, ai-avatar-news.

## Pattern 2: Demo-first (no intro)

**Структура:** Tool уже работает в кадре, voiceover поверх. Никакого приветствия.

**Когда работает:** Tool reveal / screen-share / live demo.

**Примеры:**
- (на экране уже Claude генерит код) «Смотри - это Claude. Один промпт. Готовый бот»
- (Cursor с заполняющимся файлом) «Я просто говорю что хочу. Он пишет»

**Iвана-specific:**
- (Claude Code в терминале) «Один промпт. Тут уже три файла»
- (Lovable рендер) «Я ничего не дизайнил. Это AI»

**Production-fit:** screen-record-face-cam, split-screen-trend-jack.

## Pattern 3: Live-build challenge

**Структура:** «Я соберу [X] за [N min]. Timer starts now.»

**Когда работает:** Build-with-me с явным timer / челлендж формат.

**Примеры:**
- «Соберу AI-voice agent за 10 минут. Поехали»
- «Lendinг за 5 минут с одного промпта. Засекаем»

**Iвана-specific:**
- «Контент-завод с нуля за 60 минут. Стартуем»
- «Воронка для запуска за вечер. Иду»

**Production-fit:** screen-record-face-cam, before-after.

## Pattern 4: Tool reveal flex

**Структура:** «Эта новая AI-тула просто [replaced] [task]»

**Когда работает:** Release / new feature / breakthrough capability.

**Примеры:**
- «Эта новая Claude фича делает 6 разработчиков лишними»
- «Sora 2 просто убила traditional motion-design»
- «This AI tool just made my whole team obsolete»

**Iвана-specific:**
- «Claude Code просто закрыл всех агентурщиков»
- «Этот промпт - что 3 курса по AI»
- «HeyGen avatar V - конец традиционного видеопроизводства»

**Production-fit:** ai-avatar-news, screen-record-face-cam, split-screen-trend-jack.

## Pattern 5: Before/After visual

**Структура:** В первую sec - split screen: ugly «before» и polished «after». Hook caption поверх.

**Когда работает:** Transformation / rebuild / makeover.

**Примеры:**
- «Я переписал этот $50K сайт за 11 минут» + split-screen old vs new
- «Old pitch vs my AI rebuild» split
- «До Claude / После Claude» split

**Iвана-specific:**
- «Воронка которая давала 1% → 14%»
- «Контент-завод до Claude и после»
- «Один файл промптов vs 5 SaaS подписок»

**Production-fit:** before-after (нативный formit), split-screen-trend-jack.

## Pattern 6: Contrarian

**Структура:** Установленное мнение → его опровержение автором.

**Когда работает:** Spike take / opinion / breaking convention.

**Примеры:**
- «Все говорят: учи код. Я говорю: учи промпты»
- «N8n умирает. Вот что вместо»
- «Конструкторы конструкторов конструкторов больше не нужны»
- «Курсы не работают. Вот что работает»

**Iвана-specific:**
- «Все ходят в курсы. А я просто пишу промпты»
- «Маркетологи фотошопят. Я генерирую»
- «Продюсерская модель умерла. Не заметили?»

**Production-fit:** ai-avatar-news, screen-record-face-cam, split-screen-trend-jack.

## Pattern 7: Curiosity gap

**Структура:** «Есть [X]. Но никто не использует [секретный механизм]»

**Когда работает:** Method / framework / hidden technique reveal.

**Примеры:**
- «Все знают Claude. Но не используют 1 фичу»
- «Промптинг есть у всех. Воспроизводимость - у одного из ста»
- «Контент-завод - у каждого. Эффективный - у меня»

**Iвана-specific:**
- «Все запускают курсы. А вот в чём фокус который никто не делает»
- «9 из 10 не используют эту функцию Claude»

**Production-fit:** ai-avatar-news, screen-record-face-cam.

## Pattern 8: Numbered / list (ranked or count)

**Структура:** «N способов / правил / штук про X». Каждый next beat = numbered.

**Когда работает:** Listicle / framework breakdown / methodology in chunks.

**Примеры:**
- «3 промпта которые я гоняю каждый день»
- «5 правил вайбкодинга»
- «7 фишек контент-завода»

**Iвана-specific:**
- «3 промпта для скрипта видео за минуту»
- «4 трека мини-продукта»
- «5 ошибок вайбкодеров новичков»

**Note:** Memory `feedback_no_generic_ai_artifacts` - но это про артефакты-обещания типа «100 промптов в подарок». В hook это OK, потому что numbered hook - рабочий algorithm-friendly pattern.

**Production-fit:** ai-avatar-news, screen-record-face-cam.

## Matrix: archetype × pattern fit

| Voice Register | Best pattern fit |
|---|---|
| Magician (трансформация) | 1, 2, 5 |
| Sage (мудрость / метод) | 7, 8 |
| Outlaw (бунтарь / contrarian) | 4, 6 |

## Hook strength tests (для 05-review.md)

Каждый hook проходит 3 теста:

1. **Conflict / contradiction / visual contrast / numeric outlier** - присутствует?
   - Pattern 1: numeric outlier (cheap timeframe + big result)
   - Pattern 2: visual contrast (tool already showing instead of intro)
   - Pattern 3: timer urgency
   - Pattern 4: contradiction (new tool vs status quo)
   - Pattern 5: visual contrast (split)
   - Pattern 6: contradiction (common opinion vs авторское)
   - Pattern 7: gap (everyone vs few)
   - Pattern 8: numbered specificity

2. **Value proposition понятна без контекста** - да?

3. **Первые 3 sec кончаются на cliff / question / promise** - да?

Если любой test FAIL - переписать hook (max 3 ретрая).

## Mode C special: replication

В Mode C (card.md → script) hook archetype определяется ОРИГИНАЛОМ:
- Original hook = Timeframe → use Pattern 1
- Original hook = Contrarian → use Pattern 6
- etc.

Это replication mantra: «копировать механику, переписывать содержание». Не «улучшать» hook оригинала на свой вкус.
