#!/usr/bin/env python3
"""Вставка «UI-окно на нашем фоне»: когда у автора UI-окно ПЛАВАЕТ поверх его видео
(волосы/комната/руки в кадре), берём кропом ТОЛЬКО содержимое окна (внутри его рамки)
и ставим на наш задизайненный фон с нашей рамкой. Ни пикселя автора.

Usage: window_insert.py <src.mp4> <t0> <t1> <crop W:H:X:Y> <out.mp4>
       [--out-w 980] [--bg 0x16161a] [--border 0xE07850] [--border-w 6] [--center-y 900]
Кроп задаётся ВНУТРИ рамки окна автора (замерить по стабильным кадрам, анимацию
входа окна не брать - только стабильный отрезок).
"""
import argparse, subprocess, sys

FF, FP = "ffmpeg", "ffprobe"

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("t0", type=float); ap.add_argument("t1", type=float)
ap.add_argument("crop"); ap.add_argument("out")
ap.add_argument("--out-w", type=int, default=980)
ap.add_argument("--bg", default="0x16161a")
ap.add_argument("--border", default="0xE07850")
ap.add_argument("--border-w", type=int, default=6)
ap.add_argument("--center-y", type=int, default=900)
a = ap.parse_args()

w, h, x, y = (int(v) for v in a.crop.split(":"))
out_h = int(round(a.out_w * h / w / 2) * 2)
ox = (1080 - a.out_w) // 2
oy = a.center_y - out_h // 2
bw = a.border_w
vf = (f"[0:v]crop={w}:{h}:{x}:{y},scale={a.out_w}:{out_h}:flags=lanczos,setsar=1[win];"
      f"color=c={a.bg}:s=1080x1920:r=30[bgc];"
      f"[bgc][win]overlay={ox}:{oy}:shortest=1,"
      f"drawbox=x={ox-bw}:y={oy-bw}:w={a.out_w+2*bw}:h={out_h+2*bw}:color={a.border}:t={bw},fps=30[v]")
r = subprocess.run([FF, "-v", "error", "-y", "-ss", f"{a.t0:.3f}", "-to", f"{a.t1:.3f}", "-i", a.src,
                    "-filter_complex", vf, "-map", "[v]", "-an",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", a.out],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("FFMPEG FAIL:\n" + r.stderr[-600:])
d = float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nk=1:nw=1", a.out], capture_output=True, text=True).stdout.strip())
if abs(d - (a.t1 - a.t0)) > 0.25:
    sys.exit(f"FAIL длительность {d:.2f} vs {a.t1-a.t0:.2f}")
print(f"OK окно-вставка {a.out}: {d:.2f}с, окно {a.out_w}x{out_h} на фоне {a.bg}")