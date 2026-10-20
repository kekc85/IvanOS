# Workflow 03: Design brief

Core stage. Создание конкретной спецификации картинки: композиция / verbatim text on image / палитра / типографика / tool prompt.

## Input

Из 02-finalize:
- type
- topic
- reference_creator
- platform + aspect
- brand_identity
- verbatim_quote (если есть)

## Pass 0 — Вход-гейт (mandatory reads)

Перед созданием brief / caption выписать в чат каждый обязательный вход и дать по нему строку-улику `прочитал→взял`:

| Вход | Источник | Улика (прочитал→взял) |
|---|---|---|
| voice / lexicon | `config.md` (`voice.*`, `lexicon_banned_hard`, `lexicon_required`) | `<что взял>` |
| композиция | `knowledge/composition-principles.md` | `<что взял>` |
| reference creator | `knowledge/reference-creators.md` (per type) | `<что взял>` |
| type-структура | `templates/<type>.md` | `<что взял>` |
| verbatim_quote | из 02-finalize (если есть) | `<verbatim или «нет»>` |

Правила гейта:
- Непрочитанный обязательный вход → **output запрещён** (ни design-brief, ни caption). Сначала прочитать.
- Не производить каркас по форме без чтения реальных источников (config / knowledge / template). Каркас «по памяти» = generic AI-артефакт.
- Идемпотентно: если вход уже прочитан на 02-finalize — переиспользовать из контекста, улику пометить `(reuse из 02)`.

## Шаги

### Step 1: Load template per type

```bash
template=$(cat ~/.claude/skills/single-image/templates/$type.md)
```

Каждый template даёт type-specific structure для brief.

### Step 2: Композиция

Описать что где находится в композиции:
- Primary element (центральная фигура, занимает >40%)
- Secondary elements (2-3 supporting)
- Tertiary (metadata / attribution / signature)
- Position (центр / left third / golden ratio)
- Negative space distribution (30-50%)

Применить:
- `knowledge/composition-principles.md` Hierarchy section
- Type-specific rules из template

### Step 3: Verbatim text on image

ВАЖНО: дословный текст что будет нарисован.

```
Текст на картинке (verbatim):
- Headline: «...»
- Subhead (если есть): «...»
- Labels (если diagram): «...», «...», «...»
- Attribution / signature: «...»
```

**Не** «здесь будет название», а реальный конечный текст.

Длина:
- Headline: ≤8 слов
- Subhead: ≤12 слов
- Labels: ≤3 слов each
- Quote (для quote-card): ≤25 слов / ≤140 chars
- Caption hint в image (для dashboard): 0-1 слово

Если type=meme - текст в format-specific positions (top/bottom/per element).
Если type=before-after - текст в каждом frame.

### Step 4: Палитра

Конкретные цвета (hex или semantic name из config):
- Primary background: <hex или name>
- Primary text: <hex или name>
- Accent (highlight / CTA): <hex или name>

Max 3 цвета. Apply 60-30-10 правило.

Verify contrast через `knowledge/composition-principles.md` Section 2:
- Body text contrast >= 7:1
- Headline contrast >= 4.5:1

### Step 5: Типографика

Из config.visual_identity.typography:
- Headline font family + weight + size
- Body font family + weight + size
- Attribution font family + weight + size

Max 2 typeface families в одной композиции.

### Step 6: Tool prompt

Зависит от type:

**AI-generated (concept-diagram some / quote-card some / meme some):**
```
Tool: Higgsfield (или Midjourney / DALL-E 3 для text-heavy)
Prompt: «<full prompt>»

Format prompt:
1. Subject + composition («Square minimalist diagram showing iceberg with...»)
2. Style («black ink on cream paper, Visualize Value style, no gradients, flat design»)
3. Negative («no people, no photos, no decorative elements, no 3D rendering»)
4. Aspect: «1:1, 1080x1080»
```

**Manual composition (concept-diagram complex / before-after / dashboard polish):**
```
Tool: Figma (clean shapes) или Photopea
Steps:
1. Create canvas <aspect>
2. <composition step 1>
3. <composition step 2>
...
N. Export PNG 2x retina
```

**Screenshot (dashboard-screenshot real):**
```
Tool: CleanShot X (macOS) / ShareX (Windows)
Source: <real dashboard URL or app>
Crop: <bounds>
Polish: <Photopea/Figma annotations - yellow box on key number>
Privacy: blur <customer names / emails / sensitive IDs>
```

**Meme:**
```
Tool: Photopea OR imgflip.com меm generator OR Canva
Template: <specific meme template name>
Source template image: <URL or path>
Overlays:
- Top: «<text>»
- Bottom: «<text>»
- (или per element для multi-element templates)
```

### Step 7: Cross-distribution variants

Если config.subject.platforms_primary имеет >1 platform - указать что меняется per platform:
- Aspect different → resize / recompose
- Color mode different → invert / adjust
- Text size different → recompose for thumbnail readability на mobile feed

### Step 8: Output (передача в 04-caption)

```yaml
design_brief:
  type: "<type>"
  topic: "<topic>"
  composition:
    primary: "<description>"
    secondary: [...]
    tertiary: "<description>"
    position: "<center/third/golden>"
    negative_space_target: "30-50%"
  text_on_image_verbatim:
    headline: "..."
    subhead: "..."
    labels: [...]
    attribution: "..."
  palette:
    primary_bg: "<hex>"
    primary_text: "<hex>"
    accent: "<hex>"
    contrast_check: "PASS"
  typography:
    headline: "<family weight size>"
    body: "<family weight size>"
  tool_prompt:
    tool: "<higgsfield/midjourney/figma/photopea/screenshot>"
    prompt_or_steps: "<full text or steps>"
  cross_distribution:
    platform_X: "<base brief>"
    platform_LI: "<adjustments>"
    platform_IG: "<adjustments>"
```

→ `04-caption.md`

## Принципы

1. **Verbatim, не пересказ.** Текст на картинке указывается дословно.
2. **Tool prompt = ready-to-execute.** Можно скопировать и сразу запустить в Higgsfield/MJ.
3. **Контраст verified.** Перед output - check через mental contrast calculation.
4. **Identity якорь.** Каждый brief упоминает specific identity element (palette / type / signature element автора).
5. **Cross-distribution explicit.** Не «adapt for LI», а конкретные adjustments.

## Edge cases

- **AI generator не умеет точный текст** → use DALL-E 3 (best text) или manual composition в Figma
- **Brand palette не подходит для type** (e.g., concept-diagram требует high-contrast, brand палитра muted) → отметить override + brand consistency tradeoff
- **Resolution constraint** платформы → resize в production notes
- **Real metric для dashboard не verified** → STOP, return to 02-finalize ask user verify