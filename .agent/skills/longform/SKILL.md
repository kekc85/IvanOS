---
name: longform
description: Контент-машина длинных форм (800-3000 слов) - newsletter (Kit/Beehiiv) / personal blog / LinkedIn article. RU + EN bilingual. Portable by config.md. 3 mode (Plan / Spark / Transcript) × 4 platform × 7 типов longform (v1.0 MVP teaching/story/framework). Review-стек: 6-Pass + Maxwell Ross 9 + 3 слоя + POSSE distribution + A/B subject. Triggers /longform, "напиши статью про X", "сделай newsletter", "эссе про X", "LinkedIn article", надиктовки >500 знаков с request to expand.
metadata:
  version: "1.0"
  created: "2026-05-28"
  last_reviewed: "2026-05-28"
  artifact_type: "mixed"  # teaching/framework = stylistic. story = stylistic. case-study + launch-promo listicle = action. DONE v1.0.1: 5 gates implemented conditionally в workflow/03-write.md Pass 0.5 (detect action-content → enforce PII / Event / Fact + Gate D/E в review). См. skill-craft/knowledge/bug-categories.md. Прецедент: bot-message v1.0.2.
---

# longform - Portable контент-машина длинных форм

> Skill производит готовые длинные тексты (800-3000 слов) в голосе автора для 4 платформ (Beehiiv / Kit / personal blog / LinkedIn article). Базируется на исследованных reference creators (Dan Koe / Justin Welsh / Rowan Cheung / Sahil Bloom / Tim Ferriss) + переиспользует валидаторы и review-стек из `post` v1.2. Замещает старый `long-form-essay` v1.0 (1-файловый skill без modes / без portability / без review-стека).

## Архитектура

Скилл portable: один и тот же код работает у автора и у учеников курса вайбмаркетинга. Различие - только в `config.md` и данных проекта, на которые он указывает.

**Три ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (Карта смыслов / контент-план) / Spark-B1 (расширение идеи) / Spark-B2 (генерация под JTBD) / Transcript (надиктовка) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |
| **Platform** (куда канонически идёт) | Beehiiv / Kit / personal blog / LinkedIn article |

**Router** в `workflow/01-router.md` auto-detect'ит mode по сигналам в input. Override через флаги `--plan` / `--spark` / `--transcript` / `--platform=<beehiiv\|kit\|blog\|linkedin>`.

**Onboarding** для нового пользователя - `workflow/00-onboarding-student.md`. Срабатывает при отсутствии или неполном `config.md`. После onboarding ученик имеет заполненный config + `intake/` файлы и может запускать `/longform`.

## Когда применять

Триггеры (auto-detect mode в router):

| User input | Mode | Что делает |
|---|---|---|
| `/longform` без аргументов | Plan | Берёт смысл недели из Карты смыслов запуска или контент-плана |
| «по плану», «смысл недели», дата | Plan | То же |
| `/longform про X`, «напиши статью про X», «эссе про X» | Spark-B1 | Расширяет тему X в 5-7 углов longform, ты выбираешь |
| «дай идеи для newsletter», «что писать в LinkedIn article» | Spark-B2 | Генерит 5-7 longform-идей под JTBD/avatar, ты выбираешь |
| Длинный текст (>500 знаков), «надиктовал», «вот мысли - разверни» | Transcript | Извлекает 1-3 longform-arc'а, разворачивает в полный текст |

**Не применять** для:
- Постов в TG-канал → `post`
- Постов в X / Threads (короткие нарративы / треды) → `paips-post` / `spiky-one-liner`
- Email с темой+preheader+конверсия → будущий `email-broadcast`
- Bot-broadcast → будущий `bot-broadcast`
- Video (Reels / Shorts / TikTok) → `replicate-reel`
- Carousel / single-image → `visual-concept-square` / `stripe-screenshot-post`

## Workflow (progressive disclosure)

При вызове skill последовательно грузит соответствующие `workflow/` файлы:

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

01-router.md                  ← detect mode + platform + load config
   ├─ 01a-plan.md             ← Mode A: из Карты смыслов / контент-плана
   ├─ 01b-spark.md            ← Mode B1: расширение идеи / B2: генерация под JTBD
   └─ 01c-transcript.md       ← Mode C: из надиктовки → longform arcs
       ↓
01-finalize.md                ← type rotation + hook + target length + platform spec
02-structure.md               ← detect type (один из 7) + 3-section outline + headline
03-write.md                   ← Pass 0 mandatory reads + draft + voice injection
04-review.md                  ← 6-Pass + Maxwell Ross 9 + 3 слоя + long-form regex gates
05-publish.md                 ← POSSE distribution map + A/B subject lines + derivatives plan
```

**Файлы:**

| Файл | Назначение |
|---|---|
| `workflow/00-onboarding-student.md` | First run для ученика. Создаёт config.md через 11 вопросов (включая platform priority) |
| `workflow/01-router.md` | Auto-detect mode (Plan / Spark / Transcript), subject, platform |
| `workflow/01a-plan.md` | Mode A: читает Карту смыслов / контент-план по дате недели |
| `workflow/01b-spark.md` | Mode B1: расширение идеи в 5-7 углов / Mode B2: генерация 5-7 longform-идей под JTBD |
| `workflow/01c-transcript.md` | Mode C: разбор надиктовки в 1-3 longform arcs |
| `workflow/01-finalize.md` | Общая доводка brief: type/hook/target-length/platform |
| `workflow/02-structure.md` | Detect-type (один из 7) + 3-section outline (Koe) + headline (5 elements) |
| `workflow/03-write.md` | Draft + voice injection + section pacing + specific examples |
| `workflow/04-review.md` | 6-Pass + Maxwell Ross 9 + 3 слоя + long-form regex gates |
| `workflow/05-publish.md` | POSSE map + A/B subject lines + derivatives plan |
| `workflow/RESUME-PROTOCOL.md` | State save в `/tmp/longform-state-*.yaml` + resume after crash (v1.0 fix L4.3) |

## 7 типов longform (templates)

| # | Тип | Длина | Когда | Template (v1.0 / v1.1+) |
|---|---|---|---|---|
| 1 | Teaching essay | 1200-2000 слов | Обучающий, механизм + почему + step-by-step | v1.0 `teaching-essay.md` |
| 2 | Story essay | 1000-1800 слов | Нарратив с personal payoff, Koe / Welsh | v1.0 `story-essay.md` |
| 3 | Framework essay | 1200-2200 слов | Контр-интуитивный mental model / каркас в голову | v1.0 `framework-essay.md` |
| 4 | Contrarian breakdown | 1200-2000 слов | Myth vs reality + новый взгляд | v1.1 |
| 5 | Case study | 1500-2500 слов | Конкретный кейс + lesson | v1.1 |
| 6 | Listicle (anti-generic) | 1500-2500 слов | N принципов с глубиной (НЕ «10 хуков») | v1.1 |
| 7 | Deep-dive | 2000-3000 слов | Research-heavy, raw thinking | v1.2 |

**v1.0 (текущий релиз):** templates 1, 2, 3 - закрывают ~70% реальных кейсов longform.
**v1.1:** templates 4, 5, 6.
**v1.2:** template 7 (deep-dive с research scaffold).

## 4 platform варианта

| Platform | Canonical role | Длина | Headline | Форматирование | Cross-post target |
|---|---|---|---|---|---|
| **Personal blog** | Canonical (POSSE primary) | 1200-3000 | SEO-friendly H1 | Markdown / HTML | yes - все остальные |
| **Beehiiv** | Primary newsletter (если есть paid network goal) | 1000-2200 | Subject line A/B | Beehiiv blocks (text/quote/divider/image/CTA/button) | cross-post via blog canonical |
| **Kit** | Primary newsletter (если есть tag automation goal) | 1000-2200 | Subject line A/B + preheader | Plain HTML + Kit blocks | cross-post via blog canonical |
| **LinkedIn article** | Primary distribution в LinkedIn wedge | 800-1800 | LinkedIn-friendly headline | Inline / LinkedIn editor | cross-post via blog canonical (rel="canonical") |

**Platform spec details** - `references/platform-specs.md`.

## Knowledge base (references/)

Все references грузятся по нужде через progressive disclosure:

- `references/platform-specs.md` - Beehiiv vs Kit vs blog vs LinkedIn: длина / headline / форматирование / canonical / A/B subject
- `references/longform-structures.md` - 3-section Koe + 5-step Welsh + news-driven Cheung + Bloom 4x/week + Ferriss long-form
- `references/hook-patterns-longform.md` - 12+ паттернов hook для длинных форм с RU/EN адаптацией
- `references/posse-distribution.md` - canonical → cross-post Substack/Medium/LinkedIn + rel="canonical" + derivatives plan
- `references/ru-en-adaptation.md` - bilingual правила (story-first RU vs argument-first EN, lexicon swap, structure pivot, examples swap)
- `references/maxwell-ross-9-checklist.md` - Maxwell Ross pre-publish gate (Idea / Clarity / Payoff / Specificity / Freshness / Hook / Length / Tone / CTA) адаптирован под longform
- `references/6-pass-refinement.md` - Skeptic / Expert / Scroller / Competitor / Editor / Thumbnail для длинных форм
- `references/ai-tells-longform.md` - AI-tells специфика длинных форм (более длинные паттерны, formulaic transitions, listicle-bloat)

## Examples

- `examples/track-record-longform.md` - история применений + catch_rate metric (пустой стартовый)

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/04-review.md`):**
- Em-dash «-» внутри строк → fail
- «Instagram» → auto-correct в «Нельзяграм» (RU only)
- Запретные термины из config.lexicon_banned_hard → fail
- Length > target по platform → fail
- Length < target floor по platform → warning
- Generic AI listicle patterns («10 ways», «5 reasons», без глубины) → fail
- Hook без проверки на counter-intuitive / personal anchor / problem → fail
- CTA отсутствует → fail

**6-Pass Refinement (LLM):**
Skeptic / Expert / Scroller / Competitor / Editor / Thumbnail - адаптировано под longform (более глубокий Skeptic для argumentation, Scroller через 3-секундный hook test для newsletter open rate, Competitor через сравнение с reference creator в той же нише).

**Maxwell Ross 9-Item Checklist:**
9 yes/no вопросов pre-publish (см. `references/maxwell-ross-9-checklist.md`), адаптировано под longform (Idea на уровне «один main aha» / Specificity через numbers+examples / Hook через newsletter subject + первая строка / Length через target по platform).

**3 слоя финальный gate:**
- Слой 1 валидаторы (regex)
- Слой 2 4 концепции (Pre-mortem 5 причин провала / 90% calibration / Multi-perspective Маркетолог-Эксперт-Читатель / Adaptive - новая ошибка → новый валидатор)
- Слой 3 7 контуров (Context / Соответствие предпосылкам / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность)

## Принципы

1. **Portable by config.** Один и тот же скилл работает у автора и у ученика. Различие - только `config.md` и данные проекта. Никаких hardcoded paths.
2. **Voice over structure.** Стилистика автора важнее шаблона. Если шаблон ломает голос - голос побеждает.
3. **One main "aha" per essay.** Один longform = один центральный тезис. Multi-тезисные - split на серию.
4. **POSSE by default.** Канонический URL = свой блог. Newsletter / Substack / Medium / LinkedIn = cross-post с rel="canonical".
5. **Bilingual через config.market.** RU и EN - разные структуры (story-first RU vs argument-first EN), разные lexicon, разные reference creators.
6. **Specific numbers > vague claims.** 300% specificity lift из research. Каждый пример с конкретикой.
7. **Hook crafted ≥15 минут.** Newsletter open rate / scroll-stop зависит от первой строки + subject line. Hook A/B минимум 3 варианта.
8. **No daily longform.** 1-2/неделю максимум. Daily = burnout + thinness. Daily - это TG-posts через `post`.
9. **Карта смыслов / контент-план = source of truth для Mode A.** Не дополнять, не выдумывать. Пустая запись = fallback на Mode B2.
10. **Транскрипт в Mode C - цитата, не парафраз.** Лексика автора важнее «причёсанной» формулировки.
11. **Maxwell Ross 9 + 3 слоя - финальный gate.** Никакой longform не выходит без 9/9 PASS + явного подтверждения 3 слоёв.
12. **Внутрянка после статьи.** Каждый output включает блок «Как писал»: Mode / type / platform / hook framework / structure / voice / что отброшено / A/B subject лоgika.
13. **Каждая правка = системная.** Любая обратная связь от автора закрывается на ДВУХ уровнях: (1) точечный fix в текущей статье + (2) системная правка в скилле - config / workflow stage / review gate / memory / SKILL.md.
14. **Mandatory reads перед draft.** В Pass 0 `03-write.md` обязательны: gold-standard longform автора / voice references / config / platform-spec выбранной платформы.

## Portability - для ученика курса

Ученик клонирует папку `~/.claude/skills/longform/` в свою машину и заменяет ТОЛЬКО:

1. **`config.md`** - пути, лексика, platform priority под свой проект (онboarding это делает за него при первом запуске).
2. **`examples/gold-standard-<your-name>-longform.md`** - свои лучшие длинные тексты (3-5 штук).
3. **`intake/`** (или `.business/`) - `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`. По путям из config.

Что НЕ трогаем:
- `workflow/*` - общая методология
- `references/*` - references (Maxwell Ross, structures, hooks, POSSE, AI-tells) одинаковы для всех
- `templates/*` - шаблоны 7 типов longform

Это делает скилл **product курса**: ученики курса вайбмаркетинга получают тот же инструмент, который автор использует еженедельно для newsletter и LinkedIn.

## Anti-patterns

См. `references/ai-tells-longform.md` + `references/ru-en-adaptation.md`. Ключевые:

- Em-dash «-» внутри строк
- «Instagram» вместо «Нельзяграм» (RU)
- **Generic AI listicles** («10 ways to X», «5 reasons Y», «Top 7 Z» - без глубины принципов)
- **Formulaic transitions** («Now let me tell you», «So here's the thing», «But wait, there's more»)
- **Multiple "aha" insights** в одном essay (split на серию)
- **Without specific numbers / examples** (vague = generic)
- **Without CTA** (lost engagement, no funnel)
- **Hyperbolic claims** без proof
- Negativные статистики в публичной части
- Технический жаргон без раскрытия
- Daily longform (overrun time budget + thinness)
- AI prose без voice injection (Cheung principle: AI for structure / research, не для prose)

## Memory cross-refs

- - em-dash «-» внутри строк запрещён
- - без жаргона / англицизмов
- - без негативных статистик в публичном
- - термины (3M/AARRR/Core Four) раскрывать
- - дословный перенос цитат, не пересказ
- - нет «10 хуков», «100 промптов» generic
- - specific numbers > vague claims
- - hook patterns для всех платформ
- - RU и EN - разные направления + разные структуры
- - дословно vs переписывать
- - same-format reproduction
- - дефицитность / виральность / переработка / наглядность
- `[[post]]` - параллельный skill для TG-постов (overlap резолвится: post = TG-канал ≤2500 chars, longform = newsletter/blog/LinkedIn 800-3000 слов)
- `post` - параллельный skill для X/Threads/LinkedIn-post формата PAIPS (overlap резолвится: paips-post = короткий пост-нарратив, longform = длинная статья)
- `longform` - **DEPRECATED**, замещён этим skill'ом

## Версия

**Текущая:** 1.0 (2026-05-28) - Initial release. Mirror архитектуры `post`. Router + 3 modes + finalize + structure + write + review + publish. Templates teaching / story / framework. 8 references. Portable через config.md. Bilingual RU + EN. 4 platform support. Замещает `long-form-essay` v1.0.

**Changelog:**
- v1.0 (2026-05-28): Initial release.

**SemVer правила:**
- MAJOR: breaking change в выходном формате или критериях fail
- MINOR: новый template (4-7) / новая platform / новый mode / новый reference файл
- PATCH: уточнение правил валидации, новые AI-tells, fix references

**Когда пересматривать:**
- catch_rate в track-record падает < 80%
- 3+ систематических промаха voice автора в longform
- Новые ключевые findings от Dan Koe / Justin Welsh / Tim Ferriss / Sahil Bloom (раз в квартал чек)
- Появление новой platform (Substack Notes как primary / Mirror.xyz / Paragraph.xyz)
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации скилла под автора (см. внутри файла)
- `~/.claude/skills/post/` v1.2+ - параллельный skill для TG-постов (берёт review-стек / archetype patterns / lexicon)
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
- `~/.claude/skills/long-form-essay/` v1.0 - **DEPRECATED**, замещён этим skill'ом
- `.business/marketing/channels.md` - 4 core канала автора (newsletter / YouTube+GEO / Skool / LinkedIn) - longform = newsletter + LinkedIn
- `.business/marketing/content.md` - 3 контент-pillars + cite-friendly формат + newsletter как главный продукт

## Empirical patterns layer (NEW 2026-05-28)

Этот skill интегрирован с shared empirical layer для всех content-skills.

**Mandatory Reads в Pass 0** (пути боевые, `~/IvanOS/...`; `~/.business` - симлинк на шаблон IvanOS, читать оттуда запрещено):
- `.business/growth/extracted-patterns/INTEGRATION.md` - что читать для этого скилла
- `.business/growth/extracted-patterns/hook-patterns-empirical.md` - 9 patterns из 30 corpus
- `.business/growth/extracted-patterns/voice-markers-empirical.md` - Greg/Riley/Sabrina + авторская calibration
- `.business/growth/extracted-patterns/audience-glossary.md` - agent-jargon → язык RU ЦА
- `.business/growth/extracted-patterns/funnel-awareness.md` - куда ведёт content
- `.business/voice-corpus/_format-canon-v2.md` - канон формы v2 (уровень 5 иерархии). Читается в `03-write.md` Pass 0, применение проверяется уликой формы в `04-review.md`
<!-- O1 (канон формы v2): пути выправлены на боевую копию .business/ - `~/.business` в системе IvanOS
     является симлинком на шаблон курса, а не на боевой канон автора. Чтение шаблона вместо боевого канона
     было классом дефекта «написан, но не подключён к боевым данным». -->

**Benchmark Gate** в review stage:
- Compare output vs nearest 3 examples из `benchmark-corpus-index.md`
- Score /6 для text-only OR /7 для visual
- Cutoff: 4+/6 (text) | 5+/7 (visual) = PASS

Root cause fix: до 2026-05-28 references зашивали теорию виральности из памяти. Shared layer = empirical extraction из 30 real viral шортов в авторской нише.
