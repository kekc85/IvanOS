---
name: carousel
description: Мульти-слайд карусели для Instagram + LinkedIn. End-to-end: text + visual brief + PNG/PDF render. 8-12 slides + caption RU/EN. Portable через config.md. 4 режима × 5 семейств (framework / listicle / story-case / panorama / reel-to-carousel). Output = ~/Desktop/carousels/{date}-{slug}/ с PNGs + linkedin.pdf + caption.txt. Triggers /carousel, "сделай карусель про X", "карусель для LinkedIn", "перегони рилз в карусель", "панорамная карусель".
metadata:
  version: "1.1"
  created: "2026-05-28"
  last_reviewed: "2026-05-28"
  artifact_type: "mixed"  # framework/listicle/panorama = stylistic. story-case с цифрами или announce-context = action. DONE v1.1.1: 5 gates implemented conditionally в workflow/03-write.md Pass 0.5 (detect action-content → enforce PII / Event / Fact). См. skill-craft/knowledge/bug-categories.md. Прецедент: bot-message v1.0.2.
---

# carousel - Portable контент-машина мульти-слайд каруселей

> Skill производит готовый slide-pack для IG/LinkedIn: per-slide text + visual brief с REAL elements (UI screenshots / реальные продукты / реальные числа) + caption. Закрывает carousel-ветку контент-фабрики между `single-image` (1 кадр) и `produce-reel` (видео).

## Архитектура

Скилл portable: один и тот же код у автора и учеников курса вайбмаркетинга. Различие - только `config.md` и данные проекта.

**Три ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (Карта смыслов) / Spark-B1 (идея пользователя) / Spark-B2 (генерация под JTBD) / Transcript (надиктовка) / Reel-to-carousel (card.md от ingest-reel) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |
| **Family** (что за карусель) | framework breakdown / listicle / story-case / panorama / reel-to-carousel |

**Router** в `workflow/01-router.md` auto-detect'ит mode по сигналам input. Override через флаги `--plan` / `--spark` / `--transcript` / `--reel <url>` / `--family=<type>` / `--platform=<ig|li|both>` / `--bilingual`.

**Onboarding** для нового пользователя - `workflow/00-onboarding-student.md`. Срабатывает при отсутствии или неполном `config.md`.

## Когда применять

Триггеры (auto-detect в router):

| User input | Mode | Что делает |
|---|---|---|
| `/carousel` без аргументов | Plan | Берёт смысл дня из Карты смыслов запуска |
| «по плану», «смысл дня», дата | Plan | То же |
| `/carousel про X`, «сделай карусель про X», «карусель про vibemarketing» | Spark-B1 | Расширяет тему X в 5-7 carousel-углов |
| «дай идеи каруселей», «что в карусель сегодня» | Spark-B2 | Генерит 5-7 идей под JTBD/avatar |
| Длинный текст (>500 знаков) с пометкой «для карусели» | Transcript | Извлекает 3-10 атомарных смыслов |
| `/carousel reel <url>`, «перегони рилз в карусель», «из этого ролика карусель» | Reel-to-carousel | Читает card.md от ingest-reel, mapping в slides |
| «панорамная карусель», «панорама про X» | Spark-B1 + family=panorama | Wide composition разрезанный на 3-8 slides |

**Не применять** для:

- 1 кадр / одна картинка → `single-image`
- Текст-пост без слайдов → `post` / `paips-post` / `spiky-one-liner` / `longform`
- Email → `email`
- TG-bot push → `bot-message`
- Video / Reel / Short → `video` (script) / `replicate-reel` / `produce-reel`
- Сама генерация картинок per slide → `higgsfield-generate` / `frontend-design` (carousel даёт brief + manifest, рендер отдельно)
- Motion carousel (slides с движением) → v1.1, пока вне scope

## Workflow (progressive disclosure)

При вызове skill последовательно грузит соответствующие `workflow/` файлы:

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

01-router.md                  ← detect mode + subject + platform + load config
   ├─ 01a-plan.md             ← Mode A: из Карты смыслов
   ├─ 01b-spark.md            ← Mode B1/B2: ситуативный
   ├─ 01c-transcript.md       ← Mode C: из надиктовки
   └─ 01d-reel-to-carousel.md ← Mode D: из card.md ингеста
       ↓
01-finalize.md                ← family pre-select + length budget + platform spec
02-structure.md               ← family-specific outline (Hook→Value→CTA + slide-by-slide)
03-write.md                   ← Pass 1 slides text / Pass 2 visual briefs / Pass 3 caption
04-review.md                  ← 6-Pass + Maxwell Ross 9 + 3 слоя + 9 carousel gates
05-publish.md                 ← output (per-platform format + A/B + assets manifest)
```

**Файлы:**

| Файл | Назначение |
|---|---|
| `workflow/00-onboarding-student.md` | First run для ученика. Создаёт config.md через 9 вопросов |
| `workflow/01-router.md` | Auto-detect mode + subject + platform |
| `workflow/01a-plan.md` | Mode A: читает Карту смыслов по дате |
| `workflow/01b-spark.md` | Mode B1: расширение идеи / Mode B2: генерация под JTBD |
| `workflow/01c-transcript.md` | Mode C: разбор надиктовки в атомарные смыслы |
| `workflow/01d-reel-to-carousel.md` | Mode D: чтение card.md → mapping в slide structure |
| `workflow/01-finalize.md` | Family pre-select + slide count + platform spec |
| `workflow/02-structure.md` | Family-specific outline + slide-by-slide skeleton |
| `workflow/03-write.md` | Slide text + visual briefs (REAL first) + caption |
| `workflow/04-review.md` | 6-Pass + Maxwell Ross 9 + 3 слоя + 9 carousel gates |
| `workflow/05-publish.md` | Output + A/B + assets manifest |

## 5 семейств типов (templates)

| # | Family | Slides | Структура | Reference creator | Применение |
|---|---|---|---|---|---|
| 1 | **framework-breakdown** | 8-12 | Hook + numbered 1-N + CTA | Justin Welsh / Sahil Bloom | «8 ходов X», методология |
| 2 | **listicle** | 8-10 | Hook + N items (odd/even alternation framework/screenshot) + CTA | Riley Brown / Greg Isenberg | Tool roundups, N items |
| 3 | **story-case** | 10-12 | Hook + context + problem + action + outcome + number + CTA | Pieter Levels / Lara Acosta | Personal experience, кейс с числом |
| 4 | **panorama** | 3-8 | Wide image разрезанный (leading slide 1 + payoff slide N) | Casper ZZZ / Subway daily | Wow эффект, category reveal |
| 5 | **reel-to-carousel** | 8-12 | Hook frame → beats (1 beat = 1 slide) → reveal → CTA | Welsh repurposing | Перепаковка viral Reel |

**v1.0:** эти 5 покрывают ~85% carousel use cases.
**v1.1+ planned:** motion carousel (hyperframes integration) / myth-busting / before-after standalone.

## 🔴 Видео-слайд реплицируется ВИДЕО, не скриншотом (правило в даты запуска.2026)

Если слайд карусели-источника в оригинале **ВИДЕО** (играбельная демка, 3D-вращение, анимация, скринкаст - media_type=2), его НЕЛЬЗЯ заменять статичным скриншотом / GPT-рендером / постером. Реплицируем видео видео: оригинальный ролик слайда + НАШ текст плашкой ПОВЕРХ. Это HARD-развилка в пайплайне (детект видео-детей → видео-ветка `video_overlay.py`), а не опция - см. полный конвейер в `carousel-uniqualizer` (раздел «ВИДЕО-СЛАЙДЫ = ВИДЕО»). Признак промаха: статика на месте, где в оригинале демо двигалось. Связано:.

## Knowledge base (references/)

Грузятся по нужде через progressive disclosure:

- `references/carousel-anatomy.md` - Hook/Value/CTA структура, slide pacing, 5-beat arc (Bucket E synthesis)
- `references/visual-brief-real-first.md` - 6-field schema (REAL elements priority + abstraction_check)
- `references/banned-ai-imagery.md` - 12-item checklist + examples что НЕ делать
- `references/panorama-mechanics.md` - canvas math (N×1080), slice tools, isolated-slide rule
- `references/caption-formulas.md` - IG vs LinkedIn caption (210-char LI cutoff, hashtag rules 2026)
- `references/platform-adaptations.md` - IG 1080×1350 vs LinkedIn PDF 1080×1350 + cross-distribution
- `references/reel-to-carousel-bridge.md` - mapping card.md (transcript/frames/UI inventory) → slides

## Examples

- `examples/track-record-carousel.md` - история применений + catch_rate metric

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/04-review.md`):**

- Em-dash «-» внутри строк → fail
- «Instagram» → auto-correct в «Нельзяграм»
- Banned англицизмы из `config.lexicon_banned_hard` → fail
- Slide count вне диапазона family → fail
- Per-slide length вне диапазона (hook 3-12 / value 5-25 / CTA 5-15 слов) → fail
- >1 восклицательного знака в caption → warning
- Caption длиннее platform target → fail

**9 carousel-specific gates (LLM в `04-review.md`):**

- **CR-G1 Slide count** - 8-12 IG, 7-20 LI, 3-8 panorama
- **CR-G2 Per-slide length** - hook 3-12 / value 5-25 / CTA 5-15 слов
- **CR-G3 Hook ≠ cover** - number + outcome + timeframe, не просто title
- **CR-G4 Real elements floor** - ≥40% slides содержат реальный UI/product/number
- **CR-G5 Banned AI imagery scan** - против 12-item checklist
- **CR-G6 Pacing chain** - slide N tease'ит N+1 ИЛИ закрывает loop
- **CR-G7 Caption ≠ slides duplication** - caption даёт дополнительный layer, не пересказ
- **CR-G8 Platform constraint** - IG ≤10 optimal, LI ≤20 PDF pages
- **CR-G9 Panorama integrity** (family=panorama only) - каждый slide работает isolated + cut lines чистые

**6-Pass Refinement (LLM):**
Skeptic / Expert / Scroller / Competitor / Editor / Thumbnail - адаптировано для carousel (Thumbnail = hook slide читается ли в feed preview).

**Maxwell Ross 9-Item Checklist:** 9 yes/no pre-publish (адаптировано под carousel pack).

**3 слоя финальный gate:**
- Слой 1 валидаторы (regex)
- Слой 2 4 концепции (Pre-mortem / 90% calibration / Multi-perspective / Adaptive)
- Слой 3 7 контуров (Context / Соответствие / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность)

## Принципы

1. **REAL elements first.** Visual brief каждого slide начинается с `real_elements:` (реальные UI / продукты / числа / скриншоты). Generic / абстрактное - fail.
2. **Naglyadnost > красота.** Скриншот настоящего Cursor IDE с конкретной командой важнее эстетического gradient blob.
3. **Hook = number + outcome + timeframe.** Не интрига, а конкретная награда за свайп. «<твоя выручка> за 12 месяцев на органике» > «Секрет успеха».
4. **One idea per slide.** Один beat = один slide. 2 идеи в slide - split на 2 slides.
5. **Hook ≠ cover.** Hook slide содержит явный promise, не просто title.
6. **CTA = artifact, не behavior.** «Comment "разбор" → DM ссылка на марафон» > «Follow me».
7. **Каждый slide tease'ит следующий.** Open loop / cliffhanger / curiosity gap между slides. Pacing chain mandatory.
8. **Banned AI imagery hard.** 12-item checklist обязательная проверка. Generic gradients / illustrated офисные люди / robot hands = brand suicide.
9. **Platform-aware adaptation.** IG 1080×1350 portrait, LinkedIn 1080×1350 PDF. Разная typography, разный caption budget.
10. **Bilingual через config.** RU + EN параллельно если `--bilingual` или config.subject.language=both. Не дословный перевод - культурная адаптация через chain в `multi-language-localization`.
11. **Portable by config.** Один скилл - множество авторов через `config.md`. Никаких hardcoded paths.
12. **MECE с фабрикой.** carousel = только 2+ slides. 1 slide → `single-image`. Видео → `produce-reel`.
13. **3 слоя проверки финальный gate.** Перед output обязательное явное подтверждение «3 слоя пройдено».
14. **Каждая правка = системная.** Фидбек автора → точечный fix + системная правка в скилле (config / workflow / review gate / memory). См. `[[feedback-each-correction-becomes-system-rule]]`.

## Portability - для ученика курса

Ученик клонирует папку `~/.claude/skills/carousel/` и заменяет ТОЛЬКО:

1. **`config.md`** - пути и lexicon под свой проект (onboarding делает это за него при первом запуске)
2. **`examples/gold-standard-<your-name>.md`** - свои лучшие carousels (3-5 штук)
3. **`intake/` (или `.business/`)** - `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`. По путям из config

Что НЕ трогаем:
- `workflow/*` - общая методология
- `references/*` - carousel-anatomy / banned imagery / panorama mechanics одинаковы
- `templates/*` - 5 семейств одинаковы

## Anti-patterns

Ключевые (полный список в `references/banned-ai-imagery.md`):

- **Generic AI illustrations людей в офисах** (Midjourney corporate стиль)
- **Gradient blob backgrounds + 3D abstract shapes** (templated PostNitro вид)
- **Robot hands typing / brain with circuits** клише
- **Stock photos** «diverse team smiling at laptop»
- **AI-generated avatars** вместо real photo
- **Generic vector icons** вместо real product logos
- **Soft pastel backgrounds** без content
- **Fake/cropped dashboards** (репутационный риск)
- **Symbolic "expert"** illustration
- **AI-generated charts** без реальных чисел
- **Corporate buzzwords** overlay
- **Vector illustrations** с американцами для RU аудитории
- **Hook = title** (без promise/curiosity)
- **CTA = «follow me»** без artifact
- **>2 идеи в одном slide**
- **Wall of text** на slide (>25 слов на value slide)
- **Em-dash «-»** внутри строк
- **Cut lines через лица/key text/logos** в panorama

## Memory cross-refs

- `[[feedback-no-em-dash]]` - em-dash запрещён внутри строк
- `[[feedback-no-tech-jargon-no-anglicisms]]` - без жаргона / англицизмов
- `[[feedback-no-negative-stats-in-public-offer]]` - без негативных статистик
- `[[feedback-no-inventing-facts]]` - числа только verified
- `[[feedback-no-generic-ai-artifacts]]` - generic AI = брак
- `[[feedback-images-from-icp-world]]` - образы из мира аватара
- `[[feedback-always-open-artifacts]]` - готовый brief открывать через `open`
- `[[feedback-each-correction-becomes-system-rule]]` - правки на двух уровнях
- `[[feedback-verbatim-quote-transfer]]` - дословный перенос цитат
- `[[post]]` - chain: carousel idea → post для TG-варианта
- `[[single-image]]` - параллельный skill для 1-кадровых постов
- `[[longform]]` - параллельный skill для длинного текста (carousel = derivative)
- `[[replicate-viral]]` - параллельный skill для видео
- `[[ingest-reel]]` - input для Mode D (читает card.md)
- `[[higgsfield-generate]]` - chain для AI image execution (v1.1)
- `[[frontend-design]]` - chain для typography-led slide rendering (v1.1)

## Версия

**Текущая:** 1.0 (2026-05-28) - Initial release. 5 семейств (framework-breakdown / listicle / story-case / panorama / reel-to-carousel), 4 режима (Plan / Spark / Transcript / Reel-to-carousel), 2 subject (автор / ученик), 2 platforms (IG / LinkedIn), bilingual RU + EN через config. Built on validated research (5 bucket dossiers, 2435 строк, 41 carousels разобрано).

**SemVer правила:**
- MAJOR: breaking change в формате output или критериях fail
- MINOR: новое family / новый mode / новый reference файл
- PATCH: уточнение валидации, новые banned AI patterns, fix references

**Когда пересматривать:**
- catch_rate в track-record падает < 80%
- 3+ систематических промаха по типу или voice
- Новые findings от Welsh / Acosta / Riley Brown (раз в квартал)
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации скилла под автора
- `plans/2026-05-28-carousel-skill-spec.md` - полная спецификация
- `.business/growth/carousel-research/2026-05-28/` - 5 research dossiers (2435 строк)
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
- `~/.claude/skills/post/` v2.2 - source паттерна архитектуры
- `~/.claude/skills/single-image/` v1.0 - sibling pattern (1-кадр vs 2+ slides)

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
