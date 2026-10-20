#!/usr/bin/env python3
"""source-vision-selftest.py — self-test движка покадрового зрения source_vision.py.

Синтезирует 4с клип 1080x1920, где субтитр автора ДВИЖЕТСЯ по сцене (первые 2с вверху
y≈900, последние 2с внизу y≈1300) + статичный тонкий UID-дистрактор сверху. Проверяет
то, чего НЕ умел старый 9-сэмпловый медианный детект:

  CHECK 1 ПОКАДРОВО — n_analyzed == round(dur*fps) (КАЖДЫЙ кадр, не выборка).
  CHECK 2 ТРЕКАЕТ ДВИЖЕНИЕ — медиана cy первой половины и второй РАЗЛИЧАЮТСЯ >200px
          (старая медиана дала бы одну позицию мимо обеих).
  CHECK 3 ЖИВОЙ > СТАТИКА — детект выбирает большой движущийся субтитр, НЕ статичный
          тонкий UID (cy далеко от UID-полосы y≈200).
  CHECK 4 ДЕТЕКТ ЛИЦ НЕ ПАДАЕТ — detect_faces возвращает список (YuNet/Haar), без краха.

VERDICT PASS/FAIL, exit 0/2.
"""
import os, sys, subprocess, tempfile, statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_vision

W, H, FPS, DUR = 1080, 1920, 30, 4
FONT = "/System/Library/Fonts/Avenir Next.ttc"
FFMPEG = "ffmpeg" if os.path.exists("ffmpeg") else "ffmpeg"
UID_Y = 200          # статичный тонкий UID сверху (дистрактор)
TOP_CY, BOT_CY = 900, 1300


def make_clip(path):
    from PIL import Image, ImageDraw, ImageFont
    big = ImageFont.truetype(FONT, 64, index=0)
    thin = ImageFont.truetype(FONT, 22, index=0)
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tmp = tempfile.mkdtemp(prefix="sv_self_")
    n = DUR * FPS
    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), (32, 28, 48))
        d = ImageDraw.Draw(img)
        # статичный тонкий UID-дистрактор (та же яркость, но тонкий → должен проигрывать)
        d.text((40, UID_Y), "static ui label v1.2.3 status ok", font=thin, fill=(235, 235, 235))
        # движущийся субтитр автора: МЕНЯЕТ текст каждые ~0.5с (караоке) и позицию по сцене
        word = ["GENERATION", "BUILD", "SHIP", "DEPLOY", "SCALE", "GROW", "WIN", "NOW"][i % 8]
        cy = TOP_CY if t < DUR / 2 else BOT_CY
        tw = d.textlength(word, font=big)
        d.text(((W - tw) / 2, cy - 36), word, font=big, fill=(255, 255, 255),
               stroke_width=4, stroke_fill=(0, 0, 0))
        img.save(os.path.join(tmp, "f_%04d.png" % i))
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "f_%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", path],
                       capture_output=True, text=True)
    return r.returncode == 0


def main():
    tmp = tempfile.mkdtemp(prefix="sv_clip_")
    clip = os.path.join(tmp, "moving.mp4")
    if not make_clip(clip):
        print("VERDICT FAIL: не собрался синтетический клип"); return 2

    res = source_vision.analyze(clip, want_faces=True, want_caption=True)
    s, fr = res["summary"], res["frames"]
    p = f = 0

    def expect(label, cond, detail=""):
        nonlocal p, f
        mark = "v" if cond else "x"
        print(f"  {mark} {label}" + (f"  [{detail}]" if detail else ""))
        if cond: p += 1
        else: f += 1

    expected = round(DUR * s["fps"])
    print("---- CHECK 1: ПОКАДРОВО ----")
    expect("n_analyzed == round(dur*fps) (каждый кадр)",
           abs(s["n_analyzed"] - expected) <= 1, f"{s['n_analyzed']} vs {expected}")

    caps = [(f0["t"], f0["cap"]) for f0 in fr if f0.get("cap")]
    first = [c[1][0] for c in caps if c[0] < DUR / 2]
    second = [c[1][0] for c in caps if c[0] >= DUR / 2]
    print("---- CHECK 2: ТРЕКАЕТ ДВИЖЕНИЕ ----")
    if first and second:
        mf, ms = statistics.median(first), statistics.median(second)
        expect("медиана cy 1-й и 2-й половины различаются >200px",
               abs(mf - ms) > 200, f"cy1={mf:.0f} cy2={ms:.0f}")
    else:
        expect("медиана cy 1-й и 2-й половины различаются >200px", False, "нет детектов")

    print("---- CHECK 3: ЖИВОЙ СУБТИТР > СТАТИЧНЫЙ UID ----")
    near_uid = [c for c in caps if abs(c[1][0] - UID_Y) < 80]
    near_subtitle = [c for c in caps if abs(c[1][0] - TOP_CY) < 120 or abs(c[1][0] - BOT_CY) < 120]
    expect("детект на движущемся субтитре, не на статичном UID",
           len(near_subtitle) > len(near_uid) and len(near_uid) < 0.1 * max(1, len(caps)),
           f"на субтитре={len(near_subtitle)} на UID={len(near_uid)}")

    print("---- CHECK 4: ДЕТЕКТ ЛИЦ НЕ ПАДАЕТ ----")
    expect("face_engine определён + frames несут поле faces",
           s["face_engine"] in ("yunet", "haar") and all("faces" in x for x in fr),
           f"движок={s['face_engine']}")

    print("---- ИТОГ ----")
    print(f"  {p} passed, {f} failed  (движок лиц={s['face_engine']}, fps={s['fps']:.2f})")
    if f == 0:
        print("VERDICT PASS"); return 0
    print("VERDICT FAIL"); return 2


if __name__ == "__main__":
    sys.exit(main())