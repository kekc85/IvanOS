# Template: before-after (статичный)

Transformation visual в одном кадре. Proof через визуальный contrast.

Reference: Pat Walls (Starter Story), UX/UI redesign showcases, Riley Brown rebuilds.

ВАЖНО: video before-after - отдельный skill `before-after` (video sub-format). Этот - только static.

## Brief structure

```yaml
type: before-after
sub_type: <split-vertical | split-horizontal | slider | annotated-side-by-side | stack>

before_state:
  description: "<что было>"
  visual: "<screenshot / photo path or описание>"
  label: "<≤3 слова в кадре, e.g., 'Раньше'>"

after_state:
  description: "<что стало>"
  visual: "<screenshot / photo path or описание>"
  label: "<≤3 слова в кадре, e.g., 'Сейчас'>"

delta:
  what_changed: "<concrete delta - 1 sentence>"
  honesty_check: "Same angle / lighting / scale?"
  consent: "<если чужой before-after - permission?>"

composition:
  split_direction: "<vertical | horizontal | stack>"
  divider: "<thin line / blur / hard split>"
  position: "50/50 split OR weighted ratio (e.g., 40/60 if after more impactful)"

text_on_image_verbatim:
  before_label: "<≤3 слова>"
  after_label: "<≤3 слова>"
  caption_overlay: "<0-1 слово оптional>"

palette:
  before: "muted / desaturated"
  after: "vibrant / saturated"
  contrast_check: "<7:1+ для labels>"
```

## Sub-type details

### Split vertical
- Canvas разделён по vertical center line
- Left = before, Right = after
- Labels в углах respective sides
- Standard для side-by-side reveal

### Split horizontal
- Canvas разделён по horizontal center line
- Top = before, Bottom = after
- Labels внутри каждого половинки
- Better для tall artifacts

### Slider visualization
- Curtain / slider drawn over canvas
- Hint of «slider» metaphor
- Both states visible через slider
- More dynamic feeling

### Annotated side-by-side
- 2 images side-by-side
- Arrows / labels указывают что changed
- More analytical
- 3-5 annotations max

### Stack
- Две картинки одна над другой
- Stark visual difference
- Каждая «full frame» в своей половине

## Tool prompt

**Figma (recommended):**
```
1. Canvas 1080x1080
2. Split frame по center:
   - Left/Top: before screenshot/image
   - Right/Bottom: after screenshot/image
3. Thin divider line - 2px stroke, accent color
4. Label на каждом side:
   - Font: Inter Bold 32-48pt
   - Color: contrast vs respective half
   - Position: corner или center
5. Optional caption overlay
6. Export PNG 2x retina
```

**Photopea для photo composites:**
- Same approach с masks
- Better для photo blending

## Caption guidance

- Length: ≤200 chars
- Role: setup before / context after
- Hook patterns:
  - RU: «<X> → <Y>» / «От <X> к <Y> за <время>»
  - EN: «<X> → <Y>» / «From <X> to <Y> in <time>»
- Show, don't tell (image carries 80%)

## Honesty rules (ВАЖНО)

ВСЕГДА:
- Same camera angle для photo
- Same lighting conditions
- Same scale / framing
- Same processing (no post-fix on after only)

НИКОГДА:
- Misleading proportions
- Faked screenshots в after
- Exaggerated improvement
- Different angles чтобы flatter after

## Anti-patterns specific (FAIL)

- Преувеличенные visuals («чудо-преобразование»)
- Faked screenshots
- Длинный текст overlay (>5 слов per side)
- Misleading proportions
- Без consent если чужой before-after
- Negative framing на before («какой ты был unsuccessful»)

## Subject ethics

Если показываешь чужой before-after:
- Получи permission в writing (email / DM screenshot)
- Не используй для shaming
- Не преувеличивай before в negative direction
- Дай attribution или blur identity по предпочтению автора

## Cross-distribution

- X: 1:1 vertical split
- IG: 4:5 vertical split (highest feed reach)
- LinkedIn: 1.91:1 horizontal split возможно
- TG: 1:1
- Threads: 1:1

## Type-specific review hooks

- Honest comparison? (same angle/scale/lighting)
- Consent if external?
- Labels ≤ 3 слов each
- Delta concrete (не abstract)
- Identity якорь present

## Memory cross-refs

- `[[feedback-no-inventing-facts]]` - real comparison only
- `[[feedback-no-negative-stats-in-public-offer]]` - before не shaming

## Когда переключиться на video skill

- Если хочешь motion (transition между states) → `before-after` video sub-format skill
- Если хочешь narration / voice-over → video pipeline (replicate-reel + voice-generate)
- Single-image остаётся для static frame только