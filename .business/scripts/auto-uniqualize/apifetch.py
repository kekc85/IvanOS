#!/usr/bin/env python3
import json, sys, urllib.request, os
# Граб идёт под ТВОИМ IG-аккаунтом (подключён в онбординге, ветка cookies). Риск бана на тебе.
# Безопаснее ветка Apify (аккаунт вне цепочки).
ckf=os.path.expanduser("~/.business/processes/.ig-cookies.json")
if not os.path.exists(ckf):
    print("Сначала подключи свой IG (ветка cookies), либо выбери Apify", file=sys.stderr)
    sys.exit(3)
shortcode = sys.argv[1]; out = sys.argv[2]
os.makedirs(out, exist_ok=True)
# shortcode -> media_id
AB='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
mid=0
for c in shortcode: mid=mid*64+AB.index(c)
# cookies
ckf=os.path.expanduser("~/.business/processes/.ig-cookies.json")
cookies=json.load(open(ckf))
ckstr="; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('name'))
hdr={"User-Agent":"Mozilla/5.0","x-ig-app-id":"936619743392459","Cookie":ckstr,"x-requested-with":"XMLHttpRequest"}
url=f"https://www.instagram.com/api/v1/media/{mid}/info/"
req=urllib.request.Request(url, headers=hdr)
try:
    d=json.load(urllib.request.urlopen(req, timeout=25))
except Exception as e:
    print("API err:", e); sys.exit(1)
items=d.get("items",[{}])[0]
kids=items.get("carousel_media") or [items]
print("media_id", mid, "| слайдов в API:", len(kids))
n=0; vids=[]
for i,k in enumerate(kids,1):
    # ВИДЕО-СЛАЙД (media_type==2 / есть video_versions): качаем ВИДЕО, не статику-постер.
    # Иначе видео-карусель превращалась в скриншоты = брак (автор).
    vv=k.get("video_versions")
    if vv:
        u=max(vv, key=lambda c:c.get("width",0))["url"]
        try:
            rq=urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"})
            open(f"{out}/slide-{i:02d}.mp4","wb").write(urllib.request.urlopen(rq,timeout=90).read())
            vids.append(i); n+=1; continue
        except Exception as e: print(" video dl err", e)
    cands=k.get("image_versions2",{}).get("candidates",[])
    if not cands: continue
    u=max(cands, key=lambda c:c.get("width",0))["url"]
    try:
        rq=urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"})
        open(f"{out}/slide-{i:02d}.jpg","wb").write(urllib.request.urlopen(rq,timeout=25).read()); n+=1
    except Exception as e: print(" dl err", e)
# пометка какие слайды ВИДЕО (для driver/overlay): _video_slides.txt
if vids:
    open(f"{out}/_video_slides.txt","w").write(",".join(f"{i:02d}" for i in vids))
    print("ВИДЕО-слайды:", vids, "(для video-карусели: наш текст накладывается поверх оригинального через video_overlay.py)")
print("скачано:", n)
