#!/usr/bin/env python3
"""
Threads Radar - one-time setup (auto-bootstrap).

Runs automatically from radar.py if cookies / seeds are missing.
Manual: python3 scripts/setup.py

Flow:
  1. Bootstrap seed YAML (watchlist + keywords) if missing.
  2. Acquire Meta cookies:
       PRIMARY  - auto-extract from logged-in Chrome via browser_cookie3
                  (Threads = same Meta session as Instagram).
       FALLBACK - headed Chromium login (автор logs in once) if auto yields no sessionid.
  3. Validate via radar.py --dry-run.

No secrets in code. Cookie file is chmod 600.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

HOME = Path.home()
COOKIES_PATH = HOME / ".business/processes/.threads-cookies.json"
WATCHLIST_PATH = HOME / ".business/growth/threads-watchlist.yml"
KEYWORDS_PATH = HOME / ".business/growth/threads-keywords.yml"

# X / Twitter source (EN primary upstream signal)
X_COOKIES_PATH = HOME / ".business/processes/.x-cookies.json"
X_WATCHLIST_PATH = HOME / ".business/growth/x-watchlist.yml"
X_KEYWORDS_PATH = HOME / ".business/growth/x-keywords.yml"
# auth_token authenticates the X session; ct0 = CSRF token (x-csrf-token header).
X_REQUIRED_COOKIE = "auth_token"

# sessionid is the cookie that actually authenticates the Meta session.
REQUIRED_COOKIE = "sessionid"

WATCHLIST_SEED = """# автор - Threads watchlist (seed v1.0 - auto-bootstrap)
# X/Threads handles ниши вайбкодинг / вайбмаркетинг / solopreneur AI.
# Threads username = тот же handle, что в Instagram. Проверь что профиль есть на Threads.
# Update quarterly. Cross-ref ~/.business/marketing/competitors.md.

handles:
  - rowancheung
  - rileybrown_ai
  - marc_louvion
  - dickiebush
  - Nicolascole77
  - minchoi
  - skirano
  - nutlope
  - shl
  - steipete
  - thealexbanks
  - dvassallo
  - bentossell
  - EricJorgenson
"""

KEYWORDS_SEED = """# автор - Threads search keywords (seed v1.0 - auto-bootstrap)
# 5-8 фраз. Узко лучше широко (generic = шум).

keywords:
  - vibe marketing
  - vibe coding
  - AI content
  - claude code
  - content factory
"""


# X seeds — calibrated to EXPERT audience (внедрение AI для своего дела / маркетинга /
# контента), НЕ чисто-технические девы. Per Ivan's rule: seed на экспертную аудиторию.
X_WATCHLIST_SEED = """# автор - X/Twitter watchlist (seed v1.0)
# Авторы про внедрение AI для своего дела / маркетинга / контента / solopreneur.
# НЕ чисто-dev (steipete/nutlope/skirano избегаем) - seed на ЭКСПЕРТНУЮ аудиторию.
# X handle = без @. Update quarterly. Cross-ref ~/.business/marketing/competitors.md.

handles:
  - rowancheung
  - gregisenberg
  - dickiebush
  - Nicolascole77
  - thealexbanks
  - dvassallo
  - bentossell
  - EricJorgenson
  - rileybrown_ai
"""

X_KEYWORDS_SEED = """# автор - X/Twitter search keywords (seed v1.0)
# Узко лучше широко. Ниша вайбкодинг / вайбмаркетинг / AI для соло-эксперта.

keywords:
  - vibe marketing
  - vibe coding
  - AI content
  - content factory
  - AI for solopreneurs
"""


def bootstrap_seeds():
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not WATCHLIST_PATH.exists():
        WATCHLIST_PATH.write_text(WATCHLIST_SEED)
        print(f"[seeds] bootstrapped {WATCHLIST_PATH}")
    else:
        print(f"[seeds] watchlist exists at {WATCHLIST_PATH}")
    if not KEYWORDS_PATH.exists():
        KEYWORDS_PATH.write_text(KEYWORDS_SEED)
        print(f"[seeds] bootstrapped {KEYWORDS_PATH}")
    else:
        print(f"[seeds] keywords exist at {KEYWORDS_PATH}")
    # X seeds
    if not X_WATCHLIST_PATH.exists():
        X_WATCHLIST_PATH.write_text(X_WATCHLIST_SEED)
        print(f"[seeds] bootstrapped {X_WATCHLIST_PATH}")
    else:
        print(f"[seeds] x-watchlist exists at {X_WATCHLIST_PATH}")
    if not X_KEYWORDS_PATH.exists():
        X_KEYWORDS_PATH.write_text(X_KEYWORDS_SEED)
        print(f"[seeds] bootstrapped {X_KEYWORDS_PATH}")
    else:
        print(f"[seeds] x-keywords exist at {X_KEYWORDS_PATH}")


def _save_cookies(cookie_dicts: list[dict]) -> None:
    COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    COOKIES_PATH.write_text(json.dumps(cookie_dicts, indent=2))
    os.chmod(COOKIES_PATH, 0o600)
    print(f"[cookies] saved {len(cookie_dicts)} cookies to {COOKIES_PATH} (chmod 600)")


def _save_x_cookies(cookie_dicts: list[dict]) -> None:
    X_COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    X_COOKIES_PATH.write_text(json.dumps(cookie_dicts, indent=2))
    os.chmod(X_COOKIES_PATH, 0o600)
    print(f"[x-cookies] saved {len(cookie_dicts)} cookies to {X_COOKIES_PATH} (chmod 600)")


def acquire_x_cookies_auto() -> bool:
    """PRIMARY: pull X/Twitter cookies from logged-in Chrome (no manual login).

    ⚠️ Регулярный скрейп — с РАСХОДНОГО X-аккаунта, не с бренд-аккаунта (риск бана).
    Нужны auth_token (auth) + ct0 (CSRF token -> x-csrf-token header).
    """
    try:
        import browser_cookie3
    except ImportError:
        print("[x-cookies-auto] browser_cookie3 not available - skipping")
        return False
    merged: dict[str, dict] = {}
    try:
        cj = browser_cookie3.chrome(domain_name="x.com")
    except Exception as e:
        print(f"[x-cookies-auto] x.com: {type(e).__name__}: {e}")
        return False
    for c in cj:
        d = {
            "name": c.name, "value": c.value, "domain": c.domain,
            "path": c.path or "/", "secure": bool(getattr(c, "secure", False)),
        }
        if c.expires:
            d["expirationDate"] = c.expires
        merged[c.name] = d
    names = set(merged.keys())
    print(f"[x-cookies-auto] extracted {len(merged)} cookies: {sorted(names)}")
    if X_REQUIRED_COOKIE not in names:
        print(f"[x-cookies-auto] FAIL: no '{X_REQUIRED_COOKIE}' - Chrome not logged into X?")
        return False
    if "ct0" not in names:
        print("[x-cookies-auto] WARN: no ct0 (CSRF) - GraphQL may 403; continuing")
    _save_x_cookies(list(merged.values()))
    print("[x-cookies-auto] OK - auth_token present")
    return True


def acquire_cookies_auto() -> bool:
    """PRIMARY: pull Meta cookies from logged-in Chrome (no manual login)."""
    try:
        import browser_cookie3
    except ImportError:
        print("[cookies-auto] browser_cookie3 not available - skipping auto path")
        return False

    merged: dict[str, dict] = {}
    for domain in ("instagram.com", "threads.com", "threads.net"):
        try:
            cj = browser_cookie3.chrome(domain_name=domain)
        except Exception as e:
            print(f"[cookies-auto] {domain}: {type(e).__name__}: {e}")
            continue
        for c in cj:
            # keep the entry that has a value; prefer instagram (carries sessionid)
            d = {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path or "/",
                "secure": bool(getattr(c, "secure", False)),
            }
            if c.expires:
                d["expirationDate"] = c.expires
            # dedupe by name, prefer the one with a sessionid-grade value
            if c.name not in merged or (c.name == REQUIRED_COOKIE and c.value):
                merged[c.name] = d

    names = set(merged.keys())
    print(f"[cookies-auto] extracted {len(merged)} unique cookies: {sorted(names)}")
    if REQUIRED_COOKIE not in names:
        print(f"[cookies-auto] FAIL: no '{REQUIRED_COOKIE}' found - Chrome not logged into Meta? falling back")
        return False

    _save_cookies(list(merged.values()))
    print("[cookies-auto] OK - sessionid present, auto-extraction succeeded")
    return True


async def acquire_cookies_headed() -> bool:
    """FALLBACK: headed Chromium login (автор logs in once)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        return False

    if not sys.stdin.isatty() and not os.environ.get("FORCE_HEADED"):
        print("[cookies-headed] FATAL: no cookies + non-interactive shell.")
        print("[cookies-headed] Run interactively: python3 scripts/setup.py")
        print("[cookies-headed] OR set FORCE_HEADED=1 if a GUI is available.")
        return False

    print()
    print("=" * 60)
    print("THREADS / META LOGIN - one-time fallback")
    print("=" * 60)
    print("Откроется Chromium. Залогинься через Instagram-аккаунт,")
    print("дождись ленты Threads, НЕ закрывай браузер - cookies сохранятся сами.")
    print()
    input("Press ENTER to launch Chromium...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()
        await page.goto("https://www.threads.com/login/", wait_until="domcontentloaded")
        print("[cookies-headed] waiting for login (timeout 5 min)...")
        deadline = time.monotonic() + 300
        landed = False
        while time.monotonic() < deadline:
            if "/login" not in page.url and "threads.com" in page.url:
                landed = True
                print(f"[cookies-headed] landed at {page.url}")
                break
            await asyncio.sleep(1)
        if not landed:
            print("[cookies-headed] FATAL: login timeout.")
            await browser.close()
            return False
        await asyncio.sleep(3)
        cookies = await context.cookies()
        await browser.close()

    if not cookies:
        print("[cookies-headed] FATAL: no cookies captured.")
        return False
    export = []
    for c in cookies:
        ck = {
            "name": c.get("name"), "value": c.get("value"),
            "domain": c.get("domain"), "path": c.get("path", "/"),
            "secure": c.get("secure", False), "httpOnly": c.get("httpOnly", False),
            "sameSite": c.get("sameSite", "Lax"),
        }
        if c.get("expires", -1) > 0:
            ck["expirationDate"] = c["expires"]
        export.append(ck)
    _save_cookies(export)
    return True


async def run_dry_run_validation() -> bool:
    print()
    print("=" * 60)
    print("VALIDATION via radar.py --dry-run")
    print("=" * 60)
    script_dir = Path(__file__).parent
    radar_py = script_dir / "radar.py"
    venv_python = script_dir.parent / "python3"
    proc = await asyncio.create_subprocess_exec(
        str(venv_python), str(radar_py), "--dry-run",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print(line.decode("utf-8", errors="replace").rstrip())
    rc = await proc.wait()
    return rc == 0


async def main():
    print("=" * 60)
    print("Threads Radar - SETUP")
    print("=" * 60)

    print("\n[1/3] Bootstrap seeds...")
    bootstrap_seeds()

    print("\n[2/3] Meta cookies...")
    if COOKIES_PATH.exists():
        print(f"[cookies] already exist at {COOKIES_PATH}, skipping acquisition")
        ok = True
    else:
        print("[cookies] trying AUTO extraction from Chrome (no manual login)...")
        ok = acquire_cookies_auto()
        if not ok:
            print("[cookies] auto failed - falling back to headed login")
            ok = await acquire_cookies_headed()
    if not ok:
        sys.exit(2)

    print("\n[2b/3] X/Twitter cookies (EN source)...")
    if X_COOKIES_PATH.exists():
        print(f"[x-cookies] already exist at {X_COOKIES_PATH}, skipping")
    else:
        print("[x-cookies] trying AUTO extraction from Chrome...")
        x_ok = acquire_x_cookies_auto()
        if not x_ok:
            print("[x-cookies] WARN: X cookies not acquired (Chrome not logged into X?).")
            print("[x-cookies] Threads source still works; X source disabled until cookies present.")

    print("\n[3/3] Dry-run validation...")
    validation_ok = await run_dry_run_validation()
    if not validation_ok:
        print("\n[setup] WARN: dry-run incomplete (anti-bot throttle / schema drift / 0 fresh posts).")
        print("[setup] Retry later; if persistent, check selectors in scripts/radar.py.")
        sys.exit(3)

    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print("Next: full run -> python3 scripts/radar.py")


if __name__ == "__main__":
    asyncio.run(main())
