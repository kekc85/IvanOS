# Template: dashboard-screenshot

Real metric reveal. Pure proof = bookmarks. Reference: Pieter Levels, Marc Lou, Pat Walls.

ВАЖНО: ТОЛЬКО real verified numbers. Выдуманные = brand suicide.

## Brief structure

```yaml
type: dashboard-screenshot
sub_type: <single-metric | time-series | comparison-split | multi-metric | notification>

source:
  dashboard: "<Stripe / Skool / Kit / Beehiiv / Analytics / etc>"
  url: "<URL или path к dashboard>"
  metric_name: "<MRR / subscribers / cash event / etc>"
  metric_value: "<verified number>"
  verification: "<.business/ path | user-provided | live screenshot now>"

composition:
  primary: "<главная цифра / chart>"
  highlight: "yellow box / arrow на key number"
  crop: "<bounds: что в кадре, что отрезано>"
  position: "centered or rule-of-thirds"

text_on_image_verbatim:
  caption_overlay: "<0-1 слово max в image>"
  attribution: "@<handle>"  # optional

palette:
  primary: "<реальная палитра dashboard>"
  highlight: "#FFD700 yellow"  # для box / arrow
  contrast_check: "PASS WCAG AAA"

typography:
  in_dashboard: "<native dashboard typography>"
  overlay: "Inter Bold 60pt"
```

## Privacy required

ВСЕГДА blur:
- Customer names
- Customer emails
- Internal IDs (Stripe customer IDs / Skool user IDs)
- Bank account info / partial card numbers
- Personal phone numbers
- Internal Slack messages
- Sensitive metadata

Tool: CleanShot X (macOS) blur область или Photopea blur layer.

## Tool prompt template

ВАЖНО: AI generation запрещена для этого type. Real screenshot only.

```
Steps:
1. Open <dashboard URL>
2. Navigate к <metric view>
3. CleanShot X capture (macOS): cmd+shift+5
4. Crop к key metric (cropped размер ≈1080x1080)
5. Blur sensitive (customer names / emails / IDs)
6. Open в Photopea / Figma
7. Add yellow box или arrow на key number:
   - Box: stroke #FFD700, width 4px, around number
   - OR Arrow: #FFD700, pointing к number, simple shape
8. Optional caption overlay (0-1 word) - Inter Bold 60pt #0A0A0A
9. Export PNG 2x retina
```

## Sub-type details

### Single metric reveal
- 1 number, огромный (≥40% canvas height)
- Context vis (date range / period) рядом
- 0-1 word overlay

### Time-series chart
- Line/bar chart за период
- Annotated milestone (arrow + 1-line)
- Y-axis labels visible

### Comparison split
- Before timepoint vs After
- Side-by-side в одном screenshot
- Delta clearly visible

### Multi-metric grid
- 4-6 KPI tiles
- Все relevant к topic
- One tile highlighted

### Notification screenshot
- macOS / iOS notification panel
- Stripe / PayPal / banking app
- Time / source visible
- Personal info blurred

## Caption guidance

- Length: ≤150 chars (image carries 80%)
- Role: 1-3 lines context / setup
- Hook patterns:
  - RU: «<число> <event>. <1-line context>»
  - EN: «Just hit <number>. <1-line context>»
- Не дублировать цифру из image
- Не negative статистики
- Не hyperbolic («incredible», «amazing»)

Examples:
- RU: «100К ₽ за один cash event. Без рекламы.»
- EN: «$132K MRR. 11 months, 0 employees.»

## Anti-patterns specific (FAIL)

- Выдуманные numbers (instant brand suicide)
- Projections как fact («on track to», «expecting»)
- Misleading crops (вырезан context)
- Stock dashboard images
- Customer data без permission
- AI-generated dashboard look (always real screenshot)
- Negative статистики
- Multiple highlights (overwhelm)

## Cross-distribution

- X primary: 1:1 single image
- LinkedIn Multi-Image Sequential: 2-4 images (Stripe → context → process → result)
- Threads: cross-post from X
- TG: 1:1 same as X

## Type-specific review hooks

- Real metric verified? (via `.business/` или explicit user-provided)
- Privacy: blur applied?
- AI-gen disallowed - check tool used = screenshot
- Number not hyped
- Caption не дублирует цифру

## Real numbers автора (для quick reference)

См. /:
- <твоя выручка> revenue 2025 (cash events)
- 800+ выпускников
- <размер базы> <твой-хэндл>
- 500K+ reach

Любая новая цифра должна быть verified в `.business/` ИЛИ explicitly provided in current session.