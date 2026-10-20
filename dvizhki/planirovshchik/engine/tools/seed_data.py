#!/usr/bin/env python3
"""Разворачивает шаблоны данных в рабочую папку. Только stdlib.

Две вещи, ради которых это отдельный скрипт, а не пара строк в установщике:

1. НЕ ЗАТИРАЕТ. Файл уже есть - пропускаем и говорим об этом вслух. Повторный
   запуск установщика не должен стоить человеку его недели.

2. ДАТЫ ЖИВЫЕ. В шаблоне все даты отсчитаны от якорного понедельника
   2001-01-01. Здесь они сдвигаются на текущую неделю целиком, одним и тем же
   смещением - поэтому примеры попадают в сетку, которую человек видит сегодня,
   а не в 2001 год, и относительные расстояния (вторник, среда) сохраняются.

Один и тот же скрипт зовут оба установщика, Mac и Windows: логика раскладки
живёт в одном месте и не может разъехаться между платформами.

Запуск:
  python3 seed_data.py --templates <папка шаблонов> --target <папка данных>
  python3 seed_data.py ... --check      только проверить, ничего не писать
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, timedelta

ANCHOR = date(2001, 1, 1)          # понедельник, от него отсчитаны даты в шаблонах
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# имя в шаблонах -> имя в папке данных
FILES = [
    ("sprint.json", "sprint.json"),
    ("profile.json", "profile.json"),
    ("goals-cycle.json", "goals-cycle.json"),
    ("tracker.json", "tracker.json"),
    ("config.json.example", "config.json.example"),
]

SUBDIRS = ["daily", "reviews", "backups", "state", "logs"]


def monday_of_this_week(today=None):
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def shift_dates(node, delta_days):
    """Рекурсивно сдвигает КАЖДУЮ строку вида ГГГГ-ММ-ДД. Строки другой формы,
    числа и булевы не трогаем: сдвигать надо даты, а не всё подряд."""
    if isinstance(node, dict):
        return {k: shift_dates(v, delta_days) for k, v in node.items()}
    if isinstance(node, list):
        return [shift_dates(v, delta_days) for v in node]
    if isinstance(node, str) and DATE_RE.match(node):
        try:
            return (date.fromisoformat(node) + timedelta(days=delta_days)).isoformat()
        except ValueError:
            return node
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--check", action="store_true",
                    help="только проверить: что уже есть, что появится")
    args = ap.parse_args()

    templates = os.path.abspath(os.path.expanduser(args.templates))
    target = os.path.abspath(os.path.expanduser(args.target))

    if not os.path.isdir(templates):
        print("НЕ НАЙДЕНА папка шаблонов: %s" % templates)
        return 1

    delta = (monday_of_this_week() - ANCHOR).days
    created, kept, failed = [], [], []

    if not args.check:
        os.makedirs(target, exist_ok=True)
        for sub in SUBDIRS:
            os.makedirs(os.path.join(target, sub), exist_ok=True)

    for src_name, dst_name in FILES:
        src = os.path.join(templates, src_name)
        dst = os.path.join(target, dst_name)
        if not os.path.exists(src):
            failed.append("%s: шаблона нет в ките" % src_name)
            continue
        if os.path.exists(dst):
            kept.append(dst_name)
            continue
        if args.check:
            created.append(dst_name)
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as exc:
            failed.append("%s: не читается (%s)" % (src_name, exc))
            continue
        try:
            data = json.loads(raw)
        except ValueError as exc:
            failed.append("%s: битый JSON в шаблоне (%s)" % (src_name, exc))
            continue
        data = shift_dates(data, delta)
        try:
            tmp = dst + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
                f.write("\n")
            shutil.move(tmp, dst)
        except OSError as exc:
            failed.append("%s: не записался (%s)" % (dst_name, exc))
            continue
        created.append(dst_name)

    for name in created:
        print(("появится: " if args.check else "создан:  ") + name)
    for name in kept:
        print("уже есть, не трогаю: " + name)
    for line in failed:
        print("ОШИБКА: " + line)

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
