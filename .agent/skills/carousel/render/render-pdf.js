#!/usr/bin/env node
// Combine N slide PNGs → single multi-page PDF (LinkedIn document upload)
// Usage: node render-pdf.js <output-dir> <pdf-output-path>

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const outputDir = process.argv[2];
  const pdfPath = process.argv[3];

  if (!outputDir || !pdfPath) {
    console.error('Usage: node render-pdf.js <output-dir> <pdf-output-path>');
    process.exit(1);
  }

  // Find all slide PNGs (sorted)
  const slides = fs.readdirSync(outputDir)
    .filter(f => /^slide-\d+\.png$/.test(f))
    .sort();

  if (slides.length === 0) {
    console.error(`No slide PNGs found in ${outputDir}`);
    process.exit(1);
  }

  // Build multi-page HTML
  const slidesHtml = slides.map(s =>
    `<div class="page"><img src="file://${path.resolve(outputDir, s)}" /></div>`
  ).join('\n');

  const html = `<!DOCTYPE html>
<html>
<head>
<style>
  @page { size: 1080px 1350px; margin: 0; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { margin: 0; padding: 0; }
  .page {
    width: 1080px;
    height: 1350px;
    page-break-after: always;
    overflow: hidden;
  }
  .page img {
    width: 1080px;
    height: 1350px;
    display: block;
  }
  .page:last-child { page-break-after: avoid; }
</style>
</head>
<body>
${slidesHtml}
</body>
</html>`;

  const tmpHtml = path.join(outputDir, '_tmp-pdf-source.html');
  fs.writeFileSync(tmpHtml, html);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + tmpHtml);
  await page.waitForLoadState('networkidle');

  await page.pdf({
    path: pdfPath,
    width: '1080px',
    height: '1350px',
    printBackground: true,
    preferCSSPageSize: true
  });

  await browser.close();
  fs.unlinkSync(tmpHtml);
  console.log(`✓ PDF rendered: ${pdfPath} (${slides.length} pages)`);
})();