// regression-check.mjs — СЛОЙ 2 review: визуальная регрессия (self-baseline pixelmatch).
// Ловит НЕПРЕДНАМЕРЕННЫЙ визуальный дрейф между итерациями (фикс экрана N не сломал экран N-1)
// и любое отклонение от утверждённого baseline — полнота по построению, не по списку классов.
// Использование: node regression-check.mjs <file|url> [w1,w2] [--baseline-dir D] [--threshold R] [--update]
//   первый прогон → создаёт baseline. Дальше → диф vs baseline, exit 1 если diff_ratio>threshold.
//   --update — перезаписать baseline (после АПРУВА экрана автором).
// Выход: JSON + diff-PNG рядом + exit 1 при регрессии.
import { createRequire } from 'module';
import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'fs';
const require = createRequire(process.cwd() + '/');
const { chromium } = require('playwright');
const { PNG } = require('pngjs');
const pixelmatch = (await import('file://' + require.resolve('pixelmatch'))).default; // ESM из node_modules ПРОЕКТА (cwd), не папки скрипта
const a = process.argv.slice(2);
if(!a[0]){ console.error('usage: node regression-check.mjs <file|url> [widths] [--baseline-dir D] [--threshold R] [--update]'); process.exit(2); }
if(!a[0].startsWith('http')){ const fp=a[0].startsWith('/')?a[0]:process.cwd()+'/'+a[0]; if(!existsSync(fp)){ console.error('file not found:', fp); process.exit(2); } }
const widths = (a[1] && !a[1].startsWith('--')) ? a[1].split(',').map(Number) : [390,1280];
const getOpt = (k,d)=>{const i=a.indexOf(k); return i>=0?a[i+1]:d;};
const BDIR = getOpt('--baseline-dir', '.review-baseline');
const THRESH = +getOpt('--threshold', 0.01); // maxDiffPixelRatio (индустр. 0.01-0.02)
const UPDATE = a.includes('--update');
const url = a[0].startsWith('http') ? a[0] : 'file://'+(a[0].startsWith('/')?a[0]:process.cwd()+'/'+a[0]);
const name = (a[0].split('/').pop()||'page').replace(/\.[^.]+$/,'');
if(!existsSync(BDIR)) mkdirSync(BDIR,{recursive:true});
const browser = await chromium.launch();
const report = { target:url, threshold:THRESH, widths:{}, summary:{regressions:0, baselines_created:0} };
for(const w of widths){
  const ctx = await browser.newContext({ viewport:{width:w,height:900,deviceScaleFactor:1} });
  const page = await ctx.newPage();
  await page.goto(url); await page.waitForTimeout(1500);
  const buf = await page.screenshot({ fullPage:true });
  const bpath = `${BDIR}/${name}-${w}.png`;
  if(UPDATE || !existsSync(bpath)){
    writeFileSync(bpath, buf);
    report.widths[w] = { status: UPDATE?'baseline_updated':'baseline_created' };
    if(!UPDATE) report.summary.baselines_created++;
  } else {
    const cur = PNG.sync.read(buf), base = PNG.sync.read(readFileSync(bpath));
    if(base.width!==cur.width || base.height!==cur.height){
      report.widths[w] = { status:'SIZE_CHANGED', baseline:`${base.width}x${base.height}`, current:`${cur.width}x${cur.height}` };
      report.summary.regressions++;
    } else {
      const diff = new PNG({ width:cur.width, height:cur.height });
      const np = pixelmatch(base.data, cur.data, diff.data, cur.width, cur.height, { threshold:0.1 });
      const ratio = np/(cur.width*cur.height);
      const rec = { status: ratio>THRESH?'REGRESSION':'ok', diff_ratio:+ratio.toFixed(5), diff_pixels:np };
      if(ratio>THRESH){ const dp=`${BDIR}/${name}-${w}-diff.png`; writeFileSync(dp, PNG.sync.write(diff)); rec.diff_image=dp; report.summary.regressions++; }
      report.widths[w] = rec;
    }
  }
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(report,null,2));
process.exit(report.summary.regressions>0?1:0);