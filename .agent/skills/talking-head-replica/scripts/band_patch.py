#!/usr/bin/env python3
"""Глушение вшитого караоке автора БЕЗ видимой полосы: грязные кадры латаются
полосой из ближайшего ЧИСТОГО кадра той же сцены (фон восстанавливается как был).
Цветной drawbox запрещён на светлом/текстурном фоне - даёт видимую полосу . Метод проверен на top5 (итерация 2).

Детектор глифа: нейтрально-светлый пиксель с тёмным соседом (обводка караоке).
Грязные прогоны расширяются на +-2 кадра (фейды), якорь = кадр в прогоне >=2 чистых.

Usage: band_patch.py <src.mp4> <out.mp4> [--band 1480:1600] [--detect 1500:1590]
       [--x 250:830] [--thr 3]
"""
import argparse, glob, os, shutil, subprocess, sys
from PIL import Image

FF = "ffmpeg"

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--band", default="1480:1600")
ap.add_argument("--detect", default="1500:1590")
ap.add_argument("--x", default="250:830")
ap.add_argument("--thr", type=int, default=3)
a = ap.parse_args()
Y0, Y1 = (int(v) for v in a.band.split(":"))
D0, D1 = (int(v) for v in a.detect.split(":"))
X0, X1 = (int(v) for v in a.x.split(":"))

def dirty_count(im):
    px = im.load(); cnt = 0
    for y in range(D0, D1, 2):
        for x in range(X0, X1, 3):
            r, g, b = px[x, y]
            if r > 205 and g > 205 and b > 205 and max(r, g, b) - min(r, g, b) < 45:
                for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-3, -3), (3, 3)):
                    r2, g2, b2 = px[x + dx, y + dy]
                    if r2 < 95 and g2 < 95 and b2 < 95:
                        cnt += 1; break
    return cnt

fd = a.out + ".frames"
shutil.rmtree(fd, ignore_errors=True); os.makedirs(fd)
r = subprocess.run([FF, "-v", "error", "-y", "-i", a.src, "-f", "image2", f"{fd}/%05d.png"],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("DECODE FAIL: " + r.stderr[-300:])
frames = sorted(glob.glob(f"{fd}/*.png"))
ims = [Image.open(f).convert("RGB") for f in frames]
n = len(ims)
flags = [dirty_count(im) >= a.thr for im in ims]
dil = list(flags)
for i, f in enumerate(flags):
    if f:
        for j in range(max(0, i - 2), min(n, i + 3)):
            dil[j] = True
anchors = [i for i in range(n) if not dil[i] and ((i > 0 and not dil[i - 1]) or (i < n - 1 and not dil[i + 1]))]
if not anchors:
    anchors = [i for i in range(n) if not dil[i]]
if not anchors:
    sys.exit("FAIL: нет чистых кадров-якорей, латать нечем")
fixed = 0
for i in range(n):
    if not dil[i]:
        continue
    src_i = min(anchors, key=lambda j: (abs(j - i), j > i))
    ims[i].paste(ims[src_i].crop((0, Y0, 1080, Y1)), (0, Y0)); fixed += 1
for f, im in zip(frames, ims):
    im.save(f)
r = subprocess.run([FF, "-v", "error", "-y", "-framerate", "30", "-i", f"{fd}/%05d.png",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-r", "30", a.out], capture_output=True, text=True)
shutil.rmtree(fd)
if r.returncode != 0:
    sys.exit("ENCODE FAIL: " + r.stderr[-300:])
print(f"OK band_patch {os.path.basename(a.out)}: {n} кадров, залатано {fixed}, якорей {len(anchors)}")