#!/usr/bin/env python3
"""Batch-обёртка для распознавалки: идёт по списку кандидатов и распознаёт их подряд.

Кроссплатформенно — одинаково работает на macOS и Windows. Читает API-ключи из
.env через python-dotenv, чтобы не зависеть от shell-обёрток (на Mac source-нуть
.env в bash легко, на Win в PowerShell — отдельный синтаксис; python-dotenv
снимает разницу).

Использование:

    python3 batch_recognize.py --archive "<путь к папке записи/>"

Опции:
    --types карусель,рилз     Что распознавать (по умолчанию: оба)
    --limit N                 Ограничить число постов
    --force                   Перезаписать уже распознанные
    --env PATH                Явный путь к .env (по умолчанию: автопоиск)
    --vision-model NAME       Override OPENAI_API модели (по умолчанию: gpt-4o)
    --status NAME             Новое значение поля status (default: распознан)
    --dry-run                 Только показать что будет сделано, не вызывать API

Цепочка на каждом посту:
    карусель → scripts/ocr_carousel.py --url ...
    рилз     → scripts/transcribe_reel.py --url ... --caption ...
    → scripts/write_recognized.py --path ... --status ...

Один пост = одна транзакция. Падение одного не валит batch. Прогресс пишется
в stderr каждые 5 постов. Финальный отчёт — в stdout как JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print(
        "[batch_recognize] ERROR: нет python-dotenv. Установи:\n"
        "  python3 -m pip install --user -r scripts/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)


SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # тот же python, которым запущен этот скрипт


def find_env() -> Path | None:
    """Автопоиск .env в типичных местах."""
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / "secrets.nosync" / ".env",
        Path.cwd() / "secrets" / ".env",
        Path.home() / ".claude" / ".env",
        # рядом со скриптом — на случай локальной разработки
        SCRIPT_DIR.parent.parent / ".env",
    ]
    # пройти вверх по родительским папкам до 4-х уровней от cwd
    p = Path.cwd()
    for _ in range(4):
        candidates.append(p / "secrets.nosync" / ".env")
        candidates.append(p / "secrets" / ".env")
        p = p.parent

    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def load_keys(env_path: Path | None) -> None:
    """Загружает .env в os.environ. Падает если ключей нет."""
    if env_path:
        load_dotenv(env_path, override=False)
        print(f"[batch_recognize] загрузил .env из {env_path}", file=sys.stderr)
    else:
        # python-dotenv по умолчанию ищет .env в cwd
        load_dotenv(override=False)

    missing = [k for k in ("OPENAI_API_KEY", "APIFY_TOKEN") if not os.environ.get(k)]
    if missing:
        print(
            f"[batch_recognize] ERROR: в окружении нет: {', '.join(missing)}.\n"
            "Проверь что .env лежит в одном из мест:\n"
            "  - .business/../secrets.nosync/.env (Mac, рекомендуется)\n"
            "  - .business/../secrets/.env (Windows)\n"
            "  - ~/.claude/.env\n"
            "Или передай явно через --env PATH",
            file=sys.stderr,
        )
        sys.exit(2)


def find_targets(archive: Path, types: list[str], force: bool, limit: int | None) -> list[dict]:
    """Вызывает find_targets.py, возвращает список кандидатов."""
    cmd = [PYTHON, str(SCRIPT_DIR / "find_targets.py"), str(archive)]
    for t in types:
        cmd += ["--type", t]
    if force:
        cmd.append("--force")
    if limit:
        cmd += ["--limit", str(limit)]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"[batch_recognize] find_targets упал: {proc.stderr}", file=sys.stderr)
        sys.exit(proc.returncode)

    print(proc.stderr, file=sys.stderr, end="")
    return json.loads(proc.stdout)


def recognize_one(c: dict, vision_model: str | None) -> dict:
    """Распознаёт один пост. Возвращает {ok, text, cost, error, raw}."""
    env = os.environ.copy()
    if vision_model:
        env["VISION_MODEL"] = vision_model

    if c["type"] == "карусель":
        script = SCRIPT_DIR / "ocr_carousel.py"
        cmd = [PYTHON, str(script), "--url", c["url"]]
    elif c["type"] == "рилз":
        script = SCRIPT_DIR / "transcribe_reel.py"
        cmd = [PYTHON, str(script), "--url", c["url"], "--caption", c.get("caption", "")]
    else:
        return {"ok": False, "text": "", "error": f"unknown type: {c['type']}", "cost": {}}

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        return {
            "ok": False,
            "text": "",
            "error": f"script exit {proc.returncode}: {proc.stderr.strip()[:300]}",
            "cost": {},
        }

    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "text": "",
            "error": f"bad json from {script.name}: {e}",
            "cost": {},
        }

    cost = {k: v for k, v in out.items() if k.startswith("cost_")}
    return {
        "ok": bool(out.get("ok")),
        "text": out.get("text", ""),
        "error": out.get("error"),
        "cost": cost,
        "raw": out,
    }


def write_one(path: Path, text: str, status: str) -> bool:
    """Пишет recognized_text через write_recognized.py (через stdin для длинных)."""
    cmd = [
        PYTHON,
        str(SCRIPT_DIR / "write_recognized.py"),
        "--path", str(path),
        "--status", status,
    ]
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"[batch_recognize] write упал на {path.name}: {proc.stderr}", file=sys.stderr)
        return False
    return True


def fmt_cost(cost: dict[str, float]) -> str:
    if not cost:
        return ""
    parts = []
    for k, v in cost.items():
        name = k.replace("cost_", "").replace("_usd", "")
        parts.append(f"{name}=${v:.4f}")
    return " (" + ", ".join(parts) + ")"


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch-распознавалка IG-каруселей и рилзов.")
    ap.add_argument("--archive", required=True, help="Путь к папке записи/ архива")
    ap.add_argument("--types", default="карусель,рилз", help="Через запятую: карусель, рилз, пост")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--env", help="Путь к .env (по умолчанию: автопоиск)")
    ap.add_argument("--vision-model", default=None)
    ap.add_argument("--status", default="распознан")
    ap.add_argument("--dry-run", action="store_true", help="Только показать кандидатов")
    args = ap.parse_args()

    env_path = Path(args.env).expanduser().resolve() if args.env else find_env()
    load_keys(env_path)

    archive = Path(args.archive).expanduser().resolve()
    if not archive.is_dir():
        print(f"[batch_recognize] ERROR: папка не найдена: {archive}", file=sys.stderr)
        return 2

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    candidates = find_targets(archive, types, args.force, args.limit)

    if not candidates:
        print(json.dumps({"ok": True, "total": 0, "processed": 0, "errors": []}, ensure_ascii=False))
        print("[batch_recognize] нет кандидатов — нечего распознавать", file=sys.stderr)
        return 0

    print(f"[batch_recognize] кандидатов: {len(candidates)}", file=sys.stderr)
    if args.dry_run:
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
        return 0

    total = len(candidates)
    ok_count = 0
    fail_count = 0
    errors: list[dict] = []
    total_cost: dict[str, float] = {}
    started = time.time()

    for i, c in enumerate(candidates, 1):
        print(
            f"[batch_recognize] [{i}/{total}] {c['type']} {c['id']} → распознаю…",
            file=sys.stderr,
        )
        result = recognize_one(c, args.vision_model)

        if result["ok"]:
            wrote = write_one(Path(c["path"]), result["text"], args.status)
            if wrote:
                ok_count += 1
                for k, v in result["cost"].items():
                    total_cost[k] = total_cost.get(k, 0.0) + v
                print(
                    f"[batch_recognize] [{i}/{total}] ✓ {c['id']}"
                    f"{fmt_cost(result['cost'])}",
                    file=sys.stderr,
                )
            else:
                fail_count += 1
                errors.append({"id": c["id"], "type": c["type"], "error": "write failed"})
        else:
            fail_count += 1
            errors.append({"id": c["id"], "type": c["type"], "error": result.get("error", "?")})
            print(
                f"[batch_recognize] [{i}/{total}] ✗ {c['id']}: {result.get('error')}",
                file=sys.stderr,
            )

        if i % 5 == 0 and i < total:
            elapsed = int(time.time() - started)
            print(
                f"[batch_recognize] прогресс: {i}/{total} (✓{ok_count} ✗{fail_count}) "
                f"за {elapsed}s, $ так далее: {fmt_cost(total_cost) or '$0'}",
                file=sys.stderr,
            )

    elapsed = int(time.time() - started)
    summary = {
        "ok": fail_count == 0,
        "total": total,
        "processed": ok_count,
        "failed": fail_count,
        "elapsed_sec": elapsed,
        "cost": total_cost,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        f"[batch_recognize] ИТОГ: ✓{ok_count} ✗{fail_count} из {total}, "
        f"за {elapsed//60}m{elapsed%60}s{fmt_cost(total_cost)}",
        file=sys.stderr,
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
