---
name: longform-config
version: "1.0"
last_reviewed: 2026-05-28
description: Конфиг скилла longform. Указывает пути к контексту проекта (аватар / JTBD / Brand DNA / Карта смыслов / гостинг longform-сайтов / последние newsletter / LinkedIn articles) и parameters голоса автора + priority platform. автор клонирует ученикам - каждый ученик меняет пути под свой проект и под свои платформы.
---

# longform config

> Это **точка адаптации скилла под конкретного автора и под его платформы**. Скилл (`longform`) одинаков у автора и у учеников. Различие - только в этом файле и в данных, на которые он указывает.

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  language: ru
  market: ru
  # secondary market - для bilingual выпуска
  secondary_market: en
  bilingual_mode: "ru_canonical"  # ru_canonical | en_canonical | mirror
  # Семантика ключевых терминов автора
  product_focus: "<твоя ниша / продукт>"
  longform_cadence: "1-2 раза в неделю (newsletter pillar + LinkedIn article)"
  voice_register: "тёплый-инженерный, разговорный, story-first для RU"
```

**Для ученика:** заменить `name`, `language`, `market`. `bilingual_mode = ru_canonical` если основной язык RU, `en_canonical` если EN, `mirror` если выпускаешь параллельно с разными структурами.

---

## Platforms (куда канонически идёт longform)

```yaml
platforms:
  # Канонический хост - primary POSSE target
  canonical:
    type: "personal_blog"
    url: "<твой-домен>/blog"
    slug_pattern: "/blog/{slug}"
    rel_canonical: true
    length_floor: 1200
    length_ceiling: 3000

  # Newsletter primary
  newsletter:
    provider: "kit"  # kit | beehiiv | substack | mailerlite
    url: "<твой-домен>/newsletter"
    length_floor: 1000
    length_ceiling: 2200
    subject_ab_variants: 3
    preheader_required: true

  # LinkedIn article (распределение)
  linkedin:
    profile_url: "https://www.<твой-linkedin>"
    length_floor: 800
    length_ceiling: 1800
    headline_strategy: "different_from_blog"  # LinkedIn audience требует свой headline
    rel_canonical_to_blog: true

  # Substack / Medium cross-post
  cross_post_targets:
    - provider: "substack"
      url: "<твой-newsletter>"
      rel_canonical_to_blog: true
    - provider: "medium"
      url: "https://medium.com/<твой-хэндл>"
      rel_canonical_to_blog: true
```

**Для ученика:**
1. Выбрать **canonical type**: personal_blog (если есть свой сайт) | newsletter (если есть только Kit/Beehiiv/Substack без своего сайта) | linkedin (если только LinkedIn).
2. Указать **provider** newsletter - `kit` / `beehiiv` / `substack` / `mailerlite` (от него зависит форматирование в `05-publish.md`).
3. `rel_canonical_to_blog: true` означает что cross-post с указанием канонического URL - стандарт POSSE.
4. `cross_post_targets` можно расширять или сокращать. Если канал ещё свежий - оставить только canonical.

---

## Paths (где лежит контекст проекта)

Все пути относительно корня проекта (у тебя это `~/IvanOS`).

```yaml
paths:
  # Аудитория
  avatar: ".business/audience/avatar.md"
  segments: ".business/audience/segments.md"
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"

  # Продукт
  products_dir: ".business/products/"
  pricing: ".business/products/pricing.md"

  # Brand DNA / голос
  brand_dna: ".business/Распаковка бренда.md"
  voice_reference: "examples/_TEMPLATE.md"
  voice_corpus_dir: ".business/voice-corpus/"
  story_bank_dir: ".business/story-bank/"

  # JTBD
  jtbd: ".business/audience/jtbd.md"

  # Карта смыслов (Mode A - Plan)
  content_map: ".business/запуски/<active-launch>/5.2-Карта-смыслов.md"
  content_map_format: "thematic"  # calendar | thematic | hybrid
  # Дополнительные источники инфоповодов
  content_topics_extra:
    - ".business/marketing/content.md#3-pillars"
    - ".business/Распаковка бренда.md#15-карта-инфоповодов"

  # Контент-план longform (если ведётся отдельно от Карты смыслов)
  longform_content_plan: ".business/marketing/longform-plan.md"

  # История публикаций longform (для no-repeat / type rotation)
  recent_articles_source: "webfetch"  # webfetch | file | none
  recent_articles_urls:
    - "<твой-домен>/blog"      # personal blog feed
    - "https://www.<твой-linkedin>/recent-activity/articles/"
  recent_articles_count: 5

  # Запретные термины и обязательная лексика (наследуется из post)
  lexicon: "config-lexicon.md"
```

**Для ученика:**
1. Скопировать дерево `.business/` из шаблона курса под свой проект.
2. Заполнить файлы: `avatar.md`, `jtbd.md`, `Распаковка бренда.md`, `products/`.
3. Указать **активный запуск** в `<active-launch>` (если идёт запуск) или удалить ссылку на `content_map`.
4. Указать URL канала longform или поставить `null` если сайт свежий.

---

## Voice parameters

```yaml
voice:
  archetypes_allowed: ["Magician", "Sage", "Outlaw"]
  archetypes_banned: ["Caregiver", "Lover", "Innocent"]
  pronoun: "ты"
  formality: low
  type_rotation_window: 3  # не повторять тип последние N статей
  # Долгие формы - особенности
  paragraph_length: "varied"  # short / medium / varied
  section_rhythm: "intro-3-payoff"  # Koe 3-section structure
  voice_quirks:
    - "конкретные числа и кейсы вместо абстракций"
    - "personal anchor в первых 2 абзацах"
    - "контр-интуитивные открытия как hook"
    - "разговорный, как будто пишешь близкому"
```

**Для ученика:** настроить под свою позиционировку. Если непонятно какие архетипы - пройти Фазу 0 запуска (опрос аудитории + Brand DNA).

---

## Lexicon (обязательная и запретная)

Базовая часть наследуется из `post/config.md` (см. там полный список). Здесь только longform-specific дополнения.

```yaml
lexicon_required:
  - replace: "Instagram"
    with: "Нельзяграм"
  - replace: "инстаграм"
    with: "Нельзяграм"

# Longform-specific banned (formulaic transitions)
lexicon_banned_longform:
  - "Now let me tell you"
  - "So here's the thing"
  - "But wait, there's more"
  - "А теперь самое интересное"
  - "Но это ещё не всё"
  - "И вот что я понял"
  - "Сейчас расскажу как"
  - "В этой статье я разберу"
  - "Давайте по порядку"

# Generic listicle patterns (auto-fail если template != listicle)
lexicon_banned_listicle_patterns:
  - "10 ways to"
  - "10 способов"
  - "5 reasons why"
  - "5 причин почему"
  - "Top 7"
  - "Топ-7"
  - "The ultimate guide"
  - "Полный гайд"
  - "Everything you need to know"
  - "Всё что нужно знать"

# Длина регулируется по platform - см. platforms.* выше
lexicon_warnings:
  - pattern: "![!]+"
    message: "more than one exclamation mark in row - снижай эмоциональность"
  - pattern: "^[*•]"
    count_threshold: 5
    message: "more than 5 bullets in row - конвертируй в prose или подсекции"

# Базовый banned лист наследуется из post config
lexicon_banned_hard_inherit_from: "~/.claude/skills/post/config.md#lexicon_banned_hard"
```

**Для ученика:** базовый список одинаков. Добавить свои формульные переходы и свои listicle-паттерны под нишу.

---

## Output settings

```yaml
output:
  show_self_check_report: true
  show_pose_distribution_map: true
  ab_subject_lines: 3
  derivatives_plan: true  # планировать X-thread / carousel / shorts на основе longform
  format_modes:
    - "markdown"  # default - для blog
    - "html"      # для Beehiiv / Kit
    - "linkedin"  # plain text with line breaks для LinkedIn editor
```

---

## Quick start для нового пользователя

Если ты ученик и только что склонировал скилл:

1. **Прочитай SKILL.md** - поймёшь архитектуру.
2. **Запусти `/longform`** без аргументов в первый раз.
3. Скилл проверит этот config и спросит чего не хватает.
4. **Заполни недостающее** - пути к avatar, JTBD, brand-dna, platforms.
5. Если канала ещё нет - установи `recent_articles_source: none` и оставь только `canonical`.
6. **Запусти `/longform про X`** - получишь первый longform.

---

## Активный запуск автора

```yaml
active_launch:
  ru: "<твоя-папка-запуска>"
  en: null
```

Используется для подстановки в `<active-launch>` выше. Когда стартует новый запуск - обновить здесь.

---

## Cross-skill наследование

Этот config наследует:

- **`post/config.md`** - базовый `lexicon_banned_hard` (см. `lexicon_banned_hard_inherit_from`)
- **`post/references/maxwell-ross-9-checklist.md`** - проходит к `longform/references/`
- **`post/references/archetypes-12.md`** - общая mapping архетипов

Когда обновляется banned-лист в `post/config.md` - автоматически применяется здесь через workflow `04-review.md` Pass 0 mandatory read.