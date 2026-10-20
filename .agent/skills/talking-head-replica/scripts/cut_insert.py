#!/usr/bin/env python3
"""Демо-вставка автора 1:1 из оригинала: сегмент без искажений.

Правила (нарушение любого = брак, ловится глазами на контактном листе):
- никакого zoompan/дрейфа: вставка статична (дрейф = плавание и мыло от интерполяции)
- никакой crop-растяжки: допустим только кроп с аспектом ровно 9:16, дальше
  равномерный scale кадра целиком до 1080x1920 lanczos
- вшитый текст/караоке автора глушится ЗДЕСЬ, при нарезке: drawbox сплошного
  цвета фона по зоне текста (не delogo: он мажет след-гребёнку; не плашка на финале)
- если сегмент короче окна: forward-loop (reverse/boomerang ломает скролл демо)

Usage:
  cut_insert.py <orig.mp4> <t0> <t1> <out.mp4>
      [--crop W:H:X:Y]          кроп зоны демо в пикселях ИСХОДНИКА, аспект строго 9:16 (+-1.5%)
      [--box X,Y,W,H,color]     глушение зоны текста автора, координаты ВЫХОДА 1080x1920,
                                color вида 0x0a0a0a; можно несколько --box
      [--loop-to DUR]           повторить вперёд до длительности DUR секунд
"""
import subprocess, sys, math

FF, FP = "ffmpeg", "ffprobe"

def probe_dur(f):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", f], capture_output=True, text=True)
    return float(r.stdout.strip())

args = sys.argv[1:]
if len(args) < 4:
    sys.exit(__doc__)
orig, t0, t1, out = args[0], float(args[1]), float(args[2]), args[3]
crop = None; boxes = []; loop_to = None
i = 4
while i < len(args):
    if args[i] == "--crop":
        crop = args[i + 1]; i += 2
    elif args[i] == "--box":
        boxes.append(args[i + 1]); i += 2
    elif args[i] == "--loop-to":
        loop_to = float(args[i + 1]); i += 2
    else:
        sys.exit(f"неизвестный аргумент {args[i]}")

seg = t1 - t0
if seg <= 0:
    sys.exit("FAIL: t1 <= t0")

vf = []
if crop:
    w, h, x, y = (int(v) for v in crop.split(":"))
    if abs(w / h - 9 / 16) > 0.015 * (9 / 16):
        sys.exit(f"FAIL: кроп {w}x{h} не 9:16 - равномерный scale исказит пропорции. "
                 "Выбери окно демо с аспектом 9:16")
    vf.append(f"crop={w}:{h}:{x}:{y}")
vf.append("scale=1080:1920:flags=lanczos,setsar=1,fps=30")
for b in boxes:
    x, y, w, h, color = b.split(",")
    vf.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color={color}:t=fill")

def cut(dst, loop_reps=None):
    cmd = [FF, "-v", "error", "-y"]
    if loop_reps:
        cmd += ["-stream_loop", str(loop_reps)]
    cmd += ["-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", orig] if not loop_reps else ["-i", orig]
    cmd += ["-vf", ",".join(vf), "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]
    if loop_reps and loop_to:
        cmd += ["-t", f"{loop_to:.3f}"]
    cmd += [dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("FFMPEG FAIL:\n" + r.stderr[-800:])

if loop_to and loop_to > seg:
    # два шага: чистый сегмент, затем forward-loop до нужной длины
    tmp = out + ".seg.mp4"
    cut(tmp)
    reps = math.ceil(loop_to / seg) + 1
    r = subprocess.run([FF, "-v", "error", "-y", "-stream_loop", str(reps), "-i", tmp,
                        "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-r", "30", "-an", "-t", f"{loop_to:.3f}", out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("LOOP FAIL:\n" + r.stderr[-800:])
    subprocess.run(["rm", "-f", tmp])
else:
    cut(out)

d = probe_dur(out)
want = loop_to if (loop_to and loop_to > seg) else seg
if abs(d - want) > 0.25:
    sys.exit(f"FAIL: длительность {d:.2f}с, ждали {want:.2f}с")
print(f"OK вставка {out}: {d:.2f}с, crop={crop or 'нет'}, boxes={len(boxes)}, loop={'да' if loop_to and loop_to > seg else 'нет'}")