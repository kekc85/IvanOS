import json,os,sys,urllib.request,datetime
# Граб идёт под ТВОИМ IG-аккаунтом (подключён в онбординге, ветка cookies). Риск бана на тебе.
# Безопаснее ветка Apify (аккаунт вне цепочки).
ckf=os.path.expanduser("~/.business/processes/.ig-cookies.json")
if not os.path.exists(ckf):
    print("Сначала подключи свой IG (ветка cookies), либо выбери Apify", file=sys.stderr)
    sys.exit(3)
# Парсер свежих РОЛИКОВ (Reels, media_type==2) аккаунта IG через private API + cookie.
# Близнец account_fresh_carousels.py, но под видео-ролики для конвейера replicate-viral.
# Использование: python3 account_fresh_reels.py <handle> [maxage_days=14] [min_views=0]
ckf=os.path.expanduser("~/.business/processes/.ig-cookies.json")
cookies=json.load(open(ckf)); ckstr="; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('name'))
hdr={"User-Agent":"Instagram 219.0.0.12.117 Android","x-ig-app-id":"936619743392459","Cookie":ckstr}
def get(url): return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=hdr),timeout=25))
handle=sys.argv[1].lstrip("@")
maxage=int(sys.argv[2]) if len(sys.argv)>2 else 14
minviews=int(sys.argv[3]) if len(sys.argv)>3 else 0
def views(it):
    for k in ("play_count","ig_play_count","view_count"):
        if it.get(k): return it[k]
    return 0
try:
    prof=get(f"https://www.instagram.com/api/v1/users/web_profile_info/?username={handle}")
    uid=prof["data"]["user"]["id"]
    feed=get(f"https://www.instagram.com/api/v1/feed/user/{uid}/?count=24")
except Exception as e:
    print(f"#ERR {handle} {str(e)[:60]}"); sys.exit(0)
now=datetime.datetime.now(datetime.timezone.utc)
rows=[]
for it in feed.get("items",[]):
    if it.get("media_type")!=2: continue  # 2 = video/reel
    ts=it.get("taken_at",0); age=(now-datetime.datetime.fromtimestamp(ts,datetime.timezone.utc)).days
    if age>maxage: continue
    vw=views(it)
    if vw<minviews: continue
    lk=it.get("like_count",0); cm=it.get("comment_count",0); sc=it.get("code","")
    dur=round(it.get("video_duration",0),1)
    vv=it.get("video_versions") or []
    vurl=vv[0]["url"] if vv else ""
    cap=(it.get("caption") or {}).get("text","")[:90].replace("\n"," ").replace("\t"," ")
    dt=datetime.datetime.fromtimestamp(ts,datetime.timezone.utc).strftime("%Y-%m-%d")
    rows.append((vw,age,dt,lk,cm,dur,sc,cap,vurl))
rows.sort(reverse=True)  # по просмотрам
for vw,age,dt,lk,cm,dur,sc,cap,vurl in rows:
    link=f"https://www.instagram.com/reel/{sc}/"
    print(f"{handle}\t{dt}\t{age}d\t{vw}vw\t{lk}lk\t{cm}cm\t{dur}s\t{link}\t{cap}\t{vurl}")
if not rows: print(f"#NONE {handle} (нет роликов media_type==2 за {maxage}д / min {minviews}vw)")
