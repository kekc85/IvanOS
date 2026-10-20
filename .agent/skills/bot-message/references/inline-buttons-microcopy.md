# Inline buttons microcopy

> Каталог CTA-кнопок для bot push. RU + EN. Структура «глагол + объект», длина 8-24 знака.

## Принципы microcopy

1. **Глагол действия + конкретный объект**. Не «Открыть», а «Открыть разбор». Не «Получить», а «Получить промпт».
2. **8-24 знака**. Меньше - недостаточно контекста, больше - обрезается на mobile.
3. **Tense match с текстом push**. Если в push «иду на вебинар» - кнопка «Иду», не «Идти».
4. **Lowercase, кроме первой буквы**. Капс и Title Case выглядят как кричащая реклама.
5. **Без эмоджи в одиночку**. «👉» как кнопка - fail. Эмоджи + слово допустимо если есть смысл (редко).
6. **Affordance > marketing**. Кнопка показывает что произойдёт, не убеждает кликнуть. Не «Узнай больше», а «Открыть статью».

## Каталог CTA-глаголов

### Потребление контента

| RU (длина) | EN (длина) | Применение |
|---|---|---|
| Открыть пост (11) | Open post (9) | URL на пост в канале |
| Открыть разбор (14) | Open breakdown (14) | URL на разбор |
| Читать статью (13) | Read article (12) | URL на эссе / blog |
| Смотреть видео (14) | Watch video (11) | URL на Reels / Shorts / YouTube |
| Открыть эссе (12) | Open essay (10) | URL на newsletter article |
| Слушать подкаст (15) | Listen podcast (14) | URL на аудио |

### Получение материала

| RU (длина) | EN (длина) | Применение |
|---|---|---|
| Забрать промпт (14) | Get the prompt (14) | callback → выдать lead magnet |
| Получить чек-лист (17) | Get checklist (13) | callback → выдать PDF |
| Скачать шаблон (14) | Download template (17) | URL → file |
| Забрать гайд (12) | Get the guide (13) | callback → выдать материал |
| Получить разбор (15) | Get breakdown (13) | callback → выдать |

### Регистрация / Подтверждение

| RU (длина) | EN (длина) | Применение |
|---|---|---|
| Иду на вебинар (14) | I'm in (6) | callback → подтверждение |
| Иду (3) | I'm in (6) | callback короткий |
| Зарегистрироваться (18) | Register (8) | URL → registration |
| Записаться (10) | Sign up (7) | URL → signup form |
| Подключиться (12) | Join now (8) | URL → live event |

### Покупка / Деньги

| RU (длина) | EN (длина) | Применение |
|---|---|---|
| К оплате (8) | Pay now (7) | URL → checkout |
| Войти в марафон (15) | Join marathon (13) | URL → join |
| Купить курс (11) | Buy course (10) | URL → purchase |
| Оплатить тариф (14) | Choose tier (11) | URL → pricing |

### Сегментация / Выбор

| RU (длина) | EN (длина) | Применение |
|---|---|---|
| Я новичок (9) | I'm new (7) | callback → segment new |
| Я с опытом (10) | I have experience (16) | callback → segment exp |
| Не сейчас (9) | Not now (7) | callback → defer |
| Напомнить позже (15) | Remind later (12) | callback → reschedule |
| Только посмотреть (17) | Just looking (12) | callback → segment cold |

### Откладывание

| RU (длина) | EN (длина) | Применение |
|---|---|---|
| Напомнить позже (15) | Remind later (12) | callback → reschedule reminder |
| Через час (9) | In 1 hour (9) | callback → schedule |
| Завтра (6) | Tomorrow (8) | callback → schedule tomorrow |

## Запретные microcopy (auto-fail в review)

| Pattern | Проблема |
|---|---|
| «Узнать» | Что узнать? Generic |
| «Узнать больше» | Что больше? Generic |
| «Подробнее» | Подробнее о чём? Generic |
| «Подробности» | То же |
| «Click here» | Generic, EN-AI-tell |
| «Тык» / «Сюда» | Жаргон, без смысла |
| «OK» / «Да» / «Нет» | Без объекта |
| «Ссылка» | Что за ссылка? |
| «Перейти» | Куда? |
| «🔥» / «👉» / «💎» в одиночку | Эмоджи не CTA |
| «??» | Punctuation как кнопка |

## Структура кнопочной стратегии по типу push

| Тип push | Кнопок | Strategy | Пример |
|---|---|---|---|
| voronka-push | 1-2 | single URL/callback | «Получить разбор» |
| reminder | 1 | single callback | «Иду» |
| content-tease | 1 | single URL | «Читать пост» |
| drip-segment | 1-2 | single + optional defer | «Получить» + «Завтра» |
| event-trigger | 1-2 | callback (continue) | «Продолжить» |
| re-engagement | 2 | binary segment | «Я вернулся» + «Отписаться» |
| broadcast-news | 1-2 | URL primary + defer | «Открыть» + «Не сейчас» |
| survey-poll | 2-3 | parallel options | «Вариант А» / «Вариант Б» / «Вариант В» |

## Visual layout - кнопки в рядах

Telegram inline_keyboard - массив рядов, каждый ряд - массив кнопок.

| Сценарий | Layout |
|---|---|
| 1 кнопка | `[[btn1]]` (1 ряд, 1 кнопка) |
| 2 кнопки коротких (≤12 знаков) | `[[btn1, btn2]]` (1 ряд, 2 кнопки) |
| 2 кнопки длинные | `[[btn1], [btn2]]` (2 ряда, по 1) |
| 3 кнопки короткие | `[[btn1, btn2, btn3]]` (1 ряд, 3 кнопки) |
| 3 кнопки длинные | `[[btn1], [btn2], [btn3]]` (3 ряда) |

Правило: если суммарная длина >36 знаков (с учётом отступов) - переносить в несколько рядов.

## Localization - RU ↔ EN

При bilingual (`config.bilingual.enabled: true`) - НЕ дословный перевод. Адаптация:

| RU | EN-direct (плохо) | EN-cultural (хорошо) |
|---|---|---|
| Иду на вебинар | I go to webinar | I'm in |
| Забрать промпт | Take the prompt | Get the prompt |
| Узнать (запрет) | Find out (так же плохо) | Open breakdown |

Принцип: RU - действия от себя на объект («иду», «забираю», «открываю»). EN - статус («I'm in», «I'm joining», «count me in»).

## Callback timing (Telegram 15s rule)

Telegram требует bot ответить на `callback_query` (нажатие кнопки) **в течение 15 секунд** через `answerCallbackQuery`. Если bot не отвечает - пользователь видит «callback expired» error и теряет конверсию.

### Правила для каждого callback_data

| Тип операции | Pattern | Длительность |
|---|---|---|
| Простой (выдать предзаписанный ответ) | `answerCallbackQuery` + `editMessageText` в одном handler | <1 сек, прямой response |
| Средний (BD lookup / выдать lead magnet файл) | `answerCallbackQuery({show_alert: false})` сразу + `sendMessage` отдельно | ~2-3 сек, OK |
| Длинный (генерация PDF / обращение к LLM / external API) | **Pre-emptive ack**: `answerCallbackQuery(«Готовлю материал…»)` СРАЗУ + background task → `sendMessage` через 10-60 сек | Любой, не падает |
| Очень длинный (>60 сек) | Pre-emptive ack + сохранить task_id + push-уведомление через `sendMessage` когда готово (job queue паттерн) | Любой |

### Anti-pattern

```python
# ПЛОХО - блокирует callback на длинной операции, expired error через 15 сек
@dp.callback_query(F.data == "generate_pdf")
async def handler(call):
    pdf = await generate_pdf_via_llm()  # 30 секунд
    await call.message.answer_document(pdf)
    await call.answer()  # уже expired
```

### Правильно

```python
# ХОРОШО - immediate ack, background work
@dp.callback_query(F.data == "generate_pdf")
async def handler(call):
    await call.answer("Готовлю PDF, через минуту пришлю")  # <1 сек ack
    asyncio.create_task(send_pdf_later(call.from_user.id))  # background
```

### Применимость в bot-message output

При planning callback_data в `02-structure.md` - проверять:
- Что будет на стороне bot за этой кнопкой? Долгая операция?
- Если да → в внутрянке output пометить «Long callback: требует pre-emptive ack pattern».
- Если нет (простой URL или быстрый response) → стандартный handler OK.

Это не блокирует output push'а - но bot-разработчик (или сам автор при настройке handler'а) должен это учесть. При выводе **рекомендации в внутрянку** для callback-кнопок добавлять одну строку: «Handler tip: response < 15s или pre-emptive ack».

## Tracking & analytics

Если bot engine поддерживает analytics (aiogram + ymetrika, например) - кнопки с уникальным callback_data позволяют:

- Track CTR per push
- A/B сравнение между push A и push B
- Сегментация подписчиков по их выборам

Для callback_data использовать структуру: `<type>_<topic>_<variant>_<date>`.

Примеры:
- `voronka_funnel-map_a_2026-05-28`
- `reminder_webinar_iduvarp_2026-05-28`
- `tease_post-47-purchases_2026-05-28`