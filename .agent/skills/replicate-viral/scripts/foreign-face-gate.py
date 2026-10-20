#!/usr/bin/env python3
"""
foreign-face-gate.py — ГЕЙТ «двойник ВЕЗДЕ, чужого лица нет» (AC2, автор).

Прецедент: реплика уходила с ЧУЖИМ автором в кадре вместо двойника автора, ИЛИ
двойника вообще не вставляли там, где у эталона говорящая голова. Машина это не
ловила (face-detect по выходу не делался). Этот гейт закрывает обе дыры:

  (A) ЧУЖОЕ ЛИЦО.  Любое лицо в выходном mp4 ОБЯЗАНО попадать в окно бита, который
      помечен как AVATAR-сегмент (двойник автора: layout∈{full-head,split} и сегмент
      НЕ source-passthrough). Лицо вне avatar-окна = почти наверняка чужой автор из
      source-passthrough футажа → FAIL с таймкодами.
  (B) НЕТ ДВОЙНИКА.  Если в спеке объявлен avatar-сегмент (layout∈{full-head,split}),
      а в его временном окне в выходе ВООБЩЕ нет лиц → двойника не вставили → FAIL.

Детект (0.0, ПОКАДРОВО): source_vision.detect_faces на КАЖДОМ кадре (FACE_FPS=0)
через YuNet (cv2.FaceDetectorYN) — ловит профиль/наклон/частичное лицо, что Haar-фронталка
теряла (автор протекал между 3 редкими замерами). Раньше: ffmpeg fps=3 + Haar-фронталка —
именно тот «скриншот раз в секунду», на который ловились утечки автора. FACE_FPS>0 оставлен
как ручное прореживание для очень длинных видео; дефолт 0 = нативный fps (каждый кадр).

Вход:
  foreign-face-gate.py <render.mp4> <scene.spec.json | project-meta.json> [project_root]

Окна аватара определяются из beats спеки:
  beat.layout ∈ {full-head, split} (нормализуется через layout_enum, алиасы учтены)
  И НЕ beat.source_passthrough==true  → это окно ДВОЙНИКА.
  (project-meta.json тоже принимается — если в нём есть beats[] или segments[] с t0/t1.)

Калибровка: FACE_MINSIZE (px, дефолт 120), FACE_FPS (дефолт 0 = каждый кадр; >0 = прореживание),
FACE_SCORE (YuNet score, дефолт 0.6). Порог «есть лицо в окне» = ≥1 кадр окна с лицом.

exit: 0 = PASS (ok), 2 = FAIL (block). Пишет <dir>/.foreign-face-verdict.json.
Урок: гейт = exit 0/2, НЕ 1.
"""
import json, os, sys, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout_enum import normalize as layout_norm, DYNAMIC_LAYOUTS
import source_vision

AVATAR_LAYOUTS = set(DYNAMIC_LAYOUTS)  # full-head, split = раскладки, несущие спикера/двойника
FACE_MINSIZE = int(os.environ.get("FACE_MINSIZE", "120"))
FACE_FPS = float(os.environ.get("FACE_FPS", "0"))   # 0 = КАЖДЫЙ кадр (нативный fps)
FACE_SCORE = float(os.environ.get("FACE_SCORE", "0.6"))


def fail(msg, verdict_path=None, extra=None):
    print("FAIL: %s" % msg)
    if verdict_path:
        out = {"verdict": "FAIL", "reason": msg}
        if extra:
            out.update(extra)
        try:
            json.dump(out, open(verdict_path, "w"), ensure_ascii=False, indent=1)
        except Exception:
            pass
    return 2


def ffprobe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:
        return None


def load_avatar_windows(spec):
    """Из beats спеки извлечь [(t0,t1)] окон ДВОЙНИКА (layout∈{full-head,split},
    не source-passthrough). Возвращает (windows, n_beats_total, note)."""
    beats = spec.get("beats")
    if not beats and isinstance(spec.get("segments"), list):
        # project-meta segments[] без layout — считаем КАЖДЫЙ сегмент avatar-окном
        # (segments несут look_frame/avatar_mp4 = двойник по определению).
        segs = []
        for s in spec["segments"]:
            t0, t1 = s.get("t0"), s.get("t1")
            if t0 is not None and t1 is not None:
                segs.append((float(t0), float(t1)))
        return segs, len(spec["segments"]), "окна из project-meta segments[]"
    if not beats:
        return [], 0, "в спеке нет beats[] (и нет segments[] с t0/t1)"
    wins = []
    for b in beats:
        lay = layout_norm(b.get("layout"))
        if lay in AVATAR_LAYOUTS and not b.get("source_passthrough"):
            t0, t1 = b.get("t0"), b.get("t1")
            if t0 is not None and t1 is not None:
                wins.append((float(t0), float(t1)))
    return wins, len(beats), "окна из beats[] (layout∈full-head/split, не passthrough)"


def in_any_window(t, windows, pad=0.34):
    for (a, b) in windows:
        if a - pad <= t <= b + pad:
            return True
    return False


def load_exempt_windows(spec):
    """Окна битов с ГЕНЕРАТИВНЫМ бролл-футажом автора (AI-выводы: люди/персонажи в кино-кадрах).
    Там лица = генерации автора 1:1, НЕ competitor-ведущий → foreign-face-gate не должен на них
    фейлить .
    Бит помечается `generative_broll:true` ИЛИ layout∈{full-broll,full-demo}. Возвращает [(t0,t1)].
    """
    beats = spec.get("beats")
    if not beats:
        return []
    wins = []
    for b in beats:
        lay = layout_norm(b.get("layout"))
        if b.get("generative_broll") or lay in ("full-broll", "full-demo"):
            t0, t1 = b.get("t0"), b.get("t1")
            if t0 is not None and t1 is not None:
                wins.append((float(t0), float(t1)))
    return wins


def detect_faces_timeline(render, dur):
    """ПОКАДРОВО (source_vision/YuNet): читает КАЖДЫЙ кадр (FACE_FPS=0) или прореживает
    (FACE_FPS>0). Возвращает [(t, n_faces)]. YuNet ловит профиль/частичное лицо —
    Haar-фронталка их теряла, автор протекал между редкими замерами."""
    try:
        import cv2
    except ImportError:
        return None, "cv2 не установлен — face-detect невозможен"
    yunet = source_vision.load_yunet(score=FACE_SCORE)
    haar = source_vision._haar() if yunet is None else None
    engine = "yunet" if yunet is not None else ("haar" if haar is not None else None)
    if engine is None:
        return None, "ни YuNet (models/yunet.onnx), ни Haar недоступны"
    cap = cv2.VideoCapture(render)
    if not cap.isOpened():
        return None, "видео не открылось: %s" % render
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps / FACE_FPS))) if FACE_FPS > 0 else 1
    timeline = []
    idx = 0
    n_used = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if step > 1 and (idx % step) != 0:
            idx += 1
            continue
        faces = source_vision.detect_faces(fr, yunet, haar, FACE_MINSIZE)
        timeline.append((round(idx / fps, 3), len(faces)))
        idx += 1
        n_used += 1
    cap.release()
    cov = "каждый кадр" if step == 1 else "каждый %d-й кадр" % step
    return timeline, "ok (%d кадров %s, fps=%.2f, движок=%s, minSize=%d)" % (
        n_used, cov, fps, engine, FACE_MINSIZE)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return 2
    render, spec_path = a[0], a[1]
    root = a[2] if len(a) > 2 else os.path.dirname(os.path.abspath(render))
    verdict_path = os.path.join(root, ".foreign-face-verdict.json")

    if not os.path.isfile(render):
        return fail("нет render mp4 (%s)" % render, verdict_path)
    if not os.path.isfile(spec_path):
        return fail("нет спеки/меты (%s)" % spec_path, verdict_path)
    try:
        spec = json.load(open(spec_path, encoding="utf-8"))
    except Exception as e:
        return fail("спека не валидный JSON (%s): %s" % (spec_path, e), verdict_path)

    windows, n_beats, win_note = load_avatar_windows(spec)
    exempt = load_exempt_windows(spec)  # генеративный бролл — лица там = AI-выводы автора, не ведущий
    dur = ffprobe_duration(render) or 0.0

    timeline, det_note = detect_faces_timeline(render, dur)
    if timeline is None:
        return fail("детект лиц не выполнен: %s" % det_note, verdict_path)

    # (A) чужое лицо: лицо в кадре, который НЕ в avatar-окне И НЕ в generative-broll окне
    foreign = [t for (t, nf) in timeline if nf > 0
               and not in_any_window(t, windows)
               and not in_any_window(t, exempt)]
    # (B) нет двойника: avatar-окно без единого лица
    face_times = [t for (t, nf) in timeline if nf > 0]
    empty_avatar = []
    for (a0, b0) in windows:
        has = any(a0 - 0.34 <= t <= b0 + 0.34 for t in face_times)
        if not has:
            empty_avatar.append([round(a0, 2), round(b0, 2)])

    issues = []
    if foreign:
        issues.append("ЧУЖОЕ ЛИЦО вне avatar-окна на таймкодах %s — вероятно автор-источник, "
                      "не двойник (AC2-A)" % ", ".join("%.2fс" % t for t in foreign[:12]))
    if windows and empty_avatar:
        issues.append("AVATAR-окна БЕЗ лица %s — двойник не вставлен (AC2-B)"
                      % ", ".join("%.2f→%.2f" % (w[0], w[1]) for w in empty_avatar))

    extra = {
        "render": os.path.basename(render),
        "avatar_windows": [[round(w[0], 2), round(w[1], 2)] for w in windows],
        "broll_exempt_windows": [[round(w[0], 2), round(w[1], 2)] for w in exempt],
        "windows_note": win_note,
        "detect_note": det_note,
        "n_beats": n_beats,
        "faces_total_frames": len([1 for (_t, nf) in timeline if nf > 0]),
        "issues": issues,
    }

    if issues:
        return fail("; ".join(issues), verdict_path, extra)

    extra["verdict"] = "PASS"
    json.dump(extra, open(verdict_path, "w"), ensure_ascii=False, indent=1)
    print("PASS: лица только в avatar-окнах, каждое avatar-окно содержит двойника "
          "(%d окон, %s)" % (len(windows), det_note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
