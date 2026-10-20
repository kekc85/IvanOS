# 03-write - draft + voice injection

> Принимает `structure_output`. Производит draft версии 1, затем applies voice injection (Pass 1 → Pass 2). Output = draft для `04-review.md`.

## Pass 0 - Mandatory reads (BLOCKING)

Перед написанием первого слова обязательно прочитать:

1. `examples/gold-standard-<subject.name>-longform.md` - эталоны voice автора (3-5 длинных текстов)
2. `paths.voice_reference` из config (если задан отдельно)
3. `paths.voice_corpus_dir/*` - образцы голоса
4. `config.md` - секция `voice.*` и `lexicon_*`
5. `config-v1.1-extension.md` (v1.1) - расширенные gates
6. `references/platform-specs.md` - раздел для `platform`
7. `references/ai-tells-longform.md` - что не делать
8. `references/anglicism-blocker-ru.md` (v1.1) - если language=ru
9. `references/techjarg-explain-list.md` (v1.1) - mandatory disclosure list
10. Template из `templates/<type>.md`
11. `.business/voice-corpus/_format-canon-v2.md` - **канон формы v2, форма выбирается под цель** (пороги: 296 чистых постов двух TG-доноров, окно 12 мес; третий донор - слой наблюдений §10). Читать §0-§5 и §9. Для longform брать: профиль цели (R реакции / F репосты / S продажа), архитектуру (длина, воздух, число выделений, списки, ссылки), конструкцию хука и функцию финала. НЕ брать: механики реакций как приём письма (§7 - отдельный инструмент режима A), TG-типографику, сигнатуры доноров, факты и цифры доноров.
    - **Нижняя граница медианы предложения:** в классе «разбор» медиана слов в предложении не ниже **5** при цели 5.5 (держат 11/12 верха, канон §3.1 п.10). В нарративе пункт не применяется: 6 против 6, признак не различает. Формулировки, поощряющие падение до 3 слов, к longform не применять
    - **Приоритет источников (трёхзвенный, канон §8.1):** голос автора (`_voice-profile.md`, gold-standard, п.1-4 выше) **>** канон формы v2 **>** `_donor-format-canon.md` v1 (только там, где v2 молчит). Голос при конфликте побеждает всегда. Конфликт разрешается вслух строкой-уликой `конфликт: <A> vs <B> -> взял <A> по уровню N`
12. `.business/voice-corpus/_donor-format-canon.md` - канон формы v1, **ОТМЕНЁН как источник норм** каноном v2. Не обязательный вход. Читать только как fallback там, где v2 молчит: слой Д «приёмы подачи» (рефрен, персонажи вместо абстракции, признание слабости перед сильным заявлением) - в v2 эти наблюдения не измерялись и являются гипотезами низкого ранга. Числовые нормы v1 (500-1700 знаков, «жирный почти всегда», «медиана 5-6 слов») к применению запрещены: их перекрывает профиль цели из v2 §3

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`.
- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.
- **Улика канона формы (HARD).** Отдельной строкой обязательно: `прочитал→взял: канон формы v2 → цель=<reactions/forwards/sales> (<R/F/S>), класс=<narrative/razbor/sales>, профиль <длина/жирный/списки/ссылки>`. Строки нет → output запрещён. Значение цели - СЛОВО из `brief.form_goal` (роутер, дерево канона §2.1), буква из `brief.form_goal_letter` идёт в скобках только для человека и ни с чем не сравнивается. Поле `form_goal` пусто → печатать `цель=не объявлена -> возврат в 01-router.md Step 5.5 FORM-GOAL ROUTER` и НЕ писать draft: работа на старых плоских порогах этого скилла без объявленной цели запрещена


**Voice Fidelity Gate (v1.2 - automated discovery, NO user dependency):**

**Old broken pattern (v1.1):** требовать у user `examples/gold-standard-<subject>-longform.md`. Это user-error моей стороны (incident 2026-05-28 v2).

**New pattern (v1.2):** Skill сам discovers voice signal через 4 public sources в `workflow/00-voice-signal-discovery.md`:

1. Author's public channels (автор's TG `<твой-хэндл>`, LinkedIn, blog) - primary 50%
2. Reference creators newsletter archives (Dan Koe, Welsh, Bloom, Cheung) via WebFetch - secondary 30%
3. RU competitors blogs (Замесин, RU TG-каналы) via WebFetch - tertiary 20% (language=ru)
4. Memory lexicon (`user_lexicon` + `post/references/ivan-voice` + `_voice-TEMPLATE`) - fallback fixed 20%

Voice Fidelity Score = weighted aggregate (0-100).

| Score | Action |
|---|---|
| ≥70 | PASS - proceed |
| 40-69 | WARN - proceed с warning в final output |
| <40 | LOW SIGNAL - proceed с suggestion `/longform --refresh-voice-signal` |

**NEVER STOP PIPELINE.** Voice signal is skill's responsibility, не user's. User не должен предоставлять corpus - skill discovers сам через WebFetch public sources.

Если `examples/gold-standard-<subject>-longform.md` существует - берётся как Source 0 (highest priority, fidelity weight 60%). Если отсутствует - discovery procedure из `00-voice-signal-discovery.md` запускается автоматически.

Если (4) `config.md` ИЛИ (5) `config-v1.1-extension.md` ИЛИ (10) template недоступны → FAIL pipeline (structural requirements, не voice).

**Anti-pattern (v1.2):** требовать у user предоставить voice corpus. Запрещено. Skill discovers сам.

## Pass 0.5 - Action-skill gates (conditional)

**Условие срабатывания:** если longform type **case-study** ИЛИ **listicle с launch-promo контекстом** (т.е. содержит обещание к non-reversible action: купить курс / войти в марафон / купить продукт).

**Detect:**
- type = case-study + brief.cta_goal содержит «купить» / «зарегистрироваться» / «join»
- type = listicle + контекст launch (active_launch в config + brief.angle упоминает offer)
- любая секция содержит конкретное упоминание event (workshop / live / окно продаж) с датой
- finale CTA = direct sale action

Если ни один признак не сработал → skip Pass 0.5, продолжать к Pass 1 как stylistic.

### Шаг 0.5.1 - PII enforce (Gate C)

Применить `config.privacy.pii_patterns` к каждому файлу контекста перед использованием в draft. Если config.privacy отсутствует - добавить из `~/.claude/skills/email/config.md` как template.

Особенно важно для longform: эссе часто включают screenshots / quotes из private dashboards / revenue snapshots → redact.

### Шаг 0.5.2 - Event existence (Gate B)

Detect event mentions в outline.sections + drafty:

Regex: `\b(workshop|воркшоп|live|эфир|стрим|вебинар|webinar|запуск|launch|релиз|марафон|тренинг|cohort|окно (продаж|регистрации|оплаты))\b` + конкретные даты.

Verify в:
1. `.business/запуски/<active>/`
2. `config.email.upcoming_events` (cross-skill reference) / `config.longform.upcoming_events`
3. Mode C raw_transcript

Match не найден → STOP с warning.

### Шаг 0.5.3 - Fact verification (Gate A)

Extract все числа / даты / именованные кейсы из draft. Verify против:
- `.business/INDEX.md`
- `.business/products/*`
- `.business/assets/testimonials.md`
- `.business/audience/avatar.md`
- raw_transcript (если Mode C)

UNVERIFIED ≥1 → STOP с warning списком.

**Особенность longform:** case-study эссе обычно построены вокруг конкретного результата ученика / своего. Если detail UNVERIFIED - либо подтвердить с источником, либо переписать без специфики (но это убьёт hook эссе → лучше подтвердить).

### Шаг 0.5.4 - Audit trail

В `output.internals`:
```
Action-skill check (longform):
- Type: <case-study | listicle | other>
- PII redaction: <N matches replaced>
- Event verification: <event> → <source>
- Fact verification: <N checked, M verified, K UNVERIFIED>
```

См. `~/.claude/skills/bot-message/workflow/03-write.md` Pass 0.5-0.7 для детального reference patterns.

## Pass 1 - Skeleton draft

Расписать outline в prose, секцию за секцией.

### Правила Pass 1

- Один section за раз. Не прыгать.
- Соблюдать `length_budget` с tolerance ±15%.
- Каждый bullet outline превращается в 1-3 параграфа.
- НЕ оптимизировать voice пока - pure structure.
- НЕ вставлять generic transitions («Now let me tell you», «А теперь самое интересное», «Но это ещё не всё») - banned list из config.lexicon_banned_longform.
- Numbers / examples - verbatim из brief.outline (не выдумывать).

### Особенности по type

**Teaching essay:**
- INSIGHT - главная часть. Механизм раскрывается на 2-3 уровня глубины.
- PROCESS - actionable step-by-step, каждый step тестируется «можно ли сделать после прочтения статьи?»

**Story essay:**
- INTRODUCTION расширена в полноценный story arc (setup → moment → tension)
- INSIGHT встроен в payoff story («и вот что я понял»)
- PROCESS компактный (lessons learned, не how-to)

**Framework essay:**
- INSIGHT доминирует - расписать framework как mental model (3-5 строительных блоков)
- PROCESS = как применить framework к конкретной ситуации
- Можно вставить ASCII-схему или 3-5 буллетов с компонентами framework

### Особенности по platform

- **Newsletter (Kit/Beehiiv):** добавить блоки `divider` между большими секциями, `quote` для main_aha (одна центральная цитата выделяется)
- **LinkedIn article:** короткие абзацы (1-3 строки), частые line breaks, bold для subheaders (НЕ H2/H3)
- **Blog:** стандартный Markdown, H2 для секций, H3 для подразделов внутри INSIGHT

## Pass 2 - Voice injection

После Pass 1 готов структурный draft. Pass 2 - injection voice автора.

### Правила Pass 2

1. **Lexicon swap** (auto):
   - Instagram → Нельзяграм (RU)
   - Любые `lexicon_required` replacements из config

2. **Banned list check** (regex):
   - Em-dash «-» внутри строки → replace на «-» / запятую / restructure
   - Banned terms из `post/config#lexicon_banned_hard` inherited → replace или restructure
   - Banned formulaic transitions из `longform/config#lexicon_banned_longform` → restructure

3. **Voice quirks** (из config.voice.voice_quirks):
   - Заменить абстракции на конкретные числа / имена / кейсы где возможно
   - Personal anchor должен быть в первых 2 абзацах если type=story; в первых 3 если type=teaching/framework
   - Контр-интуитивные открытия выделить в отдельные абзацы

4. **Archetype voice** (из config.voice.archetypes_allowed):
   - Magician - раскрытие механизма «как это работает изнутри»
   - Sage - учительская позиция «вот что я понял за <time>»
   - Outlaw - challenge mainstream «все делают X, и это неправильно»
   - **Banned archetypes** (Caregiver / Lover / Innocent) - фильтр на «мама-тон», «обнимашки», «ой так классно»

5. **RU vs EN structural pivot:**
   - **RU canonical:** story-first → INTRODUCTION expanded, INSIGHT теплее
   - **EN canonical:** argument-first → INSIGHT доминирует, INTRODUCTION tighter
   - См. `references/ru-en-adaptation.md`

### Pass 2.5 - Living Language injection (RU only)

Inherit from `post/references/_voice-TEMPLATE.md`. Применить:
- Живые глаголы вместо formal verbs («вкатил» → «начал», «забахал» → «сделал» - если автор сам не использует verbatim)
- Paragraph connectivity check - каждый абзац связан с предыдущим явной связью, не «а ещё», «и тогда»

## Pass 3 - Headline + CTA finalization

1. Из brief.headline_variants выбрать финальный (либо самый сильный по hook-test, либо явно указанный пользователем через `--headline=<n>`)
2. Если platform = newsletter - сгенерить 3 subject lines + 1 preheader (см. `references/platform-specs.md`)
3. CTA финализировать под platform:
   - Newsletter → «Подписаться / Forward / Reply with thoughts»
   - Blog → «Subscribe newsletter / Read related / Join club»
   - LinkedIn → «Follow / Comment / DM»

## Output для `04-review.md`

```yaml
draft_v1:
  headline: "<final>"
  subject_lines: ["<1>", "<2>", "<3>"]  # если newsletter
  preheader: "<>"  # если newsletter
  body:
    introduction: "<prose>"
    insight: "<prose>"
    process: "<prose>"
  cta: "<>"
  word_count: <N>
  language: "<>"
  platform: "<>"
  type: "<>"
  voice_signals_applied: [<list>]
  banned_terms_caught: [<list>]
```

## Что НЕ делать

- НЕ пропускать Pass 0 mandatory reads - без эталона voice будет generic AI prose
- НЕ генерить prose без structural skeleton - Pass 1 = skeleton, Pass 2 = voice. Не смешивать.
- НЕ применять voice quirks без archetype match - Sage не говорит как Outlaw
- НЕ переписывать verbatim quotes из brief (особенно из Mode C transcript) -

## Memory cross-refs

- - voice fidelity критична
- - конкретные числа > vague
- - раскрывать термины
- - verbatim цитаты
- - em-dash banned
- - без жаргона
---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
