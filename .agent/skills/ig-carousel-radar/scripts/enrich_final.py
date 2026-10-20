#!/usr/bin/env python3
"""Дотягивает точные метрики финального шорт-листа через IG media-info API:
like_count, comment_count, taken_at (дата), типы слайдов (фото/видео)."""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COOKIES = Path.home() / ".business" / "processes" / ".ig-cookies.json"
AB = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

SHORTCODES = sys.argv[1].split(",") if len(sys.argv) > 1 else []

ck = json.loads(COOKIES.read_text())
ckstr = "; ".join(f"{c['name']}={c['value']}" for c in ck if c.get("name"))
hdr = {"User-Agent": "Mozilla/5.0", "x-ig-app-id": "936619743392459",
       "Cookie": ckstr, "x-requested-with": "XMLHttpRequest"}

out = []
for sc in SHORTCODES:
    sc = sc.strip()
    if not sc:
        continue
    mid = 0
    for chx in sc:
        mid = mid * 64 + AB.index(chx)
    rec = {"shortcode": sc}
    try:
        req = urllib.request.Request(
            f"https://www.instagram.com/api/v1/media/{mid}/info/", headers=hdr)
        it = json.loads(urllib.request.urlopen(req, timeout=20).read())["items"][0]
        rec["author"] = (it.get("user") or {}).get("username", "")
        rec["likes"] = it.get("like_count", 0)
        rec["comments"] = it.get("comment_count", 0)
        rec["views"] = it.get("play_count") or it.get("ig_play_count") or it.get("view_count") or 0
        taken = it.get("taken_at", 0)
        rec["date"] = (datetime.fromtimestamp(taken, tz=timezone.utc).strftime("%Y-%m-%d")
                       if taken else "")
        carousel = it.get("carousel_media") or []
        if carousel:
            types = [m.get("media_type") for m in carousel]
            vids = sum(1 for t in types if t == 2)
            rec["slides"] = len(types)
            rec["media"] = "фото" if vids == 0 else f"видео ({vids}/{len(types)})"
        else:
            mt = it.get("media_type")
            rec["slides"] = 1
            rec["media"] = "фото" if mt == 1 else ("видео" if mt == 2 else f"тип {mt}")
    except Exception as e:
        rec["error"] = str(e)[:80]
    out.append(rec)
    time.sleep(0.5)

print(json.dumps(out, ensure_ascii=False, indent=2))