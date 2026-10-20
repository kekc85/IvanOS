---
name: "split-screen-trend-jack"
description: "Video sub-format #2 - Split-screen trend-jack with AI prompt. Top half = viral trending content, bottom = your reaction/AI demo. Heather Cooper + Sabrina Ramonov style"
---

# Split-Screen Trend-Jack + AI Prompt (Video Sub-format #2)

## Когда использовать

Catching виральные форматы 24-72 hour window. Reference creators:
- **Heather Cooper** (@HBCoop_, 60K+ + 16K newsletter) - Runway/Kling Creative Partner demos
- **Sabrina Ramonov** (1.3M cross-platform, 22M views/month TikTok) - AI tool integration

## Структура

```
Vertical 9:16 split:
- Top 50%: viral trending content / AI prompt / news / другой creator's залетевший Reel
- Bottom 50%: your face-cam OR AI demo OR commentary
- Captions: Hormozi-style bold word-by-word

Length: 15-25 sec optimal
Hook: visual transformation OR "turn yourself into [X]"
```

## Hook patterns для этого sub-format

Из viral hook library 2026:
1. **Trend-jack**: "Turn yourself into [trending pattern]"
2. **Cost-flip**: "[Brand X] spent $500K. I made it in [Y] with [tool]" (PJ Ace IM8 pattern)
3. **Contradiction**: "Everyone thinks [X]. But [opposite]"
4. **Visual transformation**: morphing AI output в первые 1 sec

## Стек tools

| Этап | Tool | Cost |
|---|---|---|
| Source viral content discovery | Virale / feed / TikTok For You | $X/мес ChatPlace |
| Top half AI generation | Kling 3.0 / Higgsfield / Nano Banana / ChatGPT image | $20-50/мес |
| Bottom half recording | iPhone front camera OR Screen Studio | hardware / $20-25 |
| Split-screen edit | CapCut (free, built-in split) | бесплатно |
| Captions | CapCut auto или Submagic | бесплатно / $16/мес |

## Workflow

### Шаг 1: Find trending source
**Critical: 24-72h window**:
- Source viral Reel у растущего creator через Virale (Нельзяграм)
- Trending sound / format на TikTok For You
- Viral X-thread с image trend
- AI tool release (новая Claude / Kling / Higgsfield feature)

**Apply virality × deficiency filters** (memory rules):
- Залетело у source 3-4 дня? (просмотры/engagement)
- Идея max 1 неделя на рынке?
- Если оба нет → DROP

### Шаг 2: Generate top half (AI)
Если source = viral prompt / trend (e.g. "Turn yourself into KBO baseball spectator"):
- Generate в Kling / Higgsfield / Nano Banana / ChatGPT image
- 5-10 sec видео-output OR static image with animation
- 9:16 vertical aspect, top half only (cropped к square if нужно)

### Шаг 3: Record bottom half
**Option A: Face-cam reaction**:
- iPhone front cam
- 5-15 sec talking head
- Reaction / commentary к трend сверху

**Option B: AI demo bottom**:
- Screen Studio capture
- Demo same prompt / tool в Claude / Lovable / etc
- Show step-by-step quickly

### Шаг 4: Split-screen assembly (CapCut)
- Top half: viral source / AI gen
- Bottom half: your face-cam / demo
- Synced timing (key moments lined up)
- Hook caption first 1.5 sec across full vertical

### Шаг 5: Captions Hormozi-style
- Word-by-word bold
- Yellow / white outlined
- Hook overlay first 1.5 sec

### Шаг 6: Distribution
- Нельзяграм Reel primary (где trend и зародился если из Reels)
- YouTube Shorts cross-post
- TikTok cross-post
- (через uniqalizer): multi-account Нельзяграм

## Гвардрейлы

- **Speed critical**: 24-72h от source publish до твоего publish (иначе trend выгорит)
- Voice автора если talking
- БЕЗ em-dash в captions
- Categorically вайбмаркетинг angle
- Trend / source attribution если copyright concerns
- БЕЗ direct copying без adaptation (Originality Score)
- Hook captures contrast в 1.5 sec

## Output format

```
**Trend source**: [URL / creator name / platform]
**Trend published**: [date]
**Time since publish**: [X hours] - target <72h
**Virality verified**: [views / engagement at source]
**Deficiency check**: [used <5 times in niche last 7 days? YES/NO]

**Top half (AI generated)**:
- Tool: [Kling / Higgsfield / Nano Banana / ChatGPT]
- Prompt: "[exact prompt]"
- Duration: [5-10 sec]
- Cost: $[X]

**Bottom half**:
- Type: [face-cam reaction OR AI demo]
- Length: [matched к top]
- Voice over: [script если talking]

**Edit specs**:
- Split: 50/50 vertical 9:16
- Hook caption first 1.5 sec: "[exact text]"
- Sync moments: [list 2-3 key alignments]
- Total length: 15-25 sec

**Distribution**:
- Primary: Нельзяграм Reel (где trend зародился)
- YouTube Shorts cross-post
- TikTok cross-post
- (через uniqalizer): multi-account Нельзяграм если применимо
- (опционально): RU dub через C.3

**A/B variants**:
- Hook A: [variant]
- Hook B: [variant]
```

## Что НЕ делаем

- Direct copying без adaptation (Originality Score детектит)
- Late jumping (через 72+ часов trend выгорел)
- Generic AI output без personal angle
- No-context split-screens (нужен visual logic)
- Long voice overs (>20 sec bottom = boring)
- Em-dash в captions

## Связано

- Memory: `project_viral_hook_library_2026`
- Memory: `feedback_strategy_copy_faster_more_better` (core strategy)
- Memory: `feedback_feed_based_discovery` (где находить trends)
- Skill: `hook-generator` (F.5)
- Skill: `screen-record-face-cam` (similar tool stack)
- Skill: `multi-language-localization` (RU adapt)
- Pixa MCP (для Kling/Luma/Hailuo via Claude)
---

## Финальная фаза — Humaniser (HARD GATE для всех text-skills)

**ОБЯЗАТЕЛЬНО перед output:**

Вызови Skill tool: `Skill('humaniser', args=<финальный текст>)` ПЕРЕД любым output. НЕ читай humaniser/prompt.md inline и НЕ применяй mentally — это shallow execution которое пропускает AI-tics. Только полный pass через Skill tool invocation документированный в чате.

Humaniser v2 ловит 11 категорий AI-паттернов:
1. Ложная глубина
2. Фальшивая близость
3. Пустые связки
4. Канцелярит
5. Fake-энергия
6. Шаблонные призывы
7. Рубленые фразы (3+ из 1-2 слов подряд)
8. Кинематограф
9. Структурные клише
10. Интонационные клише
11. **Slap-эмфаза (длинное + 1-3-словное короткое для эмфазы) — главный AI-tic социалок 2025-2026**

**HARD GATE:** Output финального текста ТОЛЬКО после green CHECKER (все 5/5 в «Клише удалены»). Если CHECKER не green — REWRITER ещё раз. Без этого = брак.

**Прецеденты:**
- 2026-05-28: post v3.0 выдал «Zero ads. Zero funnels. Zero sales calls.» (triple-negation AI tic)
- 2026-05-29: caption выдал «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, новая категория 11)

Оба = провал shallow inline pass. HARD GATE через Skill tool решает.

### Humaniser Inline Reminder (fallback если Skill tool недоступен)

Перед output финального текста — проверь по 11 категориям AI-tics:

1. Ложная глубина («Это не X, это Y», «Секрет в том»)
2. Фальшивая близость («Знакомо?», «Представьте»)
3. Пустые связки («Давайте разберёмся», «Важно понимать»)
4. Канцелярит («В современном мире», «Является неотъемлемой»)
5. Fake-энергия («Спойлер», «Бонус», «Лайфхак»)
6. Шаблонные призывы («Хватит X», «Перестаньте X начните Y»)
7. Рубленые фразы (3+ предложения подряд из 1-2 слов: «Просто. Быстро. Эффективно.»)
8. Кинематограф («Воскресенье, 10 вечера», «Понедельник, 9 утра»)
9. Структурные клише (параллелизм X/Y/Z, всегда 3 пункта)
10. Интонационные клише («невероятно простой!», «истина в том»)
11. **Slap-эмфаза**: короткое standalone (1-3 слова) после длинного для эмфазы. SMELL TEST: «можно ли слить через запятую?». YES → SLAP, слить. Исключения: structural separator перед list / hook / punchline finale.

Прецеденты провала которые этот block ловит:
- post v3.0 2026-05-28: «Zero ads. Zero funnels. Zero sales calls.» (triple-negation, cat 7+9)
- caption 2026-05-29: «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, cat 11)

При нахождении любого pattern → REWRITER (переписать) → re-CHECKER → если clean → output.

