#!/usr/bin/env python3
"""
draw_subs.py v2 - золотой all-caps Hormozi karaoke (Submagic-стиль).

Usage:
    draw_subs.py <subs.json> <in.mp4> <out.mp4> [--font-size 86] [--margin-v 290]

subs.json = [{"start": 1.23, "end": 2.5, "text": "ДВА СЛОВА",
              "words": [{"w":"ДВА","t0":1.23,"t1":1.6},{"w":"СЛОВА","t0":1.6,"t1":2.5}]}, ...]
"words" опционален - без него один статичный PNG на весь интервал группы (обратная
совместимость со старым subs.json без пословных таймингов).

Важно про среду: локальная сборка ffmpeg (из PATH; на Mac обычно homebrew, на Windows - winget)
собрана БЕЗ libass и без freetype/fontconfig - фильтров "ass" и "subtitles"
и даже "drawtext" в ней нет (проверено -filters). Поэтому вместо прожига через
.ass/libass рендерим субтитры сами через PIL в PNG с альфа-каналом и накладываем
через фильтр overlay с enable=between(t,start,end) - он есть в базовой сборке.

Караоке-механика: на каждую группу слов рендерится N PNG (N = число слов в группе,
максимум 2 по канону make_subs.py v2) - весь текст группы одной строкой, но в варианте
k активное слово k залито золотым, остальные белым. Overlay-цепочка переключает PNG
варианта ровно на границе слова (enable=between(t, wk_start, wk_end)), это и даёт
эффект бегущей золотой заливки слово-за-словом (Hormozi/Submagic karaoke).

Рядом с out кладём .ass файл как читаемый артефакт таймингов (не участвует в рендере,
по группам как раньше) - упрощает ручную сверку.
"""

import sys
import json
import subprocess
import argparse
import os
import tempfile
import shutil
from PIL import Image, ImageDraw, ImageFont

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

CANVAS_W = 1080
CANVAS_H = 1920

GOLD = (255, 201, 60, 255)
WHITE = (255, 255, 255, 255)

FONT_CANDIDATES = [
    # Oswald-Bold - канон Hormozi-класса (Г6) С КИРИЛЛИЦЕЙ, основной для русской дорожки
    os.path.expanduser("~/.claude/skills/talking-head-replica/fonts/Oswald-Bold.ttf"),
    # Anton - тот же класс, но БЕЗ кириллицы (детект глифов откатит на Oswald)
    os.path.expanduser("~/.claude/skills/talking-head-replica/fonts/anton.ttf"),
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    os.path.expanduser("~/Library/Fonts/Nunito-VF.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def sec_to_ass_time(sec):
    """Секунды -> формат ASS H:MM:SS.cc (сотые доли секунды)."""
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    cs = int(round((s - int(s)) * 100))
    s = int(s)
    if cs >= 100:
        cs -= 100
        s += 1
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        h += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass_text(text):
    """Экранирование спецсимволов ASS: { } \\ и убрать переводы строк (для читаемого .ass рядом)."""
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return text


def build_ass_sidecar(subs, out_ass_path, font_size, margin_v):
    """Читаемый .ass рядом с результатом - тайминги+стиль по группам для сверки, в рендере не используется."""
    header = f"""[Script Info]
Title: draw_subs v2
ScriptType: v4.00+
PlayResX: {CANVAS_W}
PlayResY: {CANVAS_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Anton,{font_size},&H00FFFFFF,&H003CC9FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for item in subs:
        start = sec_to_ass_time(float(item["start"]))
        end = sec_to_ass_time(float(item["end"]))
        text = escape_ass_text(item["text"])
        lines.append(f"Dialogue: 0,{start},{end},Default,0,0,0,{text}")

    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines))
        f.write("\n")


def _font_path_for_text(text):
    """Anton (первый кандидат) - латиница+цифры, БЕЗ кириллицы (проверено: cmap пуст
    для А-Я). Канон требует Anton как основной шрифт золотого караоке, но текст
    субтитров идёт на русском - поэтому детектим покрытие глифов и откатываемся
    на первый кандидат из fallback-списка (Nunito, кириллицу покрывает), если
    Anton не может отрисовать хотя бы один символ текста. Для латинских тестовых
    прогонов Anton работает как основной без отката."""
    for path in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            probe = ImageFont.truetype(path, 40)
        except Exception:
            continue
        # PIL/FreeType: getmask даёт пустую маску для отсутствующих в cmap глифов
        # (не считая пробела) - используем это как дешёвый тест покрытия без fonttools
        missing = False
        try:
            from fontTools.ttLib import TTFont
            cmap = TTFont(path).getBestCmap()
            for ch in text:
                if ch == " ":
                    continue
                if ord(ch) not in cmap:
                    missing = True
                    break
        except Exception:
            missing = False  # fonttools недоступен - доверяем первому кандидату
        if not missing:
            return path
    return FONT_CANDIDATES[0]


def load_font(size, font_path=None):
    """Загрузить шрифт по явному пути (font_path) или первый доступный кандидат.
    Anton - готовый ttf не вариативный, set_variation не требуется; для старых
    fallback-кандидатов (вариативный Nunito) пробуем выставить Bold, если шрифт
    этого не поддерживает - тихо игнорируем."""
    paths = [font_path] if font_path else FONT_CANDIDATES
    for path in paths:
        if path and os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                try:
                    font.set_variation_by_name("Bold")
                except Exception:
                    pass  # не вариативный шрифт (напр. Anton) - оставляем как есть
                return font
            except Exception:
                continue
    raise RuntimeError("не найден ни один шрифт из FONT_CANDIDATES")


def fit_font_size(draw, text, start_size, max_width, font_path=None):
    """Уменьшать размер шрифта пошагово (шаг 2px), пока строка не влезет в max_width.
    Никогда не переносим на 2 строки - вертикальный блок = брак «три этажа»."""
    size = start_size
    while size > 10:
        font = load_font(size, font_path)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font, size
        size -= 2
    return load_font(10), 10


def render_karaoke_png(words_line, active_idx, font_size, margin_v, out_png):
    """
    Отрисовать одну строку группы (nowrap, все слова через пробел) на прозрачном
    холсте 1080x1920. Слово active_idx залито золотым, остальные белым.
    У всех слов чёрная обводка (радиус 7, круговой сдвиг) + тень (offset 3, alpha 170).
    БЕЗ плашки-подложки. Низ-центр: нижний край текста на CANVAS_H - margin_v.
    words_line: список строк-слов (уже UPPERCASE, без пунктуации на конце).
    """
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    max_width = CANVAS_W - 2 * 40  # margin 40 слева/справа
    full_text = " ".join(words_line)

    font_path = _font_path_for_text(full_text)
    font, font_size = fit_font_size(draw, full_text, font_size, max_width, font_path)

    outline_r = 7
    shadow_offset = 3
    shadow_alpha = 170

    # высота строки КОНСТАНТНАЯ из метрик шрифта (ascent+descent), не из bbox текста -
    # bbox зависит от букв с выносами и дал бы дрожание базовой линии между кадрами
    ascent, descent = font.getmetrics()
    line_h = ascent + descent

    bbox_full = draw.textbbox((0, 0), full_text, font=font)
    line_w = bbox_full[2] - bbox_full[0]

    bottom_y = CANVAS_H - margin_v
    y = bottom_y - line_h
    x0 = (CANVAS_W - line_w) // 2

    # считаем x каждого слова по ширине "слово " накопительно (пробел = ширина пробела шрифта)
    space_w = draw.textlength(" ", font=font)
    x = x0
    for i, w in enumerate(words_line):
        color = GOLD if i == active_idx else WHITE
        # тень
        draw.text((x + shadow_offset, y + shadow_offset), w, font=font,
                   fill=(0, 0, 0, shadow_alpha))
        # обводка кругом
        for dx in range(-outline_r, outline_r + 1):
            for dy in range(-outline_r, outline_r + 1):
                if dx * dx + dy * dy > outline_r * outline_r:
                    continue
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), w, font=font, fill=(0, 0, 0, 255))
        # заливка поверх обводки
        draw.text((x, y), w, font=font, fill=color)
        w_width = draw.textlength(w, font=font)
        x += w_width + space_w

    canvas.save(out_png)


def has_audio_stream(video_path):
    """Проверить наличие аудио-дорожки во входном видео."""
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def get_duration(video_path):
    """Длительность видео в секундах через ffprobe."""
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    out = result.stdout.strip()
    if not out:
        raise RuntimeError(f"не удалось получить длительность: {video_path}")
    return float(out)


def build_group_variants(item, tmp_dir, group_idx, font_size, margin_v):
    """
    Построить список (png_path, enable_start, enable_end) для одной группы субтитра.
    Если у группы есть "words" - N вариантов (N = число слов), каждое окно enable
    берётся из пословных таймингов (стык слово-в-слово внутри группы). Иначе один
    статичный PNG на весь интервал группы (обратная совместимость).
    """
    variants = []
    words = item.get("words")
    if not words:
        png_path = os.path.join(tmp_dir, f"g{group_idx:03d}_static.png")
        render_karaoke_png(item["text"].split(), -1, font_size, margin_v, png_path)
        variants.append((png_path, float(item["start"]), float(item["end"])))
        return variants

    words_line = [w["w"] for w in words]
    n = len(words_line)
    for k in range(n):
        png_path = os.path.join(tmp_dir, f"g{group_idx:03d}_w{k}.png")
        render_karaoke_png(words_line, k, font_size, margin_v, png_path)
        wk_start = float(item["start"]) if k == 0 else float(words[k]["t0"])
        wk_end = float(item["end"]) if k == n - 1 else float(words[k + 1]["t0"])
        variants.append((png_path, wk_start, wk_end))
    return variants


def main():
    parser = argparse.ArgumentParser(description="Золотой word-by-word karaoke без подложки")
    parser.add_argument("subs_json")
    parser.add_argument("in_mp4")
    parser.add_argument("out_mp4")
    parser.add_argument("--font-size", type=int, default=86)
    parser.add_argument("--margin-v", type=int, default=290)
    args = parser.parse_args()

    if not os.path.exists(args.in_mp4):
        print(f"ОШИБКА: входное видео не найдено: {args.in_mp4}", file=sys.stderr)
        sys.exit(1)

    with open(args.subs_json, "r", encoding="utf-8") as f:
        subs = json.load(f)

    if not isinstance(subs, list) or len(subs) == 0:
        print("ОШИБКА: subs.json должен быть непустым массивом", file=sys.stderr)
        sys.exit(1)

    # sidecar .ass для читаемости/сверки таймингов вручную (по группам, как раньше)
    ass_path = os.path.splitext(args.out_mp4)[0] + ".ass"
    build_ass_sidecar(subs, ass_path, args.font_size, args.margin_v)

    tmp_dir = tempfile.mkdtemp(prefix="draw_subs_")
    try:
        cmd = [FFMPEG, "-y", "-i", args.in_mp4]

        filter_parts = []
        last_label = "0:v"
        input_idx = 1
        overlay_idx = 0
        for group_idx, item in enumerate(subs):
            variants = build_group_variants(item, tmp_dir, group_idx, args.font_size, args.margin_v)
            for png_path, wk_start, wk_end in variants:
                cmd += ["-i", png_path]
                out_label = f"v{overlay_idx}"
                filter_parts.append(
                    f"[{last_label}][{input_idx}:v]overlay=0:0:enable='between(t,{wk_start},{wk_end})'[{out_label}]"
                )
                last_label = out_label
                input_idx += 1
                overlay_idx += 1

        filter_complex = ";".join(filter_parts)

        cmd += ["-filter_complex", filter_complex, "-map", f"[{last_label}]"]

        audio_present = has_audio_stream(args.in_mp4)
        if audio_present:
            cmd += ["-map", "0:a", "-c:a", "copy"]

        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
        cmd.append(args.out_mp4)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("ОШИБКА ffmpeg:", file=sys.stderr)
            print(result.stderr[-3000:], file=sys.stderr)
            sys.exit(1)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # самопроверка: файл существует и длительность совпадает с входной ±0.2с
    if not os.path.exists(args.out_mp4) or os.path.getsize(args.out_mp4) == 0:
        print(f"ОШИБКА: выходной файл не создан или пуст: {args.out_mp4}", file=sys.stderr)
        sys.exit(1)

    try:
        in_dur = get_duration(args.in_mp4)
        out_dur = get_duration(args.out_mp4)
    except RuntimeError as e:
        print(f"ОШИБКА: {e}", file=sys.stderr)
        sys.exit(1)

    if abs(in_dur - out_dur) > 0.2:
        print(f"ОШИБКА: длительность разошлась: вход {in_dur:.2f}с, выход {out_dur:.2f}с", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {args.out_mp4} (длительность {out_dur:.2f}с, ass={ass_path})")


if __name__ == "__main__":
    main()
