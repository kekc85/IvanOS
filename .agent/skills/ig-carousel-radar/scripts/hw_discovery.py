#!/usr/bin/env python3
"""Широкий визуальный поиск ВИРАЛЬНЫХ каруселей в формате ЗАМЕТКИ (рукопись синей ручкой
на бумаге / текст-заметка). Хэштеги + Explore-поиск БЕЗ вирал-фильтра, качает slide-1 всех,
ранжирует по вовлечённости, собирает контактные листы PIL для глазного скана.
НЕ генерит и НЕ сочиняет - только находит реальные посты со ссылками."""
import asyncio, json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import radar
from playwright.async_api import async_playwright
from PIL import Image

TAGS = ["нейросети","нейросеть","chatgptрусский","искусственныйинтеллект","ииинструменты",
        "клод","нейросетидлябизнеса","промпты","заметки","вайбкодинг","aiдлябизнеса",
        "нейросетидляконтента","чатгпт","ботнейросеть","ainotes","handwrittennotes"]
SEARCHES = ["нейросети заметки","claude заметки","чатгпт промпты","нейросеть бизнес",
            "ии заметки","claude от руки","нейросети для контента","рукописные заметки ии"]
PER_TAG = 36
PER_KW = 24
OUT = Path("/tmp/hw-discovery3"); OUT.mkdir(exist_ok=True)
THUMBS = OUT / "thumbs"; THUMBS.mkdir(exist_ok=True)

async def main():
    radar.refresh_cookies_from_chrome()
    cookies = radar.load_cookies()
    done = radar.load_done_shortcodes()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width":1280,"height":900})
        await ctx.add_cookies(cookies)
        caps = await radar.mode_c_hashtag(ctx, TAGS, PER_TAG)
        try:
            caps += await radar.mode_d_search(ctx, SEARCHES, PER_KW)
        except Exception as e:
            radar.log(f"[hw2] search err {e}")
        await browser.close()

    seen = {}
    for c in caps:
        if c.is_carousel and c.shortcode and c.slide_1_url and c.shortcode not in done:
            if c.shortcode not in seen or (c.likes+c.comments) > (seen[c.shortcode].likes+seen[c.shortcode].comments):
                seen[c.shortcode] = c
    # rank by engagement DESC (виральность)
    items = sorted(seen.values(), key=lambda c: (c.likes + c.comments*3), reverse=True)
    radar.log(f"[hw2] {len(items)} unique fresh carousels (ranked by engagement)")

    idx = []
    for i, c in enumerate(items):
        p = THUMBS / f"{i:03d}.jpg"
        try:
            req = urllib.request.Request(c.slide_1_url, headers={"User-Agent":"Mozilla/5.0"})
            p.write_bytes(urllib.request.urlopen(req, timeout=20).read())
            idx.append((i, c.author, c.shortcode, c.likes, c.comments))
        except Exception:
            pass
    radar.log(f"[hw2] downloaded {len(idx)} thumbs")

    COLS, ROWS, CW, CH = 6, 5, 260, 325
    per = COLS*ROWS; sheets = 0
    for s in range(0, len(idx), per):
        chunk = idx[s:s+per]
        sheet = Image.new("RGB", (COLS*CW, ROWS*CH), (30,30,30))
        for j,(i,_,_,_,_) in enumerate(chunk):
            try:
                im = Image.open(THUMBS/f"{i:03d}.jpg").convert("RGB"); im.thumbnail((CW-8,CH-8))
                sheet.paste(im, ((j%COLS)*CW+4, (j//COLS)*CH+4))
            except Exception: pass
        sheet.save(OUT/f"sheet-{sheets:02d}.jpg", quality=80); sheets += 1
    (OUT/"index.json").write_text(json.dumps([{"i":i,"h":h,"sc":sc,"l":l,"c":cm} for i,h,sc,l,cm in idx], ensure_ascii=False))
    print(f"SHEETS={sheets} ITEMS={len(idx)}")
    for i,h,sc,l,cm in idx:
        print(f"{i:03d}\t{l}L {cm}C\t@{h}\t{sc}")

if __name__ == "__main__":
    asyncio.run(main())