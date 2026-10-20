#!/usr/bin/env python3
"""
presence-parity-gate.py — ГЕЙТ ПРИСУТСТВИЯ СПИКЕРА (автор, прецедент reels-review 1-3).

КОРЕНЬ: скелет закладывал `avatar_on_screen: false` на длинных сегментах (в reel-DbD81H1v6kC
три из пяти). На выходе двойник был в кадре 17-23% времени, у донора — 40-50%. Автор увидел
глазами: «по динамике отличается от оригинала, ерунда». Ни один гейт этого не ловил —
проверялись центрирование, чужие лица, layout, но НЕ ДОЛЯ ПРИСУТСТВИЯ.

ПРАВИЛО: доля кадров со спикером в нашем выходе обязана быть не ниже донорской минус допуск.
Мёртвые статичные карточки вместо живого лица = брак, даже если каждый кадр по отдельности чистый.

usage: presence-parity-gate.py --donor <orig.mp4> --ours <final.mp4> [--tol 5.0] [--json out.json]
exit 0 = паритет держится; 1 = провал присутствия (не выдавать); 2 = ошибка входа.
"""
import sys, os, json, argparse

def face_ratio(path, min_conf=0.6, per_sec=3):
    """Доля сэмплов, где найдено лицо. Сэмплим равномерно, не разреженно по таймкодам."""
    import cv2
    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "yunet.onnx")
    if not os.path.isfile(yunet):
        yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None, 0, 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    det = cv2.FaceDetectorYN.create(yunet, "", (320, 320))
    step = max(1, int(round(fps / per_sec)))
    withface = tot = i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % step == 0:
            h, w = fr.shape[:2]
            det.setInputSize((w, h))
            _, faces = det.detect(fr)
            tot += 1
            if faces is not None and len(faces) > 0 and max(float(f[14]) for f in faces) >= min_conf:
                withface += 1
        i += 1
    cap.release()
    if tot == 0:
        return None, 0, 0
    return 100.0 * withface / tot, withface, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", required=True, help="оригинал донора")
    ap.add_argument("--ours", required=True, help="наш собранный ролик")
    ap.add_argument("--tol", type=float, default=5.0, help="на сколько пунктов можем просесть")
    ap.add_argument("--json", help="куда сложить замер")
    a = ap.parse_args()

    for p in (a.donor, a.ours):
        if not os.path.isfile(p):
            print(f"FAIL: нет файла {p}")
            sys.exit(2)

    d, dw, dt = face_ratio(a.donor)
    o, ow, ot = face_ratio(a.ours)
    if d is None or o is None:
        print("FAIL: не прочитать видео")
        sys.exit(2)

    floor = max(0.0, d - a.tol)
    ok = o >= floor
    print(f"· донор: спикер в {dw}/{dt} сэмплов = {d:.1f}%")
    print(f"· наш:   спикер в {ow}/{ot} сэмплов = {o:.1f}%")
    print(f"· порог: не ниже {floor:.1f}% (донор −{a.tol})")

    if a.json:
        json.dump({"donor_pct": d, "ours_pct": o, "floor_pct": floor, "pass": ok},
                  open(a.json, "w"), ensure_ascii=False, indent=2)

    if not ok:
        gap = floor - o
        print(f"✗ FAIL: спикера в кадре меньше донорского на {gap:.1f} пункта.")
        print("  Это и есть «отличается по динамике»: на месте живого лица стоят статичные карточки.")
        print("  🔴 Чинить СКЕЛЕТОМ, а не грейдом: сегменты с avatar_on_screen=false перевести")
        print("     в K3-overlap (двойник в кадре, вставка поверх окном) либо порезать длинную")
        print("     карточку на короткие врезки 1-2с между планами со спикером.")
        sys.exit(1)

    print(f"✅ PASS: присутствие спикера держит паритет с донором ({o:.1f}% при пороге {floor:.1f}%)")
    sys.exit(0)


if __name__ == "__main__":
    main()
