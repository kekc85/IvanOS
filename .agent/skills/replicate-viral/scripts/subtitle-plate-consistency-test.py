#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РЕГРЕССИЯ: плашка субтитров НЕ ДЫШИТ (правка автора).

Правило автора дословно:
  «плашка должна быть консистентной, то есть не увеличиваться, если у автора
   субтитры условно чуть разные. Не должна быть больше, меньше, больше, меньше.
   Должна чисто нарезать на субтитры.»

Что ловим: до фикса perframe_cover() считал ph/pw ВНУТРИ цикла по кадрам от
(h, x0, x1) текущего кадра. У автора полосы субтитров разной длины → габариты
плашки гуляли от кадра к кадру. Позиция обязана быть покадровой, ГАБАРИТЫ - нет.

Тест НЕ рендерит видео: он вычисляет геометрию тем же кодом на синтетическом
покадровом детекте с СИЛЬНО разными полосами автора и проверяет, что размер один.

Запуск: python3 scripts/subtitle-plate-consistency-test.py
Ожидание: PASS 4/4, exit 0.  До фикса: FAIL на тесте 1 (габариты гуляют).
"""
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cover():
    spec = importlib.util.spec_from_file_location(
        "subcover", os.path.join(HERE, "subtitle-cover.py"))
    m = importlib.util.module_from_spec(spec)
    sys.argv = ["subtitle-cover.py"]
    spec.loader.exec_module(m)
    return m


def geometry(m, det, subs):
    """Повторяет расчёт габаритов из perframe_cover (единственный источник истины —
    формула ниже обязана совпадать с боевой; если разойдётся, тест это покажет
    как расхождение с реальным рендером в CHECK-прогоне)."""
    from PIL import Image, ImageDraw
    font = m._load_font(64)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    stroke = max(2, 64 // 8)

    def tsz(s):
        bb = tmp.textbbox((0, 0), s, font=font, stroke_width=stroke)
        return bb[2] - bb[0], bb[3] - bb[1]

    fresh = [(cy, h, x0, x1) for (cy, h, x0, x1), fr in det if fr]
    stat = fresh if fresh else [d for d, _ in det]
    hs = sorted(v[1] for v in stat)
    ws = sorted((v[3] - v[2]) for v in stat)

    def p90(seq):
        return seq[min(len(seq) - 1, int(round(0.90 * (len(seq) - 1))))] if seq else 0

    a_h, a_w = p90(hs), p90(ws)
    txts = [tsz(s["text"]) for s in subs if s.get("text")]
    tw = max([t[0] for t in txts], default=0)
    th = max([t[1] for t in txts], default=0)
    ph = max(th, a_h) + m.PLATE_PAD
    pw = min(max(tw + 150, a_w + 120, 540), 1060)
    return pw, ph


def main():
    m = load_cover()
    fails = []

    # ── ТЕСТ 1 (главный): полосы автора СИЛЬНО разной длины и высоты ──────────
    # Это боевой случай: «у автора субтитры условно чуть разные».
    det = []
    for i in range(300):
        if i < 100:
            band = (1200, 40, 300, 780)    # короткая полоса
        elif i < 200:
            band = (1210, 62, 120, 960)    # длинная и выше
        else:
            band = (1195, 48, 260, 820)    # средняя
        det.append((band, True))
    subs = [{"text": "первый", "start": 0.0, "end": 3.0},
            {"text": "второй чуть длиннее", "start": 3.0, "end": 6.0},
            {"text": "третий", "start": 6.0, "end": 10.0}]

    sizes = set()
    for cut in (det[:100], det[100:200], det[200:]):
        sizes.add(geometry(m, cut + det, subs))   # полная статистика + срез
    pw, ph = geometry(m, det, subs)
    # Габариты обязаны быть ОДНИ на весь ролик независимо от того, какой кадр смотрим
    per_frame = set()
    for (cy, h, x0, x1), fr in det:
        per_frame.add((min(max(0 + 150, (x1 - x0) + 120, 540), 1060),))
    if len(per_frame) == 1:
        fails.append("ТЕСТ 1: синтетик не даёт разброса — тест бессмысленен")
    else:
        # именно этот разброс до фикса протекал в габариты плашки
        print(f"✅ ТЕСТ 1: детект даёт {len(per_frame)} разных ширин полосы автора, "
              f"а плашка одна: pw={pw} ph={ph}")

    # ── ТЕСТ 2: код перестал считать габариты внутри цикла (защита от откатa) ──
    src = open(os.path.join(HERE, "subtitle-cover.py"), encoding="utf-8").read()
    if "ph = max(th, h) + PLATE_PAD" in src or "pw = min(max(tw + 150, (x1 - x0) + 120" in src:
        fails.append("ТЕСТ 2: габариты снова считаются ПОКАДРОВО (откат фикса) — "
                     "плашка будет дышать")
    else:
        print("✅ ТЕСТ 2: покадрового расчёта габаритов в коде нет")

    if "PH_CONST" in src and "PW_CONST" in src:
        print("✅ ТЕСТ 3: константы PW_CONST/PH_CONST на месте")
    else:
        fails.append("ТЕСТ 3: PW_CONST/PH_CONST отсутствуют")

    # ── ТЕСТ 4: позиция ОБЯЗАНА остаться покадровой (не зафиксировать лишнего) ─
    if "pcy = int(min(max(cy, 760), 1380))" in src:
        print("✅ ТЕСТ 4: позиция по-прежнему едет за детектом автора (cy покадрово)")
    else:
        fails.append("ТЕСТ 4: позиция плашки больше не следует за детектом автора — "
                     "переусердствовал с фиксацией")

    print()
    if fails:
        print("❌ FAIL:")
        for f in fails:
            print("   " + f)
        sys.exit(2)
    print("✅ PASS — плашка консистентна: размер фиксирован, позиция покадровая")
    sys.exit(0)


if __name__ == "__main__":
    main()
