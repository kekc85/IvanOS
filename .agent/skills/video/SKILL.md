---
name: video
version: "1.0"
created: 2026-05-28
last_reviewed: 2026-05-28
description: Контент-машина для видео автора (автор или ученик курса). Производит СКРИПТ (текст что произносится) + headline + production handoff brief. Длительность 15 сек - 60 мин (Shorts/Reels/TikTok vs YouTube long-form). RU + EN. Portable by config.md. 4 режима (Plan / Spark / Replication из card.md / Transcript из надиктовки) × 5 length tiers. Review = 6-Pass + Maxwell Ross 9 + 3 слоя + Hook Strength Gate. Production-варианты (face-cam / split-screen / AI-avatar / replicate / cut) = downstream skills. Triggers /video, "напиши скрипт видео", "сделай скрипт ролика", "сценарий шорта", replicate <id>, надиктовки >500 знаков для видео.
---

# video - Portable script-движок контент-завода

> Skill производит ГОТОВЫЙ СКРИПТ видео в голосе автора + structural brief для downstream production skill. Не делает production (запись / split / avatar / Remotion render) - это handoff.

## Архитектура

Skill portable: один и тот же код работает у автора и у учеников курса вайбмаркетинга. Различие - `config.md` и данные проекта.

**Три ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (Карта смыслов) / Spark-B1 (идея пользователя) / Spark-B2 (генерация под JTBD) / Replication (card.md из ingest-reel) / Transcript (надиктовка) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |
| **Length tier** | short-15-30s / short-30-60s / short-60-180s / mid-3-10min / long-10-60min |

**Router** в `workflow/01-router.md` auto-detect'ит mode + lang (RU/EN) + length tier по сигналам в input. Override через флаги `--plan` / `--spark` / `--replicate <id>` / `--transcript` / `--lang ru|en` / `--length <tier>`.

**Onboarding** для нового пользователя - v1.1 (см. Roadmap). В v1.0 только автор (paths hardcoded в config.md).

## Когда применять

Триггеры (auto-detect mode в router):

| User input | Mode | Length tier | Что делает |
|---|---|---|---|
| `/video` без аргументов | Plan | auto (default 30-60s) | Берёт смысл дня из Карты смыслов запуска |
| «по плану», «смысл дня», дата + «видео» | Plan | auto | То же |
| `/video про X` / «напиши скрипт про X» | Spark-B1 | auto | Расширяет тему X в 5-7 углов, выбираешь |
| «дай идеи на видосы» / «что снять сегодня» | Spark-B2 | auto | Генерит 5-7 идей под JTBD/avatar, выбираешь |
| `/video replicate <id>` / «такое же» + `<ingest-id>` | Replication | from card.md | Script в голосе автора из чужого Reel |
| Длинный текст (>500 знаков), «надиктовал для видео» | Transcript | auto | Извлекает 3-10 атомарных смыслов, выбираешь top-1-3 |

**Не применять** для:
- Постов в TG → `post`
- Постов в X / Threads / LinkedIn → `paips-post` / `spiky-one-liner`
- Длинной статьи / эссе / newsletter → `longform`
- Email → `email`
- Бот-рассылок → `bot-message`
- Carousel / single-image / tweet → отдельные плоскости
- Производственной техники записи / edit / render → `screen-record-face-cam` / `split-screen-trend-jack` / `ai-avatar-news` / `before-after` / `cut-from-long-form` / `replicate-reel`
- 10 hook variants A/B → `hook-generator` (standalone)
- Cuts из готового long-form YouTube → `cut-from-long-form` (Reap MCP делает свою нарезку)

## Workflow (progressive disclosure)

```
01-router.md                          ← detect mode + lang + length tier + load config
   ├─ 01a-plan.md                     ← Mode A: из Карты смыслов
   ├─ 01b-spark.md                    ← Mode B1/B2: ситуативный
   ├─ 01c-replication.md              ← Mode C: card.md → script в voice
   └─ 01d-transcript.md               ← Mode D: надиктовка → script
       ↓
02-finalize.md                        ← length tier + hook archetype + lang lock + voice register
03-structure.md                       ← template по tier + headline + skeleton
04-write.md                           ← Mandatory Reads + Pass 1 draft + Pass 2 voice + Pass 2.5 Living Language
05-review.md                          ← 6-Pass + Maxwell Ross 9 + 3 слоя + Hook Strength Gate + Length Floor/Ceiling
06-output.md                          ← script + headline + production handoff brief
```

**Файлы:**

| Файл | Назначение |
|---|---|
| `workflow/01-router.md` | Auto-detect Mode + Lang + Length tier + Subject |
| `workflow/01a-plan.md` | Mode A: читает Карту смыслов по дате |
| `workflow/01b-spark.md` | Mode B1 expand / Mode B2 generate под JTBD |
| `workflow/01c-replication.md` | Mode C: extract из card.md (ingest-reel) → brief для 02 |
| `workflow/01d-transcript.md` | Mode D: парсит надиктовку в атомарные смыслы |
| `workflow/02-finalize.md` | Length tier choice + hook archetype + lang lock |
| `workflow/03-structure.md` | Загружает `templates/<tier>.md`, skeleton + headline |
| `workflow/04-write.md` | Pass 0 Mandatory Reads + Pass 1 draft + Pass 2 voice + Pass 2.5 Living Language |
| `workflow/05-review.md` | 6-Pass + Maxwell Ross 9 + 3 слоя + Hook Strength Gate + Length check |
| `workflow/06-output.md` | Финальный script + headline + production handoff brief |

## 5 length tiers (templates)

| # | Tier | Длительность | Платформы | Структура |
|---|---|---|---|---|
| 1 | short-15-30s | 15-30 сек | Reels / Shorts / TikTok | Hook (1.5-3s) → 1 beat → Payoff → optional CTA |
| 2 | short-30-60s | 30-60 сек | Reels / Shorts / TikTok | Hook → Setup → 2-3 beats → Payoff → CTA |
| 3 | short-60-180s | 60-180 сек | Reels max / Shorts max / TikTok | Hook → Promise → 3-5 beats → Payoff → CTA |
| 4 | mid-3-10min | 3-10 мин | YouTube mid | Hook → Promise → 5-7 chapters с mini-hooks → Synthesis → CTA |
| 5 | long-10-60min | 10-60 мин | YouTube long-form | Hook → Promise/Preview → 5-9 sections с mini-hooks → Synthesis → CTA (long-tier experimental в v1.0) |

## Production handoff map

После `06-output.md` skill выдаёт recommended downstream skill. автор (или orchestrator `produce-reel`) вызывает его дальше с готовым script + brief.

| Mode + length tier | Recommended downstream skill | Что передаётся |
|---|---|---|
| Any mode + short-15-30s/30-60s/60-180s, intent «снять самому» | `screen-record-face-cam` | script + hook visual brief + demo steps |
| Any mode + short, intent «trend-jack» | `split-screen-trend-jack` | script + top-half AI brief + bottom-half script |
| Any mode + short, intent «без записи / daily volume» | `ai-avatar-news` | script + B-roll brief + Kling shots list |
| Any mode + short, intent «before/after AI rebuild» | `before-after` | script + before footage brief + AI rebuild prompts |
| Mode Replication + short | `replicate-reel` | script + spec.captions[] + overlay timeline brief |
| Mid / long-form + intent «extract Shorts» (after publish) | `cut-from-long-form` (downstream of separate publish) | full script для long-form |
| Mid / long-form (script only) | manual / future `youtube-long-form-production` | script + chapter map + headline + thumbnail brief |

## Knowledge base (references/)

Все references грузятся по нужде через progressive disclosure:

- `references/_voice-TEMPLATE.md` - lexicon (Нельзяграм / вайбкодинг / контент-завод / Дубайск / перегнать / пдп) + anti-patterns + voice principles
- `references/_voice-TEMPLATE.md` - живые глаголы / обороты / 26 классов banned AI-конструкций + Self-Discovery Method
- `references/hook-patterns-8.md` - viral hook library 2026 (8 patterns: timeframe+outcome / demo-first / live-build / tool-reveal / before-after / contrarian / curiosity-gap / numbered)
- `references/structure-by-length.md` - 5 tiers × детальная структура с временными метками
- `references/maxwell-ross-9-checklist.md` - pre-publish gate (Idea / Clarity / Payoff / Specificity / Freshness / Hook / Length / Tone / CTA) - адаптировано для видео
- `references/6-pass-refinement.md` - Skeptic / Scroller / Producer / Editor / Algorithm / Voice - video-адаптировано
- `references/ai-tells-catalog.md` - 100+ AI tells (RU+EN)
- `references/ru-en-adaptation-rules.md` - RU vs EN structural differences (RU = история→вывод, EN = тезис→аргументы)
- `references/production-handoff-map.md` - детальный mapping → downstream skill + точный brief format
- `references/platform-specs.md` - YouTube long / YT Shorts / Reels / TikTok specs (длительности / aspects / captions / posting)

## Examples

- `examples/_TEMPLATE-shorts.md` - эталонные shorts автора (накапливается по факту)
- `examples/track-record-video.md` - история применений + catch_rate metric

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/05-review.md`):**
- Em-dash «-» внутри строк → fail (CRITICAL правило проекта)
- «Instagram» → auto-correct в «Нельзяграм»
- «Инстаграм» → auto-correct в «Нельзяграм»
- «контент-фабрика» / «контент-машина» → auto-correct в «контент-завод»
- «vibe coding» / «вайб-кодинг» → auto-correct в «вайбкодинг»
- Запретные термины («артефакт» / «digital-twin» / «Grand Slam Offer» / «КЭВ» / «фасилитация» / «связки») → fail
- Длительность скрипта > target tier ceiling → fail
- Длительность скрипта < target tier floor → fail
- Hook отсутствует в первые 1.5-3 sec → fail (Hook Strength Gate)
- Имя конкретного конкурента в позиции «враг» → fail
- Негативные статистики в публичной части («20% доходят» и т.п.) → fail
- «без опыта в коде» / «не программист» / «программирование» → fail (audience объекция = «не маркетолог»)

**6-Pass Refinement (LLM, video-адаптированный):**
Skeptic / Scroller (stop-scroll проверка) / Producer (производственная реализуемость) / Editor / Algorithm (платформенные сигналы) / Voice (автор-fidelity).

**Maxwell Ross 9-Item Checklist (video-адаптированный):**
9 yes/no вопросов pre-publish - Idea / Clarity / Payoff / Specificity / Freshness / Hook strength / Length fit / Tone / CTA. См. `references/maxwell-ross-9-checklist.md`.

**3 слоя финальный gate:**
- Слой 1 валидаторы (regex)
- Слой 2 4 концепции (Pre-mortem / 90% calibration / Multi-perspective Зритель-Алгоритм-автор / Adaptive)
- Слой 3 7 контуров (Context / Соответствие предпосылкам / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность)

**Hook Strength Gate (новое относительно post):**
Отдельный assert после 6-Pass - первые 1.5-3 sec проходят 3 теста (conflict/contradiction/visual contrast присутствует? value proposition понятна без контекста? первые 3 sec кончаются на cliff/question/promise?). Если хоть один FAIL - переписать hook (max 3 ретрая, потом эскалация to user).

## Принципы

1. **Portable by config.** Один и тот же скилл работает у автора и у ученика. Различие - только `config.md` и данные проекта. Никаких hardcoded paths в workflow/references/templates.
2. **Script-only output.** Skill делает script + structural brief, НЕ делает production. Production = downstream skill после handoff.
3. **Voice over format.** Стилистика автора важнее структуры. Если шаблон ломает голос - голос побеждает.
4. **Hook первые 1.5-3 sec = 71-90% distribution.** Hook Strength Gate не пропускает слабый хук.
5. **Single insight per video (для shorts).** Один шорт = один тезис. Multi-tезисные → split на серию или → mid/long tier.
6. **Action verbs > nouns.** «Промптишь - получаешь» сильнее «возможность получения».
7. **Concrete > abstract.** «За 11 минут» > «за пару часов». «Один файл с промптами» > «структурированная база знаний».
8. **Production handoff обязателен.** В output всегда recommended downstream skill + brief, даже если автор будет производить руками.
9. **Карта смыслов = source of truth для Mode A.** Не дополнять, не выдумывать. Пустая запись = fallback на Mode B2, не вымысел.
10. **Транскрипт в Mode D / Replication в Mode C - цитата, не парафраз.** Лексика автора важнее «причёсанной» формулировки.
11. **Mandatory reads перед draft.** В Pass 0 `04-write.md` обязательны три Read'а: gold-standard / ivan-voice / config. Без них Voice Fidelity Gate failit.
12. **Maxwell Ross 9-checklist gate.** Никакой script не выходит без 9/9 PASS.
13. **3 слоя проверки - финальный gate.** Перед output обязательное явное подтверждение.
14. **Каждая правка = системная.** Любая обратная связь от автора закрывается на двух уровнях: (1) точечный fix в текущем скрипте + (2) системная правка в скилле (config / workflow stage / review gate / memory / SKILL.md). См. `post` принцип 13.

## Portability - для ученика курса (v1.1)

В v1.0 paths захардкожены под автора. В v1.1 ученик клонирует `~/.claude/skills/video/` и заменяет ТОЛЬКО:

1. **`config.md`** - paths и lexicon под свой проект (onboarding это делает за него при первом запуске).
2. **`examples/gold-standard-<your-name>-shorts.md`** - свои лучшие shorts (5-10 штук).
3. **`intake/` или `.business/`** - `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`. По путям из config.

Что НЕ трогаем: `workflow/`, `references/`, `templates/` - общая методология.

Это делает скилл **product курса**: ученики курса вайбмаркетинга получают тот же script-движок, который автор использует ежедневно.

## Сосуществование с рендер-узлом в v1.0

> ПРИМЕЧАНИЕ 2026-06-10: рендер-узел `replicate-reel` [DEPRECATED] заменён на `replicate-viral` (Фаза 6). Упоминания replicate-reel ниже = читать как replicate-viral; production handoff brief идёт в него.


`replicate-reel` Шаг 4 сейчас inline переписывает script в голосе автора из card.md. После video v1.0 это дублирование. В v1.0 они сосуществуют:

- Прямой триггер `/video replicate <id>` → video skill Mode C → output script + production handoff brief к `replicate-reel`
- Триггер `/replicate <id>` или «replicate <id>» → `replicate-reel` skill (legacy) → inline script

В v1.1 - рефакторинг: `replicate-reel` Шаг 4 будет вызывать video skill в Mode C. До тех пор - оба пути валидны.

## Anti-patterns

См. `references/ai-tells-catalog.md` + `references/_voice-TEMPLATE.md`. Ключевые:

- Em-dash «-» внутри строк (memory правило)
- «Instagram» / «Инстаграм» вместо «Нельзяграм»
- Технический жаргон в публичной части
- Negативные статистики в публичном
- DM-only ценообразование
- «эксперт» как audience descriptor (сужает воронку)
- Метафоры если есть термин автора (Машина / Пекарня / Фабрика вместо вайбкодинга)
- Атака конкурента по имени (враг = явление)
- «Только Claude» / «чисто Claude» (правильно: «Claude в ядре, 90%»)
- «без опыта в коде» / «не программист» (audience объекция = «не маркетолог»)
- Pure AI rehash без contrarian / личной позиции
- Generic «10 хуков» / «100 промптов» артефакт-обещания
- Шаблоны без применения к конкретному продукту

## Memory cross-refs

- `[[feedback-no-em-dash]]` - em-dash запрещён внутри строк
- `[[feedback-no-tech-jargon-no-anglicisms]]` - без жаргона / англицизмов
- `[[feedback-no-negative-stats-in-public-offer]]` - без негативных статистик
- `[[feedback-verbatim-quote-transfer]]` - дословный перенос цитат, не пересказ
- `[[feedback-product-positioning-no-programmer]]` - не «программист», а «эксперт»
- `[[feedback-no-attacking-competitors-by_name]]` - враг = явление
- `[[feedback-claude-in-core-not-only]]` - «Claude в ядре, 90%»
- `[[feedback-audience-not-only-experts]]` - не сужать «эксперт»
- `[[feedback-no-metaphor-if-term-exists]]` - не пихать обёртки
- `[[feedback-no-code-objection-ever]]` - никогда «без опыта в коде»
- `[[feedback-ru-en-content-adaptation-rules]]` - RU vs EN structural
- `[[project-viral-hook-library-2026]]` - 8 hook patterns по платформе
- `[[feedback-content-factory-pure-replication-not-news]]` - replication чужих viral
- `[[feedback-strategy-copy-faster-more-better]]` - same-format reproduction
- `[[post]]` - sister skill (TG-посты, та же архитектура)
- `[[longform]]` - sister skill (text long-form)
- `[[email]]` - sister skill (email)
- `[[bot-message]]` - sister skill (TG-bot broadcast)
- `[[replicate-viral]]` - downstream / параллельный (рефакторинг в v1.1)
- `[[ingest-reel]]` - upstream для Mode C
- `[[screen-record-face-cam]]` / `[[split-screen-trend-jack]]` / `[[ai-avatar-news]]` / `[[before-after]]` - downstream production skills

## Версия

**Текущая:** 1.0 (2026-05-28) - Initial release. 4 mode (Plan/Spark/Replication/Transcript) + 5 length tiers + Production handoff brief + Hook Strength Gate. Ivan-only paths. Архитектура зеркало `post` v1.2.

**Roadmap:**
- v1.1: Student onboarding (`workflow/00-onboarding-student.md`) + рефакторинг `replicate-reel` Шаг 4 → call video Mode C + EN voice gold-standard pass
- v1.2: Long-form 10-60min template корректировки на основе real data (10+ применений)
- v2.0: Multi-language (UA / ES при запуске рынков)

**SemVer правила:**
- MAJOR: breaking change в выходном формате или критериях fail
- MINOR: новый template / новый mode / новый length tier / новый reference
- PATCH: уточнение правил валидации, новые AI-tells, fix references

**Когда пересматривать:**
- catch_rate в track-record падает < 80%
- 3+ систематических промаха voice автора
- Новые findings от референсных creators (Riley Brown / Heather Cooper / Sabrina Ramonov / Chris Cordero / Rowan Cheung / Nate Herk) - раз в квартал
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации скилла под автора
- `plans/2026-05-28-skill-video.md` - план разработки
- `tasks/projects/skill-video.md` - задачи проекта
- Sister skills: `post` / `longform` / `email` / `bot-message` / `paips-post` / `spiky-one-liner` / `stripe-screenshot-post` / `visual-concept-square`
- Downstream: `screen-record-face-cam` / `split-screen-trend-jack` / `ai-avatar-news` / `before-after` / `cut-from-long-form` / `replicate-reel`
- Upstream: `ingest-reel` (для Mode C)
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
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

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.

---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
