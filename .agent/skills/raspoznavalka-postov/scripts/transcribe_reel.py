#!/usr/bin/env python3
"""Транскрипция Instagram-рилза через sian.agency.

V1 — sian-only:
  1. URL → sian.agency Apify-актор → транскрипт.
  2. Если sian вернул пустоту/null — `[нет распознаваемой речи]`.
  3. Если actor упал/timeout — ok=false с error.

КРИТИЧНО:
  Actor `sian.agency/instagram-ai-transcript-extractor` ИГНОРИРУЕТ `postUrls`
  и читает singular `instagramUrl`. Без него возвращает дефолтный Zig Ziglar
  транскрипт на любой URL. Передаём ОБА поля чтобы actor точно не свалился
  в default. Дополнительная защита: сверяем shortCode в ответе.

Правило 10 секунд (опционально через --caption):
  Если --caption передан и его длина > 100 chars, и duration ≤ 10s
  → ничего не транскрибируем, вернём text=`[caption-only b-roll: <caption>]`.
  Это экономит один Apify-вызов на коротких рилзах-«b-roll» с длинной подписью.
  Узнать duration без scrape мы не можем — но если caption длинный, скорее
  всего рилз и сам короткий; делаем scrape и сверяем duration по факту.

ENV:
  APIFY_TOKEN — обязателен
  TRANSCRIPT_SIAN_ACTOR — опционально (default: sian.agency/instagram-ai-transcript-extractor)

Output (stdout): JSON
  {"ok": bool, "text": str, "via": "sian"|"no_speech"|"caption_only"|"error",
   "duration_sec": float|None, "cost_sian_usd": float, "error": str|None}
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Any

# Импорт соседнего модуля
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apify_client import run_actor_and_wait, ApifyError  # noqa: E402

log = logging.getLogger("transcribe_reel")
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)


SIAN_ACTOR = os.getenv(
    "TRANSCRIPT_SIAN_ACTOR", "sian.agency/instagram-ai-transcript-extractor"
)
NO_SPEECH_MARKER = "[нет распознаваемой речи]"
SHORT_REEL_THRESHOLD_SEC = 10.0
CAPTION_ONLY_MIN_CHARS = 100

_SHORTCODE_RE = re.compile(r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)")


@dataclass
class TranscribeResult:
    ok: bool
    text: str = ""
    via: str = ""  # sian | no_speech | caption_only | error
    error: str | None = None
    cost_sian_usd: float = 0.0
    duration_sec: float | None = None


def extract_reel_shortcode(url: str) -> str | None:
    m = _SHORTCODE_RE.search(url or "")
    return m.group(1) if m else None


def _extract_sian_transcript(
    items: list[dict[str, Any]], *, url: str
) -> tuple[str, float | None]:
    """Достать транскрипт и длительность из sian-ответа.

    Защита от Zig Ziglar default: проверяем что item.url содержит наш shortCode.
    """
    target_sc = extract_reel_shortcode(url)
    best_text = ""
    best_dur: float | None = None
    for it in items:
        text = (
            it.get("transcript")
            or it.get("transcription")
            or it.get("text")
            or ""
        )
        if not isinstance(text, str):
            text = ""
        text = text.strip()
        dur = it.get("duration") or it.get("videoDuration")
        try:
            dur_f = float(dur) if dur is not None else None
        except (TypeError, ValueError):
            dur_f = None

        item_url = (
            it.get("url") or it.get("instagramUrl") or it.get("postUrl") or ""
        )
        if target_sc and item_url and target_sc not in item_url:
            log.warning(
                "sian returned wrong shortCode (expected %s in %s) — skipping",
                target_sc, item_url[:80],
            )
            continue

        if text and len(text) > len(best_text):
            best_text = text
            best_dur = dur_f

    return best_text, best_dur


async def transcribe_reel(
    url: str, *, apify_token: str, caption: str = "",
) -> TranscribeResult:
    """Транскрибировать один рилз. Не бросает исключений."""
    shortcode = extract_reel_shortcode(url)
    if shortcode is None:
        return TranscribeResult(
            ok=False, via="error", error=f"invalid IG reel URL: {url}"
        )

    run_input = {
        "postUrls": [url],
        "instagramUrl": url,
        "wordLevelTimestamps": False,
        "fastProcessing": False,
        "reelCount": 10,
    }
    try:
        res = await run_actor_and_wait(
            apify_token, SIAN_ACTOR, run_input, timeout_sec=240
        )
    except ApifyError as e:
        return TranscribeResult(
            ok=False, via="error", error=f"sian apify error: {e}"
        )
    except Exception as e:  # noqa: BLE001
        log.exception("sian unexpected error: %r", e)
        return TranscribeResult(
            ok=False, via="error", error=f"sian unexpected: {e!r}"
        )

    transcript, duration = _extract_sian_transcript(res.items, url=url)
    cost = res.cost_usd

    # Правило 10 сек: если у нас сейчас короткое видео с длинным caption —
    # считаем это b-roll'ом и помечаем как caption-only. Транскрипт всё равно
    # уже получен, но он, как правило, шумный/пустой; смыслово прав caption.
    if (
        caption
        and duration is not None
        and duration <= SHORT_REEL_THRESHOLD_SEC
        and len(caption) > CAPTION_ONLY_MIN_CHARS
    ):
        return TranscribeResult(
            ok=True,
            text=f"[caption-only b-roll: {caption}]",
            via="caption_only",
            cost_sian_usd=cost,
            duration_sec=duration,
        )

    if not transcript:
        return TranscribeResult(
            ok=True,
            text=NO_SPEECH_MARKER,
            via="no_speech",
            cost_sian_usd=cost,
            duration_sec=duration,
        )

    return TranscribeResult(
        ok=True,
        text=transcript,
        via="sian",
        cost_sian_usd=cost,
        duration_sec=duration,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Транскрипция одного Instagram-рилза.")
    ap.add_argument("--url", required=True, help="URL рилза")
    ap.add_argument(
        "--caption",
        default="",
        help="Caption поста (для правила 10 сек). Опционально.",
    )
    args = ap.parse_args()

    apify_token = os.getenv("APIFY_TOKEN", "").strip()
    if not apify_token:
        print("APIFY_TOKEN не задан в env", file=sys.stderr)
        return 2

    res = asyncio.run(
        transcribe_reel(args.url, apify_token=apify_token, caption=args.caption)
    )

    out = {
        "ok": res.ok,
        "text": res.text,
        "via": res.via,
        "duration_sec": res.duration_sec,
        "cost_sian_usd": round(res.cost_sian_usd, 6),
        "error": res.error,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
