#!/usr/bin/env python3
"""
contact_sheet.py - контактный лист кадров видео для приёмки глазами.

Usage:
    contact_sheet.py <video.mp4> <out.png> --times "1.0,5.2,10.3,..." [--cols 4] [--cell-width 360]
"""

import sys
import os
import argparse
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

FFMPEG = "ffmpeg"


def extract_frame(video_path, t, out_png):
    """Вытащить один кадр в момент времени t секунд."""
    cmd = [FFMPEG, "-y", "-ss", str(t), "-i", video_path,
           "-frames:v", "1", out_png]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(out_png):
        raise RuntimeError(f"не удалось извлечь кадр t={t}: {result.stderr[-1000:]}")


def load_font(size):
    """Попытаться загрузить системный шрифт, иначе дефолт PIL."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_label_with_outline(draw, xy, text, font):
    """Белый текст с чёрной обводкой (для читаемости на любом фоне кадра)."""
    x, y = xy
    outline_color = (0, 0, 0)
    fill_color = (255, 255, 255)
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill_color)


def main():
    parser = argparse.ArgumentParser(description="Контактный лист кадров")
    parser.add_argument("video")
    parser.add_argument("out_png")
    parser.add_argument("--times", required=True, help="список времён через запятую, напр. 1.0,5.2,10.3")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--cell-width", type=int, default=360)
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"ОШИБКА: видео не найдено: {args.video}", file=sys.stderr)
        sys.exit(1)

    times = [float(t.strip()) for t in args.times.split(",") if t.strip()]
    if not times:
        print("ОШИБКА: пустой список времён", file=sys.stderr)
        sys.exit(1)

    tmp_dir = tempfile.mkdtemp(prefix="contact_sheet_")
    frame_imgs = []

    try:
        for i, t in enumerate(times):
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            extract_frame(args.video, t, frame_path)
            img = Image.open(frame_path).convert("RGB")
            frame_imgs.append((t, img))

        cols = args.cols
        cell_w = args.cell_width
        rows = (len(frame_imgs) + cols - 1) // cols

        # пропорциональное уменьшение по первому кадру
        first_w, first_h = frame_imgs[0][1].size
        cell_h = int(first_h * (cell_w / first_w))

        sheet_w = cols * cell_w
        sheet_h = rows * cell_h
        sheet = Image.new("RGB", (sheet_w, sheet_h), (20, 20, 20))

        font = load_font(max(14, cell_w // 18))

        for idx, (t, img) in enumerate(frame_imgs):
            resized = img.resize((cell_w, cell_h), Image.LANCZOS)
            col = idx % cols
            row = idx // cols
            x = col * cell_w
            y = row * cell_h
            sheet.paste(resized, (x, y))
            draw = ImageDraw.Draw(sheet)
            draw_label_with_outline(draw, (x + 8, y + 8), f"t={t:.1f}s", font)

        sheet.save(args.out_png)
    finally:
        for f in os.listdir(tmp_dir):
            try:
                os.remove(os.path.join(tmp_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    # самопроверка
    if not os.path.exists(args.out_png):
        print(f"ОШИБКА: выходной png не создан: {args.out_png}", file=sys.stderr)
        sys.exit(1)

    size_bytes = os.path.getsize(args.out_png)
    if size_bytes <= 50 * 1024:
        print(f"ОШИБКА: png слишком мал ({size_bytes} байт), похоже на брак", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {args.out_png} размер сетки {sheet_w}x{sheet_h}, {size_bytes} байт, {len(frame_imgs)} кадров ({cols} колонок x {rows} строк)")


if __name__ == "__main__":
    main()
