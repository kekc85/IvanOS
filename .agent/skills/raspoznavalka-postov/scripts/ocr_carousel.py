#!/usr/bin/env python3
"""OCR Instagram-карусели/фото через OpenAI Vision.

Pipeline на один URL:
  1. shortcode из URL.
  2. Apify `apify/instagram-scraper` → slide URLs.
  3. Параллельная скачка слайдов в RAM (Semaphore=MAX_PARALLEL).
  4. Каждый слайд → OpenAI Vision → текст.
  5. Склейка «Слайд N:\\n{text}» через \\n\\n.

Ошибки одного слайда не валят всю карусель — маркер `[OCR_ERROR: ...]`.

ENV:
  OPENAI_API_KEY — обязателен
  APIFY_TOKEN    — обязателен
  VISION_MODEL   — опционально (default: gpt-4o; gpt-4o-mini для экономии)

Output (stdout): JSON
  {"ok": bool, "text": str, "slides_count": int,
   "cost_openai_usd": float, "cost_apify_usd": float,
   "error": str|None, "slide_errors": [str]}
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field

import httpx
from openai import AsyncOpenAI

# Импорт соседнего модуля (когда запускаем `python scripts/ocr_carousel.py`)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apify_client import run_actor_and_wait  # noqa: E402

log = logging.getLogger("ocr_carousel")
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)


APIFY_POST_ACTOR = "apify/instagram-scraper"
DEFAULT_VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o")

# Один high-res IG-слайд = ~1.1k токенов на gpt-4o (vs ~85k на mini), но
# TPM-лимиты у 4o тоже строже — параллелим=1 и разруливаем 429 backoff'ом.
MAX_PARALLEL_OCR_SLIDES = 1
OPENAI_429_BACKOFF_SEC = (4, 16, 30, 60, 90, 120)
SLIDE_DOWNLOAD_TIMEOUT = 30.0
SLIDE_DOWNLOAD_RETRIES = 3

OPENAI_VISION_PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.150, 0.600),
    "gpt-4o": (2.500, 10.000),
}

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

OCR_PROMPT = """На изображении — слайд карусели Instagram на русском языке.
Извлеки ВЕСЬ видимый текст: основной текст, overlay-надписи, мелкий текст,
цифры, подписи. Сохраняй оригинальное написание (КАПС оставляй КАПСОМ).
Не пересказывай, не интерпретируй, не добавляй вступлений.
Если текста на слайде нет — верни одну строку: [нет текста]"""

_SHORTCODE_RE = re.compile(r"/(?:p|reel|reels)/([A-Za-z0-9_-]+)")


@dataclass
class OcrResult:
    ok: bool
    text: str = ""
    slides_count: int = 0
    error: str | None = None
    cost_openai_usd: float = 0.0
    cost_apify_usd: float = 0.0
    slide_errors: list[str] = field(default_factory=list)


def extract_shortcode(url: str) -> str | None:
    m = _SHORTCODE_RE.search(url or "")
    return m.group(1) if m else None


async def _scrape_post(token: str, shortcode: str) -> tuple[dict | None, float]:
    run_input = {
        "directUrls": [f"https://www.instagram.com/p/{shortcode}/"],
        "resultsType": "posts",
        "resultsLimit": 1,
        "addParentData": False,
    }
    res = await run_actor_and_wait(token, APIFY_POST_ACTOR, run_input)
    target = None
    for it in res.items:
        sc = it.get("shortCode") or it.get("shortcode")
        if sc and sc == shortcode:
            target = it
            break
    if target is None and res.items:
        target = res.items[0]
    return target, res.cost_usd


def _extract_slide_urls(item: dict) -> list[str]:
    images = item.get("images")
    if isinstance(images, list) and images:
        urls = [
            u if isinstance(u, str) else (u.get("url") or u.get("displayUrl"))
            for u in images
        ]
        urls = [u for u in urls if u]
        if urls:
            return urls
    for key in ("childPosts", "sidecarChildren"):
        children = item.get(key)
        if isinstance(children, list) and children:
            urls = [c.get("displayUrl") or c.get("url") for c in children]
            urls = [u for u in urls if u]
            if urls:
                return urls
    if item.get("displayUrl"):
        return [item["displayUrl"]]
    return []


async def _download_slides(urls: list[str]) -> list[bytes]:
    sem = asyncio.Semaphore(MAX_PARALLEL_OCR_SLIDES)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(SLIDE_DOWNLOAD_TIMEOUT),
        headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"},
    ) as c:
        tasks = [_download_one(c, sem, u) for u in urls]
        return await asyncio.gather(*tasks)


async def _download_one(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str
) -> bytes:
    last_err: Exception | None = None
    async with sem:
        for attempt in range(SLIDE_DOWNLOAD_RETRIES):
            try:
                r = await client.get(url)
                if r.status_code == 200 and r.content:
                    return r.content
                last_err = httpx.HTTPError(f"HTTP {r.status_code}")
            except Exception as e:  # noqa: BLE001
                last_err = e
            if attempt + 1 < SLIDE_DOWNLOAD_RETRIES:
                await asyncio.sleep(2)
        raise RuntimeError(f"download failed: {url} ({last_err})")


async def _ocr_slides_openai(
    slide_bytes: list[bytes], *, openai_key: str, model: str,
) -> tuple[list[str], float, list[str]]:
    # SDK retry оставляем 1 — основной backoff делаем сами (SDK не знает про
    # длинные TPM-паузы и просто сжигает попытки).
    client = AsyncOpenAI(api_key=openai_key, max_retries=1)
    sem = asyncio.Semaphore(MAX_PARALLEL_OCR_SLIDES)

    async def one(blob: bytes) -> tuple[str, int, int, str | None]:
        from openai import RateLimitError, APIError

        b64 = base64.b64encode(blob).decode("ascii")
        async with sem:
            last_err_repr = ""
            for pause in (0, *OPENAI_429_BACKOFF_SEC):
                if pause:
                    await asyncio.sleep(pause)
                try:
                    resp = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": OCR_PROMPT},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{b64}"
                                        },
                                    },
                                ],
                            }
                        ],
                        max_tokens=2000,
                    )
                except RateLimitError as e:
                    last_err_repr = repr(e)[:200]
                    log.warning("openai 429 (TPM?) — backoff next")
                    continue
                except APIError as e:
                    last_err_repr = repr(e)[:200]
                    log.warning("openai APIError, retry: %r", e)
                    continue
                except Exception as e:  # noqa: BLE001
                    err = repr(e)[:200]
                    return f"[OCR_ERROR: {err}]", 0, 0, err

                text = (resp.choices[0].message.content or "").strip()
                usage = resp.usage
                in_tok = usage.prompt_tokens if usage else 0
                out_tok = usage.completion_tokens if usage else 0
                return text, in_tok, out_tok, None

            return f"[OCR_ERROR: {last_err_repr}]", 0, 0, last_err_repr

    results = await asyncio.gather(*[one(b) for b in slide_bytes])

    texts: list[str] = []
    errors: list[str] = []
    total_in = 0
    total_out = 0
    for text, in_tok, out_tok, err in results:
        texts.append(text)
        total_in += in_tok
        total_out += out_tok
        if err:
            errors.append(err)

    cost = _openai_vision_cost(model, total_in, total_out)
    return texts, cost, errors


def _openai_vision_cost(model: str, in_tok: int, out_tok: int) -> float:
    pricing = OPENAI_VISION_PRICING_USD_PER_MTOK.get(model)
    if pricing is None:
        log.warning("no pricing for OpenAI model %s — cost=0", model)
        return 0.0
    in_price, out_price = pricing
    return (in_tok / 1_000_000) * in_price + (out_tok / 1_000_000) * out_price


async def ocr_carousel(
    url: str, *, openai_key: str, apify_token: str, model: str,
) -> OcrResult:
    shortcode = extract_shortcode(url)
    if shortcode is None:
        return OcrResult(ok=False, error=f"invalid IG URL: {url}")

    try:
        item, apify_cost = await _scrape_post(apify_token, shortcode)
    except Exception as e:  # noqa: BLE001
        return OcrResult(ok=False, error=f"apify scrape: {e}")

    if item is None:
        return OcrResult(
            ok=False,
            error="apify вернул пустой результат",
            cost_apify_usd=apify_cost,
        )

    if item.get("error"):
        return OcrResult(
            ok=False,
            error=f"IG: {item.get('error')}: {item.get('errorDescription', '')}",
            cost_apify_usd=apify_cost,
        )

    slide_urls = _extract_slide_urls(item)
    if not slide_urls:
        return OcrResult(
            ok=False,
            error="нет URL слайдов в scraped item",
            cost_apify_usd=apify_cost,
        )

    try:
        slide_bytes = await _download_slides(slide_urls)
    except Exception as e:  # noqa: BLE001
        return OcrResult(
            ok=False,
            error=f"download: {e}",
            cost_apify_usd=apify_cost,
        )

    texts, openai_cost, slide_errors = await _ocr_slides_openai(
        slide_bytes, openai_key=openai_key, model=model
    )

    parts = [f"Слайд {i}:\n{t}" for i, t in enumerate(texts, 1)]
    return OcrResult(
        ok=True,
        text="\n\n".join(parts),
        slides_count=len(texts),
        cost_openai_usd=openai_cost,
        cost_apify_usd=apify_cost,
        slide_errors=slide_errors,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="OCR одной Instagram-карусели/фото.")
    ap.add_argument("--url", required=True, help="URL поста Instagram")
    ap.add_argument(
        "--model",
        default=DEFAULT_VISION_MODEL,
        help=f"OpenAI Vision model (default: {DEFAULT_VISION_MODEL})",
    )
    args = ap.parse_args()

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    apify_token = os.getenv("APIFY_TOKEN", "").strip()
    if not openai_key:
        print("OPENAI_API_KEY не задан в env", file=sys.stderr)
        return 2
    if not apify_token:
        print("APIFY_TOKEN не задан в env", file=sys.stderr)
        return 2

    res = asyncio.run(
        ocr_carousel(
            args.url,
            openai_key=openai_key,
            apify_token=apify_token,
            model=args.model,
        )
    )

    out = {
        "ok": res.ok,
        "text": res.text,
        "slides_count": res.slides_count,
        "cost_openai_usd": round(res.cost_openai_usd, 6),
        "cost_apify_usd": round(res.cost_apify_usd, 6),
        "error": res.error,
        "slide_errors": res.slide_errors,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
