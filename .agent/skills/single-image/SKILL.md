---
name: single-image
version: "1.2"
created: 2026-05-28
last_reviewed: 2026-05-28
description: Контент-машина для одиночной картинки-поста (X / LinkedIn / Нельзяграм / TG). End-to-end до rendered PNG через chain на higgsfield-generate gpt_image_2 (cost-aware - требует апрув автора). Output - visual brief + bilingual caption (RU + EN) + опционально rendered image. Portable через config.md. 3 режима (Plan из Карты смыслов / Spark ситуативный / Transcript из надиктовки) × 2 subject (автор / ученик с onboarding) × 5 типов (concept-diagram / dashboard-screenshot / meme / quote-card / before-after). Workflow router → mode → finalize → design-brief → caption → review (mandatory render+visual gate + 6-Pass + Maxwell Ross 9 + 3 слоя + no-caption test) → output + A/B + cost-aware render decision. Triggers /single-image, "сделай картинку про X", "визуализируй X", "пост-картинка", "дай идеи картинок". Флаги --auto-render / --no-render.
---

# single-image - Portable контент-машина одиночной картинки-поста

> Skill производит готовый visual brief + caption для одиночной картинки-поста. Аналог `post` по архитектуре, но output - не текст, а спецификация картинки. Закрывает image-first ветку контент-фабрики. Bilingual RU + EN из коробки.

## Архитектура

Скилл portable: один и тот же код работает у автора и у учеников курса. Различие - только в `config.md` и данных проекта.

**Три ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (Карта смыслов) / Spark-B1 (идея пользователя) / Spark-B2 (генерация под JTBD) / Transcript (надиктовка) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |
| **Type** (что за картинка) | concept-diagram / dashboard-screenshot / meme / quote-card / before-after |

**Router** в `workflow/01-router.md` auto-detect'ит mode по сигналам input. Override через флаги `--plan` / `--spark` / `--transcript` / `--type=<type>` / `--platform=<X|LI|IG|TG>`.

**Onboarding** для нового пользователя - `workflow/00-onboarding-student.md`. Срабатывает при отсутствии или неполном `config.md`.

## Когда применять

Триггеры (auto-detect mode в router):

| User input | Mode | Что делает |
|---|---|---|
| `/single-image` без аргументов | Plan | Берёт смысл дня из Карты смыслов запуска |
| «по плану», «смысл дня», дата | Plan | То же |
| `/single-image про X`, «сделай картинку про X», «визуализируй X», «framework X» | Spark-B1 | Расширяет тему X в 5-7 визуальных углов |
| «дай идеи картинок», «что визуализировать сегодня» | Spark-B2 | Генерит 5-7 идей под JTBD/avatar |
| Длинный текст (>500 знаков) с пометкой «для картинки» | Transcript | Извлекает 3-10 атомарных смыслов, выбираешь top-1-3 |

**Не применять** для:
- Текст поста без картинки → `post` / `paips-post` / `spiky-one-liner` / `longform`
- 2+ кадров / слайдов → future `carousel` skill
- Видео → `replicate-reel` / `video` / `produce-reel` / `screen-record-face-cam`
- Marketplace product cards → `higgsfield-marketplace-cards`
- Brand product photoshoot → `higgsfield-product-photoshoot`
- Сама генерация картинки → `higgsfield-generate` (single-image даёт brief + ready prompt, higgsfield исполняет)

## Workflow (progressive disclosure)

При вызове skill последовательно грузит соответствующие `workflow/` файлы:

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

01-router.md                  ← detect mode + subject + load config
   ├─ 01a-plan.md             ← Mode A: из Карты смыслов
   ├─ 01b-spark.md            ← Mode B1/B2: ситуативный
   └─ 01c-transcript.md       ← Mode C: из надиктовки
       ↓
02-finalize.md                ← выбор type + reference + platform + aspect
03-design-brief.md            ← композиция / verbatim text on image / палитра / tool prompt
04-caption.md                 ← RU + EN draft (3 hook patterns на язык)
05-review.md                  ← 6-Pass + Maxwell Ross + 3 слоя + no-caption test + anti-stock
06-output.md                  ← brief + bilingual caption + production notes + A/B 2 варианта
```

**Файлы:**

| Файл | Назначение |
|---|---|
| `workflow/00-onboarding-student.md` | First run для ученика. Создаёт config.md через 9 вопросов |
| `workflow/01-router.md` | Auto-detect mode (Plan / Spark / Transcript) и subject |
| `workflow/01a-plan.md` | Mode A: читает Карту смыслов по дате |
| `workflow/01b-spark.md` | Mode B1: расширение идеи в визуальные углы / Mode B2: генерация под JTBD |
| `workflow/01c-transcript.md` | Mode C: разбор надиктовки в атомарные визуальные смыслы |
| `workflow/02-finalize.md` | Выбор type (1 из 5) + reference creator + платформа + aspect |
| `workflow/03-design-brief.md` | Композиция + verbatim text on image + палитра + tool prompt |
| `workflow/04-caption.md` | RU + EN draft, 3 hook patterns на язык |
| `workflow/05-review.md` | 6-Pass + Maxwell Ross 9 + 3 слоя + no-caption test + anti-stock |
| `workflow/06-output.md` | Финальный output + production notes + A/B |

## 5 типов картинок (templates)

| # | Тип | Reference creator | Применение |
|---|---|---|---|
| 1 | **concept-diagram** | Jack Butcher (Visualize Value) | Mental model / framework / spectrum / 2x2 / equation. Поглощает `visual-concept-square` |
| 2 | **dashboard-screenshot** | Pieter Levels / Marc Lou | Real metric reveal (только verified data). Поглощает `stripe-screenshot-post` |
| 3 | **meme** | Distillery / meme культура | Cultural reference + topic twist. Hook через узнавание |
| 4 | **quote-card** | Naval / Hormozi | Цитата + author + minimal design. Bookmark-bait |
| 5 | **before-after** | Pat Walls / transformation visuals | Split: было X → стало Y. Статичный (не video reel) |

**v1.0:** все 5 типов покрывают ~85% image-first контента.
**v1.1+ planned:** annotated-screenshot / side-by-side-comparison / big-number-card.

## Knowledge base (knowledge/)

Грузятся по нужде через progressive disclosure:

- `knowledge/visual-types.md` - 5 типов детально (когда применять / структура / common mistakes / fail modes)
- `knowledge/reference-creators.md` - 8-12 reference creators с тем что копируем, что НЕ
- `knowledge/composition-principles.md` - иерархия / контраст / читаемость с расстояния / стоп-скролл first 0.5s / правило 60-30-10 / aspect ratios per platform
- `knowledge/anti-patterns.md` - generic AI aesthetics / стоковость / cluttered / 8+ elements / выдуманные numbers / negative статистики / hyperbolic caption

## Examples

- `examples/_TEMPLATE.md` - 5 curated примеров (по 1 на тип) под бренд автора
- `examples/track-record-single-image.md` - история применений + catch_rate metric

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/05-review.md`):**
- Em-dash «-» внутри строк → fail
- «Instagram» → auto-correct в «Нельзяграм»
- Banned англицизмы из `config.lexicon_banned_hard` → fail
- Выдуманные numbers если type=dashboard-screenshot → fail (verify через `.business/` или explicit user-provided)
- Negative статистики в публичном caption → fail
- >1 восклицательного знака в caption → warning
- Длина caption > platform target → fail

**No-caption test (специфичный для single-image):**
- Убери caption полностью. Картинка ещё несёт смысл? Если нет - править brief, чтобы картинка работала stand-alone.

**Anti-stock test:**
- Есть ли ощущение что это generic stock или AI-cliché (soft gradients / glossy 3D / абстрактные shapes без identity)? Если да - переписать brief.

**6-Pass Refinement (LLM):**
Skeptic / Expert / Scroller / Competitor / Editor / Thumbnail - адаптировано для visual content.

**Maxwell Ross 9-Item Checklist:**
9 yes/no вопросов pre-publish (адаптировано под image+caption pair).

**3 слоя финальный gate:**
- Слой 1 валидаторы (regex)
- Слой 2 4 концепции (Pre-mortem / 90% calibration / Multi-perspective / Adaptive)
- Слой 3 7 контуров (Context / Соответствие / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность)

## Принципы

1. **Картинка > caption.** Визуал несёт 80% смысла. Caption поддерживает, не дублирует.
2. **Verbatim text on image.** Точный текст что будет нарисован указывается дословно в brief, не пересказом.
3. **Reference creator first.** Каждый тип имеет authoritative reference. Копируем структуру, адаптируем смысл - не reinventing.
4. **No generic AI aesthetics.** Avoid soft gradients / glossy 3D / generic minimalism без identity автора.
5. **No-caption test mandatory.** Каждый brief проходит тест: убери caption - картинка работает stand-alone? Если нет - править.
6. **Real data only для dashboard-screenshot.** Выдуманные numbers = brand suicide. Verify через `.business/` или явное согласие пользователя.
7. **Bilingual caption всегда.** RU + EN параллельно. Автор выбирает что публикует. Не дословный перевод - культурная адаптация.
8. **Portable by config.** Один скилл - множество авторов через `config.md`. Никаких hardcoded paths.
9. **MECE с остальной фабрикой.** single-image НЕ генерит сам пост, только brief + caption. Chain с `post` / `higgsfield-generate`.
10. **3 слоя проверки финальный gate.** Перед output обязательное явное подтверждение «3 слоя пройдено».
11. **Каждая правка = системная.** Любая обратная связь от автора закрывается на ДВУХ уровнях: точечный fix + системная правка в скилле (config / workflow / review gate / memory / SKILL.md). См. `[[feedback-each-correction-becomes-system-rule]]`.

## Portability - для ученика курса

Ученик клонирует папку `~/.claude/skills/single-image/` в свою машину и заменяет ТОЛЬКО:

1. **`config.md`** - пути и lexicon под свой проект (onboarding делает это за него при первом запуске).
2. **`examples/gold-standard-<your-name>.md`** - свои лучшие visual posts.
3. **`intake/`** (или `.business/`) - `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`. По путям из config.

Что НЕ трогаем:
- `workflow/*` - общая методология
- `knowledge/*` - reference creators / composition / anti-patterns одинаковы
- `templates/*` - 5 типов одинаковы

Это делает скилл **product курса**: ученики курса вайбмаркетинга получают тот же инструмент.

## Anti-patterns

См. `knowledge/anti-patterns.md`. Ключевые:

- **Generic AI aesthetics** (soft pastel gradients / glossy 3D / абстрактные shapes без identity)
- **Stock photos** маскирующие отсутствие идеи
- **8+ elements** в одной композиции (overwhelmed audience)
- **Color-heavy** где должен быть minimalist (тип-зависимо)
- **Long explanatory captions** (image является hook, caption поддерживает)
- **Выдуманные numbers** в dashboard-screenshot (instant credibility kill)
- **Negative статистики** в публичном («20% доходят» убивает продажи)
- **Hyperbolic captions** («life-changing!», «mind-blown»)
- **Hyped buzzwords** в text on image (AI / hustle / grind / 10x)
- **Имена конкурентов** в visual или caption
- **Cluttered**: >3 visual layers без иерархии
- **Низкий контраст** между фоном и текстом
- **Шрифт-каша**: >2 семейств шрифтов в одной композиции

## Memory cross-refs

- `[[feedback-no-em-dash]]` - em-dash «-» внутри строк запрещён
- `[[feedback-no-tech-jargon-no-anglicisms]]` - без жаргона / англицизмов в caption
- `[[feedback-no-negative-stats-in-public-offer]]` - без негативных статистик
- `[[feedback-no-inventing-facts]]` - dashboard-screenshot только verified numbers
- `[[feedback-no-attacking-competitors-by-name]]` - враг = явление, не имя
- `[[feedback-no-generic-ai-artifacts]]` - generic = брак
- `[[feedback-images-from-icp-world]]` - образы из мира аватара, не AI/кода
- `[[feedback-always-open-artifacts]]` - готовый visual brief открывать через `open`
- `[[feedback-each-correction-becomes-system-rule]]` - правки идут на двух уровнях
- `[[post]]` - chain: post → single-image (если пост нуждается в картинке)
- `[[higgsfield-generate]]` - chain: single-image → higgsfield-generate (для AI-execution)
- `[[higgsfield-product-photoshoot]]` - параллельный skill для brand product visuals
- `[[visual-concept-square]]` - DEPRECATED, заменён на type=concept-diagram
- `[[stripe-screenshot-post]]` - DEPRECATED, заменён на type=dashboard-screenshot

## Версия

**Текущая:** 1.2 (2026-05-28) - **Cost ladder: FREE first, PAID only with approval**.
- Templates `concept-diagram.md`: переставлен приоритет - HTML+Playwright (FREE) PRIMARY, Figma + Photopea SECONDARY/TERTIARY (FREE), higgsfield/MJ только PAID OPTION с явным апрувом
- Workflow `05-review.md` Pass 0: render strategy теперь FREE first (HTML+Playwright validated по решению автора), paid only if author explicitly says «генери через AI»
- Workflow `06-output.md` Step 1: decision tree переписан - default FREE path, paid требует ASK «Запустить higgsfield (~$0.10-0.20)? Y/N» только если автор сам спросил AI
- Прецедент по решению автора: запустил higgsfield-generate без апрува, сжёг credit автора → правило `[[feedback-free-tools-first-for-images]]`

**v1.1 (2026-05-28)** - End-to-end render chain + mandatory visual review gate.
- Workflow `05-review.md` Pass 0: MANDATORY render + visual review BEFORE Pass 1+ (блокирует false positive «PASS на brief без картинки»)
- Workflow `06-output.md` Step 1: cost-aware render decision tree (auto-render с --auto-render flag / ask апрув / no-render)
- Workflow `06-output.md` Step 2: mandatory visual review после render
- Templates `concept-diagram.md`: primary tool = `higgsfield-generate gpt_image_2` (validated по решению автора на тесте - output editorial-feel, выделяется в feed), Figma + HTML+Playwright = fallbacks
- Чёткий cost-aware принцип: higgsfield не запускается без явного апрува автора (тратит credits)
- Прецедент: тест по решению автора на iceberg показал что brief-only оценка = false positive, нужен render

**v1.0 (2026-05-28)** - Initial release. 5 типов (concept-diagram / dashboard-screenshot / meme / quote-card / before-after), 3 режима (Plan / Spark / Transcript), 2 subject (автор / ученик), bilingual caption (RU + EN). Поглощает 2 устаревших skill (visual-concept-square, stripe-screenshot-post) как типы.

**SemVer правила:**
- MAJOR: breaking change в формате output или критериях fail
- MINOR: новый type / новый mode / новый knowledge файл
- PATCH: уточнение правил валидации, новые reference creators, fix references

**Когда пересматривать:**
- catch_rate в track-record падает < 80%
- 3+ систематических промаха по типу или voice
- Новые ключевые findings от Butcher / Levels / Cheung (раз в квартал)
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации скилла под автора
- `plans/2026-05-28-single-image-skill-spec.md` - полная спецификация и план разработки
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
- `~/.claude/skills/post/` v1.2/v2.2 - source паттерна архитектуры (router / modes / portability / config)

## Empirical patterns layer (NEW 2026-05-28)

Этот skill интегрирован с shared empirical layer для всех content-skills.

**Mandatory Reads в Pass 0:**
- `~/.business/growth/extracted-patterns/INTEGRATION.md` - что читать для этого скилла
- `~/.business/growth/extracted-patterns/hook-patterns-empirical.md` - 9 patterns из 30 corpus
- `~/.business/growth/extracted-patterns/voice-markers-empirical.md` - Greg/Riley/Sabrina + авторская calibration
- `~/.business/growth/extracted-patterns/audience-glossary.md` - agent-jargon → язык RU ЦА
- `~/.business/growth/extracted-patterns/funnel-awareness.md` - куда ведёт content

**Benchmark Gate** в review stage:
- Compare output vs nearest 3 examples из `benchmark-corpus-index.md`
- Score /6 для text-only OR /7 для visual
- Cutoff: 4+/6 (text) | 5+/7 (visual) = PASS

Root cause fix: до 2026-05-28 references зашивали теорию виральности из памяти. Shared layer = empirical extraction из 30 real viral шортов в авторской нише.

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

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.

---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.

---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
