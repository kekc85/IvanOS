---
name: single-image-config
version: "1.0"
last_reviewed: 2026-05-28
description: Конфиг скилла single-image. Указывает пути к контексту проекта (avatar / JTBD / Brand DNA / Карта смыслов / brand visual identity / tool stack) и parameters визуального стиля автора. автор клонирует ученикам - каждый ученик меняет пути под свой проект.
---

# single-image config

> Это **точка адаптации скилла под конкретного автора**. Скилл (`single-image`) одинаков у автора и у учеников. Различие - только в этом файле и в данных, на которые он указывает.

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  platforms_primary: ["X", "LinkedIn", "Нельзяграм", "TG"]
  primary_language: ru
  secondary_language: en
  bilingual_always: true  # генерим оба caption всегда
  market_primary: en  # с июня 2026
  market_secondary: ru
  niche: "вайбкодинг + вайбмаркетинг для соло-экспертов"
```

**Для ученика:** заменить `name`, `platforms_primary`, `niche`. Если работает только в одном языке - `bilingual_always: false`, secondary_language задавать опционально.

---

## Paths (где лежит контекст проекта)

Все пути относительно корня проекта (например, `~/` у автора).

```yaml
paths:
  # Аудитория
  avatar: ".business/audience/avatar.md"
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"

  # Продукт
  products_dir: ".business/products/"
  pricing: ".business/products/pricing.md"

  # Brand DNA / визуальный стиль
  brand_dna: ".business/Распаковка бренда.md"
  brand_guidelines: ".business/assets/brand-guidelines.md"

  # JTBD
  jtbd: ".business/audience/avatar.md"  # JTBD внутри avatar.md

  # Карта смыслов (Mode A - Plan)
  content_map: ".business/запуски/<active-launch>/5.2-Карта-смыслов.md"
  content_map_format: "thematic"  # calendar | thematic | hybrid

  # История картинок-постов (для no-repeat / стиль check)
  recent_images_source: "none"  # webfetch | file | none
  recent_images_count: 10

  # Запретные термины и обязательная лексика
  lexicon: "config-lexicon.md"  # inline ниже
```

---

## Visual identity

```yaml
visual_identity:
  palette_primary:
    - name: "ink"
      hex: "#0A0A0A"  # near-black для текста на светлом
    - name: "paper"
      hex: "#FAFAFA"  # off-white фон
    - name: "accent"
      hex: "#0066FF"  # синий акцент (CTA / highlight)
    - name: "warn"
      hex: "#FF6B35"  # оранжевый для contrast
  palette_secondary:
    - name: "gray-mid"
      hex: "#6B7280"
    - name: "gray-light"
      hex: "#E5E7EB"

  typography:
    sans_display: "Inter / Geist Sans / SF Pro Display"
    sans_body: "Inter / Geist Sans"
    serif_accent: "GT Sectra / Tiempos"  # для quote-card
    mono: "JetBrains Mono / Geist Mono"  # для code-style

  aesthetic_principles:
    - "Minimalist over decorative"
    - "Contrast high, color sparse"
    - "Sans-serif default, serif sparingly для accent"
    - "No gradients за исключением единичных editorial"
    - "No drop shadows (flat design)"
    - "Whitespace generous"
```

**Для ученика:** настроить под свою brand identity. Если нет - дефолтит на Ivan's setup как стартовая база.

---

## Aspect ratios per platform

```yaml
aspect_defaults:
  X: "1:1"  # 1080x1080
  LinkedIn: "1.91:1"  # 1200x627 для feed
  LinkedIn_carousel: "1:1"  # 1080x1080 для multi-image
  Instagram_feed: "4:5"  # 1080x1350 (highest reach 2026)
  Instagram_square: "1:1"  # 1080x1080
  Instagram_story: "9:16"  # 1080x1920
  TG: "1:1"  # 1080x1080
  Threads: "1:1"  # 1080x1080
```

---

## Tool stack (для production handoff)

```yaml
tool_stack:
  ai_image_generation:
    primary: "higgsfield-generate"  # chain skill для AI image execution
    fallback: "Midjourney v7"
    text_in_image: "DALL-E 3"  # лучше всех с текстом
  manual_composition:
    primary: "Figma"
    secondary: "Canva Pro"
    pixel_polish: "Photopea"  # free alternative Photoshop
  screenshot_tools:
    macos: "CleanShot X"
    annotation: "Annotate / CleanShot"
  meme:
    primary: "Photopea"
    fallback: "Canva"
```

**Для ученика:** заменить под свой стек. Если нет - дефолт работает.

---

## Reference creators (visual style anchors)

```yaml
reference_creators:
  concept-diagram:
    - name: "Jack Butcher"
      handle: "@jackbutcher"
      url: "https://x.com/jackbutcher"
      what_to_copy: "Black ink on cream paper. Minimal text. Geometric clarity. 1-2 colors max"
      what_NOT_to_copy: "Не copy его brand wordmark / specific iconography"

  dashboard-screenshot:
    - name: "Pieter Levels"
      handle: "@levelsio"
      url: "https://x.com/levelsio"
      what_to_copy: "Stripe dashboard cropped к key metric. Bold yellow highlight на цифру"
      what_NOT_to_copy: "Не copy meme-aggressive caption tone"
    - name: "Marc Lou"
      handle: "@marc_louvion"
      what_to_copy: "MRR screenshot + 1-line context"

  meme:
    - name: "Distillery (general)"
      what_to_copy: "Cultural reference + smart twist на topic"
      what_NOT_to_copy: "Не lazy reuse устаревших мемов"

  quote-card:
    - name: "Naval"
      handle: "@naval"
      what_to_copy: "Plain text on neutral background. Author small. Card-shape"
    - name: "Hormozi quote cards"
      what_to_copy: "Bold sans-serif on black. Clear hierarchy"

  before-after:
    - name: "Pat Walls (Starter Story)"
      what_to_copy: "Split visual: was X / became Y. Concrete artifacts"
```

---

## Voice parameters (для caption)

```yaml
voice:
  archetypes_allowed: ["Magician", "Sage", "Outlaw"]
  archetypes_banned: ["Caregiver", "Lover", "Innocent"]
  pronoun_ru: "ты"
  pronoun_en: "you"
  formality: low
  emoji_policy_caption: "none"  # none | sparse | abundant
  exclamation_max: 1
```

---

## Lexicon (обязательная и запретная)

```yaml
lexicon_required:
  - replace: "Instagram"
    with: "Нельзяграм"
  - replace: "инстаграм"
    with: "Нельзяграм"

lexicon_banned_hard:
  # Em-dash и known artifacts (из post)
  - "-"  # em-dash внутри строк (только в начале буллета можно)
  - "artifact"
  - "digital-twin"
  - "fast-action"
  - "Grand Slam Offer"
  - "КЭВ"
  - "связки"

  # Англицизмы в caption (русские)
  - "engagement"
  - "энгейджмент"
  - "retention"
  - "ретеншн"
  - "scope"
  - "pipeline"
  - "framework"
  - "workflow"
  - "функционал"

  # Generic AI clichés
  - "без воды"
  - "без теории"
  - "life-changing"
  - "mind-blown"
  - "10x"
  - "game-changer"
  - "hustle"
  - "grind"

  # Negative stats public (memory rule)
  - "20% доходят"
  - "только 20%"
  - "большинство не справится"

lexicon_banned_in_image_text:
  # Дополнительные банлисты ДЛЯ ТЕКСТА НА КАРТИНКЕ (повышенные требования)
  - "AI" в одиночку без контекста  # generic buzzword
  - "ChatGPT" если не специфика  # обобщённо
  - hyperbolic adjectives ("amazing" / "incredible" / "best ever")

lexicon_warnings:
  - pattern: "![!]+"
    message: "more than one exclamation mark in caption"
```

**Для ученика:** базовый список одинаков. Добавить свои запретные термины под свою нишу.

---

## Output settings

```yaml
output:
  ab_variants: 2  # сколько A/B вариантов caption генерим на язык помимо основного
  show_self_check_report: true
  show_no_caption_test_result: true
  show_anti_stock_test_result: true
  open_artifact_command: "open"  # OS-aware auto-open: "open" (macOS) / "start" (Windows) / "xdg-open" (Linux); или _shared/bin/open-file
```

---

## Validation refresh tracking

```yaml
validation:
  banned_list_last_review_date: "2026-05-28"
  banned_list_refresh_interval_days: 30
```

---

## Quick start для нового пользователя

Если ты ученик и только что склонировал скилл:

1. **Прочитай SKILL.md** - поймёшь архитектуру.
2. **Запусти `/single-image`** без аргументов в первый раз.
3. Скилл проверит этот config и спросит чего не хватает (запустит onboarding).
4. **Заполни недостающее** - путь к avatar, JTBD, brand identity, tool stack.
5. **Запусти `/single-image про X`** - получишь первый visual brief.

---

## Активный запуск автора

```yaml
active_launch:
  ru: "<твоя-папка-запуска>"
  en: null  # ещё не стартовал
```

Используется для подстановки в `<active-launch>` выше.