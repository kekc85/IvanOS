# Workflow 06: Output

Финальный output skill. Visual brief + bilingual caption + production notes + A/B + self-check report.

## Input

- design_brief (из 03)
- captions (из 04, RU 3 варианта + EN 3 варианта)
- review (из 05, с выбранными best variants)
- config (output settings)

## Output формат

```
═══════════════════════════════════════
SINGLE-IMAGE BRIEF - {topic}
═══════════════════════════════════════

Тип: {type}
Платформа primary: {platform}
Aspect: {aspect}
Reference creator: {reference}

───────────────────────────────────────
ВИЗУАЛЬНЫЙ BRIEF
───────────────────────────────────────

Композиция:
- Primary: {primary element}
- Secondary: {secondary elements}
- Position: {position}
- Negative space: {%}

Текст на картинке (verbatim):
- Headline: «{text}»
- Subhead: «{text}»
- Labels: «{labels list}»
- Attribution: «{text}»

Палитра:
- Background: {hex} ({name})
- Text: {hex} ({name})
- Accent: {hex} ({name})
- Contrast: {ratio}:1 (PASS WCAG AAA)

Типографика:
- Headline: {family weight size}
- Body: {family weight size}

───────────────────────────────────────
TOOL PROMPT (ready to execute)
───────────────────────────────────────

Tool: {tool}

{full prompt текст или steps}

───────────────────────────────────────
CAPTION RU
───────────────────────────────────────

A (рекомендую): {best variant text}

B: {second variant text}

C: {third variant text}

───────────────────────────────────────
CAPTION EN
───────────────────────────────────────

A (рекомендую): {best variant text}

B: {second variant text}

C: {third variant text}

───────────────────────────────────────
PRODUCTION NOTES
───────────────────────────────────────

- Tool stack: {tool} + {polish tool}
- Time estimate: {15-30 min generate / 30-60 min compose}
- Output format: PNG 2x retina
- File naming: {date}-{type}-{topic-slug}.png
- Cross-distribution:
  - X primary: {variant + aspect}
  - LinkedIn: {variant + aspect + tweaks}
  - Instagram: {variant + aspect}
  - TG: {variant}

───────────────────────────────────────
SELF-CHECK REPORT
───────────────────────────────────────

3 слоя проверки: PASS
- Слой 1 валидаторы: PASS (em-dash 0 / banned 0 / выдуманные numbers 0)
- Слой 2 4 концепции: PASS
- Слой 3 7 контуров: PASS

No-caption test: PASS / FAIL
- Картинка stand-alone несёт смысл: {explanation}

Anti-stock test: PASS / FAIL
- Identity якорь: {какой specific element якорит к бренду автора}

6-Pass refinement: {N findings, всё non-critical}

Maxwell Ross 9: {score}/9

───────────────────────────────────────
КАК ПОСТРОЕН (внутрянка)
───────────────────────────────────────

- Mode: {mode}
- Source context: {откуда взяли topic}
- Тип выбран потому что: {обоснование}
- Reference creator: {почему именно этот}
- Composition rationale: {почему такая}
- Caption variants отобраны по: {hook patterns / voice / length fit}
- Что было отброшено: {альтернативы которые review отклонил}

═══════════════════════════════════════
```

## Auto-actions после output

### Step 1: Render strategy (FREE FIRST, PAID requires approval)

Skill производит готовый brief + caption. **По умолчанию render через FREE tools** (HTML+Playwright / Figma / Photopea). Платные AI generators (higgsfield / Midjourney / DALL-E) только с явным апрувом автора.

См. memory `[[feedback-free-tools-first-for-images]]` - правило установлено по решению автора после прецедента с непрошеной higgsfield-генерацией.

**Decision tree:**

| Сигнал в input | Render path |
|---|---|
| Default (нет специальных flags / просьб) | **FREE → HTML + Playwright screenshot** (см. templates/{type}.md PRIMARY) |
| `--free-only` flag или «бесплатно» | Same - FREE path only |
| Geometry слишком complex для HTML / нужен photo composite | **FREE → Figma manual** или **Photopea** (handoff автору если нужен manual work) |
| Автор явно сказал «генери через AI / higgsfield / GPT Image / MJ» | **PAID → ASK апрув** «Запустить higgsfield-generate gpt_image_2 (~$0.10-0.20)? Y/N» → только после YES |
| `--auto-render-paid` flag (explicit override) | Auto-chain в paid AI generator (явное согласие автора) |
| `--no-render` flag | Skip render, output brief только |

**FREE path execution (HTML + Playwright):**

1. Создать HTML файл `/tmp/single-image-{slug}/{type}.html` с composition из 03-design-brief
2. Запустить HTTP server в фоне:
   ```bash
   cd /tmp/single-image-{slug} && python3 -m http.server 8765 &
   ```
3. Через Playwright tools:
   - `browser_resize width=1080 height=1080`
   - `browser_navigate http://localhost:8765/{type}.html`
   - `browser_take_screenshot filename=~/{slug}.png`
4. `kill` HTTP server: `kill %1` или через TaskStop
5. `open ~/{slug}.png` - verify exit code 0

**PAID path execution (ONLY after explicit approval):**

```bash
# Проверить баланс
higgsfield account status

# Запустить (только после YES от автора!)
higgsfield generate create gpt_image_2 \
  --prompt "<from design_brief.tool_prompt>" \
  --aspect_ratio <from finalize.aspect> \
  --resolution 2k --wait
```

Сохранить URL → `curl -o {path}.png <url>` → `open {path}.png`.

**ВАЖНО:**
- БЕЗ явного «генери через AI» от автора - НЕ запускать платные tools
- Если автор не специфицировал - default FREE path без вопросов
- Если автор спросил «можно лучше?» - предложить FREE path improvements first, paid только если FREE не fits

### Step 2: Mandatory visual review (после render)

Если rendered image получен (любой path):
1. `open <rendered-path>` для author review
2. Прогон Pass 0 из `05-review.md` Mandatory render+visual review
3. Если visual issues - flag в output + suggest re-render с corrections

Если автор отказался от render - explicit warning в output: «brief не валидирован визуально, only spec checked».

### Step 3: Track record

Записать применение в `examples/track-record-single-image.md`:
- Date / topic / type / mode
- Render path used (higgsfield / Figma / none)
- Credits spent (если higgsfield)
- catch_rate placeholder (заполнить после публикации)

### Step 4: Open final

Открыть финальный rendered artifact командой ОС: `open <path>` (macOS) / `start "" "<path>"` (Windows) / `xdg-open <path>` (Linux), либо `~/.claude/skills/_shared/bin/open-file <path>` (memory `[[feedback-always-open-artifacts]]`). Проверить exit code 0.

## Cross-distribution explicit

Если config.subject.platforms_primary имеет >1 platform - в Production notes секция «Cross-distribution» описывает что adapt'ить:

| From → To | Adaptation |
|---|---|
| X 1:1 → LinkedIn 1.91:1 | Crop / recompose. Headline могла нужно ужать. Caption длиннее (story tone) |
| X 1:1 → Instagram 4:5 | Resize. Text size может потребовать increase для feed thumbnail readability. Hashtags add |
| X 1:1 → TG 1:1 | Identical, может другой caption tone (less hashtags) |

## A/B testing notes

Для каждого поста:
- Vis variant 1 (primary, тот что в Brief)
- Vis variant 2 (если в spec был alternative composition - optional)
- Caption A vs B на разных platforms (auto-rotation)

После 7-14 days - проверить metrics, записать winners в track-record.

## Edge cases

- **Только один язык в config (bilingual_always=false)** → output показывает только primary_language captions
- **No-caption test FAILED но user override** → output но с big WARNING «caption обязателен, image не работает stand-alone»
- **Anti-stock FAILED но user override** → output но с WARNING «контент похож на generic, рекомендую переделать»
- **Multi-platform conflict** (один primary chosen) → output только primary, secondary в cross-distribution notes как «требует adaptation»

## Принципы

1. **Production-ready output.** Brief можно сразу взять и выполнить в Higgsfield / Figma / etc.
2. **Self-check transparent.** Все 3 слоя checked, results видны.
3. **Внутрянка показывается.** Автор видит как было построено (memory rotation / archetype / reference / etc).
4. **A/B варианты для caption всегда.** Не один финальный, а 3 (best + 2 alternatives).
5. **Track record auto-write.** Каждое применение фиксируется для catch_rate metric.