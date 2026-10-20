---
name: "ai-avatar-news"
description: "Video sub-format #4 - AI-avatar news read. Cheung pipeline. Daily volume без записи. Wispr Flow + Claude Project + HeyGen Avatar V + ElevenLabs PVC + Kling 3.0"
---

# AI-Avatar News Read (Video Sub-format #4)

## Когда использовать

Daily volume без необходимости лично записывать видео. Reference: Rowan Cheung (Нельзяграм 0→160K за 12 мес).

Использовать после accumulate baseline trust на других sub-formats (W3+ или позже). Не для cold start - audience нужен base trust.

## Stack

| Этап | Tool | Cost |
|---|---|---|
| Voice dictation walk | Wispr Flow | $12/мес |
| Script generation | Claude 3.7 Sonnet через Custom Project | $20/мес |
| Avatar generation | HeyGen Avatar V (15-сек clone) | $29-60/мес |
| Voice clone | ElevenLabs PVC (Russian PVC trained на 30-60 min) | $22-99/мес |
| B-roll | Kling 3.0 | $0.10/sec ≈ $1-3 per short |
| Assembly | Descript или manual editor | $24/мес |

**Total**: ~$120-250/мес

## Workflow

### Шаг 1: Воice dictation walk (morning, 2 hours)
- Walk + Wispr Flow voice-to-text → raw transcripts
- 5-7 scripts/posts из одной прогулки
- Темы: AI news Claude releases / Skool updates / vibemarketing observations / contrarian takes

### Шаг 2: Claude Project drafts
- Paste raw transcripts в Claude Project автора (trained на его top pieces)
- Prompt: "make a post/script в моём voice"
- Output: 90% draft

### Шаг 3: Human edit 10%
- Hook punch (first 1.5-3 sec)
- Format / pacing adjustment
- авторский angle / contrarian twist
- Remove generic AI language

### Шаг 4: HeyGen Avatar V render
- Paste edited script
- Render 60-90 sec vertical short (3-5 min processing)
- Avatar settings:
  - **face <30% screen time** (uncanny valley prevention)
  - Russian language если для RU аудитория

### Шаг 5: B-roll generation (Kling 3.0)
- Generate visuals matching script topics
- AI tool demos / abstract concepts / news visuals
- ~$0.10/sec - средне $1-3 per short

### Шаг 6: Assembly + captions (Descript)
- Combine avatar + B-roll
- Add bold captions (Hormozi style word-by-word)
- Subtitle-first для silent viewers
- Final length: 30-90 sec vertical

### Шаг 7: Quality control gates
- Lipsync glitches check
- Accent drift в Russian (особенно на >60 sec)
- B-roll mismatch
- Hook strength в first 1.5 sec
- AI labeling (Нельзяграм optional but expected для AI-niche)

## Гвардрейлы

- Voice автора (Brand DNA + lexicon)
- Russian PVC mandatory (instant clone дрифтит)
- Avatar face <30% screen time
- B-roll dominates frame
- Каждый clip ≤60 sec для accent stability
- Hook punch human-edited (не AI auto)
- Contrarian / opinion angle всегда human source
- БЕЗ em-dash в captions
- Lexicon: Нельзяграм / Дубайск / контент-завод

## Output format

```
**Topic**: [input from morning walk]
**Length target**: [30-60 sec / 60-90 sec]
**Language**: [EN / RU]

**Edited script**:
[hook 1.5-3 sec]
[main content body]
[CTA closing]

**Avatar render specs**:
- Tool: HeyGen Avatar V
- Voice: ElevenLabs PVC Russian (если RU) / English
- Length: [X sec]
- Face time: <30% (will be supplemented by B-roll)

**B-roll specs** (Kling 3.0):
- Shot 1 (0-3 sec): [description]
- Shot 2 (3-10 sec): [description]
- ...
- Estimated cost: $[X]

**Assembly notes**:
- Captions: Hormozi-style word-by-word
- Hook overlay: [first 3 sec text]
- Final aspect: 9:16 vertical

**Distribution**:
- Нельзяграм Reel
- YouTube Shorts
- TikTok
- (если RU): TG <твой-хэндл>

**QC checklist**:
- [ ] Lipsync clean
- [ ] No accent drift (especially Russian)
- [ ] B-roll matches script topics
- [ ] Hook in 1.5 sec
- [ ] AI label (если на TikTok / Нельзяграм)
```

## Failure cases (избегать)

- **No prior audience trust** - dies без base
- **Avatar face >30% screen** - uncanny valley
- **Generic AI rehash** без contrarian take - slop label
- **Wrong niche** - UGC / lifestyle / vulnerability content feels uncanny
- **Over-automation** - human 10% edit non-negotiable
- **Accent drift на Russian** - PVC mandatory, instant недостаточен

## Связано

- Memory: `project_ai_avatar_cheung_pipeline` (полный context)
- Memory: `feedback_ru_en_content_adaptation_rules` (для Russian adaptation)
- Voice-trained Claude Project: `.business/processes/voice-trained-claude-project.md`
- MCP: HeyGen MCP / Pixa MCP (для Kling)
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

