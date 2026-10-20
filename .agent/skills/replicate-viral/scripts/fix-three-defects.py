#!/usr/bin/env python3
"""fix-three-defects.py — три дефекта приёмки автора (по решению автора), чинятся за один проход.

1. ДУБЛЬ ПОДЛОЖКИ. Над карточкой двойника торчит вторая обрезанная макушка — хвост того же
   twin-кадра, оставшийся под панелью. Автор: «там два раза продублирован на фоне подложки
   из меня». Замер: настоящая грань карточки y=615, хвост сидит на y=483..615.
   Лечение: полоса хвоста заливается фоном сцены (медианный цвет полосы НАД панелью).

2. МЕЛЬКАНИЕ. Двойник появляется/исчезает на 1-4 кадра подряд — читается как лаг.
   Автор: «я появляюсь, пропадаю, появляюсь, пропадаю, хотя вставка одна и та же».
   Замер: 12 микро-переключений на 5 роликах. Лечение: прогон короче MIN_RUN кадров
   поглощается соседним состоянием (кадры берутся из более длинного соседа).

3. ТОНКИЙ ШРИФТ СУБТИТРОВ. У донора субтитр жирнее и читается проще.
   Лечение: утолщение штриха морфологической дилатацией тёмной обводки + повышение
   контраста текстовых пикселей в зоне субтитра.

usage: fix-three-defects.py <in.mp4> <out.mp4> [--card-y 615] [--tail-y 483] [--min-run 5]
"""
import argparse, os, subprocess, sys
import numpy as np
import cv2


def face_seq(frames, det, W, H):
    seq = []
    for fr in frames:
        det.setInputSize((W, H))
        _, f = det.detect(fr)
        seq.append(1 if (f is not None and len(f) > 0 and max(float(x[14]) for x in f) >= 0.6) else 0)
    return seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--card-y", type=int, default=615, help="верхняя грань настоящей карточки")
    ap.add_argument("--tail-y", type=int, default=483, help="где начинается хвост-дубль")
    ap.add_argument("--min-run", type=int, default=5, help="прогоны короче — поглощаются")
    ap.add_argument("--no-dup", action="store_true", help="не чинить дубль подложки")
    ap.add_argument("--no-font", action="store_true", help="не трогать шрифт")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    n = len(frames)
    print(f"· {os.path.basename(a.src)}: {n} кадров {W}x{H} @{fps:.0f}fps")

    # ---- дефект 1: хвост подложки над карточкой ----
    fixed_dup = 0
    if not a.no_dup:
        y0, y1 = a.tail_y, a.card_y
        for i, fr in enumerate(frames):
            strip = fr[y0:y1, :]
            if not strip.size:
                continue
            # 🔴 ТОЛЬКО split-кадры. На full-head (двойник во весь экран) в полосе 483..615
            # законно находится лоб — трогать нельзя, иначе layout-parity падает
            # (замер: расхождения шли по классу full-head, 14.7-19.8с ролика 1).
            # Признак split: НИЖЕ полосы идёт тёмная студия карточки, а ВЫШЕ — светлая панель.
            above = fr[max(0, y0 - 60):y0, :]
            below = fr[y1 + 10:min(fr.shape[0], y1 + 70), :]
            if not above.size or not below.size:
                continue
            va = cv2.cvtColor(above, cv2.COLOR_BGR2GRAY).mean()
            vb = cv2.cvtColor(below, cv2.COLOR_BGR2GRAY).mean()
            if not (va - vb > 25):
                continue
            # хвост = в полосе есть кожа/волосы (насыщенный тёплый) на фоне светлой сцены
            hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
            skin = ((hsv[:, :, 0] < 30) & (hsv[:, :, 1] > 45) & (hsv[:, :, 2] > 55)).mean()
            if skin > 0.02:
                # берём фон ИЗ ПОЛОСЫ НАД хвостом (там чистая сцена панели)
                # 🔴 НЕ плоский цвет: продолжаем панель её же пикселями (растяжка 2 строк
                # над хвостом). Плоская заливка роняла layout-parity со 100% до 93.7% —
                # классификатор терял края панели. Растяжка сохраняет и края, и структуру.
                ref = fr[max(0, y0 - 3):max(1, y0 - 1), :]
                if ref.size:
                    patch = cv2.resize(ref, (fr.shape[1], y1 - y0), interpolation=cv2.INTER_LINEAR)
                    fr[y0:y1, :] = patch
                    fixed_dup += 1
        print(f"· дубль подложки: залито на {fixed_dup} кадрах (полоса y={y0}..{y1})")

    # ---- дефект 2: мелькание ----
    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "yunet.onnx")
    if not os.path.isfile(yunet):
        yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    det = cv2.FaceDetectorYN.create(yunet, "", (320, 320))
    seq = face_seq(frames, det, W, H)

    runs = []
    cur, start = seq[0], 0
    for i, v in enumerate(seq[1:], 1):
        if v != cur:
            runs.append([cur, start, i - start])
            cur, start = v, i
    runs.append([cur, start, n - start])

    fixed_flicker = 0
    for k, (v, s, l) in enumerate(runs):
        if l >= a.min_run:
            continue
        # поглощаем коротышку более длинным соседом
        prev_len = runs[k - 1][2] if k > 0 else 0
        next_len = runs[k + 1][2] if k + 1 < len(runs) else 0
        if prev_len == 0 and next_len == 0:
            continue
        if prev_len >= next_len and k > 0:
            donor_idx = runs[k - 1][1] + runs[k - 1][2] - 1
        else:
            donor_idx = runs[k + 1][1]
        donor_idx = max(0, min(donor_idx, n - 1))
        for j in range(s, s + l):
            frames[j] = frames[donor_idx].copy()
        fixed_flicker += l
    print(f"· мелькание: сглажено {fixed_flicker} кадров в {sum(1 for v,s,l in runs if l < a.min_run)} микро-прогонах")

    # ---- дефект 3: тонкий шрифт субтитров ----
    # утолщаем ТЁМНУЮ обводку белого текста → штрих визуально жирнее
    # 🔴 ВАЖНО: утолщать ТОЛЬКО пиксели субтитра. Первый заход брал всё светлое ниже 0.45H
    # и залепил белым кардиган и микрофон. Субтитр отличается от одежды тем, что у него
    # ТЁМНАЯ ОБВОДКА вплотную к белому — ищем именно такие пиксели.
    ker = np.ones((3, 3), np.uint8)
    fixed_font = 0
    if a.no_font:
        frames_iter = []
    else:
        frames_iter = frames
    if not a.no_font:
     for i, fr in enumerate(frames):
        zone = fr[int(H * 0.45):, :]
        if not zone.size:
            continue
        g = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
        bright = (g > 232).astype(np.uint8)
        if bright.mean() < 0.002:
            continue
        dark = (g < 70).astype(np.uint8)
        # обводка рядом: тёмное в окрестности 7px от светлого
        near_dark = cv2.dilate(dark, np.ones((7, 7), np.uint8), iterations=1)
        text = cv2.bitwise_and(bright, near_dark)
        if text.mean() < 0.0008:
            continue
        # оставляем только компоненты размером с букву (не крупные пятна одежды)
        num, lab, stats, _ = cv2.connectedComponentsWithStats(text, 8)
        keep = np.zeros_like(text)
        for c in range(1, num):
            area = stats[c, cv2.CC_STAT_AREA]
            hgt = stats[c, cv2.CC_STAT_HEIGHT]
            if 25 <= area <= 9000 and 12 <= hgt <= 130:
                keep[lab == c] = 1
        if keep.sum() == 0:
            continue
        thick = cv2.dilate(keep, ker, iterations=1)
        m = (thick > 0)[:, :, None].astype(np.float32)
        white = np.full_like(zone, 255)
        fr[int(H * 0.45):, :] = (zone * (1 - m * 0.75) + white * (m * 0.75)).astype(np.uint8)
        fixed_font += 1
    print(f"· шрифт: штрих утолщён на {fixed_font} кадрах")

    raw = a.out + ".raw.mp4"
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    for fr in frames:
        vw.write(fr)
    vw.release()

    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-i", a.src,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-crf", "0", "-qp", "0",
                    "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-shortest", a.out], check=True)
    os.remove(raw)
    print(f"✅ {a.out}")


if __name__ == "__main__":
    main()
