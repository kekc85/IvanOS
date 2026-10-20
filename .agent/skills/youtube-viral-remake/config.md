---
name: youtube-viral-remake-config
description: Конфиг скилла youtube-viral-remake. Указывает пути к контексту проекта (голос автора, аватар, банк смыслов эталонных YouTube), язык, тему, роль ролика по умолчанию (acquisition / launch-lead-magnet). автор клонирует ученикам - каждый ученик меняет пути и subject под свой проект через onboarding (фаза 00).
metadata:
  version: "1.0"
  last_reviewed: 2026-07-18
---

# youtube-viral-remake config

> Это **точка адаптации скилла под конкретного автора**. Код скилла одинаков у автора и учеников,
> различие - только этот файл и данные, на которые он указывает. Бизнес-специфику (оффер,
> код-слова, смыслы запуска) сюда НЕ вшивать - она заходит как ВХОД (config + бриф), не как логика

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  language: ru                      # ru | en | both
  market: ru                        # ru | en | both (EN - основной с июня 2026, RU дублирует)
  niche: "вайбкодинг + вайбмаркетинг для соло-экспертов"
  topic_focus: "Claude Code, нейросети, как эксперту собрать первый цифровой продукт"
  format_definition: "длинный YouTube-ролик 10-60 мин, 16:9, faceless-first (голова на хук+CTA)"
  youtube_role_in_funnel: "top-of-funnel acquisition + источник AI-цитирования (GEO)"
```

**Для ученика:** заменить `name`, `niche`, `topic_focus` на свои. `youtube_role_in_funnel` не трогать,
если YouTube у тебя тоже верх воронки

---

## Role (какую роль собираем по умолчанию - переспрашивается в фазе 00)

```yaml
role:
  default: acquisition              # acquisition | launch-lead-magnet
  # acquisition:       органический YouTube, CTA = лид-магнит + код-слово в комменты,
  #                    доставка = публичный YouTube ТОЛЬКО по команде автора
  # launch-lead-magnet: закрытый разбор за регистрацию на марафон, единственное действие =
  #                    РЕГИСТРАЦИЯ (без код-слова/домашки), доставка = ТОЛЬКО localhost + бот,
  #                    НИКОГДА публичный домен
```

**Для ученика:** если делаешь только органику - оставь `acquisition`. Роль всегда переспрашивается
в фазе 00, дефолт лишь подсказка

---

## Paths (где лежит контекст проекта)

Пути относительно корня проекта (`~/IvanOS` у автора).

```yaml
paths:
  # Голос автора (канон для скрипта - делегируется в video, но outcome-гейт читает отсюда)
  voice_profile: ".business/voice-corpus/_voice-profile.md"

  # Аудитория (outcome-язык-гейт: барьер ЦА = «я не маркетолог», НЕ «я не программист»)
  avatar: ".business/audience/avatar.md"
  audience_dir: ".business/audience/"

  # Банк смыслов эталонных YouTube-роликов (720 смыслов из 6 эталонов, справочник хуков/тезисов)
  youtube_sense_bank: ".business/запуски/<твоя-папка-запуска>/прогрев-уроки/чек-лист-смыслов-youtube.md"

  # Рабочая папка ingest (сюда фаза 02 кладёт card.md - контракт Skill('video') replicate)
  ingest_dir: ".business/growth/ingest/"

  # Рабочая папка выдачи production-пакета и черновика
  workdir: "~/Desktop/yt-remake/"
```

**Для ученика:** заменить пути под свой проект. `youtube_sense_bank` можно оставить пустым, если у
тебя нет своего банка эталонов - тогда фаза 02 строит структуру напрямую из источника без справочника

---

## Voice (голос - финальная сверка, основной стек несёт video)

```yaml
voice:
  hard_rules:                       # HARD, страхует humaniser + outcome-гейт
    - "нет длинных тире «—», только дефис «-»"
    - "нет точки в конце абзаца"
    - "в outcome для ЦА запрещено: программирование / MVP / SaaS / приложение / разработчик"
    - "outcome = «мини-продукт эксперта» / «цифровой продукт эксперта»"
  cta_by_role:
    acquisition: "лид-магнит + код-слово в комменты (одним заходом)"
    launch-lead-magnet: "единственное действие = регистрация (без код-слова)"
```

**Для ученика:** `hard_rules` про тире/точку универсальны для голоса автора. Запрет «программирование/
MVP» - специфика ЦА автора (новички-эксперты, барьер «я не маркетолог»); под свою ЦА скорректировать

---

## Mastery (совет директоров для скрипта/деконструкции)

```yaml
mastery:
  virality_attention: ["mrbeast", "derek-thompson", "jonah-peretti"]   # удержание YouTube
  storytelling: ["mckee", "blake-snyder"]                              # арка нарратива
  public_speaking: ["chris-anderson", "carmine-gallo"]                 # структура выступления
  protocol: "mastery/PROTOCOL.md"
```

**Для ученика:** оставить как есть - это методы удержания, универсальны для long-form YouTube

---

## Output

```yaml
output:
  package_dir: "~/Desktop/yt-remake/{date}-{slug}/"     # production-пакет + storyboard + черновик
  deliver_in_chat: true                                  # ссылка оригинала + путь пакета + черновик
  never_auto_publish: true                               # ничего в прод/на домен без явной команды
```