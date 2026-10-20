# workflow/03-write.md

> Draft + voice injection. Pass 0 mandatory reads → Pass 1 draft → Pass 2 voice/living-language injection.

## Pass 0 - Mandatory Reads (BEFORE draft)

**Без этих Read'ов Voice Fidelity Gate в `04-review.md` failit.** Это не опция.

| Read | Источник | Зачем |
|---|---|---|
| 1. `examples/_TEMPLATE.md` | по brief.language | few-shot эталон voice |
| 2. `config.paths.tg_content_voice` → `~/.claude/skills/post/references/_voice-TEMPLATE.md` | post references | уникальные термины (16) / антипаттерны (11) / приёмы (5) |
| 3. **HARD MANDATORY** `~/.claude/skills/post/references/_voice-TEMPLATE.md` | post references | **98 классов AI-tells на 7 уровнях** + 28 ban list. Grep по каждому ключевому классу (PH-1, PH-3, PH-7, PH-9, PH-20, PH-25, ST-1, S-5, L-7, L-5, PH-14). Не self-eval |
| 4. `config.md` + `config-lexicon.md` | этот skill | пути / voice params / lexicon |
| 5. `templates/<brief.type>.md` | этот skill | каркас + style guide для типа |
| 6. (опционально для launch-sequence) `references/launch-sequence-frameworks.md` | этот skill | PLF / Halbert / Welsh sequence patterns |
| 7. **HARD MANDATORY** `.business/voice-corpus/_format-canon-v2.md` | .business | **канон формы v2: форма выбирается под цель** (пороги: 296 чистых постов двух TG-доноров, окно 12 мес; третий донор - слой наблюдений §10). Читать §0-§5 и §9. Для письма брать: профиль цели (R реакции / F репосты / S продажа), коридор длины, число выделений жирным, потолок списков, правила ссылок, конструкцию хука (Subject строится по профилю цели: R кадр или ярлык, F опись с цифрой, S ярлык или квитанция), функцию финала (R вывод и закрытая петля, F адрес в хвосте, S живая реплика, не URL). **Нижняя граница медианы предложения:** в классе «разбор» не ниже **5** слов при цели 5.5 (канон §3.1 п.10); в нарративе пункт не применяется (6 против 6, не различает). НЕ брать: TG-типографику, механики реакций как приём письма (§7 - отдельный инструмент режима A), сигнатуры доноров, факты и цифры доноров |
| 8. `.business/voice-corpus/_donor-format-canon.md` | .business | канон формы v1, **ОТМЕНЁН как источник норм** каноном v2. **Не обязательный вход.** Читать только как fallback там, где v2 молчит: слой «приёмы подачи» (в v2 не измерялся, гипотезы низкого ранга). Числовые нормы v1 (500-1700 знаков, «жирный почти всегда», «медиана 5-6 слов») к применению запрещены - их перекрывает профиль цели v2 §3 |

**Приоритет источников формы (трёхзвенный, канон §8.1):** голос автора (входы 1-3, `_voice-profile.md`) **>** канон формы v2 (вход 7) **>** донор-канон v1 (вход 8, только там, где v2 молчит). Голос при конфликте побеждает всегда. Ниже канона формы стоят плоские дефолты этого скилла (`config.md`, шаблоны типов) - они fallback там, где молчит канон. Конфликт разрешается вслух строкой `конфликт: <A> vs <B> -> взял <A> по уровню N`

После Read'ов - записать в чат одну строку:

```
Pass 0 done: voice + living-language + lexicon + template loaded.
```

Без этой строки → не начинать draft.

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`.
- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.
- **Улика канона формы (HARD).** Отдельной строкой обязательно: `прочитал→взял: канон формы v2 → цель=<reactions/forwards/sales> (<R/F/S>), класс=<narrative/razbor/sales>, профиль <длина/жирный/списки/ссылки>`. Строки нет → output запрещён. Значение цели - СЛОВО из `brief.form_goal` (дерево канона §2.1), буква из `brief.form_goal_letter` идёт в скобках только для человека и ни с чем не сравнивается. Поле `form_goal` пусто → печатать `цель=не объявлена -> возврат в 01-router.md Step 5.5 FORM-GOAL ROUTER` и НЕ писать draft: работа на старых порогах `config.md` и шаблона типа без объявленной цели запрещена


## Pass 0.5 - PII redaction enforcement (Action-skill Gate C)

email - **action skill** (письмо зовёт к non-reversible действию: клик → лендинг → покупка). Truth verification mandatory.

Применить `config.privacy.pii_patterns` к КАЖДОМУ файлу контекста ПЕРЕД использованием в draft.

### 0.5.1: Read config.privacy

- `redact_pii_in_context` (must `true`)
- `pii_patterns` (regex list)
- `skip_files` (allowlist)

### 0.5.2: Применить regex к контенту

```python
for pattern in config.privacy.pii_patterns:
    content = re.sub(pattern, config.privacy.replace_with, content)
```

### 0.5.3: Расширенные PII классы для email

Дополнительно redactить если файл `is_private: true`:

- Финансовые snapshots: `\$\s?\d{1,3}[KMB]?`, `\d+\s?(тыс|млн|K|M|B)`
- MRR / ARR snapshots из private revenue files
- Personal subscriber lists / emails

НЕ redactить если в `paths.products.pricing` (публичные цены).

### 0.5.4: Audit trail

В internals: `PII redaction: N matches replaced from <files>`

## Pass 0.6 - Event existence check (Action-skill Gate B)

Если в draft упоминается event (workshop / live / эфир / запуск / вебинар / окно / марафон / cohort / cash event) - **verify ИЛИ require user confirm**.

### 0.6.1: Detect event mentions

Regex по draft (Subject + Preheader + Body + CTA):
- `\b(workshop|воркшоп)\b`
- `\b(live|эфир|стрим)\b`
- `\b(вебинар|webinar)\b`
- `\b(запуск|launch|релиз|cash event)\b`
- `\b(марафон|тренинг|cohort)\b`
- `\b(окно (продаж|регистрации|оплаты))\b`
- Конкретные даты: «<число> <месяц>», «через <N> дней», «сегодня в <время>»

### 0.6.2: Verify match

1. Search в `.business/запуски/<active>/` (любой `.md`)
2. Search в `config.email.upcoming_events`
3. Mode C → check в `raw_transcript`

Match → **PASS**.

Match НЕ найден → **STOP**:

```
WARNING: Event «<name>» в draft, но не найден в:
- `.business/запуски/<active>/`
- `config.email.upcoming_events`
- Mode C transcript (если применимо)

Действия:
1. Подтверди дату/время/куда ведёт?
2. Удалить из draft?
3. Переформулировать без анонса event?

Без подтверждения - НЕ генерирую финальный email (защита от ложных обещаний базе).
```

### 0.6.3: Audit trail

В internals: `Event verification: <event> → <source> / confirmed / UNVERIFIED`

## Pass 0.7 - Fact verification (Action-skill Gate A)

Для каждой цифры / даты / именованного факта в draft - match ИЛИ flag UNVERIFIED.

### 0.7.1: Extract facts

Regex по Subject + Preheader + Body + CTA:
- Числа с единицами: `\b\d+\s?(человек|учеников|подписчиков|месяцев|лет|часов|покупок|тысяч|млн)\b`
- Денежные суммы: `\b\$\s?\d+`, `\b\d+\s?[Rr]?\s?руб\b`, `\b\d+\s?[Kk]\s?(USD|EUR|RUB|\$|€|₽)`
- Конкретные даты: `\b\d+\s?(января|февраля|...|декабря)\b`
- Именованные сущности: brand / product / случаи из своей базы / имена клиентов

### 0.7.2: Verify

```
SOURCES = [
  config.paths.avatar,
  config.paths.products_dir/*,
  config.paths.brand_dna,
  config.paths.business_index,
  config.paths.testimonials,
  raw_transcript (если Mode C)
]

for fact in extracted_facts:
    if not any(fact in read(s) for s in SOURCES):
        flag(fact, "UNVERIFIED")
```

### 0.7.3: UNVERIFIED ≥1 → STOP

```
WARNING: Следующие утверждения в email не verified:
- «<quote>» (в Subject / Body / CTA)
- ...

Подтверди или удалить.

Без подтверждения - НЕ генерирую финальный email.
```

### 0.7.4: Audit trail

В internals: `Fact verification: N checked, M verified, K UNVERIFIED → <action>`

## Pass 1 - Draft

### Step 1.1 - Draft Subject A/B variants

Сгенерировать 3-5 Subject вариантов из `02-structure.md` brief.subject_variants. Применить voice (а не generic email Subject formulas):

- Использовать лексику из `~/.claude/skills/post/references/_voice-TEMPLATE.md`
- Hook frameworks из `references/subject-formulas-50.md`
- Длина ≤50 chars (mobile-first)
- Проверить spam-trigger words

Output: список subject_variants с финальным текстом.

### Step 1.2 - Draft Preheader

50-90 chars, не дублирует Subject. Если language=both → отдельный preheader для RU + EN.

### Step 1.3 - Draft Body

По skeleton из `02-structure.md` brief.body_skeleton. По секциям, в порядке.

**Правила Pass 1:**

- Длина по word_allocations (±20% per section)
- Voice = автора RU (из gold-standard + ivan-voice). НЕ generic email копирайтинг.
- Plain-text bias (Kit). Без HTML-зависимого смысла. Жирный/курсив - через символы (плюсы/минусы), не через теги.
- 1/3/1 rhythm (первая строка короткая, тело - чередование длин, финал - короткий + CTA)
- Mobile-first: первый параграф ≤200 chars (above-fold preview)
- Один CTA-goal, в местах из brief.cta_positions
- Source quotes (если Mode C) - **дословно** вставить из brief.source_quotes
- Avoid banned terms (lexicon)
- Avoid metaphors (см. _voice-TEMPLATE anti-patterns)

### Step 1.4 - Draft CTA

CTA text + link (placeholder если нет реального URL). Для sales-letter - повторяющиеся CTA (above-fold + bottom + p.s.) с одним и тем же link, но разными hooks ("Забронировать место", "Перейти к оформлению", "Last call: оформить").

## Pass 2 - Voice Injection + Living Language

### Step 2.1 - Voice Injection

Прочитать draft и переписать каждый параграф через filter:

- Удалить generic email copywriting шаблоны ("I hope this finds you well" / "Just a quick note")
- Заменить generic verbs на живые из `~/.claude/skills/post/references/_voice-TEMPLATE.md`
- Inject 1-2 уникальных термина автора из _voice-TEMPLATE.md (вайбкодинг / вайбмаркетинг / контент-завод / Нельзяграм)
- Применить 1/3/1 rhythm если нарушен

### Step 2.2 - Living Language check (per-paragraph)

Для каждого параграфа проверить через 26 classes из _voice-TEMPLATE.md:

- Class A: метафоры (запрещены)
- Class B: corporate phrases (запрещены)
- Class C: generic AI tells (запрещены)
- ... (все 26 классов)

Если хотя бы один параграф failит → переписать.

### Step 2.3 - Paragraph connectivity

Проверить flow между параграфами:

- Каждый параграф логически вытекает из предыдущего
- Нет abrupt темной смены
- Bridge phrases присутствуют (но без cliché bridges типа "And here's the kicker")

### Step 2.4 - EN version (если language=both)

Если brief.language=both:

- Прочитать `[[multi-language-localization]]` правила
- НЕ дословный перевод. Культурная адаптация:
  - Subject: переписать с EN hook frameworks (Welsh / Halbert)
  - Preheader: переписать с EN copywriting воркинга
  - Body: переписать с сохранением big idea + voice, но EN-native style (короче параграфы, more direct, less rhetorical)
  - CTA: EN voice ("Get the playbook" / "Join now" не «Получить плейбук»)
- Использовать `examples/_TEMPLATE.md` как voice reference (если есть)

## Output Pass 2

```yaml
draft:
  subject_variants: [{framework, text}, ...]
  preheader_ru: "..."
  preheader_en: "..."  (если both)
  body_ru: "<full body draft>"
  body_en: "<full body draft>"  (если both)
  cta_text_ru: "..."
  cta_text_en: "..."  (если both)
  cta_link: "<url>"
  cta_positions: [...]
  words_count_ru: N
  words_count_en: M
```

→ `workflow/04-review.md`.

## Anti-patterns Pass 0+1+2

- НЕ начинать draft без Pass 0 mandatory reads (Voice Fidelity Gate failit)
- НЕ генерировать draft в первом проходе, потом «подгонять voice» - voice идёт сразу с Pass 1, Pass 2 только полирует
- НЕ парафразить source_quotes из Mode C - дословный перенос (см. `[[feedback-verbatim-quote-transfer]]`)
- НЕ выходить за `target_words_max` - fail
- НЕ переключать language в середине письма (одно письмо = один язык; both = два отдельных файла output)
- НЕ оставлять placeholder CTA-link «{LINK}» в финальном output - пользоваться config или просить URL
---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
