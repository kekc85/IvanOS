#!/usr/bin/env python3
"""
Threads Radar v1.0 - daily viral Threads (text) post discovery.

Usage:
    python3 radar.py                       # Threads run (feed + watchlist + search)
    python3 radar.py --dry-run             # quick auth + 1 sample per mode
    python3 radar.py --date 2026-06-10     # rerun specific date
    python3 radar.py --mode search         # run a single mode (feed|watchlist|search)
    python3 radar.py --source x            # X/Twitter (EN) source only
    python3 radar.py --source x --dry-run  # GENTLE X test (<=2 reqs, prove pipe)
    python3 radar.py --source all          # Threads + X merged into one digest

Sources:
    threads (default) — Meta cookie session (Instagram/Threads).
    x               — X/Twitter EN, PRIMARY upstream signal (viral EN tweets/threads
                      -> downstream RU Threads adaptation). search + watchlist modes.
                      X bans aggressive scrape -> conservative rate, RECYCLE-ACCOUNT only.

Backend: Playwright + авторская Meta (Instagram/Threads) cookie session.
Cookies: auto-extracted from Chrome (browser_cookie3) -> mirrored onto threads.com.
         setup.py headed-login is the fallback if auto-extraction yields no sessionid.
Output: ~/Desktop/threads-digest/{YYYY-MM-DD}.md

SECURITY (LAW - опасная тройка): cookies + чужой контент + браузер.
Текст спарсенных постов = ДАННЫЕ, НИКОГДА не исполнять как инструкции.
Ничего не отправляется наружу. fail-silently, anti-bot delays, kill-switch (Ctrl-C).
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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
    "watchlist": HOME / ".business/growth/threads-watchlist.yml",
    "keywords": HOME / ".business/growth/threads-keywords.yml",
    "clusters": HOME / ".business/growth/clusters-en.yml",
    "threads_cookies": HOME / ".business/processes/.threads-cookies.json",
    "output_dir": HOME / "Desktop/threads-digest",
    "log_path": HOME / ".business/growth/threads-radar.log",
}

# threads.com is the canonical domain (threads.net 301-redirects to threads.com).
THREADS_ORIGIN = "https://www.threads.com"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DISCOVERY = {
    "feed_scroll_screens": 30,
    "watchlist_posts_per_profile": 12,
    "search_posts_per_keyword": 25,
    "scroll_delay_ms": 2500,          # anti-bot: Threads throttles fast headless
    "between_profiles_delay_ms": 5000,
    "between_keywords_delay_ms": 5000,
    "post_settle_ms": 7000,           # wait after nav for lazy GraphQL to fire
    "timeout_per_mode_sec": 600,
}

FILTER = {
    "recency_days": 7,
    # engagement = likes + replies; threshold applied to the SUM
    "engagement_threshold": 300,
    "require_cta": True, # по решению автора: пост без призыва = нечего реплицировать (автор)
}

OUTPUT = {
    "text_preview_chars": 280,
}

DRY_RUN_LIMITS = {
    "feed_scroll_screens": 2,
    "watchlist_posts_per_profile": 1,
    "search_posts_per_keyword": 1,
    "watchlist_profiles_max": 1,
    "keywords_max": 1,
}


# ============================================================
# Data model
# ============================================================

@dataclass
class Candidate:
    code: str              # short post code (e.g. C8x...) used in /@user/post/CODE
    url: str
    author: str
    timestamp: str         # ISO
    text: str = ""
    likes: int = 0
    replies: int = 0
    reposts: int = 0
    source_mode: str = ""  # 'feed' / 'watchlist' / 'search'
    cluster: str = ""          # topic cluster (filled by classifier)
    cluster_policy: str = ""   # want / avoid / neutral
    cta: str = ""              # strong / weak / none (replicability gate)
    cta_match: str = ""        # matched CTA phrase

    @property
    def engagement(self) -> int:
        return int(self.likes) + int(self.replies)

    @property
    def metrics_known(self) -> bool:
        # DOM-fallback yields URL/date/text but NO like/reply counts (those live
        # only in the GraphQL response). Distinguish "0 engagement" from "unknown".
        return (self.likes or self.replies or self.reposts) > 0

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
        return f"{int(h / 24)}d"


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
    return [x.lstrip("@").strip() for x in items if isinstance(x, str) and x.strip()]


def run_setup_auto():
    """Auto-invoke setup.py if cookies / seeds missing. Idempotent."""
    if globals().get("_setup_attempted"):
        return
    globals()["_setup_attempted"] = True
    import subprocess
    script_dir = Path(__file__).parent
    venv_python = script_dir.parent / "python3"
    setup_py = script_dir / "setup.py"
    log("running setup.py to bootstrap...")
    try:
        subprocess.run([str(venv_python), str(setup_py)], check=False)
    except Exception as e:
        log(f"setup.py invocation failed: {e}")


def load_cookies() -> list[dict]:
    """Load cookies and mirror them onto threads.com + threads.net.

    Threads auth = the SAME Meta session as Instagram. The cookie file may carry
    .instagram.com cookies (sessionid etc.); we replicate each onto the Threads
    domains so the logged-in session is recognised on threads.com.
    """
    if not PATHS["threads_cookies"].exists():
        log(f"cookies missing at {PATHS['threads_cookies']} - delegating to setup.py")
        run_setup_auto()
        if not PATHS["threads_cookies"].exists():
            log("FATAL: setup.py did not produce cookies")
            sys.exit(2)
    with open(PATHS["threads_cookies"]) as f:
        raw = json.load(f)

    cookies = []
    mirror_domains = [".instagram.com", ".threads.com", ".threads.net"]
    for c in raw:
        name = c.get("name")
        value = c.get("value")
        if not name or not value:
            continue
        for dom in mirror_domains:
            ck = {"name": name, "value": value, "domain": dom, "path": c.get("path", "/")}
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
            cookies.append(ck)
    return cookies


# ============================================================
# Discovery - GraphQL interception (primary) + DOM scrape (fallback)
# ============================================================

# NOTE: Threads serves post metadata (likes/replies/text/date) via lazy
# POST https://www.threads.com/graphql/query responses, NOT in the SSR document.
# We intercept those responses (same pattern as ig-carousel-radar) and walk the
# JSON defensively. Threads' Relay schema is masked/varies -> node_to_candidate
# tries many key names. If GraphQL yields nothing we fall back to DOM scrape.
# Maintenance plan in SKILL.md.

def _attach_graphql_interceptor(page: Page, bucket: list[Candidate]):
    pending: list[asyncio.Task] = []

    def on_response(resp):
        try:
            if "graphql/query" not in resp.url:
                return
            if resp.request.method != "POST":
                return
        except Exception:
            return

        async def grab(r=resp):
            try:
                data = await r.json()
            except Exception:
                return
            for c in extract_candidates_from_graphql(data):
                bucket.append(c)

        pending.append(asyncio.ensure_future(grab()))

    page.on("response", on_response)
    return pending


def extract_candidates_from_graphql(data: Any) -> list[Candidate]:
    """Walk a Threads GraphQL response, pull post nodes defensively."""
    out: list[Candidate] = []

    def looks_like_post(n: dict) -> bool:
        # a Threads post node carries text_post_app_info OR a code+caption,
        # OR engagement counters. Multiple shapes across feed/profile/search.
        return (
            "text_post_app_info" in n
            or ("code" in n and ("caption" in n or "like_count" in n))
            or ("pk" in n and "like_count" in n)
        )

    def walk(node):
        if isinstance(node, dict):
            if looks_like_post(node):
                try:
                    cand = node_to_candidate(node)
                    if cand.code or cand.text:
                        out.append(cand)
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
    """Map a Threads post node -> Candidate. Schema varies; be defensive."""
    code = n.get("code") or n.get("shortcode") or ""

    # author
    user = n.get("user") or n.get("owner") or {}
    author = user.get("username") or n.get("username") or ""

    # timestamp (unix seconds)
    taken = n.get("taken_at") or n.get("taken_at_timestamp") or n.get("device_timestamp") or 0
    try:
        ts = datetime.fromtimestamp(int(taken), tz=timezone.utc).isoformat() if taken else ""
    except Exception:
        ts = ""

    # text / caption
    cap = n.get("caption")
    if isinstance(cap, dict):
        text = cap.get("text") or ""
    elif isinstance(cap, str):
        text = cap
    else:
        text = n.get("text") or ""

    # engagement
    likes = n.get("like_count")
    if likes is None:
        likes = (n.get("like_and_view_counts_disabled") and 0) or 0
    tpa = n.get("text_post_app_info") or {}
    replies = (
        tpa.get("direct_reply_count")
        or tpa.get("reply_count")
        or n.get("reply_count")
        or 0
    )
    reposts = tpa.get("repost_count") or n.get("repost_count") or 0

    url = f"{THREADS_ORIGIN}/@{author}/post/{code}" if (author and code) else (
        f"{THREADS_ORIGIN}/post/{code}" if code else ""
    )

    return Candidate(
        code=code,
        url=url,
        author=author,
        timestamp=ts,
        text=text,
        likes=int(likes or 0),
        replies=int(replies or 0),
        reposts=int(reposts or 0),
    )


async def _dom_scrape(page: Page) -> list[Candidate]:
    """Fallback: read rendered posts from the DOM when GraphQL capture is empty."""
    try:
        rows = await page.evaluate(r"""
        () => {
          const out = [];
          const seen = new Set();
          // Threads post permalinks look like /@user/post/CODE
          const links = [...document.querySelectorAll("a[href*='/post/']")];
          for (const a of links) {
            const href = a.getAttribute('href') || '';
            const m = href.match(/\/@([^/]+)\/post\/([A-Za-z0-9_-]+)/);
            if (!m) continue;
            const key = m[2];
            if (seen.has(key)) continue;
            seen.add(key);
            // climb to a container that also holds a <time>
            let box = a;
            for (let i = 0; i < 10 && box; i++) {
              box = box.parentElement;
              if (box && box.querySelector('time')) break;
            }
            const t = box ? box.querySelector('time') : null;
            out.push({
              author: m[1],
              code: m[2],
              datetime: t ? (t.getAttribute('datetime') || t.getAttribute('title')) : null,
              text: box ? (box.innerText || '').slice(0, 400) : ''
            });
            if (out.length >= 40) break;
          }
          return out;
        }
        """)
    except Exception as e:
        log(f"[dom-scrape] error: {e}")
        return []

    cands = []
    for r in rows:
        ts = ""
        dt = r.get("datetime")
        if dt:
            try:
                ts = datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
            except Exception:
                ts = ""
        cands.append(Candidate(
            code=r.get("code", ""),
            url=f"{THREADS_ORIGIN}/@{r.get('author','')}/post/{r.get('code','')}",
            author=r.get("author", ""),
            timestamp=ts,
            text=(r.get("text") or "").strip(),
        ))
    return cands


async def scroll(page: Page, screens: int, delay_ms: int):
    for _ in range(screens):
        try:
            await page.mouse.wheel(0, 2200)
        except Exception:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(delay_ms / 1000)


async def _harvest(page: Page, url: str, screens: int, mode: str) -> list[Candidate]:
    """Load a URL, intercept GraphQL while scrolling, merge with DOM fallback."""
    bucket: list[Candidate] = []
    pending = _attach_graphql_interceptor(page, bucket)
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        status = resp.status if resp else "?"
        await asyncio.sleep(DISCOVERY["post_settle_ms"] / 1000)
        # Threads soft-blocks rapid headless hits with a 404 decoy page.
        body_preview = await page.evaluate(
            "() => document.body ? document.body.innerText.slice(0,80) : ''"
        )
        if "page is" in body_preview.lower() and "wander" in body_preview.lower():
            log(f"[{mode}] anti-bot 404 decoy on {url} (status {status}) - skipping, increase delays")
            return []
        await scroll(page, screens, DISCOVERY["scroll_delay_ms"])
        # let any in-flight graphql grabs finish
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        if not bucket:
            log(f"[{mode}] graphql empty for {url} - trying DOM fallback")
            bucket = await _dom_scrape(page)
    except Exception as e:
        log(f"[{mode}] error on {url}: {e}")
    for c in bucket:
        c.source_mode = mode
    return bucket


async def mode_feed(context: BrowserContext, screens: int) -> list[Candidate]:
    log(f"[feed] scroll x{screens}")
    page = await context.new_page()
    try:
        caps = await _harvest(page, THREADS_ORIGIN + "/", screens, "feed")
    finally:
        await page.close()
    log(f"[feed] captured {len(caps)}")
    return caps


async def mode_watchlist(context: BrowserContext, handles: list[str], per_profile: int,
                         max_profiles: int | None = None) -> list[Candidate]:
    if max_profiles:
        handles = handles[:max_profiles]
    log(f"[watchlist] sweep x{len(handles)} profiles")
    all_caps: list[Candidate] = []
    for h in handles:
        page = await context.new_page()
        try:
            screens = max(2, (per_profile // 3) + 1)
            caps = await _harvest(page, f"{THREADS_ORIGIN}/@{h}", screens, "watchlist")
            all_caps.extend(caps)
        finally:
            await page.close()
        await asyncio.sleep(DISCOVERY["between_profiles_delay_ms"] / 1000)
    log(f"[watchlist] captured {len(all_caps)} across {len(handles)} profiles")
    return all_caps


async def mode_search(context: BrowserContext, keywords: list[str], per_kw: int,
                      max_kw: int | None = None) -> list[Candidate]:
    if max_kw:
        keywords = keywords[:max_kw]
    log(f"[search] sweep x{len(keywords)} keywords")
    all_caps: list[Candidate] = []
    import urllib.parse
    for kw in keywords:
        page = await context.new_page()
        try:
            q = urllib.parse.quote(kw)
            screens = max(2, (per_kw // 5) + 1)
            url = f"{THREADS_ORIGIN}/search?q={q}&serp_type=default"
            caps = await _harvest(page, url, screens, "search")
            all_caps.extend(caps)
        finally:
            await page.close()
        await asyncio.sleep(DISCOVERY["between_keywords_delay_ms"] / 1000)
    log(f"[search] captured {len(all_caps)} across {len(keywords)} keywords")
    return all_caps


# ============================================================
# Filter pipeline
# ============================================================

def filter_candidates(candidates: list[Candidate]) -> tuple[list[Candidate], dict, list[Candidate], list[Candidate]]:
    log(f"[filter] input: {len(candidates)}")

    # 1. recency < N days (skip ones with unknown timestamp = age 9999)
    max_age_h = FILTER["recency_days"] * 24
    candidates = [c for c in candidates if 0 <= c.age_hours <= max_age_h]
    log(f"[filter] after recency<{FILTER['recency_days']}d: {len(candidates)}")

    # 2. engagement (likes + replies) threshold.
    # Candidates WITH known metrics must clear the bar. Candidates with UNKNOWN
    # metrics (DOM-fallback, no counters) are kept as leads (flagged), not dropped
    # silently — otherwise a GraphQL-empty run yields 0 finalists despite live posts.
    known = [c for c in candidates if c.metrics_known and c.engagement >= FILTER["engagement_threshold"]]
    unknown = [c for c in candidates if not c.metrics_known]
    candidates = known + unknown
    log(f"[filter] after engagement>={FILTER['engagement_threshold']}: "
        f"{len(known)} metric'd + {len(unknown)} metrics-unknown (DOM-only leads)")

    # 3. dedupe by URL (merge source labels)
    seen: dict[str, Candidate] = {}
    for c in candidates:
        if not c.url:
            continue
        if c.url not in seen:
            seen[c.url] = c
        else:
            if c.source_mode and c.source_mode not in seen[c.url].source_mode:
                seen[c.url].source_mode += f"+{c.source_mode}"
    candidates = list(seen.values())
    log(f"[filter] after dedupe: {len(candidates)}")

    # 4. topic clustering (zero-LLM keyword classifier, second relevance layer).
    #    Drops avoid-clusters (e.g. prompt-handout) when mode=drop_avoid; tags the rest.
    clusters_cfg = load_clusters(PATHS["clusters"])
    candidates, dropped, breakdown = apply_clusters(candidates, lambda c: c.text, clusters_cfg)
    log(f"[filter] clusters mode={clusters_cfg.get('mode')} breakdown={breakdown} dropped_avoid={len(dropped)}")

    # 5. CTA gate: пост без призыва = нечего реплицировать -> выкинуть (configurable)
    for c in candidates:
        c.cta, c.cta_match = detect_cta(c.text)
    dropped_nocta = []
    if FILTER.get("require_cta"):
        kept = [c for c in candidates if c.cta != "none"]
        dropped_nocta = [c for c in candidates if c.cta == "none"]
        candidates = kept
        log(f"[filter] after require_cta: {len(candidates)} (dropped no-CTA: {len(dropped_nocta)})")

    # 6. sort: want-cluster first, strong-CTA before weak, then engagement DESC
    cta_rank = {"strong": 0, "weak": 1, "none": 2}
    candidates.sort(key=lambda c: (policy_rank(c.cluster_policy), cta_rank.get(c.cta, 2), -c.engagement))
    log(f"[filter] final: {len(candidates)} finalists")
    return candidates, breakdown, dropped, dropped_nocta


# ============================================================
# Digest writer
# ============================================================

def write_digest(date_str: str, finalists: list[Candidate], counts: dict) -> Path:
    PATHS["output_dir"].mkdir(parents=True, exist_ok=True)
    digest_path = PATHS["output_dir"] / f"{date_str}.md"

    lines = [
        f"# Threads Radar - {date_str}",
        "",
        (f"Прогон: feed ({counts.get('feed', 0)}) + watchlist ({counts.get('watchlist', 0)}) "
         f"+ search ({counts.get('search', 0)}) + x ({counts.get('x', 0)}) = total {counts.get('total', 0)} "
         f"-> filtered -> finalists {len(finalists)}"),
        "",
        f"Config: engagement_threshold={FILTER['engagement_threshold']} / recency_days={FILTER['recency_days']}",
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
            txt_p = (c.text or "").replace("\n", " ").strip()[:90]
            lines.append(f'- @{c.author} [{c.cluster}] eng={c.engagement} - "{txt_p}" - {c.url}')
        lines.append("")
    nocta = counts.get("dropped_nocta") or []
    if nocta:
        lines.append(f"## Выкинуто (нет призыва/CTA - нечего реплицировать): {len(nocta)}")
        for c in sorted(nocta, key=lambda x: -x.engagement)[:20]:
            txt_p = (c.text or "").replace("\n", " ").strip()[:90]
            lines.append(f'- @{c.author} eng={c.engagement} - "{txt_p}" - {c.url}')
        lines.append("")

    if not finalists:
        lines += [
            "## 0 finalists",
            "",
            "Возможные причины:",
            f"- engagement_threshold слишком высокий (текущий: {FILTER['engagement_threshold']})",
            f"- Watchlist/keywords не дали постов за последние {FILTER['recency_days']} дней",
            "- Anti-bot throttle (404-decoy) - увеличь delays, прогони позже",
            "",
            "См. `prompts/03-tune-thresholds.md`.",
        ]
    else:
        for i, c in enumerate(finalists, 1):
            preview = (c.text or "").replace("\n", " ").strip()[:OUTPUT["text_preview_chars"]]
            if c.metrics_known:
                eng_line = f"- engagement: {c.engagement} (likes {c.likes} + replies {c.replies}) / reposts {c.reposts}"
            else:
                eng_line = "- engagement: metrics-unknown (DOM-only lead; GraphQL не отдал счётчики — открой URL для точных метрик)"
            lines += [
                f"## #{i} @{c.author} - {c.age_human} назад",
                eng_line,
                f"- cluster: {c.cluster} ({c.cluster_policy}) / CTA: {c.cta}" + (f' "{c.cta_match}"' if c.cta_match else ""),
                f"- source: {c.source_mode}",
                f'- text (first {OUTPUT["text_preview_chars"]} chars): "{preview}"',
                f"- URL: {c.url}",
                "",
            ]

    digest_path.write_text("\n".join(lines))
    log(f"[digest] wrote {digest_path}")
    return digest_path


# ============================================================
# Main
# ============================================================

async def run(dry_run: bool, date_str: str, only_mode: str | None, source: str = "threads"):
    log("=" * 50)
    log(f"threads-radar start. source={source} dry_run={dry_run} date={date_str} mode={only_mode or 'all'}")
    log("=" * 50)

    want_threads = source in ("threads", "all")
    want_x = source in ("x", "all")

    # ---- X / Twitter source (EN primary upstream signal) -------------------
    x_caps: list[Candidate] = []
    if want_x:
        try:
            from x_source import collect_x, X_PATHS
        except Exception as e:
            log(f"[x] import failed: {e}")
            X_PATHS = None
            collect_x = None
        if collect_x:
            x_keywords = load_seed_yaml(X_PATHS["keywords"], "keywords")
            x_handles = load_seed_yaml(X_PATHS["watchlist"], "handles")
            log(f"[x] seeds: {len(x_keywords)} keywords, {len(x_handles)} handles")
            # gentle = dry_run (X is ban-sensitive; dry-run = max 2 reqs, prove pipe)
            x_caps = await collect_x(only_mode=only_mode, gentle=dry_run,
                                     keywords=x_keywords, handles=x_handles)
            if dry_run:
                log(f"[x][DRY-RUN/GENTLE] captured {len(x_caps)} tweets")
                if x_caps:
                    s = max(x_caps, key=lambda c: c.engagement)
                    log(f"[x][DRY-RUN] sample: @{s.author} eng={s.engagement} "
                        f"(♥{s.likes} 💬{s.replies} 🔁{s.reposts}) age={s.age_human} url={s.url}")
                    # show live JSONL evidence
                    for c in x_caps[:5]:
                        log("[x][JSONL] " + json.dumps({
                            "author": c.author, "likes": c.likes, "replies": c.replies,
                            "reposts": c.reposts, "ts": c.timestamp,
                            "text": (c.text or "")[:90], "url": c.url,
                        }, ensure_ascii=False))
                else:
                    log("[x][DRY-RUN] WARN: 0 tweets — login-wall / throttle / schema drift. "
                        "Do NOT hammer; retry later from recycle account.")
            if not want_threads:
                # X-only run: filter + digest right here
                if dry_run:
                    return
                finalists, cluster_breakdown, dropped, dropped_nocta = filter_candidates(x_caps)
                counts = {"feed": 0, "watchlist": 0, "search": 0,
                          "x": len(x_caps), "total": len(x_caps),
                          "after_filter": len(finalists),
                          "cluster_breakdown": cluster_breakdown, "dropped_avoid": dropped,
                          "dropped_nocta": dropped_nocta}
                digest_path = write_digest(date_str, finalists, counts)
                log("=" * 50)
                log(f"DONE (X). digest: {digest_path} | finalists: {len(finalists)}")
                log("=" * 50)
                print(f"\n>>> Open digest: open {digest_path}")
                return

    if not want_threads:
        return

    handles = load_seed_yaml(PATHS["watchlist"], "handles")
    keywords = load_seed_yaml(PATHS["keywords"], "keywords")
    log(f"watchlist: {len(handles)} handles, keywords: {len(keywords)}")

    if not handles and not keywords and only_mode in (None, "watchlist", "search"):
        log("FATAL: both watchlist and keywords empty. See prompts/02-setup-cookies.md")
        sys.exit(3)

    cookies = load_cookies()
    log(f"cookies: {len(cookies)} entries loaded (mirrored across IG/Threads domains)")

    if dry_run:
        feed_screens = DRY_RUN_LIMITS["feed_scroll_screens"]
        per_profile = DRY_RUN_LIMITS["watchlist_posts_per_profile"]
        per_kw = DRY_RUN_LIMITS["search_posts_per_keyword"]
        max_profiles = DRY_RUN_LIMITS["watchlist_profiles_max"]
        max_kw = DRY_RUN_LIMITS["keywords_max"]
    else:
        feed_screens = DISCOVERY["feed_scroll_screens"]
        per_profile = DISCOVERY["watchlist_posts_per_profile"]
        per_kw = DISCOVERY["search_posts_per_keyword"]
        max_profiles = None
        max_kw = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
        await context.add_cookies(cookies)

        # auth sanity check
        page = await context.new_page()
        await page.goto(THREADS_ORIGIN + "/@zuck", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        if "/login" in page.url:
            log("FATAL: cookies invalid - redirected to login. Re-run setup.py (prompts/02).")
            await browser.close()
            sys.exit(4)
        await page.close()
        log("[auth] session accepted (no login redirect)")

        # Threads anti-bot is sensitive to parallelism. Run modes SEQUENTIALLY.
        feed_caps: list[Candidate] = []
        wl_caps: list[Candidate] = []
        search_caps: list[Candidate] = []

        if only_mode in (None, "feed"):
            try:
                feed_caps = await mode_feed(context, feed_screens)
            except Exception as e:
                log(f"[feed] failed: {e}")
        if only_mode in (None, "watchlist") and handles:
            try:
                wl_caps = await mode_watchlist(context, handles, per_profile, max_profiles)
            except Exception as e:
                log(f"[watchlist] failed: {e}")
        if only_mode in (None, "search") and keywords:
            try:
                search_caps = await mode_search(context, keywords, per_kw, max_kw)
            except Exception as e:
                log(f"[search] failed: {e}")

        await browser.close()

    counts = {"feed": len(feed_caps), "watchlist": len(wl_caps), "search": len(search_caps),
              "x": len(x_caps)}
    all_caps = feed_caps + wl_caps + search_caps + x_caps
    counts["total"] = len(all_caps)
    log(f"merged: {counts['total']} raw candidates (incl x={len(x_caps)})")

    if dry_run:
        log(f"[DRY-RUN] feed={counts['feed']} watchlist={counts['watchlist']} search={counts['search']}")
        if counts["total"] == 0:
            log("[DRY-RUN] WARN: 0 captured. Anti-bot throttle or schema drift - retry later / check selectors.")
            sys.exit(5)
        log("[DRY-RUN] OK - at least one mode functional")
        # show a sample
        s = all_caps[0]
        log(f"[DRY-RUN] sample: @{s.author} eng={s.engagement} age={s.age_human} url={s.url}")
        return

    finalists, cluster_breakdown, dropped, dropped_nocta = filter_candidates(all_caps)
    counts["after_filter"] = len(finalists)
    counts["cluster_breakdown"] = cluster_breakdown
    counts["dropped_avoid"] = dropped
    counts["dropped_nocta"] = dropped_nocta
    digest_path = write_digest(date_str, finalists, counts)

    log("=" * 50)
    log(f"DONE. digest: {digest_path} | finalists: {len(finalists)}")
    log("=" * 50)
    print(f"\n>>> Open digest: open {digest_path}")


def main():
    parser = argparse.ArgumentParser(description="Threads Radar v1.0")
    parser.add_argument("--dry-run", action="store_true", help="Quick auth + 1 sample per mode")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD) for rerun")
    parser.add_argument("--mode", choices=["feed", "watchlist", "search"], help="Run a single mode only")
    parser.add_argument("--source", choices=["threads", "x", "all"], default="threads",
                        help="Signal source: threads (default) | x (Twitter EN) | all")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        print(f"ERROR: invalid --date format: {date_str}")
        sys.exit(1)

    try:
        asyncio.run(run(dry_run=args.dry_run, date_str=date_str, only_mode=args.mode, source=args.source))
    except KeyboardInterrupt:
        log("interrupted by user (kill-switch)")
        sys.exit(130)


if __name__ == "__main__":
    main()