# Template: mid-3-10min (YouTube mid-form)

Грузится в `workflow/03-structure.md` когда `length_tier = mid-3-10min`.

**Когда применять:** YouTube mid-form. Глубокий разбор / методология / case-study. Chapters с mini-hooks обязательны для retention.
**Reference creators:** Nate Herk (long methodology), Riley Brown (deeper tutorials), Chris Cordero (EN mid-form).
**Sweet spot duration:** 6 min (360 sec).

## Structure (chapters + mini-hooks)

| Section | Duration | Words RU | Words EN | Назначение |
|---|---|---|---|---|
| hook | 15 sec | 38 | 41 | Stop scroll + visual contrast |
| promise/preview | 15 sec | 38 | 41 | Что узнаешь за 6 min |
| setup | 20 sec | 50 | 54 | Контекст |
| chapter_1 | 60 sec | 150 | 162 | Грань 1 |
| mini_hook_2 | 5 sec | 13 | 14 | Retention bridge |
| chapter_2 | 60 sec | 150 | 162 | Грань 2 |
| mini_hook_3 | 5 sec | 13 | 14 | Retention bridge |
| chapter_3 | 60 sec | 150 | 162 | Грань 3 |
| mini_hook_4 | 5 sec | 13 | 14 | Retention bridge |
| chapter_4 | 60 sec | 150 | 162 | Грань 4 (optional) |
| synthesis | 40 sec | 100 | 108 | Связка + insight |
| cta | 15 sec | 38 | 41 | Action |

Sum (4 chapters): 360 sec / ~903 words RU.
3-chapter version: 280 sec.
5-chapter version: 425 sec (близко к ceiling).

## Headline (YouTube title)

ОБЯЗАТЕЛЕН. ≤70 chars. Формула:
- Specificity (число / имя / artefact)
- Promise (что зритель получит)
- Hook archetype-aware

Examples:
- «Контент-завод на Claude Skills: 6 минут на полный setup»
- «Я заменил 3 SaaS подписки одним промптом. Вот как»
- «N8N умирает: 4 признака что пора переходить»

3 variants: Primary / Alt A (curiosity) / Alt B (concrete result).

## Hook archetype fit

Best fit:
- Pattern 7 (Curiosity gap) - отлично (длинный setup)
- Pattern 8 (Numbered) - отлично (chapters = list)
- Pattern 6 (Contrarian) - для opinion piece
- Pattern 1 (Timeframe + outcome) - для case-study

## Pacing

- Темп medium. Не Hormozi-rush.
- RU 2.3-2.5 слов/sec
- Каждые 60-90 sec retention dip prevention = mini_hook
- Visual changes каждые 5-10 sec (B-roll / screen demo swap)

## Mini-hook patterns

- «А вот что я раньше упускал»
- «Тут есть один фокус, который меняет всё»
- «Самое интересное в третьем шаге»
- «И вот где обычно ошибаются»
- «А теперь самый главный вопрос»

Без mini-hooks retention к 2:00 падает >40%.

## Caption overlay (YouTube)

- НЕ Hormozi word-by-word
- YouTube auto-captions достаточно
- Optional: burned-in subtitles при ru→en cross-distribution
- Aspect 16:9 horizontal

## Production handoff

Manual production (нет automated skill в v1.0).
Future: youtube-mid-form-production skill.
Output: full script + headline + chapter map + thumbnail brief.

## Chapter map (YouTube timestamps)

В description видео:
```
0:00 - Hook
0:15 - Что узнаешь за 6 минут
0:30 - Контекст
0:50 - <Chapter 1>
1:55 - <Chapter 2>
3:00 - <Chapter 3>
4:05 - <Chapter 4>
5:10 - Связка + insight
5:50 - Action
```

## Thumbnail brief

- 1280×720 minimum
- Vibrant high-contrast colors
- Face автора (если screen-cam)
- Big bold text (≤6 слов, ALL CAPS, contrasting)
- Visual contrast (before/after / numeric prominent)

## Beat placeholders (для 04-write.md)

```yaml
hook:
  duration_sec: 15
  seed: "<extended hook, 38 слов>"
promise:
  duration_sec: 15
  seed: "<3-5 bullets что узнаешь>"
setup:
  duration_sec: 20
  seed: "<контекст темы, история>"
chapter_1:
  duration_sec: 60
  seed: "<грань 1 с 2-3 examples>"
  has_mini_hook_after: true
chapter_2:
  duration_sec: 60
  seed: "<грань 2>"
  has_mini_hook_after: true
chapter_3:
  duration_sec: 60
  seed: "<грань 3>"
  has_mini_hook_after: true (if chapter_4)
chapter_4:
  duration_sec: 60
  seed: "<optional грань 4>"
  optional: true
synthesis:
  duration_sec: 40
  seed: "<key takeaways 3-5 пунктов + emotional landing>"
cta:
  duration_sec: 15
  seed: "<single action + value proposition>"
```

## Anti-patterns

- Skip mini-hooks (retention падает >40% к 2:00)
- Hormozi-pacing для 6 min (выматывает зрителя)
- Списки 7+ items в одной chapter (split на N chapters)
- Hook <10 sec (для long-form нужен deeper hook)
- Synthesis = «обсудим в комментах» (не payoff)
- Multiple CTA в разных chapters (только в финале)
- 9:16 vertical для YouTube long (всегда 16:9)
- Burned-in Hormozi captions (нативные captions достаточно)

## Length check

Floor 180 sec / Ceiling 600 sec / Sweet spot 5-7 min.