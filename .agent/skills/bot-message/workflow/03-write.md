# 03 - Write (draft + voice + button microcopy)

> Превращает scaffold в готовый текст push + готовый button microcopy. Голос автора > причёсанность.

## Вход

От `02-structure.md`:
- Scaffold (hook + body + CTA + buttons placeholder)
- Тип сообщения
- Hook framework
- Сегмент аудитории
- Must-keep лексика (от Mode C - дословные обороты автора)
- Контекст

## Pass 0: Mandatory reads (без них NoVoice)

Перед draft - обязательно прочитать:

1. `paths.voice_reference_long` (cross-ref на `post/examples/_TEMPLATE.md`) - для общего голоса
2. `paths.voice_reference_bot` (`examples/_TEMPLATE.md`) - для bot-специфики (если файл существует, иначе fallback на (1))
3. `references/_voice-TEMPLATE.md` - анти-паттерны и bot-адаптация
4. `~/.claude/skills/post/references/_voice-TEMPLATE.md` - живые глаголы / 26 классов banned AI-конструкций

Без этих Read'ов Voice Fidelity Gate в `04-review.md` failит.

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`.
- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.


## Pass 0.5: PII redaction enforcement (Action-skill Gate C)

bot-message - **action skill** (push зовёт к non-reversible действию). Truth verification mandatory.

Применить `config.privacy.pii_patterns` к КАЖДОМУ файлу контекста ПЕРЕД использованием в draft.

### Шаг 0.5.1: Read config.privacy

- `redact_pii_in_context` (must `true`, иначе hard fail с warning)
- `pii_patterns` (список regex)
- `skip_files` (allowlist)

### Шаг 0.5.2: Применить regex к контенту

```python
for pattern in config.privacy.pii_patterns:
    content = re.sub(pattern, config.privacy.replace_with, content)
```

### Шаг 0.5.3: Расширенные PII классы для action skill

Дополнительно redactить если файл `is_private: true`:

- Финансовые snapshots: `\$\s?\d{1,3}[KMB]?`, `\d+\s?(тыс|млн|K|M|B)`
- Subscriber counts из private files
- Personal timestamps («$280K на счёте», «100K MRR»)

НЕ redactить если в `paths.products.pricing` (там цены публичные).

### Шаг 0.5.4: Audit trail

В внутрянку: `PII redaction: N matches replaced from <files>`

## Pass 0.6: Event existence check (Action-skill Gate B)

Если в draft упоминается event - **verify ИЛИ require user confirm**.

### Шаг 0.6.1: Detect event mentions

Regex по draft:
- `\b(workshop|воркшоп)\b`
- `\b(live|эфир|стрим)\b`
- `\b(вебинар|webinar)\b`
- `\b(запуск|launch|релиз)\b`
- `\b(марафон|тренинг)\b`
- `\b(окно (продаж|регистрации))\b`
- Конкретные даты: «<число> <месяц>», «завтра в <время>»

### Шаг 0.6.2: Verify match

Для каждого detected event:

1. Search в `.business/запуски/<active>/` (любой `.md`)
2. Search в `config.bot.upcoming_events`
3. Mode C → check в `raw_transcript` (user-source = OK override)

Match → **PASS**, использовать детали из источника.

Match НЕ найден → **STOP**, output:

```
WARNING: Event «<name>» упомянут в draft, но не найден в:
- `.business/запуски/<active>/`
- `config.bot.upcoming_events`
- transcript (если Mode C)

1. Реальное событие, но не зафиксировано - подтверди детали?
2. Outdated - удалить?
3. Выдумал - переформулировать?

Без подтверждения - НЕ генерирую (защита от ложных обещаний).
```

### Шаг 0.6.3: Audit trail

В внутрянку: `Event verification: <event> → <source> / confirmed / UNVERIFIED`

## Pass 0.7: Fact verification (Action-skill Gate A)

Для каждого числа / даты / именованного утверждения - match ИЛИ flag UNVERIFIED.

### Шаг 0.7.1: Extract facts

Regex по draft:
- Числа с единицами: `\b\d+\s?(человек|учеников|подписчиков|месяцев|лет|часов|покупок|тысяч|млн)\b`
- Денежные суммы: `\b\$\s?\d+`, `\b\d+\s?[Rr]?\s?руб\b`, `\b\d+\s?[Kk]\s?(USD|EUR|RUB|\$|€|₽)`
- Конкретные даты: `\b\d+\s?(января|февраля|...|декабря)\b`
- Именованные сущности: brand / product names

### Шаг 0.7.2: Verify

```
SOURCES = [
  config.paths.avatar,
  config.paths.products_dir/*,
  config.paths.brand_dna,
  config.paths.business_index,
  raw_transcript (если Mode C)
]

for fact in extracted_facts:
    if not any(fact in read(s) for s in SOURCES):
        flag(fact, "UNVERIFIED")
```

### Шаг 0.7.3: Если UNVERIFIED ≥1

**STOP**, output:

```
WARNING: Следующие утверждения не verified:
- «<quote>»
- «<quote>»

Подтверди или отредактируй draft.

Без подтверждения - НЕ генерирую финальный push.
```

### Шаг 0.7.4: Audit trail

В внутрянку: `Fact verification: N checked, M verified, K UNVERIFIED → <action>`

## Pass 1: Draft текста

### Шаг 1.1: Hook (первые 50 знаков)

Hook должен:
- Содержать смысл (не «А вот и я снова»)
- Быть читаем в notification preview (iOS ≈ 50, Android ≈ 95)
- Не начинаться с эмоджи (отдельные клиенты могут резать)
- Не содержать восклицания

Hook-templates по framework (RU + EN):

| Framework | RU example | EN example |
|---|---|---|
| Numbered | «3 ошибки воронки, которые ты делаешь» | «3 funnel mistakes you make» |
| Contrarian | «забудь про A/B тесты на push» | «forget A/B testing your push» |
| Vulnerable | «потерял 30% базы за неделю» | «lost 30% of my list in a week» |
| Results-First | «12% CTR на этом push - вот хук» | «12% CTR on this push - here's the hook» |
| Curiosity-Gap | «один push принёс 47 покупок» | «one push, 47 purchases» |
| Myth-Busting | «push не работает, если…» | «push fails if you…» |
| Question-Hook | «знаешь почему open есть, а кликов нет?» | «know why opens are high but clicks aren't?» |
| Time-Trigger | «через 1 час старт» | «kicks off in 1 hour» |

### Шаг 1.2: Body (50-220 знаков от hook'а)

Body доводит от hook'а к CTA:
- 1-2 коротких предложения
- Без воды
- Без metaphor abuse
- Конкретика > абстракция

### Шаг 1.3: CTA-bridge (опционально, 0-30 знаков)

Тонкая связка от body к кнопке. Часто не нужна - кнопка сама делает affordance. Если нужна - короткая стрелка:
- «↓ открой»
- «детали в кнопке»

**Запрет:** «жми кнопку», «нажми сюда», «тапни» - это дублирование affordance.

## Pass 2: Voice injection

После draft пропустить через voice-фильтр:

### 2.1 - Заменить generic на bookmarked terms (из config.banned_terms)

- «Instagram» → «Нельзяграм»
- «программист» → «эксперт» / «соло-предприниматель»
- generic CTA «Узнать» → конкретный глагол + объект

### 2.2 - Inject автора-специфичную лексику (если применимо)

Из `post/references/_voice-TEMPLATE.md` 16 уникальных терминов. Не пихать насильно, но если контекст позволяет - использовать:
- контент-завод / контент-ферма
- вайбкодинг / вайбмаркетинг
- перегнать / пдп
- Нельзяграм / Дубайск

### 2.3 - Living language pass

Из `post/references/_voice-TEMPLATE.md`:
- Живые глаголы вместо AI-канцеляризма
- Запрет на 26 классов banned AI-конструкций (A-Z)
- Paragraph connectivity (если есть >1 предложение - переход между ними естественный)

### 2.4 - Mode C - must-keep verbatim

Если был Mode C - проверить что все must-keep обороты автора попали в финальный текст. Если нет - переписать body с их включением.

## Pass 3: Button microcopy

Для каждой кнопки из scaffold подобрать текст 8-24 знака:

### Структура текста кнопки

`<Глагол действия> + <Объект>`

| Тип CTA | RU example | EN example | Длина |
|---|---|---|---|
| Открыть материал | «Открыть разбор» | «Open breakdown» | 14 / 14 |
| Получить lead magnet | «Забрать промпт» | «Get the prompt» | 14 / 14 |
| Зарегистрироваться | «Иду на вебинар» | «I'm in» | 14 / 6 |
| Подтверждение присутствия | «Иду» | «I'm in» | 3 / 6 |
| Откладывание | «Напомнить позже» | «Remind later» | 15 / 12 |
| Покупка | «К оплате» | «Pay now» | 8 / 7 |
| Сегментация | «Я только начал» | «Just starting» | 15 / 13 |

### Запретные кнопки (auto-fail)

- «Узнать», «Подробнее», «Click here», «Сюда», «Тык» - без контекста
- «OK», «Да», «Нет» - без объекта
- «Ссылка» - что за ссылка
- «👉», «🔥» в одиночку - эмоджи без слова

### Кнопка-тип в JSON

| RU button text | tg-bot type | JSON поле |
|---|---|---|
| «Открыть Skool» | URL | `"url": "https://skool.com/..."` |
| «Забрать промпт» | callback | `"callback_data": "get_prompt_v1"` |
| «Открыть мини-апп» | web_app | `"web_app": {"url": "https://..."}` |
| «К оплате» | pay | `"pay": true` |

## Шаг финал: scaffold → готовый блок

После Pass 0-3 у тебя:

```
TEXT (готовый):
<100-300 знаков, прошедшие voice injection>

BUTTONS (готовые microcopy):
- Текст: «<8-24 знака>», Тип: <URL/callback/web_app/pay>, Назначение: <куда>
- (если 2-3 кнопки) то же для каждой

A/B альтернатива:
<альтернативная формулировка hook'а или альтернативная кнопочная стратегия>

Внутрянка (для блока «как писал»):
- Hook framework: <использованный>
- Body approach: <какое наблюдение / переход>
- Button strategy: <выбранная>
- Что отброшено: <если был выбор между формулировками>
```

Передать в `04-review.md` для финального gate.

## Anti-patterns Write

- **Не писать draft без Pass 0**. Без mandatory reads голос будет generic - это закроет Voice Fidelity Gate в review с fail.
- **Не оптимизировать длину до достижения смысла**. Сначала смысл, потом - режем лишнее. Если режу к 200 знакам и теряю hook - лучше 230 знаков с hook'ом.
- **Не использовать metaphor abuse**. Глаголы в небуквальном значении («сжигает», «ломает», «выстрелил») в коротком формате читаются как невнятица.
- **Не дублировать сам CTA**. Если кнопка «Открыть разбор» - в тексте не пишем «нажми чтобы открыть разбор».
- **Не использовать «просто», «довольно», «достаточно», «по сути», «буквально», «сразу же», «вот»** - banned filler.
- **Не делать восклицания**. 0 восклицательных знаков в push (см. config.voice.exclamation_max).
---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
