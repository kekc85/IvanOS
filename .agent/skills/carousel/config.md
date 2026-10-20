---
name: carousel-config
version: "1.0"
last_reviewed: 2026-05-28
description: Конфиг скилла carousel. Указывает пути к контексту проекта (аватар / JTBD / Brand DNA / Карта смыслов / продукты), параметры голоса автора, banned AI imagery checklist, platform specs IG+LinkedIn. автор клонирует ученикам - каждый ученик меняет пути под свой проект через onboarding.
---

# carousel config

> Это **точка адаптации скилла под конкретного автора**. Скилл (`carousel`) одинаков у автора и учеников. Различие - только в этом файле и в данных, на которые он указывает.

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  language: ru                          # ru | en | both (если both - bilingual output)
  market: ru                            # ru | en | both
  niche: "vibemarketing + vibe coding for solo experts"
  content_factory_definition: "<что у тебя за контент-формат>"
  product_focus: "<твоя ниша / продукт>"
  primary_platforms:
    - instagram                         # IG carousel 1080×1350 ≤10 slides
    - linkedin                          # LI document PDF 1080×1350 ≤20 pages
  secondary_platforms:
    - threads                           # cross-distribution из IG carousel
    - telegram                          # bridge mode - carousel как hero+narrative
```

**Для ученика:** заменить `name`, `niche`, `product_focus` на свои. Если не работает с одной из платформ - убрать из `primary_platforms`.

---

## Paths (где лежит контекст проекта)

Все пути относительно корня проекта (у тебя это `~/IvanOS`).

```yaml
paths:
  # Аудитория
  avatar: ".business/audience/avatar.md"
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"

  # Продукт
  products_dir: ".business/products/"
  pricing: ".business/products/pricing.md"

  # Brand DNA / голос
  brand_dna: ".business/Распаковка бренда.md"
  voice_reference: "examples/_TEMPLATE.md"
  voice_corpus_dir: ".business/voice-corpus/"

  # JTBD
  jtbd: ".business/audience/jtbd.md"

  # Карта смыслов (Mode A - Plan)
  content_map: ".business/запуски/<active-launch>/5.2-Карта-смыслов.md"
  content_topics_extra:
    - ".business/Распаковка бренда.md#15-карта-инфоповодов"

  # История постов / каруселей (для no-repeat)
  recent_carousels_source: "manual"     # webfetch | file | manual | none
  recent_carousels_count: 5
  
  # Reel-to-carousel input (Mode D)
  reel_ingest_dir: ".business/growth/ingest/"   # где лежат card.md от ingest-reel

  # Lexicon
  lexicon_required_replacements:
    - replace: "Instagram"
      with: "Нельзяграм"
    - replace: "инстаграм"
      with: "Нельзяграм"
```

**Для ученика:**
1. Скопировать дерево `.business/` из шаблона курса.
2. Заполнить `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`.
3. Указать `<active-launch>` (если идёт запуск) или удалить ссылки на `content_map`.

---

## Voice parameters

```yaml
voice:
  archetypes_allowed: ["Magician", "Sage", "Outlaw"]
  archetypes_banned: ["Caregiver", "Lover", "Innocent"]
  hook_pronoun: "ты"
  formality: low
  rotation_window: 3                    # не повторять archetype 3 carousels подряд
```

---

## Platform specs

```yaml
platforms:
  instagram:
    aspect_ratio: "1080x1350"           # 4:5 portrait, mobile-optimized
    slide_count_optimal: [8, 10]
    slide_count_max: 10
    file_format: ["jpg", "png"]
    caption_max: 2200
    caption_fold_chars: 125             # IG "...more" cutoff
    hashtags_optimal: [3, 5]
    cta_style: "comment_keyword → DM"
    
  linkedin:
    aspect_ratio: "1080x1350"
    slide_count_optimal: [8, 12]
    slide_count_max: 20
    file_format: ["pdf"]                # LI = document PDF only
    caption_max: 3000
    caption_fold_chars: 210             # LI "see more" cutoff
    hashtags_optimal: [0, 2]            # 2026 LI deprioritizes hashtags
    cta_style: "newsletter_subscribe | comment_keyword"
    
  panorama_family:
    canvas_width_per_slide: 1080
    canvas_height: 1350
    slide_count_sweet_spot: 3           # 80% swipe-through
    slide_count_max: 8
    cut_line_clearance_px: 80           # important elements не на cut line
```

---

## Per-family length budgets

```yaml
family_specs:
  framework-breakdown:
    slide_count: [8, 12]
    slide_text_budget:
      hook: [3, 12]                     # words
      value: [5, 25]
      cta: [5, 15]
    structure: "hook + numbered 1-N + CTA"
    reference_creator: "Justin Welsh"
    
  listicle:
    slide_count: [8, 10]
    slide_text_budget:
      hook: [3, 12]
      value: [5, 20]
      cta: [5, 15]
    structure: "hook + N items (odd=text/even=screenshot alternation) + CTA"
    reference_creator: "Riley Brown"
    
  story-case:
    slide_count: [10, 12]
    slide_text_budget:
      hook: [3, 12]
      value: [5, 25]
      cta: [5, 15]
    structure: "hook + context + problem + action + outcome + number + CTA"
    reference_creator: "Lara Acosta / Pieter Levels"
    
  panorama:
    slide_count: [3, 8]
    slide_text_budget:
      leading: [3, 15]                  # leading slide должен работать isolated
      middle: [0, 10]                   # middle slides могут быть text-light
      payoff: [3, 15]
    structure: "leading + middle (continuous wide image) + payoff"
    reference_creator: "Casper / Subway"
    
  reel-to-carousel:
    slide_count: [8, 12]                # adjusts по длине Reel
    slide_text_budget:
      hook: [3, 12]
      value: [5, 25]
      cta: [5, 15]
    structure: "hook frame → 1 beat = 1 slide → reveal → CTA"
    reference_creator: "Welsh repurposing"
    conversion_table:
      reel_15s: [6, 8]
      reel_30s: [8, 10]
      reel_60s: [10, 12]
```

---

## Assets pipeline (NEW v2.0 - обязательно для hero-led templates)

Карусели visual-first: каждый slide содержит hero element (фото / screenshot / scene) занимающий ≥40% canvas. Этот раздел описывает откуда брать hero images per asset_type.

```yaml
assets_pipeline:
  brand_library:
    path: "~/.business/assets/brand-library/"
    subfolders:
      selfies: "Real photos автора (face / portrait / scene)"
      signatures: "Signature shots (recurring brand elements)"
      logos: "Brand logos + sub-brand marks"
      brand_graphics: "Brand graphics (custom illustrations / icons)"
      scenes_cinematic: "Pre-generated AI cinematic scenes (higgsfield-soul-id outputs cached)"
      ui_screenshots: "Pre-captured UI screenshots (Skool / Stripe / Beehiiv / Claude Code / Cursor)"
    when_to_use: "Слайд требует authentic Ivan presence (selfie / scene) OR cached brand element"
    
  ai_generation:
    chain: "higgsfield-generate"
    soul_id_chain: "higgsfield-soul-id"
    when_to_use: "Cinematic background / character scene / mood photo которого нет в brand_library"
    examples:
      - "автор за Claude Code IDE с теплым освещением - higgsfield-soul-id"
      - "Эстетика desk-setup-evening - higgsfield-generate"
      - "Conceptual hero для абстрактных тем (вайбкодинг как ремесло) - higgsfield-generate"
    output_dir: "~/.business/assets/brand-library/scenes-cinematic/{date}-{topic}/"
    
  web_screenshots:
    chain: "ui-record"
    when_to_use: "Need real web app screenshot (Skool MRR / TG Web message / Stripe dashboard / Beehiiv stats / Kit subscriber list)"
    examples:
      - "Skool dashboard $X MRR - ui-record skool.com/community/{slug}"
      - "Beehiiv newsletter stats - ui-record beehiiv.com/dashboard"
      - "Stripe public dashboard share - ui-record stripe.com/payments"
    output_dir: "~/.business/assets/brand-library/ui-screenshots/{date}-{tool}/"
    
  desktop_screenshots:
    chain: "manual queue + AppleScript"
    when_to_use: "Need desktop app screenshot (Claude Code IDE / Cursor / Figma)"
    helpers:
      - "~/scripts/screencap-cc-ide.sh - captures Claude Code IDE window"
      - "~/scripts/screencap-cursor.sh - captures Cursor IDE"
    output_dir: "~/.business/assets/brand-library/ui-screenshots/{date}-{tool}/"
    
  reel_ingest_reuse:
    chain: "ingest-reel card.md frames"
    when_to_use: "Mode D reel-to-carousel - frames из original Reel"
    source: ".business/growth/ingest/{date}-{shortcode}/frames/"

  composition_chain:
    chain: "frontend-design"
    when_to_use: "Need multi-element composition (hero photo + UI overlay + typography) - design aesthetic direction"
    note: "Только для AESTHETIC DIRECTION выбора. Render через 06-render Playwright."

asset_selection_priority:
  # Per slide, выбор asset идёт по приоритету:
  1: "brand_library (cached) - самое быстрое + brand-consistent"
  2: "ui-record web (if applicable) - real UI guarantee"
  3: "higgsfield-soul-id (if hero = Ivan persona) - personal authenticity"
  4: "higgsfield-generate (cinematic scene without persona)"
  5: "manual queue desktop (if UI is desktop-only)"
  6: "FAIL - slide blocked, request user collect asset"
```

**Для ученика:**
- Заменить `~/.business/assets/brand-library/` на свой путь
- Добавить свои `subfolders` под свою нишу (например для здоровья - `food-shots`, `meal-prep`, etc.)
- Если нет higgsfield-soul-id (нет своего soul_id) - заменить chain на higgsfield-generate с persona prompts

---

## Banned AI imagery (12-item checklist)

```yaml
banned_ai_imagery:
  # Auto-fail в CR-G5 если detected в visual brief
  
  - "Generic AI-illustrated люди в офисах (Midjourney corporate стиль)"
  - "Gradient blob backgrounds + 3D abstract shapes"
  - "Robot hands typing / brain with circuits клише"
  - "Stock photos 'diverse team smiling at laptop'"
  - "AI-generated avatars вместо real photo автора"
  - "Generic vector icons вместо real product logos"
  - "Soft pastel backgrounds без content"
  - "Fake/cropped dashboards (репутационный риск)"
  - "Symbolic 'expert' illustration generic"
  - "AI-generated charts без реальных чисел"
  - "Corporate buzzwords overlay (synergy/leverage)"
  - "Vector illustrations с американцами для RU аудитории"

# Поле для расширения ученикам - добавлять свои nuance-specific
banned_ai_imagery_user_extra: []
```

**Для ученика:** добавлять свои nuance-specific banned patterns в `banned_ai_imagery_user_extra`. Например для здоровья - banned "stock photo doctor stethoscope".

---

## Lexicon (банлисты)

```yaml
lexicon_banned_hard:
  # Auto-fail в slide text или caption
  
  # Em-dash
  - "-"                                 # em-dash внутри строк (только начало буллета OK)
  
  # Англицизмы-формализмы
  - "валидируется"
  - "валидация"
  - "onboarding"
  - "онбординг"
  - "engagement"
  - "энгейджмент"
  - "retention"
  - "pipeline"
  - "пайплайн"
  - "framework"
  - "фреймворк"
  - "workflow"
  - "webhook"
  - "endpoint"
  - "rate-limit"
  - "scope"
  - "скоуп"
  - "оркестратор"
  - "функционал"
  - "артефакт"
  - "digital-twin"
  - "fast-action"
  - "Grand Slam Offer"
  - "КЭВ"
  - "связки"
  
  # Generic AI clichés
  - "без воды"
  - "без теории"
  - "безопасная подушка"
  - "финансовая страховка"
  - "адская"
  - "звезду прошлого"
  
  # Formal explanatory linkers
  - "именно поэтому"
  - "так как"
  - "в результате чего"
  - "по причине"
  - "вследствие"
  - "таким образом"
  - "следовательно"

lexicon_warnings:
  - pattern: "!{2,}"                    # >1 восклицательного
    message: "more than one exclamation"
  - pattern: "^[-*•]"
    count_threshold: 2
    message: "more than one bullet list per caption"
```

**Для ученика:** базовый список одинаков. Добавлять свои термины под свою нишу.

---

## Output settings

```yaml
output:
  ab_variants: 2                        # сколько A/B вариантов hook/caption
  show_3layers_report: true
  show_assets_manifest: true            # список всех нужных assets (UI screenshots, photos)
  open_artifacts: true                  # после output - open готовый brief
  caption_languages:                    # auto-derive из subject.language
    - ru
    # - en                              # uncomment если subject.language=both
```

---

## Validation refresh tracking

```yaml
validation:
  banned_ai_imagery_last_review: "2026-05-28"
  banned_ai_imagery_refresh_days: 14   # 2 weeks
  banned_lexicon_last_review: "2026-05-28"
  banned_lexicon_refresh_days: 7
```

---

## Quick start для нового пользователя

Если ты ученик и только что склонировал скилл:

1. **Прочитай SKILL.md** - поймёшь архитектуру (5 семейств / 4 режима).
2. **Запусти `/carousel`** без аргументов.
3. Скилл проверит этот config и спросит чего не хватает.
4. **Заполни недостающее** - путь к avatar, JTBD, brand-dna, products.
5. Если нет активного запуска - установи `content_map: null`.
6. **Запусти `/carousel про X`** - получишь первую карусель.

---

## Активный запуск автора

```yaml
active_launch:
  ru: "<твоя-папка-запуска>"
  en: null                              # ещё не стартовал
```

Используется для подстановки `<active-launch>` выше. Когда стартует новый запуск - обновить здесь.