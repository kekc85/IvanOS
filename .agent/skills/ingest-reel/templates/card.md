---
url: {URL}
platform: {Нельзяграм Reel | TikTok | YouTube Short}
author: {Display Name (@handle)}
uploader_id: {ID}
upload_date: {YYYY-MM-DD}
duration_sec: {N}
views: {N or n/a}
likes: {N}
comments: {N}
language: {ru | en | auto-detected}
ingested: {YYYY-MM-DD}
ingest_skill_version: 1.1
format_classification:
  primary: "{NN-slug из .business/growth/format-library-vertical-2026.md или 'new'}"
  secondary: []                  # ["NN-slug", ...] для гибридов, иначе []
  confidence: high               # high | medium | low
  reasoning: "{1-2 предложения: что в кадре + транскрипте однозначно указало на этот формат. Если 'new' — обосновать почему ни один из 20 не подходит и предложить новый slug в виде NN-slug}"
  gate_a:                        # сырые наблюдения из GATE A inventory, на основе которых сделана классификация
    face_pct: {0-100}            # % кадра занимает лицо/тело автора (по grid.jpg)
    ui_pct: {0-100}              # % кадра — UI/screen recording/external media
    pip: {true | false}          # есть ли picture-in-picture
    split: "{none | horizontal-50-50 | horizontal-30-70 | vertical | triple | other}"
    captions_dominant: {true | false}  # большие burnt-in captions — главный визуал
---

# {Headline: что это за ролик в одной строке}

## Caption / Description

> {Caption from platform, original language}

## Транскрипт ({whisper model}, {detected lang})

```
{Полный транскрипт}
```

## Структура (timestamps)

- **0.0–{X.X}s - Hook:** {описание первых 1.5-3 секунд, что цепляет}
- **{X.X}–{Y.Y}s - Development:** {основная часть, перечисление / разбор / демонстрация}
- **{Y.Y}–{end}s - CTA:** {призыв в конце, follow / comment X / link in bio}

## Технические приёмы

- **Format type:** см. `format_classification.primary` в шапке. Полное описание формата — в `.business/growth/format-library-vertical-2026.md`. Не дублировать здесь.
- **Layout:** {fullscreen / split-screen 50/50 / split-screen 30/70 / PiP corner / variable composition}
- **Speaker presence:** {camera / heygen-style avatar / off-screen voice / none}
- **Overlay content:** {что показано сверху speaker'а: screen recording / Higgsfield / Kling / static slides / charts / другие}
- **Captions style:** {шрифт, размер, позиция, цвет, анимация}
- **Music / sound:** {trending audio / original VO / silence / mix}
- **Transitions:** {hard cut / whip pan / zoom / morph / другое - частота}
- **Color / visual signature:** {доминантная палитра, освещение, ракурс}
- **Pacing:** {N элементов в секунду / средняя длительность шота}

## Метрики и сигналы (если доступны)

- **Likes:** {N}
- **Comments:** {N}
- **Saves:** {N if visible in screenshot or info.json}
- **Save:Like ratio:** {ratio} - {>0.1 = high save rate, library content / <0.05 = entertainment}
- **Hook strength estimate:** {1-10} - {обоснование на основе первых 3 секунд}

## Применимость для контент-завода автора

{2-4 предложения: как именно этот формат / эта идея может работать в нише вайбмаркетинга. Конкретные сценарии, не абстрактно. Учитывать что автор - соло, минимум времени на продакшн, EN+RU. Учитывать память `feedback_strategy_copy_faster_more_better` - same-format reproduction.}

**Риски / caveats:**
- {если есть юр./reputational риски - copyright, конкурент в кадре, тематика}
- {если требует high-production setup - отметить}

## Spec для replication (вход для фазы 2 - Remotion / HeyGen)

```json
{
  "format_type": "{из каталога}",
  "duration_target_sec": {N},
  "hook_strategy": "{type of hook}",
  "voice_script_brief": "{краткий бриф для генератора сценария в voice автора через skill adaptation}",
  "narrative_arc": [
    {"sec": "0-{X}", "beat": "hook", "content": "..."},
    {"sec": "{X}-{Y}", "beat": "development", "content": "..."},
    {"sec": "{Y}-end", "beat": "cta", "content": "..."}
  ],
  "visual_layers": [
    {
      "track": "speaker",
      "source": "heygen | camera | none",
      "position": "bottom-half | center | corner-br",
      "crop": "9:16 | square | etc"
    },
    {
      "track": "overlay",
      "source": "screen-recording | higgsfield-batch | kling-prompt | static-slides",
      "position": "top-half | fullscreen-cuts | corner",
      "timing": "[(start_sec, end_sec, asset_id), ...]"
    }
  ],
  "transitions": [
    {"at_sec": "...", "type": "hard-cut | whip | zoom"}
  ],
  "captions": {
    "style": "submagic-bold | minimal-white | custom",
    "position": "center | bottom-third",
    "color": "#FFFFFF",
    "background": "transparent | black-stroke"
  },
  "music": {
    "type": "trending-audio | original-vo | mubert-prompt",
    "prompt": "..."
  }
}
```

## Главный insight

{Один абзац: что в этом ролике самое ценное для системы автора. То что нельзя пропустить. Если есть meta-trick (как растущий counter в первом ингесте) - обозначить.}

## Файлы

- `{video_id}.mp4` - исходное видео
- `audio.wav` - 16kHz mono для Whisper
- `transcript.txt` / `transcript.json` - Whisper output
- `{video_id}.info.json` - yt-dlp metadata
- `frames/` - кадры {fps}fps ({N} штук)
- `grid.jpg` - обзорная сетка