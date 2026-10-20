#!/usr/bin/env python3
"""Build a 5x4 reference grid of the 20 canonical Reel formats with slug labels.

Usage:
    python3 build-format-grid.py <format-examples-dir> <output.jpg>

Reads files named NN-slug.jpg from <format-examples-dir>, lays them out 5 cols x 4 rows
with the slug printed under each tile. Output is the single mosaic used by ingest-reel
SKILL.md Step 3 as the visual classifier reference.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TILE_W = 270
TILE_H = 480
LABEL_H = 44
COLS = 5
ROWS = 4
GAP = 8
PAD = 12

FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def pick_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main(src_dir: Path, out_path: Path) -> None:
    tiles = sorted(src_dir.glob("[0-9][0-9]-*.jpg"))
    if len(tiles) != COLS * ROWS:
        sys.exit(f"expected {COLS * ROWS} tiles, found {len(tiles)} in {src_dir}")

    cell_w = TILE_W
    cell_h = TILE_H + LABEL_H
    canvas_w = PAD * 2 + COLS * cell_w + (COLS - 1) * GAP
    canvas_h = PAD * 2 + ROWS * cell_h + (ROWS - 1) * GAP

    canvas = Image.new("RGB", (canvas_w, canvas_h), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)
    font = pick_font(22)

    for idx, tile_path in enumerate(tiles):
        row, col = divmod(idx, COLS)
        x = PAD + col * (cell_w + GAP)
        y = PAD + row * (cell_h + GAP)

        img = Image.open(tile_path).convert("RGB")
        img = img.resize((TILE_W, TILE_H), Image.LANCZOS)
        canvas.paste(img, (x, y))

        label = tile_path.stem
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = x + (TILE_W - text_w) // 2
        text_y = y + TILE_H + (LABEL_H - text_h) // 2 - 4
        draw.rectangle(
            [x, y + TILE_H, x + TILE_W, y + TILE_H + LABEL_H],
            fill=(20, 20, 24),
        )
        draw.text((text_x, text_y), label, fill=(240, 240, 240), font=font)

    canvas.save(out_path, "JPEG", quality=88, optimize=True)
    print(f"wrote {out_path} ({canvas_w}x{canvas_h})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: build-format-grid.py <format-examples-dir> <output.jpg>")
    main(Path(sys.argv[1]), Path(sys.argv[2]))