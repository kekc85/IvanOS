# Template: long-10-60min (YouTube long-form)

Грузится в `workflow/03-structure.md` когда `length_tier = long-10-60min`.

> **Status v1.0: EXPERIMENTAL.** Будет корректировка после 3-5 реальных применений. автор этот формат не делает регулярно - данные накапливаются.

**Когда применять:** YouTube long-form. Deep dive / case-study / методология полная / course-lesson.
**Reference creators:** Nate Herk full methodology breakdowns, Riley Brown deep tutorials, Chris Cordero long-form interviews.
**Sweet spot duration:** 25 min (1500 sec).

## Structure (5-9 sections с deep mini-hooks)

| Section | Duration | Words RU | Words EN | Назначение |
|---|---|---|---|---|
| hook | 20 sec | 50 | 54 | Stop scroll |
| promise/preview | 25 sec | 63 | 68 | Roadmap видео + что узнаешь |
| context | 60 sec | 150 | 162 | Зачем тема, откуда |
| section_1 | 4-5 min | 600-750 | 648-810 | Subtopic 1 (с 2-3 mini-hooks) |
| section_2 | 4-5 min | 600-750 | 648-810 | Subtopic 2 |
| section_3 | 4-5 min | 600-750 | 648-810 | Subtopic 3 |
| section_4 | 4-5 min | 600-750 | 648-810 | Subtopic 4 (optional) |
| section_5 | 4-5 min | 600-750 | 648-810 | Subtopic 5 (optional) |
| synthesis | 90 sec | 225 | 243 | Key takeaways list |
| cta + outro | 30 sec | 75 | 81 | Action + next video preview |

3-section version: ~1100 sec (~18 min)
4-section version: 1500 sec (~25 min) - sweet spot
5-section version: ~1850 sec (~31 min)

## Headline (YouTube title)

ОБЯЗАТЕЛЕН. ≤70 chars. Long-form titles work с:
- «Полный гайд», «полное руководство», «деep dive» frames OK
- Numeric specificity («2 часа», «10 шагов»)
- Result + timeframe + method

Examples:
- «Контент-завод на Claude Skills: полный setup за 25 минут»
- «От 0 до $10K MRR за 90 дней. Полная разборка»
- «Vibe marketing от A до Z: одна система, 8 каналов»

## Hook archetype fit

Long-form позволяет deeper hooks:
- Pattern 7 (Curiosity gap) - extended setup
- Pattern 8 (Numbered) - sections = list
- Pattern 6 (Contrarian) - opinion с deep justification
- Pattern 1 (Timeframe + outcome) - case-study format

## Pacing

- Темп slower than mid-form
- RU 2.2-2.4 слов/sec
- Section mini-hooks every 60-90 sec WITHIN section
- Bigger pattern-interrupt в начале каждой section
- Variable visual changes (B-roll длиннее можно, demo сегменты comfortable)

## Section mini-hooks (внутри section)

Каждую 60-90 sec - small pattern-interrupt:
- «И вот ещё что заметил»
- «Эта часть критична»
- «Tут есть unexpected момент»
- «Сейчас покажу live»

В начале каждой section (за исключением section_1) - bigger pattern-interrupt:
- «Теперь самое важное»
- «А вот где меняется всё»
- «Перейдём к части где обычно ошибаются»

## Caption overlay

- НЕ Hormozi word-by-word
- YouTube auto-captions
- Optional: burned-in subtitles только если cross-distribution (RU→EN)
- Aspect 16:9 horizontal

## Production handoff

Manual production (нет automated skill в v1.0).
Future: youtube-long-form-production skill.

Output: full script + headline + chapter map + thumbnail brief + outro plan.

## Chapter map (обязателен для YouTube long)

В description видео - chapters timestamps:
```
0:00 - Hook
0:20 - Что узнаешь за 25 минут
0:45 - Контекст
1:45 - <Section 1 название>
5:45 - <Section 2 название>
10:00 - <Section 3 название>
14:30 - <Section 4 название>
19:00 - Key takeaways
22:30 - Action + что дальше
```

Каждый section в chapter map ≤6 слов в названии (mobile preview cuts).

## Thumbnail brief (для YouTube long)

- 1280×720 minimum
- Vibrant с high contrast
- Face автора (если screen-cam recording)
- Big bold text (≤6 слов ALL CAPS)
- Number prominent если есть («25 МИНУТ», «8 ШАГОВ»)
- Visual proof element (screenshot Stripe, app demo)

## Outro plan (optional)

После CTA - 10-15 sec outro:
- Preview next video («Дальше я разберу X»)
- Subscribe reminder integrated naturally
- End-screen (YouTube auto-frame)

## Beat placeholders (для 04-write.md)

```yaml
hook:
  duration_sec: 20
  seed: "<deeper hook, 50 слов>"

promise:
  duration_sec: 25
  seed: "<3-5 bullet roadmap>"

context:
  duration_sec: 60
  seed: "<контекст, история темы>"

section_1:
  duration_sec: 240-300
  seed: "<subtopic 1 с 2-3 mini-hooks внутри>"
  mini_hooks_inside: 2-3

section_2:
  duration_sec: 240-300
  pattern_interrupt_start: true
  mini_hooks_inside: 2-3

section_3:
  duration_sec: 240-300
  pattern_interrupt_start: true
  mini_hooks_inside: 2-3

section_4:
  duration_sec: 240-300
  optional: true

section_5:
  duration_sec: 240-300
  optional: true

synthesis:
  duration_sec: 90
  seed: "<key takeaways list 5-7 пунктов + emotional landing>"

cta_outro:
  duration_sec: 30
  seed: "<single CTA + next video preview>"
```

## Anti-patterns

- Skip section mini-hooks (retention падает >50% к 5:00)
- Hormozi-pacing на 25 min (выматывает)
- Слишком много sections (>5) - splits внимание
- Hook <15 sec (для long-form читателю нужен time to commit)
- Synthesis = «обсудим в комментах» (всегда concrete takeaways)
- Multiple CTA в разных sections (только в финале)
- 9:16 vertical (всегда 16:9)
- Burned-in Hormozi captions (нативные достаточно)
- Script written in one pass без breaks между sections - читается как лекция, не как video

## Experimental notes (v1.0)

- Long-form pacing data для автора не накоплен (нет регулярных long-form)
- Sweet spot 25 min - guess based на market average; будет корректировка
- 5-section version (~31 min) - close to ceiling, не тестировано
- Mini-hooks density (2-3 per section) - needs validation
- После первых 3 реальных применений - корректировать в v1.2

## Length check

Floor 600 sec (10 min) / Ceiling 3600 sec (60 min) / Sweet spot 18-30 min.

## Cross-distribution after publish

После YouTube long publish → `cut-from-long-form` extract 5-7 shorts через Reap MCP:
- Long-form RU → cuts RU + auto-dub EN
- Long-form EN → cuts EN + auto-dub RU
- Distribute cuts на Shorts / Reels / TikTok