#!/usr/bin/env python3
"""subtitle-cover.py — накрывает ВШИТЫЕ субтитры автора ТЁМНОЙ НЕПРОЗРАЧНОЙ ПЛАШКОЙ
и кладёт НАШИ белые RU-субтитры поверх. БЕЗ инпейнта (ProPainter), БЕЗ блюра.
Лёгкая схема: ffmpeg overlay + PIL-рендеренные прозрачные PNG (т.к. ffmpeg 8.x здесь
БЕЗ drawtext/subtitles/libass — есть только overlay/drawbox/format/scale).

Прецедент / уроки (НЕ повторять):
1. ПЛАШКА ДОЛЖНА БЫТЬ НЕПРОЗРАЧНОЙ (чужой текст под ней НЕ просвечивает).
   В PIL rounded_rectangle(fill=(0,0,0,a)) на RGBA ЗАМЕНЯЕТ пиксель (не композит).
   Решение: плашку рисуем как СПЛОШНУЮ непрозрачную тёмную rounded-rect (~20,20,20,255)
   при alpha>=~0.99, либо корректно композитим тёмный@alpha поверх белого-opaque когда
   alpha<1 (alpha_composite, не replace). Дефолт alpha 0.92 → практически чёрная.
2. Image-входы (plate.png, cue.png) в ffmpeg задаём с -loop 1 -framerate -t <dur>,
   иначе одиночный PNG в overlay даёт ПРЕРЫВИСТУЮ плашку. Выход с -shortest.
3. Плашка — ровно полоса субтитров (~10-20% кадра), не пол-экрана, не основной UI.
4. Наш текст в safe-zone (text-cy <= 1430), не на лице.
5. Плашка на всю длительность присутствия их субтитров (дефолт — весь ролик,
   чтобы их субтитры не выглядывали в gap'ах между нашими репликами).
6. 🔴 ПЛАШКА = РАЗМЕР ПЛАШКИ АВТОРА + пара мм (автор, поправил дважды):
   НЕ жирный бар на пол-панели («жрёт пространство») и НЕ впритык к тексту («тоненькие,
   уже оригинала»). Эталон — сама Submagic-пилюля автора: высота ≈ текст+56px (~115px),
   ширина ≈ текст+150px (мин ~540px), радиус ~26.
7. 🔴 ПОЗИЦИЯ = ДЕТЕКТ автора ПОКАДРОВО, не фикс: субтитр автора гуляет по сценам
   (сплит — на шве; демо после 30с — ниже, под контентом). Фикс-позиция промахивается.
   Детект искать по ВСЕЙ высоте (не только нижние 45%) — автор бывает full-frame, субтитр
   у него тогда в нижней трети, но содержимое выше. Робастный детектор (эрозия тонкого
   UI-текста + темпоральный признак караоке + удержание позиции) — `~/<твоя рабочая папка ролика>/build2/subs2.py`.

Usage:
  subtitle-cover.py --src in.mp4 --subs subs.json --out out.mp4
       [--plate-top 1085 --plate-bot 1540 --text-cy 1345 --plate-alpha 0.92
        --font-size 56 --detect --plate-window cues]
  subs.json = [{"start":0.0,"end":2.4,"text":"наша реплика"}, ...]
  --detect : ПОКАДРОВЫЙ движок (source_vision) — на КАЖДОМ кадре находит реальную полосу
             субтитра автора (cy,h,x0,x1), темпорально-связно (караоке-признак + удержание
             + отброс глитча), и кладёт плашку РОВНО туда, размером под пилюлю автора, с
             нашим текстом поверх. Это дефолт продакшена (ЗАКОН 4). БЕЗ --detect = ручной
             статичный режим по --plate-top/--plate-bot/--text-cy (override / тесты).
  --split-windows file.json : [[t0,t1],...] окна сплита — в них низ плашки прижат к шву.
  --plate-window full|cues : (только статичный режим) full — плашка весь ролик; cues — окна реплик.
Exit 0 ok / 1 ошибка.
"""
import sys, os, json, subprocess, argparse, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_vision import detect_caption, CaptionTracker, GLITCH_PX  # единый покадровый детект

PLATE_PAD = 56          # высота плашки = текст/пилюля автора + пара мм (правило 2a)
SPLIT_SEAM_DEFAULT = 838  # шов сплита (низ плашки прижать сюда в split-окне)

W, H = 1080, 1920
FONT_PATH = "/System/Library/Fonts/Avenir Next.ttc"
FFMPEG = "ffmpeg" if os.path.exists("ffmpeg") else "ffmpeg"
FFPROBE = "ffprobe" if os.path.exists("ffprobe") else "ffprobe"


def probe_duration(src):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", src],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def probe_dims(src):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", src], capture_output=True, text=True)
    try:
        w, h = out.stdout.strip().split("x")
        return int(w), int(h)
    except Exception:
        return W, H


def make_plate_png(path, top, bot, alpha):
    """Непрозрачная тёмная rounded-rect полоса top..bot на прозрачном холсте."""
    from PIL import Image, ImageDraw
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # целевой цвет плашки: тёмный, при alpha~1 практически чёрный (20,20,20)
    base = (18, 18, 20)
    a = int(round(max(0.0, min(1.0, alpha)) * 255))
    margin_x = 24
    radius = 28
    rect = [margin_x, int(top), W - margin_x, int(bot)]
    # рисуем плашку как НЕПРОЗРАЧНУЮ заливку на отдельном слое и композитим
    plate_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate_layer)
    d.rounded_rectangle(rect, radius=radius, fill=(base[0], base[1], base[2], a))
    canvas = Image.alpha_composite(canvas, plate_layer)
    canvas.save(path)
    return rect


def _load_font(size):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT_PATH, size, index=0)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def make_cue_png(path, text, cy, font_size, max_w=W - 160):
    """Белый текст с тёмной обводкой, центр по cy. На прозрачном холсте."""
    from PIL import Image, ImageDraw
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    font = _load_font(font_size)
    lines = _wrap(d, text.strip(), font, max_w)
    line_h = int(font_size * 1.22)
    total_h = line_h * len(lines)
    y = int(cy) - total_h // 2
    stroke = max(2, font_size // 14)
    for ln in lines:
        tw = d.textlength(ln, font=font)
        x = (W - tw) / 2
        d.text((x, y), ln, font=font, fill=(255, 255, 255, 255),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 235))
        y += line_h
    canvas.save(path)


MAX_KARAOKE_WORDS = 3


def check_karaoke_groups(subs, max_words=MAX_KARAOKE_WORDS):
    """Караоке-инвариант : наши субтитры = группы ≤3 слов, быстро
    появляются/пропадают. Cue с >max_words слов = субтитр-АБЗАЦ (плашка-кирпич) = брак.
    Возвращает (ok, fails[]). Пустые cue игнорируем (брака нет)."""
    fails = []
    for i, s in enumerate(subs):
        txt = str(s.get("text", "")).strip()
        if not txt:
            continue
        n = len(txt.split())
        if n > max_words:
            label = s.get("label", f"cue#{i}")
            fails.append(
                f"СУБТИТР-АБЗАЦ вместо караоке [{label}] @ {float(s.get('start',0)):.2f}s: "
                f"{n} слов (>{max_words}) «{txt[:50]}» — дроби на группы ≤{max_words} слов")
    return (len(fails) == 0, fails)


def merge_windows(subs, gap=0.4):
    """Объединить близкие cue-окна в непрерывные интервалы для плашки."""
    if not subs:
        return []
    iv = sorted((float(s["start"]), float(s["end"])) for s in subs)
    out = [list(iv[0])]
    for a, b in iv[1:]:
        if a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _active_cue(subs, t):
    for s in subs:
        if float(s["start"]) <= t < float(s["end"]):
            return str(s.get("text", "")).strip()
    return None


def perframe_detect(src, glitch_px=GLITCH_PX):
    """ПОКАДРОВЫЙ детект полосы субтитра автора по КАЖДОМУ кадру src.
    Возвращает (det, fps, N): det[i] = (cy,h,x0,x1,fresh). fresh=True если полоса
    реально найдена на этом кадре (не удержание). hold/glitch как в эталоне subs2."""
    import cv2
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    det, prev_er = [], None
    tracker = CaptionTracker(glitch_px=glitch_px)   # единый темпоральный сглаживатель
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        best, prev_er = detect_caption(fr, prev_er, 0, 0)
        sm, fresh = tracker.update(best)
        if sm is None:
            sm = (1200, 50, 240, 840)               # дефолт пока автор не появился
        det.append((sm, fresh))
    cap.release()
    return det, fps, len(det)


def perframe_cover(args, subs):
    """ЗАКОН 4 покадрово: на каждом кадре плашка под реальную пилюлю автора + наш текст.
    Плашка появляется когда активен наш cue ИЛИ когда субтитр автора реально на кадре
    (никогда не торчит); размер = пилюля автора + пара мм; позиция = детект автора."""
    import cv2
    from PIL import Image, ImageDraw
    vw, vh = probe_dims(args.src)
    split_wins = []
    if args.split_windows and os.path.isfile(args.split_windows):
        split_wins = [tuple(w) for w in json.load(open(args.split_windows))]

    det, fps, N = perframe_detect(args.src)
    font = _load_font(args.font_size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    stroke = max(2, args.font_size // 8)

    def tsz(s):
        bb = tmp.textbbox((0, 0), s, font=font, stroke_width=stroke)
        return bb[2] - bb[0], bb[3] - bb[1]

    def in_split(t):
        return any(a <= t < b for a, b in split_wins)

    # ─── КОНСИСТЕНТНАЯ ГЕОМЕТРИЯ (правка автора) ───────────────────
    # Правило автора дословно: «плашка должна быть консистентной, то есть не
    # увеличиваться, если у автора субтитры чуть разные. Не должна быть больше,
    # меньше, больше, меньше». Плашка НЕ широкая и НЕ узкая — она РОВНО одна
    # на весь ролик: размер считаем ОДИН раз по статистике ВСЕХ кадров
    # (покадровый детект остаётся — он двигает ПОЗИЦИЮ, но не габариты).
    # До правки ph/pw пересчитывались внутри цикла от (h,x0,x1) текущего кадра —
    # это и было «дышание» плашки, самый частый предмет браковок.
    _fresh = [(cy, h, x0, x1) for (cy, h, x0, x1), fr in det if fr]
    _stat = _fresh if _fresh else [d for d, _ in det]
    _hs = sorted(v[1] for v in _stat)
    _ws = sorted((v[3] - v[2]) for v in _stat)

    def _p90(seq):
        return seq[min(len(seq) - 1, int(round(0.90 * (len(seq) - 1))))] if seq else 0

    author_h = _p90(_hs)          # накрываем 90% полос автора, выбросы не растягивают
    author_w = _p90(_ws)
    all_txt = [tsz(s.get("text", ""))
               for s in (subs if isinstance(subs, list) else [])
               if s.get("text")]
    txt_w = max([t[0] for t in all_txt], default=0)   # самый длинный НАШ cue
    txt_h = max([t[1] for t in all_txt], default=0)

    PH_CONST = max(txt_h, author_h) + PLATE_PAD
    PW_CONST = min(max(txt_w + 150, author_w + 120, 540), 1060)
    print(f"[консистентная плашка] pw={PW_CONST} ph={PH_CONST} "
          f"(автор p90: h={author_h} w={author_w}; наш текст max: w={txt_w} h={txt_h}) "
          f"— размер ФИКСИРОВАН на весь ролик, меняется только позиция")

    ovdir = tempfile.mkdtemp(prefix="subcover_ov_")
    drawn = 0
    for i in range(N):
        t = i / fps
        (cy, h, x0, x1), fresh = det[i]
        text = _active_cue(subs, t)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if text or fresh:
            ph = PH_CONST                                     # НЕ от кадра — константа
            pw = PW_CONST                                     # НЕ от кадра — константа
            if in_split(t):
                seam = split_wins and SPLIT_SEAM_DEFAULT or SPLIT_SEAM_DEFAULT
                ptop = seam - ph                              # низ плашки прижат к шву
                pcy = ptop + ph // 2
            else:
                pcy = int(min(max(cy, 760), 1380))            # safe-zone, по детекту автора
                ptop = pcy - ph // 2
            d = ImageDraw.Draw(img)
            px = (W - pw) // 2
            d.rounded_rectangle([px, ptop, px + pw, ptop + ph], radius=26,
                                fill=(16, 16, 18, 255))       # непрозрачная тёмная
            if text:
                d.text((W // 2, ptop + ph // 2), text, font=font, anchor="mm",
                       fill=(255, 255, 255, 255), stroke_width=stroke,
                       stroke_fill=(0, 0, 0, 255))
            drawn += 1
        img.save(os.path.join(ovdir, f"f_{i:05d}.png"))

    cmd = [FFMPEG, "-y", "-v", "error", "-i", args.src,
           "-framerate", f"{fps:.4f}", "-start_number", "0",
           "-i", os.path.join(ovdir, "f_%05d.png"),
           "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
           "-map", "[v]", "-map", "0:a?",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-c:a", "aac", "-shortest", args.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL ffmpeg (perframe):\n", r.stderr[-2000:]); sys.exit(1)
    if not os.path.isfile(args.out) or os.path.getsize(args.out) < 1000:
        print("FAIL: выход пустой (perframe)"); sys.exit(1)
    print(f"OK (ПОКАДРОВО): {args.out} — {N} кадров, плашка на {drawn}, "
          f"движок=source_vision per-frame, fps={fps:.2f}")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--subs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plate-top", type=int, default=1085)
    ap.add_argument("--plate-bot", type=int, default=1540)
    ap.add_argument("--text-cy", type=int, default=1345)
    ap.add_argument("--plate-alpha", type=float, default=0.92)
    ap.add_argument("--font-size", type=int, default=56)
    ap.add_argument("--detect", action="store_true")
    ap.add_argument("--split-windows", default=None,
                    help="[[t0,t1],...] окна сплита — низ плашки к шву")
    ap.add_argument("--plate-window", choices=["full", "cues"], default="full")
    ap.add_argument("--max-karaoke-words", type=int, default=MAX_KARAOKE_WORDS,
                    help="макс слов в нашем караоке-cue (>порога = субтитр-абзац = FAIL)")
    args = ap.parse_args()

    if not os.path.isfile(args.src):
        print(f"FAIL: нет src {args.src}"); sys.exit(1)
    if not os.path.isfile(args.subs):
        print(f"FAIL: нет subs {args.subs}"); sys.exit(1)
    subs = json.load(open(args.subs))

    # ЗАКОН: караоке ≤3 слов  — не рендерим субтитр-абзац
    kok, kfails = check_karaoke_groups(subs, args.max_karaoke_words)
    if not kok:
        print("FAIL: караоке-инвариант нарушен (субтитр-абзац вместо группы ≤3 слов):")
        for f in kfails:
            print("  ✗", f)
        sys.exit(1)

    # ПОКАДРОВЫЙ путь (дефолт продакшена, ЗАКОН 4): плашка под реального автора на каждом кадре
    if args.detect:
        perframe_cover(args, subs)
        return  # perframe_cover делает sys.exit

    dur = probe_duration(args.src)
    if dur <= 0:
        print("FAIL: не определилась длительность src"); sys.exit(1)
    vw, vh = probe_dims(args.src)

    # сюда попадаем только в РУЧНОМ статичном режиме (без --detect): плашка по аргументам
    plate_top, plate_bot = args.plate_top, args.plate_bot

    # safe-zone clamp для нашего текста
    if args.text_cy > 1430:
        args.text_cy = 1430
    if args.text_cy < 310:
        args.text_cy = 310

    tmpdir = tempfile.mkdtemp(prefix="subcover_")
    plate_png = os.path.join(tmpdir, "plate.png")
    make_plate_png(plate_png, plate_top, plate_bot, args.plate_alpha)

    # окна, в которых нужна плашка
    if args.plate_window == "full":
        plate_windows = [(0.0, dur)]
    else:
        plate_windows = [tuple(w) for w in merge_windows(subs)]

    # собираем ffmpeg-команду
    inputs = ["-i", args.src]
    # плашка как зацикленный вход на всю длительность
    inputs += ["-loop", "1", "-framerate", "30", "-t", f"{dur:.3f}", "-i", plate_png]
    cue_pngs = []
    for i, s in enumerate(subs):
        cp = os.path.join(tmpdir, f"cue{i}.png")
        make_cue_png(cp, s["text"], args.text_cy, args.font_size)
        cue_pngs.append((cp, float(s["start"]), float(s["end"])))
        d_i = max(0.05, float(s["end"]) - float(s["start"]))
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{d_i:.3f}", "-i", cp]

    # filter_complex: base -> наложить плашку (в окнах) -> наложить cue (в их окнах)
    fc = []
    cur = "[0:v]"
    plate_idx = 1
    plate_enable = "+".join([f"between(t,{a:.3f},{b:.3f})" for a, b in plate_windows])
    fc.append(f"{cur}[{plate_idx}:v]overlay=0:0:enable='{plate_enable}'[vp]")
    cur = "[vp]"
    for j, (cp, st, en) in enumerate(cue_pngs):
        in_idx = 2 + j
        nxt = f"[vc{j}]"
        fc.append(f"{cur}[{in_idx}:v]overlay=0:0:enable='between(t,{st:.3f},{en:.3f})'{nxt}")
        cur = nxt
    fc_str = ";".join(fc)
    # последний label
    last = cur

    cmd = [FFMPEG, "-y", "-v", "error"] + inputs + [
        "-filter_complex", fc_str,
        "-map", last, "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-c:a", "aac", "-shortest", args.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL ffmpeg:\n", r.stderr[-2000:]); sys.exit(1)
    if not os.path.isfile(args.out) or os.path.getsize(args.out) < 1000:
        print("FAIL: выход пустой"); sys.exit(1)
    out_dur = probe_duration(args.out)
    print(f"OK: {args.out} ({out_dur:.2f}s) plate y[{plate_top}..{plate_bot}] "
          f"alpha={args.plate_alpha} text_cy={args.text_cy} windows={args.plate_window}")
    sys.exit(0)


if __name__ == "__main__":
    main()
