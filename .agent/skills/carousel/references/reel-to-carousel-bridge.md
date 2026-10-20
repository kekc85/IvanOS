# reel-to-carousel-bridge

> Mapping вертикального видео (Reel / Short / TikTok) в static carousel 8-12 slides. Загружается когда `mode=reel-to-carousel` (флаг `--reel <url>` или фразы «перегони рилз в карусель»). Источник - `.business/growth/carousel-research/2026-05-28/bucket-e-reel-to-carousel.md` + skill `ingest-reel`.

## Что такое reel-to-carousel

Переосмысление виральной vertical видео-единицы в static deck 8-12 slides. **Не скриншоты из видео**, а структурное preconversion с self-contained slides (каждый читается без контекста).

**Когда применять:**

- Viral Reel другого автора (после `ingest-reel`) - replicate в карусель формат
- Свой Reel - distribute на LinkedIn как PDF + IG как parallel формат
- Long-form контент → дистрибуция: Reel + Carousel + TG-пост + Newsletter (POSSE)
- Reels отгорают за 48-72 часа, carousels живут неделями evergreen

**Чем НЕ является:**

- Не скриншоты из видео в slide-deck
- Hook slide ≠ frame 0:00 видео (обычно blank / face mid-blink / camera adjustment)
- Не дословный transcript - переосмысление в bomber-style copy
- Не motion - чистая static (Motion carousel = v1.1)

## Card.md schema от ingest-reel

`ingest-reel` skill производит `card.md` + ассоциированные файлы. Carousel skill читает следующие поля:

```yaml
card.md sections:
  transcript:                           # Whisper word-level + full text
    - transcript.json                   # word-by-word timing
    - transcript_full.txt               # plain readable
  
  frames:                               # extracted video frames
    - grid.jpg                          # overview всех ключевых frames
    - 0:01.jpg / 0:03.jpg / ...         # individual frames (full-res)
  
  ui_inventory:                         # ui-inventory.md если был запущен
    - GATE_A: type classification (face % / UI % / PIP Y/N)
    - GATE_B: brand specifics inventory (real products mentioned)
    - GATE_C: talk-track word-level pinning
    - GATE_D: pre-render manifest
  
  meta:
    - author (handle, platform)
    - duration_seconds
    - hook_text (если экстрактнули)
    - cta_text (последние 2-3 сек transcript)
    - tags / categories
```

## Card.md → carousel mapping

| Card.md component | Используется для |
|---|---|
| `transcript.json` (word-level Whisper) | Beat-segmentation + per-slide text generation |
| `transcript_full.txt` | Полный контекст для structure промпта (Hook→Context→CTA arc) |
| `frames/grid.jpg` | Outline какие моменты доступны как hero images |
| `frames/0:0X.jpg` (full-res) | Hero images per slide |
| `ui-inventory.md` GATE B | UI screenshots per slide (Cursor / Claude Code / n8n / Lovable / Stripe) |
| `ui-inventory.md` GATE A (face % / UI %) | Hook slide pattern selection (face-cam → motion-triple, UI-heavy → screenshot hero) |
| `hook_text` (если экстрактнули) | Hook slide typography copy (с переписыванием) |
| CTA verbal (последние 2-3 сек) | CTA slide reason copy (с переписыванием в slide-стиль) |

## Beat extraction rules

**1 beat = 1 slide** - каноническое правило (с оговорками cluster / split).

Transcript режется на **beats** через смысловые границы:

- Смена тезиса
- Reveal / punchline
- Before → After переход
- Question → Answer pair
- List item (если транскрипт = listicle)

**Verbal filler вырезается полностью.** Talking points «так вот», «значит», «в общем», «вообще» - не переносятся. Slide должен быть bomber, не разговорный.

**Density rule:** один beat = одна мысль = один slide. Никогда не пихать 2 идеи в 1 slide.

### Когда 1 beat = 1 slide (default)

- Listicle Reel («5 tools для X») → 1 tool = 1 slide
- Numbered methodology Reel («3 шага к Y») → 1 шаг = 1 slide
- Story Reel с явными scene cuts → 1 scene = 1 slide

### Когда cluster (2-3 beats → 1 slide)

- Talking-head Reel с filler словами → группировать смежные beats
- Reel > 60 сек когда beats > 12 - иначе overflow карусели
- Verbal repetition / parenthetical asides → merge в основной beat

### Когда split (1 beat → 2 slides)

- Dense beat с before/after contrast → 1 slide before, 1 slide after
- Beat с code / UI showcase → 1 slide statement, 1 slide screenshot
- Hook beat (первая фраза + payoff) → split на hook slide + context slide

## Slide count по длине Reel

| Reel длина | Slides | Логика |
|---|---|---|
| 10-15 сек | 6-8 slides | Каждый beat ≈ 1.5-2 сек видео = 1 slide. Tight pacing. |
| 30 сек | 8-10 slides | Sweet spot. 1 beat = 1 slide с 1-2 cluster cases. |
| 45 сек | 9-11 slides | Между sweet spot и full expansion. |
| 60 сек | 10-12 slides | Full expansion. Допустимы 2 slides на один dense beat. |
| 60-90 сек | 12 slides cap | IG cap = 10, LinkedIn = 20, но вовлечённость падает после 13. Stick to 12. |
| <10 сек (mini-Reel) | 4-6 slides | Не растягивать искусственно до 8. Filler slides убивают вовлечённость. |

**Default для skill:** 9 slides (median sweet spot 8-12, LinkedIn 7 даёт +18%).

## Кривая вовлечённости trick (2026)

ER падает после slide 3, восстанавливается на slide 8+. Распределение нагрузки:

- **Slides 1-3:** max hook punch, front-load value. Самые важные идеи здесь.
- **Slides 4-7:** «valley» - основная masa контента, depth. Допустимо более dense текстом.
- **Slides 8-10:** payoff + bonus insight + CTA. Saves / shares accumulate здесь.

## Frame selection priority

3 типа frames извлекаются по приоритету:

1. **Reveal frames** (приоритет 1) - момент когда автор показывает результат (final UI, dashboard, before/after). High-res, кропается в hero slide.

2. **Motion-triple frames** (приоритет 2, Justin Welsh trick) - 3 frames «start of movement / middle / end» с автором (pointing / smiling) → ставятся горизонтально на hook slide с «Play» иконкой поверх. Микро-сторителлинг в статике, намекает на видео-источник, создаёт curiosity.

3. **UI screenshots** (приоритет 3) - если в Reel показывали инструмент - pure UI frame без автора, добавляется annotation (стрелка / обводка / callout).

**Frame quality gate:** все extracted frames должны быть в full resolution (не preview thumbnails). На hero slide frame занимает 60-70% площади, оставшиеся 30-40% - typography overlay.

**Decision tree для hook frame:**

```
есть reveal frame с high contrast?     → use it
нет, есть UI screenshot с numbers?     → use it
нет, есть face-cam с motion?           → motion-triple Welsh pattern
нет ничего качественного               → pure typography hook на solid color
```

## Hook frame patterns (4 канонических)

### Pattern 1 - Question hook

Verbal вопрос из Reel → крупный bold typography на чистом фоне.

- Source: «Что если LinkedIn ER зависит от 1 переменной?»
- Slide: full-bleed text 80-120 pt, solid color background

### Pattern 2 - Stat hook

Цифра-bomber из видео → один крупный number на slide.

- Source: «78% saves приходят на slide 8+»
- Slide: number «78%» 200 pt + supporting text 36 pt

### Pattern 3 - Before/After hook

Split-screen на hook slide (left = до, right = после).

- Source: face-cam «вот старый процесс / вот новый»
- Slide: vertical split 50/50, left frame + right frame, headline overlay центрировано

### Pattern 4 - Motion-triple grid hook (Welsh)

3 frames автора в grid + «Play» button overlay + headline. Намекает на видео-источник.

- Source: face-cam Reel с автором pointing / talking
- Slide: 3 horizontal frames + play icon center + headline bottom

В 2026 на hook есть **0.25 секунды** чтобы остановить scroll - hook slide design идёт ПЕРЕД copy.

## Loss compensation matrix

Что теряется при переходе video → static + как компенсировать.

| Теряется в Reel | Компенсация в carousel |
|---|---|
| Movement (cuts, zoom, motion) | Bold typography weight contrast, размер шрифта 80-120 pt на hook |
| Voice tone / emotion | ALL CAPS для emphasis, italics для интонации, color на key слова |
| Music / beat / rhythm | Visual rhythm через repeating template grid (8 slides одного формата) |
| Sound effects (whoosh, ding) | Layered visuals - frame + sticker + arrow + highlight overlay |
| Real-time pacing | Slide numbers внизу («3/9»), progress dots - visual «next beat coming» |
| Face-cam authority | 1-2 slides с фото автора + signature line «- автор» |

## CTA conversion rules

Verbal CTA «follow me / like this / save it» в видео → отдельный CTA slide в конце.

**Структура:**

- **Soft CTA в середине** (slide 5-6): «Сохрани, чтобы вернуться» - встроенная фраза на content slide
- **Hard CTA на последнем slide:** button-style design + reason («Подпишись - на этой неделе разберу X / Y / Z»)

**CTA должен быть action-specific под жанр:**

| Жанр Reel | CTA pattern |
|---|---|
| Educational / methodology | Ask SAVE («Сохрани этот разбор для возврата») |
| Controversy / spiky take | Ask COMMENT («Согласен / не согласен - в комменты») |
| Diagnostic / problem reveal | Ask CLICK / DM («Комментарий "разбор" - пришлю ссылку») |
| Tool roundup | Ask SAVE («Сохрани список инструментов») |
| Funnel slide / lead-gen | Ask FOLLOW («Подпишись на <твой-хэндл>») |
| Newsletter content | Ask SUBSCRIBE (LinkedIn) |

Carousels с явным CTA slide делают +20-30% ER vs без.

## Edge cases (6 типов Reel)

### Case A - Pure face-cam Reel (no UI)

- Hook: motion-triple (3 frames автор pointing / talking) + bold typography
- Content slides: typography-heavy на solid color (brand)
- Frames использовать sparingly - 2-3 face shots максимум в 10 slides
- Risk: carousel становится «wall of text»
- Mitigation: каждый 3-й slide - visual break (quote card / stat callout / icon)

### Case B - Pure UI Reel (screen recording)

- Hook: hero UI screenshot + question typography overlay
- Content slides: UI screenshots с annotations (стрелки / callouts / highlights)
- Frames extraction: брать key UI states (start / mid-action / final result)
- Risk: UI без context - читатель не понимает что это
- Mitigation: slide 2 - «Что ты смотришь: [Tool name + 1-line context]»

### Case C - Split-screen Reel (face + UI)

- Hook: split-screen image (face left / UI right) - точно как в видео
- Content slides: alternate face slides (commentary) и UI slides (demo)
- Frames extraction: pairs (face frame + corresponding UI frame at same timestamp)
- Risk: чрезмерное чередование разрывает narrative
- Mitigation: 2 UI slides подряд + 1 face slide (3:1 ratio как обычно в demo Reels)

### Case D - Reel с heavy motion graphics / VFX

- Hook slide: можно extract single iconic motion frame если есть peak (zoom-in conclusion)
- Иначе - generate hook from scratch (pure typography)
- VFX motion loss compensation: typography weight + color gradients
- Risk: статика чувствуется «плоской» vs оригинал
- Mitigation: добавить мини-progress bar внизу slide («3/9») - implies sequence / motion

### Case E - Reel без явного CTA

- Не оставлять carousel без CTA slide - генерить из контекста
- Default fallbacks:
  - «Подпишись на <твой-хэндл> - на этой неделе разбор X»
  - «Сохрани, чтобы вернуться»
  - «Комментарий "X" - пришлю Y в DM»

### Case F - Reel < 10 сек (mini-Reel)

- 4-6 slides достаточно, НЕ растягивать искусственно до 8
- Risk: filler slides убивают вовлечённость
- Mitigation: лучше короткий tight carousel чем растянутый

## Self-contained slides правило

Каждый slide должен читаться **без контекста** окружающих. Тест:

> Если зритель зашёл в feed на slide 5 (mid-carousel), он должен понимать что это про что.

Проверка для каждого slide:

- [ ] Есть micro-headline или icon обозначающий тему slide
- [ ] Текст self-explanatory (не «как мы говорили выше»)
- [ ] Visual element passes контекст (UI с подписью tool name, не «какой-то экран»)
- [ ] Slide number («3/9») есть как orientation

Если slide требует context из предыдущего - переписать в self-contained формат.

## Chain с produce-reel / replicate-reel

| Trigger | Skill | Действие |
|---|---|---|
| Reel URL впервые | `ingest-reel` | Создать card.md (transcript + frames + ui-inventory) |
| Карусель из существующего card.md | `carousel` mode D | Mapping card → slides + visual brief + caption |
| Replicate Reel в авторском голосе | `replicate-reel` | Создать новый Reel в голосе автора |
| End-to-end Reel + carousel parallel | `produce-reel --also-carousel` | Orchestrator chain'ит ingest → replicate-reel + carousel parallel |
| Карусель видео уже сделана, нужен video | `produce-reel` отдельно | Не chain - паралельный output |

**produce-reel с флагом `--also-carousel`** запускает carousel skill на том же card.md после render Reel. Один источник → два output (video + static deck) для distribution.

## Когда НЕ использовать reel-to-carousel mode

- Reel без UI / numbers / клиентских кейсов = неинтересно в static (используй другой формат - post / spiky-one-liner)
- Reel - чистая comedy / meme без educational density (carousels плохо несут юмор)
- Reel < 5 сек - недостаточно beats для разворота в 6+ slides
- Reel где главная ценность - motion / soundtrack / VFX (loss compensation не вытягивает)

## Цепочка reel-to-carousel (по шагам)

```
1. card.md path verified (от ingest-reel)
   ↓
2. parse card.md → extract transcript + frames + ui-inventory
   ↓
3. detect Reel type (face-cam / UI / split-screen / mixed) → GATE A from ui-inventory
   ↓
4. beat-segmentation (transcript → 8-12 beats, filler вырезан)
   ↓
5. structure (beats → Hook / Context / Insight × N / CTA arc)
   ↓
6. frame-mapping (frames → which slide hero)
   ↓
7. copy generation per slide (Ivan voice + bomber style + self-contained rule)
   ↓
8. design brief per slide (typography + color + layout + REAL elements)
   ↓
9. review (3 слоя + carousel-specific gates CR-G1...G9)
   ↓
10. output bundle (slide-by-slide spec + caption + assets manifest)
```

## Review gates специфичные для reel-to-carousel

Дополнительно к 9 общим carousel gates в `workflow/04-review.md`:

- **RC-G1:** Each slide self-contained? (читается без контекста других)
- **RC-G2:** Beat-density ≤1 idea per slide?
- **RC-G3:** Hook slide stops scroll? (typography weight test, contrast ratio ≥7:1)
- **RC-G4:** Slide count appropriate для Reel длины? (по таблице conversion 5.3)
- **RC-G5:** Filler verbal вырезан? (нет «так вот», «значит», «в общем»)
- **RC-G6:** CTA slide action-specific под жанр? (educational=save / controversy=comment)
- **RC-G7:** Frames в full resolution (не preview)?
- **RC-G8:** Reel type detection → hook pattern matches? (face-cam → motion-triple, UI → screenshot hero)

Если хоть один fail - вернуться к Pass 2 visual brief или Pass 3 caption в `workflow/03-write.md`.

## Default reel-to-carousel spec для автора

- Slide count: 9 (median sweet spot)
- Hook pattern: auto-detect по GATE A (face-cam → motion-triple, UI → reveal screenshot)
- Beat extraction: filler-stripped, 1 beat = 1 slide default
- CTA: «Подпишись на <твой-хэндл>» (default) или per genre rules
- Selfie slides: 1-2 (slide 1 hook + slide 8 pre-CTA, Acosta pattern)
- Slide numbers: «1/9», «2/9»... in bottom-right corner
- Typography: 60 pt headline / 36 pt body, sans-serif
- Output: text spec + visual brief + caption RU (+ EN если bilingual флаг)