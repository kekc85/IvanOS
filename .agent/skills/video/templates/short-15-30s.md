# Template: short-15-30s (ультра-короткий шорт)

Грузится в `workflow/03-structure.md` когда `length_tier = short-15-30s`.

**Когда применять:** loop-friendly шорт для virality. Sharp single idea без preamble. Reels / Shorts / TikTok минимальная длительность.
**Reference creators:** Riley Brown (Pattern 1 timeframe), Sabrina Ramonov (Pattern 4 tool reveal).
**Sweet spot duration:** 25 sec.

## Structure (5 beats)

| Beat | Duration | Words RU | Words EN | Назначение |
|---|---|---|---|---|
| hook | 3 sec | 8 | 10 | Stop scroll, immediate contrast/promise |
| body_1 | 8 sec | 20 | 22 | Одна конкретная грань |
| body_2 | 8 sec | 20 | 22 | Развитие или контраст |
| payoff | 4 sec | 10 | 11 | Insight / drop mic |
| cta_or_close | 2 sec | 4 | 5 | Optional CTA или закрытие |

Sum: 25 sec / ~62 words RU.

## Fallback каркас (NEW 2026-05-28, from SOLO pisatel-rilz-razgovor)

Если для темы НЕТ tested template из gold-standard, использовать 5-блочный fallback:

| Block | Duration | Назначение |
|---|---|---|
| Хук | 2-3 sec | Pattern interrupt, конфликт/контраст/numeric outlier |
| Проблема | 5-10 sec | Узнаваемая боль рынка / ICP формулировкой опроса |
| Решение | 5-10 sec | Личный сдвиг автора + механизм |
| Разбор | 3-5 sec | Почему именно так работает (one insight) |
| CTA | 2-5 sec | Нейтральный («подпишись если откликается») или воронка («в шапке → забирай») |

Использование: для тем у которых нет аналога в gold-standard корпусе. Преимущество — гарантированно не сломается, недостаток — менее специфично чем custom template.

## Hook archetype fit

Pattern 1 / 2 / 4 / 5 / 6 - подходят. Pattern 7 (curiosity gap) и Pattern 8 (numbered) - НЕ подходят (нужен setup на 60+ sec).

## Pacing

- Очень быстро. Каждый beat = 1-2 caption lines.
- Темп RU ~2.5 слов/sec, EN ~2.7.
- Никаких пауз / breath / setup phrases.
- Hook = первая ясная фраза, без «привет», «сегодня», «в этом видео».

## Caption overlay

- 8-12 lines total, ALL CAPS Hormozi
- 2-4 слова на line
- Hook line bigger, hold 1.5 sec
- Каждая line 0.4-1.0 sec on screen

## Long caption pattern для overlay-рилзов (NEW 2026-05-28, from SOLO pisatel-rilz-overlay)

Для overlay-рилзов (text на b-roll, не автор в кадре) описание под видео может быть длинным (до 1700-2200 знаков IG). Использовать 4-bullet structure с ▸ если хочется выдать 3-5 несвязанных уроков/инсайтов на одну тему:

```
Контекст-сетап (1-2 предложения, hook от первого лица)

Вот N вещей которые я понял.

▸ Lesson 1 (заголовок)

Раскрытие в 1-2 предложения, конкретно.

▸ Lesson 2 (заголовок)

Раскрытие.

▸ Lesson 3 (заголовок)

Раскрытие.

Closing rhythm (1-2 предложения, drop mic — без CTA или с нейтральным).
```

Преимущества: визуальный сканнинг (▸ держат внимание), легко удалить/добавить bullet, ритмично. Альтернатива narrative-описанию когда тема естественно состоит из N независимых уроков.

## Production handoff

screen-record-face-cam / split-screen-trend-jack / ai-avatar-news / before-after.
Aspect: 9:16 vertical.

## Beat placeholders (для 04-write.md)

```yaml
hook:
  archetype: <from finalize>
  seed: "<8 слов outlaw/magician hook>"
  caption_lines: [<2 lines>]
body_1:
  seed: "<20 слов конкретная грань 1>"
  caption_lines: [<3-4 lines>]
body_2:
  seed: "<20 слов грань 2 или контраст>"
  caption_lines: [<3-4 lines>]
payoff:
  seed: "<10 слов insight>"
  caption_lines: [<2 lines>]
cta_or_close:
  seed: "<4 слова single action или drop mic>"
  caption_lines: [<1 line>]
  optional: true
```

## Anti-patterns

- Setup beat ДО body (нет времени)
- 3+ body beats (не помещается)
- Длинные предложения >12 слов
- Hook >5 слов (читается дольше 1 sec)
- Финал = «давайте обсудим» (не payoff)
- CTA = «like + subscribe» (generic)

## Length check

Floor 15 sec / Ceiling 30 sec. В 05-review G11/G12 sum check.