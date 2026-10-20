# Workflow 06-render - End-to-end render pipeline (PNG + PDF)

> ⚠️ В ПАКЕТ НЕ ВХОДЯТ: `playwright-pdf.js`. Команды с этими именами даны как ОПИСАНИЕ: инструмент либо приходит из внешнего пакета, который ставится отдельно, либо собирается на твоём проекте по этой же инструкции. Внутри поставки такого файла нет

**Назначение:** превратить carousel object (slides + visual briefs + caption) в готовую папку с PNG slides + LinkedIn PDF + caption files. Output = ready-to-publish.
**Вход:** `carousel` после `05-publish.md` (с assets_manifest + render_strategy per slide)
**Выход:** `~/Desktop/carousels/{date}-{slug}/` с N PNGs + caption.txt + linkedin.pdf + assets-manual-queue.txt

---

## Шаг 0 - Output folder setup

```bash
SLUG=$(echo "${carousel.topic}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-zа-я0-9]/-/g' | cut -c1-50)
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="$HOME/Desktop/carousels/${DATE}-${SLUG}"
mkdir -p "$OUTPUT_DIR"
```

---

## Шаг 1 - Per-slide render по render_strategy

Для каждого slide в carousel.slides[] выбрать render path:

### Strategy: `typography`

Slide с только текстом + brand styling (hook / numbered framework headlines / CTA).

**Chain:** `[[frontend-design]]`

```
1. Прочитать carousel/render/templates/typography-{role}.html (есть в `render/templates/`)
2. Inject slide.text + brand colors из config (red accent / cream bg)
3. Inject typography (Inter / Roboto / Helvetica) из config.platforms
4. Render через Playwright headless Chrome:
   - viewport 1080×1350
   - wait для font loading
   - page.screenshot({path: 'slide-NN.png', type: 'png'})
5. Save в $OUTPUT_DIR/slide-NN.png
```

### Strategy: `web-screenshot`

Slide требует UI screenshot web-tool (Skool / Stripe / Kit / TG Web / Beehiiv / LinkedIn / Notion / GitHub).

**Chain:** `[[ui-record]]` (screenshot mode, not video mode)

```
1. Из visual_brief.real_elements извлечь URL + crop region
2. ui-record screenshot --url <url> --selector <css-selector> --viewport 1920x1080
3. ffmpeg crop к region of interest 
4. Composite на 1080×1350 canvas с typography overlay через frontend-design
5. Save в $OUTPUT_DIR/slide-NN.png
```

Если URL требует авторизации (Skool admin / Stripe dashboard) → fallback на `desktop-manual` (см. ниже).

### Strategy: `desktop-manual`

Slide требует screenshot desktop app (Claude Code IDE / Cursor / Figma / Terminal native).

**Не можем headless автоматизировать.** Output queue для manual capture.

```
1. Append в $OUTPUT_DIR/assets-manual-queue.txt:
   slide-NN.png required:
   - Tool: Claude Code IDE
   - Action: открыть file ~/.claude/skills/carousel/workflow/03-write.md
   - Crop region: editor pane only, 800×600
   - Annotations: highlight rectangle на lines 45-50
2. Generate placeholder slide-NN.png (typography-only fallback с text "Manual screenshot pending - see assets-manual-queue.txt")
3. ИЛИ если есть AppleScript helper - попытаться automate (см. references/render-pipeline.md)
```

### Strategy: `brand-asset`

Slide использует существующий asset из brand library (selfie / logo / signature image).

```
1. Lookup в config.paths.brand_assets ИЛИ ~/.business/assets/
2. Если asset exists → copy + composite через frontend-design
3. Если asset missing → fallback на desktop-manual + queue
```

### Strategy: `composite`

Panorama / hybrid slide требует multi-source composite (wide image разрезанный).

**Chain:** `[[frontend-design]]` для HTML composition + Playwright для slicing

```
1. Render wide canvas (N×1080 × 1350) с frontend-design
2. Playwright multi-screenshot с clip parameters - по N сегментам
3. Save каждый сегмент как slide-NN.png
```

---

## Шаг 2 - Caption files

```bash
# Caption RU
cat > $OUTPUT_DIR/caption-ru.txt << EOF
${carousel.caption.ru}
EOF

# Caption EN (если bilingual)
if [ "${carousel.bilingual}" = "true" ]; then
  cat > $OUTPUT_DIR/caption-en.txt << EOF
${carousel.caption.en}
EOF
fi

# A/B variants
cat > $OUTPUT_DIR/ab-variants.txt << EOF
Hook alt 1: ${carousel.ab_variants.hook_alt_1}
Hook alt 2: ${carousel.ab_variants.hook_alt_2}
Caption alt: ${carousel.ab_variants.caption_alt}
EOF
```

---

## Шаг 3 - LinkedIn PDF (если platform=li | both)

```javascript
// playwright-pdf.js (template в carousel/render/)
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1080, height: 1350 } });
  const page = await context.newPage();
  
  // Combine все slide HTMLs в single multi-page document
  await page.setContent(`<style>@page { size: 1080px 1350px; margin: 0; }</style>` + allSlidesHTML);
  await page.pdf({
    path: process.env.OUTPUT_DIR + '/linkedin.pdf',
    width: '1080px',
    height: '1350px',
    pageRanges: '',
    printBackground: true
  });
  await browser.close();
})();
```

Запуск:
```bash
OUTPUT_DIR=$OUTPUT_DIR node ~/.claude/skills/carousel/render/playwright-pdf.js
```

---

## Шаг 4 - Final manifest

```bash
cat > $OUTPUT_DIR/MANIFEST.md << EOF
# Carousel: ${carousel.topic}

Generated: ${DATE}
Family: ${carousel.family}
Platform: ${carousel.platform}
Slides: ${carousel.slides.length}

## Files
- slide-01.png ... slide-NN.png (1080×1350 PNG)
- caption-ru.txt
- caption-en.txt (если bilingual)
- ab-variants.txt
- linkedin.pdf (если platform=li|both)
- assets-manual-queue.txt (если есть desktop-manual TODOs)

## Status
- Rendered: ${RENDERED_COUNT}/${TOTAL_COUNT} slides
- Manual queue: ${MANUAL_QUEUE_COUNT} items

## Next steps
1. Если manual queue не пустой - сделать screenshots по queue
2. Re-run skill с флагом --re-render для replacement placeholder slides
3. Upload: IG carousel manually (slide-NN.png по порядку) / LinkedIn PDF upload
EOF
```

---

## Шаг 5 - Open output folder

```bash
open $OUTPUT_DIR
```

Memory правило: `[[feedback-always-open-artifacts]]` - открыть готовый output.

---

## Шаг 6 - Report в чат

```
✓ Carousel rendered: ${carousel.topic}

Folder: ${OUTPUT_DIR}
Rendered: ${RENDERED_COUNT}/${TOTAL_COUNT} slides (${PERCENT}%)
Manual queue: ${MANUAL_QUEUE_COUNT} items в assets-manual-queue.txt
PDF: ${PDF_PATH if li}

Готово к публикации:
- IG: загрузить slide-NN.png по порядку
- LinkedIn: upload linkedin.pdf как document
- Caption: copy из caption-ru.txt

${if MANUAL_QUEUE_COUNT > 0:}
⚠ Осталось ${MANUAL_QUEUE_COUNT} manual screenshots - см. assets-manual-queue.txt
${endif}
```

---

## Fallback chain (если render fails)

1. **typography fails** (frontend-design unavailable) → CSS-only basic render через Playwright + inline styles
2. **web-screenshot fails** (auth required / page broken) → desktop-manual queue
3. **composite fails** (Playwright crashes) → individual slide renders + post-merge через ImageMagick
4. **PDF fails** (Playwright PDF broken) → ImageMagick PNG sequence → PDF combine

В любом случае - render выдаёт **что-то** для каждого slide (даже placeholder), не блокирует.

---

## Принципы

1. **Always output, never block.** Если render fails - placeholder + manual queue, не error.
2. **Strategy-driven.** Каждый slide knows как себя рендерить через render_strategy field.
3. **Chain not embed.** Render delegates в `[[frontend-design]]` / `[[ui-record]]` / Playwright - не reinventing.
4. **Open final folder.** `open` на $OUTPUT_DIR в конце - memory правило.
5. **Manual queue tracked.** Что не получилось auto - в queue с инструкциями.
6. **Re-render-able.** Skill можно перезапустить с `--re-render` после ручных screenshots.

---

## Render strategy decision table

| Slide content type | render_strategy | Chain |
|---|---|---|
| Hook (number + outcome text) | typography | frontend-design |
| Numbered framework headline | typography | frontend-design |
| CTA с keyword + arrow | typography | frontend-design |
| Real product UI: Skool / Stripe / TG Web / Beehiiv / Kit | web-screenshot | ui-record + crop |
| Real product UI: Claude Code IDE / Cursor / Figma desktop | desktop-manual | manual queue + AppleScript helper |
| Author selfie / signature | brand-asset | brand library lookup |
| Panorama wide composition | composite | frontend-design multi-segment |
| Photo + UI overlay hybrid | composite | brand-asset + frontend-design overlay |