---
name: email-config
version: "1.0.1"
last_reviewed: 2026-05-28
description: Конфиг скилла email. Указывает пути к контексту проекта (аватар / JTBD / Brand DNA / карта воронки / launch sequence map) + ESP + voice params + language + privacy (action-skill gates). автор клонирует ученикам - каждый ученик меняет пути под свой проект.
---

# Privacy section (Action-skill Gate C)

```yaml
privacy:
  redact_pii_in_context: true       # default ON
  pii_patterns:
    - "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"  # email
    - "\\+?7[\\s\\-]?\\(?\\d{3}\\)?[\\s\\-]?\\d{3}[\\s\\-]?\\d{2}[\\s\\-]?\\d{2}"  # phone RU
    - "\\b\\d{4}[\\s\\-]?\\d{4}[\\s\\-]?\\d{4}[\\s\\-]?\\d{4}\\b"  # credit card
    - "\\$\\s?\\d{1,3}[KMB]?"                                  # финансовые snapshots
    - "\\d+\\s?(тыс|млн|K|M|B)"                                 # количественные snapshots
  replace_with: "<PII>"
  skip_files:
    - ".business/products/pricing.md"   # публичные цены, не PII
    - ".business/assets/testimonials.md"  # публичные кейсы
```

# Validation hooks (action-skill enforcement)

```yaml
validation:
  pii_redaction_required: true        # Pass 0.5 enforce
  event_existence_required: true       # Pass 0.6 enforce
  fact_verification_required: true     # Pass 0.7 enforce
  cta_verb_object_pair_required: true  # EMAIL-G3 Gate D
  cta_url_must_return_200: true # правка автора: КАЖДЫЙ URL в письме curl-проверить (HTTP 200) ПЕРЕД выдачей; канон воркшопа = {{ССЫЛКА_НА_ТВОЙ_ОФФЕР}} (НЕ.html — 404)
  self_review_factlist_required: true  # Layer 5.5 Gate E
```

**Не отключать без явного решения.** Это hard gates действия action skill.

---

# email config

> Это **точка адаптации скилла под конкретного автора**. Скилл (`email`) одинаков у автора и у учеников. Различие - только в этом файле и в данных, на которые он указывает.

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  language: ru          # ru | en | both - default language for outputs
  market: ru            # ru | en | both
  # Семантика ключевых терминов автора
  product_focus: "<твоя ниша / продукт>"
  funnel_position: "newsletter → клуб Skool <твоя подписка> → cash events <твой ценовой диапазон> <частота запусков>"
```

**Для ученика:** заменить `name`, `language`, `product_focus` на свои. Если ученик ведёт RU и EN параллельно - `language: both`, skill будет выдавать обе версии.

---

## ESP (Email Service Provider)

```yaml
esp:
  default: kit                    # kit | beehiiv
  kit:
    plain_text_bias: true         # Kit предпочитает plain-text
    broadcast_or_sequence: broadcast  # broadcast | sequence
    tags_enabled: true
    deliverability_audit: true    # Pass 5 review запускает spam-trigger scan
  beehiiv:
    html_blocks_enabled: true
    segments_enabled: true
    premium_tier_targeting: false
```

**Для ученика:** если используешь Kit - оставить дефолт. Если Beehiiv - поменять `default: beehiiv`. Если оба - `default: kit` (для broadcast) + `beehiiv` opt-in через флаг `--esp beehiiv`.

---

## Paths (где лежит контекст проекта)

Все пути относительно корня проекта (`~/IvanOS` у автора = домашняя директория с `.business/`).

```yaml
paths:
  # Аудитория
  avatar: ".business/audience/avatar.md"
  segments: ".business/audience/segments.md"     # опционально
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"

  # Продукт
  products_dir: ".business/products/"
  pricing: ".business/products/pricing.md"

  # Brand DNA / голос
  brand_dna: ".business/Распаковка бренда.md"
  voice_reference_ru: "examples/_TEMPLATE.md"
  voice_reference_en: "examples/_TEMPLATE.md"

  # JTBD
  jtbd: ".business/audience/jtbd.md"

  # Карта воронки (Mode A - Plan) + launch sequence
  funnel_map: ".business/marketing/funnel.md"
  launch_sequence_map: ".business/запуски/<твоя-папка-запуска>/launch-sequence.md"  # раскрыт литерально: email workflow плейсхолдер не подставляет 
  active_launch: "<твоя-папка-запуска>"   # имя папки активного запуска

  # Voice-bridge на post (общий voice)
  tg_content_voice: "~/.claude/skills/post/references/_voice-TEMPLATE.md"
  tg_content_living_language: "~/.claude/skills/post/references/_voice-TEMPLATE.md"
  tg_content_archetypes: "~/.claude/skills/post/references/archetypes-12.md"
  tg_content_hooks: "~/.claude/skills/post/references/hooks-15-templates.md"
  tg_content_maxwell_ross: "~/.claude/skills/post/references/maxwell-ross-9-checklist.md"

  # История писем (для no-repeat по subject lines)
  recent_emails_dir: ".business/marketing/email-archive/"
  recent_emails_count: 20    # последние 20 subjects читать перед генерацией A/B вариантов

  # Бизнес-контекст для fact verification (Action-skill Gate A)
  business_index: ".business/INDEX.md"
  business_index_is_private: true  # содержит финансовые snapshots
  testimonials: ".business/assets/testimonials.md"
  testimonials_is_private: false  # публичные кейсы

  # Upcoming events (Action-skill Gate B verification)
  # Список запланированных events. Pass 0.6 verifies mentions против этого + active launch dir.
  upcoming_events: []
  # Пример:
  # upcoming_events:
  #   - name: "Эфир по запуску курса"
  #     date: "2026-05-29 19:00 MSK"
  #     type: "live"
  #     url: "https://..."

  # Запретные термины и обязательная лексика
  lexicon: "config-lexicon.md"

  # Output
  output_dir: ".business/marketing/email-outbox/"
  output_filename_format: "YYYY-MM-DD-{type}-{slug}.md"
```

**Для ученика:**

1. Скопировать дерево `.business/` из шаблона курса под свой проект.
2. Заполнить файлы: `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`, `.business/marketing/funnel.md`.
3. Указать **активный запуск** в `<active-launch>` (если идёт запуск) или удалить ссылку на `launch_sequence_map` (Mode A для launch sequence работать не будет, останутся nurture + sales-letter из funnel map).
4. Указать ESP и оставить voice-bridge путь на post (если post тоже клонирован).

---

## Voice parameters

```yaml
voice:
  archetypes_allowed: ["Magician", "Sage", "Outlaw"]
  archetypes_banned: ["Caregiver", "Lover", "Innocent"]
  rhythm: "1/3/1"
  pronoun_ru: "ты"
  pronoun_en: "you"
  formality: low                 # low | mid | high
  rotation_window: 5             # не повторять archetype последние N писем
  first_line_max_chars: 60       # первая строка письма - короткая (above-fold)
  paragraphs_target: "3-7"       # 3-7 параграфов в body для nurture/launch; sales до 12
```

**Для ученика:** настроить под свою позиционировку. Архетипы выходят из Brand DNA / Распаковки бренда.

---

## Email-specific parameters

```yaml
email:
  # Subject lines
  subject_max_chars: 50          # hard fail >60, warning >50
  subject_min_chars: 15
  subject_ab_count: 3            # минимум 3 варианта A/B, max 5
  subject_frameworks_per_ab:
    - curiosity                  # «То чего я не говорил год»
    - direct_benefit             # «Как я делаю $5K/мес из 100 подписчиков»
    - contrarian                 # «Почему я больше не пишу daily»
    - numbered                   # «3 ошибки которые убивают конверсию»
    - personal_confession        # «Я облажался вчера»
    - question                   # «Ты тоже так делаешь?»
    - urgency                    # «Last call: до полуночи» (только в окне продаж sales-letter)

  # Preheader
  preheader_min_chars: 50
  preheader_max_chars: 90
  preheader_dup_threshold: 0.7   # similarity > 70% с Subject → fail

  # CTA
  cta_count_per_email: 1          # одна цель письма (для sales-letter - 1 цель, повторяется 2-3 раз)
  cta_link_min_count_nurture: 1
  cta_link_min_count_sales: 2     # above-fold + bottom

  # Body
  body_min_words_nurture: 600
  body_max_words_nurture: 900
  body_min_words_launch: 350 # правка по решению автора: floor = защита от огрызка; pre-launch тизеры плотные и короткие. Sweet-spot ПО ПОЗИЦИИ (pre-launch -1d 400-600, -3d 600-800, launch-day 800-1200) живёт в templates/launch-sequence-email.md, не дублируется hard-floor'ом
  body_max_words_launch: 1200
  body_min_words_sales: 800
  body_max_words_sales: 1500

  # Mobile-first
  first_para_max_chars: 200       # above-fold preview
  bullet_count_max: 1              # порог, пока brief.form_goal не объявлена: >1 списка в одном письме = warning, >2 = fail (кроме sales-letter где допустимо 2)
  # K-email (канон формы v2 §9 + §8.2 таблица «≤1 список»): при объявленной brief.form_goal порог берётся из профиля, не из bullet_count_max выше.
  # Сравнение идёт со СЛОВОМ в brief.form_goal (reactions / forwards / sales) и brief.form_class (narrative / razbor / sales);
  # буквы R / F / S ниже - это имена профилей из канона и значением для сравнения не являются:
  #   form_goal=reactions + form_class=narrative (профиль R-нарратив): 0 блоков (HARD, §9 режим R п.9, держат 93% верха) - список любого размера = FAIL, не warning
  #   form_goal=reactions + form_class=razbor (профиль R-разбор): ≤1 блок до 3 предикативных пунктов (WARN, §9 режим R п.9)
  #   form_goal=forwards (профиль F, репосты): 1-2 блока тире со ссылкой - опись это несущая конструкция носителя, желательна, не штраф (WARN, §9 режим F п.4 + §8.2 таблица «≤1 список»)
  #   form_goal=sales (профиль S, продажа): ≤1 блок (§8.2 таблица «≤1 список»; в §9 режим S явного пункта под список нет - число берётся из таблицы §8.2)
  #   Пустой brief.form_goal -> письмо не выпускается: EMAIL-G12 даёт FAIL, возврат в workflow/01-router.md Step 5.5 FORM-GOAL ROUTER за целью

  # A/B output
  output_show_all_subjects: false # правка автора: A/B только внутренняя кухня, в выдачу ТОЛЬКО финальная тема (winner)
  output_recommend_winner: true    # skill рекомендует winner на основе типа письма + voice fit

  # Sequence-awareness
  sequence_position_required_for_launch: true   # без позиции в launch-sequence-map fail для Mode A launch
```

---

## Lexicon (обязательная и запретная)

См. `config-lexicon.md` (отдельный файл - лексика автора).

```yaml
lexicon:
  file: "config-lexicon.md"
  auto_replace:
    Нельзяграм: Нельзяграм
    инсту: Нельзяграм
    Facebook: Запрещённограм
  banned:
    - artifact
    - digital-twin
    - fast-action
    - КЭВ
    - связки
    - Grand Slam Offer
    - vendor-lock
    - архитектор ИИ-систем
    - Дубайск          # в email Дубайск НЕ используется, в отличие от TG где допустимо в личном контексте
    - "девочки"
    - "вахвахвах"
    - "Уважаемый подписчик"
    - "Дорогой друг"
    - "Здравствуйте, уважаемые"
```

---

## No-repeat history

```yaml
no_repeat:
  enabled: true
  source: file                   # file | api | none
  count: 20                      # последние N писем
  match_on:
    - subject_full
    - subject_hook_framework
    - cta_goal
    - body_main_topic
  threshold: 0.65                # similarity > 65% по любому из match_on = warning, > 85% = fail
```

**Зачем:** не отправлять подписчикам письмо с Subject почти как у предыдущего → unsubscribe risk.

---

## Spam-trigger sensitivity

```yaml
spam_check:
  enabled: true
  source: "references/spam-triggers-list.md"
  hard_fail_words_ru:
    - "бесплатно"           # допустимо контекстно «бесплатный гайд внутри», но не в Subject
    - "срочно"
    - "только сегодня"
    - "ОФИЦИАЛЬНО"
    - "100%"
    - "гарантия"            # контекстно в sales-letter допустимо «гарантия возврата 14 дней»
    - "недорого"
  hard_fail_words_en:
    - "free"
    - "urgent"
    - "guaranteed"          # контекстно в sales допустимо «money-back guarantee»
    - "ACT NOW"
    - "100%"
  warning_patterns:
    - "[A-ZА-Я]{4,}"        # 4+ CAPS подряд
    - "!{2,}"                # >1 «!»
    - "\\${1,}\\d"           # «$50», «$1997»
    - "₽\\s?\\d"
```

---

## Output format

```yaml
output:
  format: markdown
  formatting_always: true # правка автора «сразу с форматированием и всегда»
  output_in_code_fence_raw_markdown: true  # 🔴 финальный текст ВСЕГДА в ```-fence с СЫРЫМИ маркерами, чтобы **/__ скопировались дословно (НЕ отрендеренный жирный — маркеры теряются при копировании в Telegram)
  formatting_rules:
    bold: "опорные тезисы / главная выгода / дедлайн / цифра-доказательство, 2-5 на письмо (Telegram-markdown **...**)"
    italic: "смягчающие ремарки / P.S. (Telegram-markdown __...__), по канону голоса §3"
    never_plain: true              # НЕ выдавать письмо голым plain-text
    never_rendered: true           # НЕ выдавать отрендеренный markdown в чат — только raw в код-блоке
  structure:
    - section: "Subject"
      content: "ровно ОДИН (варианты списком = брак, правка автора); кандидаты сравниваются внутри, отброшенные - строкой во Внутрянке"
    - section: "Preheader"
      content: "single line, 50-90 chars"
    - section: "Body"
      content: "plain-text (Kit default) или HTML blocks (Beehiiv opt-in)"
    - section: "CTA"
      content: "ровно 1 цель письма, link + кнопка-текст"
    - section: "Внутрянка"
      content: "как писал: Mode / type / hook framework / archetype / CTA-goal / sequence-position / A/B логика / что отброшено"
  copy_ready: true              # output блок copy-paste ready в Kit/Beehiiv ESP
  separate_files_for_languages: true   # если language=both → два output файла RU.md + EN.md
```

---

## Когда пересматривать config

- Сменилась ESP платформа (Kit → Beehiiv)
- Сменился активный запуск (`active_launch`)
- Сменился `language` (RU → EN или both)
- 3+ систематических промаха voice → пересмотреть `archetypes_allowed` / `rotation_window`
- Smam-trigger false-positives - обновить `hard_fail_words` лист
- Раз в 3 месяца минимум