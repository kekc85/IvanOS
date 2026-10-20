# Render pipeline reference

Mapping render_strategy → chain skill / tool + примеры.

---

## 5 render strategies

### 1. `typography`

Slide с только текстом + brand styling. Hook / numbered step / CTA / synthesis slides.

**Chain:** `frontend-design` skill → HTML template из `carousel/render/templates/typography-{role}.html` → Playwright screenshot.

**Pipeline:**
```bash
# 1. Generate HTML
cat carousel/render/templates/typography-hook.html | \
  sed "s|{{TEXT}}|${slide.text}|" | \
  sed "s|{{ACCENT_COLOR}}|${config.brand.accent}|" > /tmp/slide-NN.html

# 2. Playwright screenshot
node -e "
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
  await page.goto('file:///tmp/slide-NN.html');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: '${OUTPUT_DIR}/slide-NN.png', type: 'png' });
  await browser.close();
})();"
```

**Время per slide:** ~3-5 sec.

---

### 2. `web-screenshot`

Slide требует UI screenshot web-tool. Tools которые работают:
- Skool community pages (public)
- TG Web (web.telegram.org)
- Stripe public pricing pages
- Beehiiv newsletter previews
- LinkedIn public profiles
- GitHub repos / contribution graphs
- Notion public pages

**Chain:** `ui-record` skill в screenshot mode.

**Pipeline:**
```bash
# 1. ui-record screenshot
~/.claude/skills/ui-record/scripts/record.sh \
  --url "${slide.visual_brief.real_elements[0].url}" \
  --selector "${slide.visual_brief.real_elements[0].css_selector}" \
  --viewport "1920x1080" \
  --output /tmp/raw-screenshot.png

# 2. Composite на 1080×1350 canvas через frontend-design
# (HTML с background image + typography overlay)
# 3. Playwright screenshot финал
```

**Что НЕ работает auto:** tools с авторизацией (Stripe Admin / Skool Admin / Kit dashboard) → fallback на `desktop-manual`.

---

### 3. `desktop-manual`

Desktop apps без web URL (Claude Code IDE / Cursor / Figma desktop / Native Mac apps / Terminal full screen).

**Не automate-able headless.** Output → manual queue.

**Pipeline:**
```bash
# Append в assets-manual-queue.txt
cat >> $OUTPUT_DIR/assets-manual-queue.txt << EOF

slide-NN.png required:
- Tool: ${slide.visual_brief.real_elements[0].tool}
- Action: ${slide.visual_brief.real_elements[0].setup_action}
- Crop region: ${slide.visual_brief.real_elements[0].crop}
- Save to: $OUTPUT_DIR/manual/slide-NN.png
- Annotations after capture: ${slide.visual_brief.text_overlay}
EOF

# Generate placeholder PNG (typography "Manual screenshot pending")
# через typography strategy
```

**AppleScript helper (опционально для tools с известным workflow):**

```applescript
-- carousel/render/applescripts/screenshot-claude-code.scpt
tell application "Claude Code"
  activate
  open "file://$HOME/.claude/skills/carousel/workflow/03-write.md"
end tell
delay 1
do shell script "screencapture -R 100,100,1280,800 /tmp/cc-shot.png"
```

Используется если есть pre-built helper для конкретного tool в `carousel/render/applescripts/`.

---

### 4. `brand-asset`

Slide использует existing asset из brand library (selfie / logo / signature).

**Pipeline:**
```bash
# Lookup
ASSET_PATH=$(find ~/.business/assets/ -name "${slide.visual_brief.real_elements[0].asset_name}*" -type f | head -1)

if [ -z "$ASSET_PATH" ]; then
  # Asset missing → manual queue
  echo "BRAND ASSET MISSING: ${slide.visual_brief.real_elements[0].asset_name}" >> $OUTPUT_DIR/assets-manual-queue.txt
  # Generate placeholder
else
  # Composite через frontend-design HTML с background-image: $ASSET_PATH
  # Playwright screenshot
fi
```

---

### 5. `composite`

Panorama wide composition разрезанная на N slides + hybrid (real asset + typography overlay).

**Chain:** `frontend-design` для HTML composition + Playwright multi-clip screenshot.

**Pipeline:**
```bash
# 1. Render wide canvas (N×1080) HTML
# 2. Playwright multi-screenshot per segment
node -e "
const { chromium } = require('playwright');
(async () => {
  const N = ${slide_count};
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: N*1080, height: 1350 } });
  await page.goto('file:///tmp/panorama-wide.html');
  await page.waitForLoadState('networkidle');
  
  for (let i = 0; i < N; i++) {
    await page.screenshot({
      path: '${OUTPUT_DIR}/slide-' + String(i+1).padStart(2, '0') + '.png',
      clip: { x: i*1080, y: 0, width: 1080, height: 1350 }
    });
  }
  await browser.close();
})();"
```

---

## Auto-assignment в `02-structure.md`

Default render_strategy per slide role:

| Role | Default render_strategy |
|---|---|
| hook | typography |
| context | typography |
| numbered_step (text only) | typography |
| numbered_step (с screenshot) | web-screenshot OR desktop-manual |
| item (listicle text) | typography |
| item (listicle screenshot) | web-screenshot OR desktop-manual |
| reveal | brand-asset OR web-screenshot |
| synthesis | typography |
| cta | typography (с brand-asset для selfie) |
| panorama leading / middle / payoff | composite |

Override через `slide.render_strategy` в structure stage.

---

## Brand pre-baked templates

Templates в `carousel/render/templates/`:

- `typography-hook.html` - Hook slide (large number + outcome + timeframe)
- `typography-step.html` - Numbered framework step
- `typography-listicle-item.html` - Listicle item с counter (N/M)
- `typography-cta.html` - CTA slide (keyword + arrow + signature)
- `typography-quote.html` - Quote / lesson slide
- `panorama-segment.html` - Panorama segment с continuity stripes
- `hybrid-overlay.html` - Real asset (background) + typography overlay

Каждый template содержит:
- `{{TEXT}}` placeholder
- `{{ACCENT_COLOR}}` (из config.brand.accent)
- `{{BACKGROUND}}` (cream off-white default)
- `{{TYPOGRAPHY_PRIMARY}}` (Inter Bold default)
- `{{TYPOGRAPHY_SIZE}}` (60pt headline / 36pt body)

Это даёт brand consistency без re-doing CSS каждый раз.

---

## Render decision tree

```
For each slide:
  if slide.render_strategy == 'typography':
    → typography-{role}.html → Playwright
  
  elif slide.render_strategy == 'web-screenshot':
    if URL public no-auth:
      → ui-record screenshot → composite
    else:
      → fallback desktop-manual
  
  elif slide.render_strategy == 'desktop-manual':
    if applescript helper exists:
      → run AppleScript → screencapture
    else:
      → manual queue + placeholder
  
  elif slide.render_strategy == 'brand-asset':
    if asset exists в brand library:
      → composite через HTML
    else:
      → manual queue + placeholder
  
  elif slide.render_strategy == 'composite':
    → wide HTML + Playwright multi-clip
```

---

## Re-render mode

После manual screenshots в `$OUTPUT_DIR/manual/`:

```bash
/carousel --re-render $OUTPUT_DIR
```

Skill:
1. Reads $OUTPUT_DIR/MANIFEST.md (carousel object)
2. Для каждой PNG в $OUTPUT_DIR/manual/ - replace placeholder slide-NN.png
3. Re-builds linkedin.pdf если platform=li
4. Updates MANIFEST.md status
5. Открыть папку командой ОС: `open $OUTPUT_DIR` (macOS) / `start "" "$OUTPUT_DIR"` (Windows) / `xdg-open "$OUTPUT_DIR"` (Linux), либо `~/.claude/skills/_shared/bin/open-file "$OUTPUT_DIR"`

---

## Принципы

1. **Strategy-driven render.** Каждый slide knows как себя render через `render_strategy`.
2. **Chain not embed.** Render = composition chains в `frontend-design` / `ui-record` / Playwright.
3. **Always output.** Если auto fails → placeholder + manual queue, не error.
4. **Re-render-able.** После manual screenshots → re-run для replacement placeholders.
5. **Brand pre-baked.** HTML templates в `carousel/render/templates/` для consistency.