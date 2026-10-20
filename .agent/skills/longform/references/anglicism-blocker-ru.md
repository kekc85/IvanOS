# Anglicism Blocker (RU canonical)

> Hard gate в `04-review.md` Pass 1 для RU canonical text. Каждый англицизм auto-fail с подсказкой RU-замены. Density threshold: >5 англицизмов на 1000 слов = FAIL. Inherits + extends `post/config.md` lexicon_banned_hard.

## Принцип

В RU canonical longform каждый англицизм должен иметь чёткую причину остаться (proper noun продукта, отсутствие точного RU аналога, цитата). Все остальные случаи замены через RU аналоги. Это **не стилистическое предпочтение**, это hard rule: один англицизм = один FAIL, density >5/1000 слов = revision request.

## Catalog (для regex check)

### Контент / маркетинг nouns

| Англицизм | RU замена | Notes |
|---|---|---|
| tools | инструменты | hard fail |
| tool | инструмент | hard fail |
| stack | связка / набор / комплект | hard fail |
| pipeline | завод / процесс / поток | hard fail (уже в post) |
| framework | каркас / схема | hard fail (уже) |
| workflow | процесс / порядок | hard fail (уже) |
| feedback | обратная связь / отклик | hard fail (уже как фидбэк) |
| feedback loop | петля обратной связи | hard fail |
| pipeline | завод / процесс | hard fail |
| transition | переход | hard fail |
| crossfade | плавный переход | hard fail |
| viral | вирусный / залетающий | hard fail |
| layered | многоуровневый / по уровням | hard fail |
| catalog | библиотека / список | hard fail |
| mockup / mockups | макет / макеты | hard fail |
| validators | проверки | hard fail |
| gauntlet | прогон | hard fail |
| guesswork | гадание / предположения | hard fail |
| reveal | раскрытие | hard fail |
| payoff (в meta-контексте) | оплата / результат | hard fail (OK как технический термин нарратологии в отдельных абзацах review-секции, но НЕ в body) |
| stack-up | сборка | hard fail |
| breakdown | разбор | hard fail (как noun) |
| takeaway | вывод | hard fail |
| hack / hacks | приём / приёмы | hard fail |
| hustle | пахота / суета | hard fail |
| edge case | пограничный случай | hard fail (раскрыть в первый раз) |
| use case | сценарий применения | hard fail |
| insight / insights | находка / прозрение | hard fail |
| flow | поток | hard fail |
| onboarding | первичная настройка | hard fail (уже) |
| scope | охват | hard fail (уже) |
| roadmap | план / маршрут | hard fail |
| value prop | ценностное предложение | hard fail |
| trigger | пусковая фраза / запуск | hard fail (раскрыть как технический термин) |
| brief | задача / задание | hard fail |
| draft | черновик | hard fail |

### AI / Tech terms (raised verbally - раскрытие в первом упоминании обязательно)

| Англицизм | Когда OK | Когда FAIL |
|---|---|---|
| OCR | если раскрыто в первом упоминании «OCR (распознавание текста на изображении)» | без раскрытия |
| TTS | если раскрыто «TTS (синтез голоса из текста)» | без раскрытия |
| LLM | если раскрыто «LLM (большая языковая модель)» | без раскрытия |
| voice clone | если раскрыто «клонирование голоса» | без раскрытия |
| avatar (AI) | если раскрыто «цифровой двойник» | без раскрытия |
| TG-pipeline | если раскрыто | без раскрытия |
| motion blocks | если раскрыто «блоки анимации» | без раскрытия |
| easing curves | если раскрыто «кривые ускорения» | без раскрытия |
| Material motion tokens | если раскрыто «токены анимации Material Design» | без раскрытия |
| hook | если раскрыто «зацепка первых секунд» | без раскрытия |
| catalog (motion) | если раскрыто | без раскрытия |
| ingest | если раскрыто «загрузка и анализ» | без раскрытия |

### Generic banned phrases

| Фраза | RU замена |
|---|---|
| talking head | говорящая голова в кадре |
| heading-shot | заголовок |
| screen-record | запись экрана |
| face-cam | лицо в кадре |
| split-screen | разделённый экран |
| stop-scroll | остановка скролла |
| open rate | процент открытий |
| click-through | переходы |
| engagement | вовлечение (уже banned как энгейджмент) |
| retention | удержание (уже banned) |
| churn | отток |
| stack-rank | приоритизировать |

## Density rule

**Total англицизмов в RU canonical longform / total words * 1000 > 5 → FAIL.**

Подсчёт: count всех matches с этим catalog.

При FAIL - output revision request со списком конкретных matches + suggested RU replacements per match.

## Когда англицизм legitimate (whitelisted exception)

| Тип | Пример | Правило |
|---|---|---|
| Proper noun продукт | n8n, Claude, HeyGen, ElevenLabs, Kling, Remotion, Telegram (как brand) | OK как noun |
| Цитата | «он сказал: it works» | OK в кавычках |
| Технический термин с явным раскрытием в первом упоминании | «OCR (распознавание текста на изображении)» | OK |
| URL/email/handle | newsletter@example.com | OK |

## Memory cross-refs

- - главное правило
- - обязательное раскрытие