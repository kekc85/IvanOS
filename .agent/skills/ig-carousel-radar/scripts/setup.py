#!/usr/bin/env python3
"""
IG Carousel Radar - one-time setup (auto-bootstrap).

Запускается автоматически из radar.py если cookies / seeds отсутствуют.
Можно запустить руками: python3 scripts/setup.py

Flow:
  1. Bootstrap seed YAML files (watchlist + hashtags) если отсутствуют
  2. Bootstrap IG cookies через headed Chromium login (ученик логинится в СВОЙ IG в UI; BYOA)
  3. Validate via dry-run

Не требует Cookie-Editor extension. Не сохраняет username / password - только cookies post-login.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && python3 -m playwright install chromium")
    sys.exit(1)

HOME = Path.home()
COOKIES_PATH = HOME / ".business/processes/.ig-cookies.json"
WATCHLIST_PATH = HOME / ".business/growth/watchlist-en.yml"
HASHTAGS_PATH = HOME / ".business/growth/hashtags-en.yml"

WATCHLIST_SEED = """# автор - IG watchlist EN (seed v1.0 - auto-bootstrap)
# Конкуренты + reference creators в vibemarketing / vibecoding / AI tools / solopreneur EN
# Update quarterly. Cross-ref ~/.business/marketing/competitors.md before adding handles.

handles:
  # Reference creators (авторские alpha refs, validated)
  - rileybrown_ai
  - sabrina.ramonov
  - heatherbcooper

  # Solopreneur / indie hackers EN
  - levelsio
  - greg.isenberg
  - marc_louvion

  # Add 10-20 total. Источник handles - .business/marketing/competitors.md
"""

HASHTAGS_SEED = """# автор - IG hashtags EN (seed v1.0 - auto-bootstrap)
# 5-10 tags max. Узкая ниша лучше широкой.
# Anti-pattern - generic tags типа #marketing / #business (100K posts/day = noise > signal).

tags:
  - vibecoding
  - vibemarketing
  - aitools
  - claudecode
  - aimarketing
  - indiehacker
  - solopreneur
  - aiautomation
"""


def bootstrap_seeds() -> tuple[bool, bool]:
    """Create seed YAML files if missing. Returns (watchlist_created, hashtags_created)."""
    wl_created = False
    ht_created = False

    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not WATCHLIST_PATH.exists():
        WATCHLIST_PATH.write_text(WATCHLIST_SEED)
        wl_created = True
        print(f"[seeds] bootstrapped {WATCHLIST_PATH}")
    else:
        print(f"[seeds] watchlist already exists at {WATCHLIST_PATH}")

    if not HASHTAGS_PATH.exists():
        HASHTAGS_PATH.write_text(HASHTAGS_SEED)
        ht_created = True
        print(f"[seeds] bootstrapped {HASHTAGS_PATH}")
    else:
        print(f"[seeds] hashtags already exists at {HASHTAGS_PATH}")

    return wl_created, ht_created


async def acquire_cookies_via_login() -> bool:
    """Open headed Chromium → ученик logs in into HIS OWN IG → save HIS cookies on landing (BYOA)."""
    if COOKIES_PATH.exists():
        print(f"[cookies] already exist at {COOKIES_PATH}, skipping login")
        return True

    if not sys.stdin.isatty() and not os.environ.get("FORCE_HEADED"):
        print("[cookies] FATAL: no cookies + non-interactive shell.")
        print("[cookies] Run interactively: python3 scripts/setup.py")
        print("[cookies] OR set FORCE_HEADED=1 если уверен что GUI доступен")
        return False

    COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("IG LOGIN - one-time setup (BYOA: твоя сессия, не автора курса)")
    print("=" * 60)
    print("Сейчас откроется Chromium с https://instagram.com/accounts/login")
    print("Действия:")
    print("  1. Залогинься в СВОЙ IG руками (включая 2FA если нужно)")
    print("  2. Дождись landing на feed (главная IG страница)")
    print("  3. НЕ закрывай браузер - script сохранит cookies автоматически")
    print("  4. Script автоматически закроет браузер через 3 секунды после landing")
    print()
    input("Press ENTER to launch Chromium...")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        print("[cookies] waiting for login (timeout 5 min)...")

        # Wait until URL goes off /accounts/login/ (= успешный login)
        deadline = time.monotonic() + 300
        landed = False
        while time.monotonic() < deadline:
            current = page.url
            if "/accounts/login" not in current and "/accounts/onetap" not in current and "/accounts/login" not in current:
                # Make sure we're on actual IG feed or main page
                if "instagram.com" in current and "/login" not in current:
                    landed = True
                    print(f"[cookies] landed at {current}")
                    break
            await asyncio.sleep(1)

        if not landed:
            print("[cookies] FATAL: login timeout (5 min). Аборт.")
            await browser.close()
            return False

        # Wait 3 sec for cookies to stabilize
        print("[cookies] stabilizing for 3s...")
        await asyncio.sleep(3)

        cookies = await context.cookies()
        await browser.close()

    if not cookies:
        print("[cookies] FATAL: no cookies captured.")
        return False

    # Save in Cookie-Editor compatible format (matches radar.py loader)
    export = []
    for c in cookies:
        ck = {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "sameSite": c.get("sameSite", "Lax"),
        }
        if c.get("expires", -1) > 0:
            ck["expirationDate"] = c["expires"]
        export.append(ck)

    COOKIES_PATH.write_text(json.dumps(export, indent=2))
    os.chmod(COOKIES_PATH, 0o600)
    print(f"[cookies] saved {len(export)} cookies to {COOKIES_PATH} (chmod 600)")
    return True


async def run_dry_run_validation() -> bool:
    """Re-invoke radar.py --dry-run to validate setup."""
    print()
    print("=" * 60)
    print("VALIDATION via radar.py --dry-run")
    print("=" * 60)

    script_dir = Path(__file__).parent
    radar_py = script_dir / "radar.py"
    venv_python = script_dir.parent / "python3"

    proc = await asyncio.create_subprocess_exec(
        str(venv_python),
        str(radar_py),
        "--dry-run",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
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
    print("IG Carousel Radar - SETUP")
    print("=" * 60)

    # 1. Seeds
    print("\n[1/3] Bootstrap seeds...")
    bootstrap_seeds()

    # 2. Cookies
    print("\n[2/3] IG cookies...")
    cookies_ok = await acquire_cookies_via_login()
    if not cookies_ok:
        sys.exit(2)

    # 3. Validate
    print("\n[3/3] Dry-run validation...")
    validation_ok = await run_dry_run_validation()
    if not validation_ok:
        print("\n[setup] WARN: dry-run incomplete. Check logs above.")
        print("[setup] Common causes:")
        print("  - IG GraphQL schema changed (maintenance update в scripts/radar.py)")
        print("  - Anti-bot soft-block (retry в 24h)")
        print("  - 0 carousels in 1-sample dry-run (normal если accounts не публикуют сейчас)")
        sys.exit(3)

    print()
    print("=" * 60)
    print("SETUP COMPLETE ✓")
    print("=" * 60)
    print("Next: full run")
    print("  python3 scripts/radar.py")
    print()
    print("Optional cron 08:00 daily:")
    print("  /schedule create ig-carousel-radar")
    print()


if __name__ == "__main__":
    asyncio.run(main())