#!/usr/bin/env python3
"""Точечный обход доноров-носителей формата «текст-заметка / Claude-эксперимент».
Переиспользует функции radar.py. БЕЗ вирал-отсечки (жанр даёт высокий comment при
умеренном like). Фильтр: carousel + age < AGE_DAYS. Тянет slide-1 thumbs для
визуальной проверки формата + печатает структурированный список."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import radar  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

# Доноры-носители note-text / Claude-experiment / solopreneur-note жанра
DONORS = [
    "taki.gpt", "charliehills", "talnavarro1", "alyciachapman_", "maverickgpt",
    "carter.braydon", "theclarkgary", "matthgray", "justinwelsh",
    "milamarksonofficial", "sabrina.ramonov", "gannon.meyer", "imanoubou",
    "realrileybrown", "quantumfield.ai",
]
AGE_DAYS = 30
PER_PROFILE = 12


async def main():
    radar.refresh_cookies_from_chrome()
    cookies = radar.load_cookies()
    radar.log(f"[donor-sweep] cookies: {len(cookies)} entries")
    done = radar.load_done_shortcodes()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        await context.add_cookies(cookies)
        caps = await radar.mode_b_watchlist(context, DONORS, PER_PROFILE)
        await browser.close()

    # Dedup by shortcode, keep carousels, recent, not-done
    seen = {}
    for c in caps:
        if not c.is_carousel or not c.shortcode:
            continue
        if c.shortcode in done:
            continue
        if c.age_hours > AGE_DAYS * 24:
            continue
        if c.shortcode not in seen or c.comments > seen[c.shortcode].comments:
            seen[c.shortcode] = c

    out = sorted(seen.values(), key=lambda c: c.comments, reverse=True)
    radar.log(f"[donor-sweep] {len(out)} fresh carousels from {len(DONORS)} donors")

    rows = []
    for c in out:
        thumb = radar.download_thumb(c)
        rows.append({
            "author": c.author, "shortcode": c.shortcode, "url": c.url,
            "age": c.age_human, "likes": c.likes, "comments": c.comments,
            "views": c.views, "caption": c.caption[:240],
            "thumb": str(thumb) if thumb else "",
        })

    outpath = Path.home() / "Desktop" / "ig-digest" / "donor-sweep.json"
    outpath.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n=== {len(rows)} CAROUSELS ===")
    for r in rows:
        print(f"@{r['author']} | {r['age']} | {r['likes']}L {r['comments']}C | "
              f"{r['shortcode']} | {r['caption'][:90]}")
    print(f"\nJSON: {outpath}")


if __name__ == "__main__":
    asyncio.run(main())