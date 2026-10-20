# 05 - Publish (output text + JSON кнопок + A/B + внутрянка)

> Финальный output в чат. Готово к копи в bot admin / sender CLI. JSON универсальный Telegram Bot API формат.

## Вход

От `04-review.md`:
- Финальный TEXT (прошедший все gates)
- Финальный BUTTONS (microcopy + тип + назначение)
- A/B альтернатива
- Внутрянка
- Флаги (если были - для прозрачности)

## Output формат

### Если `config.output.format == "chat"` (default)

Plain text блок в чат (для копи в TG bot admin без обработки):

```
═══════════════════════════════
TEXT (A - основной)
═══════════════════════════════

<финальный текст 100-300 знаков>

═══════════════════════════════
КНОПКИ (JSON, Telegram Bot API InlineKeyboardMarkup)
═══════════════════════════════

{
  "inline_keyboard": [
    [
      {"text": "<microcopy>", "callback_data": "<slug>"}
    ]
  ]
}

═══════════════════════════════
TEXT (B - A/B альтернатива)
═══════════════════════════════

<альтернативный текст 100-300 знаков>

═══════════════════════════════
КНОПКИ B (JSON)
═══════════════════════════════

{
  "inline_keyboard": [
    [
      {"text": "<microcopy B>", "callback_data": "<slug>"}
    ]
  ]
}

═══════════════════════════════
ВНУТРЯНКА
═══════════════════════════════

Mode: <Plan/Spark-B1/Spark-B2/Transcript>
Type: <voronka-push/reminder/content-tease/...>
Segment: <all/cold/warm/hot/buyer/...>
Hook framework A: <Numbered/Contrarian/.../Time-Trigger>
Hook framework B: <отличающийся от A>
Button strategy A: <single URL / single callback / two-choice / ...>
Button strategy B: <отличающаяся от A>
Что отброшено: <угол X не выбран потому что Y>
A/B логика: <тестируем переменную Z: hook vs button vs angle>
Флаги (если были): <список + митигации из review>
```

### Если `config.output.format == "file"`

Save в `.business/bot/drafts/<YYYY-MM-DD>-<type>-<short-slug>.md` с тем же содержимым. Затем `open <path>` если `config.output.open_after_save: true`.

### Если `config.output.format == "both"`

И в чат, и в файл.

## JSON формат - детали

### Telegram Bot API InlineKeyboardMarkup

Базовая структура:

```json
{
  "inline_keyboard": [
    [
      {"text": "Открыть разбор", "callback_data": "open_breakdown_v1"}
    ]
  ]
}
```

Каждая строка `inline_keyboard` - отдельный массив с кнопками в одном ряду. Чаще всего:
- 1 кнопка → один ряд с одной кнопкой
- 2 кнопки → один ряд с двумя ИЛИ два ряда с одной (в зависимости от длины текста)
- 3 кнопки → один ряд с тремя (если короткие) или три ряда (если длинные)

### Типы кнопок

| Тип | JSON ключ | Пример |
|---|---|---|
| URL | `"url": "https://..."` | `{"text": "Открыть Skool", "url": "https://skool.com/..."}` |
| callback_data | `"callback_data": "slug"` | `{"text": "Забрать промпт", "callback_data": "get_prompt"}` |
| web_app | `"web_app": {"url": "https://..."}` | `{"text": "Открыть мини-апп", "web_app": {"url": "https://..."}}` |
| pay | `"pay": true` | `{"text": "К оплате", "pay": true}` |

### Adaptации для других engines

| Engine | Адаптация |
|---|---|
| Senler | конвертировать `callback_data` → `payload`, не поддерживает `web_app` |
| GetCourse | inline-кнопки не поддерживаются напрямую, fallback на текст с ссылкой |
| Self-coded (aiogram/Pyrogram) | формат Telegram Bot API без изменений |

Если `bot.engine != telegram_bot_api` - в output добавить блок «АДАПТАЦИЯ для <engine>» с конкретными изменениями.

## Pre-flight: Telegram API rate limit

Перед output - расчёт времени рассылки и предупреждение, если база большая:

### Лимиты Telegram Bot API

- **Cloud Bot API (api.telegram.org):** ~30 сообщений/сек на bot. Превышение - HTTP 429 «Too Many Requests» + retry_after.
- **Local Bot API server (own server):** без жёсткого лимита, но Telegram backend всё равно throttle при `>30 msg/sec` сторонним подписчикам разным.
- **На одного user:** ~1 msg/sec (для broadcast на одного user это не блокер).

### Pre-flight calculation

При наличии `bot.subscriber_count` в config (или эстимейте от автора):

```
base = bot.subscriber_count
sec_to_complete = base / 25   # safe rate 25/sec, оставляем margin
min_to_complete = sec_to_complete / 60
```

| База | Время через Cloud API (25/sec) | Рекомендация |
|---|---|---|
| ≤100 | <5 сек | Pass, отправлять без throttle |
| 100-1000 | 4-40 сек | Pass, минимальный throttle (sleep 0.04 между msg) |
| 1000-10000 | 40 сек - 7 мин | WARN: использовать `asyncio.sleep(0.04)` или batch через aiogram dispatcher rate limit |
| >10000 | >7 мин | WARN: рекомендация Local Bot API server ИЛИ broadcast service (Telegram Bot Master, Botfather Premium) |

### Block в output (если база >1000 или unknown)

Добавить в output блок перед «Готово»:

```
RATE LIMIT:
- База подписчиков: ~<N> (из config / estimate)
- Время рассылки через Cloud API: ~<X> минут
- Рекомендация: <throttle / Local API / batch service>
- Risk: при отправке без throttle bot получит 429, push не доставится части базы.
```

### Anti-pattern

Не запускать `send_message` циклом без `await asyncio.sleep` если база >100. Cloud Bot API throttle bot account на минуты при flood detection.

## Логирование (опционально)

Если `paths.recent_push_log` задан - добавить запись:

```
| 2026-05-28 | voronka-push | «3 ошибки воронки…» | [ожидает result] |
```

в файл `recent_push_log`. Запись финализируется (поле `result`) после того, как автор даст обратную связь (через `06-feedback-loop.md` v1.1+ или вручную).

## Подтверждение в чат

После всего output - короткое:

```
Готово. Скопируй TEXT + JSON в bot admin. После публикации - дай знать catch_rate / CTR, обновлю track-record.
```

## Anti-patterns Publish

- **Не сохранять в файл без необходимости**. Default = chat, чтобы автор копировал из чата на mobile. Файл нужен только если есть многошаговая работа.
- **Не показывать только финальный вариант без A/B**. A/B обязателен (см. `config.validation.ab_variant_required`).
- **Не пропускать внутрянку**. Без блока «как писал» - теряется обоснование выбора и не накапливается понимание паттернов.
- **Не использовать TG-форматирование без проверки**. `*bold*`, `_italic_` могут сломаться в зависимости от parse_mode (Markdown / MarkdownV2 / HTML). По умолчанию push идёт plain text - никаких *`_`. Если нужен emphasis - `**` только если bot.parse_mode задан явно.
---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
