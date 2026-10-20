# Template library — каталог + params

Каждый шаблон = HyperFrames-композиция `templates/<id>/index.html` + `params.json`. Seek-driven, без RNG (сиды позиций — в разметку). Канвас 1080×1920. Watermark по умолчанию.

## Build status (v1.0)

Все 10 шаблонов v1.0 — ✅ **built + render-validated** (lint 0 errors, determinism чисто, реальный рендер 1080×1920, 2026-06-01). Контактный лист рендеров: `~/.business/growth/motion-elements/2026-06-01-pilot-comment-pop/`.

| id | Статус | Приоритет |
|---|---|---|
| `comment-pop` | ✅ render-validated (+ audio e2e: 9 SFX-треков вмиксованы нативно) | high |
| `count-up-ticker` | ✅ render-validated (number roll по timeline-прогрессу) | high |
| `kinetic-caption` | ✅ render-validated (per-word slam) | high |
| `code-terminal` | ✅ render-validated (type-on по прогрессу + caret) | high |
| `before-after-wipe` | ✅ render-validated (clip-path wipe + светящийся делитель) | high |
| `ui-comparison-bar` | ✅ render-validated (bars + winner pulse) | high |
| `chat-bubbles` | ✅ render-validated (typing-dots + пузыри) | high |
| `price-odometer` | ✅ render-validated (roll + strike + badge) | high |
| `scribble-callout` | ✅ render-validated (stroke-dashoffset draw-on; для богаче — HF hand-drawn block через `hyperframes-registry`) | high |
| `screen-zoom-punch` | ✅ render-validated (punch-in + spotlight mask) | high |

**v1.1 defer** (medium/low из каталога эффектов): lower-third · progress-bar · glitch/RGB-split · emoji-burst-standalone · VHS-timeline · bar-race · velocity-stinger · waveform · map-route. Каждый — новая папка `templates/<id>/` без правки движка.

> Принцип расширения: сначала доказать петлю реальным рендером (де-риск), потом штамповать по образцу. Все params в каждом `templates/<id>/index.html` подставляются скиллом из брифа; тексты/числа/логотипы — РЕАЛЬНЫЕ (context-gap gate), не дефолты из шаблона.
> $0 SFX-пак: `bash scripts/make-starter-sfx.sh sfx` (синтетика FFmpeg для мгновенного e2e), для финала заменить на CC0 (`knowledge/free-audio-sources.md`).

## Шаблоны и params

### `comment-pop` — каскад комментов/лайков/эмодзи (max stop-scroll, social proof)
`params.json`: `comments[]` (`{avatar_initial, name, text}`), `emoji_burst[]`, `accent_color`, `bg`, `stagger`, `seed`, `duration`, `_out`, `_with_audio`.
SFX-профиль: каждое появление коммента → `pop`; финальный всплеск эмодзи → `impact`; подложка lo-fi/tech.

### `count-up-ticker` — odometer/roll-up числа (climax-beat)
`params.json`: `from`, `to`, `prefix`/`suffix` (`$`, `%`, `MRR`), `duration`, `digit_roll` (odometer|fade), `strikethrough_old`, `clink_particle`, `accent_color`.
SFX: per-increment `tick`; финальный снап → `ding`/`clink`.

### `kinetic-caption` — word-by-word highlight/slam под бит/озвучку (+completion)
`params.json`: `text`, `words[]` или `transcript_json`, `highlight_color`, `punch_scale`, `font`, `beat_timestamps[]`.
SFX: на каждый слэм слова → `impact` (тихо) на бите; бит-онсеты из librosa.

### `code-terminal` — печать кода/команд с курсором, syntax-цвета, «collapse → один промпт»
`params.json`: `lines[]`, `prompt_line`, `output_lines[]`, `char_speed`, `theme`, `caret_blink`.
SFX: печать → `typewriter` (мягко, не на каждый символ); enter/run → `click`; вывод → `whoosh`.

### `before-after-wipe` — clip-path wipe «было → стало» со светящимся делителем
`params.json`: `before_img`, `after_img`, `direction`, `divider_glow_color`, `wipe_duration`.
SFX: проход делителя → `whoosh`; фиксация «после» → `impact`.

### `ui-comparison-bar` — 2-3 стороны (Old vs AI / Tool A/B/C), SVG-логотипы, winner pulse
`params.json`: `items[]` (`{label, logo_svg, score, color}`), `winner_index`, `pulse_color`.
SFX: заливка баров → `riser`; победитель пульс → `ding`.

### `chat-bubbles` — DM/iMessage по пузырю с typing-dots
`params.json`: `messages[]` (`{side, text, delay}`), `typing_indicator`, `per_char_type`, `theme` (imessage|tg).
SFX: появление пузыря → `pop`; нотификация → `ding`.

### `scribble-callout` — маркер-кружок/стрелка/подчёркивание draw-on
HF ships hand-drawn block → ставить `npx hyperframes add <block>` (`hyperframes-registry`).
`params.json`: `shape` (circle|arrow|underline), `position{x,y}`, `color`, `roughness`, `draw_duration`.
SFX: рисование → `whoosh` (маркер).

### `screen-zoom-punch` — punch-in на кнопку/строку + dim-mask spotlight
`params.json`: `media_src`, `target{x,y,scale}`, `origin`, `dim_mask`, `ease`.
SFX: панч-ин → `whoosh` + `impact` в точке фокуса.

### `price-odometer` — slot-machine роллинг цен/скидок/MRR (urgency, оффер-climax)
`params.json`: `from`, `to`, `currency`, `strikethrough_old_price`, `discount_pct`.
SFX: ролл → `tick`×N; фикс цены → `clink`.

## Правила построения HTML-композиции (все шаблоны)
1. Один корневой `[data-composition-id]`, канвас 1080×1920.
2. Анимация — GSAP timeline, зарегистрированная по конвенции HF. Лейблы на акцентных твинах (для аудио-cue).
3. Никакого `Math.random`/`setInterval`/`Date.now` — позиции/джиттер пред-вычислены из `seed` в разметке.
4. Числа/счётчики — интерполяция от прогресса timeline, НЕ `setInterval`.
5. Safe-zone: контент в пределах top/bottom 130px, left/right 80px.
6. Watermark-слой `<твой-хэндл>` bottom-right (если не `--no-watermark`).
7. Видео-слои `muted playsinline`; звук — отдельные `<audio>` (см. `prompts/03-audio.md`).