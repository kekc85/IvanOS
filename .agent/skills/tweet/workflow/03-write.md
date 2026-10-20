# 03-write.md - Draft pass + voice injection

Принимает skeleton от 02-structure. Производит ready text.

## Pass 0 - Mandatory reads (HARD)

Read 3 obligatory files перед draft:
1. `examples/gold-standard-<author>.md` (если existed, иначе skip warning)
2. `references/_voice-TEMPLATE.md` ИЛИ соответствующий voice reference
3. `config.md` (re-read для voice register)
4. **HARD MANDATORY** `.business/voice-corpus/_format-canon-v2.md` - **канон формы v2: форма выбирается под цель** (пороги: 296 чистых постов двух TG-доноров, окно 12 мес; третий донор - слой наблюдений §10). Читать §0-§5 и §9. Для X/Threads брать: профиль цели (R реакции / F репосты / S продажа), конструкцию хука по профилю (R кадр-эпизод или назывной ярлык 1-4 слова без глагола, петля вместо пересказа; F опись с цифрой и габаритом артефакта; S ярлык или квитанция о случившемся факте), функцию финала (R вывод и закрытая петля; F адрес в хвосте; S живая реплика, не URL), правила ссылок и перечислений. НЕ брать: TG-разметку, механики реакций как приём письма (§7 - отдельный инструмент режима A), сигнатуры доноров, факты и цифры доноров. В mega-thread скелет ложится на твит-единицу: хук → микро-абзац → поворот → закрытие петли
   - **Ритм: нижняя граница есть, «рубленость» как самоцель отменена.** В классе «разбор» медиана слов в предложении **не ниже 5** при цели 5.5 (держат 11/12 верха), доля отрезков до 3 слов **не выше 0.20** (канон §3.1 п.10). В нарративе пункт не применяется: 6 против 6, признак не различает. У слабого разбора предложения вдвое короче (3.0 против 5.5) - падение до 3 слов это маркер низа, а не стиль
   - **Приоритет источников (трёхзвенный, канон §8.1):** голос автора (входы 1-3) **>** канон формы v2 **>** донор-канон v1 (только там, где v2 молчит). Голос при конфликте побеждает всегда. Ниже канона - плоские дефолты этого скилла (`config.md`, шаблоны типов, Hook Char Zone Gate). Конфликт разрешается вслух строкой `конфликт: <A> vs <B> -> взял <A> по уровню N`
5. `.business/voice-corpus/_donor-format-canon.md` - канон формы v1, **ОТМЕНЁН как источник норм** каноном v2. **Не обязательный вход.** Читать только как fallback там, где v2 молчит: слой «приёмы подачи» (в v2 не измерялся, гипотезы низкого ранга). Числовые нормы v1 (500-1700 знаков, «жирный почти всегда», «медиана 5-6 слов») к применению запрещены - их перекрывает профиль цели v2 §3

Без них Pass 2 voice injection failит. Это закрывает класс «скилл написал generic».

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`.
- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.
- **Улика канона формы (HARD).** Отдельной строкой обязательно, в том же формате, что проверяет `form_mode` в `04-review.md`: `прочитал→взял: канон формы v2 → цель=<reactions|forwards|sales|gate> (<R/F/S/A>), профиль <длина/жирный/списки/ссылки>`. Строки нет → output запрещён. Цель берётся из `brief.form_goal` (дерево канона §2.1); поле пусто → output запрещён целиком, писать по старым порогам `config.md` и шаблона типа нельзя - вернуться в `01-router.md` Step 5.5 FORM-GOAL ROUTER за целью, а не печатать `цель=не объявлена` как разрешение продолжать


## Pass 1 - Initial draft

Заполнить skeleton beats реальным content:
- Hook: use chosen variant from `02-structure.md`
- Beats: expand each draft tweet - concrete + verbatim где возможно
- Closer: insert per type pattern

Constraints:
- Каждый tweet ≤280 chars (X) или ≤500 (Threads)
- Hook tweet thread ≤220 chars (для thread indicator room)
- 1/3/1 ритм где applicable (короткая первая / длинные средние / короткая последняя)

## Pass 2 - Voice injection

Применить voice markers из `references/_voice-TEMPLATE.md` (или RU equivalent):

**автор RU lexicon (memory):**
- Нельзяграм (НЕ Instagram)
- контент-завод
- вайбкодинг / вайбмаркетинг
- ферма
- перегнать (видео)
- пдп
- Дубайск

**Voice rhythm:**
- На "ты" (РУ)
- Короткие parameters
- Конкретные числа / имена / даты

**For EN (если language=en):**
- Derived из Welsh primary cluster + автор Brand DNA
- Concrete numbers ($X, N days, specific person)
- Inverted clichés
- No AI tells (см. `references/ai-tells-en.md`)

## Pass 2.5 - Living Language

Проверить против banned constructions:
- Метафоры (глаголы в небуквальном значении: «ломает», «закрывает», «выстрелил»)
- Несуществующие словосочетания
- AI-conjunctions ("moreover", "furthermore", "in conclusion", "in summary", "to elaborate")
- Em-dash «-» внутри строк → fail
- Восклицательные знаки >1 → warning

Если найдено - rewrite соответствующее beat.

## Pass 2.6 - RU Russification (NEW v1.1, если language=ru)

ТОЛЬКО для language=ru. Закрывает класс "грамматическая калька с EN".

Sequential check против `references/ru-grammar-russification.md`:

**Step 1 - Глаголы-кальки:**
- "делать результат" → "давать результат" / "приносить результат"
- "иметь результат" → "получить результат" / "выйти на результат"
- "делать смысл" → "иметь смысл" / "логично"
- "делать прогресс" → "продвигаться"
- "построить экосистему" → переформулировать (banned)
- "создавай(те) ценность" (безадресный императив без объекта, как самостоятельный совет) → "приносить пользу"; **сужено вслед за humaniser кат.13, замер: владелец пишет так сам (VOICE-015, ivan-final-0)** - форма от 1-го лица с объектом/фактом рядом («создаю ценность для X тем, что…», «отдаёт ценность сразу») живой оборот, НЕ трогать
- "забрать ценность" → переформулировать

**Step 2 - Англицизмы в RU narrative:**
- "shipped" → "запущенный" / "выпущенный"
- "real" → "настоящий" / "реальный"
- "mode" → "режим"
- "platform" → "платформа"
- "feature" → "функция"
- "update" → "обновление"
- "release" → "выпуск"
- "perfect" → "идеальный" / "точный"
- Voice corpus terms (Нельзяграм / вайбкодинг / вайбмаркетинг / контент-завод / Дубайск) - ОСТАЁТСЯ

**Step 3 - AI tells RU (полный catalog):**
Sequential check против `references/ai-tells-ru.md`:
- Tier 1 риторические фигуры → rewrite beat
- Tier 4 автор-specific banned → rewrite beat
- Tier 5 structure tells → manual check ритма

Если найдено - rewrite specific beat с замещающей конструкцией из catalog.

## Pass 3 - Cross-post adapt (если platform_target = both)

X version → Threads version:
- Same content base
- Expand 280 → 500 chars если есть room (Threads gives more space)
- Same hook, slightly expanded beats
- Same closer

Если threads-only - start native 500 chars, не cut from 280.

## Step Output

```yaml
draft:
  x_tweets: [<tweet 1>, <tweet 2>, ...]
  threads_posts: [<post 1>, <post 2>, ...]
  char_counts:
    x: [<N1>, <N2>, ...]
    threads: [<N1>, <N2>, ...]
  hook_char_count: <N>
  hook_in_zone: A | B
  voice_passes:
    mandatory_reads: PASS
    voice_injection: PASS
    living_language: PASS
```

→ Hand off to `04-review.md`.

## Anti-patterns

- НЕ skip Pass 0 mandatory reads (закрывает generic class)
- НЕ verbatim copy patterns from research - derive в автор voice
- НЕ Pass 2 без Pass 1 (separate concerns)
- НЕ скоп ≤220 для thread hook (нужно room для "1/N" indicator)
- НЕ adapt X → Threads через простой паддинг - Pass 3 = semantic expansion

## Memory cross-refs

- `[[feedback-no-em-dash]]`
- `[[feedback-no-tech-jargon-no-anglicisms]]`
- `[[feedback-verbatim-quote-transfer]]`
- `[[feedback-mandatory-reads-before-draft]]` (из post/post Pass 0 architecture)
---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
