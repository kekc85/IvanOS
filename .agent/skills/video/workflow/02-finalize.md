# 02-finalize - Length tier + hook archetype + lang lock + voice register

Стадия 2. Берёт brief от 01a/b/c/d и finalizes параметры: length tier, hook archetype, lang lock, voice register, target platform. После 02 - все ключевые параметры замкнуты.

## Loaded by

- 01a-plan.md / 01b-spark.md / 01c-replication.md / 01d-transcript.md по завершении

## Input

Brief YAML из mode-файла.

## Output

Finalized brief для 03-structure.md:

```yaml
finalized:
  mode: "<inherited>"
  source: <inherited>
  
  # Tier
  length_tier: "<short-15-30s|short-30-60s|short-60-180s|mid-3-10min|long-10-60min>"
  duration_sec_target: <number>
  words_target: <number>
  platforms: ["<reels|shorts|tiktok|youtube>", ...]
  
  # Language
  lang: "ru" | "en" | "both"
  
  # Voice register
  voice_register: "Magician" | "Sage" | "Outlaw"
  voice_register_reason: "<string>"
  
  # Hook archetype
  hook_archetype: "<from references/hook-patterns-8.md>"
  hook_archetype_reason: "<string>"
  
  # Audience
  target_audience_segment: "<inherited or refined>"
  
  # Meaning
  meaning_title: "<inherited>"
  meaning_body_seed: "<inherited or fleshed seed>"
  
  # Replication-specific (if mode C)
  card_md_path: "<...>"  # null if not C
  original_format: "<NN-slug>"  # null if not C
  original_hook: "<...>"  # null if not C
```

## Шаги

### Шаг 1: Resolve length_tier (если auto)

Если length_tier == "auto":
- Mode A: default short-30-60s; если в Карте смыслов помечено «для long-form» - mid-3-10min
- Mode B1/B2: default short-30-60s
- Mode C: из card.md duration_sec (см. 01c-replication.md mapping)
- Mode D: по сложности атома (1 идея + 1 пример → short-30-60s; +2-3 примера → short-60-180s; методология → mid-3-10min)

### Шаг 2: Load tier params

```
Read: <config>.length_tiers[<length_tier>]
```

Извлечь:
- floor_sec / ceiling_sec / target_sec
- words_target_ru / words_target_en
- platforms
- experimental flag (для long-10-60min)

`duration_sec_target` = `target_sec`
`words_target` = `words_target_ru` если lang ru, else `words_target_en`. Для both - оба.

### Шаг 3: Validate experimental flag

Если `length_tier == long-10-60min`:
- Output warning в чат: «Tier long-10-60min experimental в v1.0 - будет корректировка после реальных применений»
- Продолжить, не блокировать

### Шаг 3.5: Validate platform × tier compatibility (HARD GATE)

Reels / Shorts / TikTok принимают максимум ~180 sec. Любой mid-3-10min или long-10-60min tier на этих платформах = FAIL.

Маппинг (config.length_tiers[<tier>].platforms задаёт допустимые):

| Tier | Допустимые платформы |
|---|---|
| short-15-30s | reels, shorts, tiktok |
| short-30-60s | reels, shorts, tiktok |
| short-60-180s | reels, shorts, tiktok |
| mid-3-10min | youtube |
| long-10-60min | youtube |

Алгоритм:
1. Извлечь `requested_platforms` из brief (если пользователь явно сказал «для шорта» / «для рилса» / «для тиктока» / «для YouTube»).
2. Если `length_tier` → `config.platforms` ∩ `requested_platforms` = ∅ → **FAIL**.
3. Explicit message в чат: «Конфликт: tier <tier> не подходит для платформ <requested_platforms>. Допустимые: <tier.platforms>. Либо смени tier, либо смени платформу.»
4. STOP. Не передавать в 03-structure.

Если пользователь явно не указал платформу - взять `config.length_tiers[<tier>].platforms` дефолтом.

**Audit reference:** L4.3 / L5.2 в `audit-video-2026-05-28.md`. Trojan input «30-min видео для Reels» должен FAIL на этом gate.

### Шаг 4: Lock lang

Финализировать lang. Если both:
- Output скрипта будет содержать обе версии в финальном файле (06-output.md)
- Skip translation = false

Если router сказал en но source (Mode C card.md) ru - output warning: «оригинал RU, генерим EN - это перевод+адаптация, не прямой перенос». Тут реакция:
- a) переключиться на ru
- b) продолжить EN с двойным проходом ru→адаптация→en

Default: предложить (a) если не сказано иначе.

### Шаг 5: Pick voice register

Возможные: Magician / Sage / Outlaw (из config.voice_rules.archetypes_allowed).

Алгоритм:
1. Если brief содержит archetype_recommended (Mode A/B/D могут передать) - взять его, проверив archetype_rotation_window:
   - Read track-record последних N видео (N = config.voice_rules.archetype_rotation_window, default 3)
   - Если recommended уже использовался последние N подряд - взять следующий из allowed
2. Если recommendation нет - выбрать по содержанию смысла:
   - Methodology / framework / explanation → Sage
   - Contrarian / провокация / breaking convention → Outlaw
   - Tool reveal / build-with-me / transformation → Magician
3. Mode C - следовать архетипу оригинала если он определим из card.md (часто Outlaw для contrarian Reels)

Сохранить `voice_register_reason` (1 строка обоснование).

### Шаг 6: Pick hook archetype

Из 8 patterns в `references/hook-patterns-8.md`:

| # | Pattern | Когда подходит |
|---|---|---|
| 1 | Timeframe + outcome | Demo / build-with-me / before-after |
| 2 | Demo-first (no intro) | Tool reveal / screen-share |
| 3 | Live-build challenge | Build-with-me с timer |
| 4 | Tool reveal flex | Release / new feature |
| 5 | Before/After visual | Transformation / rebuild |
| 6 | Contrarian | Opinion / spike take |
| 7 | Curiosity gap | Method / framework |
| 8 | Numbered/list | Listicle / framework breakdown |

Алгоритм:
1. Mode C - если card.md имеет hook_original, сохранить и взять тот же pattern (replication mantra «копировать механику, переписывать содержание»)
2. Mode A/B/D - выбрать по содержанию + voice register:
   - Outlaw → Contrarian (6) или Tool reveal flex (4)
   - Sage → Curiosity gap (7) или Numbered (8)
   - Magician → Timeframe (1) или Demo-first (2) или Before/After (5)

Сохранить `hook_archetype_reason`.

### Шаг 7: Strategy paragraph в чат

```
Финализация:
- Tier: <length_tier> (target <target_sec>s, words ~<words_target>)
- Платформы: <platforms>
- Язык: <lang>
- Voice register: <voice_register> (<reason>)
- Hook archetype: <hook_archetype> (<reason>)
- Сегмент аудитории: <segment>
```

### Шаг 8: Handoff к 03-structure.md

## Hard rules

- Никогда не менять length_tier «по ходу» в 03/04/05 - после 02 он locked.
- Archetype rotation - обязательная проверка по track-record. Не повторять последние N подряд.
- Mode C - strongly prefer original hook archetype (это replication, а не reinterpretation).
- Experimental tier long-10-60min - обязательное warning в чат до start.

## Anti-patterns

- Auto-выбор tier по «удобству writer» (модель хочет короче - это не основание)
- Игнор archetype rotation
- Mode C с другим hook archetype чем оригинал - это уже не replication, это re-imagination, должно быть явно
- both lang без явного intent (двойная работа без причины)
- experimental tier без warning