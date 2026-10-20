import { chromium } from '~/landing-vibecoding-oplata/node_modules/playwright/index.mjs';
import fs from 'fs';
const TXT=process.argv[2], OUT=process.argv[3];
const script=fs.readFileSync(TXT,'utf8').trim();
const prompt=`Сделай видео с говорящей головой. Аватар: <your name> (твой аватар). Голос: <your name> -- 10. Широкий ландшафтный кадр 16:9, аватар точно по центру, крупный план. Без b-roll, без вставок, без субтитров, без музыки. Один непрерывный план. Текст дословно: ${script.replace(/\n+/g,' ')}`;
const b=await chromium.connectOverCDP('http://localhost:9222');
const ctx=b.contexts()[0];
let page=ctx.pages().find(p=>p.url().includes('heygen'))||await ctx.newPage();
// ВАЖНО: каждый рендер = НОВЫЙ чат. Иначе HeyGen дописывает в старый диалог и отдаёт его первое видео.
await page.goto('https://app.heygen.com/home',{waitUntil:'domcontentloaded'});
await page.waitForTimeout(9000);
// если на главной висит старый диалог - жмём Create New
const fresh=await page.locator('text=/Create New/i').first();
if(await fresh.count().catch(()=>0)) { await fresh.click().catch(()=>{}); await page.waitForTimeout(4000); }
const ta=page.locator('textarea').first();
await ta.click(); await page.waitForTimeout(400); await ta.fill('');
await ta.type(prompt,{delay:3});
await page.waitForTimeout(1800);
const len=(await ta.inputValue()).length;
await page.locator('button[aria-label="Submit"]').click();
await page.waitForTimeout(20000);
const url=page.url();
console.log('TA_LEN:',len);
console.log('URL_AFTER:',url);
if(OUT&&OUT!=='/dev/null') fs.writeFileSync(OUT,url.split('/').pop());
await b.close(); process.exit(0);
