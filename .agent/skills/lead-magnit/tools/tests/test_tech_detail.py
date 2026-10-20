#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фикстуры оси 4 novice-check: класс нулевой терпимости «тех-деталь».

Зачем отдельный прогон. Ось 4 введена по решению автора после того, как боевой гейт
напечатал PASS на живой странице, где шесть кодов ответа растворились в 3206
словах. Значит проверять надо не «есть ли слово в словаре», а поведение гейта
на ДВУХ половинах: там, где тех-деталь есть, обязан быть FAIL, и там, где
похожие цифры и слова живут своей нетехнической жизнью («404 рубля»,
«200 символов», «узел большой сети»), обязан остаться PASS. Без второй половины
класс закрывается опусканием порога, а корпус краснеет по собственному шуму.

Запуск:  python3 tools/tests/test_tech_detail.py
Код выхода: 0 - все фикстуры отработали как объявлено, 1 - хоть одна разошлась.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(os.path.dirname(HERE), "novice-check.py")
FIX = os.path.join(HERE, "tech-detail")

# (файл, ожидаемый код возврата, что именно проверяем)
CASES = [
    ("pos-1-kod-200.md", 1, "«отдался кодом 200» - код ответа в прозе"),
    ("pos-2-uzly.md", 1, "«три узла проверки» - узлы замера"),
    ("pos-3-rc.md", 1, "«rc=1» - код возврата"),
    ("pos-4-endpoint.md", 1, "«эндпоинт» и «юзер-агент»"),
    ("pos-5-podpis-kadra.md", 1, "подпись кадра «значения это код первого ответа» без цифры рядом"),
    ("pos-6-hesh-fayla.md", 1, "«хеш файла», «sha256», «хэши» - настоящая тех-деталь"),
    ("neg-1-404-rubley.md", 0, "«404 рубля» - цена, не код ответа"),
    ("neg-2-200-simvolov.md", 0, "«200 символов» - длина, не код ответа"),
    ("neg-3-uzel-svyazi.md", 0, "«узел большой сети» - тема статьи, не замер"),
    ("neg-4-heshtegi.md", 0, "«хештеги / хэштеги / хеш-тег» - слово из соцсетей, не тех-деталь (R-13)"),
]


def run(path):
    p = subprocess.run([sys.executable, GATE, path], capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    bad = 0
    for name, want, what in CASES:
        rc, out = run(os.path.join(FIX, name))
        ok = rc == want
        bad += 0 if ok else 1
        mark = "OK  " if ok else "FAIL"
        axis = [l.strip() for l in out.splitlines() if "тех-деталь" in l]
        print("  %s %-26s rc=%d (ждали %d) · %s" % (mark, name, rc, want, what))
        for a in axis[:2]:
            print("         %s" % a)
    print("фикстуры оси 4: %d/%d прошло" % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
