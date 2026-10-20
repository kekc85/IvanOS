---
name: "motion-storyboard"
description: "Motion-design storyboard skill v4.0 — для каждого сегмента ингеста выбирает motion block из catalog v4.0 + Material motion tokens (7 easing curves / 16 duration tokens / 6 spring tokens) + Material transition categories (Container Transform / Shared Axis / Fade Through / Fade). 9 academic families (F-AP / F-DZ / F-CH / F-3D / F-CP / F-UI / F-VX / F-IL / F-PR — School of Motion grounded). 2 motion registers (Standard / Emphasized — Material grounded) + 5 style variants orthogonal axis (Cream-Cinematic / BW-Looper / Dirty-AI / Psychedelic / Vibemarketing). Uses v2.0 Anthropic XML prompt template (reference observations at TOP / verbatim values / Material tokens / self-check). Sits между ui-inventory и replicate-reel в content-factory pipeline. Output: motion-storyboard.md per-segment plan + build_order для replicate-reel. Триггеры: 'разработай motion план', 'storyboard ролика', '/motion-storyboard <ingest-folder>'."
---

# Motion Storyboard — план motion design до сборки ролика

## Когда использовать

После `ingest-reel` и `ui-inventory`, **до** рендер-узла. > ПРИМЕЧАНИЕ 2026-06-10: рендер-узел = `replicate-viral` Фаза 6 (ранее `replicate-reel` [DEPRECATED]). Упоминания «replicate-reel» ниже читать как этот рендер-узел; `build_order[]` идёт в `replicate-viral`. Решает задачу: «каждый сегмент будущего ролика должен ссылаться на конкретный motion block из catalog с явной customization, transition к следующему сегменту и согласованным style sheet».

Без storyboard агенты replicate-reel выбирают motion наугад — теряется polarity discipline и conformance с catalog'ом.

## Входы

Обязательные:
- `<ingest-folder>` — путь к ингесту с `transcript.json` (word-level), `card.md`, `montages/`
- `ui-inventory.md` в `<ingest-folder>` (от skill `ui-inventory`)

Опциональные:
- `--polarity cinematic-3d|bw-looper|hybrid` (default: `cinematic-3d`)
- `--intensity low|medium|high` (default: `medium`) — управляет pacing aggressiveness и количеством visual layers
- `--audience ru|en` (default: `en`) — RU добавляет Cyrillic typography token + screen-record cinematic patterns

## 4 UI source paths (выбор на storyboard этапе)

Каждый сегмент storyboard указывает один из 4 path для UI source:

1. **`real`** — реальная запись софта через `ui-record` skill (Cursor / Claude Code / Lovable / Nelzyagram-app). Pixel-exact UI fidelity. Дефолт когда нужно показать workflow в реальном инструменте.

2. **`synthetic`** — vibe-coded mock через `hyperframes` HTML+GSAP+CSS. Когда нужна абстрактная диаграмма / концепт-визуал / synthetic UI которого нет в реальных tools.

3. **`ai_generated`** — Higgsfield Nano Banana Pro + Seedance 2.0 через replicate-reel Шаг 6.5. Фантазийная метафора / character-consistent сцена / абстрактный концепт.

4. **`hybrid`** (новое) — комбинация: реальная запись `ui-record` MP4 как base layer + overlay `hyperframes` блоки (highlight arrow / pulse ring / hand-drawn circle / device-frame-tilt) поверх. Когда нужно усилить нарратив на реальном UI без потери authenticity.

### Когда выбирать hybrid

- Beat говорит «нажми сюда» / «вот эта кнопка» — base = real workflow recording, overlay = highlight на cursor position
- Showcase реального инструмента в branded mockup frame — base = ui-record output, overlay = device-frame-tilt
- Step-by-step demo с per-step emphasis — base = real recording, overlay = kinetic emphasis caption preset + arrow

### Storyboard output format с ui_source_path

```yaml
segment_3:
  duration_sec: 4.5
  beat: "pivot - конструкторы умирают, вот что вместо"
  ui_source_path: hybrid
  base_layer:
    type: ui-record
    scenario: claude-code-build
  overlay_blocks:
    - block: animated_arrow
      target: cursor_at_2.4s
      params: {direction: down, color: yellow}
    - block: hand_drawn_circle
      target: "Composer input"
      params: {timing: [2.6, 3.4]}
  motion_register: emphasized
  style_variant: vibemarketing
  caption_preset: kinetic
  transition_in: container_transform
  transition_out: fade_through
```

`ui_source_path` поле унаследуется через build_order в replicate-reel.

## Шаги

### Шаг 0 (MANDATORY GATE): Pre-build library inventory check

Перед началом любой storyboard authoring — обязательный inventory existing library.

```bash
bash ~/.business/growth/scripts/pre-build-library-check.sh
```

Decision tree:
1. Existing Rourke-prompted block (O3/B15/O4/C9/A17/G23/J4/O5) fits brief? → reference it directly в build_order, не reinventить с нуля
2. Composing 2-3 existing blocks fits? → compose в storyboard build_order
3. Только если ничего не подходит → custom build (и сразу add к library через `hyperframes` skill)

**Без этого Шага 0 — НЕ переходить к Шагу 1.** Memory: `feedback-library-first-before-build`.

Прецедент по решению автора: showcase v1/v2 — построил simple terminal mock когда O3/B15/G23 already existed rendered. 2 hours wasted на rebuild примитивов.

### Шаг 1: Разбить transcript на семантические юниты

Открыть `transcript.json` (word-level timestamps). Сгруппировать слова в **юниты по 1.5-4 секунды** на natural sentence/phrase boundaries.

Эвристика:
- Юнит закрывается на: точка / запятая / вопрос / paragraph break / >300ms silence
- Юниты <1.5s — слить со следующим; >4s — split на natural break

Сохранить как `units[]` с полями: `index`, `start_ts`, `end_ts`, `text`, `duration`.

### Шаг 2: Классифицировать каждый юнит по 3 осям

Для каждого юнита определить:

**Ось 1 — content_type** (что юнит делает в нарративе):
- `hook` — первые 0-3s, attention grab
- `intrigue` — second hook, paradox / surprise
- `explanation` — step-by-step или concept reveal
- `proof` — number / quote / before-after
- `cta` — finally / next / CTA
- `outro` — wrap-up / brand stamp

**Ось 2 — emotion** (регистр):
- `curious` / `confident` / `surprise` / `urgent` / `contemplative`

**Ось 3 — visual_handle** (что главное в кадре):
- `number` (метрика, $) → A6 / A8
- `mascot` (живой character) → F2
- `ui_mock` (chat, terminal, app) → B2 / B9 / G family
- `typography` (text-driven) → A1 / I5
- `cord` (connection metaphor) → D3
- `scene_opener` (establishing) → B10
- `background_only` (atmospheric) → E1 / E2

### Шаг 3: Map юнит → motion block(s)

Прочитать `~/.business/growth/motion-vocabulary.md` (single source of truth).

Алгоритм выбора:
1. Filter по **polarity** (Cinematic-3D | BW-Looper | universal)
2. Filter по **content_type** соответствию
3. Filter по **visual_handle**
4. Sort by **Tier 1 → Tier 2 → Tier 3** (priority order)
5. Pick top 1 primary + 0-1 overlay (если intensity ≥ medium)

Каждый выбранный block — ссылка на конкретный path в library:
`~/.business/growth/assets/motion-blocks/<family>/<block>/index.html`

**ВАЖНО**: всегда ссылаться на **catalog ID** (A1 / B2 / D3 / F2), НЕ на generic "type-on" / "3D card" — это нарушает 2F catalog conformance в ui-inventory.

### Шаг 3.5: Fallback логика (если block отсутствует в library)

Иногда нужен block которого ещё нет в `~/.business/growth/assets/motion-blocks/`. Не подменять "близким" из другой family — это нарушает 2G fidelity.

Правильный fallback:
1. Записать в storyboard как `gap`: `{ "needed": "C3 Knowledge graph zoom-out", "substitute": null, "action": "custom_build" }`
2. В разделе `## Gaps` storyboard'а перечислить все custom-build needs
3. Replicate-reel должен либо custom-build блок (используя `hyperframes` skill), либо понизить intensity и заменить на closest **same-family-same-tier** (например если C3 отсутствует, но C7 Avatar grid — same family Tier 2 — допустим).

### Шаг 4: Назначить Material transition categories между сегментами

Между unit[i] и unit[i+1] выбрать ОДНУ из 4 канонических Material transition categories:

| Category | Spec | Когда применять |
|---|---|---|
| **Container Transform** | Element morph with shared bounding container | Brand-mark morph between scenes, card → details |
| **Shared Axis X** | Spatial X-axis movement | Whip-pan, step navigation, hierarchical drill |
| **Shared Axis Y** | Spatial Y-axis movement | Vertical reveal, scroll-style transitions |
| **Fade Through** | Outgoing fades out fully, then incoming fades in | Blackout cut, scene-to-scene unrelated content |
| **Fade** | Crossfade with overlap | Related transitions, dialog open/close |

**Duration default per Material tokens** (см. catalog v4.0 Section 1.2):
- Quick transitions (whip-pan, blackout): `dur.medium.1` (250ms) — `dur.medium.2` (300ms)
- Standard scene change: `dur.medium.3` (350ms) — `dur.medium.4` (400ms)
- Cinematic chapter break: `dur.long.2` (500ms) — `dur.long.4` (600ms)
- Hero/outro: `dur.xlong.1` (700ms) — `dur.xlong.2` (800ms)

**Easing default per Material tokens**:
- Enter screen → `ease.standard.decelerate` (`0,0,0,1`) или `ease.emphasized.decelerate` (`0.05,0.7,0.1,1`)
- Exit screen → `ease.standard.accelerate` (`0.3,0,1,1`) или `ease.emphasized.accelerate` (`0.3,0,0.8,0.15`)
- Begin AND end on screen → `ease.standard` (`0.2,0,0,1`) или `ease.emphasized`

**Z-axis EXCLUDED** (Reels плоские, depth-of-field не применяется).

### Шаг 4.5: Register + style variant zoning (если ролик >20s)

v4.0 заменяет старый "polarity" model на **2 motion registers + 5 style variants** (orthogonal axes — см. catalog v4.0 Section 2).

**Motion register zoning** (>20s ролик required):
- Zone 1: **Standard register** (utility motion, `ease.standard`, `dur.short-medium`)
- Transition: Material Fade Through (blackout) или Shared Axis hard cut
- Zone 2: **Emphasized register** (brand/hero motion, `ease.emphasized`, `dur.medium-long`)

**Style variant assignment** (orthogonal axis, может switch separately):
- Cream-Cinematic (Greg / Cursor / Notion) — off-white #F7F4EB, dark forest green, coral accent
- BW-Looper (Dan Koe / Visual Hustles) — pure #000/#FFF, single accent
- Dirty-AI (Ohneis) — grain, bloom, anti-clean, editorial poster
- Psychedelic (Emonee) — saturated electric palette, kinetic morph
- Vibemarketing-Documentary (Riley / Nate) — warm studio, real iPhone, dark green Vibecode brand

**Rule:** style variant ≠ motion register. Cream-Cinematic visual style работает с обоими registers. Switching style variant между zones требует Material Fade Through transition.

### Шаг 5: Style sheet — Material tokens + palette + typography + pacing

**Motion tokens** (catalog v4.0 Section 1, single source of truth):

```yaml
motion_tokens:
  easing:
    standard: "cubic-bezier(0.2, 0, 0, 1)"
    standard_decelerate: "cubic-bezier(0, 0, 0, 1)"
    standard_accelerate: "cubic-bezier(0.3, 0, 1, 1)"
    emphasized: "M3 path curve"
    emphasized_decelerate: "cubic-bezier(0.05, 0.7, 0.1, 1)"
    emphasized_accelerate: "cubic-bezier(0.3, 0, 0.8, 0.15)"
    linear: "cubic-bezier(0, 0, 1, 1)"  # ONLY для progress bars / loops
  duration:
    short_1: 50      # subliminal flicker
    short_2: 100     # cursor feedback
    short_3: 150     # badge punch start
    short_4: 200     # button press
    medium_1: 250    # whip-pan, blackout
    medium_2: 300    # scene transition fade
    medium_3: 350    # standard reveal
    medium_4: 400    # UI zoom
    long_1: 450      # card morph
    long_2: 500      # hero reveal start
    long_3: 550      # brand stamp
    long_4: 600      # long fade
    xlong_1: 700     # outro fade
    xlong_2: 800     # cinematic establish
    xlong_3: 900     # full-screen transition
    xlong_4: 1000    # cinematic only
  spring:
    fast_spatial:    { damping: 0.9, stiffness: 1400 }
    fast_effects:    { damping: 1.0, stiffness: 3800 }
    default_spatial: { damping: 0.9, stiffness: 700 }
    default_effects: { damping: 1.0, stiffness: 1600 }
    slow_spatial:    { damping: 0.9, stiffness: 300 }
    slow_effects:    { damping: 1.0, stiffness: 800 }
  stagger:
    tight: 40        # blur reveal
    standard: 80     # SplitText word-by-word
    loose: 150       # bullet list
    dramatic: 300    # sequential card flip
```

**Palette** (style variant defaults):
- Cream-Cinematic: cream `#f5f1e8` + forest `#2a3528` + coral `#d97757` + amber `#ff9b3d`
- BW-Looper: warm-white `#faf8f5` + ink `#181818` + ОДИН accent (`#e63946` Dan Koe red default)

**Typography** (style variant defaults):
- Cream-Cinematic: EB Garamond serif italic + Inter sans UI
- BW-Looper: PP Editorial New uppercase tracking + sketch handwritten

**Pacing** (catalog v4.0 Section 7.4 NN/g grounded):
- Single animation event: 100-500ms (NN/g range)
- Entrance:Exit ratio 1.2-1.5x (entrance longer)
- Response time hard threshold: ≤100ms after trigger
- Linear easing = automatic fail (NN/g verbatim)
- Segment average duration 1.5-2.0s (автор pacing)
- Hook ≤1.5s
- Static text >2.0s без inner motion = брак

### Шаг 6: Build order для replicate-reel

Сформировать `build_order[]` — список compositions которые replicate-reel будет рендерить и собирать в timeline.

Каждый composition entry:
- `id` — `comp-001-hook`
- `start_ts` / `end_ts` — позиция в final timeline
- `block_id` — A1 / B2 / D3 / etc
- `block_path` — конкретный путь к library block
- `customization` — `data-*` attrs (text content, colors, timings)
- `overlay_blocks` — список optional overlay block_ids (если intensity ≥ medium)
- `transition_from_prev` — H1 / H2 / D6 / etc
- `audio_units` — какие transcript units покрывает (для voice-generate)

## Output structure

`<ingest-folder>/motion-storyboard.md`:

```markdown
# Motion Storyboard — <ingest-id>

## Style sheet
- Polarity: <cinematic-3d|bw-looper|hybrid>
- Palette: H7.<set-name> (<color tokens>)
- Typography: H8.<pair-name>
- Pacing target: <2-4s|3-5s> per beat
- Audience: <ru|en>

## Per-unit plan

| # | TS | text | content_type | emotion | visual_handle | primary_block | overlay_blocks | transition_in | customization |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.0-2.8 | "If you take notes..." | hook | curious | typography | A1 | E1 (bg) | — | text_italic="take notes" |
| 2 | 2.8-5.5 | "Claude just became..." | intrigue | confident | mascot | F2 | A1 | H1 | character_shape=asterisk |
| ... | | | | | | | | | |

## Gaps (custom builds needed)
- C3 Knowledge graph zoom-out — needed for unit 7, no library block yet, action=custom_build via `hyperframes` skill

## Build order (для replicate-reel)
```yaml
- id: comp-001-hook
  block_id: A1
  block_path: ~/.business/growth/assets/motion-blocks/A-typography/A1-serif-italic-emphasis-typeon
  start_ts: 0.0
  end_ts: 2.8
  customization:
    data-text-prefix: "If you "
    data-italic-word: "take notes"
    data-text-suffix: ""
  overlay_blocks: []
  transition_from_prev: null
  audio_units: [1]

- id: comp-002-intrigue
  block_id: F2
  ...
```

## Review hook
После рендера каждого composition — invoke `ui-inventory` Level 1-4 review с этим storyboard как primary spec для 2F catalog conformance + 2G motion-block fidelity. Overall ≥80 threshold per composition. <80 — fix и re-render, не переходить к следующему.
```

## v2.0 Anthropic XML prompt template (MANDATORY format для каждого segment)

REPLACES Rourke v1.0 markdown template. Empirically validated по решению автора на G23 A/B test — v2.0 produces visibly more reference-faithful, numerically-specified, industry-grounded compositions. Reference: catalog v4.0 Section 6 + `~/.business/growth/authority-research/anthropic-prompt-eng.md` Section 5.

**Why v2.0 over v1.0 (empirical):**
- v1.0 (Rourke) НЕ требовал `<reference_observations>` с frame paths → G23 v1 fabricated unrelated dark macOS Finder UI which не существует в reference reel at all
- v2.0 forces reference observations AT TOP → fabrication невозможна, model reproduces actual reference composition

**Каждое описание per-unit motion plan ОБЯЗАНО следовать XML structure:**

```xml
<role>
You are a motion designer producing a HyperFrames sub-composition for a vertical Reel.
Output: deterministic seek-driven HTML, render as MP4 1080x1920 30fps.
</role>

<reference_observations>
  <ingest_id>2026-MM-DD-VIDEOID</ingest_id>
  <segment timestamp="X.Xs-Y.Ys" type="hook|intrigue|explanation|proof|cta|outro">
    <visual_handle>verbatim observable description of dominant element</visual_handle>
    <author_face>visible | PIP bottom-left 35% scale | absent</author_face>
    <key_motion_event t="X.Xs">verbatim measurement (scale 1.0→1.4 over 400ms, ease cubic-bezier(0.2,0,0,1))</key_motion_event>
    <reference_frame_path>/Users/.../ingest/.../scene-frames/f_XXX.jpg</reference_frame_path>
  </segment>
</reference_observations>

<style_block>
  <palette>
    <bg_primary>#F4F0EA</bg_primary>
    <accent>#D97757</accent>
    <text_primary>#181818</text_primary>
  </palette>
  <typography>
    <headline_font>"EB Garamond", serif</headline_font>
    <body_font>"Inter", sans-serif</body_font>
    <mono_font>"Geist Mono", monospace</mono_font>
  </typography>
  <motion_tokens>
    <!-- Material grounded — см. Шаг 5 для full token list -->
    <ease_standard>cubic-bezier(0.2, 0, 0, 1)</ease_standard>
    <ease_emphasized_decelerate>cubic-bezier(0.05, 0.7, 0.1, 1)</ease_emphasized_decelerate>
    <dur_short_3>150ms</dur_short_3>
    <dur_medium_2>300ms</dur_medium_2>
    <dur_long_2>500ms</dur_long_2>
    <stagger_standard>80ms</stagger_standard>
  </motion_tokens>
  <polarity_register>Standard | Emphasized</polarity_register>
  <style_variant>Cream-Cinematic | BW-Looper | Dirty-AI | Psychedelic | Vibemarketing</style_variant>
</style_block>

<acts>
  <act index="1" timestamp="0.0s-1.2s" duration_ms="1200">
    Title fade-in with scale 0.95→1.0 + opacity 0→1, easing ease_emphasized_decelerate, total dur_long_2 (500ms)
  </act>
  <act index="2" timestamp="1.2s-4.0s" duration_ms="2800">
    Real product UI (см. reference_frame f_007.jpg) zoom-in scale 1.0→1.4 over dur_medium_4 (400ms), ease_standard
  </act>
</acts>

<per_element>
  <element id="headline" type="text" act="1">
    Position: x=50%, y=15%, anchor=center
    Font: headline_font 64px, color text_primary, italic for words tagged <em>
    Animation: opacity 0→1 + scale 0.95→1.0, dur_medium_3 (350ms), ease_emphasized_decelerate
    Disney principles applied: Timing (#9), Slow In/Out (#6), Anticipation (#2)
  </element>
  <element id="ui_screenshot" type="image" act="2">
    Asset path: /Users/.../assets/screenshots/n8n-workflow-detail.png
    Initial state: scale=1.0, x=center, y=center
    Final state: scale=1.4, translateY=-40px
    Animation: dur_medium_4 (400ms), ease_standard
    Material transition: Container Transform (preview→detail)
  </element>
</per_element>

<examples>
  <example>
    <reference>Greg Isenberg cf6WEZUVbEI at t=2.1s</reference>
    <pattern>Identical zoom+slide pattern; using для visual_handle continuity</pattern>
  </example>
</examples>

<output_schema>
  Output a single HTML file with:
  1. <style> block declaring CSS custom properties для всех motion tokens (referenced by name)
  2. <body> with elements positioned per per_element specs
  3. <script> registering animations via window.__hfAnime / GSAP timeline seekable
  All animations MUST respond to hf-seek events (deterministic playback).
  Fonts: explicit `"EB Garamond", serif` strings (no CSS var() references — HF deterministic font mapper не разрешает var() font-family references).
</output_schema>

<self_check>
Before finalizing, verify (6-criterion gate):
- [ ] All numerical values verbatim (no "subtle"/"smooth"/"gentle"/"snappy")
- [ ] All motion tokens reference style_block (no inline cubic-bezier/ms outside style_block)
- [ ] Each element has explicit duration / easing / Disney principles list
- [ ] Reference frames cited with explicit file paths
- [ ] Output is deterministic under hf-seek (no setTimeout, no Date.now)
- [ ] No generic AI aesthetics (no Inter as default, no purple gradients, no Cream house-style default unless explicitly chosen as style_variant)
</self_check>
```

**Anti-patterns banned (v2.0 explicit):**
- ❌ Generic adjectives ("subtle", "smooth", "gentle", "snappy") — banned, replace verbatim numerical values
- ❌ Negative instructions ("don't make abstract") — replace positive ("use real product UI from reference frame f_007.jpg")
- ❌ Polarity-only specification — model defaults to house style. Mandatory: explicit style_variant + verbatim hex
- ❌ Missing `<self_check>` section — model finishes без verify, ships incomplete
- ❌ Inline tokens outside `<style_block>` — single source of truth violated, downstream renders inconsistent
- ❌ Reference data after instructions — Anthropic data shows queries at end +30% quality. Reference observations MUST be AT TOP.

**Verbatim specifics rules (preserved from v1.0):**
- Точные hex (`#EF6820`, не "orange")
- Точные durations (Material token references like `dur_medium_3` = 350ms)
- Точные stagger (Material token references: `stagger_standard` = 80ms)
- Точные easings (Material cubic-bezier values, not GSAP shorthand like `power3.out`)
- Точные размеры (`150-200px`, `1080×1920`, `30fps`)

**Кинематографичный язык (preserved):**
- "camera zooms in / sweeps upward / pans left / pulls back"
- "bursts into existence" / "explodes out in loose 3D scatter"
- "spring release" / "elastic bounce-in" / "radial glow breathes"

## Anti-patterns

1. **Случайный motion без catalog ID** — каждый primary_block должен быть конкретный ID из vocabulary (A1, B2, D3, F2 etc), не описание ("type-on text" / "3D card"). Без ID невозможна 2F conformance check.
2. **Mixing polarities без hybrid contract** — alternating Cinematic-3D ↔ BW-Looper на каждом юните = расфокус. Hybrid допустим только zoned (≥8s zones) с явным transition.
3. **Substitute из чужой family при отсутствии block в library** — лучше gap + custom_build документация, чем "C3 заменим на A1 чтобы было". Compromises 2G fidelity check.
4. **Custom build без catalog entry** — если делаем новый block — после render обновить `motion-vocabulary.md` с новой записью (или хотя бы flag в gaps section как "needs catalog entry"). Иначе vocabulary стагнирует.
5. **Игнорировать H5 perf rule** — все animations только transform + opacity, никаких layout-trigger properties (width / height / top / left animated). Linter ui-inventory это поймёт, но проще не нарушать с начала.

## Output

```
<ingest-folder>/
  motion-storyboard.md      # ⭐ финальный план
  motion-storyboard.json    # машинно-читаемая версия build_order (опционально для replicate-reel)
```

## Связано

- `ingest-reel` — производит transcript.json + montages (входы)
- `ui-inventory` — v4.0 4-gate inventory (Type / Brand specifics / Talk-track timing / Pre-render manifest) + v4.0 5-level review (WCAG / Disney+Material / NN/g / Reference Fidelity / PDCA). См. ui-inventory SKILL.md
- `replicate-reel` — потребляет motion-storyboard.md как primary spec для HF composition assembly
- `produce-reel` — orchestrator, вызывает motion-storyboard между ui-inventory и replicate-reel
- **Catalog v4.0:** `~/.business/growth/catalog-v4-skeleton-draft.md` (transitional, finalize в Phase 2 mapping). Frozen `motion-vocabulary.md` v3.1 — reference only
- **Authority foundations:**
  - `~/.business/growth/authority-research/disney-12.md`
  - `~/.business/growth/authority-research/material-motion.md` (motion tokens single source)
  - `~/.business/growth/authority-research/apple-hig.md`
  - `~/.business/growth/authority-research/anthropic-prompt-eng.md` (v2.0 prompt template)
  - `~/.business/growth/authority-research/school-of-motion.md` (9 academic families)
  - `~/.business/growth/authority-research/qa-frameworks.md` (WCAG + NN/g)
- Library: `~/.business/growth/assets/motion-blocks/<family>/<block>/`
- `hyperframes` — для custom build блоков из gaps section