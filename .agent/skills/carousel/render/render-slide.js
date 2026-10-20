#!/usr/bin/env node
// Render one slide HTML → PNG 1080×1350 via Playwright
// Usage: node render-slide.js <html-path> <png-output-path>

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const htmlPath = process.argv[2];
  const pngPath = process.argv[3];

  if (!htmlPath || !pngPath) {
    console.error('Usage: node render-slide.js <html-path> <png-output-path>');
    process.exit(1);
  }

  if (!fs.existsSync(htmlPath)) {
    console.error(`HTML not found: ${htmlPath}`);
    process.exit(1);
  }

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1080, height: 1350 },
    deviceScaleFactor: 2  // retina quality
  });
  const page = await context.newPage();

  const absPath = path.resolve(htmlPath);
  await page.goto('file://' + absPath);

  // Wait for fonts to load
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);

  await page.screenshot({
    path: pngPath,
    type: 'png',
    fullPage: false,
    omitBackground: false
  });

  await browser.close();
  console.log(`✓ Rendered: ${pngPath}`);
})();