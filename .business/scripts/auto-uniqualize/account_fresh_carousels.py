import json,os,sys,urllib.request,datetime
# 🛑 ГАРД анти-бан (автор): приватный IG-API под ОСНОВНЫМ аккаунтом <твой-хэндл> ЗАПРЕЩЁН
# (.ig-cookies.json + private API = триггер checkpoint-бана). Burner + явное «да» → IVAN_ALLOW_BURNER_IG=1.
if os.environ.get("IVAN_ALLOW_BURNER_IG") != "1":
    sys.stderr.write("🛑 СТОП: приватный IG-API под основным аккаунтом запрещён (правило автора «больше банов никогда»). Burner + явное «да» → IVAN_ALLOW_BURNER_IG=1.\n")
    sys.exit(3)
ckf=os.path.expanduser("~/.business/processes/.ig-cookies.json")
cookies=json.load(open(ckf)); ckstr="; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('name'))
hdr={"User-Agent":"Instagram 219.0.0.12.117 Android","x-ig-app-id":"936619743392459","Cookie":ckstr}
def get(url): return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=hdr),timeout=25))
handle=sys.argv[1].lstrip("@"); maxage=int(sys.argv[2]) if len(sys.argv)>2 else 5
try:
    prof=get(f"https://www.instagram.com/api/v1/users/web_profile_info/?username={handle}")
    uid=prof["data"]["user"]["id"]
    feed=get(f"https://www.instagram.com/api/v1/feed/user/{uid}/?count=20")
except Exception as e:
    print(f"#ERR {handle} {str(e)[:50]}"); sys.exit(0)
now=datetime.datetime.now(datetime.timezone.utc)
for it in feed.get("items",[]):
    if it.get("media_type")!=8: continue
    ts=it.get("taken_at",0); age=(now-datetime.datetime.fromtimestamp(ts,datetime.timezone.utc)).days
    if age>maxage: continue
    lk=it.get("like_count",0); cm=it.get("comment_count",0); sc=it.get("code","")
    n=len(it.get("carousel_media",[]))
    cap=(it.get("caption") or {}).get("text","")[:95].replace("\n"," ").replace("\t"," ")
    # УРОК по решению автора: collab-пост в фиде имеет чужого owner (talnavarro1 -> @iamavatal, фэшн).
    # Маркируем, чтобы отбор сразу видел чужой контент и не жёг prep на нетематику.
    ou=((it.get("user") or {}).get("username") or "").lstrip("@")
    mark=f"\tCOLLAB:@{ou}" if ou and ou.lower()!=handle.lower() else ""
    print(f"{handle}\t{age}d\t{lk}\t{cm}\t{n}sl\t{sc}\t{cap}{mark}")
