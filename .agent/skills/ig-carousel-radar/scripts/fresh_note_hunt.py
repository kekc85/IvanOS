import asyncio,json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent)); import radar
from playwright.async_api import async_playwright
from datetime import datetime,timezone
SEARCHES=["I let claude run my","I gave claude access","claude made this post","I let claude write",
          "claude runs my instagram","I gave claude my","claude grew my account","I let claude manage",
          "claude posted this","handwritten claude notes","I connected claude"]
AB="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
ck=json.load(open(str(Path.home()/'.business/processes/.ig-cookies.json')))
ckstr='; '.join(f"{c['name']}={c['value']}" for c in ck if c.get('name'))
hdr={'User-Agent':'Mozilla/5.0','x-ig-app-id':'936619743392459','Cookie':ckstr}
def info(sc):
    mid=0
    for c in sc: mid=mid*64+AB.index(c)
    try:
        it=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://www.instagram.com/api/v1/media/{mid}/info/",headers=hdr),timeout=15).read())["items"][0]
        t=it.get('taken_at',0); age=(datetime.now(timezone.utc)-datetime.fromtimestamp(t,tz=timezone.utc)).days if t else 999
        return it.get('like_count',0),it.get('comment_count',0),age,(it.get('user') or {}).get('username','')
    except: return 0,0,999,''
async def main():
    radar.refresh_cookies_from_chrome(); cookies=radar.load_cookies(); done=radar.load_done_shortcodes()
    async with async_playwright() as pw:
        b=await pw.chromium.launch(headless=True)
        ctx=await b.new_context(user_agent=hdr['User-Agent'],viewport={"width":1280,"height":900})
        await ctx.add_cookies(cookies)
        caps=await radar.mode_d_search(ctx,SEARCHES,30); await b.close()
    seen={c.shortcode:c for c in caps if c.is_carousel and c.shortcode and c.shortcode not in done}
    rows=[]
    for sc in list(seen)[:120]:
        l,cm,age,h=info(sc)
        if age<=12 and (l>=800 or cm>=400): rows.append((age,l,cm,h,sc))
    rows.sort(key=lambda r:(r[1]+r[2]*3),reverse=True)
    print(f"FRESH+VIRAL note candidates: {len(rows)}")
    for age,l,cm,h,sc in rows: print(f"{age}d {l}L {cm}C @{h} https://instagram.com/p/{sc}/")
asyncio.run(main())
