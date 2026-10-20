---
name: "before-after"
description: "Video sub-format #5 - Before/After transformation reel. Old web/app/pitch vs AI-rebuilt version. Highest stop-scroll rate Нельзяграм май 2026. Riley Brown variants"
---

# Before/After Transformation (Video Sub-format #5)

## Когда использовать

Когда можешь демонстрировать **visual transformation** через AI tool. Reference: Riley Brown variants ("I rebuilt this $50K website in 11 minutes"), Sebastien Jefferies clone demos.

**Highest stop-scroll rate Нельзяграм май 2026** - visual contrast hooks instantly.

## Структура

```
Length: 15-25 sec optimal (peak engagement)
Aspect: 9:16 vertical
Visual: split OR wipe transition

Sequence:
- 0:00-0:01 - Hook + "Before" frame (ugly v1, problem stated)
- 0:01-0:03 - Smooth transition (split or wipe)
- 0:03-0:18 - "After" reveal + tool used + quick how-to
- 0:18-0:25 - Result + CTA
```

## Hook patterns для этого формат

Из viral hook library 2026:
1. **Timeframe + outcome**: "I rebuilt this $50K website in 11 minutes"
2. **Before/After split-screen**: visual ugly → polished within 1 sec
3. **Forbidden knowledge**: "The agency doesn't want you to know..."
4. **Demo-first**: tool already running на screen + voiceover

## Стек tools

| Этап | Tool | Cost |
|---|---|---|
| Recording before | Screen Studio / Tella | $20-25/мес |
| Rebuilding в Lovable/Bolt/Cursor | Lovable $20/мес / Bolt / Cursor $20/мес | varies |
| Final transition + cuts | CapCut (free) или DaVinci через Jumper MCP | бесплатно |
| Captions | CapCut auto или Submagic | бесплатно / $16/мес |

## Workflow

### Шаг 1: Find "Before" candidate
Source:
- Свой старый product / pitch / landing
- Ученика project (с разрешения) - "до" версия
- Open-source ugly landing / app (no copyright issues)
- Trending бренд / startup с outdated design (careful с trademark)

### Шаг 2: Record "Before"
- Screen Studio / Tella session
- Show problem visually (ugly UI / slow load / confusing copy)
- 5-10 sec footage с zoom-in на pain points

### Шаг 3: Rebuild в AI tool
- Lovable / Bolt / Cursor с Claude Code
- 10-30 min build = enough для demo (don't optimize endlessly)
- Record build process в Screen Studio
- Capture key moments: prompt → response → final

### Шаг 4: Record "After"
- Same product/landing новой версии
- Show same features улучшенными
- 5-10 sec footage с zoom на key improvements

### Шаг 5: Edit transition
**Option A: Split-screen** (instant visual contrast):
- Left: before, right: after, same moment
- 0.5 sec вращение / wipe
- Каждая половина same length

**Option B: Wipe transition** (sequential reveal):
- 0:01 - before frame
- 0:01-0:03 - smooth wipe right-to-left
- 0:03 - after frame appears

### Шаг 6: Add captions Hormozi-style
- Word-by-word bold yellow/white outlined
- Hook caption first 1.5 sec
- Tool name + time displayed prominently

### Шаг 7: Distribution
- Нельзяграм Reel primary
- YouTube Shorts cross-post
- TikTok cross-post (uniqalizer для multi-account если применимо)
- (опционально) RU dub через C.3

## Гвардрейлы

- Voice автора (если voice over - authentic talking)
- Real demo (не staged fake)
- Show actual prompts + steps в build process
- Hook captures contrast в 1.5 sec
- БЕЗ em-dash в captions
- Privacy: blur user data / customer names если applicable
- Permission если используешь чужой product как "before"

## Output format

```
**Topic**: [Before/After transformation idea]
**Target length**: 15-25 sec
**Hook variant**: [from F.5 hook-generator]

**Before specs**:
- Source: [own old / student / open-source / brand-trending]
- Problem visible: [ugly UI / slow / confusing copy / etc]
- Recording: 5-10 sec footage
- Tool: Screen Studio / Tella

**AI rebuild specs**:
- Tool used: [Lovable / Bolt / Cursor / Claude Code]
- Estimated build time: [10-30 min]
- Key prompts to demonstrate: [list 2-3]
- Recording: Screen Studio session

**After specs**:
- Same features улучшенные visually
- Recording: 5-10 sec footage
- Zoom на key improvements

**Edit specs**:
- Transition type: split-screen ИЛИ wipe
- Hook caption first 1.5 sec: "[exact text]"
- Bold captions Hormozi-style word-by-word
- Tool name + time displayed prominently
- Total length: 15-25 sec
- Aspect: 9:16 vertical

**Production checklist**:
- [ ] Before footage captured
- [ ] AI rebuild completed + recorded
- [ ] After footage captured
- [ ] Permissions secured (если чужой product)
- [ ] Transition edited
- [ ] Captions added
- [ ] Final length check

**Distribution**:
- Primary: Нельзяграм Reel
- YouTube Shorts cross-post
- TikTok cross-post
- (через uniqalizer): multi-account Нельзяграм если применимо
- (опционально): RU dub через C.3
```

## Что НЕ делаем

- Faked / staged demos
- Misleading "before" (искусственно ugly)
- Trademark violations (чужие бренды без permission)
- Long demos (более 30 sec теряет engagement)
- Generic CTA в финале
- Em-dash в captions

## Связано

- Memory: `project_viral_hook_library_2026` (Reels hook patterns)
- Memory: `feedback_strategy_copy_faster_more_better`
- Skill: `hook-generator` (F.5)
- Skill: `screen-record-face-cam` (similar tool stack)
- Skill: `cut-from-long-form` (если длинный rebuild record)
- Skill: `multi-language-localization` (RU adapt)
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

