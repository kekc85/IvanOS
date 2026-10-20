# Workflow 03-write - Slide text + Visual briefs + Caption

**Назначение:** заполнить outline реальным content - slide text per slide, visual brief с REAL elements, caption.
**Вход:** `outline.slides[]` skeleton от `02-structure.md`
**Выход:** полный `carousel` объект (slides + caption) → `04-review.md`

3 passes (sequential).

---

## Pass 0 - Mandatory Reads (hard gate)

Перед draft обязательны Read'ы 1-6 (только если ещё не прочитано на ideate-stage). Вход 7 (донор-канон v1) не обязателен - он отменён и читается только как fallback:

1. `paths.voice_reference` - gold-standard 5 caroussels автора
2. `references/carousel-anatomy.md` - Hook/Value/CTA structure
3. `references/visual-brief-real-first.md` - 6-field schema
4. `config.md` - banned AI imagery list + lexicon + platform specs
5. `~/.business/products/sticky-offers.md` (NEW 2026-05-28 — sticky source-of-truth по продуктам/ценам/дисклеймерам, если файл существует и subject=ivan; чтобы не выдумывать цифры/даты/формулировки/CTA)

6. **HARD MANDATORY** `.business/voice-corpus/_format-canon-v2.md` - **канон формы v2: форма выбирается под цель** (пороги: 296 чистых постов двух TG-доноров, окно 12 мес; третий донор - слой наблюдений §10). Читать §0-§5 и §9. **Профиль применяется к caption; анатомия слайдов остаётся своя** (`references/carousel-anatomy.md`). Для карусели брать: профиль цели (R реакции / F репосты / S продажа), конструкцию хука слайда 1 по профилю (R кадр-эпизод или назывной ярлык 1-4 слова без глагола, открывает петлю; F опись с цифрой и габаритом артефакта; S ярлык или квитанция о факте), правило «один слайд = одна мысль» как аналог требования «один тезис на пост» (держат 93% верха), функцию финала (R вывод и закрытая петля - финал возвращает слово или образ хука; F адрес в хвосте; S живая реплика, не URL), правила ссылок и перечислений в caption. НЕ брать: TG-разметку, механики реакций как приём письма (§7 - отдельный инструмент режима A), сигнатуры доноров, факты и цифры доноров
   - **Ритм: нижняя граница есть, «рубленость» как самоцель отменена.** В классе «разбор» медиана слов в предложении **не ниже 5** при цели 5.5 (держат 11/12 верха), доля отрезков до 3 слов **не выше 0.20**. В нарративе пункт не применяется: 6 против 6, признак не различает. Пункт списка-существительное в столбик без глагола - маркер низа (0/12 против 2/12), каждый пункт обязан содержать глагол или быть вопросом
   - **Приоритет источников (трёхзвенный, канон §8.1):** голос автора (входы 1-4) **>** канон формы v2 **>** донор-канон v1 (только там, где v2 молчит). Голос при конфликте побеждает всегда. Ниже канона - плоские дефолты этого скилла (`config.md`, `carousel-anatomy.md` в части длин и потолков, шаблоны `templates/*`). Конфликт разрешается вслух строкой `конфликт: <A> vs <B> -> взял <A> по уровню N`
7. `.business/voice-corpus/_donor-format-canon.md` - канон формы v1, **ОТМЕНЁН как источник норм** каноном v2. **Не обязательный вход.** Читать только как fallback там, где v2 молчит: слой «приёмы подачи» (в v2 не измерялся, гипотезы низкого ранга). Числовые нормы v1 (500-1700 знаков, «жирный почти всегда», «медиана 5-6 слов») к применению запрещены - их перекрывает профиль цели v2 §3

Без них Voice Fidelity Gate в `04-review.md` будет fail.

Помечать `mandatory_reads` соответственно.

### Вход-гейт — улика прочитал→взял (HARD)

Перед draft выписать в чат по КАЖДОМУ обязательному входу строку-улику `прочитал→взял: <вход> → <что конкретно взял>`.
- Непрочитанный обязательный вход → **output запрещён**. Сначала прочитать, потом писать.
- Не производить каркас по форме без чтения реальных источников (voice / living-language / config / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: вход уже прочитан на ideate-стадии → пометить улику `(reuse)`, повторный Read не нужен.
- **Улика канона формы (HARD).** Отдельной строкой обязательно, в том же формате, что проверяет `form_mode` в `04-review.md`: `прочитал→взял: канон формы v2 → цель=<reactions|forwards|sales|gate> (<R/F/S/A>), профиль <длина/жирный/списки/ссылки>`. Строки нет → output запрещён. Цель берётся из `brief.form_goal` (дерево канона §2.1); поле пусто → output запрещён целиком, писать по старым порогам `config.md` и `carousel-anatomy.md` нельзя - вернуться в `01-router.md` Шаг 4.5 FORM-GOAL ROUTER за целью, а не печатать `цель=не объявлена` как разрешение продолжать


---

## Pass 0.5 - Action-skill gates (conditional)

**Условие срабатывания:** если carousel содержит **announce** / **launch-promo** / **case-study с цифрами** контент (т.е. зовёт к non-reversible action: купить / зарегистрироваться / прийти на event).

**Detect через outline.family + slide content:**
- family = story-case + slide mentions конкретный case study с цифрами
- любой slide содержит мention event (workshop / эфир / запуск / окно продаж)
- finale CTA = direct sale action (Купить / Получить продукт / Войти в марафон)

Если ни один признак не сработал → skip Pass 0.5, продолжать к Pass 1 как stylistic.

### Шаг 0.5.1 - PII enforce (Gate C)

Применить `config.privacy.pii_patterns` (см. skill-craft/knowledge/bug-categories.md «Action skills») к каждому файлу контекста. Если config.privacy отсутствует - сначала добавить из bot-message/config.md как template.

### Шаг 0.5.2 - Event existence (Gate B)

Detect event mentions в outline.slides:

Regex: `\b(workshop|воркшоп|live|эфир|стрим|вебинар|webinar|запуск|launch|релиз|марафон|тренинг|окно (продаж|регистрации))\b` + конкретные даты.

Verify в:
1. `.business/запуски/<active>/`
2. `config.bot.upcoming_events` (если есть) / `config.carousel.upcoming_events`
3. Mode C raw_transcript

Match не найден → STOP с warning.

### Шаг 0.5.3 - Fact verification (Gate A)

Extract все числа / даты / именованные кейсы из slide content. Verify против `.business/INDEX.md` + products + testimonials + raw_transcript.

UNVERIFIED ≥1 → STOP с warning списком.

### Шаг 0.5.4 - Audit trail

В `output.internals`:
```
Action-skill check (carousel):
- PII redaction: <N matches replaced>
- Event verification: <event> → <source>
- Fact verification: <N checked, M verified, K UNVERIFIED>
```

См. `~/.claude/skills/bot-message/workflow/03-write.md` Pass 0.5-0.7 для детального reference patterns.

---

## Pass 1 - Slide text (text per slide)

Для каждого slide в outline:

```yaml
slides[i]:
  text: "<5-25 слов в зависимости от role>"
  verbatim_anchor: "<если есть source_quote - preserve>"
```

**Правила text:**

- Hook (3-12 слов): number + outcome + timeframe. «8 ходов вайбмаркетинга. <твоя выручка> позже:»
- Value (5-25): один тезис. Если 2 идеи - split на 2 slides.
- CTA (5-15): single artifact, не behavior. «Comment "разбор" → DM ссылка»

**Voice rules:**
- Pronoun: `config.voice.hook_pronoun` (default «ты»)
- Filler removal: «значит», «вот», «вообще» - out
- Em-dash «-» внутри строк - fail (auto-replace на «-»)
- Англицизмы из `config.lexicon_banned_hard` - fail

**Source quotes priority:** если slide содержит цитату из надиктовки - verbatim preserve, не «причёсывать».

---

## Pass 2 - Visual briefs (REAL elements first)

Для каждого slide заполнить 6-field schema:

```yaml
slides[i].visual_brief:
  real_elements:           # ⭐ ГЛАВНОЕ ПОЛЕ
    - "<конкретный UI element / product / number>"
    - "<example: Cursor IDE Composer panel showing voice prompt>"
    - "<example: Stripe dashboard MRR $X figure>"
    - "<example: Author face photo, signature smile>"
  
  composition: "<что в кадре, layout, focal point>"
  typography: "<font choice + sizes - 60pt hook / 36pt body>"
  color_palette: "<brand colors + accent (Ivan red)>"
  text_overlay: "<exact text overlay if any (annotations on UI)>"
  abstraction_check: "PASS | FAIL - НЕТ из 12 banned AI patterns?"
  pacing_role: "promise | curiosity gap | reveal | loop-close | CTA"
  
  # v1.1 ADDED: render automation
  render_strategy: "typography | web-screenshot | desktop-manual | brand-asset | composite"
  render_inputs:
    template: "<carousel/render/templates/typography-hook.html>"  # если typography
    url: "<URL>"                                                  # если web-screenshot
    css_selector: "<#dashboard-mrr>"                              # если web-screenshot
    tool_name: "<Claude Code IDE>"                                # если desktop-manual
    setup_action: "<открыть file ~/.claude/skills/carousel/...>"  # если desktop-manual
    asset_name: "<ivan-selfie-2026.jpg>"                          # если brand-asset
    placeholders:                                                 # для typography templates
      HOOK_NUMBER: "7"
      HOOK_TEXT: "систем контент-фабрики"
      HOOK_SUB: "<твоя выручка> через органику"
      PROOF: "Stripe Skool MRR"
```

**Render strategy assignment:**

Default по role (auto, override через explicit setting):

| Slide role | Default strategy | Когда override |
|---|---|---|
| hook (typography-only) | typography | если есть hero image - composite |
| context (text + diagram) | typography | если diagram = real screenshot - web-screenshot |
| numbered_step (text) | typography | если step = product UI - web-screenshot / desktop-manual |
| item (listicle text) | typography | если item = real tool - web-screenshot / desktop-manual |
| reveal | brand-asset | если reveal = web tool UI - web-screenshot |
| synthesis | typography | (rarely override) |
| cta | typography (с brand-asset signature) | (rarely override) |
| panorama leading / middle / payoff | composite | (always) |

**Real elements типы (по family):**

- framework-breakdown: real UI screenshots showing each step
- listicle: real product logos (Cursor / Claude Code / Lovable / Stripe / Kit / Skool)
- story-case: real numbers + screenshots (Stripe MRR / DM screenshots / dashboard)
- panorama: continuous real composition (Stack-as-Panorama: Claude+Lovable+higgsfield в одной wide composition)
- reel-to-carousel: extracted frames из card.md frames inventory

**FAIL conditions:**
- `real_elements` пустой ИЛИ только generic («какой-то dashboard»)
- `abstraction_check` = FAIL (попал в `config.banned_ai_imagery`)
- Composition = «AI-generated illustration of expert»

---

## Pass 3 - Caption

> 🔴 Если CTA caption = КОД-СЛОВО (lead-magnet) — строить СТРОГО по канону `~/.claude/skills/_shared/lead-magnet-description-structure.md` (6 блоков: хук-парадокс / суть / примеры-с-якорями / личный опыт / что внутри / CTA код-слово; эталон github-ролик). НЕ плоский caption.

Caption ≠ дублирование slides. Caption даёт **дополнительный layer**:

- Контекст / backstory
- Дополнительный value (mini-PAIPS)
- Hook к CTA (если slide-CTA нужно усиление)

Длина по platform:
- IG: ≤2200 chars, hook в первых 125 chars (до «...more»)
- LinkedIn: ≤3000 chars, hook в первых 210 chars (до «see more»)

Structure:
```
[Hook line - 1 sentence - должен работать standalone в feed preview]
[Body - 3-5 short paragraphs - backstory или mini-PAIPS]
[CTA - repeat or amplify slide CTA]
[Hashtags - IG 3-5 / LinkedIn 0-2]
```

**Bilingual:** если `config.subject.language = both` - генерить RU caption, затем chain в `multi-language-localization` для EN адаптации (не дословный перевод).

---

## Pass 4 - A/B alternatives

Сгенерировать 2 A/B варианта:

- **A/B Hook:** альтернативный hook slide text (другой формат - questional / stat / before-after)
- **A/B Caption:** альтернативная первая строка caption (другой angle)

Сохранить в `carousel.ab_variants`.

---

## Шаг 5 - Передача в review

```yaml
carousel:
  family: "<from outline>"
  platform: "<from brief>"
  slides: [<8-12 объектов с text + visual_brief + verbatim_anchor>]
  caption:
    ru: "<full text>"
    en: "<full text если bilingual>"
    hashtags: [...]
  ab_variants:
    hook_alt: "<alternative hook text>"
    caption_alt_first_line: "<alternative caption opening>"
  assets_manifest:
    - "<list of real_elements что нужно достать или сделать>"
```

Перейти в `workflow/04-review.md`.

---

## Принципы

1. **Pass 0 mandatory reads - hard.** Voice fidelity без них не достичь.
2. **REAL elements first per slide.** Generic = brand suicide.
3. **One idea per slide.** 2 идеи → split на 2 slides.
4. **Voice preservation.** Source quotes verbatim, не «причёсывать».
5. **Caption ≠ duplication.** Дополнительный layer, не пересказ.
6. **A/B mandatory.** Hook + caption alternatives для тестирования.
7. **Assets manifest tracking.** Что нужно собрать для рендера - фиксировать.
---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
