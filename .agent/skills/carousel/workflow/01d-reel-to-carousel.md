# Workflow 01d - Mode D: Reel-to-carousel (из card.md ингеста)

**Назначение:** взять card.md от `ingest-reel`, пересобрать в carousel structure.
**Вход:** URL рилза ИЛИ путь к существующему card.md
**Выход:** carousel brief с slide-by-slide mapping → передача в `01-finalize.md`

---

## Шаг 1 - Получить card.md

**Если дан URL:**
1. Проверить `config.paths.reel_ingest_dir/<video_id>/card.md` - существует?
2. Если НЕТ - chain в `ingest-reel` skill. Дождаться завершения.
3. Если ДА - продолжить.

**Если дан путь:** проверить файл валиден (имеет transcript + frames sections).

---

## Шаг 2 - Read card.md

Извлечь 4 секции:

1. **Transcript** (Whisper output) - talking points с timestamps
2. **Frames** - пути к JPG + descriptions
3. **UI inventory** - какие UI элементы / продукты показаны
4. **Author + meta** - handle, length, engagement если known

`mandatory_reads.card_md = true`.

---

## Шаг 3 - Identify Reel type через GATE A reuse

Использовать `ui-inventory` GATE A:

- **Face-cam dominant** (face % > 70) → carousel typography-heavy + 1-2 author face slides
- **UI-cam dominant** (UI % > 70) → carousel screenshot-led
- **Hybrid PIP** → carousel mixed (text + screenshot pairs)
- **Pure UI** (no face) → carousel = pure screenshots + typography overlay

→ `brief.reel_type = "<face | ui | hybrid | pure-ui>"`.

---

## Шаг 4 - Beat-mapping transcript → slides

**Правило 1 beat = 1 slide.**

```yaml
beats:
  - beat_id: 1
    timestamp: "00:00-00:03"
    type: "hook"
    verbatim: "<точная фраза из Whisper>"
    associated_frame: "<frame на timestamp>"
    
  - beat_id: 2
    timestamp: "00:03-00:08"
    type: "context"
    verbatim: "..."
    associated_frame: "..."
```

**Beat types:** hook / context / discovery / reward / cta.

**Filler removal:** «так вот», «вообще», «значит» - вырезать.

---

## Шаг 5 - Slide count по длине Reel

| Reel length | Slide count target |
|---|---|
| 15s | 6-8 |
| 30s | 8-10 |
| 60s | 10-12 |

Если beats > target → cluster соседних. Если < → split.

---

## Шаг 6 - Frame selection per slide

Приоритет:

1. **Reveal frames** - final UI / dashboard / before-after (HIGHEST)
2. **Motion-triple grid** (Welsh trick) - 3 frames «start/mid/end» на hook + «Play» icon overlay
3. **UI screenshots** - pure UI + аннотации (стрелка / обводка)
4. **Face frame** - если автор показал эмоцию / pointing gesture
5. **Typography-only** - если frame слабый

**Quality gate:** full resolution (не превью). Hero frame занимает 60-70% площади slide.

---

## Шаг 7 - Loss compensation matrix

| Loss | Compensation |
|---|---|
| Movement | Bold typography weight, 80-120pt на hook |
| Voice tone | ALL CAPS / italics для интонации |
| Music / beat | Visual rhythm через repeating template |
| Sound effects | Layered visuals (frame + sticker + arrow) |
| Real-time pacing | Slide numbers (3/9), progress dots |
| Face-cam authority | 1-2 slides с фото автора + signature line |

В `brief.loss_compensation` отметить применённые техники.

---

## Шаг 8 - CTA conversion

Verbal CTA из Reel → static:

- **Soft CTA** (slide 5-6): «Сохрани, чтобы вернуться»
- **Hard CTA** (последний slide): button-style + reason

Жанр-specific:
- Educational → ask SAVE
- Контроверсия → ask COMMENT
- Diagnostic → ask CLICK / DM
- Funnel → ask FOLLOW

---

## Шаг 9 - Передача в finalize

```yaml
brief:
  mode: "reel-to-carousel"
  topic: "<из card.md title или Reel hook>"
  family: "reel-to-carousel"
  reel_url: "<URL>"
  card_md_path: "<path>"
  reel_type: "<face | ui | hybrid | pure-ui>"
  beats: [...]
  frame_inventory: {...}
  loss_compensation: [...]
  cta_strategy: "<save | comment | click | follow>"
  source_quotes: [<verbatim beats[*].verbatim>]
```

Перейти в `workflow/01-finalize.md`.

---

## Принципы

1. **Card.md = source of truth.** Не дополнять, не выдумывать.
2. **1 beat = 1 slide.** Cluster/split с оговорками.
3. **Reveal frames приоритет.** Final UI / dashboard / payoff frames всегда выше generic.
4. **Loss compensation mandatory.** Что теряется - компенсация в brief.
5. **Self-contained slides.** Каждый slide читается без контекста.