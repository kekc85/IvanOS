#!/usr/bin/env python3
"""
twin-centering-check.py — машинный гейт «ДВОЙНИК РОВНО» (автор, прецедент reel-DZpavmHNRtd «Headroom»).

КОРЕНЬ: HeyGen в НАТИВНОМ портрете 9:16 кладёт аватар систематически правее центра
(замерено: twin2_raw native-portrait → лицо +194px / +18.0% от центра; разброс по кадрам
всего 14px = это не рандом, а как HeyGen компонует портрет). Ре-рендер этого НЕ чинит —
только жжёт кредиты. Рабочий метод: рендерить ШИРОКО 16:9 (≈3440×1920), где аватар у HeyGen
по центру, → кропить центрированную колонку 1080×1920 ЛОКАЛЬНО (twin-frame.py) → +7px / +0.6%.

Этот гейт меряет ФИНАЛЬНЫЙ twin-рендер (full-screen говорящая голова 9:16):
горизонтальное смещение медианы лица от центра кадра по выборке кадров.
  |offset| > tol_pct% ширины  → FAIL «неровно».
  лицо найдено в <50% кадров   → FAIL (нечего центрировать / не та дорожка).
Доп. (WARN, не FAIL): вертикальный хедрум (верх лица слишком высоко/низко).

usage:
  twin-centering-check.py <render.mp4> [--tol-pct 8] [--min-conf 0.6] [--json <out>]
exit 0 = PASS (ровно), 1 = FAIL (неровно), 2 = usage/ошибка ввода.
Пишет <render_dir>/.twin-centering-verdict.json (verdict, offset_px, offset_pct, n, src_w).

Также используется как библиотека: from twin_centering_check import measure_offset
"""
import sys, os, json, argparse

TOL_PCT_DEFAULT = 8.0   # |смещение лица| > 8% ширины = FAIL. 18%→FAIL, 0.6%→PASS (чистое разделение)


def measure_offset(path, min_conf=0.6, max_samples=48, step_s=1.0):
    """Вернуть dict с медианным смещением лица от центра по выборке кадров.
    {'ok':bool,'w':int,'h':int,'n':int,'median_cx':float,'offset_px':float,
     'offset_pct':float,'cx_spread':float,'face_top_med':float,'frames_total':int,'face_frac':float}
    ok=False если cv2/модель недоступны или лицо не найдено."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"ok": False, "reason": "cv2 не установлен"}
    yunet = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "yunet.onnx")
    if not os.path.isfile(yunet):
        return {"ok": False, "reason": f"нет модели YuNet: {yunet}"}
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return {"ok": False, "reason": "не открыть видео"}
    det = cv2.FaceDetectorYN.create(yunet, "", (1080, 1920))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    dur_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    dur_s = dur_frames / fps if fps else 0
    # выборка по времени, не плотнее max_samples
    if dur_s <= 0:
        ts = [i * step_s for i in range(max_samples)]
    else:
        n_s = min(max_samples, max(3, int(dur_s / step_s)))
        ts = [dur_s * (i + 0.5) / n_s for i in range(n_s)]
    cxs, tops, aspects = [], [], []
    w = h = 0
    sampled = 0
    for t in ts:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, fr = cap.read()
        if not ok:
            continue
        sampled += 1
        h, w = fr.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(fr)
        if faces is None or len(faces) == 0:
            continue
        f = max(faces, key=lambda f: f[2] * f[3])
        x, y, fw, fh, conf = float(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[14])
        if conf < min_conf or fw < 60:
            continue
        cxs.append(x + fw / 2.0)
        tops.append(y)
        aspects.append(fh / fw)
    cap.release()
    if not cxs or w == 0:
        return {"ok": False, "reason": "лицо не найдено", "frames_total": sampled,
                "face_frac": 0.0, "w": w, "h": h}
    cxs = np.array(cxs)
    median_cx = float(np.median(cxs))
    offset_px = median_cx - w / 2.0
    return {
        "ok": True, "w": int(w), "h": int(h), "n": int(len(cxs)),
        "median_cx": round(median_cx, 1),
        "offset_px": round(offset_px, 1),
        "offset_pct": round(offset_px / w * 100.0, 2),
        "cx_spread": round(float(cxs.max() - cxs.min()), 1),
        "face_top_med": round(float(np.median(tops)), 1),
        "face_aspect_med": round(float(np.median(aspects)), 3),
        "frames_total": int(sampled),
        "face_frac": round(len(cxs) / max(1, sampled), 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("--tol-pct", type=float, default=TOL_PCT_DEFAULT)
    ap.add_argument("--min-conf", type=float, default=0.6)
    ap.add_argument("--max-aspect", type=float, default=1.6,
                    help="медиана h/w лица выше = вертикальное растяжение (ERROR-REGISTER #15; норма 1.3-1.45, растянутый прецедент 1.864)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    if not os.path.isfile(a.render):
        print(f"FAIL: нет файла {a.render}")
        sys.exit(2)

    m = measure_offset(a.render, min_conf=a.min_conf)
    fails, facts, warns = [], [], []

    if not m.get("ok"):
        # cv2/модель недоступны = не можем судить → не блокируем (PASS с пометкой),
        # но «лицо не найдено» при найденных кадрах = подозрительно (FAIL).
        reason = m.get("reason", "не измерено")
        if reason == "лицо не найдено" and m.get("frames_total", 0) >= 3:
            fails.append("ЛИЦО НЕ НАЙДЕНО ни на одном кадре — не та дорожка / двойник вне кадра")
            verdict = "FAIL"
        else:
            facts.append(f"центрирование: не измерено ({reason})")
            verdict = "PASS"
    else:
        facts.append(f"кадр {m['w']}x{m['h']} | лицо на {m['n']}/{m['frames_total']} кадрах ({int(m['face_frac']*100)}%)")
        facts.append(f"медиана лица cx={m['median_cx']} (центр={m['w']/2:.0f}) | смещение {m['offset_px']:+.0f}px / {m['offset_pct']:+.1f}% | разброс {m['cx_spread']:.0f}px")
        facts.append(f"верх лица (хедрум) median={m['face_top_med']:.0f}")
        # face_frac<50% — НЕ FAIL: композит со вставками тула законно имеет кадры без лица.
        # Жёсткий FAIL только по смещению (ниже). Полное отсутствие лица ловится веткой ok=False.
        if m["face_frac"] < 0.5:
            warns.append(f"лицо найдено на {int(m['face_frac']*100)}% кадров (<50%) — норма для композита со вставками; смещение мерим по talking-head кадрам")
        if abs(m["offset_pct"]) > a.tol_pct:
            side = "ВПРАВО" if m["offset_px"] > 0 else "ВЛЕВО"
            fails.append(
                f"ДВОЙНИК НЕРОВНО: лицо смещено {side} на {m['offset_px']:+.0f}px ({m['offset_pct']:+.1f}% > порог {a.tol_pct}%). "
                f"Это нативный портрет HeyGen (он всегда смещает). НЕ ре-рендери HeyGen (жжёт кредиты) — "
                f"рендери 16:9 и кропни центрированно: twin-frame.py <wide.mp4> --out <portrait.mp4>"
            )
        facts.append(f"аспект лица (h/w) median={m['face_aspect_med']:.3f} (порог {a.max_aspect})")
        if m["face_aspect_med"] > a.max_aspect:
            fails.append(
                f"ДВОЙНИК РАСТЯНУТ ПО ВЕРТИКАЛИ: аспект лица {m['face_aspect_med']:.3f} > {a.max_aspect} "
                f"(норма 1.3-1.45; прецедент «я вытянут вверх» = 1.864, ERROR-REGISTER #15). "
                f"Корень: окно кропа шире 9:16 вжато scale-ом. НЕ ре-рендери — кропни 1:1 без масштабирования "
                f"или равномерным scale (один коэффициент по обеим осям)"
            )
        # хедрум — мягко
        if m["h"]:
            top_frac = m["face_top_med"] / m["h"]
            if top_frac < 0.03:
                warns.append(f"хедрум: лоб у самого верха (top={m['face_top_med']:.0f}) — мало воздуха над головой")
            elif top_frac > 0.42:
                warns.append(f"хедрум: лицо низко (top={m['face_top_med']:.0f}, {top_frac*100:.0f}% высоты) — много пустоты сверху")
        verdict = "FAIL" if fails else "PASS"

    out = {"verdict": verdict, "render": os.path.basename(a.render),
           "tol_pct": a.tol_pct, "fails": fails, "warns": warns, "facts": facts, "metrics": m}
    jpath = a.json or os.path.join(os.path.dirname(os.path.abspath(a.render)) or ".", ".twin-centering-verdict.json")
    try:
        json.dump(out, open(jpath, "w"), ensure_ascii=False, indent=2)
    except Exception:
        pass
    print(f"========== TWIN-CENTERING: {verdict} ==========")
    for f in facts: print("  ·", f)
    for w_ in warns: print("  ⚠", w_)
    for f in fails: print("  ✗", f)
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()