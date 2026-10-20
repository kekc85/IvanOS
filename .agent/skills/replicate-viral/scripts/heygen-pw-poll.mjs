import { chromium } from '~/landing-vibecoding-oplata/node_modules/playwright/index.mjs';
import fs from 'fs';
const PID=process.argv[2], OUT=process.argv[3];
const b=await chromium.connectOverCDP('http://localhost:9222');
const ctx=b.contexts()[0];
let page=ctx.pages().find(p=>p.url().includes('heygen'))||await ctx.newPage();
await page.goto(`https://app.heygen.com/video-agent/${PID}`,{waitUntil:'domcontentloaded'});
await page.waitForTimeout(9000);
let srcs=[];
for(let i=0;i<80;i++){
  const r=await page.evaluate(()=>{
    const vids=[...document.querySelectorAll('video')].map(v=>v.currentSrc||v.src)
      .filter(s=>s&&s.startsWith('http'))
      .filter(s=>!s.includes('dynamic.heygen.ai/Experiment'));  // отсечь рекламу главной
    return {vids:[...new Set(vids)],cooking:/cooking|generating|processing/i.test(document.body.innerText)};
  });
  if(r.vids.length){srcs=r.vids;console.log('READY iter',i,'vids',r.vids.length);break;}
  if(i%4===0)console.log('iter',i,'cooking=',r.cooking);
  await page.waitForTimeout(25000);
}
fs.writeFileSync(OUT,JSON.stringify(srcs,null,1));
console.log('SRCS',srcs.length);
await b.close(); process.exit(0);
