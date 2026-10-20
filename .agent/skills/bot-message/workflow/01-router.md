# 01 - Router (detect mode + load config)

> Точка входа в skill. Загружает `config.md`, детектит mode (Plan / Spark-B1 / Spark-B2 / Transcript) и передаёт управление в соответствующий 01a/01b/01c.

## Шаг 1: Load config

1. Read `config.md` (по пути `~/.claude/skills/bot-message/config.md` или указанному).
2. Если config отсутствует / неполный (`bot.handle == null`) → перейти в `00-onboarding-student.md`. После onboarding вернуться сюда.
3. Извлечь:
   - `subject.name`, `subject.language`, `subject.market`
   - `bot.handle`, `bot.engine`, `bot.segments`, `bot.supported_button_types`
   - `paths.*` (все пути к контексту)
   - `voice.*` (параметры голоса)
   - `length.*` (лимиты)
   - `validation.*` (gates)

## Шаг 2: Detect mode

Парсить user input на сигналы:

### Override-флаги (приоритет 1)

| Флаг | Mode |
|---|---|
| `--plan` | Plan (Mode A) |
| `--spark` | Spark-B (Mode B1 или B2 по контексту) |
| `--transcript` | Transcript (Mode C) |

### Auto-detect (приоритет 2)

| Сигнал в input | Mode | Доказательство |
|---|---|---|
| Длина input >500 знаков И «надиктовал/мысли/transcript» | Transcript | Mode C |
| `/push` без аргументов | Plan | Mode A |
| `/push` + день/шаг воронки («Day 3», «после вебинара», «следующий шаг») | Plan | Mode A |
| `/push про X` / «напиши сообщение про X» / «сделай push про X» | Spark-B1 | Mode B1 (есть тема) |
| «дай идеи для push», «что писать в боте сегодня», «winback холодным», «напомни про вебинар» | Spark-B2 | Mode B2 (нет темы, есть триггер) |
| Пустой input | Plan (default), при пустой карте → Spark-B2 | Mode A → fallback |

### Конфликт сигналов

Если 2 сигнала одинакового веса (например, длинный transcript + флаг `--plan`) - выигрывает override-флаг. Если нет флага - Transcript побеждает Plan/Spark (надиктовка содержит конкретное намерение).

## Шаг 3: Извлечь параметры для следующего шага

Перед передачей в 01a/01b/01c - извлечь:

- **Сегмент аудитории** (если упомянут): «cold», «warm», «hot», «buyer» - из `bot.segments`. Если не упомянут - `all`.
- **Тип сообщения** (если упомянут явно): voronka-push / reminder / content-tease / drip-segment / event-trigger / re-engagement / broadcast-news / survey-poll. Если не упомянут - определит `02-structure.md`.
- **Желаемая длина** (если упомянута явно): short / medium / long. По умолчанию - определит `02-structure.md` по типу.
- **Trigger context** (если Mode B2): что произошло, почему этот push? («вебинар через час», «не открывал 30 дней», «купил клуб»).

## Шаг 4: Передать управление

| Mode | Следующий файл | Что передаётся |
|---|---|---|
| Plan | `01a-plan.md` | + параметр `funnel_step` если указан |
| Spark-B1 | `01b-spark.md` | + параметр `topic` (тема из input) |
| Spark-B2 | `01b-spark.md` | + параметр `trigger` (контекст триггера) |
| Transcript | `01c-transcript.md` | + параметр `raw_transcript` (исходный текст) |

## Шаг 5: Подтверждение в чат

Перед запуском следующего файла - однострочное подтверждение в чат:

```
Mode: <Plan/Spark-B1/Spark-B2/Transcript> | Type: <auto/named> | Segment: <all/named> | Bot: <handle>
```

Если автор хочет переопределить - может ответить и роутер пересчитает. Иначе через 1 ход переходим к ideate.

## Edge cases

- **Mode A без funnel_map**: warning «карта воронки не найдена, переключаюсь в Spark-B2». Спросить trigger context. Если пользователь не отвечает - генерить идеи под все актуальные сегменты.
- **Mode C коротче 500 знаков**: warning «текст коротковат для transcript, обработаю как Spark-B1 с этой темой». Без явного апрува, продолжать.
- **Несовместимый engine + button type**: если `bot.engine: senler` и input хочет `web_app` кнопку - warning «Senler не поддерживает web_app, выберу URL или callback». В output JSON автоматически адаптировать.