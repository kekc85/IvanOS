---
name: "cut-from-long-form"
description: "Extract 5-7 viral cuts from YouTube long-form video via Reap MCP. Produces vertical Shorts / Reels / TikTok ready for distribution with auto-translation to RU."
---

# Cut from Long-Form (sub-format #3)

## Когда использовать

После публикации weekly YouTube long-form pillar. Auto-extract 5-7 cuts для daily Shorts / Reels / TikTok distribution.

Sub-format #3 из 5 video sub-formats. **Самый efficient способ multiply контент**: 1 long-form запись → 5-7 cuts → cross-distributed.

## Tool stack

**Primary**: **Reap MCP** (через Claude, free)
- Input: YouTube URL or video file
- Auto-extracts viral moments
- Adds captions in 98 languages
- Auto-dubs in 80 languages
- Output: vertical 9:16 ready Shorts

**Backup**: OpusClip / Submagic (paid SaaS) если Reap MCP недоступен

## Шаги

### Шаг 1: Verify long-form ready
- YouTube video uploaded (or local file path)
- Длительность 8-25 мин (optimal для cut extraction)

### Шаг 2: Invoke Reap MCP
Через Claude prompt:
```
Use Reap MCP to extract 5-7 viral shorts from [YouTube URL or file path].
Settings:
- Length per short: 30-60 seconds
- Captions: detect source language automatically (RU primary для авторская контента, EN если long-form на английском)
- Vertical 9:16 aspect ratio
- Include face/speaker focus when applicable
- Output: 5-7 ranked clips
```

### Шаг 3: Manual review extracted clips
Проверить каждый из 5-7:
- Стопит scroll? (first 3 sec hook)
- Self-contained meaning? (не "продолжение в long-form")
- Voice clear?
- Visual interesting?

Drop 1-2 weakest, keep top 4-6.

### Шаг 4: Apply F.5 Hook + Title generator
Для каждого clip - generate 3-5 hook variations для A/B testing:
```
For each clip:
- Hook variant A (curiosity gap)
- Hook variant B (contrarian)
- Hook variant C (numbered list)
```

### Шаг 5: RU localization (parallel)
Reap MCP auto-dubs - просто request:
```
Auto-dub each clip to Russian.
Localize examples ($K USD → ₽K RUB / EN names → RU).
Output: 4-6 EN clips + 4-6 RU clips = 8-12 final clips for distribution.
```

### Шаг 6: Distribution scheduling
- EN clips: YouTube Shorts + Нельзяграм Reels + TikTok (через Buffer)
- RU clips: TG <твой-хэндл> + RU Нельзяграм accounts (через Uniqalizer multi-account)
- Cadence: 1 EN + 1 RU per day distributed across week

## Гвардрейлы

- Voice автора сохранён (не AI generic voice если auto-dub)
- БЕЗ em-dash в captions
- Категория вайбмаркетинг (если applicable)
- Lexicon RU: Нельзяграм / Дубайск / контент-завод
- Каждый cut self-contained (можно понять без long-form)

## Output format

```
**Source long-form**: [YouTube URL / title / length]

**Extracted clips** (через Reap MCP):
1. Clip A (0:23-1:05, 42 sec) - Topic: [X]
   Hook variant: "[hook A]"
   RU version: "[hook RU]"
2. Clip B (4:18-5:00, 42 sec) - Topic: [Y]
   Hook: "..."
   ...
[5-7 total]

**Production status**:
- EN clips ready: [N]
- RU dubs ready: [N]
- Scheduled distribution: [list dates + platforms]

**Total content output from 1 long-form**: [N EN clips + N RU clips = N×2 final pieces]
```

## Что НЕ делаем

- Edit clips beyond Reap MCP output (keep efficient)
- Add complex transitions / effects (lose authenticity)
- Force non-viral moments как cuts (drop them)
- Use generic AI voice если auto-dub звучит non-Ivan (manual record вместо auto-dub)

## Связано

- `tasks/projects/mcp-skills-install.md` - Reap MCP setup
- `.business/processes/acquisition-methodology.md` - workflow context
- Skills: hook-generator (F.5) для hook variants