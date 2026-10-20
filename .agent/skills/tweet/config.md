---
name: tweet-config
version: "1.0"
last_reviewed: 2026-05-28
description: Конфиг скилла tweet. Указывает пути к контексту проекта (аватар / JTBD / Brand DNA / Карта смыслов / последние X posts) и parameters X+Threads handles + language default. автор клонирует ученикам - каждый ученик меняет под свой проект.
---

# tweet config

> Это точка адаптации скилла под конкретного автора. Скилл (`tweet`) одинаков у автора и у учеников. Различие - только в этом файле и в данных, на которые он указывает.

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  language_default: ru   # ru | en
  market: ru             # ru | en | both
  # X presence
  x_handle: null          # <твой-хэндл>_x (TBD при активации X для EN запуска июнь 2026)
  x_url: null
  threads_handle: null
  threads_url: null
  # Категория и фокус
  category_term_ru: "вайбмаркетинг + вайбкодинг"
  category_term_en: "vibe marketing + vibe coding"
  product_focus_ru: "<твоя ниша / продукт>"
  product_focus_en: "<твоя ниша / продукт>"
```

**Для ученика:** заменить `name`, `x_handle`, `threads_handle` на свои. Если X handle ещё не запущен - `x_handle: null`, скилл будет работать без чтения предыдущих постов (без archetype rotation).

## Paths (где лежит контекст проекта)

Все пути относительно корня проекта (например, `~` у автора).

```yaml
paths:
  # Аудитория
  avatar: ".business/audience/avatar.md"
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"

  # Продукт
  products_dir: ".business/products/"
  pricing: ".business/products/pricing.md"

  # Brand DNA / голос / Карта смыслов
  brand_dna: ".business/Распаковка бренда.md"
  brand_sense_map: ".business/sense-map-автор.md"

  # Запуск (active launch - для Карты смыслов Mode A)
  active_launch: "<твоя-папка-запуска>"
  launch_sense_map: ".business/запуски/<твоя-папка-запуска>/5.2-Карта-смыслов.md"

  # Voice samples
  voice_corpus: ".business/voice-corpus/"
  story_bank: ".business/story-bank/"

  # Последние X posts (для archetype rotation, опционально)
  x_recent_posts: null   # null если X handle новый, иначе путь к export csv/json
```

## Voice parameters

```yaml
voice:
  primary_register: "build-in-public"   # cluster из synthesis-light.md
  secondary_register: "paips-story"
  tertiary_register: "idea-drop"
  banned_registers:
    - "gender-war"          # Iman register B
    - "political"           # Sanchez subset
    - "extreme-lowercase"   # Yacine nvim-tribalism
    - "self-quoting"        # Hormozi "As I always say"
    - "borrowed-mantras"    # Butcher "Move fast and break stuff"
  archetype_rotation_window: 3  # не повторять archetype последние N постов
```

## Hook char zone rule (HARD)

```yaml
hook_zone:
  zone_a_min: 40
  zone_a_max: 100
  zone_b_min: 200
  zone_b_max: 280
  dead_zone_min: 100
  dead_zone_max: 200   # fail если hook в этом range
```

## Thread length rule (HARD)

```yaml
thread_length:
  compact_min: 8
  compact_max: 15
  mega_min: 18
  mega_max: 34
  awkward_min: 3
  awkward_max: 7   # fail если thread в этом range
```

## Frequency cadence (recommendation, не enforce)

```yaml
cadence:
  daily_single_tweets: "2-3"        # Welsh formula
  weekly_mini_thread: 1             # Welsh weekly thread
  monthly_mega_thread: 1            # Bloom Named-Principle
  quarterly_recycle: true           # refresh viral threads
```

## Platform target defaults

```yaml
platform:
  default_target: "both"   # x | threads | both
  cross_post_adapt: true   # X → Threads identical pattern (Cheung) с 280→500 expansion
  threads_max_chain: 10    # algorithm penalty при длинных Threads chains
```

## Запретные термины (HARD fail в 04-review.md)

```yaml
banned_terms:
  ru:
    # Jargon / англицизмы
    - "артефакт"
    - "digital-twin"
    - "цифровой двойник"
    - "fast-action"
    - "КЭВ"
    - "связки"
    - "Grand Slam Offer"
    - "архитектор ИИ-систем"
    # AI-tells Tier 1 — риторические фигуры (v1.1)
    - "Что важно сделать первым"
    - "Главное открытие"
    - "В этом и заключается"
    - "По сути"
    - "На самом деле всё проще"
    - "Здесь кроется"
    - "Вот в чём дело"
    - "Дело вот в чём"
    - "Реальность такова"
    - "Правда в том что"
    - "Стоит отметить что"
    - "Важно понимать что"
    - "Не случайно что"
    - "Ключевой момент"
    - "В современном мире"
    - "В сегодняшних реалиях"
    - "В наше время"
    - "В эпоху ИИ"
    # Tier 4 автор-specific banned (v1.1)
    - "выстрелил"
    - "закрывает боль"
    - "полная картина"
    - "комплексный подход"
    - "глубоко погрузиться"
    - "копнуть глубже"
    - "разложить по полочкам"
    - "разобрать по косточкам"
    - "построить экосистему"
    - "связать всё в систему"
    - "выстроить"
    - "сборки"
    # Grammar calque (v1.1)
    - "делать результат"
    - "делает результат"
    - "делают результат"
    - "иметь результат"
    - "делать смысл"
    - "делать прогресс"
    # СУЖЕНО по решению автора вслед за humaniser кат.13, замер: владелец пишет так
    # сам (VOICE-015, ivan-final-0). Бан ТОЛЬКО безадресного императива без
    # объекта («Создавай(те) ценность» как самостоятельный совет) - см.
    # references/ru-grammar-russification.md «create value». Живой оборот от
    # 1-го лица с объектом/фактом рядом бан не образует.
    - "создавай(те) ценность"
    - "забрать ценность"
    # Англицизмы в narrative (v1.1)
    - "shipped"
    - "real"
    - "perfect"
    # Bare-imperative staccato pairs/triples (v1.2)
    - "Сначала продукт"
    - "Потом контент"
    - "И всё."
    - "Точка."
    - "Без вариантов."
    - "Никак иначе."
    - "Делай. Тестируй. Запускай"
    - "Слушай. Делай. Запускай"
    - "Продукт. Не контент"
    - "Контент. Не продукт"
  en:
    - "delve"
    - "tapestry"
    - "in conclusion"
    - "moreover"
    - "furthermore"
    - "ensure"
    - "embark on a journey"
    - "navigate the landscape"
    - "in the realm of"
    - "harness the power"
  symbols:
    - "-"  # em-dash внутри строк (memory rule)
```

## Auto-corrections

```yaml
auto_correct:
  ru:
    - { from: "Instagram", to: "Нельзяграк" }
    - { from: "Инстаграм", to: "Нельзяграм" }
  en: {}   # no auto-corrections в EN
```

## Track record path

```yaml
track_record_file: "~/.claude/skills/tweet/examples/track-record-tweet.md"
```

## Notes для адаптации ученика

При первом запуске `00-onboarding-student.md` задаёт 9 вопросов:

1. Имя автора?
2. X handle (если есть)?
3. Threads handle (если есть)?
4. Language default (RU / EN / both)?
5. Market (RU / EN / both)?
6. Категория (1-2 термина)?
7. Product focus (одна строка)?
8. Primary voice register (build-in-public / paips-story / spiky / aphorism / idea-drop)?
9. Где лежат файлы проекта (.business / intake / custom path)?

После заполнения - `config.md` готов, скилл запускается.

## Memory cross-refs

- `[[feedback-no-em-dash]]`
- `[[feedback-no-tech-jargon-no-anglicisms]]`
- `[[project-info-marketing-math]]` - RU воронка контекст
- `[[project-author-business]]` - автора real numbers (<выручка> 2025 / <число учеников>)