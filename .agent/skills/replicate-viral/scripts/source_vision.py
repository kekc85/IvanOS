#!/usr/bin/env python3
"""
source_vision.py — ЕДИНЫЙ ПОКАДРОВЫЙ ПРОХОД ЗРЕНИЯ (источник истины для всего скилла).

Корень (автор): «глаза» скилла моргали раз в секунду — foreign-face-gate
извлекал 3 кадра/сек слабой Haar-фронталкой (автор протекал между замерами),
subtitle-cover брал 9 сэмплов на весь ролик → медиана → ОДНА статичная плашка
(не попадала после 30с, торчал чужой субтитр, плашка то толстая то тонкая).
Покадровый код, который автор ПРИНЯЛ на <твой-прошлый-проект> (subs2.py / capdetect.py), жил
одноразово в папке проекта и умирал. Этот модуль поднимает его в скилл как ДВИЖОК:
читает КАЖДЫЙ кадр, темпорально-связно, и кормит и плашку, и гейт, и сегментацию.

Что считает на КАЖДОМ кадре:
  · faces      — YuNet (cv2.FaceDetectorYN) по ВСЕМУ кадру (профиль/наклон/частичное
                 лицо — то, что Haar-фронталка теряла); Haar-фолбэк если модель пропала.
  · top_skin   — доля кожи (HSV) в верхней зоне — ловит лоб/макушку автора там, где
                 детектор лица не сработал (правило по решению автора №1, протечка автора в верх).
  · caption    — полоса субтитра автора (cy,h,x0,x1): белый текст + эрозия (душит тонкий
                 UI) + ТЕМПОРАЛЬНЫЙ признак (караоке меняется покадрово → предпочесть
                 меняющуюся полосу статичному UID) — промотнуто из capdetect/subs2.
  · layout     — content (нет лица) / FULL (лицо в центре-верхе) / split (лицо в низу).

Темпоральная связность (не решения по одному кадру):
  · caption: удержание последней позиции при пропуске, отброс глитча (скачок > glitch_px);
  · author_present: дилатация присутствия автора в верхней зоне ±hold_frames (≈0.5с).

CLI:
  source_vision.py <video> [--out source-vision.json] [--no-faces] [--no-caption]
     [--step N] [--cap-ymin Y] [--cap-ymax Y] [--top-zone FRAC] [--glitch-px PX]
  --step N   : анализировать каждый N-й кадр (дефолт 1 = КАЖДЫЙ кадр). Поднимать >1
               только для очень длинных видео; гейт проверяет покрытие.

Также импортируется: analyze(), detect_caption(), load_yunet(), detect_faces(), skin_frac().
exit: 0 ok, 2 ошибка (нет видео / cv2).
"""
import os, sys, json, argparse

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YUNET_PATH = os.path.join(SKILL_DIR, "models", "yunet.onnx")

# --- параметры детекта субтитра (эталон capdetect.py, не менять без регресса) ---
WHITE_G = 205          # порог яркости белого текста
WHITE_CHROMA = 40      # |b-r|,|g-r| < этого = ахроматический (белый, не цветной UI)
ERODE_K = (3, 3)       # убивает тонкий UI-текст
CLOSE_K = (61, 5)      # сшивает буквы строки субтитра в полосу
MIN_W, MIN_H, MAX_H = 110, 24, 150
MIN_AR = 2.0           # w/h полосы субтитра
MIN_DENS = 0.10
GLITCH_PX = 260        # скачок центра полосы > этого = глитч → удержать прошлую
CAP_YMIN, CAP_YMAX = 0, 0  # 0 = вся высота (автор бывает full-frame, субтитр гуляет)

# --- HSV-кожа (ловит лоб/макушку автора в верхней панели) ---
SKIN_LO = (0, 30, 60)
SKIN_HI = (25, 170, 255)
SKIN_LO2 = (170, 30, 60)   # обёрнутый красный край тона кожи
SKIN_HI2 = (180, 170, 255)


def load_yunet(input_size=(320, 320), score=0.6, nms=0.3, topk=5000):
    """cv2.FaceDetectorYN на нашей модели. None если cv2/модель недоступны."""
    try:
        import cv2
    except ImportError:
        return None
    if not os.path.exists(YUNET_PATH):
        return None
    try:
        return cv2.FaceDetectorYN.create(YUNET_PATH, "", input_size, score, nms, topk)
    except Exception:
        return None


def _haar():
    import cv2
    p = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    c = cv2.CascadeClassifier(p)
    return None if c.empty() else c


def detect_faces(frame, yunet=None, haar=None, min_size=70):
    """Лица по ВСЕМУ кадру. YuNet (профиль/наклон/частичное) → фолбэк Haar.
    Возвращает [(x,y,w,h,score)] в координатах кадра."""
    import cv2
    h, w = frame.shape[:2]
    out = []
    if yunet is not None:
        try:
            yunet.setInputSize((w, h))
            _, faces = yunet.detect(frame)
            if faces is not None:
                for f in faces:
                    x, y, bw, bh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                    if bw >= min_size and bh >= min_size:
                        out.append((max(0, x), max(0, y), bw, bh, float(f[-1])))
            return out
        except Exception:
            pass
    if haar is not None:
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for (x, y, bw, bh) in haar.detectMultiScale(g, 1.1, 5, minSize=(min_size, min_size)):
            out.append((int(x), int(y), int(bw), int(bh), 1.0))
    return out


def skin_frac(frame, y0, y1, x0=None, x1=None):
    """Доля пикселей цвета кожи (HSV) в зоне [y0:y1, x0:x1]. 0..1."""
    import cv2, numpy as np
    h, w = frame.shape[:2]
    x0 = 0 if x0 is None else max(0, x0)
    x1 = w if x1 is None else min(w, x1)
    y0, y1 = max(0, y0), min(h, y1)
    if y1 <= y0 or x1 <= x0:
        return 0.0
    roi = frame[y0:y1, x0:x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array(SKIN_LO, np.uint8), np.array(SKIN_HI, np.uint8))
    m2 = cv2.inRange(hsv, np.array(SKIN_LO2, np.uint8), np.array(SKIN_HI2, np.uint8))
    m = cv2.bitwise_or(m1, m2)
    return float(cv2.countNonZero(m)) / float(roi.shape[0] * roi.shape[1])


def _white_erosion(frame, ymin, ymax):
    """Бинарная карта белого текста после эрозии (тонкий UI убит)."""
    import cv2, numpy as np
    b, gc, r = cv2.split(frame)
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    white = ((g > WHITE_G)
             & (np.abs(b.astype(int) - r.astype(int)) < WHITE_CHROMA)
             & (np.abs(gc.astype(int) - r.astype(int)) < WHITE_CHROMA)).astype("uint8") * 255
    white[:ymin, :] = 0
    if ymax:
        white[ymax:, :] = 0
    er = cv2.erode(white, cv2.getStructuringElement(cv2.MORPH_RECT, ERODE_K), iterations=1)
    return er


def detect_caption(frame, prev_er=None, ymin=0, ymax=0):
    """Полоса субтитра автора на ОДНОМ кадре, темпорально-взвешенная.
    Возвращает ((cy,h,x0,x1), er) или (None, er). prev_er — карта прошлого кадра:
    кандидат, который ИЗМЕНИЛСЯ относительно прошлого (караоке), получает буст —
    статичный UID той же яркости не перебивает живой субтитр (эталон subs2.py)."""
    import cv2, numpy as np
    h, w = frame.shape[:2]
    ymax = ymax or h
    er = _white_erosion(frame, ymin, ymax)
    d = cv2.morphologyEx(er, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_RECT, CLOSE_K))
    cnts, _ = cv2.findContours(d, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, bs = None, -1.0
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw < MIN_W or bh < MIN_H or bh > MAX_H or bw / max(bh, 1) < MIN_AR:
            continue
        patch = er[y:y + bh, x:x + bw]
        area = cv2.countNonZero(patch)
        if area / (bw * bh) < MIN_DENS:
            continue
        chg = 0.0
        if prev_er is not None:
            pp = prev_er[y:y + bh, x:x + bw]
            if pp.shape == patch.shape:
                chg = float(np.mean(cv2.absdiff(patch, pp))) / 255.0
        score = area * (0.25 + 2.0 * chg)   # живой (меняющийся) субтитр перебивает статику
        if score > bs:
            bs = score
            best = (y + bh // 2, bh, x, x + bw)
    return best, er


class CaptionTracker:
    """Темпоральный сглаживатель полосы субтитра. Решает дилемму глитч-vs-смена-сцены:
    одиночный скачок >glitch_px = глитч (держим прошлую позицию), но если новая позиция
    ДЕРЖИТСЯ accept_k кадров подряд = реальная смена сцены (принимаем). Без accept_k
    одиночный hold залипал навсегда на смене сцены (cy не догонял субтитр). Один класс
    на всех потребителей (subtitle-cover, source-vision) — единый источник истины."""

    def __init__(self, glitch_px=GLITCH_PX, accept_k=3, default=None):
        self.glitch_px = glitch_px
        self.accept_k = accept_k
        self.last = default
        self.pending = None
        self.pending_n = 0

    def update(self, best):
        """best = (cy,h,x0,x1) | None. Возвращает (smoothed | None, fresh: bool)."""
        if best is None:
            return self.last, False
        if self.last is None:
            self.last = best
            return best, True
        if abs(best[0] - self.last[0]) <= self.glitch_px:
            self.last = best
            self.pending = None
            self.pending_n = 0
            return best, True
        # далёкий скачок: копим подтверждение, что это смена сцены, а не глитч
        if self.pending is not None and abs(best[0] - self.pending[0]) <= self.glitch_px:
            self.pending_n += 1
        else:
            self.pending = best
            self.pending_n = 1
        if self.pending_n >= self.accept_k:
            self.last = self.pending
            self.pending = None
            self.pending_n = 0
            return self.last, True
        return self.last, False        # пока держим прошлую (возможный глитч)


def analyze(path, want_faces=True, want_caption=True, step=1,
            cap_ymin=CAP_YMIN, cap_ymax=CAP_YMAX, top_zone=0.5,
            glitch_px=GLITCH_PX, hold_frames=15, min_face=70):
    """ПОКАДРОВЫЙ проход. Возвращает dict с per-frame timeline + summary.
    step=1 → КАЖДЫЙ кадр (дефолт). top_zone — доля высоты сверху для скан-кожи автора."""
    try:
        import cv2
    except ImportError:
        raise RuntimeError("cv2 не установлен — покадровый проход невозможен")
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("видео не открылось: %s" % path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    yunet = load_yunet() if want_faces else None
    haar = _haar() if (want_faces and yunet is None) else None
    face_engine = "yunet" if yunet is not None else ("haar" if haar is not None else "none")
    top_y1 = int(H * top_zone)

    frames = []
    prev_er = None
    tracker = CaptionTracker(glitch_px=glitch_px)
    idx = 0
    n_read = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if step > 1 and (idx % step) != 0:
            idx += 1
            continue
        t = idx / fps
        rec = {"i": idx, "t": round(t, 3)}
        if want_faces:
            fc = detect_faces(fr, yunet, haar, min_face)
            rec["faces"] = [[x, y, w, h, round(s, 3)] for (x, y, w, h, s) in fc]
            rec["top_skin"] = round(skin_frac(fr, 0, top_y1), 4)
            # layout по самому крупному лицу
            if fc:
                bx = max(fc, key=lambda f: f[2] * f[3])
                fcy = bx[1] + bx[3] / 2.0
                rec["layout"] = "FULL" if fcy < H * 0.5 else "split"
            else:
                rec["layout"] = "content"
        if want_caption:
            best, prev_er = detect_caption(fr, prev_er, cap_ymin, cap_ymax)
            sm, _fresh = tracker.update(best)
            rec["cap"] = list(sm) if sm is not None else None
        frames.append(rec)
        idx += 1
        n_read += 1
    cap.release()

    # дилатация присутствия автора в верхней зоне ±hold_frames (запас ±0.5с)
    author_thr = 0.045
    if want_faces:
        raw = [(f.get("top_skin", 0.0) >= author_thr) or (f.get("layout") == "FULL")
               for f in frames]
        dil = list(raw)
        n = len(raw)
        for i in range(n):
            if raw[i]:
                for j in range(max(0, i - hold_frames), min(n, i + hold_frames + 1)):
                    dil[j] = True
        for i in range(n):
            frames[i]["author_top"] = bool(dil[i])

    summary = {
        "path": os.path.abspath(path),
        "fps": round(fps, 4), "w": W, "h": H,
        "n_frames_total": idx, "n_analyzed": n_read, "step": step,
        "face_engine": face_engine,
        "frames_with_face": sum(1 for f in frames if f.get("faces")),
        "frames_with_caption": sum(1 for f in frames if f.get("cap")),
        "frames_author_top": sum(1 for f in frames if f.get("author_top")),
        "layout_hist": {k: sum(1 for f in frames if f.get("layout") == k)
                        for k in ("content", "FULL", "split")},
    }
    return {"summary": summary, "frames": frames}


def cap_lookup(frames):
    """Хелпер для потребителей: функция t → (cy,h,x0,x1) ближайшего кадра."""
    import bisect
    ts = [f["t"] for f in frames]

    def look(t):
        i = bisect.bisect_left(ts, t)
        i = min(max(i, 0), len(frames) - 1)
        return frames[i].get("cap")
    return look


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-faces", action="store_true")
    ap.add_argument("--no-caption", action="store_true")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--cap-ymin", type=int, default=CAP_YMIN)
    ap.add_argument("--cap-ymax", type=int, default=CAP_YMAX)
    ap.add_argument("--top-zone", type=float, default=0.5)
    ap.add_argument("--glitch-px", type=int, default=GLITCH_PX)
    a = ap.parse_args()
    if not os.path.isfile(a.video):
        print("FAIL: нет видео %s" % a.video); return 2
    try:
        res = analyze(a.video, want_faces=not a.no_faces, want_caption=not a.no_caption,
                      step=a.step, cap_ymin=a.cap_ymin, cap_ymax=a.cap_ymax,
                      top_zone=a.top_zone, glitch_px=a.glitch_px)
    except RuntimeError as e:
        print("FAIL: %s" % e); return 2
    out = a.out or (os.path.splitext(a.video)[0] + ".source-vision.json")
    json.dump(res, open(out, "w"), ensure_ascii=False)
    s = res["summary"]
    print("OK source-vision: %s" % out)
    print("  %d кадров проанализировано (step=%d, fps=%.2f, движок лиц=%s)"
          % (s["n_analyzed"], s["step"], s["fps"], s["face_engine"]))
    print("  лица=%d  субтитр=%d  автор-в-верху=%d  layout=%s"
          % (s["frames_with_face"], s["frames_with_caption"],
             s["frames_author_top"], s["layout_hist"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())