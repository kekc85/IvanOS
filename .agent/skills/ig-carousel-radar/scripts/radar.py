#!/usr/bin/env python3
"""
IG Carousel Radar v1.0 - daily viral IG carousel discovery.

Usage:
    python3 radar.py               # full run
    python3 radar.py --dry-run     # quick auth + 1 sample per mode
    python3 radar.py --date 2026-05-29  # rerun specific date

Backend: Playwright + IG cookie session ученика (BYOA, его сессия не автора).
Output: ~/Desktop/ig-digest/{YYYY-MM-DD}.md
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

try:
    from playwright.async_api import async_playwright, BrowserContext, Page
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright pyyaml && playwright install chromium")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)

# Topic cluster classifier (zero-LLM, second relevance layer). Lives next to this script.
sys.path.insert(0, str(Path(__file__).parent))
from cluster import load_clusters, apply_clusters, policy_rank, detect_cta


# ============================================================
# Config (mirrors config.md - keep in sync)
# ============================================================

HOME = Path.home()

PATHS = {
    "watchlist": HOME / ".business/growth/watchlist-en.yml",
    "hashtags": HOME / ".business/growth/hashtags-en.yml",
    "clusters": HOME / ".business/growth/clusters-en.yml",
    # реестр уже-уникализированных каруселей (output + queue auto-uniqualize) для дедупа
    "uniqualize_root": HOME / ".business/scripts/auto-uniqualize",
    "ig_cookies": HOME / ".business/processes/.ig-cookies.json",
    "output_dir": HOME / "Desktop/ig-digest",
    "thumbs_dir": HOME / "Desktop/ig-digest/.thumbs",
    "log_path": HOME / ".business/growth/ig-radar.log",
}

DISCOVERY = {
    "feed_scroll_screens": 50,
    "watchlist_posts_per_profile": 10,
    "hashtag_posts_per_tag": 30,
    "scroll_delay_ms": 1500,
    "between_profiles_delay_ms": 3000,
    "between_hashtags_delay_ms": 3000,
    "timeout_per_mode_sec": 600,
}

FILTER = {
    "recency_days": 14, # по решению автора (автор, жёстко): максимум 1 неделя, старьё не брать
    "comments_threshold": 0, # по решению автора: комменты НЕ критерий (накручены чужой «comment X»). Меряем лайками
    "require_carousel": True,
    "require_cta": False, # по решению автора: БЕРЁМ оригиналы БЕЗ своего код-слова (мы добавляем свой)
    "max_per_author": 3, # по решению автора: до 3/автор (виральные брать независимо от автора)
    # по решению автора (автор): главный сигнал виральности = ПРОСМОТРЫ ~500k+ (несколько сотен тысяч).
    # Лайки 10k — лишь прокси/fallback (IG часто прячет лайки; у видео/рилз видны просмотры).
    # Проходит, если просмотры >= порога ИЛИ (где просмотров нет) лайки >= прокси-порога.
    "views_threshold": 80000,
    "likes_threshold": 2500,
    "strong_comments_override": 10**9,
}

OUTPUT = {
    "caption_preview_chars": 200,
}

DRY_RUN_LIMITS = {
    "feed_scroll_screens": 1,
    "watchlist_posts_per_profile": 1,
    "hashtag_posts_per_tag": 1,
    "watchlist_profiles_max": 1,
    "hashtag_tags_max": 1,
}


# ============================================================
# Data model
# ============================================================

@dataclass
class Candidate:
    shortcode: str
    url: str
    author: str
    timestamp: str  # ISO
    is_carousel: bool
    comments: int = 0
    likes: int = 0
    views: int = 0
    caption: str = ""
    slide_1_url: str = ""
    source_mode: str = ""  # 'feed' / 'watchlist' / 'hashtag'
    cluster: str = ""          # topic cluster (filled by classifier)
    cluster_policy: str = ""   # want / avoid / neutral
    cta: str = ""              # strong / weak / none (replicability gate)
    cta_match: str = ""        # matched CTA phrase

    @property
    def age_hours(self) -> float:
        try:
            ts = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        except Exception:
            return 9999

    @property
    def age_human(self) -> str:
        h = self.age_hours
        if h < 24:
            return f"{int(h)}h"
        return f"{int(h/24)}d"

    @property
    def engagement_ratio(self) -> float:
        return (self.comments / self.likes * 100) if self.likes > 0 else 0


# ============================================================
# Helpers
# ============================================================

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        PATHS["log_path"].parent.mkdir(parents=True, exist_ok=True)
        with open(PATHS["log_path"], "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_seed_yaml(path: Path, key: str) -> list[str]:
    if not path.exists():
        log(f"seed file missing at {path} - delegating to setup.py")
        run_setup_auto()
        if not path.exists():
            log(f"WARN: setup.py did not produce {path}")
            return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    items = data.get(key, [])
    return [x for x in items if isinstance(x, str) and x.strip()]


def run_setup_auto():
    """Auto-invoke setup.py if cookies / seeds missing. Idempotent (re-runs OK)."""
    global _setup_attempted
    if globals().get("_setup_attempted"):
        return
    globals()["_setup_attempted"] = True
    import subprocess
    script_dir = Path(__file__).parent
    venv_python = script_dir.parent / "python3"
    setup_py = script_dir / "setup.py"
    log(f"running setup.py to bootstrap...")
    try:
        subprocess.run([str(venv_python), str(setup_py)], check=False)
    except Exception as e:
        log(f"setup.py invocation failed: {e}")


def load_done_shortcodes() -> set[str]:
    """Shortcodes уже-сделанных каруселей из auto-uniqualize (output/ + queue/ _source_url.txt).
    Чтобы радар НЕ приносил повтор того, что уже уникализировали."""
    done: set[str] = set()
    root = PATHS["uniqualize_root"]
    if not root.exists():
        return done
    for f in root.rglob("_source_url.txt"):
        try:
            txt = f.read_text()
        except Exception:
            continue
        for m in re.findall(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)", txt):
            done.add(m)
    if done:
        log(f"[dedup] {len(done)} уже-сделанных каруселей в реестре")
    return done


def refresh_cookies_from_chrome() -> bool:
    """PRIMARY cookie source: pull fresh IG cookies from logged-in Chrome (no manual login).
    IG invalidates headless sessions server-side, so the saved file goes stale silently
    (recognises account via ds_user_id but sessionid is dead -> 'Continue' wall -> 0 captures).
    Re-extract on every run so a stale file never quietly breaks discovery."""
    try:
        import browser_cookie3
    except ImportError:
        log("[cookies] browser_cookie3 unavailable - using saved file as-is")
        return False
    merged: dict[str, dict] = {}
    try:
        cj = browser_cookie3.chrome(domain_name="instagram.com")
    except Exception as e:
        log(f"[cookies] chrome extract failed ({type(e).__name__}: {e}) - using saved file")
        return False
    for c in cj:
        d = {"name": c.name, "value": c.value, "domain": c.domain,
             "path": c.path or "/", "secure": bool(getattr(c, "secure", False))}
        if c.expires:
            d["expirationDate"] = c.expires
        if c.name not in merged or (c.name == "sessionid" and c.value):
            merged[c.name] = d
    if "sessionid" not in merged:
        log("[cookies] no sessionid in Chrome (not logged into IG?) - using saved file")
        return False
    PATHS["ig_cookies"].parent.mkdir(parents=True, exist_ok=True)
    PATHS["ig_cookies"].write_text(json.dumps(list(merged.values()), indent=2))
    try:
        os.chmod(PATHS["ig_cookies"], 0o600)
    except Exception:
        pass
    log(f"[cookies] refreshed {len(merged)} cookies from Chrome (sessionid present)")
    return True


def load_cookies() -> list[dict]:
    if not PATHS["ig_cookies"].exists():
        log(f"cookies missing at {PATHS['ig_cookies']} - delegating to setup.py")
        run_setup_auto()
        # setup.py either succeeded (cookies now present) or exit'd. Re-check:
        if not PATHS["ig_cookies"].exists():
            log("FATAL: setup.py did not produce cookies")
            sys.exit(2)
    with open(PATHS["ig_cookies"]) as f:
        raw = json.load(f)
    cookies = []
    for c in raw:
        ck = {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        }
        if c.get("expirationDate"):
            ck["expires"] = int(c["expirationDate"])
        if c.get("httpOnly"):
            ck["httpOnly"] = True
        if c.get("secure"):
            ck["secure"] = True
        ss = c.get("sameSite", "Lax")
        if ss in ("no_restriction", "unspecified"):
            ck["sameSite"] = "None"
        else:
            ck["sameSite"] = ss.capitalize() if ss else "Lax"
        if ck["name"] and ck["value"]:
            cookies.append(ck)
    return cookies


# ============================================================
# Discovery modes
# ============================================================

# NOTE: IG HTML селекторы fragile. Maintenance plan в SKILL.md.
# v1 use shared_data / GraphQL response interception как primary, DOM selectors fallback.

async def intercept_post_data(page: Page) -> list[Candidate]:
    """Hook on GraphQL responses to capture post metadata."""
    captured: list[Candidate] = []

    async def handle_response(response):
        try:
            url = response.url
            if "graphql" not in url and "/api/v1/" not in url:
                return
            # IG serves /api/graphql with content-type text/javascript (body is valid JSON).
            # Parse body as JSON regardless of declared content-type.
            txt = await response.text()
            data = json.loads(txt)
            for c in extract_candidates_from_graphql(data):
                captured.append(c)
        except Exception:
            pass

    page.on("response", handle_response)
    return captured


def extract_candidates_from_graphql(data: Any) -> list[Candidate]:
    """Walk GraphQL response, extract candidates. Defensive - IG schema varies."""
    out: list[Candidate] = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("__typename") in ("GraphSidecar", "XDTMediaDict") or node.get("media_type") == 8:
                try:
                    out.append(node_to_candidate(node))
                except Exception:
                    pass
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return out


def node_to_candidate(n: dict) -> Candidate:
    """Map IG node → Candidate. Schema varies (GraphQL vs feed API)."""
    shortcode = n.get("shortcode") or n.get("code") or ""
    typename = n.get("__typename") or n.get("product_type") or ""
    media_type = n.get("media_type", 0)
    is_carousel = typename == "GraphSidecar" or media_type == 8

    # Author
    owner = n.get("owner") or n.get("user") or {}
    author = owner.get("username") or ""

    # Timestamp
    taken = n.get("taken_at_timestamp") or n.get("taken_at") or 0
    if taken:
        ts = datetime.fromtimestamp(int(taken), tz=timezone.utc).isoformat()
    else:
        ts = ""

    # Engagement
    likes = (n.get("edge_media_preview_like") or {}).get("count") or n.get("like_count") or 0
    comments = (n.get("edge_media_to_comment") or {}).get("count") or n.get("comment_count") or 0
    # Просмотры (автор: главный сигнал виральности ~500k+; у видео/рилз видны, у каруселей часто скрыты)
    views = (n.get("video_view_count") or n.get("video_play_count") or n.get("play_count")
             or n.get("ig_play_count") or n.get("view_count") or 0)

    # Caption
    caption_edges = (n.get("edge_media_to_caption") or {}).get("edges") or []
    caption = ""
    if caption_edges:
        caption = (caption_edges[0].get("node") or {}).get("text") or ""
    elif n.get("caption"):
        cap = n["caption"]
        caption = cap.get("text") if isinstance(cap, dict) else str(cap)

    # Slide 1
    slide_1 = n.get("display_url") or ""
    if not slide_1:
        resources = n.get("image_versions2", {}).get("candidates", [])
        if resources:
            slide_1 = resources[0].get("url", "")

    return Candidate(
        shortcode=shortcode,
        url=f"https://instagram.com/p/{shortcode}/" if shortcode else "",
        author=author,
        timestamp=ts,
        is_carousel=is_carousel,
        comments=int(comments),
        likes=int(likes),
        views=int(views),
        caption=caption,
        slide_1_url=slide_1,
    )


async def scroll_page(page: Page, screens: int, delay_ms: int):
    for i in range(screens):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(delay_ms / 1000)


async def mode_a_feed(context: BrowserContext, screens: int) -> list[Candidate]:
    log(f"[mode-a] feed scroll x{screens}")
    page = await context.new_page()
    captured = await intercept_post_data(page)
    try:
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        await scroll_page(page, screens, DISCOVERY["scroll_delay_ms"])
    except Exception as e:
        log(f"[mode-a] error: {e}")
    finally:
        await page.close()
    for c in captured:
        c.source_mode = "feed"
    log(f"[mode-a] captured {len(captured)} posts")
    return captured


async def mode_b_watchlist(context: BrowserContext, handles: list[str], per_profile: int, max_profiles: int | None = None) -> list[Candidate]:
    if max_profiles:
        handles = handles[:max_profiles]
    log(f"[mode-b] watchlist sweep x{len(handles)} profiles")
    all_caps: list[Candidate] = []
    for h in handles:
        page = await context.new_page()
        captured = await intercept_post_data(page)
        try:
            await page.goto(f"https://www.instagram.com/{h}/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            # Scroll enough to load per_profile posts (3 posts per row × N rows ≈ scrolls)
            scrolls = max(1, (per_profile // 3) + 1)
            await scroll_page(page, scrolls, DISCOVERY["scroll_delay_ms"])
        except Exception as e:
            log(f"[mode-b] {h} error: {e}")
        finally:
            await page.close()
        for c in captured:
            c.source_mode = "watchlist"
        all_caps.extend(captured)
        await asyncio.sleep(DISCOVERY["between_profiles_delay_ms"] / 1000)
    log(f"[mode-b] captured {len(all_caps)} posts across {len(handles)} profiles")
    return all_caps


async def mode_c_hashtag(context: BrowserContext, tags: list[str], per_tag: int, max_tags: int | None = None) -> list[Candidate]:
    if max_tags:
        tags = tags[:max_tags]
    log(f"[mode-c] hashtag sweep x{len(tags)} tags")
    all_caps: list[Candidate] = []
    for t in tags:
        page = await context.new_page()
        captured = await intercept_post_data(page)
        try:
            await page.goto(f"https://www.instagram.com/explore/tags/{t}/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            scrolls = max(2, (per_tag // 6) + 1)
            await scroll_page(page, scrolls, DISCOVERY["scroll_delay_ms"])
        except Exception as e:
            log(f"[mode-c] #{t} error: {e}")
        finally:
            await page.close()
        for c in captured:
            c.source_mode = "hashtag"
        all_caps.extend(captured)
        await asyncio.sleep(DISCOVERY["between_hashtags_delay_ms"] / 1000)
    log(f"[mode-c] captured {len(all_caps)} posts across {len(tags)} tags")
    return all_caps


async def mode_d_search(context: BrowserContext, keywords: list[str], per_kw: int) -> list[Candidate]:
    """Explore ПОИСК ПО КЛЮЧЕВЫМ СЛОВАМ (автор: смотреть через лупу/Explore, не watchlist).
    Алгоритм Explore сам показывает реально залетевшее по запросу, по ВСЕМ авторам."""
    from urllib.parse import quote
    log(f"[mode-d] keyword search x{len(keywords)} queries")
    all_caps: list[Candidate] = []
    for kw in keywords:
        page = await context.new_page()
        captured = await intercept_post_data(page)
        try:
            await page.goto(f"https://www.instagram.com/explore/search/keyword/?q={quote(kw)}",
                            wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await scroll_page(page, max(2, (per_kw // 6) + 1), DISCOVERY["scroll_delay_ms"])
        except Exception as e:
            log(f"[mode-d] '{kw}' error: {e}")
        finally:
            await page.close()
        for c in captured:
            c.source_mode = "search"
        all_caps.extend(captured)
        await asyncio.sleep(DISCOVERY["between_hashtags_delay_ms"] / 1000)
    log(f"[mode-d] captured {len(all_caps)} posts across {len(keywords)} queries")
    return all_caps


# ============================================================
# Filter pipeline
# ============================================================

def enrich_views_from_embed(candidates: list[Candidate], cap: int = 100, delay: float = 0.4) -> list[Candidate]:
    """Дотягивает ПРОСМОТРЫ через media info API (`/api/v1/media/{id}/info/` -> play_count/ig_play_count).
    ПОЧЕМУ НЕ embed (история по решению автора): IG перекроил embed-страницу и выкинул оттуда video_view_count
    -> старый scrape возвращал 0/N. info API (тот же, что в apifetch.py) отдаёт реальные просмотры.
    🔴 ВАЖНО: просмотры есть ТОЛЬКО у Reels/видео (media_type=2). У КАРУСЕЛЕЙ (media_type=8) IG просмотры
    НЕ отдаёт в принципе (play_count=None) -> для этого carousel-радара останется 0 -> fallback на лайки.
    Проверено по решению автора: рилзы DYPgTzuSilc=186445, DX6Z4P3uDcS=264065; карусели -> None."""
    import time as _t
    AB = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    try:
        ck = json.loads(PATHS["ig_cookies"].read_text())
        ckstr = "; ".join(f"{c['name']}={c['value']}" for c in ck if c.get("name"))
    except Exception:
        ckstr = ""
    hdr = {"User-Agent": "Mozilla/5.0", "x-ig-app-id": "936619743392459",
           "Cookie": ckstr, "x-requested-with": "XMLHttpRequest"}
    enriched = 0
    for c in candidates[:cap]:
        if not c.shortcode:
            continue
        try:
            mid = 0
            for ch in c.shortcode:
                mid = mid * 64 + AB.index(ch)
            req = urllib.request.Request(
                f"https://www.instagram.com/api/v1/media/{mid}/info/", headers=hdr)
            it = json.loads(urllib.request.urlopen(req, timeout=20).read())["items"][0]
            vc = it.get("play_count") or it.get("ig_play_count") or it.get("view_count") or 0
            if vc:
                c.views = int(vc)
                enriched += 1
        except Exception:
            pass
        _t.sleep(delay)
    log(f"[views] обогащено просмотрами {enriched}/{min(len(candidates), cap)} (info API; у каруселей IG просмотров НЕТ → лайки)")
    return candidates


def filter_candidates(candidates: list[Candidate]) -> tuple[list[Candidate], dict, list[Candidate], list[Candidate], list[Candidate], list[Candidate]]:
    log(f"[filter] input: {len(candidates)} candidates")
    done_codes = load_done_shortcodes()

    # 1. type == carousel
    if FILTER["require_carousel"]:
        candidates = [c for c in candidates if c.is_carousel]
        log(f"[filter] after carousel-only: {len(candidates)}")

    # 2. age < N days
    max_age_h = FILTER["recency_days"] * 24
    candidates = [c for c in candidates if 0 <= c.age_hours <= max_age_h]
    log(f"[filter] after recency<{FILTER['recency_days']}d: {len(candidates)}")

    # 2b. ОБОГАЩЕНИЕ ПРОСМОТРАМИ из embed (в ленте/сетке их нет; у видео/рилз — video_view_count).
    candidates = enrich_views_from_embed(candidates)

    # 3. comments threshold
    candidates = [c for c in candidates if c.comments >= FILTER["comments_threshold"]]
    log(f"[filter] after comments>={FILTER['comments_threshold']}: {len(candidates)}")

    # 3a. virality gate: лайки>=N ИЛИ комменты>=strong (автор: только жёстко-виральное)
    lk, strong = FILTER.get("likes_threshold", 0), FILTER.get("strong_comments_override", 10**9)
    vw = FILTER.get("views_threshold", 500000)
    candidates = [c for c in candidates if c.views >= vw or c.likes >= lk or c.comments >= strong]
    log(f"[filter] after virality (views>={vw} OR likes>={lk} OR comments>={strong}): {len(candidates)}")

    # 3b. rejected authors: автор забраковал явно - не показывать никогда
    rejected = set(load_seed_yaml(PATHS["watchlist"], "rejected"))
    if rejected:
        candidates = [c for c in candidates if c.author not in rejected]
        log(f"[filter] after rejected-authors ({len(rejected)}): {len(candidates)}")

    # 4. dedupe by URL
    seen = {}
    for c in candidates:
        if c.url and c.url not in seen:
            seen[c.url] = c
        elif c.url in seen:
            # Merge source_mode label
            if c.source_mode not in seen[c.url].source_mode:
                seen[c.url].source_mode += f"+{c.source_mode}"
    candidates = list(seen.values())
    log(f"[filter] after dedupe: {len(candidates)}")

    # 5. topic clustering (zero-LLM keyword classifier, second relevance layer).
    #    Drops avoid-clusters (e.g. prompt-handout) when mode=drop_avoid; tags the rest.
    clusters_cfg = load_clusters(PATHS["clusters"])
    candidates, dropped, breakdown = apply_clusters(candidates, lambda c: c.caption, clusters_cfg)
    log(f"[filter] clusters mode={clusters_cfg.get('mode')} breakdown={breakdown} dropped_avoid={len(dropped)}")

    # 6. CTA gate: no-CTA выкидываем ТОЛЬКО если НЕ наша тема (шум). On-topic (want) без призыва
    # оставляем - подставим СВОЙ призыв при уникализации (решение автора).
    for c in candidates:
        c.cta, c.cta_match = detect_cta(c.caption)
    dropped_nocta = []
    if FILTER.get("require_cta"):
        kept = [c for c in candidates if not (c.cta == "none" and c.cluster_policy != "want")]
        dropped_nocta = [c for c in candidates if c.cta == "none" and c.cluster_policy != "want"]
        candidates = kept
        log(f"[filter] after CTA-gate: {len(candidates)} (выкинуто no-CTA+off-topic: {len(dropped_nocta)})")

    # 7. dedup против уже-сделанных каруселей (auto-uniqualize реестр)
    dropped_done = [c for c in candidates if c.shortcode in done_codes]
    if dropped_done:
        candidates = [c for c in candidates if c.shortcode not in done_codes]
        log(f"[filter] after dedup-done: {len(candidates)} (выкинуто уже-сделанных: {len(dropped_done)})")

    # 8. sort: want-cluster first, strong-CTA before weak, then ПРОСМОТРЫ DESC (лайки×50 как прокси)
    cta_rank = {"strong": 0, "weak": 1, "none": 2}
    candidates.sort(key=lambda c: (policy_rank(c.cluster_policy), cta_rank.get(c.cta, 2), -max(c.views, c.likes * 50, c.comments)))

    # 9. author diversity: ≤ max_per_author в основной выдаче, остальное -> overflow
    cap = FILTER.get("max_per_author", 1)
    per_author: dict[str, int] = {}
    diverse, overflow = [], []
    for c in candidates:
        n = per_author.get(c.author, 0)
        if n < cap:
            diverse.append(c)
            per_author[c.author] = n + 1
        else:
            overflow.append(c)
    log(f"[filter] author-diversity: {len(diverse)} финалистов (≤{cap}/автор), overflow {len(overflow)}")
    log(f"[filter] final: {len(diverse)} finalists")
    return diverse, breakdown, dropped, dropped_nocta, dropped_done, overflow


# ============================================================
# Thumb download
# ============================================================

def download_thumb(candidate: Candidate) -> Path | None:
    if not candidate.slide_1_url or not candidate.shortcode:
        return None
    target = PATHS["thumbs_dir"] / f"{candidate.shortcode}.jpg"
    if target.exists():
        return target
    try:
        PATHS["thumbs_dir"].mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            candidate.slide_1_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )
        with urllib.request.urlopen(req, timeout=15) as r, open(target, "wb") as f:
            f.write(r.read())
        return target
    except Exception as e:
        log(f"[thumb] {candidate.shortcode} failed: {e}")
        return None


# ============================================================
# Digest writer
# ============================================================

def write_digest(
    date_str: str,
    finalists: list[Candidate],
    counts: dict,
) -> Path:
    PATHS["output_dir"].mkdir(parents=True, exist_ok=True)
    digest_path = PATHS["output_dir"] / f"{date_str}.md"

    lines = [
        f"# IG Carousel Radar - {date_str}",
        "",
        f"Прогон: feed ({counts.get('feed', 0)}) + watchlist ({counts.get('watchlist', 0)}) + hashtag ({counts.get('hashtag', 0)}) + search ({counts.get('search', 0)}) = total {counts.get('total', 0)} -> filtered {counts.get('after_filter', 0)} -> finalists {len(finalists)}",
        "",
        f"Config: comments_threshold={FILTER['comments_threshold']} / recency_days={FILTER['recency_days']}",
        "",
    ]

    # Cluster breakdown (что радар нашёл по форматам - данные для прунинга watchlist)
    breakdown = counts.get("cluster_breakdown") or {}
    dropped = counts.get("dropped_avoid") or []
    if breakdown:
        lines.append("## Кластеры (формат-фильтр)")
        for name, n in sorted(breakdown.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {name}: {n}")
        lines.append("")
    if dropped:
        lines.append(f"## Выкинуто (avoid-формат): {len(dropped)}")
        for c in dropped[:20]:
            cap_p = (c.caption or "").replace("\n", " ").strip()[:90]
            lines.append(f'- @{c.author} [{c.cluster}] {c.comments}c - "{cap_p}" - {c.url}')
        lines.append("")
    nocta = counts.get("dropped_nocta") or []
    if nocta:
        lines.append(f"## Выкинуто (нет призыва/CTA - нечего реплицировать): {len(nocta)}")
        for c in sorted(nocta, key=lambda x: -x.comments)[:20]:
            cap_p = (c.caption or "").replace("\n", " ").strip()[:90]
            lines.append(f'- @{c.author} {c.comments}c - "{cap_p}" - {c.url}')
        lines.append("")
    done_list = counts.get("dropped_done") or []
    if done_list:
        lines.append(f"## Пропущено (УЖЕ сделано ранее): {len(done_list)}")
        for c in sorted(done_list, key=lambda x: -x.comments)[:20]:
            lines.append(f"- @{c.author} {c.comments}c - {c.url}")
        lines.append("")
    overflow = counts.get("overflow") or []
    if overflow:
        lines.append(f"## Overflow (тот же автор уже в выдаче, держим для разнообразия): {len(overflow)}")
        for c in overflow[:20]:
            cap_p = (c.caption or "").replace("\n", " ").strip()[:80]
            lines.append(f'- @{c.author} [{c.cluster}] {c.comments}c - "{cap_p}" - {c.url}')
        lines.append("")

    if not finalists:
        lines.extend([
            "## 0 finalists",
            "",
            "Возможные причины:",
            "- COMMENTS_THRESHOLD слишком высокий (текущий: {})".format(FILTER["comments_threshold"]),
            "- Watchlist handles не публиковали carousel за последние {} дней".format(FILTER["recency_days"]),
            "- Hashtag pool слишком узкий",
            "",
            "См. `prompts/03-tune-thresholds.md` для tune.",
        ])
    else:
        for i, c in enumerate(finalists, 1):
            thumb_path = download_thumb(c)
            thumb_rel = f".thumbs/{c.shortcode}.jpg" if thumb_path else ""
            caption_preview = (c.caption or "").replace("\n", " ").strip()[:OUTPUT["caption_preview_chars"]]
            lines.extend([
                f"## #{i} @{c.author} - {c.age_human} назад",
                f"- views: {c.views} / likes: {c.likes} / comments: {c.comments}",
                f"- cluster: {c.cluster} ({c.cluster_policy}) / CTA: {c.cta}" + (f' "{c.cta_match}"' if c.cta_match else ""),
                f"- source: {c.source_mode}",
                f"- slide-1: ![preview]({thumb_rel})" if thumb_rel else "- slide-1: [download failed]",
                f'- caption (first {OUTPUT["caption_preview_chars"]} chars): "{caption_preview}"',
                f"- URL: {c.url}",
                "",
            ])

    digest_path.write_text("\n".join(lines))
    log(f"[digest] wrote {digest_path}")
    return digest_path


# ============================================================
# Main
# ============================================================

async def run(dry_run: bool, date_str: str, hunt: bool = False):
    log("=" * 50)
    log(f"radar.py start. dry_run={dry_run} date={date_str} hunt={hunt}")
    log("=" * 50)

    # Load seeds
    handles = load_seed_yaml(PATHS["watchlist"], "handles")
    tags = load_seed_yaml(PATHS["hashtags"], "tags")
    if hunt:
        # --hunt: широкий проход по ВСЕМ конкурентам (актив + демотированные технические).
        # Фильтры качества (CTA + не-промпт) держатся, аудитория помечается в watchlist.
        demoted = load_seed_yaml(PATHS["watchlist"], "demoted_technical")
        merged = handles + [h for h in demoted if h not in handles]
        log(f"[hunt] +{len(merged)-len(handles)} demoted competitors -> {len(merged)} handles total")
        handles = merged
    log(f"watchlist: {len(handles)} handles, hashtags: {len(tags)} tags")

    if not handles and not tags:
        log("FATAL: both watchlist and hashtags empty. See prompts/02-setup-cookies.md")
        sys.exit(3)

    # Load cookies (refresh from logged-in Chrome first - saved file goes stale silently)
    refresh_cookies_from_chrome()
    cookies = load_cookies()
    log(f"cookies: {len(cookies)} entries loaded")

    # Limits
    if dry_run:
        feed_screens = DRY_RUN_LIMITS["feed_scroll_screens"]
        per_profile = DRY_RUN_LIMITS["watchlist_posts_per_profile"]
        per_tag = DRY_RUN_LIMITS["hashtag_posts_per_tag"]
        max_profiles = DRY_RUN_LIMITS["watchlist_profiles_max"]
        max_tags = DRY_RUN_LIMITS["hashtag_tags_max"]
    else:
        feed_screens = DISCOVERY["feed_scroll_screens"]
        per_profile = DISCOVERY["watchlist_posts_per_profile"]
        per_tag = DISCOVERY["hashtag_posts_per_tag"]
        max_profiles = None
        max_tags = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        await context.add_cookies(cookies)

        # Auth sanity check
        page = await context.new_page()
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        # Detect both hard logout (login redirect) AND the soft "Continue as <user>" re-auth wall
        # that appears when sessionid is server-side invalidated (ds_user_id still recognises the
        # account). The wall is NOT /accounts/login, so a URL-only check gives a false 'healthy'.
        auth_dead = "/accounts/login" in page.url
        if not auth_dead:
            try:
                body = await page.evaluate("document.body ? document.body.innerText.slice(0,400) : ''")
                if ("Continue" in body and "another profile" in body) or "Create new account" in body:
                    auth_dead = True
            except Exception:
                pass
        if auth_dead:
            log("FATAL: IG session invalid (login redirect or 'Continue' re-auth wall). "
                "Log into instagram.com in Chrome, then re-run (cookies auto-refresh from Chrome).")
            await browser.close()
            sys.exit(4)
        await page.close()
        log("[auth] healthy")

        # Explore keyword-search queries (автор: главный источник — лупа/Explore, не watchlist)
        search_keywords = ["я подключил нейросеть", "я попросил chatgpt", "я попросил нейросеть",
                           "нейросеть вместо", "claude код слово", "я дал ии доступ", "ии эксперимент",
                           "нейросеть заработала", "я подключил ии", "chatgpt эксперимент",
                           "claude code", "vibe coding", "ai automation", "anthropic claude", "ai tools 2026", "chatgpt tips"]
        # Run 4 modes parallel (feed + watchlist + hashtag + keyword-search)
        results = await asyncio.gather(
            mode_a_feed(context, feed_screens),
            mode_b_watchlist(context, handles, per_profile, max_profiles),
            mode_c_hashtag(context, tags, per_tag, max_tags),
            mode_d_search(context, search_keywords, per_tag),
            return_exceptions=True,
        )

        feed_caps = results[0] if not isinstance(results[0], Exception) else []
        wl_caps = results[1] if not isinstance(results[1], Exception) else []
        hash_caps = results[2] if not isinstance(results[2], Exception) else []
        search_caps = results[3] if not isinstance(results[3], Exception) else []

        counts = {
            "feed": len(feed_caps),
            "watchlist": len(wl_caps),
            "hashtag": len(hash_caps),
            "search": len(search_caps),
        }
        all_caps = feed_caps + wl_caps + hash_caps + search_caps
        counts["total"] = len(all_caps)
        log(f"merged: {counts['total']} raw candidates")

        await browser.close()

    if dry_run:
        log(f"[DRY-RUN] feed={counts['feed']} watchlist={counts['watchlist']} hashtag={counts['hashtag']}")
        log("[DRY-RUN] skipping filter+digest write")
        if counts["total"] == 0:
            log("[DRY-RUN] WARN: 0 captured. Selectors may be broken or auth weak.")
            sys.exit(5)
        log("[DRY-RUN] OK - all 3 modes functional")
        return

    # Filter
    finalists, cluster_breakdown, dropped, dropped_nocta, dropped_done, overflow = filter_candidates(all_caps)
    counts["after_filter"] = len(finalists)
    counts["cluster_breakdown"] = cluster_breakdown
    counts["dropped_avoid"] = dropped
    counts["dropped_nocta"] = dropped_nocta
    counts["dropped_done"] = dropped_done
    counts["overflow"] = overflow

    # Write digest
    digest_path = write_digest(date_str, finalists, counts)

    log("=" * 50)
    log(f"DONE. digest: {digest_path}")
    log(f"finalists: {len(finalists)}")
    log("=" * 50)

    print(f"\n>>> Open digest: open {digest_path}")


def main():
    parser = argparse.ArgumentParser(description="IG Carousel Radar v1.0")
    parser.add_argument("--dry-run", action="store_true", help="Quick auth + 1 sample per mode")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD) for rerun")
    parser.add_argument("--hunt", action="store_true", help="Широкий проход по ВСЕМ конкурентам (актив + демотированные)")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        print(f"ERROR: invalid --date format: {date_str}")
        sys.exit(1)

    try:
        asyncio.run(run(dry_run=args.dry_run, date_str=date_str, hunt=args.hunt))
    except KeyboardInterrupt:
        log("interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
