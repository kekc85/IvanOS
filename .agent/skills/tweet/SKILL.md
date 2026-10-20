---
name: tweet
version: "1.2"
created: 2026-05-28
last_reviewed: 2026-05-28
description: Контент-машина для X (Twitter) + Threads (Meta). Single tweet / mini-thread / mega-thread в голосе автора. Лимиты X 280, Premium 25K, Threads 500. Bilingual RU+EN через config. Portable через config.md. 3 режима (Plan / Spark / Transcript) × 2 subject × 2 platform × 2 language. 7 типов (single punchline / PAIPS story / spiky one-liner / numbered list mini-thread / story-news mega-thread / contrarian / how-i-did). Review = 6-Pass + Maxwell Ross 9 + 3 слоя + Hook Char Zone Gate + Thread Length Gate. Triggers /tweet, "напиши твит", "сделай тред", "tweet про X", "thread про X", надиктовки >500 знаков для X.
---

# tweet - Контент-машина X + Threads

> Skill производит готовые твиты / треды / Threads chains в голосе автора. Базируется на research 21 EN авторов с X-specific extraction (314 verbatim posts, см. `references/research-index.md`). автор и ученики курса вайбмаркетинга используют один и тот же tool через portable `config.md`.

## Архитектура

Скилл portable: один и тот же код работает у автора и у учеников курса. Различие - только в `config.md` и данных проекта.

**4 ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (Карта смыслов) / Spark-B1 (идея пользователя) / Spark-B2 (генерация под JTBD) / Transcript (надиктовка) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |
| **Platform target** | X-only / Threads-only / Both (cross-post с adapt) |
| **Language** | RU / EN (default из config) |

**Router** в `workflow/01-router.md` auto-detect'ит mode по сигналам в input + флаги `--plan` / `--spark` / `--transcript` / `--x` / `--threads` / `--ru` / `--en`.

**Onboarding** для нового пользователя - `workflow/00-onboarding-student.md`. Срабатывает при отсутствии или неполном `config.md`.

## Когда применять

Триггеры (auto-detect mode в router):

| User input | Mode | Что делает |
|---|---|---|
| `/tweet` без аргументов | Plan | Берёт смысл дня из Карты смыслов запуска |
| «по плану», «смысл дня», дата | Plan | То же |
| `/tweet про X` / «напиши твит про X» / «сделай thread про X» | Spark-B1 | Расширяет тему X в 5-7 углов, ты выбираешь |
| «дай идеи твитов» / «что писать на X сегодня» | Spark-B2 | Генерит 5-7 идей под JTBD/avatar |
| Длинный текст (>500 знаков), «надиктовал для твита» | Transcript | Извлекает 3-10 атомарных смыслов |
| Флаги `--x` / `--threads` / `--ru` / `--en` | Любой | Forced platform / language |

**Не применять** для:

- TG / LinkedIn narrative → `post` skill
- Newsletter / longform article ≥800 слов → `longform`
- Email broadcast → `email`
- Bot/Skool DM → `bot-message`
- Video / Reels script → `video`
- Carousel → `carousel`
- Single image (concept-diagram / dashboard-screenshot / meme / quote-card / before-after) → `single-image`

## Workflow (progressive disclosure)

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

01-router.md                  ← detect mode + platform + language + load config
   ├─ 01a-plan.md             ← Mode A: из Карты смыслов
   ├─ 01b-spark.md            ← Mode B1/B2: ситуативный
   └─ 01c-transcript.md       ← Mode C: из надиктовки
       ↓
01-finalize.md                ← archetype rotation + hook + format (single/thread)
02-structure.md               ← detect-type (один из 7) + skeleton + hook
03-write.md                   ← pass 1 draft + pass 2 voice injection
04-review.md                  ← 6-Pass + Maxwell Ross 9 + 3 слоя + Hook Char Zone Gate + Thread Length Gate
05-publish.md                 ← output (X + Threads adapt) + A/B + STEPPS + self-check
```

## 7 типов (templates)

| # | Тип | Длина | Template | Применение |
|---|---|---|---|---|
| 1 | Single punchline | ≤280 X / ≤500 Threads | `templates/single-punchline.md` | Daily, aphorism/spiky |
| 2 | PAIPS story | 5-8 tweet mini-thread OR 150-300 слов X long | `templates/paips-story.md` | Welsh signature, поглотил `paips-post` |
| 3 | Spiky one-liner | ≤140 chars | `templates/spiky-oneliner.md` | Hormozi / Iman, поглотил `spiky-one-liner` |
| 4 | Numbered list mini-thread | 5-15 tweets | `templates/numbered-list.md` | "5 things that work in 2026" |
| 5 | Story / news mega-thread | 18-34 tweets | `templates/mega-thread.md` | Bloom Named-Principle / Cole framework / Cheung AI news |
| 6 | Contrarian take | single или 3-tweet hook+proof+lesson | `templates/contrarian.md` | "Most advice is wrong" |
| 7 | How-I-did demo | 8-12 tweets build-in-public | `templates/how-i-did.md` | Levels / Marc Lou / Friks |

**v1.0 MVP:** types 1, 2, 3, 4 - закрывают ~75% daily output.
**v1.1+:** types 5, 6, 7 - добавляются после catch_rate verification.

## Knowledge base (references/)

Progressive disclosure:

- `references/viral-hooks-2026-x.md` - 15 hook patterns (8 base + 7 new) × verbatim examples
- `references/thread-structure.md` - 3-mode rule + Cole's 7 templates + Bloom Named-Principle
- `references/_voice-TEMPLATE.md` - автора EN voice derived from gold-standard (Welsh primary)
- `references/ai-tells-en.md` - EN AI tells catalog
- `references/ai-tells-ru.md` - **[v1.1]** RU AI tells catalog (5 tiers, 60+ patterns)
- `references/ru-grammar-russification.md` - **[v1.1]** EN→RU grammar rules без кальки
- `references/x-platform-rules.md` - X 2026 algorithm rules
- `references/threads-platform-rules.md` - Meta Threads algorithm + cross-post rules

## Examples

- `examples/track-record-tweet.md` - история применений + catch_rate metric

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/04-review.md`):**

- X tweet >280 chars (если не `--long`) → fail
- Threads post >500 chars → fail
- Em-dash «-» внутри строк → fail (memory `[[feedback-no-em-dash]]`)
- «Instagram» → auto-correct «Нельзяграм» (RU only)
- Запретные термины («artifact» / «digital-twin» / «Grand Slam Offer» / «КЭВ» / «связки») → fail
- Hashtags >0 → fail (X 2026 algorithm penalty)
- Links в hook tweet (не Threads chain closer) → warning
- Thread: hook tweet >220 chars → warning (need room для thread indicator)
- Восклицательных знаков >1 → warning
- AI-tells EN ("delve" / "tapestry" / "in conclusion" / "ensure") → fail

**Hook Char Zone Gate (v1.0, понижен до WARN каноном формы v2):**
- Zone A: 40-100 chars (short punch) OR Zone B: 200-280 chars (compressed narrative)
- **Dead zone: 100-200 chars → WARNING плюс одна строка обоснования** (было fail). Зоны взяты из чужого исследования Welsh/Bloom/Cole и с нашими данными не сверены: у нас измерена не длина хука, а его **состав**. Блокировать чужим порогом запрещено
- **Состав хука по цели формы (то, что измерено):**
  - `form_goal = forwards` (F, репосты): **цифра или валюта в хуке обязательна** (63% верха против 20% низа), хук не короче 50 знаков, цель 64. Короткий интригующий хук в этом треке мёртв: получателю не за что зацепиться
  - `form_goal = reactions` (R): в первой строке **нет числа ≥1000 и нет круглой метрики канала** (подписчики, просмотры, выручка), `+` первым знаком запрещён - чистое поле держат 93% верха. Хук - сцена или парадокс, ориентир 60 знаков (≤60 у 70% верха)
  - `form_goal = sales` (S): цель 36 знаков, ориентир 50 (держат 62% верха, поэтому печать, а не блок); в самом хуке **нет связки «ты/твой/вы + сумма»** - это HARD, 0/34 в верхе против 3/34 у низа
  - `form_goal` пуст → цель не объявлена, это отдельный HARD FAIL (Гейт 0, канон §9), а не WARNING: выдача блокируется до возврата в `01-router.md` Step 5.5 FORM-GOAL ROUTER, состав хука по старым зонам при этом не оценивается

**Thread Length Gate (NEW, v1.0):**
- Compact: 8-15 tweets OR Mega: 18-34 tweets
- **Awkward middle 3-7 tweets → fail** (confirmed research)

**6-Pass Refinement (LLM):**
Skeptic / Expert / Scroller / Competitor / Editor / Thumbnail - адаптировано под X+Threads.

**Maxwell Ross 9-Item Checklist:**
9 yes/no вопросов pre-publish.

**3 слоя финальный gate** - обязательно перед output.

## Принципы

0. **ПОРЯДОК ИСТОЧНИКОВ ФОРМЫ (канон формы v2 §8.1).** Уровень выше **переписывает** уровень ниже, а не дополняет. Конфликт разрешается вслух строкой-уликой `конфликт: <правило A> vs <правило B> -> взял <A> по уровню N`:

   1. Реальность и факты, запрет выдумки
   2. Прямое указание автора в этой сессии
   3. Голос автора (`_voice-profile.md`, корпус `A-telegram/`) - лексика, интонация, табу
   4. Слой 0 «Деньги» и Sales Gate - только при `launch_window = true`
   5. **`.business/voice-corpus/_format-canon-v2.md`** - канон формы под цель
   6. `.business/voice-corpus/_donor-format-canon.md` v1 - **отменён как источник норм**, остаются только неизмеренные наблюдения слоя «приёмы подачи», и то как гипотезы
   7. **Плоские дефолты этого скилла - fallback там, где молчат уровни 5 и 6.** Сюда явно относятся: **Hook Char Zone Gate**, Thread Length Gate, таблицы длин по типам, пороги приёмов, потолки списков, шаблоны `templates/*`
   8. Generic-каркасы (Брансон, atomic essay, 15 LinkedIn-хуков)

   **Механика override:** блокирующий пункт канона снимается ровно одним способом - строкой `конфликт: <пункт канона> vs <правило уровня N> -> взял уровень N` плюс дословная цитата правила уровня N. Нет строки - блок остаётся. Ссылка на уровень 6, 7 или 8 override не даёт: они ниже канона. **Пустой `brief.form_goal` - это не откат на уровень 7, а `form_mode: FAIL` (Гейт 0, канон §9): выдача блокируется, пайплайн возвращается в `01-router.md` Step 5.5 FORM-GOAL ROUTER за целью, а не продолжает писать по плоским дефолтам скилла.**

1. **Portable by config.** Один скилл работает у автора и у ученика. Различие - только `config.md` и данные проекта.
2. **Voice over format.** Стилистика автора важнее структуры. Если шаблон ломает голос - голос побеждает.
3. **Single idea per post.** Один tweet = один тезис. Multi-тезисные → split на mini-thread.
4. **Hook carries 80%.** Первая строка - всё. При объявленной цели хук строится по профилю канона (уровень 5), Hook Char Zone Gate работает как WARN-ориентир уровня 7. `formula_id` шаблона при объявленной цели - опциональное поле, а не условие PASS.
5. **Bimodal char rule - ориентир, не закон.** 40-100 OR 200-280 остаётся дефолтом уровня 7 при пустой цели. При объявленной цели решает состав хука из профиля (F цифра обязательна, R чистое поле без крупной метрики, S без «ты + сумма»), зона даёт WARNING.
6. **Bimodal thread rule.** 8-15 compact OR 18-34 mega. Никаких 3-7.
7. **Newsletter / community CTA в thread closer.** Welsh/Bloom/Cole pattern.
8. **Cross-post X → Threads identical** (Cheung pattern) с 280→500 expansion adapt.
9. **No hashtags / no emoji storm в hook** - universal 2026.
10. **Карта смыслов = source of truth для Mode A.** Не дополнять, не выдумывать.
11. **Transcript = verbatim quote, не парафраз** (Mode C).
12. **Maxwell Ross 9-checklist gate.** Никакой output без 9/9 PASS.
13. **3 слоя проверки.** Обязательно перед output.
14. **Внутрянка после поста.** Каждый output включает блок «Как писал»: Mode / platform / type / hook pattern / char zone / archetype / voice cluster / что отброшено / A/B логика.

## Portability - для ученика курса

Ученик клонирует папку и заменяет ТОЛЬКО:

1. **`config.md`** - пути и лексика под свой проект (онboarding делает это автоматически)
2. **`examples/gold-standard-<your-name>.md`** - свои лучшие посты (5-10)
3. **`intake/`** или `.business/` - `avatar.md` / `jtbd.md` / `brand-dna.md` / `products/`

Что НЕ трогаем:
- `workflow/*` - общая методология
- `references/*` - research база (Maxwell Ross / hooks / archetypes / AI-tells)
- `templates/*` - 7 шаблонов типов

## Anti-patterns (универсальные X 2026)

- Hashtags (universal penalty)
- Emoji storms 🚀💯🔥 в hook
- Engagement bait ("RT if you agree")
- 100-200 char hooks (dead zone) - **WARN, не fail**: порог из чужого исследования, каноном формы v2 понижен (см. Hook Char Zone Gate выше)
- 3-7 tweet threads (awkward middle)
- Long links в hook tweet
- Generic "Hard work pays off" без specifics
- AI-tells EN ("delve" / "tapestry" / "in conclusion")
- Em-dash «-» внутри строк (memory)
- «Instagram» вместо «Нельзяграм» (RU only)
- Negative статистики в публичном
- Имена конкурентов в attack (Common Enemy = явление)
- Self-quoting ("As I always say") - Hormozi/Naval anti-pattern
- Visual concept post (→ `single-image` type=concept-diagram)
- Stripe screenshot post (→ `single-image` type=dashboard-screenshot)

## Absorbed deprecated skills

- `paips-post` → `tweet` type=paips-story (template `templates/paips-story.md`)
- `spiky-one-liner` → `tweet` type=spiky-oneliner (template `templates/spiky-oneliner.md`)
- `stripe-screenshot-post` → УЖЕ deprecated, ушёл в `single-image` type=dashboard-screenshot
- `visual-concept-square` → УЖЕ deprecated, ушёл в `single-image` type=concept-diagram

## Memory cross-refs

- `[[feedback-no-em-dash]]` - em-dash запрещён внутри строк
- `[[feedback-no-tech-jargon-no-anglicisms]]` - без жаргона / англицизмов
- `[[feedback-no-negative-stats-in-public-offer]]` - без негативных статистик
- `[[feedback-verbatim-quote-transfer]]` - Mode C дословный перенос
- `[[project-viral-hook-library-2026]]` - base 8 X hook patterns
- `[[post]]` - параллельный skill для TG+LinkedIn narrative
- `[[longform]]` - параллельный skill для 800-3000 слов
- `[[single-image]]` - параллельный skill для visual concept / dashboard / meme / quote-card / before-after
- `[[email]]` - параллельный skill для email
- `[[bot-message]]` - параллельный skill для TG bot push
- `[[multi-language-localization]]` - для RU ↔ EN cultural adaptation

## Версия

**Текущая:** 1.2 (2026-05-28) - Bare-imperative staccato patch.

**Changelog:**
- **v1.2 (2026-05-28):** Added Tier 1F **Bare-imperative staccato pairs/triples** в `ai-tells-ru.md` ("Сначала X. Потом Y." / "X. И всё." / "Делай. Тестируй. Запускай." / 10+ паттернов с regex). Расширен `config.md` banned_terms.ru staccato фразами. Updated G6b в `04-review.md` с Tier 1F + ссылкой на Humaniser final phase. Прецедент: skill v1.1 пропустил "Сначала продукт. Потом контент." - близкий родственник triple-negation который v1.1 не покрыл.
- **v1.1 (2026-05-28):** Added `references/ai-tells-ru.md` (60+ RU AI-tell patterns, 5 tiers) + `references/ru-grammar-russification.md` (EN→RU calque rules). Split G6 на G6a/b/c bilingual. Added Pass 2.6 RU Russification. Прецедент: v1.0 пропустил "Что важно сделать первым - X. Не Y. Не Z." + "shipped" / "делают результат".
- **v1.0 (2026-05-28):** Initial release. 7 типов / 4 ortho axes / 15 hook patterns / 4 thread skeletons / Hook Char Zone Gate + Thread Length Gate.


**SemVer:**
- MAJOR: breaking change в output формате или 7 типах
- MINOR: новый template / новый mode / новый reference
- PATCH: уточнение validators, новые AI-tells, fix refs

**Когда пересматривать:**
- catch_rate в track-record < 80%
- X / Threads algorithm change (quarterly check)
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации под автора
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
- `~/.claude/skills/post/` - sibling skill для TG+LinkedIn narrative (reference architecture)

## Empirical patterns layer (NEW 2026-05-28)

Этот skill интегрирован с shared empirical layer для всех content-skills.

**Mandatory Reads в Pass 0** (пути боевые, `~/IvanOS/...`; `~/.business` - симлинк на шаблон IvanOS, читать оттуда запрещено):
- `.business/growth/extracted-patterns/INTEGRATION.md` — что читать для этого скилла
- `.business/growth/extracted-patterns/hook-patterns-empirical.md` — 9 patterns из 30 corpus
- `.business/growth/extracted-patterns/voice-markers-empirical.md` — Greg/Riley/Sabrina + авторская calibration
- `.business/growth/extracted-patterns/audience-glossary.md` — agent-jargon → язык RU ЦА
- `.business/growth/extracted-patterns/funnel-awareness.md` — куда ведёт content
- `.business/voice-corpus/_format-canon-v2.md` — **канон формы v2** (уровень 5 иерархии, см. Принцип 0). Читается в `03-write.md` Pass 0 п.4, применение проверяется уликой формы в `04-review.md`

**Benchmark Gate** в review stage:
- Compare output vs nearest 3 examples из `benchmark-corpus-index.md`
- Score /6 для text-only OR /7 для visual
- Cutoff: 4+/6 (text) | 5+/7 (visual) = PASS

Root cause fix: до 2026-05-28 references зашивали теорию виральности из памяти. Shared layer = empirical extraction из 30 real viral шортов в авторской нише.
