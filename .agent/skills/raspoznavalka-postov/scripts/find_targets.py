#!/usr/bin/env python3
"""Сканер базы знаний (.business) — ищет md-файлы постов, готовые к распознаванию.

Фильтр кандидатов:
  - YAML-frontmatter валиден
  - network == "Instagram"
  - type in (--type ...)  (по умолчанию «карусель» и «рилз»)
  - recognized_text пустое  (если не --force)

Output: JSON массив в stdout — `[{path, id, type, url, caption, network}, ...]`
По умолчанию sort'нут по published DESC (свежие первыми).

Stderr — человекочитаемая сводка (для логов).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import frontmatter


DEFAULT_TYPES = ("карусель", "рилз")


def is_empty(v) -> bool:
    """`recognized_text: ""`, отсутствие поля или None — всё считаем «пустым»."""
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Найти Instagram-посты в базе знаний (.business), готовые к распознаванию."
    )
    ap.add_argument("archive_dir", help="Папка с md-файлами архива")
    ap.add_argument(
        "--type",
        action="append",
        choices=("карусель", "рилз", "пост"),
        help="Тип контента (повторяемо). По умолчанию: карусель + рилз.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Включить уже распознанные (recognized_text непустой).",
    )
    ap.add_argument(
        "--limit", type=int, default=None, help="Ограничить число кандидатов."
    )
    args = ap.parse_args()

    archive = Path(args.archive_dir).expanduser().resolve()
    if not archive.exists():
        print(f"[find_targets] папка не существует: {archive}", file=sys.stderr)
        return 2

    allowed_types = tuple(args.type) if args.type else DEFAULT_TYPES

    candidates: list[dict] = []
    seen_total = 0
    skipped_bad = 0

    for path in sorted(archive.rglob("*.md")):
        seen_total += 1
        try:
            post = frontmatter.load(path)
        except Exception as e:  # noqa: BLE001
            print(f"[find_targets] {path}: bad frontmatter — {e}", file=sys.stderr)
            skipped_bad += 1
            continue

        meta = post.metadata or {}
        if meta.get("network") != "Instagram":
            continue
        if meta.get("type") not in allowed_types:
            continue
        if not args.force and not is_empty(meta.get("recognized_text")):
            continue

        url = (meta.get("url") or "").strip()
        if not url or "instagram.com" not in url:
            continue

        candidates.append({
            "path": str(path),
            "id": (meta.get("id") or "").strip(),
            "type": meta.get("type"),
            "url": url,
            "caption": (meta.get("caption") or "").strip(),
            "network": meta.get("network"),
            "status": meta.get("status"),
            "published": str(meta.get("published") or ""),
        })

    candidates.sort(key=lambda c: c["published"], reverse=True)

    if args.limit is not None and args.limit > 0:
        candidates = candidates[: args.limit]

    by_type: dict[str, int] = {}
    for c in candidates:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1

    print(
        f"[find_targets] scanned={seen_total} bad_yaml={skipped_bad} "
        f"candidates={len(candidates)} by_type={by_type}",
        file=sys.stderr,
    )

    json.dump(candidates, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
