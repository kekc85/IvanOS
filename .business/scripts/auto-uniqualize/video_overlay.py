#!/usr/bin/env python3
"""video_overlay.py — наш русский текст ПОВЕРХ видео-слайда карусели, закрывая оригинальный.

Зачем: если слайд карусели в оригинале ВИДЕО (media_type=2, играбельная демка/3D/анимация),
его НЕЛЬЗЯ заменять статичным скриншотом (автор: «если карусель в формате видео,
вырезай видео, мне твои картинки не нужны»). Берём оригинальное видео как есть и кладём НАШ
заголовок плашкой ПОВЕРХ вшитого чужого текста (англ. заголовок автора + его @хэндл).

Подход (закрывает чужой вшитый текст без inpaint):
  scale COVER до 1080x1350 (видео заполняет кадр целиком, чужой текст уезжает к верх/низ краям)
  -> верхняя тёмная плашка с НАШИМ заголовком (перекрывает оригинальный верхний заголовок)
  -> нижняя тёмная плашка (перекрывает оригинальный @хэндл/подпись автора)
ffmpeg здесь без drawtext (часто собран без freetype) -> текст рисуем PIL'ом в PNG-оверлей.

Usage: video_overlay.py <in.mp4> <out.mp4> "<заголовок с \\n>" [--secs 8]
"""
import sys, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

inp, outp, title = sys.argv[1], sys.argv[2], sys.argv[3]
secs = 8
if "--secs" in sys.argv: secs = float(sys.argv[sys.argv.index("--secs")+1])

W, H = 1080, 1350
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
font = ImageFont.truetype(FONT_PATH, 54)

# PNG-оверлей: верхняя плашка (наш заголовок, закрывает чужой верхний текст) + нижняя плашка (закрывает хэндл)
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
TOP_H = 400   # закрывает оригинальный заголовок автора (он у верхнего края после cover)
BOT_H = 420   # закрывает оригинальный @хэндл/подпись автора (у нижнего края)
d.rectangle([0, 0, W, TOP_H], fill=(0, 0, 0, 255))
d.rectangle([0, H - BOT_H, W, H], fill=(0, 0, 0, 255))
y = 120
for ln in title.split("\\n"):
    bb = d.textbbox((0, 0), ln, font=font); w = bb[2] - bb[0]
    d.text(((W - w) / 2, y), ln, font=font, fill=(255, 255, 255, 255)); y += 76
tmp_png = tempfile.mktemp(suffix=".png")
ov.save(tmp_png)

# COVER scale (заполнить кадр, обрезать лишнее) + наложить оверлей
vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
      f"crop={W}:{H}[bg];[bg][1:v]overlay=0:0")
r = subprocess.run(["ffmpeg", "-y", "-i", inp, "-i", tmp_png,
                    "-filter_complex", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-an", "-t", str(secs), outp],
                   capture_output=True, text=True)
os.remove(tmp_png)
if r.returncode != 0:
    sys.stderr.write(r.stderr[-800:]); sys.exit(1)
print(f"video overlay ok -> {outp}")
