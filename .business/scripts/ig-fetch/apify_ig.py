#!/usr/bin/env python3
"""ig-fetch: безопасный канал Instagram-данных через Apify (аккаунт и IP автора вне цепочки).

Зачем: после банов в даты запуска и заморозки профиля по решению автора НИКАКОЙ парсинг не идёт
ни под cookies автора, ни с его IP. Всё публичное берём через Apify-акторы
(их инфраструктура, их сессии), картинки потом докачиваем с CDN бесплатно.

Токен: env APIFY_TOKEN или ~/.claude/.env (канон-место, его же читает raspoznavalka-postov).

Команды:
  post <url|shortcode>                  метаданные поста одним JSON в stdout
  carousel <url|shortcode> [outdir]     скачать фото-карусель в слайды slide-NN.jpg
                                        + caption.txt + _source_url.txt (формат auto-uniqualize)
  profile <username> [limit]            посты профиля с метриками, JSONL в stdout

Стоимость: ~$0.0023-0.0027 за пост (pay-per-event apify/instagram-scraper).
Каждый запуск печатает фактический cost в stderr.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.apify.com/v2"
ACTOR = "apify~instagram-scraper"
RUN_TIMEOUT_SEC = 300
POLL_SEC = 4


def token() -> str:
    t = os.environ.get("APIFY_TOKEN", "").strip()
    if not t:
        env_path = os.path.expanduser("~/.claude/.env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("APIFY_TOKEN="):
                    t = line.split("=", 1)[1].strip()
                    break
    if not t:
        sys.exit("APIFY_TOKEN не найден ни в env, ни в ~/.claude/.env")
    return t


def _req(url: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def run_actor(run_input: dict) -> tuple[list[dict], float]:
    """Запустить актор, дождаться, вернуть (items, cost_usd)."""
    t = token()
    run = _req(f"{API}/acts/{ACTOR}/runs?token={t}", run_input)["data"]
    run_id = run["id"]
    deadline = time.time() + RUN_TIMEOUT_SEC
    while time.time() < deadline:
        time.sleep(POLL_SEC)
        run = _req(f"{API}/actor-runs/{run_id}?token={t}")["data"]
        if run["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    if run["status"] != "SUCCEEDED":
        sys.exit(f"Apify run {run_id}: {run['status']}")
    cost = run.get("usageTotalUsd") or 0.0
    ds = run["defaultDatasetId"]
    items = _req(f"{API}/datasets/{ds}/items?token={t}&format=json")
    return items, cost


def to_url(arg: str) -> str:
    if arg.startswith("http"):
        return arg.split("?")[0]
    return f"https://www.instagram.com/p/{arg}/"


def fetch_post(arg: str) -> tuple[dict, float]:
    items, cost = run_actor({
        "directUrls": [to_url(arg)],
        "resultsType": "posts",
        "resultsLimit": 1,
    })
    if not items:
        sys.exit("Apify вернул 0 items - пост недоступен или удалён")
    return items[0], cost


def download(url: str, path: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())


def cmd_post(arg: str) -> None:
    item, cost = fetch_post(arg)
    print(json.dumps(item, ensure_ascii=False, indent=1))
    print(f"[cost] ${cost:.4f}", file=sys.stderr)


def cmd_carousel(arg: str, outdir: str | None) -> None:
    item, cost = fetch_post(arg)
    code = item.get("shortCode") or re.sub(r"\W", "", arg)[-11:]
    outdir = outdir or f"./{code}"
    os.makedirs(outdir, exist_ok=True)
    images = [c.get("displayUrl") for c in (item.get("childPosts") or [])
              if c.get("displayUrl")]
    if not images and item.get("displayUrl"):
        images = [item["displayUrl"]]
    for i, u in enumerate(images, 1):
        download(u, os.path.join(outdir, f"slide-{i:02d}.jpg"))
    with open(os.path.join(outdir, "caption.txt"), "w") as f:
        f.write(item.get("caption") or "")
    with open(os.path.join(outdir, "_source_url.txt"), "w") as f:
        f.write(to_url(arg) + "\n")
    meta = {k: item.get(k) for k in (
        "shortCode", "ownerUsername", "type", "likesCount", "commentsCount",
        "videoViewCount", "timestamp", "childPosts")}
    meta["childPosts"] = len(item.get("childPosts") or [])
    with open(os.path.join(outdir, "meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"{outdir}: {len(images)} слайдов, автор @{item.get('ownerUsername')}, "
          f"лайки {item.get('likesCount')}, комменты {item.get('commentsCount')}")
    print(f"[cost] ${cost:.4f}", file=sys.stderr)


def cmd_profile(username: str, limit: int) -> None:
    items, cost = run_actor({
        "directUrls": [f"https://www.instagram.com/{username}/"],
        "resultsType": "posts",
        "resultsLimit": limit,
    })
    for it in items:
        print(json.dumps({
            "code": it.get("shortCode"), "type": it.get("type"),
            "timestamp": it.get("timestamp"), "likes": it.get("likesCount"),
            "comments": it.get("commentsCount"), "views": it.get("videoViewCount"),
            "caption": (it.get("caption") or "")[:4000],
        }, ensure_ascii=False))
    print(f"[cost] ${cost:.4f} за {len(items)} постов", file=sys.stderr)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]
    if cmd == "post" and len(args) >= 2:
        cmd_post(args[1])
    elif cmd == "carousel" and len(args) >= 2:
        cmd_carousel(args[1], args[2] if len(args) > 2 else None)
    elif cmd == "profile" and len(args) >= 2:
        cmd_profile(args[1], int(args[2]) if len(args) > 2 else 50)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
