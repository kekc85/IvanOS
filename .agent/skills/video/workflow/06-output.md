# 06-output - Final script + headline + production handoff brief

Стадия 6. Финальный output. Формирует:
- Готовый script в формате для копи/voice-generate
- Headline / caption overlay
- Production handoff brief (какой downstream skill + что передать)
- Archive в `<config.paths.script_archive_dir>`

## Loaded by

- 05-review.md по завершении (после явной фразы «3 слоя пройдено, флагов нет»)

## Input

Reviewed draft из 05.

## Output

### Output 1: В чат пользователю (Telegram-friendly plain text)

```
=========================================
SCRIPT
=========================================

[script_full - готов к копи в voice-generate]

=========================================
CAPTIONS (overlay)
=========================================

[каждая caption_line на отдельной строке, ALL CAPS для shorts]

=========================================
HEADLINE
=========================================

Primary: [headline]
Alt A: [headline]
Alt B: [headline]

=========================================
PRODUCTION HANDOFF
=========================================

Recommended skill: <skill name>
Length tier: <tier>
Lang: <lang>
Aspect: <9:16|16:9>

Hook visual brief:
[1-2 строки описание визуала для первых 3 sec]

B-roll needs:
[list или «none»]

Caption style:
[Hormozi-style word-by-word bold yellow/white outlined | static | none]

Tool stack:
[recommended tools для production]

=========================================
META
=========================================

Mode: <A|B1|B2|C|D>
Voice register: <archetype>
Hook archetype: <pattern>
Source: <launch_id / spark / ingest_id / надиктовка>
Track-record entry: добавлено в examples/track-record-video.md
```

### Output 2: Archive файл

```
Write: <config.paths.script_archive_dir>/<YYYY-MM-DD>-<short-slug>.md
```

Структура файла:

```yaml
---
created: <YYYY-MM-DD>
mode: <...>
length_tier: <...>
lang: <...>
voice_register: <...>
hook_archetype: <...>
source_type: <sense_map|spark|card_md|transcript>
source_ref: <launch_id / video_id / transcript word_count>
audience_segment: <...>
production_handoff:
  recommended_skill: <...>
  status: pending|in_progress|done
---

# <Headline primary>

## Script (для voice-generate)

<script_full>

## Captions (overlay)

<captions_full, one per line>

## Headline alternatives

- Primary: <...>
- Alt A: <...>
- Alt B: <...>

## Production handoff brief

[full brief как в Output 1]

## Meta

[full meta]

## Track-record link

См. `examples/track-record-video.md` запись <date>-<short-slug>.
```

### Output 3: Track-record update

```
Edit: ~/.claude/skills/video/examples/track-record-video.md
```

Добавить запись в формате:

```
## <YYYY-MM-DD>-<short-slug>

- Mode: <...>
- Tier: <...>
- Lang: <...>
- Voice register: <...>
- Hook archetype: <...>
- Source: <...>
- Audience segment: <...>
- Maxwell Ross: 9/9
- Hook Strength: PASS (N ретраев)
- Handoff: <recommended_skill> (status: pending)
- Outcome: TBD (заполнить после производства и публикации)
```

## Production handoff map (детальный)

| Tier | Intent / Mode | Recommended skill | Что передаём |
|---|---|---|---|
| short-15-30s/30-60s/60-180s | Mode A/B + intent «снять самому face-cam» | `screen-record-face-cam` | script + caption_overlay_first_3s + demo steps brief |
| short | Mode A/B + intent «trend-jack» | `split-screen-trend-jack` | script + top-half AI prompt brief + bottom-half facecam script |
| short | Mode A/B + intent «без записи / daily volume» | `ai-avatar-news` | script + B-roll shots list (Kling 3.0) + caption style |
| short | Mode A/B + intent «before/after AI rebuild» | `before-after` | script + before footage brief + AI rebuild prompts + after brief |
| short | Mode C (replication) | `replicate-reel` | script + spec.captions[] structure + overlay_timeline hints + speaker_audio_src plan (`--with-voice`) + speaker_video_src plan (`--with-avatar`) |
| mid-3-10min | Любой mode + intent «cuts после publish» | (post-publish) `cut-from-long-form` | full script + headline + chapter map (для Reap MCP context) |
| mid-3-10min | Любой mode + intent «native YT mid» | manual production (нет skill в v1.0) | script + headline + chapter map + thumbnail brief |
| long-10-60min | Любой mode | manual production (нет skill в v1.0) | full script + chapter map (5-9 sections) + headline + thumbnail brief + outro |

## Шаги

### Шаг 1: Format Output 1 (чат)

Plain text, без таблиц, без угловых скобок-плейсхолдеров (только реальный контент).

### Шаг 2: Generate slug

slug = first 4 значимых слова headline_primary, kebab-case, ru→translit или en as-is.

Example: «Конструкторы умирают» → `konstruktory-umirayut-vot-chto-vmesto`

### Шаг 3: Write archive

```
Write: <config.paths.script_archive_dir>/<YYYY-MM-DD>-<slug>.md
```

Если папка не существует - создать (`mkdir -p`).

### Шаг 4: Update track-record

```
Edit: ~/.claude/skills/video/examples/track-record-video.md
```

Append-only.

### Шаг 5: Production handoff invocation suggestion

После output - explicit suggestion в чат:

```
Готово. Следующий шаг - production:

Запусти: `/<recommended_skill> <slug>` или скопируй script вручную.
```

[Если Mode C + replicate-reel:]

```
Или сразу: `/replicate <ingest_id>` - он подхватит этот скрипт автоматически в v1.1 (в v1.0 - копи руками в Шаг 4 replicate-reel).
```

### Шаг 6: Open archive в IDE (если применимо)

```bash
# macOS: open · Windows: start "" · Linux: xdg-open · универсально: ~/.claude/skills/_shared/bin/open-file
open "<config.paths.script_archive_dir>/<YYYY-MM-DD>-<slug>.md"
```

Memory `feedback_always_open_artifacts` - автор не кликает, нужно открыть через `open`.

### Шаг 7: Backlog в конце

В конце ответа - full backlog задач из `tasks/today.md` (memory правило `feedback_always_show_backlog`).

## Hard rules

- Archive файл обязателен (без него теряется history)
- Track-record update обязателен (catch_rate metric)
- Open артефакт через `open` (memory правило)
- Backlog в конце (memory правило)

## Anti-patterns

- Output без archive (script одноразовый)
- Track-record skip (catch_rate ломается)
- Production handoff без конкретного skill name (vague)
- Skip backlog в конце ответа

## Связано

- `examples/track-record-video.md` - accumulating catch_rate
- Downstream skills - все из production handoff map