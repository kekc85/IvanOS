#!/usr/bin/env python3
"""subtitle-cover-selftest.py — self-test для subtitle-cover.py.

Синтезирует 5с вертикальный клип 1080x1920 с ВШИТЫМ ЧУЖИМ английским субтитром
(жёлтый «THIS IS THEIR SUBTITLE», burned через ffmpeg overlay поверх градиент-фона,
+ тихий звук). Прогоняет subtitle-cover. Проверяет:
  · в полосе ИХ субтитра ПОСЛЕ накрытия: std яркости ~0 (текст убит) И нет жёлтых пикселей;
    причём проверяем НЕ только центр, но и ЛЕВЫЙ/ПРАВЫЙ края плашки (правило 3:
    плашка по высоте оригинала, непрозрачна, чужой текст не торчит по краям);
  · в нашей строке: белый текст есть (>2000 px), И он НЕ жёлтый (правило 2: шрифт
    одноцветный белый, жёлтый запрещён в даты запуска).

Плюс изолированные under-test кейсы (CHECK-карта):
  CHECK 1 КАРАОКЕ ≤3 СЛОВ — позитив (cue ≤3 слов проходит) + негатив (cue 4 слова → cover exit 1);
  CHECK 2 ШРИФТ НЕ ЖЁЛТЫЙ — позитив (наш белый текст не жёлтый) + негатив (синтет. жёлтый текст ловится);
  CHECK 3 ПЛАШКА ПО ВЫСОТЕ+НЕПРОЗРАЧНА ПО КРАЯМ — позитив (residual=0 в центре И по краям) +
          негатив (узкая плашка → чужой текст торчит на краю → ловится).
PASS только если их текст накрыт (центр+края) И наш виден И не жёлтый И все CHECK зелёные.
VERDICT PASS/FAIL, exit 0/2.
"""
import os, sys, json, subprocess, tempfile

W, H = 1080, 1920
FONT_PATH = "/System/Library/Fonts/Avenir Next.ttc"
FFMPEG = "ffmpeg" if os.path.exists("ffmpeg") else "ffmpeg"
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subtitle-cover.py")

# их субтитр расположим в нижней зоне ~ y 1300..1380 (центр 1340)
THEIR_TOP, THEIR_BOT = 1300, 1382
THEIR_CY = (THEIR_TOP + THEIR_BOT) // 2


def make_their_subtitle_png(path):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 58, index=0)
    except Exception:
        font = ImageFont.load_default()
    text = "THIS IS THEIR SUBTITLE"
    tw = d.textlength(text, font=font)
    x = (W - tw) / 2
    y = THEIR_CY - 30
    # ярко-жёлтый с чёрной обводкой — типичный burned-in субтитр
    d.text((x, y), text, font=font, fill=(255, 225, 0, 255),
           stroke_width=3, stroke_fill=(0, 0, 0, 255))
    img.save(path)


def yellow_dominant(bgr_region):
    """Дешёвый пиксельный чек: доминирует ли ЖЁЛТЫЙ в текст-зоне (правило 2).
    Жёлтый = высокие R и G, низкий B. Считаем долю жёлтых среди ЯРКИХ (текст) пикселей.
    Возвращает (is_yellow, frac, yellow_px, bright_px)."""
    import numpy as np
    b = bgr_region[:, :, 0].astype(int)
    g = bgr_region[:, :, 1].astype(int)
    r = bgr_region[:, :, 2].astype(int)
    lum = (b + g + r) / 3.0
    bright = lum > 140                       # пиксели текста (на тёмной плашке)
    yellow = (r > 150) & (g > 150) & (b < 120)
    bright_px = int(np.sum(bright))
    yellow_px = int(np.sum(yellow & bright))
    frac = (yellow_px / bright_px) if bright_px > 0 else 0.0
    # доминирует, если >35% ярких пикселей текста жёлтые (одиночный антиалиас не триггерит)
    return (frac > 0.35 and yellow_px > 200), frac, yellow_px, bright_px


def run_cover(tmp, subs, plate_top, plate_bot, text_cy, src,
              extra=None, out_name="out.mp4"):
    """Прогнать subtitle-cover.py, вернуть (returncode, out_path, stdout, stderr)."""
    subs_path = os.path.join(tmp, f"subs_{out_name}.json")
    json.dump(subs, open(subs_path, "w"), ensure_ascii=False)
    out = os.path.join(tmp, out_name)
    cmd = [sys.executable, SCRIPT, "--src", src, "--subs", subs_path, "--out", out,
           "--plate-top", str(plate_top), "--plate-bot", str(plate_bot),
           "--text-cy", str(text_cy), "--plate-alpha", "0.97", "--font-size", "54"]
    if extra:
        cmd += extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, out, r.stdout, r.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="subcover_selftest_")
    their_png = os.path.join(tmp, "their.png")
    make_their_subtitle_png(their_png)

    src = os.path.join(tmp, "src.mp4")
    # градиент-фон 5с + burned их субтитр + тихий звук
    cmd_src = [
        FFMPEG, "-y", "-v", "error",
        "-f", "lavfi", "-i", f"gradients=s={W}x{H}:d=5:c0=0x202040:c1=0x804020,format=rgba",
        "-loop", "1", "-framerate", "30", "-t", "5", "-i", their_png,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "2:a", "-t", "5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", src]
    r = subprocess.run(cmd_src, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(src):
        print("VERDICT FAIL: не собрался исходник\n", r.stderr[-1500:]); sys.exit(2)

    # наши субтитры — белые, в нашей строке (НАД их полосой, в safe-zone)
    OUR_CY = 1180
    subs = [
        {"start": 0.0, "end": 2.4, "text": "наша первая реплика"},
        {"start": 2.4, "end": 5.0, "text": "вторая реплика поверх"},
    ]
    subs_path = os.path.join(tmp, "subs.json")
    json.dump(subs, open(subs_path, "w"), ensure_ascii=False)

    out = os.path.join(tmp, "out.mp4")
    # плашка должна накрыть их полосу 1300..1382 → ставим plate с запасом
    cmd_run = [
        sys.executable, SCRIPT,
        "--src", src, "--subs", subs_path, "--out", out,
        "--plate-top", str(THEIR_TOP - 30), "--plate-bot", str(THEIR_BOT + 30),
        "--text-cy", str(OUR_CY), "--plate-alpha", "0.97", "--font-size", "54"]
    r = subprocess.run(cmd_run, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0 or not os.path.isfile(out):
        print("VERDICT FAIL: subtitle-cover упал\n", r.stderr[-1500:]); sys.exit(2)

    # извлечь кадр на 2.5с
    import cv2
    import numpy as np
    frame_png = os.path.join(tmp, "frame.png")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "2.5", "-i", out,
                    "-frames:v", "1", frame_png],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    img = cv2.imread(frame_png)
    if img is None:
        print("VERDICT FAIL: не извлёкся кадр"); sys.exit(2)
    # BGR
    h, w = img.shape[:2]

    # --- ПРОВЕРКА 1: их полоса накрыта (центральная зона плашки, без нашего текста) ---
    band = img[THEIR_TOP:THEIR_BOT, 60:w - 60]
    gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
    band_std = float(np.std(gray))
    band_mean = float(np.mean(gray))
    # жёлтые пиксели: высокий R,G и низкий B (в BGR: B низкий, G высокий, R высокий)
    b, g, rr = band[:, :, 0].astype(int), band[:, :, 1].astype(int), band[:, :, 2].astype(int)
    yellow_mask = (rr > 150) & (g > 150) & (b < 120)
    yellow_px = int(np.sum(yellow_mask))

    # --- ПРОВЕРКА 2: наш белый текст виден в нашей строке ---
    our_band = img[OUR_CY - 90:OUR_CY + 90, 0:w]
    og = cv2.cvtColor(our_band, cv2.COLOR_BGR2GRAY)
    white_px = int(np.sum(og > 220))

    THEIR_COVERED = band_std < 8.0 and yellow_px < 50 and band_mean < 60
    OUR_VISIBLE = white_px > 2000

    # --- ПРОВЕРКА 3 (правило 3): residual чужого текста по КРАЯМ плашки = 0 ---
    # плашка margin_x=24 → берём узкие столбцы у левого и правого внутренних краёв.
    EDGE_W = 90
    left_band = img[THEIR_TOP:THEIR_BOT, 26:26 + EDGE_W]
    right_band = img[THEIR_TOP:THEIR_BOT, w - 26 - EDGE_W:w - 26]
    left_std = float(np.std(cv2.cvtColor(left_band, cv2.COLOR_BGR2GRAY)))
    right_std = float(np.std(cv2.cvtColor(right_band, cv2.COLOR_BGR2GRAY)))
    left_mean = float(np.mean(cv2.cvtColor(left_band, cv2.COLOR_BGR2GRAY)))
    right_mean = float(np.mean(cv2.cvtColor(right_band, cv2.COLOR_BGR2GRAY)))
    EDGES_CLEAN = (left_std < 8.0 and right_std < 8.0 and left_mean < 60 and right_mean < 60)

    # --- ПРОВЕРКА 2 (правило 2): наш текст НЕ жёлтый ---
    our_yellow, our_yfrac, our_ypx, our_bright = yellow_dominant(our_band)
    OUR_NOT_YELLOW = not our_yellow

    print("---- ПИКСЕЛЬНАЯ ПРОВЕРКА (главный кейс) ----")
    print(f"их полоса центр y[{THEIR_TOP}..{THEIR_BOT}]: std={band_std:.2f} (need<8) "
          f"mean={band_mean:.2f} (need<60) yellow_px={yellow_px} (need<50) "
          f"→ {'НАКРЫТО' if THEIR_COVERED else 'ПРОСВЕЧИВАЕТ'}")
    print(f"их полоса КРАЯ: left std={left_std:.2f}/mean={left_mean:.2f} "
          f"right std={right_std:.2f}/mean={right_mean:.2f} (need std<8,mean<60) "
          f"→ {'ЧИСТО' if EDGES_CLEAN else 'ТЕКСТ ТОРЧИТ ПО КРАЮ'}")
    print(f"наша строка y~{OUR_CY}: white_px={white_px} (need>2000) "
          f"→ {'ВИДЕН' if OUR_VISIBLE else 'НЕ ВИДЕН'}")
    print(f"наш текст жёлтый? frac={our_yfrac:.2f} yellow_px={our_ypx}/bright={our_bright} "
          f"→ {'ЖЁЛТЫЙ (FAIL)' if our_yellow else 'не жёлтый (ok)'}")

    main_ok = THEIR_COVERED and OUR_VISIBLE and EDGES_CLEAN and OUR_NOT_YELLOW
    main_reasons = []
    if not THEIR_COVERED: main_reasons.append("их субтитр НЕ накрыт в центре (просвечивает)")
    if not EDGES_CLEAN:   main_reasons.append("чужой текст торчит по КРАЮ плашки (плашка узкая)")
    if not OUR_VISIBLE:   main_reasons.append("наш текст НЕ виден")
    if not OUR_NOT_YELLOW: main_reasons.append("наш шрифт ЖЁЛТЫЙ (запрещён в даты запуска)")

    # ===== ИЗОЛИРОВАННЫЕ CHECK-КЕЙСЫ (positive + negative) =====
    sub_pass, sub_fail = 0, 0

    def expect(label, cond):
        nonlocal sub_pass, sub_fail
        if cond:
            print(f"  v {label}"); sub_pass += 1
        else:
            print(f"  x {label}"); sub_fail += 1

    print("---- CHECK 1: КАРАОКЕ ≤3 СЛОВ ----")
    # positive: cue ≤3 слов → cover проходит (exit 0)
    rc_ok, _o, _so, _se = run_cover(
        tmp, [{"start": 0.0, "end": 2.0, "text": "три слова ровно"}],
        THEIR_TOP - 30, THEIR_BOT + 30, OUR_CY, src, out_name="kar_ok.mp4")
    expect("позитив: cue '3 слова' → cover PASS (exit 0)", rc_ok == 0)
    # negative: cue 4 слова → cover FAIL (exit 1) с маркером «СУБТИТР-АБЗАЦ»
    rc_bad, _o2, so2, _se2 = run_cover(
        tmp, [{"start": 0.0, "end": 2.0, "text": "это уже четыре слова"}],
        THEIR_TOP - 30, THEIR_BOT + 30, OUR_CY, src, out_name="kar_bad.mp4")
    expect("негатив: cue '4 слова' → cover FAIL (exit 1) + «СУБТИТР-АБЗАЦ»",
           rc_bad == 1 and "СУБТИТР-АБЗАЦ" in so2)

    print("---- CHECK 2: ШРИФТ НЕ ЖЁЛТЫЙ ----")
    # positive: наш реальный (белый) текст не жёлтый — уже посчитан выше
    expect("позитив: наш белый текст не жёлтый", OUR_NOT_YELLOW)
    # negative: синтетический жёлтый текст ловится yellow_dominant
    yp = os.path.join(tmp, "yellowtext.png")
    make_yellow_our_png(yp, OUR_CY)
    yframe = os.path.join(tmp, "yf.png")
    subprocess.run([FFMPEG, "-y", "-v", "error",
                    "-f", "lavfi", "-i", f"color=c=0x121214:s={W}x{H}:d=1",
                    "-i", yp, "-filter_complex", "[0:v][1:v]overlay=0:0",
                    "-frames:v", "1", yframe],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    yimg = cv2.imread(yframe)
    yband = yimg[OUR_CY - 90:OUR_CY + 90, 0:W]
    yhit, yf2, _yp2, _yb2 = yellow_dominant(yband)
    expect(f"негатив: синтетический жёлтый текст ловится (frac={yf2:.2f})", yhit)

    print("---- CHECK 3: ПЛАШКА ПО ВЫСОТЕ + НЕПРОЗРАЧНА ПО КРАЯМ ----")
    # positive: широкая плашка (весь её диапазон) → края чисто — уже посчитан выше
    expect("позитив: широкая плашка, residual по краям = 0", EDGES_CLEAN)
    # negative: УЗКАЯ плашка (узкое окно по ШИРИНЕ невозможно через CLI — плашка всегда
    # на всю ширину). Узость по ВЫСОТЕ: плашка НИЖЕ полосы их субтитра → верх их полосы
    # торчит. Ставим plate ниже их текста → проверяем что их верх просвечивает.
    rc_n, out_narrow, _son, _sen = run_cover(
        tmp, [{"start": 0.0, "end": 2.0, "text": "наш текст"}],
        THEIR_BOT + 10, THEIR_BOT + 120, 1180, src, out_name="plate_narrow.mp4")
    nf = os.path.join(tmp, "nf.png")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "1.0", "-i", out_narrow,
                    "-frames:v", "1", nf],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    nimg = cv2.imread(nf)
    # их полоса (THEIR_TOP..THEIR_BOT) теперь НЕ накрыта (плашка ниже) → текст просвечивает
    their_uncov = nimg[THEIR_TOP:THEIR_BOT, 60:W - 60]
    tu_std = float(np.std(cv2.cvtColor(their_uncov, cv2.COLOR_BGR2GRAY)))
    expect(f"негатив: плашка короче полосы → их субтитр просвечивает (std={tu_std:.1f}>8)",
           rc_n == 0 and tu_std > 8.0)

    # ===== ИТОГ =====
    print("---- ИТОГ ----")
    print(f"  главный кейс: {'OK' if main_ok else 'FAIL — ' + '; '.join(main_reasons)}")
    print(f"  под-кейсы CHECK 1-3: {sub_pass} passed, {sub_fail} failed")

    if main_ok and sub_fail == 0:
        print("VERDICT PASS")
        sys.exit(0)
    else:
        print("VERDICT FAIL")
        sys.exit(2)


def make_yellow_our_png(path, cy):
    """синтетический ЖЁЛТЫЙ текст в нашей строке (негатив-кейс правила 2)."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 64, index=0)
    except Exception:
        font = ImageFont.load_default()
    text = "ЖЁЛТЫЙ СУБТИТР"
    tw = d.textlength(text, font=font)
    d.text(((W - tw) / 2, cy - 35), text, font=font,
           fill=(255, 215, 0, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    img.save(path)


if __name__ == "__main__":
    main()
