---
name: bot-message
description: TG-бот broadcast push (100-300 знаков + 1-3 inline-кнопки, цель = клик). Portable через config.md. 3 режима (Plan из карты воронки / Spark / Transcript) × 8 типов (voronka-push / reminder / content-tease / drip-segment / event-trigger / re-engagement / broadcast-news / survey-poll). Output = текст + JSON кнопок + A/B. Triggers /bot-message, /push, "пуш в воронке", "напоминание о вебинаре", "drip Day N", "send a push", "winback subscribers".
metadata:
  version: "1.0.2"
  created: "2026-05-28"
  last_reviewed: "2026-05-28"
  artifact_type: "action"  # action / stylistic / mixed - см. skill-craft/knowledge/bug-categories.md
---

# bot-message - Контент-машина TG-бот сообщений

> Skill производит готовые broadcast сообщения для TG-бота в голосе автора: короткие push (100-300 знаков) + inline-кнопки (1-3 опции CTA). Базируется на архитектуре `post` (3 режима × portable subject), адаптированной под notification-stream UX и bot-broadcast спецификацию Telegram Bot API.

## Архитектура

Skill portable: один и тот же код работает у автора и у учеников курса вайбмаркетинга. Различие - только `config.md` и данные проекта, на которые он указывает.

**Два ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (карта воронки) / Spark-B1 (идея пользователя) / Spark-B2 (генерация под триггер) / Transcript (надиктовка) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |

**Router** в `workflow/01-router.md` auto-detect'ит mode по сигналам в input. Override через флаги `--plan` / `--spark` / `--transcript`.

**Onboarding** для нового пользователя - `workflow/00-onboarding-student.md`. Срабатывает при отсутствии или неполном `config.md`. После onboarding ученик имеет заполненный config + указанный бот и может запускать `/push`.

## Когда применять

Триггеры (auto-detect mode в router):

| User input | Mode | Что делает |
|---|---|---|
| `/push` без аргументов | Plan | Берёт следующий шаг из карты воронки |
| «по плану», «следующий шаг воронки», «drip Day 3» | Plan | То же |
| `/push про X` / «напиши сообщение про X» | Spark-B1 | Расширяет тему в 3-5 углов с разными кнопочными стратегиями |
| «напоминание о вебинаре», «winback холодных» | Spark-B2 | Генерит 3-5 кандидатов под триггер, ты выбираешь |
| Длинный текст (>500 знаков) «это в бот» | Transcript | Дистиллирует надиктовку в 3-5 push-кандидатов |

**Не применять** для:
- Постов в TG-канал (≥280 знаков, чтение в ленте) → `post`
- Email рассылок (subject + body + HTML CTA) → планируется `email-broadcast` v1
- Постов в Нельзяграм / X / LinkedIn → `paips-post` / `spiky-one-liner` / `long-form-essay`
- Длинных bot conversations (multi-step dialog, FSM) → это бизнес-логика бота, не broadcast

**MECE-граница с post:** bot-message = push в notification stream (≤300 знаков, кнопка-клик). post = пост в публичный канал (280-2500 знаков, чтение в ленте, может включать ссылку в тексте). Если сомневаешься - длина решает: ≤300 → bot-message, >300 → post.

## Workflow (progressive disclosure)

При вызове skill последовательно грузит соответствующие `workflow/` файлы:

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

01-router.md                  ← detect mode + load config
   ├─ 01a-plan.md             ← Mode A: из карты воронки
   ├─ 01b-spark.md            ← Mode B1/B2: ситуативный
   └─ 01c-transcript.md       ← Mode C: из надиктовки
       ↓
02-structure.md               ← detect-type (один из 8) + scaffold + button strategy
03-write.md                   ← pass 0 mandatory reads + draft + voice + button microcopy
04-review.md                  ← 3 слоя + bot-specific gates (length / buttons / notification preview)
05-publish.md                 ← output (текст + JSON кнопок + A/B + внутрянка)
```

**Файлы:**

| Файл | Назначение |
|---|---|
| `workflow/00-onboarding-student.md` | First run для ученика. Создаёт config.md через 7 вопросов |
| `workflow/01-router.md` | Auto-detect mode (Plan / Spark / Transcript) и subject |
| `workflow/01a-plan.md` | Mode A: читает карту воронки и определяет следующий шаг |
| `workflow/01b-spark.md` | Mode B1: расширение идеи / Mode B2: генерация под триггер |
| `workflow/01c-transcript.md` | Mode C: разбор надиктовки в push-кандидаты |
| `workflow/02-structure.md` | Detect-type (один из 8) + scaffold + button strategy |
| `workflow/03-write.md` | Pass 0 mandatory reads + draft + voice injection + button microcopy |
| `workflow/04-review.md` | 3 слоя + bot-specific gates |
| `workflow/05-publish.md` | Output: текст + JSON inline-keyboard + A/B + внутрянка |

## 8 типов сообщений (templates)

| # | Тип | Длина | Кнопок | Template | Применение |
|---|---|---|---|---|---|
| 1 | voronka-push | 100-200 | 1-2 | `templates/voronka-push.md` | Daily, вовлечение в следующий шаг |
| 2 | reminder | 100-200 | 1 | `templates/reminder.md` | Окно запуска, напоминание о действии |
| 3 | content-tease | 150-250 | 1 | `templates/content-tease.md` | 2-3/нед, анонс нового материала |
| 4 | drip-segment | 150-300 | 1-2 | без отдельного шаблона | Прогрев, шаг N серии |
| 5 | event-trigger | 100-200 | 1-2 | без отдельного шаблона | Реакция на действие (купил → onboarding) |
| 6 | re-engagement | 150-250 | 2 | без отдельного шаблона | Winback холодных раз в квартал |
| 7 | broadcast-news | 150-300 | 1-2 | без отдельного шаблона | Анонс события всем |
| 8 | survey-poll | 100-200 | 2-3 | без отдельного шаблона | Мини-опрос с вариантами-кнопками |

**v1.0 (текущий релиз):** типы 1, 2, 3 - закрывают ~70-80% повседневной воронки.
**v1.1:** типы 4, 5 (drip-segment + event-trigger) - добавятся при первом активном drip.
**v1.2:** типы 6, 7, 8 - добавятся при первом winback / запуске продукта / опросе аудитории.

## Knowledge base (references/)

Все references грузятся по нужде через progressive disclosure:

- `references/bot-message-anatomy.md` - notification-stream UX: правило 50/95/300 знаков (preview iOS / Android / cap), hook discipline в первые 50, no walls of text
- `references/inline-buttons-microcopy.md` - CTA-глаголы RU+EN, длина текста кнопки (8-20 знаков), button strategy (URL / callback / web_app / pay), запретные generic-CTA
- `references/bot-anti-patterns.md` - стены текста / >3 кнопок / generic CTA / multi-emoji / multi-! / лишние переносы / DM-only ценообразование
- `references/_voice-TEMPLATE.md` - bot-адаптация голоса автора (cross-ref на `post/references/_voice-TEMPLATE.md` + bot-специфика: brevity, имperative mood, direct address «ты»)

## Examples

- `examples/_TEMPLATE.md` - bootstrap с TODO: положить 5-10 эталонных push из последних запусков автора (после v1.0 init)
- `examples/track-record-bot-message.md` - история применений + catch_rate metric (≥80% target)

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/04-review.md`):**
- Длина текста >300 знаков → fail
- Длина текста <80 знаков → warning (слишком тонко, возможна потеря смысла)
- Em-dash «-» внутри строк → fail
- «Instagram» → auto-correct в «Нельзяграм»
- >3 inline-кнопок → fail
- Длина текста кнопки >24 знака → warning (truncation на mobile)
- Generic CTA («Узнать», «Подробнее», «Click here», «Сюда» без контекста) → fail
- Запретные термины («artifact» / «digital-twin» / «КЭВ» / «связки») → fail
- >1 восклицательного знака → fail (notification noise)
- >1 эмоджи в первых 50 знаках → warning (visual clutter в preview)
- Списков/буллетов >0 → fail (не место в push)

**Notification preview test:**
Первые 50 знаков (iOS preview cap) читаются без контекста и понятны? Если нет - переписать hook.

**3 слоя финальный gate:**
- Слой 1 валидаторы (regex выше + ban-list)
- Слой 2 4 концепции (Pre-mortem / 90% calibration / Multi-perspective / Adaptive)
- Слой 3 7 контуров (Context / Соответствие предпосылкам / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность)

## 🔴 Цепочка касаний = бенчмарк прошлого дня (правило проекта)

**Push / пуш / сообщение в цепочке касаний - это ПОЛНОЦЕННОЕ сообщение по бенчмарку предыдущего дня, а не огрызок.** Перед сборкой дня N - ОБЯЗАТЕЛЬНО прочитать цепочку дня N-1 (предыдущий push той же серии / drip / прогрева) как эталон и держать ТОТ ЖЕ объём смысла и качество проработки. ЗАПРЕЩЕНЫ короткие огрызки / спам в разы меньше бенчмарка («одна строчка вместо вчерашних трёх абзацев смысла»). Если день N-1 нёс хук + развитие + конкретику + CTA - день N несёт столько же, не схлопывается в пустышку. Перед draft: найти вчерашнее сообщение серии → зафиксировать его объём/структуру как floor → собирать не ниже. Прецедент: цепочка-продолжение ушла огрызками в разы меньше предыдущего дня = брак.

## 🔴 Публикуемый текст - ТОЛЬКО через конвейер скилла (правило проекта)

**Любой текст, который автор скопирует/отправит/опубликует, собирается ТОЛЬКО через профильный конвейер этого скилла (router → structure → write → review → publish + humaniser), НИКОГДА руками мимо него.** Написать push «в обход» в чате = пропуск Pass 0 mandatory reads, voice injection, bot-specific gates и 3 слоёв = брак по определению. Нет исключений «тут же одна строчка». Прецедент есть.

## Принципы

1. **Portable by config.** Один и тот же скилл работает у автора и у ученика. Различие - только `config.md` и данные проекта. Никаких hardcoded paths.
2. **Notification stream first.** Хук = первые 50 знаков. Если в этих 50 знаках смысл не считывается - push мёртв.
3. **Один push = одно действие.** Multi-CTA push (две разные цели) разбивается на две отдельные единицы.
4. **1-3 кнопки максимум.** ≥4 кнопок = выбор парализован, конверсия падает. Лучше 1 чёткая, чем 3 размытые.
5. **CTA в кнопке, не в тексте.** Текст подводит. Кнопка делает. Дублировать «жми кнопку» - антипаттерн.
6. **No metaphor abuse.** Push в потоке уведомлений требует буквальности. Метафора в коротком формате читается как невнятица.
7. **No-repeat в Spark-B2.** Перед генерацией читаются последние 10 push'ей бота. Повторы темы/кнопочной стратегии фильтруются.
8. **Карта воронки = source of truth для Mode A.** Не дополнять, не выдумывать. Пустая запись = fallback на Spark-B2 с warning.
9. **Транскрипт в Mode C - цитата, не парафраз.** Лексика автора важнее причёсанности.
10. **Bot-specific gates - финальный gate.** Никакой push не выходит без прохождения длина + кнопки + preview test + 3 слоя.
11. **Внутрянка после push.** Каждый output включает блок «Как писал»: Mode / type / hook framework / button strategy / что отброшено / A/B логика.
12. **Каждая правка = системная.** Любая обратная связь от автора закрывается на двух уровнях: точечный fix + системная правка в скилле. См. `post` принцип 13.

## Output формат

Финальный output в чат (без файлов, для копи):

```
ТЕКСТ:
<100-300 знаков, готово к копи в bot admin>

КНОПКИ (JSON, Telegram Bot API InlineKeyboardMarkup):
[
  [{"text": "<8-24 знака>", "callback_data": "<slug>"}]
]
или
[
  [{"text": "<...>", "url": "https://..."}]
]

A/B ВАРИАНТ:
<альтернатива с другой кнопочной стратегией или другим hook'ом>

ВНУТРЯНКА:
Mode: <Plan/Spark-B1/Spark-B2/Transcript>
Type: <один из 8>
Hook framework: <Numbered/Contrarian/Vulnerable/Results-First/etc.>
Button strategy: <URL/callback/web_app/pay>
Что отброшено: <угол A не выбран потому что Y>
A/B логика: <тестируем X против Y>
```

JSON формат - универсальный Telegram Bot API. Переходит в любой движок (aiogram / Pyrogram / Senler / самописный).

## Portability - для ученика курса

Ученик клонирует папку `~/.claude/skills/bot-message/` в свою машину и заменяет ТОЛЬКО:

1. **`config.md`** - пути и параметры под свой проект (онбординг это делает за него при первом запуске).
2. **`examples/gold-standard-bot-<your-name>.md`** - свои лучшие push (5-10 штук).
3. **`intake/`** (или `.business/`) - `avatar.md`, `funnel-map.md`, `brand-dna.md`. По путям из config.

Что НЕ трогаем:
- `workflow/*` - общая методология
- `references/*` - references (анатомия / кнопки / anti-patterns) одинаковы для всех
- `templates/*` - шаблоны 8 типов

Это делает скилл **product курса**: ученики получают тот же инструмент, который автор применяет в своих воронках ежедневно.

## Anti-patterns (краткий список)

Полный - `references/bot-anti-patterns.md`. Ключевые:

- Стена текста без хука (>200 знаков без перехода - глаз соскальзывает)
- Generic CTA («Узнать», «Подробнее» без объекта)
- ≥4 кнопок (выбор парализует)
- Эмоджи в каждом предложении (clutter)
- >1 восклицательного знака (noise)
- Метафоры в push («сжигает мозг», «выстрелит» - невнятица в кратком формате)
- «Жми кнопку» в тексте (кнопка сама - affordance)
- Списки и буллеты (не формат push)
- DM-only ценообразование («цена в личке»)
- Травел-флекс / статус-флекс
- Em-dash «-» внутри строк
- «Instagram» вместо «Нельзяграм»

## Memory cross-refs

- `[[feedback-no-em-dash]]` - em-dash запрещён внутри строк
- `[[feedback-no-tech-jargon-no-anglicisms]]` - без жаргона / англицизмов
- `[[feedback-no-negative-stats-in-public-offer]]` - без негативных статистик
- `[[feedback-product-positioning-no-programmer]]` - не «программист», а «эксперт»
- `[[feedback-no-code-objection-ever]]` - никогда «без опыта в коде»
- `[[feedback-prompts-propose-not-ask]]` - bot push предлагает, не запрашивает
- `[[post]]` - параллельный skill для длинных постов в канал (MECE граница по длине ≤300 vs >300)
- `post` - параллельный skill для X/Threads/LinkedIn (другая платформа)
- `longform` - параллельный skill для X/Newsletter/LinkedIn Article (другая длина)
- `[[skill-craft]]` - методология build применена при создании

## Версия

**Текущая:** 1.0.2 (2026-05-28) - Action-skill class fix. Root cause из E2E test: skill применял ментальную модель stylistic skill (как post), но bot-message по природе - action skill (push зовёт к non-reversible действию). Добавлены 5 mandatory gates: Pass 0.5 PII enforcement, Pass 0.6 Event existence check, Pass 0.7 Fact verification, 4.0.4 Generic CTA verb+object pair, Pass 4.4 Self-Review Cross-Check. Закрывает класс ошибок «AI fact invention» который v1.0.1 audit пропустил.

**Предыдущая:** 1.0.1 (2026-05-28) - Audit closure. Em-dash sweep (382→0). Description trim (704→<500). Rate limit pre-flight в `05-publish.md`. Callback 15s timing в `inline-buttons-microcopy.md`. Pass 0.5 sanitize transcript в `01c-transcript.md`. PII redaction в `config.md`. Frontmatter migration в `metadata:` (VS Code compat).

**Changelog:**
- v1.0.2 (2026-05-28): Action-skill class fix. 5 mandatory gates (PII enforcement / Event existence / Fact verification / Verb+object CTA / Self-Review Cross-Check). Config: `paths.business_index`, `bot.upcoming_events`, `artifact_type: action`. Root cause: E2E test catch_rate halftura 100% при real 33% - skill пропускал fact invention класс ошибок.
- v1.0.1 (2026-05-28): Closure post-audit findings из `examples/audit-bot-message-2026-05-28.md`. Critical+Important+Minor pursued. Em-dash также swept across content-factory (post / longform / email / carousel / single-image / video, 5215→0).
- v1.0 (2026-05-28): Initial release. 3 templates (voronka-push / reminder / content-tease) + 9 workflow stages + 4 references + portable config. Закрывает 70-80% повседневной воронки.

**SemVer правила:**
- MAJOR: breaking change в выходном формате (текст+JSON+A/B) или критериях fail
- MINOR: новый template (типы 4-8) / новый mode / новый reference
- PATCH: уточнение правил валидации, новые anti-patterns, fix references

**Когда пересматривать:**
- catch_rate в track-record падает <80%
- 3+ систематических промаха по типу или voice
- Появление нового bot engine (если потребуется адаптация JSON формата)
- **Telegram Bot API changelog** - quarterly review на https://core.telegram.org/bots/api (новые типы кнопок / изменения лимитов / web_app spec)
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации скилла под автора (см. внутри файла)
- `~/.claude/skills/post/` - родственный skill (тот же ментальный паттерн)
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
- `.business/audience/avatar.md` - целевая аудитория для voice/topic
- `.business/processes/launch-methodology.md` - Фаза 6.1 (карта воронки)

## Empirical patterns layer (NEW 2026-05-28)

Этот skill интегрирован с shared empirical layer для всех content-skills.

**Mandatory Reads в Pass 0:**
- `~/.business/growth/extracted-patterns/INTEGRATION.md` - что читать для этого скилла
- `~/.business/growth/extracted-patterns/hook-patterns-empirical.md` - 9 patterns из 30 corpus
- `~/.business/growth/extracted-patterns/voice-markers-empirical.md` - Greg/Riley/Sabrina + авторская calibration
- `~/.business/growth/extracted-patterns/audience-glossary.md` - agent-jargon → язык RU ЦА
- `~/.business/growth/extracted-patterns/funnel-awareness.md` - куда ведёт content

**Benchmark Gate** в review stage:
- Compare output vs nearest 3 examples из `benchmark-corpus-index.md`
- Score /6 для text-only OR /7 для visual
- Cutoff: 4+/6 (text) | 5+/7 (visual) = PASS

Root cause fix: до 2026-05-28 references зашивали теорию виральности из памяти. Shared layer = empirical extraction из 30 real viral шортов в авторской нише.
