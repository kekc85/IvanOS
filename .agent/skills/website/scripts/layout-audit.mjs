// layout-audit.mjs — ДЕТЕРМИНИРОВАННЫЙ аудит макета. Часть Фазы 09 review (website-скилл).
// Ловит проверяемые дефекты, которые критик-«на глаз» пропускает: наложения текста,
// прилипшие секции (нет отступа), вылет за вьюпорт, обрезку контента. Гоняется на МОБ+ДЕСКТОП.
// Использование: node layout-audit.mjs <file|url> [w1,w2] [--sections "sel"] [--gap-min N]
// Выход: JSON-отчёт в stdout + exit 1 если есть дефекты (можно гейтить).
// playwright тянем из node_modules ТЕКУЩЕГО проекта (cwd), а не из папки скилла
import { createRequire } from 'module';
import { existsSync } from 'fs';
const require = createRequire(process.cwd() + '/');
const { chromium } = require('playwright');
const a = process.argv.slice(2);
if(!a[0]){ console.error('usage: node layout-audit.mjs <file|url> [widths]'); process.exit(2); }
if(!a[0].startsWith('http')){ const fp=a[0].startsWith('/')?a[0]:process.cwd()+'/'+a[0]; if(!existsSync(fp)){ console.error('file not found:', fp); process.exit(2); } }
const widths = (a[1] && !a[1].startsWith('--')) ? a[1].split(',').map(Number) : [360,768,1024,1280]; // дефолт — зоны между брейкпоинтами, не 3 точки
const getOpt = (k,d)=>{const i=a.indexOf(k); return i>=0?a[i+1]:d;};
const GAP_MIN = +getOpt('--gap-min', 20);
const OVERLAP_MIN = 8;
const PERF = a.indexOf('--no-perf') < 0;                 // перф-пол (mobile-first) включён по умолчанию; --no-perf глушит
const WEIGHT_BUDGET_KB = +getOpt('--weight-budget', 0);  // 0 = вес только advisory (не блокирует); >0 = HARD-бюджет в KB на моб
const SECTION_SEL = getOpt('--sections', 'header, section, .ba, .scr2, footer');
const url = a[0].startsWith('http') ? a[0] : 'file://'+(a[0].startsWith('/')?a[0]:process.cwd()+'/'+a[0]);
const browser = await chromium.launch();
const report = { target:url, gap_min:GAP_MIN, widths:{}, summary:{defects:0} };
for(const w of widths){
  const context = await browser.newContext({ viewport:{width:w,height:900,deviceScaleFactor:1} }); // newContext (не newPage) — иначе axe падает
  const page = await context.newPage();
  await page.addInitScript(()=>{window.__cls=0;try{new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__cls+=e.value;}).observe({type:'layout-shift',buffered:true});}catch(e){} // CLS-наблюдатель ДО навигации
    window.__lcp=0;try{new PerformanceObserver(l=>{const es=l.getEntries();const last=es[es.length-1];if(last)window.__lcp=last.renderTime||last.loadTime||last.startTime||0;}).observe({type:'largest-contentful-paint',buffered:true});}catch(e){}}); // LCP-наблюдатель (advisory)
  await page.goto(url); await page.waitForTimeout(1500);
  const r = await page.evaluate(({GAP_MIN,OVERLAP_MIN,SECTION_SEL,PERF,WEIGHT_BUDGET_KB})=>{
    const vw=innerWidth, out={section_sticking:[],text_overlaps:[],viewport_overflow:[],content_clipped:[],container_overflow:[],touch_targets:[],image_dims:[],orphan_candidates:[],flexitem_orphan:[],render_blocking:[],font_display:[],img_offscreen_eager:[],weight_over_budget:[],dark_ai_theme:[],hardcoded_colors:[],css_dup_selector:[]};
    const abs=e=>{const b=e.getBoundingClientRect();return{l:b.left,t:b.top+scrollY,r:b.right,b:b.bottom+scrollY,w:b.width};};
    let bandEls=[...document.querySelectorAll(SECTION_SEL)].filter(e=>e.getBoundingClientRect().width>vw*0.5);
    bandEls=bandEls.filter(e=>!bandEls.some(o=>o!==e&&e.contains(o))); // убрать обёртки, содержащие другой band (ложный минус-отступ)
    let bands=bandEls.map(e=>{const c=getComputedStyle(e);return {sel:(e.className||e.tagName).toString().split(' ')[0],pt:parseFloat(c.paddingTop)||0,pb:parseFloat(c.paddingBottom)||0,...abs(e)};}).sort((x,y)=>x.t-y.t);
    // визуальный зазор = расстояние между КОНТЕНТОМ секций = box_gap + paddingBottom(prev) + paddingTop(curr).
    // Секции часто flush-боксами (gap=0), но разделены внутренним padding (118px) — это НЕ слипание .
    for(let i=1;i<bands.length;i++){const g=Math.round(bands[i].t-bands[i-1].b + bands[i-1].pb + bands[i].pt);
      if(g<GAP_MIN) out.section_sticking.push({between:bands[i-1].sel+' → '+bands[i].sel,gap_px:g,need:GAP_MIN});}
    const clippedByAncestor=e=>{ // элемент обрезан предком overflow≠visible, сам предок в пределах вьюпорта → за вьюпорт НЕ вылезает (напр. marquee-тикер в overflow:hidden)
      let p=e.parentElement;
      while(p&&p!==document.body){const pcs=getComputedStyle(p);
        if(pcs.overflowX!=='visible'||pcs.overflowY!=='visible'||pcs.overflowX==='clip'){const pr=p.getBoundingClientRect();return pr.right<=vw+5&&pr.left>=-5;}
        p=p.parentElement;}
      return false;};
    document.querySelectorAll('body *').forEach(e=>{const cs=getComputedStyle(e);
      if(cs.position==='fixed'||cs.visibility==='hidden'||cs.display==='none'||cs.pointerEvents==='none')return; // декор (напр. aurora) вылезает за край ПО ДИЗАЙНУ
      const b=e.getBoundingClientRect(); if(b.width<4)return;
      if((b.right>vw+5||b.left<-5)&&e.children.length<=3&&!clippedByAncestor(e))
        out.viewport_overflow.push({sel:(e.className||e.tagName).toString().split(' ')[0],left:Math.round(b.left),right:Math.round(b.right),vw});});
    const stick=[...document.querySelectorAll('[class*="note"],[class*="tag"],[class*="sticker"],[class*="badge"]')]
      .filter(e=>{const p=getComputedStyle(e).position;return p==='absolute'||p==='fixed';});
    const txt=[...document.querySelectorAll('p,h1,h2,h3,h4,li,a,button,span,[class*="title"],[class*="text"],[class*="meth"],[class*="sx"],[class*="chip"],[class*="pill"],[class*="tag"]')].filter(e=>{const t=(e.innerText||'').trim();return t&&t.length>1&&e.children.length===0;});
    const I=(p,q)=>Math.max(0,Math.min(p.right,q.right)-Math.max(p.left,q.left))*Math.max(0,Math.min(p.bottom,q.bottom)-Math.max(p.top,q.top));
    stick.forEach(s=>{const sr=s.getBoundingClientRect();txt.forEach(t=>{
      if(s.contains(t)||t.contains(s)||!t.innerText||!t.innerText.trim())return;
      // наезд считаем на РЕАЛЬНЫЕ текстовые прогоны (Range), не на бокс блока — иначе стикер над пустой частью
      // широкого <p> даёт ложняк .
      const rng=document.createRange(); rng.selectNodeContents(t);
      const rects=[...rng.getClientRects()].filter(r=>r.width>1&&r.height>1);
      let ov=0,ta=0; for(const r of rects){ov+=I(sr,r);ta+=r.width*r.height;}
      if(ta>0&&100*ov/ta>OVERLAP_MIN&&t.innerText.trim().length>3)
        out.text_overlaps.push({sticker:(s.className||'').toString().split(' ')[0],covers:(t.className||t.tagName).toString().split(' ')[0]+' «'+t.innerText.trim().slice(0,22)+'»',pct:Math.round(100*ov/ta)});});});
    document.querySelectorAll('p,h1,h2,h3,[class*="title"]').forEach(e=>{
      if(e.scrollWidth>e.clientWidth+2&&getComputedStyle(e).overflowX!=='visible')
        out.content_clipped.push({sel:(e.className||e.tagName).toString().split(' ')[0],scrollW:e.scrollWidth,clientW:e.clientWidth});});
    // F. ГЕНЕРИК container_overflow — контент вылез за СВОЙ стилизованный бокс (буква за плашку/чип/кнопку/карточку),
    //    при ЛЮБОМ overflow-режиме. Это закрывает класс целиком, а не частный случай (см. философию полноты в 09-self-review).
    // Прецедент по решению автора: текст «наставничество» торчал за float-badge — старая content_clipped его пропускала
    //    (исключала overflow:visible, а это ИМЕННО он). Детектор generic: scrollW/H > clientW/H у визуального контейнера.
    document.querySelectorAll('body *').forEach(e=>{
      const cs=getComputedStyle(e);
      if(cs.position==='fixed'||cs.display==='none'||cs.visibility==='hidden')return;
      const radius=parseFloat(cs.borderTopLeftRadius)||0;
      const hasBg=cs.backgroundColor&&cs.backgroundColor!=='rgba(0, 0, 0, 0)'&&cs.backgroundColor!=='transparent';
      const hasBorder=(parseFloat(cs.borderTopWidth)||0)>0||(parseFloat(cs.borderLeftWidth)||0)>0;
      if(!(radius>=6&&(hasBg||hasBorder)))return;            // только визуально-замкнутый компонент (плашка/чип/кнопка/карточка)
      const b=e.getBoundingClientRect();
      if(b.width<8||b.width>=vw*0.92||b.height>640)return;   // не секции/обёртки, только компоненты
      const ox=cs.overflowX,oy=cs.overflowY;
      // Флагаем ТОЛЬКО ось с overflow:visible — это «контент реально торчит наружу» (буква за плашку).
      // hidden=клип (намеренный декор-блоб в overflow:hidden даёт ложняк), auto/scroll=прокрутка — не дефект.
      const dx=(ox==='visible')?(e.scrollWidth-e.clientWidth):0;
      const dy=(oy==='visible')?(e.scrollHeight-e.clientHeight):0;
      if(dx>2||dy>2)
        out.container_overflow.push({sel:(e.className||e.tagName).toString().split(' ')[0],
          axis:dx>2?'x':'y',overflow_px:Math.max(dx,dy),scrollW:e.scrollWidth,clientW:e.clientWidth,scrollH:e.scrollHeight,clientH:e.clientHeight,
          text:(e.innerText||'').trim().slice(0,30)});
    });
    // E. орфаны — РОВНО одно слово на последней строке заголовка (честный подсчёт слов на строке через Range)
    document.querySelectorAll('h1,h2,h3,h4,[class*="title"],.rt,.note,[class*="note"],.tag,[class*="tag"],.eyebrow,[class*="badge"]').forEach(e=>{
      const full=(e.innerText||'').trim(); if(!full||full.split(/\s+/).length<3)return;
      const tw=document.createTreeWalker(e,NodeFilter.SHOW_TEXT); const words=[]; let n;
      while(n=tw.nextNode()){const s=n.nodeValue,re=/\S+/g; let m;
        while(m=re.exec(s)){const rg=document.createRange();rg.setStart(n,m.index);rg.setEnd(n,m.index+m[0].length);
          const rc=rg.getBoundingClientRect(); if(rc.width>0)words.push({w:m[0],top:Math.round(rc.top)});}}
      if(words.length<3)return;
      const lines={}; words.forEach(w=>{const k=Math.round(w.top/8)*8;(lines[k]=lines[k]||[]).push(w.w);}); // допуск 8px (плашки/трансформы)
      const tops=Object.keys(lines).map(Number).sort((a,b)=>a-b); if(tops.length<2)return; // одна строка — орфана нет
      if(lines[tops[tops.length-1]].length===1) // НЕблокирующий кандидат: намерение (акцент-плашка vs случайный отрыв) решает vision-критик (линза 5)
        out.orphan_candidates.push({sel:(e.className||e.tagName).toString().split(' ')[0],text:full.slice(0,28),orphan_word:lines[tops[tops.length-1]][0]});
    });
    // F. orphan чипа/тега — flex-wrap/grid-контейнер, где ПОСЛЕДНИЙ ряд = 1 элемент при остальных рядах ≥2
    //    .
    //    Скоуп против false-positive: ≥4 однотипных «чипов» (каждый <60% ширины контейнера, схожая высота).
    document.querySelectorAll('*').forEach(c=>{
      const cs=getComputedStyle(c);
      const flexWrap=cs.display.indexOf('flex')>=0&&cs.flexWrap==='wrap';
      const grid=cs.display.indexOf('grid')>=0;
      if(!flexWrap&&!grid)return;
      const kids=[...c.children].filter(k=>{const ks=getComputedStyle(k);return ks.display!=='none'&&k.getClientRects().length;});
      if(kids.length<4)return;
      const boxes=kids.map(k=>k.getBoundingClientRect());
      const cw=c.getBoundingClientRect().width; if(cw<1)return;
      if(!boxes.every(b=>b.width>0&&b.width<cw*0.6))return; // несколько в ряд = «чипы», не блок-строки
      const h0=boxes[0].height; if(!boxes.every(b=>Math.abs(b.height-h0)<=6))return; // однотипные
      const rows={}; boxes.forEach(b=>{const k=Math.round(b.top/8)*8;rows[k]=(rows[k]||0)+1;});
      const tops=Object.keys(rows).map(Number).sort((a,b)=>a-b); if(tops.length<2)return;
      const counts=tops.map(t=>rows[t]);
      if(counts[counts.length-1]===1&&Math.max(...counts)>=2)
        out.flexitem_orphan.push({sel:(c.className||c.tagName).toString().split(' ')[0],items:kids.length,rows:counts.join('+'),lone:(kids[kids.length-1].innerText||'').trim().slice(0,18)});
    });
    // G. touch-target ≥24×24px (WCAG 2.2 SC 2.5.8) — отдельный кликабельный мельче 24px = промах на тач
    document.querySelectorAll('a[href],button,[role="button"],input:not([type="hidden"]),select,label[for]').forEach(e=>{
      const cs=getComputedStyle(e); if(cs.display==='none'||cs.display==='inline'||cs.visibility==='hidden'||!e.getClientRects().length)return;
      const b=e.getBoundingClientRect();
      if(b.width>=1&&b.height>=1&&(b.width<24||b.height<24))
        out.touch_targets.push({sel:(e.className||e.tagName).toString().split(' ')[0],w:Math.round(b.width),h:Math.round(b.height),text:(e.innerText||e.value||'').trim().slice(0,18)});
    });
    // H. <img> без явных размеров/aspect-ratio → reflow/CLS при загрузке
    document.querySelectorAll('img').forEach(e=>{
      const cs=getComputedStyle(e);
      if((e.getAttribute('width')&&e.getAttribute('height'))||(cs.aspectRatio&&cs.aspectRatio!=='auto'))return;
      if(e.getBoundingClientRect().width>40) out.image_dims.push({src:(e.currentSrc||e.src||'').split('/').pop().slice(0,28),reason:'нет width/height и aspect-ratio'});
    });
    // ───────── ПЕРФ-ПОЛ (mobile-first): скорость загрузки. Считаем на ВЕДУЩЕЙ мобильной ширине ─────────
    // (≤480) — «на мобилке грузиться максимально быстро» важнее всего (распоряжение автора). Десктоп
    // эти классы НЕ флагает (perfOut пуст), чтобы не дублировать. HARD-классы — нуль-FP, всегда правимы.
    if(PERF && vw<=480){
      // I. render-blocking <script src> в <head> без defer/async/module → блокирует первый рендер (моб особенно).
      if(document.head) document.head.querySelectorAll('script[src]').forEach(s=>{
        const t=(s.getAttribute('type')||'').toLowerCase();
        if(!s.defer && !s.async && t!=='module' && t!=='application/json' && t!=='application/ld+json')
          out.render_blocking.push({src:(s.getAttribute('src')||'').split('/').pop().slice(0,40),reason:'<script> в <head> без defer/async'});
      });
      // II. font-display: валиден ТОЛЬКО swap|fallback. optional раньше пропускался, но это FOIT/FOUT-риск
      //    (optional = браузер даёт шрифту ~100мс, не успел → НАВСЕГДА fallback на этой загрузке; текст «прыгает»/не тот шрифт).
      // автор: optional убран из разрешённого → флаг (HARD через тот же ключ font_display).
      try{ for(const ss of document.styleSheets){ let rules; try{rules=ss.cssRules;}catch(e){continue;} if(!rules)continue;
        for(const rl of rules){ if(rl.type===5 && rl.style){ const fd=(rl.style.getPropertyValue('font-display')||'').trim().toLowerCase();
          if(fd==='optional') out.font_display.push({family:(rl.style.getPropertyValue('font-family')||'?').replace(/["']/g,'').slice(0,30),reason:'@font-face font-display:optional (FOIT/FOUT-риск — нужен swap)'});
          else if(!/^(swap|fallback)$/.test(fd)) out.font_display.push({family:(rl.style.getPropertyValue('font-family')||'?').replace(/["']/g,'').slice(0,30),reason:'@font-face без font-display:swap (FOIT)'}); }}}
      }catch(e){}
      document.querySelectorAll('link[rel="stylesheet"][href*="fonts.googleapis.com"],link[rel="preload"][as="font"]').forEach(l=>{
        const h=l.getAttribute('href')||''; if(!/fonts\.googleapis\.com/.test(h))return;
        const dm=h.match(/display=(swap|optional|fallback)/);
        if(dm && dm[1]==='optional') out.font_display.push({family:'google-fonts',reason:'link &display=optional (FOIT/FOUT-риск — нужен swap)'});
        else if(!dm || !/display=(swap|fallback)/.test(h)) out.font_display.push({family:'google-fonts',reason:'link без &display=swap'}); });
      // III. <img> заведомо ниже сгиба (top > 1.5×высоты вьюпорта) без loading=lazy → грузится впустую, тормозит первый экран.
      const vh=innerHeight;
      document.querySelectorAll('img').forEach(e=>{ const b=e.getBoundingClientRect(); if(b.width<40||b.height<40)return;
        const top=b.top+scrollY; const lz=(e.getAttribute('loading')||'').toLowerCase();
        if(top>vh*1.5 && lz!=='lazy') out.img_offscreen_eager.push({src:(e.currentSrc||e.src||'').split('/').pop().slice(0,28),top:Math.round(top),reason:'ниже сгиба без loading=lazy'}); });
      // IV. вес страницы (advisory по умолчанию; HARD только при --weight-budget>0) — суммарный объём ресурсов, что качает моб.
      let weight=0; try{ for(const e of performance.getEntriesByType('resource')) weight += (e.decodedBodySize||e.encodedBodySize||e.transferSize||0); }catch(e){}
      out._perf = { weight_kb: Math.round(weight/1024), requests: (performance.getEntriesByType('resource')||[]).length, dom_nodes: document.querySelectorAll('*').length };
      if(WEIGHT_BUDGET_KB>0 && out._perf.weight_kb>WEIGHT_BUDGET_KB)
        out.weight_over_budget.push({weight_kb:out._perf.weight_kb,budget_kb:WEIGHT_BUDGET_KB,reason:'вес мобильной страницы превышает бюджет'});
    }
    // ───────── ДИЗАЙН-СИСТЕМА / ТЕМА (НЕ mobile-only; считаем на каждой ширине, тема может быть адаптивной) ─────────
    // Хелперы цвета: парс любого цвет-значения в {r,g,b,a}; относительная яркость (WCAG); HSL-насыщенность.
    const parseColor=(s)=>{ if(!s)return null; s=s.trim().toLowerCase();
      if(s==='transparent')return {r:0,g:0,b:0,a:0};
      let m=s.match(/^#([0-9a-f]{3,8})$/);
      if(m){let h=m[1]; if(h.length===3)h=h.split('').map(c=>c+c).join(''); if(h.length===4)h=h.slice(0,3).split('').map(c=>c+c).join('')+h.slice(3).repeat(2);
        if(h.length===6)return {r:parseInt(h.slice(0,2),16),g:parseInt(h.slice(2,4),16),b:parseInt(h.slice(4,6),16),a:1};
        if(h.length===8)return {r:parseInt(h.slice(0,2),16),g:parseInt(h.slice(2,4),16),b:parseInt(h.slice(4,6),16),a:parseInt(h.slice(6,8),16)/255};}
      m=s.match(/rgba?\(([^)]+)\)/);
      if(m){const p=m[1].split(/[ ,/]+/).filter(Boolean).map(parseFloat); if(p.length>=3)return {r:p[0],g:p[1],b:p[2],a:p[3]==null?1:p[3]};}
      // современные цвет-функции (oklch/oklab/lab/lch/color/hwb) Chromium отдаёт как есть —
      // нормализуем через canvas fillStyle в rgb/hex, иначе тёмная неонка на oklch обходит детект (ре-ревью 3)
      if(/^(oklch|oklab|lab|lch|color|hwb)\(/.test(s)){ try{ const cv=document.createElement('canvas').getContext('2d'); cv.fillStyle='#000'; cv.fillStyle=s; const o=cv.fillStyle; if(o&&o!==s)return parseColor(o); }catch(e){} }
      return null; };
    const lum=(c)=>{ const f=v=>{v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4);}; return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
    const sat=(c)=>{ const r=c.r/255,g=c.g/255,b=c.b/255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2; if(mx===mn)return 0; return l>0.5?(mx-mn)/(2-mx-mn):(mx-mn)/(mx+mn); };
    // J. dark-ai-theme: доминирующий фон по ПЛОЩАДИ. Тёмная ВСЯ страница (взвеш. яркость < порог) + есть высоконасыщенный неон → флаг.
    //    Локальная тёмная секция (spotlight) на светлой странице не триггерит: она проигрывает по суммарной площади светлому фону.
    try{
      const blocks=[...document.querySelectorAll('body, body *')].filter(e=>{const cs=getComputedStyle(e);
        if(cs.display==='none'||cs.visibility==='hidden')return false; const b=e.getBoundingClientRect(); return b.width>40&&b.height>40;});
      let totA=0,wLum=0; const vhh=innerHeight;
      blocks.forEach(e=>{ const cs=getComputedStyle(e); const bg=parseColor(cs.backgroundColor); if(!bg||bg.a<0.5)return;
        const b=e.getBoundingClientRect(); const visT=Math.max(0,Math.min(b.bottom,vhh)-Math.max(b.top,0)); const a=b.width*visT; if(a<=0)return;
        totA+=a; wLum+=lum(bg)*a; });
      const avgLum= totA>0 ? wLum/totA : 1;
      // неоновый акцент: насыщенный (>0.55) цвет текста/границы/фона у заметного элемента.
      // lum>0.12 (а не 0.25): ловит холодные AI-slop акценты средней светлоты (blue-600 lum≈0.15,
      // violet≈0.20) — ре-ревью по решению автора. Срабатывает только на ТЁМНОЙ странице (avgLum<0.18),
      // поэтому тёплый светлый бренд автора не задевается.
      let neon=null;
      for(const e of blocks){ const cs=getComputedStyle(e);
        for(const prop of ['color','backgroundColor','borderTopColor']){ const c=parseColor(cs[prop]); if(c&&c.a>0.6&&sat(c)>0.55&&lum(c)>0.12&&lum(c)<0.85){neon={prop,rgb:`rgb(${c.r},${c.g},${c.b})`};break;} }
        if(neon)break; }
      if(totA>0 && avgLum<0.18 && neon)
        out.dark_ai_theme.push({avg_bg_luminance:Math.round(avgLum*1000)/1000,neon_accent:neon.rgb,reason:'тёмная тема всей страницы + неоновый акцент (AI-slop тёмная тема)'});
    }catch(e){}
    // K. hardcoded-colors (WARNING — FP-риск): доля цвет-литералов вне var(--token) выше порога.
    //    Считаем по ТЕКСТУ правил стайлшитов: значения color/background/border-color, литерал (#/rgb/hsl) vs var(--...).
    try{
      let litCount=0, varCount=0; const samples=[];
      const COLORPROP=/(?:^|[\s;{])(color|background-color|background|border(?:-top|-right|-bottom|-left)?-color|fill|stroke|outline-color)\s*:\s*([^;}]+)/gi;
      for(const ss of document.styleSheets){ let rules; try{rules=ss.cssRules;}catch(e){continue;} if(!rules)continue;
        for(const rl of rules){ if(rl.type!==1||!rl.style||!rl.cssText)continue; let m;
          const ct=rl.cssText; COLORPROP.lastIndex=0;
          while(m=COLORPROP.exec(ct)){ const val=m[2].trim().toLowerCase();
            if(/^(transparent|inherit|currentcolor|none|unset|initial)$/.test(val))continue;
            const hasVar=/var\(\s*--/.test(val);
            const hasLit=/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i.test(val);
            if(hasVar) varCount++;
            else if(hasLit){ litCount++; if(samples.length<8)samples.push((rl.selectorText||'?').slice(0,30)+' {'+m[1]+'}'); }
          } } }
      const tot=litCount+varCount;
      if(tot>=12 && litCount/tot>0.4)
        out.hardcoded_colors.push({hardcoded:litCount,tokenized:varCount,ratio:Math.round(100*litCount/tot)/100,samples:samples.slice(0,5),reason:'много цветов литералами вместо var(--token) (дизайн-система не на токенах)'});
    }catch(e){}
    // L. css-dup-selector (WARNING — FP-риск): один и тот же class-селектор в РАЗНЫХ правилах пере-определяет ОДНО свойство.
    //    Не путать с легитимным @media-override → правила внутри media пропускаем (parentRule type 4).
    try{
      const seen={}; // selector → {prop → count}
      const dups=[];
      const walk=(rules)=>{ for(const rl of rules){ if(rl.type!==1||!rl.selectorText||!rl.style)continue;
        // только одиночный class-селектор (.foo), без комбинаторов/составных — чтобы не ловить .a .b и .a:hover как «дубль»
        const sels=rl.selectorText.split(',').map(s=>s.trim()).filter(s=>/^\.[A-Za-z0-9_-]+$/.test(s));
        for(const sel of sels){ const rec=seen[sel]=seen[sel]||{props:{},files:0}; rec.files++;
          for(let i=0;i<rl.style.length;i++){ const p=rl.style[i]; rec.props[p]=(rec.props[p]||0)+1; } } } };
      for(const ss of document.styleSheets){ let rules; try{rules=ss.cssRules;}catch(e){continue;} if(!rules)continue; walk(rules); }
      for(const sel in seen){ const rec=seen[sel]; if(rec.files<2)continue;
        const reprops=Object.keys(rec.props).filter(p=>rec.props[p]>1);
        if(reprops.length) dups.push({selector:sel,rules:rec.files,redefined_props:reprops.slice(0,6)});
      }
      if(dups.length) out.css_dup_selector.push(...dups.slice(0,10).map(d=>({...d,reason:'class-селектор переопределён в нескольких правилах (каскад-коллизия)'})));
    }catch(e){}
    return out;
  },{GAP_MIN,OVERLAP_MIN,SECTION_SEL,PERF,WEIGHT_BUDGET_KB});
  r.cls = Math.round((await page.evaluate(()=>window.__cls||0))*1000)/1000; // CLS за окно загрузки (порог 0.1; transform/opacity не считаются)
  r.lcp_ms = Math.round(await page.evaluate(()=>window.__lcp||0)); // LCP (advisory; на file:// близок к 0, на live-URL информативен)
  // Слой 1: axe-core (контраст + a11y), если установлен в проекте
  try { const _axe = require('@axe-core/playwright'); const AxeBuilder = _axe.AxeBuilder || _axe.default;
    const ax = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa']).analyze();
    r.axe_violations = ax.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length}));
  } catch(e){ r.axe = /Cannot find|ERR_MODULE/.test(e.message||'') ? 'skip: npm i -D @axe-core/playwright' : 'axe error: '+(e.message||'').split(String.fromCharCode(10))[0]; }
  const n=r.section_sticking.length+r.text_overlaps.length+r.viewport_overflow.length+r.content_clipped.length+r.container_overflow.length+r.touch_targets.length+r.image_dims.length+r.orphan_candidates.length+r.flexitem_orphan.length+(r.cls>0.1?1:0)+((r.axe_violations||[]).filter(v=>v.impact==='serious'||v.impact==='critical').length)+(r.render_blocking||[]).length+(r.font_display||[]).length+(r.img_offscreen_eager||[]).length+(r.weight_over_budget||[]).length+(r.dark_ai_theme||[]).length; // orphan (текст И чип) БЛОКИРУЕТ + перф-пол (render-blocking/FOIT-шрифт/offscreen-img без lazy/вес-сверх-бюджета) + dark_ai_theme HARD. hardcoded_colors/css_dup_selector = WARNING (FP-риск) — НЕ в defects-счётчике, не блокируют
  report.widths[w]=r; report.summary.defects+=n; await context.close();
}
await browser.close();
console.log(JSON.stringify(report,null,2));
process.exit(report.summary.defects>0?1:0);
