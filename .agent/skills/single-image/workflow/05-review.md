# Workflow 05: Review

Многоуровневая проверка финального brief + caption pair перед output. Если FAIL - regenerate с corrections.

## Input

- design_brief (из 03)
- captions (из 04)
- config (validators)
- knowledge/anti-patterns.md

## Шаги

### Pass 0: MANDATORY render + visual review (BLOCKING)

КРИТИЧНО: оценивать brief как markdown спецификацию = false positive. Только rendered картинка показывает реальные проблемы (overlap элементов / читаемость текста / композиция / identity fit).

**Перед любым другим Pass:**

1. **Render через FREE tool first** (cost-aware, memory `[[feedback-free-tools-first-for-images]]`):
   - **Primary (FREE):** HTML + Playwright screenshot - composition из 03-design-brief в HTML, render через headless Chromium, screenshot 1080x1080. Validated по решению автора
   - **Secondary (FREE):** Figma manual - handoff автору, ждать выполнение (если нужен pixel-perfect typography)
   - **Tertiary (FREE):** Photopea - для photo composites
   - **PAID (только с явным апрувом автора):** higgsfield-generate gpt_image_2 - НЕ запускать пока автор не сказал «генери через AI». Без явного апрува = НЕ ИСПОЛЬЗОВАТЬ
2. **Open** rendered PNG командой ОС: `open <path>` (macOS) / `start "" "<path>"` (Windows) / `xdg-open <path>` (Linux), либо `~/.claude/skills/_shared/bin/open-file <path>` (memory `[[feedback-always-open-artifacts]]`), verify exit code 0
3. **Visual review** на rendered image (не на brief!):
   - Composition: нет overlap элементов? hierarchy читается?
   - Text: всё читаемо на 200x200 thumbnail? нет artifact text (typos / выпадающие символы)?
   - Identity: brand якорь visible (palette / typography / signature)?
   - Stop-scroll: что цепляет в первые 0.5 sec?
4. **Findings → corrections.** Если визуально что-то не так - править brief / palette / composition И re-render. НЕ proceed на Pass 1+ пока visual review не PASS

**Hard rules:**
- Pass 0 без actual rendered image = АВТО-FAIL всего review. Brief-only оценка запрещена (аналог `[[feedback-no-video-review-via-static-frames]]` для image)
- Default render = FREE tool (HTML+Playwright). НЕ предлагать paid first
- Paid AI generator (higgsfield/MJ/DALL-E) использовать ТОЛЬКО при явном «генери через AI» от автора. Прецедент по решению автора - сжёг credit без апрува

---

### Pass 1: Hard regex gates (deterministic)

**На каждом caption (RU + EN, все 3 варианта):**

```python
gates = {
  "em_dash_in_line": r"[^\n]-[^\n]",  # em-dash не в начале bullet
  "instagram_not_corrected": r"\b(Instagram|инстаграм)\b",
  "banned_anglicism": "<from config.lexicon_banned_hard>",
  "negative_stat_ru": r"20% доходят|только 20%|большинство не справится|90% делают.*неправильно",
  "negative_stat_en": r"only 20%|most people fail|90% don't",
  "hyperbolic_ru": r"жизнь изменилась|взрыв мозга",
  "hyperbolic_en": r"life-changing|mind-blown|10x|game-changer",
  "exclamation_overflow": r"!{2,}",
  "length_overflow": "len > platform_target",
}
```

Каждый FAIL = caption variant дисквалифицируется. Если все 3 вариантов одного языка fail → regenerate.

**На text_on_image:**
- Hyped buzzwords («AI» одиноко / hustle / grind / 10x) → FAIL
- Negative статистики → FAIL
- Имена конкурентов из `.business/marketing/competitors.md` → FAIL

### Pass 2: Type-specific checks

**concept-diagram:**
- Labels count ≤ 7 elements (anti-cluttered)
- Geometry один из 10
- Color count ≤ 2

**dashboard-screenshot:**
- Real metric verified? (через `.business/` или explicit user-provided)
- Privacy: blur applied для sensitive data?
- AI-generation disallowed

**meme:**
- Template recognizable (last 12 мес)?
- Recognition test passed (mom test)?
- Inside-joke check

**quote-card:**
- Quote length ≤ 25 слов / ≤ 140 chars
- Attribution verified (если чужая)?

**before-after:**
- Honest comparison (same angle/scale/lighting)?
- Consent если чужой before-after?

### Pass 3: No-caption test (специфичный для single-image)

Mental simulation: убрать caption полностью. Картинка ещё несёт смысл?

- **YES** → PASS
- **NO** → flag «image слишком зависит от caption»:
  - Option A: править brief - добавить self-explanatory element в image
  - Option B: пометить «caption required», но это weak case (image не работает stand-alone)

### Pass 4: Anti-stock test

Mental simulation: open feed где 100 generic posts с этим typovыm AI-style. Этот brief выделяется?

Если **NO** (сливается в feed как fade) → identity якорь missing. Править brief.

Detection через `knowledge/anti-patterns.md` Generic AI aesthetics section:
- Brief mentions «modern», «sleek», «vibrant» как primary attribute → flag
- Tool prompt включает «cinematic», «3D render», «depth of field» без specific reason → flag
- No identity element (specific palette / type / signature) → flag

### Pass 5: Self-distinguish test

Сравнить с last 10 image-posts автора:
- Topic похож на recent? → warning, не повтор ли это
- Visual approach похож? → variety check
- Hook похож? → caption variant nudge

Если 3+ overlap markers → warning «слишком похоже на recent X»

### Pass 6: 6-Pass Refinement (LLM mental judge)

Прогон каждой пары brief+caption через 6 lens:

1. **Skeptic:** «Что здесь не работает / выдумано / преувеличено?»
2. **Expert:** «Технически верно? Reference creator style правильно применён?»
3. **Scroller:** «Я пролистываю feed. Что заставит остановиться?»
4. **Competitor:** «Кто из конкурентов делает похожее лучше? Чем мы отличаемся?»
5. **Editor:** «Что убрать / упростить? Какое слово / element лишний?»
6. **Thumbnail:** «В thumbnail-view (200x200px) что видно? Понятен ли смысл?»

Каждый pass = list findings. Если 3+ findings critical → regenerate brief или caption.

### Pass 7: Maxwell Ross 9-checklist

Адаптировано под image+caption pair:

1. **Idea** - есть ли в этом посте 1 чёткая идея?
2. **Clarity** - audience поймёт без пояснения?
3. **Payoff** - после view audience имеет «aha» moment?
4. **Specificity** - конкретно ли (vs generic)?
5. **Freshness** - не повтор ли previous posts?
6. **Hook** - первые 0.5 sec работают?
7. **Length** - подходит ли длина caption для platform?
8. **Tone** - voice consistent с brand?
9. **CTA** - есть ли implicit или explicit next-step? (для quote-card / meme может быть нет - OK)

Минимум 8/9 PASS для green light.

### Pass 8: 3 слоя финальный gate

**Слой 1 валидаторы (regex):** Pass 1 + Pass 2 (если PASS, слой PASS)

**Слой 2 - 4 концепции:**
- **Pre-mortem 5 причин провала:** что может пойти не так с этим post?
- **90% calibration:** в моих answer'ах об image quality - calibrated?
- **Multi-perspective:** Маркетолог / Дизайнер / Аудитория - что каждый скажет?
- **Adaptive integration:** на основе finding'ов - что adjustment'тить?

**Слой 3 - 7 контуров:**
1. Context - правильно понял задачу?
2. Соответствие предпосылкам - бьётся с brand / Карта / mode?
3. Целесообразность - правильное ли это сейчас (vs другой type)?
4. Релевантность - для audience и JTBD?
5. Фактология - все цифры / атрибуты verified?
6. Реализуемость - выполнимо ли brief tools'ами доступными?
7. Достоверность - не выдумал ли я что-то?

Каждый layer PASS / FAIL. Все 3 = PASS = green light для output.

### Pass 8.5: 4 теста заголовка (SOLO `pisatel-*` canib)

Применяется к **caption hook** (первая строка caption под картинкой) + **visual concept text** (текст на самом изображении, если есть). Gate перед утверждением, BLOCKING:

1. **Самодостаточность.** Текст на картинке + caption первая строка понятны холодному скроллеру без открытия post / без описания. Если читатель должен «прочитать всю caption чтобы понять о чём image» → FAIL.
2. **Конкретное действие.** В hook есть глагол / результат / цифра, не абстракция. «3 системы для $30K/мес» → PASS. «Думайте иначе о вашем бренде» → FAIL.
3. **Простой русский / английский.** Без жаргона ниши, без чрезмерных англицизмов. Тест: «Сказал бы avatar текст вслух?» Нет → FAIL.
4. **Не сужает ширину.** Не отсекает зрителей по узкой профессии если concept горизонтальный.

Если хоть один FAIL → rewrite caption hook / visual text. После 2 ретраев → escalation.

### Pass 8.7: Identity + Citations Gate (SOLO canib)

Read `~/.claude/skills/_shared/identity-citations-gate.md`, применяй Gate 1 (Identity-preservation) + Gate 2 (Verbatim citations) для caption hook + visual text если содержат цитаты ICP. Если FAIL → revision.

### Pass 9: Adaptive learning hook

После review - если обнаружены NEW types failure (which не покрывает текущий config / knowledge):
- Записать в `examples/track-record-single-image.md` секция «New failure modes discovered»
- Flag для future config update

Это закрывает цикл «каждая правка становится system rule» (см. memory [[feedback-each-correction-becomes-system-rule]]).

## Output

```yaml
review:
  pass_1_regex: "PASS / FAIL: <findings>"
  pass_2_type_specific: "PASS / FAIL: <findings>"
  pass_3_no_caption_test: "PASS / FAIL"
  pass_4_anti_stock: "PASS / FAIL"
  pass_5_self_distinguish: "PASS / WARNING / FAIL"
  pass_6_6_pass_refinement: "<findings per lens>"
  pass_7_maxwell_ross: "<score>/9"
  pass_8_3_layers:
    layer_1_validators: "PASS / FAIL"
    layer_2_4_concepts: "<findings>"
    layer_3_7_contours: "PASS / FAIL per contour"
  overall: "GREEN / YELLOW / RED"
  best_caption_variant_ru: "A / B / C"
  best_caption_variant_en: "A / B / C"
```

Если overall = GREEN → `06-output.md`.
Если YELLOW → flag minor issues + proceed but warn.
Если RED → regenerate specific stages (brief / caption) с corrections.

## Принципы

1. **Hard gates - блок.** Em-dash / выдуманные numbers / negative stats не пропускаются.
2. **No-caption test mandatory.** Каждый brief через него.
3. **3 слоя - финальный gate.** Без явного PASS - не output.
4. **Findings становятся правилами.** Adaptive learning loop.
---

## VALUE-DELIVERY GATE (shared, injected)

> Обязательный гейт «что текст ОБЯЗАН доставить» (вещество, не форма). Источник истины — `~/.claude/skills/_shared/value-delivery-gate.md`. Прецедент по решению автора: пост-«огрызок» без пользы + диагностическое действие.

`Read(~/.claude/skills/_shared/value-delivery-gate.md)` и примени на стадии ценности и на ревью:

1. **Действие ГЕНЕРАТИВНОЕ, не диагностическое (HARD).** Actionable-шаг даёт на руки новый результат/артефакт, а не подтверждает известное («посчитай свою цифру» = диагностика = FAIL; «собери первый продукт через нейросеть» = генеративное). Тест: появился ли у читателя НОВЫЙ результат?
2. **Реальная ценность ≥2 value-types (HARD).** Текст несёт ≥2 из: V1 инсайт / V5 модель «почему» / V2 генеративное действие / пруф-кейс с цифрой. Только «было плохо → стало хорошо + призыв» = бот-сообщение = FAIL «ноль пользы».
3. **Объём+формат — ТОЛЬКО длинные форматы** (educational/story/longform): ~2300-2500 символов, богатое форматирование ≥4 типов (<2 = брак). НЕ применять к микроформатам (tweet ≤280 / bot-message / IG-caption) — там только правила 1-2 по сути.

Независимый верификатор обязан проверить: действие генеративное? ≥2 value-types? не огрызок? Память.
