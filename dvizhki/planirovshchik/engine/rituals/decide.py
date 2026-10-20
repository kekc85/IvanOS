#!/usr/bin/env python3
"""Снять флаг «требует решения» - единственная дверь, через которую движок
трогается с места, пока интерфейс этого не умеет.

Задача, пережившая 3 переноса, дальше не двигается: она ждёт явного выбора
(правило миграции из bullet journal). Раньше флаг ставился, а снять его было
негде вообще - движок вставал молча и навсегда.

    python3 decide.py list
    python3 decide.py e5 do                 # делаю, вернуть в сетку (по умолчанию завтра)
    python3 decide.py e5 do --to 2026-09-02 # делаю такого-то числа
    python3 decide.py e5 drop               # удалить
    python3 decide.py e5 delegate           # делегировать, уходит в бэклог
    python3 decide.py e5 someday --ttl 30   # в someday с TTL

Это ДЕЙСТВИЕ ЧЕЛОВЕКА: каждая команда двигает след человека (pulse), который
читает сторож.
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    PLANNER_JSON, load_json, load_profile, today, backup_and_write_sprint,
    record_human_action, run_ritual, next_free_day, dur_min,
)

ACTIONS = ("do", "drop", "delegate", "someday")


def track_label(sprint, code):
    tracks = sprint.get("tracks") or {}
    tr = tracks.get(code) if isinstance(tracks, dict) else None
    if isinstance(tr, dict) and tr.get("label"):
        return tr["label"]
    return code or "?"


def cmd_list(sprint):
    events = [e for e in (sprint.get("events") or []) if isinstance(e, dict)]
    stuck = [e for e in events if e.get("needsDecision") is True]
    if not stuck:
        print("Задач, требующих решения, нет. Движок не заблокирован.")
        return 0
    print(f"Требуют решения: {len(stuck)}")
    for e in stuck:
        print(
            f"  {e.get('id', '?'):<6} [{track_label(sprint, e.get('track'))}] {e.get('title')} "
            f"- переносов {e.get('moved', '?')}, висит с {e.get('stuckSince', '?')}, дата {e.get('date')}"
        )
    print()
    print("Решение: decide.py <id> do | drop | delegate | someday")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Решение по застрявшей задаче планировщика")
    ap.add_argument("event_id", help="id события или слово list")
    ap.add_argument("action", nargs="?", choices=ACTIONS, help="do | drop | delegate | someday")
    ap.add_argument("--to", dest="to", default=None, help="дата возврата YYYY-MM-DD (для do)")
    ap.add_argument("--ttl", dest="ttl", type=int, default=30, help="TTL в днях для someday")
    ap.add_argument("--who", dest="who", default=None, help="кому делегировано")
    args = ap.parse_args()

    sprint, err = load_json(PLANNER_JSON)
    if err:
        print(f"Нет данных спринта: {err}")
        sys.exit(1)

    if args.event_id == "list":
        sys.exit(cmd_list(sprint))

    if not args.action:
        print("Нужно действие: do | drop | delegate | someday")
        sys.exit(2)

    events = sprint.get("events") or []
    target = None
    for e in events:
        if isinstance(e, dict) and str(e.get("id")) == args.event_id:
            target = e
            break
    if target is None:
        print(f"Событие {args.event_id} не найдено. Список: decide.py list")
        sys.exit(1)

    title = target.get("title", "?")
    profile = load_profile()
    t = today()
    what = None

    if args.action == "do":
        if args.to:
            try:
                new_date = date.fromisoformat(args.to)
            except ValueError:
                print(f"Дата {args.to!r} не разбирается, нужен формат YYYY-MM-DD")
                sys.exit(2)
        else:
            new_date, _load, _norm, _over = next_free_day(
                t, profile.get("protectedDays", ["sun"]) or [], events, profile, add_min=dur_min(target)
            )
        target.pop("needsDecision", None)
        target.pop("stuckSince", None)
        target["moved"] = 0
        target["date"] = new_date.isoformat()
        what = f"решение по «{title}»: делаю, возвращена в сетку на {new_date.isoformat()}"

    elif args.action == "drop":
        sprint["events"] = [e for e in events if e is not target]
        what = f"решение по «{title}»: удалена"

    elif args.action == "delegate":
        sprint["events"] = [e for e in events if e is not target]
        item = {
            "id": target.get("id"),
            "title": title,
            "est": target.get("est", dur_min(target)),
            "track": target.get("track"),
            "when": "делегировано" + (f": {args.who}" if args.who else ""),
        }
        sprint.setdefault("backlog", []).append(item)
        what = f"решение по «{title}»: делегирована" + (f" ({args.who})" if args.who else "")

    elif args.action == "someday":
        sprint["events"] = [e for e in events if e is not target]
        ttl_date = t + timedelta(days=max(args.ttl, 1))
        item = {
            "id": target.get("id"),
            "title": title,
            "est": target.get("est", dur_min(target)),
            "track": target.get("track"),
            "when": f"someday, TTL до {ttl_date.isoformat()}",
            "ttl": ttl_date.isoformat(),
        }
        sprint.setdefault("backlog", []).append(item)
        what = f"решение по «{title}»: в someday до {ttl_date.isoformat()}"

    backup = backup_and_write_sprint(sprint)
    record_human_action(what)
    print(what)
    print(f"sprint.json обновлён, бэкап: {backup}")
    left = [e for e in (sprint.get("events") or []) if isinstance(e, dict) and e.get("needsDecision") is True]
    print(f"Осталось требующих решения: {len(left)}")


if __name__ == "__main__":
    run_ritual("decide", main)
