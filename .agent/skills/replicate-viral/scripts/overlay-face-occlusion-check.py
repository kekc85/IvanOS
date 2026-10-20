#!/usr/bin/env python3
"""
overlay-face-occlusion-check.py — машинный гейт «ТЕКСТ НЕ НА ЛИЦЕ» (H1-окклюзия).

ПРЕЦЕДЕНТ (автор, reel-DaIcYfeIpr6): «снова там субтитры у меня на лице...
удали это на хер». Корень: позиция CTA-блока скопирована у автора-источника (верх кадра),
но у автора в том кадре лицо в углу, а наш двойник анфас по центру → текст лёг на лицо.
Класс трижды пропущен ГЛАЗАМИ (дефект был виден на проверочной панели). Отсюда закон:
позиция текста источника НЕ переносится слепо — каждый cue сверяется с лицом НАШЕГО кадра
ЧИСЛОМ (ERROR-REGISTER #16).

Меряет: для каждого cue (png-оверлей, кадры n0..n1) — пересечение плотного alpha-bbox
текста (alpha>200) с bbox лица (YuNet) на 3 кадрах окна (начало/середина/конец).
  пересечение > 2% площади лица  → FAIL (текст на лице)
  лицо не найдено ни на одном проверочном кадре ни одного cue → FAIL (проверка пустая,
  не считается PASS — прецедент этой же сессии: POS_FRAMES-сиды давали face=None и
  фиктивный «PASS»)

usage:
  overlay-face-occlusion-check.py --render <final.mp4> --cues <cues.json> [--fps 25] [--max-overlap 0.02]
  cues.json = [["overlays/hook_a.png", 0, 23], ["overlays/cta_b.png", 227, 312], ...]
    (png может лежать относительно cwd или рядом с render)
exit 0 = PASS, 1 = FAIL, 2 = usage/ошибка ввода.
Пишет <render_dir>/.occlusion-verdict.json (verdict, per-cue метрики).

Фуллскрин-вставки (карточки, непрозрачный фон по всему кадру) в cues.json НЕ включать —
они законно закрывают двойника целиком, это не окклюзия текстом.
"""
import sys, os, json, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--cues", required=True, help="JSON: [[png, frame0, frame1], ...]")
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--max-overlap", type=float, default=0.02,
                    help="доля площади лица, перекрытая текстом, выше = FAIL")
    a = ap.parse_args()
    if not os.path.isfile(a.render):
        print(f"FAIL: нет файла {a.render}"); sys.exit(2)
    try:
        cues = json.load(open(a.cues))
    except Exception as e:
        print(f"FAIL: не читается cues.json: {e}"); sys.exit(2)
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError as e:
        print(f"FAIL: нет зависимости ({e}) — гейт обязателен, поставь cv2/PIL"); sys.exit(2)

    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    if not os.path.isfile(yunet):
        print(f"FAIL: нет модели YuNet: {yunet}"); sys.exit(2)
    det = cv2.FaceDetectorYN.create(yunet, "", (320, 320), 0.6, 0.3, 5000)  # порог 0.6 как twin-centering: дефолт 0.9 терял лицо на CTA-кадрах (прецедент калибровки)
    cap = cv2.VideoCapture(a.render)
    if not cap.isOpened():
        print("FAIL: не открыть видео"); sys.exit(2)

    rdir = os.path.dirname(os.path.abspath(a.render)) or "."
    rows, fails, faces_seen = [], [], 0
    for item in cues:
        png, n0, n1 = item[0], int(item[1]), int(item[2])
        p = png if os.path.isfile(png) else os.path.join(rdir, png)
        if not os.path.isfile(p):
            fails.append(f"{png}: файл оверлея не найден"); continue
        alpha = np.asarray(Image.open(p).split()[3])
        ys, xs = np.where(alpha > 200)
        if len(xs) == 0:
            rows.append({"cue": os.path.basename(png), "note": "пустой оверлей", "overlap": 0.0}); continue
        tx0, ty0, tx1, ty1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        worst, fbox = 0.0, None
        # по ВРЕМЕНИ (POS_MSEC): POS_FRAMES на этом кодеке давал пустые детекты (прецедент)
        for n in (n0 + 1, (n0 + n1) // 2, max(n0 + 1, n1 - 1)):
            cap.set(cv2.CAP_PROP_POS_MSEC, n / a.fps * 1000.0)
            ok, fr = cap.read()
            if not ok:
                continue
            det.setInputSize((fr.shape[1], fr.shape[0]))
            _, f = det.detect(fr)
            if f is None or len(f) == 0:
                continue
            x, y, w, h = [float(v) for v in f[0][:4]]
            faces_seen += 1
            ix = max(0.0, min(x + w, tx1) - max(x, tx0))
            iy = max(0.0, min(y + h, ty1) - max(y, ty0))
            ov = ix * iy / max(1.0, w * h)
            if ov > worst or fbox is None:
                worst = max(ov, worst)
                fbox = [int(x), int(y), int(w), int(h)]
        rows.append({"cue": os.path.basename(png), "frames": [n0, n1],
                     "text_bbox": [tx0, ty0, tx1, ty1], "face_bbox": fbox,
                     "overlap": round(worst, 4)})
        if worst > a.max_overlap:
            fails.append(f"{os.path.basename(png)} (кадры {n0}-{n1}): текст перекрывает лицо на "
                         f"{worst*100:.1f}% (> {a.max_overlap*100:.0f}%) — текст в свободную зону, "
                         f"позицию источника НЕ переносить слепо (ERROR-REGISTER #16)")
    cap.release()
    if faces_seen == 0 and rows:
        fails.append("лицо не найдено НИ на одном проверочном кадре — проверка пустая, не PASS "
                     "(не та дорожка / битые сиды кадров)")
    verdict = "FAIL" if fails else "PASS"
    out = {"verdict": verdict, "render": os.path.basename(a.render),
           "max_overlap": a.max_overlap, "fails": fails, "cues": rows}
    try:
        json.dump(out, open(os.path.join(rdir, ".occlusion-verdict.json"), "w"),
                  ensure_ascii=False, indent=2)
    except Exception:
        pass
    print(f"========== OVERLAY-FACE-OCCLUSION: {verdict} ==========")
    for r in rows:
        print(f"  · {r['cue']:16} overlap={r.get('overlap',0)*100:.1f}% face={r.get('face_bbox')}")
    for f in fails:
        print("  ✗", f)
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
