# config.md - Portable adaptation point

Этот файл - единственная точка адаптации скилла `video` под конкретного автора. Меняешь только этот файл при клонировании скилла на нового ученика.

В v1.0 - hardcoded под автора. В v1.1 будет генериться через `workflow/00-onboarding-student.md` (9 вопросов).

## Subject

```yaml
subject:
  name: "<Твоё имя>"
  handle_tg: "<твой-хэндл>"
  handle_yt: "<твой-хэндл>"  # placeholder, проверить актуальное
  handle_ig: "<твой-хэндл>"
  handle_tt: "<твой-хэндл>"
  category: "вайбмаркетинг"          # категория-метод автора
  niche: "вайбкодинг + вайбмаркетинг для начинающих экспертов"
  language_primary: "ru"
  language_secondary: "en"
```

## Paths (где живут источники smыcлов и интейк)

```yaml
paths:
  # Бизнес-контекст
  business_index: "~/.business/INDEX.md"
  avatar: "~/.business/audience/avatar.md"
  objections: "~/.business/audience/objections.md"
  journey: "~/.business/audience/journey.md"
  jtbd: "~/.business/audience/avatar.md"  # JTBD сейчас в avatar.md
  
  # Карты смыслов (Mode A source of truth)
  # ВАЖНО: sense-map-автор.md DEPRECATED по решению автора (контейнер выдуманных фактов).
  # Brand-level source = Распаковка бренда.md. Карта смыслов конкретного запуска = из запуски/.
  sense_map_brand: "~/.business/Распаковка бренда.md"
  sense_map_launches_dir: "~/.business/запуски/"
  # Fallback если нет активного запуска и Brand-level не покрывает тему - переключение на Mode B2
  
  # Brand Voice references
  brand_dna: "~/.business/Распаковка бренда.md"
  voice_corpus: "~/.business/voice-corpus/"
  story_bank: "~/.business/story-bank/"
  
  # Контент-завод
  ingest_dir: "~/.business/growth/ingest/"
  produced_dir: "~/.business/growth/produced/"
  competitors_scan_dir: "~/.business/growth/competitors-scan/"
  
  # Output
  script_archive_dir: "~/.business/growth/scripts/"
  
  # Reflection
  history_dir: "~/.business/история/"
  
  # Memory
  memory_dir: "~/.claude/projects/<твой-проект>/memory/"
```

## Voice lexicon (CRITICAL - hard regex rules)

```yaml
lexicon_force:
  # Auto-correct (case-insensitive)
  "Instagram": "Нельзяграм"
  "Инстаграм": "Нельзяграм"
  "instagram": "Нельзяграм"
  "контент-фабрика": "контент-завод"
  "контент-машина": "контент-завод"
  "content factory": "контент-завод"
  "вайб-кодинг": "вайбкодинг"
  "vibe coding": "вайбкодинг"
  "вайб-маркетинг": "вайбмаркетинг"
  "vibe marketing": "вайбмаркетинг"
  "Дубай": "Дубайск"        # в контексте лексики автора
  
lexicon_banned:
  # Hard fail на review
  - "артефакт"
  - "контур"
  - "фасилитация"
  - "digital twin"
  - "digital-twin"
  - "Grand Slam Offer"
  - "Grand Slam"
  - "КЭВ"
  - "связки"
  - "связочка"
  - "fast-action"
  - "без опыта в коде"
  - "не программист"
  - "программирование"
  - "программисты"

lexicon_native:
  # Слова, которые автор реально использует - поощряются
  - "Нельзяграм"
  - "Дубайск"
  - "контент-завод"
  - "вайбкодинг"
  - "вайбмаркетинг"
  - "ферма"
  - "перегнать"
  - "перегон"
  - "пдп"
  - "залетает"
  - "пилишь"
  - "гоняешь"
  - "соберёшь"
  - "вкатишься"
```

## Voice rules (CRITICAL)

```yaml
voice_rules:
  # Audience
  audience_descriptor: "ты / тех у кого / один человек"
  audience_descriptor_banned: ["эксперт"]   # сужает воронку
  
  # Объекция аудитории
  primary_objection: "не маркетолог"
  banned_objections: ["без опыта в коде", "не программист"]
  
  # Враг
  enemy_type: "явление"   # не имя
  enemy_examples: ["конструкторы", "продюсерская модель", "курсомания"]
  enemy_banned: ["GetCourse", "<конкурент>", "Skillbox"]   # имена конкретные = fail
  
  # Claude позиционирование
  claude_phrasing: "Claude в ядре, закрывает 90%"
  claude_banned: ["только Claude", "чисто Claude"]
  
  # Em-dash правило
  em_dash_inside_lines: false   # запрет
  em_dash_at_bullet_start: true  # разрешено
  
  # Негативные статистики
  negative_stats_in_public: false
  
  # Tone
  rhythm: "1/3/1"   # короткая → переменная → короткая
  sentence_length_target: "4-8 слов"
  address: "ты"   # не «вы»
  verb_preference: "глагольный"   # действия, не свойства
  concreteness: "числа конкретные, не круглые-плакатные"
  
  # Архетипы (Marc & Pearson 12)
  archetypes_allowed: ["Magician", "Sage", "Outlaw"]
  archetypes_banned: ["Caregiver", "Lover", "Innocent"]
  archetype_rotation_window: 3   # не повторять последние 3 видео
```

## Length tier defaults

```yaml
length_tiers:
  short-15-30s:
    floor_sec: 15
    ceiling_sec: 30
    target_sec: 25
    words_target_ru: 60       # ~2.5 слова/сек темп автора
    words_target_en: 65       # темп EN ~2.7 слова/сек
    platforms: ["reels", "shorts", "tiktok"]
    
  short-30-60s:
    floor_sec: 30
    ceiling_sec: 60
    target_sec: 45
    words_target_ru: 110
    words_target_en: 120
    platforms: ["reels", "shorts", "tiktok"]
    
  short-60-180s:
    floor_sec: 60
    ceiling_sec: 180
    target_sec: 90
    words_target_ru: 225
    words_target_en: 245
    platforms: ["reels", "shorts", "tiktok"]
    
  mid-3-10min:
    floor_sec: 180
    ceiling_sec: 600
    target_sec: 360
    words_target_ru: 900
    words_target_en: 970
    platforms: ["youtube"]
    
  long-10-60min:
    floor_sec: 600
    ceiling_sec: 3600
    target_sec: 1500
    words_target_ru: 3750
    words_target_en: 4050
    platforms: ["youtube"]
    experimental: true
```

## Hook Strength Gate

```yaml
hook_strength:
  first_n_sec: 3
  max_retries: 3
  tests:
    - "В первые 3 sec присутствует conflict / contradiction / visual contrast / numeric outlier"
    - "Value proposition понятна зрителю без предыдущего контекста"
    - "Первые 3 sec заканчиваются на cliff / question / promise (не на резюме)"
  on_fail: "переписать hook, max 3 ретрая, потом эскалация to user"
```

## 6-Pass Refinement perspectives (video-адаптировано)

```yaml
six_pass:
  - skeptic        # «зачем мне это смотреть»
  - scroller       # «остановит ли scroll в 1.5 sec»
  - producer       # «реально ли это снять / реализуемо ли»
  - editor         # «темп / pacing / повторы»
  - algorithm      # «watch time / completion rate / saves / shares»
  - voice          # «звучит ли как автор»
```

## Maxwell Ross 9-checklist (video-адаптировано)

```yaml
maxwell_ross_9:
  - idea           # есть ли центральная идея в одно предложение
  - clarity        # понятно ли с первого просмотра
  - payoff         # есть ли выплата зрителю
  - specificity    # конкретика (числа / имена / артефакты)
  - freshness      # не повторяет ли предыдущие видео
  - hook_strength  # первые 1.5-3 sec стопят scroll
  - length_fit     # длительность попадает в target tier
  - tone           # voice автора не выдуман
  - cta            # CTA в финале или explicit отсутствие
```

## Mandatory Reads (для Pass 0 в 04-write.md)

Pass 0 теперь читает **shared empirical layer** в `~/.business/growth/extracted-patterns/` + audience layer + voice. Это критический фикс root cause v1.0 (где skill читал только теорию).

```yaml
mandatory_reads:
  # SHARED EMPIRICAL LAYER (extracted from 30 viral corpus, 2026-05-28)
  - path: "~/.business/growth/extracted-patterns/hook-patterns-empirical.md"
    purpose: "9 hook patterns с verbatim examples из top viral шортов"
    required: true
  - path: "~/.business/growth/extracted-patterns/body-structure-empirical.md"
    purpose: "Walkthrough patterns (Greg/Riley/Sabrina styles)"
    required: true
  - path: "~/.business/growth/extracted-patterns/cta-patterns-empirical.md"
    purpose: "5 CTA types с funnel mechanics"
    required: true
  - path: "~/.business/growth/extracted-patterns/voice-markers-empirical.md"
    purpose: "Verbatim phrases per creator + авторский voice calibration"
    required: true
  - path: "~/.business/growth/extracted-patterns/funnel-awareness.md"
    purpose: "Funnel destination requirements + lead magnet checklist"
    required: true
  - path: "~/.business/growth/extracted-patterns/audience-glossary.md"
    purpose: "Agent-jargon → язык авторской ЦА translation"
    required: true
  - path: "~/.business/growth/extracted-patterns/visual-formats-empirical.md"
    purpose: "Visual format archetypes + visual brief requirements"
    required: true
  
  # AUDIENCE / OBJECTIONS / JOURNEY (был критический gap в v1.0)
  - path: "~/.business/audience/avatar.md"
    purpose: "ICP - кто зритель, что у него есть/нет"
    required: true
  - path: "~/.business/audience/objections.md"
    purpose: "Реальные возражения (не «без опыта в коде»)"
    required: true
  - path: "~/.business/audience/journey.md"
    purpose: "Куда зритель идёт после шорта"
    required: true
  
  # CONTENT PILLARS (для topic validation)
  - path: "~/.business/marketing/content.md"
    purpose: "Pillars - для проверки что тема in-scope"
    required: true
  
  # IVAN VOICE (specific to author - не пересекается с empirical voice markers)
  - path: "$HOME/.claude/skills/video/references/_voice-TEMPLATE.md"
    purpose: "авторский lexicon + anti-patterns"
    required: true
  - path: "$HOME/.claude/skills/video/references/_voice-TEMPLATE.md"
    purpose: "Живые глаголы / banned AI-конструкции"
    required: true
  - path: "$HOME/.claude/skills/video/config.md"
    purpose: "This file"
    required: true

  # OPTIONAL but recommended (для replication mode)
  - path: "~/.business/growth/extracted-patterns/benchmark-corpus-index.md"
    purpose: "Index 30 viral шортов для Benchmark Gate"
    required: false
  - path: "~/.business/growth/extracted-patterns/authority-namedrop-pattern.md"
    purpose: "Authority proof requirements для Pattern 3 (inevitability)"
    required: false
```

## Production handoff defaults

```yaml
production_defaults:
  caption_style: "Hormozi-style word-by-word bold yellow/white outlined"
  aspect_vertical: "9:16"
  aspect_horizontal: "16:9"   # для YouTube long
  
  # Hook visual
  hook_visual_required: true
  hook_visual_first_sec: 1.5
  
  # Brand watermark
  watermark_text: "<твой-хэндл>"
  caption_color_replicate: "#FFFFFF"      # VariableComposition
  caption_color_offer: "#FFEB3B"          # TutorialOfferSplitScreen
  caption_stroke_color: "#000000"
```

## Track-record path

```yaml
track_record_path: "$HOME/.claude/skills/video/examples/track-record-video.md"
```

## Roadmap markers

```yaml
roadmap:
  v1_1_features:
    - "student_onboarding"
    - "replicate_reel_mode_c_refactor"
    - "en_voice_goldstandard_pass"
  v1_2_features:
    - "long_form_corrections_from_real_data"
  v2_0_features:
    - "ua_es_languages"
```