# 00 - Onboarding student (first run)

> Срабатывает при отсутствии или неполном `config.md` (например, нет `bot.handle` или `paths.avatar`). Цель - собрать минимальный конфиг через 7 вопросов и записать в `config.md`. После - передать управление в `01-router.md`.

## Триггер

- `config.md` отсутствует
- ИЛИ `bot.handle == null`
- ИЛИ `paths.avatar` указан, но файл по этому пути не существует

## Output

Заполненный `config.md` + создан (или подтверждён существующим) файл `paths.avatar`. После - перейти в `01-router.md` без явного апрува (sane defaults применяются автоматически).

## 7 вопросов

Задаются последовательно. Если в IDE доступен AskUserQuestion с `<ide_opened_file>` контекстом - через него. Если нет (CLI) - plain text список (см. memory `feedback_no_askuserquestion_in_cli`).

### Q1: Имя автора

> Как тебя зовут (имя + фамилия, как в публичной части)?

→ `subject.name`

### Q2: Бот воронки

> Какой telegram bot handle, куда уйдут push? Формат `@your_bot`.

→ `bot.handle`

### Q3: Engine бота

> На чём собран бот?
> - aiogram / Pyrogram / самописный - выбрать `telegram_bot_api`
> - Senler - выбрать `senler`
> - GetCourse - выбрать `getcourse`
> - Другой - описать одной строкой

→ `bot.engine` + (если кастомный) пометка в README

### Q4: Сегменты подписчиков

> Какие сегменты настроены в боте? Перечисли через запятую. Если только «все» - пиши `all`.
> Примеры: `cold, warm, hot, buyer, no_buy`

→ `bot.segments`

### Q5: Язык бота

> На каком языке бот разговаривает с подписчиками?
> - ru
> - en
> - both (RU + EN - два бота)

→ `subject.language` + (если both) `bilingual.enabled: true`

### Q6: Карта воронки

> Есть ли карта воронки (документ со списком шагов: какой push когда уходит и куда ведёт)?
> - да, путь: `<your-path>.md`
> - нет, пока без неё - Mode A работать не будет, останутся Spark + Transcript

→ `paths.funnel_map` или `null`

### Q7: Стиль обращения

> Как бот обращается к подписчику?
> - «ты»
> - «вы»
> - безличное (через инфинитивы и пассив)

→ `voice.address`

## Дефолты после Q1-Q7

Остальные параметры - sane defaults:
- `voice.imperative_friendly: true` (если Q7 = «ты»), `false` (если «вы»)
- `voice.emoji_policy: minimal`
- `voice.exclamation_max: 0`
- `length.max: 300`, `length.buttons.count_max: 3`
- `output.format: chat`
- `output.include_ab_variant: true`
- `output.include_internals: true`
- `validation.three_layers_required: true`

## Запись config.md

После сбора ответов - Write по пути `~/.claude/skills/bot-message/config.md` (или указанному в окружении ученика). Использовать как шаблон существующий `config.md` автора, заменив только заполненные поля.

## Проверка после записи

1. Прочитать `paths.avatar` - существует ли файл? Если нет - warning «положи аватар по пути X перед `/push`, иначе voice будет generic».
2. Прочитать `paths.funnel_map` (если указан) - существует? Если нет - warning «карта воронки не найдена, Mode A → fallback на Spark-B2».

## Передача управления

После записи config + проверок → `01-router.md` принимает оригинальный input пользователя (тот же `/push <args>`, что инициировал onboarding) и продолжает workflow.