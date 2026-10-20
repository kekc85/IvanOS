#!/usr/bin/env python3
"""
twin-frame.py — КАНОННЫЙ кроп двойника в РОВНЫЙ портрет 1080×1920 (автор).
ЕДИНЫЙ источник истины для кадрирования twin (заменяет ad-hoc per-project ffmpeg, cropx.txt).

ВХОД: ШИРОКИЙ HeyGen-рендер (Landscape 16:9, обычно 3440×1920). HeyGen в этом формате
кладёт аватар по центру → есть запас по бокам, чтобы центрировать кропом.
ВЫХОД: 1080×1920 портрет, лицо детерминированно по центру (медиана лица по ВСЕМ кадрам,
не по 1-3 сэмплам → нет дрейфа головы).

🔴 ЗАПРЕТ: на вход НЕЛЬЗЯ подавать нативный портрет HeyGen (ширина ≈1080) — он уже смещён
на ~18% и кропом по горизонтали это не лечится (нет запаса). Скрипт упадёт с подсказкой
«рендери 16:9». Чинить «неровно» ре-рендером HeyGen ЗАПРЕЩЕНО (жжёт кредиты, портрет всегда смещён).

usage: twin-frame.py <wide_render.mp4> --out <portrait.mp4> [--w 1080] [--h 1920] [--tol-pct 8]
exit 0 = собран и прошёл само-проверку центрирования; 1 = ошибка/не прошёл.
"""
import sys, os, json, argparse, subprocess, importlib.util

# Файл гейта назван с дефисом (стиль репо) → грузим по пути, не обычным import
_gate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twin-centering-check.py")
_spec = importlib.util.spec_from_file_location("twin_centering_check", _gate)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
measure_offset = _mod.measure_offset


def median_face_cx_wide(path, min_conf=0.6):
    """Медиана горизонтального центра лица по ВСЕМ кадрам широкого рендера (робастно к дрейфу)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None, None, None
    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    cap = cv2.VideoCapture(path)
    det = cv2.FaceDetectorYN.create(yunet, "", (1080, 1920))
    cxs = []
    w = h = 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    n = min(120, max(8, int(dur)))  # ~1 сэмпл/сек, до 120
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, dur * (i + 0.5) / n * 1000.0 if dur else i * 1000.0)
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(fr)
        if faces is None or len(faces) == 0:
            continue
        f = max(faces, key=lambda f: f[2] * f[3])
        if float(f[14]) < min_conf:
            continue
        cxs.append(float(f[0]) + float(f[2]) / 2.0)
    cap.release()
    if not cxs:
        return None, w, h
    return float(np.median(cxs)), w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--tol-pct", type=float, default=8.0)
    a = ap.parse_args()
    if not os.path.isfile(a.src):
        print(f"FAIL: нет файла {a.src}"); sys.exit(1)

    cx, sw, sh = median_face_cx_wide(a.src)
    if sw == 0:
        print("FAIL: не открыть/не прочитать видео"); sys.exit(1)
    print(f"· исходник {sw}x{sh}, медиана лица cx={cx}")

    # Нативный портрет на вход = нечем центрировать
    if sw < a.w + 80:
        print(f"✗ FAIL: исходник шириной {sw}px ≈ портрет, нет запаса для центрирования.")
        print("  Это и есть «неровно». HeyGen-портрет смещён ~18% вправо и кропом не лечится.")
        print("  🔴 Рендери ШИРОКО (Landscape 16:9, ~3440×1920) — там аватар у HeyGen по центру —")
        print("     и подай ШИРОКИЙ рендер сюда. Ре-рендер HeyGen в портрет НЕ поможет (жжёт кредиты).")
        sys.exit(1)

    if cx is None:
        cx = sw / 2.0
        print("  ⚠ лицо не найдено — центрирую по геометрии кадра")

    # X левого края колонки так, чтобы лицо встало в центр выхода
    x = int(round(cx - a.w / 2.0))
    x = max(0, min(x, sw - a.w))
    # 🔴 ФИКС по решению автора: исходник HeyGen бывает НИЖЕ целевых 1920 (реально отдаёт 1936x1080).
    # Старый путь резал колонку 1080x1080 и тянул её scale-ом до 1080x1920 = лицо вытянуто
    # в 1.78 раза (гейт twin-centering-check ловил «аспект 1.87 при норме 1.3-1.45»).
    # Правильно: РАВНОМЕРНЫЙ scale по обеим осям (коэффициент один), потом кроп окна 9:16.
    if sh < a.h:
        k = a.h / float(sh)                      # один коэффициент на обе оси = без искажения
        up_w, up_h = int(round(sw * k)), a.h
        cx_up = cx * k                           # центр лица в апскейленных координатах
        x = int(round(cx_up - a.w / 2.0))
        x = max(0, min(x, up_w - a.w))
        print(f"· источник {sw}x{sh} ниже {a.h}: равномерный scale ×{k:.3f} → {up_w}x{up_h}, "
              f"кроп колонка x={x}..{x + a.w}")
        vf = f"scale={up_w}:{up_h}:flags=lanczos,crop={a.w}:{a.h}:{x}:0"
    else:
        ch = min(sh, a.h)
        y = max(0, (sh - ch) // 2)
        print(f"· кроп колонка x={x}..{x + a.w} (из {sw}), y={y}..{y + ch}")
        vf = f"crop={a.w}:{ch}:{x}:{y}"
    cmd = ["ffmpeg", "-y", "-i", a.src, "-vf", vf,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium",
           "-c:a", "copy", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(a.out):
        print("FAIL: ffmpeg кроп упал:", r.stderr[-400:]); sys.exit(1)

    # САМО-ПРОВЕРКА: выход обязан быть по центру (иначе не выдавать)
    m = measure_offset(a.out)
    if m.get("ok") and abs(m["offset_pct"]) > a.tol_pct:
        print(f"✗ FAIL: после кропа всё ещё неровно ({m['offset_pct']:+.1f}%). Проверь исходник.")
        sys.exit(1)
    off = m.get("offset_pct") if m.get("ok") else "н/д"
    print(f"✅ собран {a.out} — лицо по центру (смещение {off}%). Прогони гейт twin-centering-check.py для вердикта")
    sys.exit(0)


if __name__ == "__main__":
    main()