---
name: bot-message-config
version: "1.0"
last_reviewed: 2026-05-28
description: Конфиг скилла bot-message. Указывает пути к контексту проекта (avatar / funnel-map / brand-dna / последние push), параметры голоса автора, параметры бота (handle, button engine, segments), language. автор клонирует ученикам - каждый ученик меняет под свой проект.
---

# bot-message config

> Это **точка адаптации скилла под конкретного автора и бота**. Скилл (`bot-message`) одинаков у автора и у учеников. Различие - только в этом файле и в данных, на которые он указывает.

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  language: ru
  market: ru
  # Дополнительные семантические якоря для voice
  product_focus: "<твоя ниша / продукт>"
  positioning: "вайбмаркетинг - категория автора, вайбкодинг - инструмент в ядре"
```

**Для ученика:** заменить `name`, `product_focus`, `positioning` на свои.

---

## Bot (целевой бот воронки)

```yaml
bot:
  handle: "<твой-хэндл>_bot"           # Имя бота, куда уходит push
  engine: "telegram_bot_api"               # telegram_bot_api | senler | getcourse | other
  button_engine: "inline_keyboard"         # inline_keyboard | reply_keyboard | none
  # Допустимые типы кнопок (config задаёт что доступно в этом боте)
  supported_button_types:
    - url
    - callback_data
    - web_app
  # Сегменты подписчиков (опционально, для drip / re-engagement / event-trigger)
  segments:
    - cold              # не открывал >30 дней
    - warm              # последний открыл 7-30 дней назад
    - hot               # открыл за последние 7 дней
    - buyer_skool       # купил клуб
    - buyer_cash_event  # купил cash event
  # URL для кнопок (часто используемые)
  primary_landing_url: "https://<твой-домен>"
  skool_join_url: null  # заполнить когда EN запуск с июня 2026

  # Upcoming events (Action-skill Gate B verification)
  # Список реальных запланированных событий. Pass 0.6 Event existence check
  # match'ит mentions в draft против этого списка.
  # Формат: name | date | type | url-or-callback
  upcoming_events: []
  # Пример заполненного:
  # upcoming_events:
  #   - name: "Эфир по запуску курса вайбкодинг"
  #     date: "2026-05-29 19:00 MSK"
  #     type: "live"
  #     callback: "live_2026-05-29_join"
  #   - name: "Открытие окна продаж клуба"
  #     date: "2026-06-15"
  #     type: "launch"
  #     url: "https://skool.com/..."
```

**Для ученика:**
1. Указать handle своего бота.
2. Указать engine: для самописного бота на aiogram - `telegram_bot_api`. Senler / GetCourse имеют ограничения по button JSON формату - будет адаптация в `05-publish.md`.
3. Сегменты - список тех меток, которые реально настроены в боте. Если сегментов нет (свежий бот) - оставить только `all`.

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
  voice_reference_long: "references/_voice-TEMPLATE.md"  # cross-ref на gold-standard постов
  voice_reference_bot: "references/_voice-TEMPLATE.md"                            # bot-specific (когда заполнен)

  # Карта воронки (Mode A - Plan)
  funnel_map: ".business/запуски/<active-launch>/voronka-map.md"
  funnel_map_format: "step-based"  # step-based | day-based | trigger-based
  # Карта воронки = source of truth для следующего шага.
  # Если файла нет - Mode A падает в fallback на Spark-B2 с warning.

  # История push (для no-repeat в Spark-B2)
  recent_push_source: "manual"          # manual | file | none
  recent_push_log: ".business/bot/recent-push.md"  # ручной лог последних 10 push (формат: дата | тип | hook | результат)
  recent_push_count: 10

  # Бизнес-контекст для fact verification (Action-skill Gate A)
  business_index: ".business/INDEX.md"
  business_index_is_private: true  # содержит финансовые данные, redact PII при чтении

  # Лексикон (запреты и обязательные термины)
  lexicon: "~/.claude/skills/post/config-lexicon.md"  # переиспользуем общий с post
```

**Для ученика:**
1. Скопировать дерево `.business/` под свой проект.
2. Заполнить `avatar.md`, `journey.md`, `products/`.
3. Создать `voronka-map.md` под активный запуск (или удалить пути если воронки нет - Mode A работать не будет).
4. Если ведёшь лог push - указать путь. Если нет - `recent_push_source: none`.

---

## Voice parameters

```yaml
voice:
  # Голос автора: short, imperative, direct address «ты»
  address: "ты"             # «ты» / «вы» / «безличное»
  imperative_friendly: true # «глянь», «жми», «открой» - допустимы
  emoji_policy: "minimal"   # off | minimal (≤1 per push) | accent (1 in hook + max 1 in tail)
  exclamation_max: 0        # bot push: 0 восклицательных знаков (notification noise)
  ellipsis_allowed: false   # многоточия запрещены (выглядят слабо)
  question_max: 1           # ≤1 вопрос на push (рассеивает фокус)

  # Запретные термины для bot push
  banned_terms:
    - "Instagram"            # → Нельзяграм
    - "artifact" / "артефакт"
    - "digital-twin"
    - "КЭВ"
    - "связки"
    - "Grand Slam Offer"
    - "цена в личке"
    - "сразу же"             # waffle
    - "буквально"            # filler
    - "по сути"              # filler
    - "просто"               # weakens
    - "довольно"             # weakens
    - "достаточно"           # weakens

  # Запрет на metaphor abuse в коротком формате
  no_metaphor_in_first_50chars: true
  no_metaphor_in_buttons: true

  # Rotation: не повторять hook framework последние 3 push
  hook_rotation_window: 3
  type_rotation_window: 5  # не повторять тип сообщения последние 5 push
```

**Для ученика:** настроить под свой стиль. Если бот формальный - `address: "вы"`, `imperative_friendly: false`. Если канал бренда более emoji-friendly - `emoji_policy: "accent"`.

---

## Length policy

```yaml
length:
  text:
    min: 80                # warning ниже
    target_short: [80, 150]   # короткий push (reminder)
    target_medium: [120, 220] # средний (voronka-push)
    target_long: [180, 300]   # средне-длинный (event-trigger, survey-poll)
    target_tease: [300, 700]  # развёрнутый тизер 2-3 абзаца (content-tease, broadcast-news, drip-segment) — fix 2026-05-29: один абзац не разворачивает ценность
    max_short: 300         # hard cap для short/medium/long типов
    max_tease: 800         # hard cap для tease/news/drip (2-3 абзаца)
  buttons:
    count_min: 1           # минимум кнопок (push без CTA = пост, не push)
    count_max: 3           # больше - парализует выбор
    text_min: 8            # «Открыть» - минимум воспринимаемый
    text_max: 24           # ограничение mobile truncation
  hook:
    preview_chars: 50      # iOS notification preview ≈ 50 знаков
    must_carry_meaning: true  # в этих 50 знаках смысл должен считываться
```

---

## Output format

```yaml
output:
  format: "chat"  # chat | file | both
  # chat = текст готов к копи прямо в чате (рекомендуется для CLI / mobile)
  # file = сохранить в .business/bot/drafts/<date>-<type>.md
  json_style: "telegram_bot_api"  # telegram_bot_api | senler | getcourse
  include_ab_variant: true        # всегда показывать 1 A/B альтернативу
  include_internals: true         # включать блок «как писал» (Mode/type/hook/button strategy/что отброшено)
  open_after_save: false          # если file - открывать через `open`?
```

---

## Bilingual mode (EN запуск с июня 2026)

```yaml
bilingual:
  enabled: false  # включить когда EN бот запущен
  primary: ru
  secondary: en   # дублировать push в EN-боте?
  en_voice_reference: null  # путь к EN gold-standard когда будет
  # Если both - output Mode A: RU + EN параллельно с одинаковой структурой
```

**Для ученика:** обычно `enabled: false`. Включается только если у автора 2 бота (RU + EN) и нужно дублировать.

---

## Cross-refs на другие skills

```yaml
cross_refs:
  tg_content: "~/.claude/skills/post/"          # длинные посты в канал
  longform: "~/.claude/skills/longform/"              # 800-3000 слов эссе
  email: "~/.claude/skills/email/"                    # email рассылки
  paips_post: "~/.claude/skills/paips-post/"          # X/Threads/LinkedIn PAIPS
  voice_reference_source: "references/_voice-TEMPLATE.md"
  living_language_source: "~/.claude/skills/post/references/_voice-TEMPLATE.md"
```

**Зачем:** `bot-message` переиспользует voice references из `post`, чтобы не дублировать (один голос автора = один источник). Bot-специфика накладывается сверху через `references/_voice-TEMPLATE.md`.

---

## Privacy (PII redaction)

```yaml
privacy:
  redact_pii_in_context: true       # default ON. Redact PII перед использованием контекста для draft
  pii_patterns:
    - email                          # \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b
    - phone_ru                       # \+?7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}
    - phone_intl                     # \+\d{1,3}\s?\d{4,14}
    - credit_card                    # \b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b
    - tg_token                       # \d{9,10}:[A-Za-z0-9_-]{35}
  replace_with: "<PII>"               # placeholder при replace
  skip_files:                         # файлы где PII OK (own subscriber data, internal)
    - ".business/audience/avatar.md"  # ICP/persona без real subscribers
```

**Зачем:** skill читает `funnel_map.md`, `avatar.md`, `objections.md`, `recent_push_log` - там могут быть real subscriber emails/phones/Stripe IDs. При генерации draft эти данные попадают в Anthropic API context. Redaction до использования - mitigation.

**Для ученика:** оставить default ON. Если PII специально нужно (например, в lead magnet с конкретным email подписчика - кастомизированный onboarding push) - отключить точечно через override в конкретном workflow stage.

---

## Validation hooks (опционально)

```yaml
validation:
  notification_preview_test: true   # обязательная проверка: первые 50 знаков читаемы без контекста?
  button_clarity_test: true         # обязательная проверка: понятно ли куда ведёт кнопка из её текста + 50 знаков push?
  three_layers_required: true       # 3 слоя финального gate обязательны
  ab_variant_required: true         # A/B вариант обязателен в output
  pii_redaction_required: true      # PII redaction перед использованием контекста (см. privacy выше)
  transcript_sanitize_required: true  # Mode C Pass 0.5 sanitize check
  rate_limit_preflight_required: true  # 05-publish.md pre-flight расчёт для базы >100
  callback_timing_note: true        # для callback кнопок - note про 15s rule в внутрянке
```

**Не отключать без явного решения** - это hard gates скилла.

---

## Самообучение

В конце сессии (после каждого `/push`) - если автор дал обратную связь:
1. Точечная правка в текущем push.
2. Системная правка: добавить anti-pattern в `references/bot-anti-patterns.md` ИЛИ ужесточить gate в `workflow/04-review.md` ИЛИ обновить banned_terms в этом config.

Принцип `feedback-each-correction-becomes-system-rule` (см. `post` принцип 13).