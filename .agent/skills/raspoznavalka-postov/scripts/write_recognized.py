#!/usr/bin/env python3
"""Записать результат распознавания обратно во frontmatter md-файла.

Обновляет:
  - recognized_text: распознанный текст (YAML-multiline или quoted single-line)
  - status: новое значение (по умолчанию «распознан»)
  - updated: сегодняшняя дата (ISO)

Тело документа (markdown после frontmatter) НЕ трогаем.
Идемпотентно: повторный запуск с тем же текстом ничего лишнего не делает.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import frontmatter


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Записать recognized_text в frontmatter одного md-файла."
    )
    ap.add_argument("--path", required=True, help="Путь к md-файлу")
    ap.add_argument(
        "--text",
        help="Распознанный текст. Если флага нет — читаем stdin.",
    )
    ap.add_argument(
        "--status",
        default="распознан",
        help="Новое значение поля status (default: распознан)",
    )
    ap.add_argument(
        "--no-status-change",
        action="store_true",
        help="Не трогать status (например, если уже выставлен вручную).",
    )
    args = ap.parse_args()

    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        print(f"[write_recognized] файл не найден: {path}", file=sys.stderr)
        return 2

    text = args.text if args.text is not None else sys.stdin.read()
    text = text.rstrip("\n")
    if not text:
        print("[write_recognized] пустой text — отказываюсь писать", file=sys.stderr)
        return 2

    post = frontmatter.load(path)
    post["recognized_text"] = text
    if not args.no_status_change:
        post["status"] = args.status
    post["updated"] = date.today().isoformat()

    with path.open("w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post, sort_keys=False))
        f.write("\n")

    print(
        f"[write_recognized] OK {path.name}: "
        f"{len(text)} chars, status={post.get('status')}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
