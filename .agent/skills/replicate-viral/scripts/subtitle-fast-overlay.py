#!/usr/bin/env python3
"""subtitle-fast-overlay.py — БЫСТРЫЙ дефолтный путь наших RU-субтитров (сессия по решению автора).

Зачем: subtitle-cover.py --detect (EAST покадрово) ЗАВИСАЛ ~1.5 часа на сборке reel-DXUH5dcDwKN.
Этот путь рендерит PNG (компактная НЕПРОЗРАЧНАЯ плашка + белый текст БЕЗ тени) по каждому cue
через PIL и накладывает ОДНИМ проходом ffmpeg overlay с enable='between(t,start,end)' — секунды,
не часы. ffmpeg-сборка тут БЕЗ libass (есть только overlay), потому через PNG.

Канон плашки (МЕТОД 2, автор «аккуратно, только субтитры автора, не в 3 раза больше»):
- компактная ОДНА строка (высота ~94px), НЕ 230+;
- ШИРИНА по нашему тексту (max(текст+90, floor)), НЕ форсить ~1000px/на всю ширину;
- НЕПРОЗРАЧНАЯ alpha=255 (иначе чужой текст просвечивает);
- БЕЗ drop-shadow за белым текстом (тень двоит контур = «размытие»);
- текст ≤3 слова на cue (караоке) — иначе предупреждение.

Usage:
  subtitle-fast-overlay.py --src in.mp4 --subs subs.json --out out.mp4
      [--font <ttf> --font-size 54 --plate-y0 1340 --plate-h 94 --text-cy 1387
       --plate-floor 360 --max-words 3 --dur <sec>]
  subs.json = [{"start":0.0,"end":2.4,"text":"наша реплика"}, ...]  (≤3 слова на cue)
Exit 0 ok / 1 ошибка.
"""
import sys, os, json, subprocess, argparse

W, H = 1080, 1920
DEFAULT_FONT = os.path.expanduser("~/<твоя рабочая папка ролика>/AvenirNextBold.ttf")
if not os.path.exists(DEFAULT_FONT):
    DEFAULT_FONT = "/System/Library/Fonts/Avenir Next.ttc"  # PIL читает .ttc индекс 0
FFMPEG = "ffmpeg" if os.path.exists("ffmpeg") else "ffmpeg"
FFPROBE = "ffprobe" if os.path.exists("ffprobe") else "ffprobe"


def probe_dur(p):
    try:
        return float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", p]).strip())
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--subs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--font-size", type=int, default=54)
    ap.add_argument("--plate-y0", type=int, default=1340)
    ap.add_argument("--plate-h", type=int, default=94)
    ap.add_argument("--text-cy", type=int, default=1387)
    ap.add_argument("--plate-floor", type=int, default=360)  # минимальная ширина плашки
    ap.add_argument("--max-words", type=int, default=3)
    ap.add_argument("--dur", type=float, default=0.0)
    a = ap.parse_args()

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("FAIL: PIL не установлен (pip install pillow)"); return 1

    cues = json.load(open(a.subs, encoding="utf-8"))
    if not cues:
        print("FAIL: пустой subs.json"); return 1
    over = [c for c in cues if len(str(c.get("text", "")).split()) > a.max_words]
    if over:
        print("WARN: %d cue с >%d слов (караоке-абзац) — %r"
              % (len(over), a.max_words, over[0]["text"]))

    font = ImageFont.truetype(a.font, a.font_size)
    pngdir = os.path.join(os.path.dirname(os.path.abspath(a.out)) or ".", "_subfast_png")
    os.makedirs(pngdir, exist_ok=True)
    CX = W // 2
    for i, c in enumerate(cues):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        txt = str(c["text"])
        bb = d.textbbox((0, 0), txt, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        pw = max(tw + 90, a.plate_floor)
        px0, px1 = CX - pw // 2, CX + pw // 2
        d.rounded_rectangle([px0, a.plate_y0, px1, a.plate_y0 + a.plate_h],
                            radius=22, fill=(13, 13, 16, 255))  # НЕПРОЗРАЧНАЯ
        tx = CX - tw // 2 - bb[0]
        ty = a.text_cy - th // 2 - bb[1]
        d.text((tx, ty), txt, font=font, fill=(255, 255, 255, 255))  # БЕЗ тени
        img.save(os.path.join(pngdir, "c%03d.png" % i))

    dur = a.dur or probe_dur(a.src) or 0
    inputs = ["-i", a.src]
    for i in range(len(cues)):
        inputs += ["-loop", "1", "-i", os.path.join(pngdir, "c%03d.png" % i)]
    fc, prev = [], "0:v"
    for i, c in enumerate(cues):
        out = "v%d" % i
        fc.append("[%s][%d:v]overlay=0:0:enable='between(t,%s,%s)'[%s]"
                  % (prev, i + 1, c["start"], c["end"], out))
        prev = out
    cmd = [FFMPEG, "-nostdin", "-loglevel", "error"] + inputs + \
          ["-filter_complex", ";".join(fc), "-map", "[%s]" % prev, "-map", "0:a?"]
    if dur:
        cmd += ["-t", "%.3f" % dur]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "16",
            "-pix_fmt", "yuv420p", "-r", "30", a.out, "-y"]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("FAIL: ffmpeg overlay rc=%d" % r.returncode); return 1
    print("OK: %s (%d cue, плашка y%d..%d h=%d, alpha=255, без тени)"
          % (a.out, len(cues), a.plate_y0, a.plate_y0 + a.plate_h, a.plate_h))
    return 0


if __name__ == "__main__":
    sys.exit(main())