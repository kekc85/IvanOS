# Template: concept-diagram

Mental model / framework / spectrum / 2x2 / iceberg / pyramid / funnel / equation visualization.

Reference: Jack Butcher (Visualize Value).

## Brief structure (заполнить в 03-design-brief)

```yaml
type: concept-diagram
geometry: <spectrum | 2x2 | iceberg | funnel | pyramid | equation | boxes-arrows | venn | tree | cycle>

composition:
  primary: "<главный геометрический элемент / центр диаграммы>"
  secondary:
    - "<supporting element 1>"
    - "<supporting element 2>"
  position: "center | left-third | golden-ratio"
  negative_space_target: "40-50%"

text_on_image_verbatim:
  headline: "<≤6 слов, optional если diagram self-explanatory>"
  labels:  # дословно, по каждому elementу
    - "<label 1, ≤3 слов>"
    - "<label 2, ≤3 слов>"
  attribution: "@<handle>"  # optional

palette:
  primary_bg: "{ink|paper}"
  primary_text: "{ink|paper}"
  accent: "{accent|none}"
  contrast_check: "<7:1+ для текста, 4.5:1+ для headline>"

typography:
  headline: "Inter Bold 80pt"
  labels: "Inter Medium 24pt"
  attribution: "Inter Regular 14pt"
```

## Geometry guidance

### Spectrum / scale
- 2-5 точек на оси (НЕ 6+ - overwhelm)
- Подписи на каждой точке + 2 end-labels (X axis)
- Optional Y-axis для 2D positioning

### 2x2 matrix
- 4 квадранта, явные labels per quadrant
- Опционально - точки positioning конкретных things
- X axis label + Y axis label

### Iceberg
- 20-30% выше «воды»: visible labels
- 70-80% ниже: hidden labels (3-7 штук)
- Линия waterline горизонтальная по золотому сечению

### Funnel
- 3-5 стадий, top wide → bottom narrow
- Цифры или labels по стадиям

### Pyramid
- 3-5 уровней
- Maslow-style или skill-tree
- Vertical hierarchy

### Equation / formula
- ≤7 elements (e.g., "X = (A × B) / C")
- Один result =, ≤2 operators

### Framework boxes + arrows
- 3-5 boxes connected
- Arrows clearly directional
- ≤7 nodes total

### Venn
- 2-3 круга
- Intersection labelled
- Equal size circles (unless intentional)

### Tree
- Root → 2-4 branches → leaves
- ≤3 levels deep
- ≤12 leaves total

### Cycle
- 3-5 nodes, циклически connected
- Стрелки по часовой
- 1 entry/exit point подсвечен

## Tool prompt template

**Cost ladder:** FREE first → PAID только с явным апрувом автора (memory `[[feedback-free-tools-first-for-images]]`).

---

**PRIMARY (FREE): HTML + Playwright screenshot** (deterministic, pixel-perfect, $0, validated по решению автора на iceberg тесте - v3 PNG получился readable, brand-consistent):

```html
<!DOCTYPE html>
<html><head><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800&display=swap');
body { width: 1080px; height: 1080px; background: #FAFAFA; font-family: 'Inter'; position: relative; }
.headline { position: absolute; top: 80px; left: 0; right: 0; text-align: center; font-size: 60px; font-weight: 800; }
/* SVG iceberg + labels + footer */
</style></head><body>
<!-- Compose geometry per type sub-type (iceberg / 2x2 / spectrum / etc) -->
</body></html>
```

Render pipeline:
1. Write HTML to `/tmp/single-image-{slug}/{type}.html`
2. Python HTTP server `python3 -m http.server 8765` (background)
3. Playwright `browser_resize 1080 1080` → `browser_navigate http://localhost:8765/{type}.html` → `browser_take_screenshot {output}.png`
4. Открыть командой ОС: `open {output}.png` (macOS) / `start "" "{output}.png"` (Windows) / `xdg-open {output}.png` (Linux), либо `~/.claude/skills/_shared/bin/open-file {output}.png`

Reference working pattern: `/tmp/single-image-test/iceberg-v3.html`.

---

**SECONDARY (FREE): Figma** (когда нужен pixel-perfect typography + shapes control, free tier OK):
```
1. New file 1080x1080, cream background #FAFAFA
2. Geometric shapes: {описание shapes}
3. Text labels: Inter Bold 60-80pt headline, Inter Medium 24pt labels
4. Color: #0A0A0A text, optional accent #0066FF
5. Brand footer bar чёрный #0A0A0A 56-64px с author + handle
6. Export PNG 2x retina
```

---

**TERTIARY (FREE): Photopea** (free browser Photoshop alternative для composite work):
- Аналогично Figma но для photo composites / polish
- URL: photopea.com (browser-based, no install)

---

**PAID OPTION 1 (REQUIRES APPROVAL): higgsfield-generate gpt_image_2** (~1 credit, ~$0.10-0.20):
- Сильнее в editorial-feel / hand-drawn aesthetic
- Validated по решению автора - выделяется в feed но 1 typo в text accuracy
- **НЕ запускать без явного «генери через AI» / «сделай через higgsfield» от автора**

```bash
higgsfield generate create gpt_image_2 \
  --prompt '<full prompt>' \
  --aspect_ratio 1:1 --resolution 2k --wait
```

---

**PAID OPTION 2 (REQUIRES APPROVAL): Midjourney v7** ($30+/мес subscription):
- Если автор предпочитает MJ aesthetic
- Same: only с явным апрувом

```
minimalist {geometry} diagram, black ink on cream paper, geometric, clean, Visualize Value style --ar 1:1 --no gradient, photo, 3D, decoration
```

---

**Decision flow:**
1. Default → HTML + Playwright (FREE)
2. Если HTML не fits aesthetic / геометрия слишком complex → Figma (FREE)
3. Если нужны photo composites → Photopea (FREE)
4. **Только если автор сам спросил «через AI / better quality / нужна editorial-feel»** → ASK апрув на higgsfield/MJ → ТОЛЬКО после YES запускать
5. Без апрува платное - не использовать

Cost-aware rule cited: `workflow/06-output.md` Step 1 decision tree.

## Caption guidance per concept-diagram

- Length: ≤200 chars
- Role: 1-line context для diagram (если headline в image не достаточен)
- Hook patterns:
  - RU: «Карта <topic>:» / «Простыми словами: <topic>»
  - EN: «A map of <topic>:» / «In one frame:»
- Avoid: пересказа того что на diagram

## Anti-patterns specific

- 8+ elements (cluttered)
- Multiple typeface families
- Decorative icons без semantic role
- Gradient fills (use flat)
- Drop shadows
- Стрелки в разные хаотичные directions
- Text-heavy labels (>3 слов)
- Цветовой rainbow (≤2 colors)

## Examples reference

Jack Butcher signature moves:
- «Productize Yourself» iceberg
- «Time vs Leverage» 2x2
- «Specific Knowledge» funnel
- «Outputs / Inputs» equation

Copy structure, не content.

## Type-specific review hooks (для 05-review.md)

- Labels count ≤ 7
- Geometry один из 10 valid
- Color count ≤ 2
- Identity anchor present (palette / typography / signature)