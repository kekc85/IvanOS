#!/usr/bin/env python3
"""Класс нулевой терпимости отдельно от порогов: ось 4 гейта novice.

ЗАЧЕМ ЭТОТ ФАЙЛ (наряд R-48, дыра обхода). Флаг `--skip-novice` был задуман под
легаси-операции: у старой страницы плотность жаргона и терминальные скрины -
известная стоимость переиздания, ронять из-за них волну правок бессмысленно. Но
флаг гасил ВЕСЬ гейт целиком, вместе с классом «тех-деталь для продвинутых», у
которого порога нет вовсе: закон владельца 23.08.2026 звучит как «ноль вхождений»
(`~/.claude/skills/lead-magnit/knowledge/novice-standard.md` §2.1). То есть любая
легаси-операция могла законно провезти на прод «код 403» и «три узла».

Поэтому под флагом гейт novice не снимается, а СУЖАЕТСЯ до этого файла: пороговые
оси не судятся, класс нулевой терпимости судится по-прежнему и роняет стадию.

Как судит: зовёт боевой `novice-check.py --json` и смотрит одно поле -
`tech_detail_hits`. Печатает пары «что убираем → чем заменяем» прямо в вывод,
чтобы исполнителю не приходилось лезть в канон за формулировкой.

ПОЧЕМУ ЕСТЬ ЗАПАСНОЙ ВЫХОД ПО КОДУ ВОЗВРАТА. В песочнице селфтеста соседние
инструменты стоят стабами: стаб печатает пусто и объявляет вердикт кодом
возврата. Если stdout не разбирается как JSON, этот файл не выдумывает вердикт, а
повторяет код возврата инструмента - тогда герметичность песочницы сохраняется, а
в бою (настоящий JSON) судит ровно ось 4.

Использование: novice_zero.py <target> --tool <путь к novice-check.py>
                               [--stage draft|page] [--doors <канон>]
"""
import argparse
import json
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--tool", required=True)
    ap.add_argument("--stage", default="auto")
    ap.add_argument("--doors", default=None)
    a = ap.parse_args()

    cmd = [sys.executable, a.tool, a.target, "--stage", a.stage, "--json"]
    if a.doors:
        cmd += ["--doors", a.doors]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        res = json.loads(r.stdout)
    except Exception:
        print("novice-zero: инструмент ответил не JSON, повторяю его код возврата "
              f"{r.returncode} (режим песочницы/стаба)")
        if r.stdout.strip():
            print(r.stdout.strip()[:400])
        return r.returncode

    hits = res.get("tech_detail_hits", 0)
    print("novice-zero: судится ТОЛЬКО класс нулевой терпимости (ось 4), "
          "пороговые оси на этом прогоне сняты флагом --skip-novice")
    if not hits:
        print("novice-zero: тех-деталей для продвинутых 0, класс чист")
        return 0
    print(f"novice-zero: тех-детали для продвинутых {hits} вхождений - "
          "класс нулевой терпимости, порога у него нет")
    for t in res.get("tech_detail", []):
        print(f"  убрать [{t.get('term')}] x{t.get('n')} → {t.get('fix')}")
        if t.get("example"):
            print(f"     пример: {t['example'][:160]}")
    print("novice-zero: замены берутся из novice-standard.md §2.1; "
          "не получается заменить, не потеряв факт - страница не публикуется")
    return 1


if __name__ == "__main__":
    sys.exit(main())
