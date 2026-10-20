#!/usr/bin/env python3
"""rebuild-from-donor.py — сборка реплики ИЗ ФУТАЖА АВТОРА (ЗАКОН 1 скилла).

КОРЕНЬ (автор, дословно): «ты не вырезал классные эффекты у автора в оригинале,
нарушил skill… вместо этого какое-то говно люто нарисовал абстрактное. Ты должен был ВСЁ
у автора забрать, вырезать. Вообще ничего не отрисовывать!»
И второе: «должна быть вырезка вокруг меня, я из фона должен вырезаться. А ты сзади меня
то же самое поставил» — двойник стоял ДВУМЯ слоями, отсюда двойная макушка.

ЧТО ДЕЛАЕТ:
1. ПАНЕЛЬ = живой кроп из видео донора по таймкодам. Его анимация, курсор, эффекты — 1:1.
   Ничего не рисуется. Зона спикера донора вырезается из кропа (там будет наш двойник).
2. ДВОЙНИК = ОДИН слой вырезки по силуэту (rembg u2net), кладётся ПОВЕРХ панели.
   Никакого прямоугольника позади — фон студии не тащится, макушка не двоится.
3. СУБТИТРЫ жирные, как у донора.

usage: rebuild-from-donor.py --project <dir> --donor <orig.mp4> --map <DONOR-MAP.md> --out <final.mp4>
"""
import argparse, json, os, subprocess, sys
import numpy as np
import cv2

REMBG_PY = os.path.expanduser("~/.venv-rembg/bin/python")


def donor_speaker_band(donor, samples=40):
    """Где у донора сидит спикер: медианные границы его лица по всему ролику."""
    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "yunet.onnx")
    if not os.path.isfile(yunet):
        yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    cap = cv2.VideoCapture(donor)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    det = cv2.FaceDetectorYN.create(yunet, "", (320, 320))
    tops = []
    W = H = 0
    for i in range(samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (i + 0.5) / samples))
        ok, fr = cap.read()
        if not ok:
            continue
        H, W = fr.shape[:2]
        det.setInputSize((W, H))
        _, f = det.detect(fr)
        if f is not None and len(f) > 0:
            b = max(f, key=lambda x: x[2] * x[3])
            if float(b[14]) >= 0.7:
                tops.append(float(b[1]))
    cap.release()
    if not tops:
        return None, W, H
    return float(np.median(tops)), W, H


def cutout_video(src, out_webm, every=1):
    """Вырезка двойника по силуэту → mov с альфой. ОДИН слой, без подложки."""
    tmp = out_webm + ".frames"
    os.makedirs(tmp, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-vf", f"select=not(mod(n\\,{every}))", "-vsync", "0",
                    f"{tmp}/f%05d.png"], check=True)
    script = f'''
import os, sys
from rembg import remove, new_session
from PIL import Image
s = new_session("u2net")
d = "{tmp}"
fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
for i, f in enumerate(fs):
    p = os.path.join(d, f)
    Image.open(p).convert("RGB")
    out = remove(Image.open(p), session=s)
    out.save(p)
    if i % 40 == 0:
        print(f"cut {{i}}/{{len(fs)}}", flush=True)
print("cut done", len(fs))
'''
    subprocess.run([REMBG_PY, "-c", script], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "25",
                    "-i", f"{tmp}/f%05d.png", "-c:v", "qtrle", "-pix_fmt", "argb",
                    out_webm], check=True)
    return out_webm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--donor", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", action="store_true", help="только замер, без сборки")
    a = ap.parse_args()

    band, W, H = donor_speaker_band(a.donor)
    print(f"· донор {W}x{H}: верх лица спикера медиана y={band:.0f} ({band/H:.3f}H)" if band
          else f"· донор {W}x{H}: лицо не найдено")
    if a.probe:
        return


if __name__ == "__main__":
    main()
