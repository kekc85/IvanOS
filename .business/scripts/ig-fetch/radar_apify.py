#!/usr/bin/env python3
"""Радар виральных IG-каруселей через Apify - замена cookie-бэкенда radar.py.

Аккаунт и IP автора вне цепочки: дискавери идёт актором apify/instagram-scraper
(watchlist-режим: свежие посты хендлов из ~/.business/growth/watchlist-en.yml).
Feed-режим старого радара невозможен без аккаунта и не переносится by design.

Usage:
  python3 radar_apify.py                        # полный прогон watchlist
  python3 radar_apify.py --handles a,b,c        # только эти хендлы (смоук/точечно)
  python3 radar_apify.py --limit 10             # постов на профиль (default 10)
  python3 radar_apify.py --recency 7            # свежесть в днях (default 7)
  python3 radar_apify.py --min-likes 1000       # порог лайков (default 1000)

Output: ~/Desktop/ig-digest/{YYYY-MM-DD}.md + финалисты в stdout.
Cost: ~$0.0023/пост => полный прогон 20 хендлов x 10 постов ~ $0.5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from apify_ig import run_actor  # noqa: E402

HOME = Path.home()
WATCHLIST = HOME / ".business/growth/watchlist-en.yml"
CLUSTERS = HOME / ".business/growth/clusters-en.yml"
AU = HOME / ".business/scripts/auto-uniqualize"
OUT_DIR = HOME / "Desktop/ig-digest"
RADAR_SCRIPTS = HOME / ".claude/skills/ig-carousel-radar/scripts"

MAX_PER_AUTHOR = 3


def load_handles() -> list[str]:
    """Лёгкий парс `handles:` из watchlist-en.yml без pyyaml."""
    handles, in_handles = [], False
    for line in open(WATCHLIST, encoding="utf-8"):
        s = line.rstrip()
        if re.match(r"^handles:\s*$", s):
            in_handles = True
            continue
        if in_handles:
            if s and not s.startswith((" ", "\t", "#")):
                break
            m = re.match(r"\s*-\s*([A-Za-z0-9._]+)", s)
            if m:
                handles.append(m.group(1))
    return handles


def done_shortcodes() -> set[str]:
    """Шорткоды уже отработанных доноров (дедуп против машины уникализации)."""
    done: set[str] = set()
    for src in AU.glob("*/*/_source_url.txt"):
        try:
            m = re.search(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)", src.read_text())
        except OSError:
            continue
        if m:
            done.add(m.group(1))
    reg = AU / "_DELIVERED_REGISTRY.txt"
    if reg.exists():
        done.update(l.strip() for l in reg.read_text().splitlines() if l.strip())
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handles", help="comma-separated override")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--recency", type=int, default=7)
    ap.add_argument("--min-likes", type=int, default=1000)
    args = ap.parse_args()

    handles = ([h.strip() for h in args.handles.split(",") if h.strip()]
               if args.handles else load_handles())
    if not handles:
        sys.exit("watchlist пуст")
    print(f"[radar] {len(handles)} хендлов x {args.limit} постов "
          f"(~${len(handles) * args.limit * 0.0023:.2f})", file=sys.stderr)

    items, cost = run_actor({
        "directUrls": [f"https://www.instagram.com/{h}/" for h in handles],
        "resultsType": "posts",
        "resultsLimit": args.limit,
    })
    print(f"[radar] получено {len(items)} постов, cost ${cost:.4f}", file=sys.stderr)

    now = datetime.now(timezone.utc)
    done = done_shortcodes()
    cands = []
    for it in items:
        if it.get("type") != "Sidecar":
            continue
        code = it.get("shortCode")
        ts = it.get("timestamp")
        if not code or not ts or code in done:
            continue
        age_days = (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).days
        if age_days > args.recency:
            continue
        likes = it.get("likesCount") or 0
        if likes < args.min_likes:
            continue
        cands.append({
            "code": code, "author": it.get("ownerUsername"),
            "likes": likes, "comments": it.get("commentsCount") or 0,
            "age_days": age_days, "slides": len(it.get("childPosts") or []),
            "caption": (it.get("caption") or "")[:400],
            "url": f"https://www.instagram.com/p/{code}/",
        })

    # формат-фильтр кластерами (тот же классификатор, что у старого радара);
    # apply_clusters пишет атрибуты - оборачиваем dict в SimpleNamespace и обратно
    try:
        from types import SimpleNamespace
        sys.path.insert(0, str(RADAR_SCRIPTS))
        from cluster import load_clusters, apply_clusters  # noqa: E402
        cfg = load_clusters(CLUSTERS)
        wrapped = [SimpleNamespace(**c) for c in cands]
        kept, dropped, breakdown = apply_clusters(wrapped, lambda c: c.caption, cfg)
        if dropped:
            print(f"[radar] кластеры выкинули {len(dropped)} (avoid-формат)", file=sys.stderr)
        print(f"[radar] кластеры: {breakdown}", file=sys.stderr)
        cands = [vars(w) for w in kept]
    except Exception as e:
        print(f"[radar] кластеры пропущены: {e}", file=sys.stderr)

    cands.sort(key=lambda c: c["likes"] + c["comments"], reverse=True)
    per_author: dict[str, int] = {}
    finalists = []
    for c in cands:
        per_author[c["author"]] = per_author.get(c["author"], 0) + 1
        if per_author[c["author"]] <= MAX_PER_AUTHOR:
            finalists.append(c)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    lines = [f"# IG Carousel Radar (Apify) - {date}",
             "",
             f"Хендлов: {len(handles)} · постов: {len(items)} · "
             f"финалистов: {len(finalists)} · cost ${cost:.4f}",
             ""]
    for i, c in enumerate(finalists, 1):
        cl = c.get("cluster", "-")
        lines += [f"## {i}. @{c['author']} - {c['likes']} лайков, {c['comments']} комм",
                  f"{c['url']}",
                  f"слайдов: {c['slides']} · возраст: {c['age_days']}д · кластер: {cl}",
                  f"> {c['caption'][:200]}".replace("\n", " "),
                  ""]
    digest = OUT_DIR / f"{date}.md"
    digest.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(finalists, ensure_ascii=False, indent=1))
    print(f"[radar] digest: {digest}", file=sys.stderr)


if __name__ == "__main__":
    main()
