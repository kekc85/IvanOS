---
name: "pattern-extraction"
description: "C.4 Reverse-engineer viral content patterns from corpus. Jack Butcher style (50K tweets analyzed). Extract hooks / structures / what works для replication в авторском voice"
---

# Pattern Extraction (C.4)

## Когда использовать

Когда нужно **systematically извлечь паттерны** из корпуса виральных pieces (свои best / конкурента / категории). Output = reusable templates для future content production.

Reference: **Jack Butcher Visualize Value** - reverse-engineered tweet rules из 50,796 tweets, built **Pattern** product поверх анализа.

## Когда running

- **Monthly**: analyze свои топ 20-30 pieces last 30 days → find what works у тебя
- **Quarterly**: deep dive 50+ pieces у топ-3 конкурентов → extract their winning patterns
- **Before campaign**: niche-specific corpus analysis для new product/cash event launch
- **Voice-train update**: refresh C.5 Claude Project с новыми patterns

## Что extract

| Element | Что искать |
|---|---|
| **Hook patterns** | First 1.5-3 sec / 1-2 lines structure |
| **Length distribution** | Optimal piece length для virality в этой нише |
| **Pacing** | Beat structure (видео = sec breaks / text = paragraph breaks) |
| **CTA patterns** | Type + position + wording |
| **Visual elements** | Image vs video / static vs animated / colors |
| **Engagement bait** | Bookmarks vs likes vs comments triggers |
| **Topic clusters** | Что resonates conceptually |
| **Voice markers** | Phrases / cadence / tone specifics |
| **Anti-patterns** | Что НЕ работает (low performers) |

## Шаги extraction

### Шаг 1: Define corpus
- **Source**: свои / конкурент / niche broad
- **Time window**: last 30/90/365 days
- **Volume**: 20-50 pieces minimum для statistical signal
- **Platform**: один primary (e.g. only Reels или only X-threads)
- **Performance threshold**: top X% by engagement / views

### Шаг 2: Collect data
- **Свои pieces**: native analytics export (Нельзяграм / YouTube / X Analytics)
- **Чужие pieces**: manual scan через feed / Virale / Web research
- **Per piece data points**:
  - Date published
  - Platform
  - Hook (first 1.5-3 sec / 1-2 lines)
  - Length (sec / words)
  - Engagement metrics (views / likes / saves / shares / comments)
  - CTA (если есть)
  - Visual format
  - Topic / theme

### Шаг 3: Pattern detection через Claude
Paste corpus в Claude prompt:
```
Analyze this corpus of [N] [pieces / Reels / X-threads / posts] from [creator / niche].

Identify:
1. Hook patterns - top 5 recurring structures
2. Length distribution - optimal length для virality
3. Pacing patterns - beat structure для top performers
4. CTA patterns - type + position + wording
5. Voice markers - phrases / cadence specifics
6. Topic clusters - what resonates conceptually
7. Anti-patterns - what consistently underperforms

For each pattern report:
- Pattern name
- Specific examples (3+ pieces from corpus)
- Performance correlation (views / engagement)
- Why it works (psychological mechanism)
- How to replicate в авторском voice + категория вайбмаркетинг
```

### Шаг 4: Synthesize templates
Из patterns → **reusable templates**:
- Hook templates (with [variables] для adaptation)
- Length / pacing guidelines
- CTA templates
- Voice consistency markers

### Шаг 5: Update artifacts
- **C.5 Voice-trained Claude Project**: add new pattern examples в knowledge base
- **Hook library memory** (`project_viral_hook_library_2026`): добавить newly discovered patterns
- **Skills update**: если pattern достаточно reusable - create new dedicated Skill

### Шаг 6: A/B testing plan
- Pick 2-3 new patterns to test next week
- Track performance vs baseline
- Iterate

## Гвардрейлы

- Минимум 20 pieces для statistical signal (меньше = noise)
- Один platform / format в одном extraction run (не смешивать Reels + X-threads)
- Voice автора при template synthesis (категория вайбмаркетинг)
- БЕЗ копирования чужой voice (только structure)
- Privacy: если используешь чужие pieces - public sources only
- Track patterns over time (не one-off snapshot)

## Output format

```
**Corpus**: [source / time window / volume / platform]
**Performance threshold**: [top X% by metric]

**Pattern 1: [name]**
- Structure: [exact template with [variables]]
- Examples in corpus: [3+ pieces with metrics]
- Performance correlation: [view/engagement uplift vs baseline]
- Why it works: [psychological mechanism]
- Replication template в voice автора:
  "[template with [variables] для filling]"

**Pattern 2: [name]**
[same structure]

[... 5-10 patterns total]

**Length / pacing findings**:
- Optimal length: [X-Y sec/words]
- Beat structure: [pattern]

**CTA findings**:
- Most effective: [pattern]
- Position: [start / middle / end]

**Voice markers** (если analyzing свой corpus):
- Recurring phrases: [list]
- Cadence specifics: [observations]

**Anti-patterns** (low performers):
- [pattern что НЕ работает]
- [reason]

**Action items**:
- [ ] Update C.5 Claude Project knowledge base
- [ ] Add patterns to viral hook library memory
- [ ] Create new Skill для most reusable pattern
- [ ] A/B test 2-3 new patterns в next week
```

## Что НЕ делаем

- Pattern extraction на <20 pieces (noise > signal)
- Mixing platforms / formats в одном run
- Copying чужой voice (structure only, не tone)
- Static patterns (rerun monthly / quarterly)
- Без verification на свежий A/B test

## Связано

- Memory: `project_viral_hook_library_2026`
- Memory: `project_ai_avatar_cheung_pipeline` (Cheung Claude Project на 20+ top tweets)
- Memory: `feedback_strategy_copy_faster_more_better`
- C.5 Voice-trained Claude Project: `.business/processes/voice-trained-claude-project.md`
- Skill: `hook-generator` (использует patterns from this skill)
- Skill: `adaptation` (использует patterns для same-format adaptation)
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

