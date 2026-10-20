# Template: short-60-180s (длинный шорт)

Грузится в `workflow/03-structure.md` когда `length_tier = short-60-180s`.

**Когда применять:** longer storytelling + personal anecdote + 3-5 beats методологии. Reels max / TikTok comfortable. Высокие saves rate, но retention dip middle обязателен.
**Reference creators:** Nate Herk (methodology), Heather Cooper (Runway/Kling), Rowan Cheung (AI news).
**Sweet spot duration:** 90 sec.

Reels max - 90 sec. YouTube Shorts max - 60 sec (НЕ применять). TikTok до 180 sec comfortable.

## Structure (8 beats)

| Beat | Duration | Words RU | Words EN | Назначение |
|---|---|---|---|---|
| hook | 3 sec | 8 | 9 | Stop scroll |
| promise | 7 sec | 18 | 19 | Что зритель получит |
| setup | 10 sec | 25 | 27 | Контекст |
| body_1 | 18 sec | 45 | 49 | Грань 1 с примером |
| body_2 | 18 sec | 45 | 49 | Грань 2 с примером |
| body_3 | 18 sec | 45 | 49 | Грань 3 с примером |
| payoff | 12 sec | 30 | 32 | Synthesis + insight |
| cta | 4 sec | 10 | 11 | Action |

Sum: 90 sec / ~226 words RU.

## Hook archetype fit

Best fit:
- Pattern 7 (Curiosity gap)
- Pattern 6 (Contrarian extended)
- Pattern 8 (Numbered «3 фишки про X»)
- Pattern 1 (Timeframe с deeper breakdown)

## Pacing

- Есть room для примеров и для воздуха
- 1 personal anecdote (story segment 8-12 sec) приемлем
- Mini-hook в начале body_2 ОБЯЗАТЕЛЕН (без него retention dip)

## Retention dip risk

Середина (sec 45-60) - типичная просадка. Mini-hook patterns:
- «А вот что интересно»
- «И тут есть фокус»
- «Самое важное в третьем шаге»
- «А вот ещё что заметил»

## Caption overlay

- 25-40 lines total, ALL CAPS Hormozi
- 2-6 слов на line
- Hook line bigger, hold 1.5 sec
- 0.5-2.0 sec on screen per line (variable)

## Production handoff

screen-record-face-cam (deep demo) / ai-avatar-news (daily volume + B-roll) / replicate-reel (Mode C).
Aspect: 9:16 vertical.

## Headline / caption overlay first 3 sec

≤50 chars Hook line.

Examples:
- «ВСЕ ЗНАЮТ CLAUDE. НИКТО НЕ ИСПОЛЬЗУЕТ ОДНУ ФИЧУ»
- «3 ПРОМПТА КОТОРЫЕ Я ГОНЯЮ КАЖДЫЙ ДЕНЬ. ТРЕТИЙ - ЛУЧШИЙ»

## Beat placeholders (для 04-write.md)

```yaml
hook:
  seed: "<3-sec hook, 8 слов>"
promise:
  seed: "<что зритель узнает за 90 sec>"
setup:
  seed: "<контекст: откуда тема, что было раньше>"
body_1:
  seed: "<грань 1 + example + implication>"
body_2:
  mini_hook: true
  seed: "<MINI-HOOK + грань 2 + example>"
body_3:
  seed: "<грань 3 + example>"
payoff:
  seed: "<synthesis + emotional landing + key insight>"
cta:
  seed: "<single action>"
```

## Beat shape (для body)

Каждый body_N (18 sec / 45 RU words) = 3-part shape:
1. Setup of point (~5 sec)
2. Concrete example or demo (~8 sec)
3. Implication / why important (~5 sec)

## Anti-patterns

- Hook >3 sec
- Setup >12 sec (отнимает время от body)
- Только 2 body beats (нужно 3 для 90 sec)
- Skip mini-hook в body_2 (retention dip fails)
- Payoff <8 sec (для 90 sec нужна качественная посадка)
- Multiple CTA (single action only)
- Long sentences >15 words (темп падает)

## Platform-specific

- YouTube Shorts: НЕ применять (max 60 sec). Use short-30-60s.
- Reels: OK до 90 sec
- TikTok: OK до 180 sec; sweet spot 90-120 sec

## Example reference

`examples/_TEMPLATE-shorts.md`:
- Эталон 3 (Mode C replication Sage) - 95 sec, в TikTok comfortable

## Length check

Floor 60 sec / Ceiling 180 sec strict / Sweet spot 75-105 sec.