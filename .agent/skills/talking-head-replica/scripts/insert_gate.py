#!/usr/bin/env python3
"""HARD-гейт вставки: покадровый скан КАЖДОГО кадра на присутствие автора.
Стратегия автора (по решению автора): не правило-заметка, а машинный бенчмарк по миллисекундам,
без PASS этого гейта композит не собирается.

Проверки на каждом кадре (30fps, без пропусков):
1. Лицо: OpenCV YuNet (models/yunet.onnx). Любое лицо в любом кадре = FAIL.
2. Skin-ratio: доля скин-тон пикселей > порога = FAIL (ловит руки/волосы/кожу без лица).
3. Торцы (первые/последние 12 кадров): строгий режим - skin-порог вдвое ниже
   (транзишн-флеши автора живут на торцах).

4. --expect-static-margins (для окно-вставок window_insert.py): поля кадра = НАШ статичный
   фон, любое движение в полях = вокруг окна протекло живое видео автора = FAIL.

Usage: insert_gate.py <insert.mp4> [--skin-max 0.06] [--edge-frames 12] [--expect-static-margins]
Exit 0 = PASS, exit 1 = FAIL со списком кадров.
Брендовые оранж/беж фоны автора дают ложный skin (YCrCb): после визуальной верификации
кадров глазами допускается явный override --skin-max с пометкой в отчёте.
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
import cv2

MODEL = os.path.expanduser("~/.claude/skills/talking-head-replica/models/yunet.onnx")
FF = "ffmpeg"

def skin_ratio(bgr):
    # классический YCrCb-детектор кожи; работает по даунскейлу для скорости
    small = cv2.resize(bgr, (270, 480))
    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (30, 133, 77), (255, 173, 127))
    return float(np.count_nonzero(mask)) / mask.size

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("insert")
    ap.add_argument("--skin-max", type=float, default=0.06)
    ap.add_argument("--edge-frames", type=int, default=12)
    ap.add_argument("--expect-static-margins", action="store_true")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="gate_")
    r = subprocess.run([FF, "-v", "error", "-y", "-i", a.insert, "-f", "image2", f"{tmp}/%05d.png"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("FAIL декод: " + r.stderr[-300:])
    frames = sorted(os.listdir(tmp))
    n = len(frames)
    det = cv2.FaceDetectorYN.create(MODEL, "", (0, 0), score_threshold=0.72)
    bad = []
    prev_margins = None
    for i, fr in enumerate(frames):
        img = cv2.imread(os.path.join(tmp, fr))
        h, w = img.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(img)
        edge = i < a.edge_frames or i >= n - a.edge_frames
        sr = skin_ratio(img)
        limit = a.skin_max / 2 if edge else a.skin_max
        why = []
        if faces is not None and len(faces) > 0:
            why.append(f"ЛИЦО x{len(faces)}")
        if sr > limit:
            why.append(f"skin {sr:.3f}>{limit:.3f}{' (торец)' if edge else ''}")
        if a.expect_static_margins:
            g = cv2.cvtColor(cv2.resize(img, (270, 480)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            margins = np.concatenate([g[:60].ravel(), g[-60:].ravel(), g[:, :30].ravel(), g[:, -30:].ravel()])
            if prev_margins is not None:
                md = float(np.mean(np.abs(margins - prev_margins)))
                if md > 2.5:
                    why.append(f"живые поля {md:.1f} (видео автора вокруг окна?)")
            prev_margins = margins
        if why:
            bad.append((i, round(i / 30.0, 2), "; ".join(why)))
    for f in frames:
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    if bad:
        print(f"FAIL {os.path.basename(a.insert)}: {len(bad)}/{n} кадров с автором")
        for i, t, why in bad[:12]:
            print(f"  кадр {i} (t={t}с): {why}")
        sys.exit(1)
    print(f"PASS {os.path.basename(a.insert)}: {n} кадров, автора нет")

if __name__ == "__main__":
    main()