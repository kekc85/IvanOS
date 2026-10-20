#!/usr/bin/env python3
"""Поиск ЖАНРА рукописных заметок-экспериментов ('I connected/gave Claude to X -> result -> steps')
по зарубежным аккаунтам. mode_d_search по фразам жанра + grab slide-1 + montage для глазного скана."""
import asyncio, json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import radar
from playwright.async_api import async_playwright
from PIL import Image

SEARCHES = ["I connected claude to my instagram","I gave claude","claude grew my instagram",
            "I let claude run","I asked claude to make me","claude faceless instagram",
            "I connected claude","claude content account","handwritten claude"]
PER_KW = 30
OUT = Path("/tmp/genre-hunt"); OUT.mkdir(exist_ok=True)
THUMBS = OUT/"thumbs"; THUMBS.mkdir(exist_ok=True)

async def main():
    radar.refresh_cookies_from_chrome()
    cookies = radar.load_cookies()
    done = radar.load_done_shortcodes()
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        ctx = await b.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width":1280,"height":900})
        await ctx.add_cookies(cookies)
        caps = await radar.mode_d_search(ctx, SEARCHES, PER_KW)
        await b.close()
    seen={}
    for c in caps:
        if c.is_carousel and c.shortcode and c.slide_1_url and c.shortcode not in done:
            if c.shortcode not in seen or (c.likes+c.comments)>(seen[c.shortcode].likes+seen[c.shortcode].comments):
                seen[c.shortcode]=c
    items=sorted(seen.values(), key=lambda c:(c.likes+c.comments*3), reverse=True)
    radar.log(f"[genre] {len(items)} carousels")
    idx=[]
    for i,c in enumerate(items):
        try:
            req=urllib.request.Request(c.slide_1_url, headers={"User-Agent":"Mozilla/5.0"})
            (THUMBS/f"{i:03d}.jpg").write_bytes(urllib.request.urlopen(req,timeout=20).read())
            idx.append((i,c.author,c.shortcode,c.likes,c.comments))
        except Exception: pass
    COLS,ROWS,CW,CH=6,5,260,325; per=COLS*ROWS; s=0
    for st in range(0,len(idx),per):
        sh=Image.new("RGB",(COLS*CW,ROWS*CH),(30,30,30))
        for j,(i,_,_,_,_) in enumerate(idx[st:st+per]):
            try:
                im=Image.open(THUMBS/f"{i:03d}.jpg").convert("RGB"); im.thumbnail((CW-8,CH-8))
                sh.paste(im,((j%COLS)*CW+4,(j//COLS)*CH+4))
            except Exception: pass
        sh.save(OUT/f"sheet-{s:02d}.jpg",quality=80); s+=1
    (OUT/"index.json").write_text(json.dumps([{"i":i,"h":h,"sc":sc,"l":l,"c":cm} for i,h,sc,l,cm in idx],ensure_ascii=False))
    print(f"SHEETS={s} ITEMS={len(idx)}")
    for i,h,sc,l,cm in idx: print(f"{i:03d}\t{l}L {cm}C\t@{h}\t{sc}")

if __name__=="__main__": asyncio.run(main())