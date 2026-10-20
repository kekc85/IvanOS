#!/usr/bin/env python3
"""layout-parity-bench.py — ПОСЕКУНДНЫЙ БЕНЧМАРК РАСКЛАДКИ донор vs наш ролик.

КОРЕНЬ (автор, «на первых секундах у автора сплитскрин, у нас просто лица,
это грубое нарушение скилла… ты должен каждую миллисекунду отсматривать и делать бенчмарк»):
presence-parity-gate мерил ТОЛЬКО долю кадров с лицом. Ролики её держали (69-78%), но
РАСКЛАДКА разъезжалась: там где у донора split (сверху карточка, снизу спикер) — у нас
full-head во весь экран. Ни один гейт этого не ловил.

ЧТО МЕРИТ: на каждой временной точке (шаг 0.2с по нормированному времени) классифицирует
кадр донора и наш кадр в один из layout-классов и сравнивает их:
  split    — есть и контент-зона сверху, и лицо снизу
  full-head— лицо крупно, контента сверху нет
  full-ui  — контент во весь кадр, лица нет
Совпадение по классу = PASS для этой точки. Итог: доля совпавших точек + карта расхождений.

usage: layout-parity-bench.py --donor <orig.mp4> --ours <final.mp4> [--min-match 85] [--json out.json]
exit 0 = раскладка сходится; 1 = разъехалась (не выдавать); 2 = ошибка входа.
"""
import sys, os, json, argparse


def classify(frame, det):
    """Класс раскладки одного кадра: split / full-head / full-ui."""
    import cv2
    import numpy as np
    h, w = frame.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(frame)
    face = None
    if faces is not None and len(faces) > 0:
        f = max(faces, key=lambda x: x[2] * x[3])
        if float(f[14]) >= 0.6:
            face = f

    if face is None:
        return "full-ui", None

    fy = float(face[1])
    fh = float(face[3])
    face_cy = fy + fh / 2.0
    face_frac = fh / h                      # насколько лицо крупное

    # Зона НАД лицом: если там лежит контент (яркая/структурная плашка,
    # отличная от фона студии), это split. Меряем по верхней полосе до макушки.
    top_h = max(1, int(fy) - 10)
    if top_h < h * 0.12:
        return "full-head", face_frac       # лица почти от края — контенту негде быть

    top = frame[0:top_h, :]
    g = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)
    # контент-панель = много краёв ИЛИ заметно светлее нижней части кадра
    edges = cv2.Canny(g, 60, 160)
    edge_density = float((edges > 0).mean())
    bottom = frame[int(h * 0.6):, :]
    bright_gap = float(g.mean()) - float(cv2.cvtColor(bottom, cv2.COLOR_BGR2GRAY).mean())

    has_panel = edge_density > 0.012 or bright_gap > 28
    if has_panel and face_cy > h * 0.42:
        return "split", face_frac
    return "full-head", face_frac


def scan(path, det, points):
    """Классы раскладки в заданных долях длительности (0..1)."""
    import cv2
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    dur = total / fps if fps else 0
    out = []
    for p in points:
        cap.set(cv2.CAP_PROP_POS_MSEC, p * dur * 1000.0)
        ok, fr = cap.read()
        if not ok:
            out.append(("n/a", None))
            continue
        out.append(classify(fr, det))
    cap.release()
    return out, dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", required=True)
    ap.add_argument("--ours", required=True)
    ap.add_argument("--step", type=float, default=0.2, help="шаг по времени, сек")
    # 🔴 автор дословно: «здесь должно быть на 99,99% сходства, расхождение быть
    # не должно вообще». Порог НЕ понижать — любое расхождение раскладки = брак.
    ap.add_argument("--min-match", type=float, default=99.99, help="мин. доля совпавших точек, %%")
    ap.add_argument("--json")
    a = ap.parse_args()

    for p in (a.donor, a.ours):
        if not os.path.isfile(p):
            print(f"FAIL: нет файла {p}")
            sys.exit(2)

    import cv2
    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "yunet.onnx")
    if not os.path.isfile(yunet):
        yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    det = cv2.FaceDetectorYN.create(yunet, "", (320, 320))

    # общая сетка по НОРМИРОВАННОМУ времени: ролики разной длины, сравниваем по доле сюжета
    cap = cv2.VideoCapture(a.donor)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    dur_d = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    cap.release()
    n = max(10, int(dur_d / a.step))
    points = [(i + 0.5) / n for i in range(n)]

    dl, dur_d = scan(a.donor, det, points)
    ol, dur_o = scan(a.ours, det, points)

    match = 0
    diffs = []
    for i, p in enumerate(points):
        dc, _ = dl[i]
        oc, _ = ol[i]
        if dc == oc:
            match += 1
        else:
            diffs.append({"t_donor": round(p * dur_d, 2), "t_ours": round(p * dur_o, 2),
                          "donor": dc, "ours": oc})
    pct = 100.0 * match / len(points)

    print(f"· донор {dur_d:.1f}с, наш {dur_o:.1f}с, точек сравнения {len(points)} (шаг {a.step}с)")
    print(f"· раскладка совпала в {match}/{len(points)} точек = {pct:.1f}%")

    if diffs:
        print(f"· расхождений {len(diffs)}, первые 15:")
        for d in diffs[:15]:
            print(f"    {d['t_ours']:5.1f}с: у донора {d['donor']:9s} → у нас {d['ours']}")

    if a.json:
        json.dump({"match_pct": pct, "diffs": diffs,
                   "donor_dur": dur_d, "ours_dur": dur_o},
                  open(a.json, "w"), ensure_ascii=False, indent=2)

    if pct < a.min_match:
        print(f"✗ FAIL: раскладка разъехалась ({pct:.1f}% при пороге {a.min_match}%).")
        print("  ЗАКОН 1: где у донора split — у нас split, где full-head — full-head.")
        print("  🔴 Чинить скелетом побитно по карте расхождений выше, не грейдом.")
        sys.exit(1)

    print(f"✅ PASS: раскладка держит донора ({pct:.1f}%)")
    sys.exit(0)


if __name__ == "__main__":
    main()
