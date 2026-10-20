#!/usr/bin/env python3
"""
ui-detect.py — ВИДИТ что у конкурента на ВЕРХНЕМ экране (выше лица/сплит-линии)
и выдаёт МАШИНОЧИТАЕМУЮ инструкцию репликации. Корень проблемы: агент на Opus
не понимал, что в верхнем сплите (скринкаст? анимированный UI-мок? hero-вставка?)
и не мог отрисовать так же.

БЕЗ платных API. Чистые эвристики (opencv + ffmpeg + numpy + PIL). Точность 100%
не нужна — нужна ЧЕСТНАЯ уверенность (confidence + «не уверен»).

Классы верхней зоны:
  real-screencast  — запись реального UI: тёмный/светлый хром, прямоугольные панели,
                     МНОГО мелких текстовых строк (высокая плотность мелких контуров),
                     выраженная сетка вертикальных/горизонтальных рёбер. Часто dark-mode
                     (near-black фон → высокий dom_frac, но это НЕ мок).
  animated-ui-mock — отрисованный мок: ПЛОСКИЙ ЯРКИЙ/НАСЫЩЕННЫЙ доминирующий цвет
                     (часто кислотный неон), КРУПНАЯ типографика, мало текстуры,
                     синтетические заливки/градиенты.
  hero-footage     — фотореализм: высокая текстурная энтропия, НЕТ UI-сетки прямоугольников,
                     богатый цвет, нет плоского доминанта, нет рядов мелкого текста.
  full-author      — лицо занимает верх кадра (haar-cascade), это не UI а говорящая голова.

Семплинг fps~1, режем верхнюю зону по детекту лица (как scene-audit.py),
сегментируем подряд идущие кадры одного класса в шоты (t0-t1).

Выход: markdown «## UI-РЕПЛИКАЦИЯ ВЕРХА» — таблица сегментов с действием репликации.

usage:
  ui-detect.py <video.mp4> [--out report.md] [--fps 1] [--debug]
exit 0 = ОК, 2 = не смог прочитать видео.
"""
import argparse, os, subprocess, sys, tempfile
from collections import Counter
import numpy as np
from PIL import Image

def _has_tesseract():
    from shutil import which
    return which('tesseract') is not None

# ---------------------------------------------------------------------------
# ffmpeg/ffprobe хелперы (тот же подход, что в scene-audit.py)
# ---------------------------------------------------------------------------
def duration(mp4):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                        '-of','csv=p=0', mp4], capture_output=True, text=True)
    try:
        d = float(r.stdout.strip());  return d if d > 0 else None
    except (ValueError, AttributeError):
        return None

def dims(mp4):
    r = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                        'stream=width,height','-of','csv=p=0:s=x', mp4], capture_output=True, text=True)
    try:
        w,h = r.stdout.strip().split('x');  w,h = int(w),int(h)
        return (w,h) if w>0 and h>0 else None
    except (ValueError, AttributeError):
        return None

def grab(mp4, t, scale=None):
    out = tempfile.mktemp(suffix='.png')
    vf = f'scale={scale}' if scale else 'null'
    subprocess.run(['ffmpeg','-y','-ss',str(t),'-i',mp4,'-frames:v','1','-vf',vf,out],
                   capture_output=True)
    return out if os.path.exists(out) else None

# ---------------------------------------------------------------------------
# Детект лица — переиспользуем подход scene-audit.py (haar frontal)
# ---------------------------------------------------------------------------
def detect_face_frac(png, H):
    try:
        import cv2
    except Exception:
        return None
    img = cv2.imread(png)
    if img is None:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    f = cc.detectMultiScale(g, 1.1, 5, minSize=(80,80))
    if len(f) == 0:
        return None
    x,y,w,h = max(f, key=lambda z: z[2])
    return dict(y0=y/H, y1=(y+h)/H, h_frac=h/H, cy=(y+h/2)/H)

# ---------------------------------------------------------------------------
# Признаки верхней зоны (numpy на ужатом кадре)
# ---------------------------------------------------------------------------
def zone_features(rgb):
    h, w, _ = rgb.shape
    arr = rgb.astype(np.float32)
    gray = (0.299*arr[:,:,0] + 0.587*arr[:,:,1] + 0.114*arr[:,:,2])

    mx = arr.max(axis=2); mn = arr.min(axis=2)
    sat = np.where(mx > 1e-3, (mx - mn) / (mx + 1e-3), 0.0)
    sat_mean = float(sat.mean())
    neon_frac = float(((sat > 0.55) & (mx > 140)).mean())

    q = (arr // 32).astype(np.int32)
    keys = q[:,:,0]*100 + q[:,:,1]*10 + q[:,:,2]
    vals, counts = np.unique(keys, return_counts=True)
    dom_frac = float(counts.max() / keys.size)
    # КАКОГО цвета доминант — критично: dark-mode скринкаст имеет высокий dom_frac
    # (near-black фон), но это НЕ designed fill мока. Мок = ЯРКАЯ/насыщенная заливка.
    dom_key = int(vals[counts.argmax()])
    dr = (dom_key // 100) * 32 + 16
    dg = ((dom_key // 10) % 10) * 32 + 16
    db = (dom_key % 10) * 32 + 16
    dom_lum = (0.299*dr + 0.587*dg + 0.114*db)
    dom_sat = (max(dr,dg,db) - min(dr,dg,db)) / (max(dr,dg,db) + 1e-3)
    dom_is_dark = bool(dom_lum < 55)
    dom_is_fill = bool(dom_lum >= 70 and (dom_sat > 0.25 or dom_lum > 170))
    # «доля designed-fill»: dom_frac, засчитываемый в мок ТОЛЬКО если доминант — яркая заливка
    fill_frac = dom_frac if dom_is_fill else 0.0

    hist, _ = np.histogram(gray, bins=32, range=(0,255))
    p = hist / max(hist.sum(), 1)
    p = p[p > 0]
    entropy = float(-(p * np.log2(p)).sum())

    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    edge_density = float((gx > 25).mean() + (gy > 25).mean()) / 2.0

    row_switch = (gx > 30).mean(axis=1)
    text_rows_frac = float((row_switch > 0.06).mean())

    col_edge = (gx > 35).mean(axis=0)
    rowL_edge = (gy > 35).mean(axis=1)
    strong_vlines = int((col_edge > 0.35).sum())
    strong_hlines = int((rowL_edge > 0.35).sum())
    ui_grid = strong_vlines + strong_hlines

    dark_frac = float((gray < 60).mean())
    grayish_frac = float((sat < 0.18).mean())

    return dict(
        sat_mean=round(sat_mean,3), neon_frac=round(neon_frac,3),
        dom_frac=round(dom_frac,3), fill_frac=round(fill_frac,3),
        dom_is_dark=dom_is_dark, dom_is_fill=dom_is_fill,
        entropy=round(entropy,3), edge_density=round(edge_density,4),
        text_rows_frac=round(text_rows_frac,3), ui_grid=ui_grid,
        dark_frac=round(dark_frac,3), grayish_frac=round(grayish_frac,3),
    )

# ---------------------------------------------------------------------------
# Классификатор — эвристики, откалиброванные на DUqeScpDAHW + DZF4V4aMxKz
# ---------------------------------------------------------------------------
def classify(f):
    scores = {'real-screencast':0.0, 'animated-ui-mock':0.0, 'hero-footage':0.0}
    why = {'real-screencast':[], 'animated-ui-mock':[], 'hero-footage':[]}

    # есть ли реальная UI-структура (мелкие строки текста ИЛИ жёсткая сетка)
    ui_structure = (f['text_rows_frac'] > 0.16) or (f['ui_grid'] >= 8)

    # --- animated-ui-mock: ЯРКАЯ/насыщенная плоская заливка + мало UI-структуры ---
    if f['neon_frac'] > 0.10:
        scores['animated-ui-mock'] += 2.4; why['animated-ui-mock'].append(f"неон-заливка {f['neon_frac']}")
    if f['fill_frac'] > 0.30 and not ui_structure:
        scores['animated-ui-mock'] += 1.8; why['animated-ui-mock'].append(f"плоская яркая заливка {f['fill_frac']}")
    if f['dom_is_fill'] and f['sat_mean'] > 0.35 and f['text_rows_frac'] < 0.16:
        scores['animated-ui-mock'] += 1.2; why['animated-ui-mock'].append(f"насыщенный designed-фон {f['sat_mean']}")
    if f['fill_frac'] > 0.22 and f['edge_density'] < 0.06 and f['text_rows_frac'] < 0.12:
        scores['animated-ui-mock'] += 1.0; why['animated-ui-mock'].append("крупная типографика, не мелкие строки")

    # --- real-screencast: UI-хром + много мелких строк + жёсткая сетка (любой фон) ---
    if f['text_rows_frac'] > 0.18:
        scores['real-screencast'] += 2.2; why['real-screencast'].append(f"мелкие текст-строки {f['text_rows_frac']}")
    if f['ui_grid'] >= 6:
        scores['real-screencast'] += 1.8; why['real-screencast'].append(f"жёсткая UI-сетка {f['ui_grid']}")
    elif f['ui_grid'] >= 4:
        scores['real-screencast'] += 1.0; why['real-screencast'].append(f"UI-сетка рёбер {f['ui_grid']}")
    # dark-mode хром: тёмный доминант + детализация = скринкаст, НЕ мок
    if f['dom_is_dark'] and f['edge_density'] > 0.03 and (f['text_rows_frac'] > 0.10 or f['ui_grid'] >= 4):
        scores['real-screencast'] += 1.5; why['real-screencast'].append("dark-mode UI-хром с детализацией")
    if f['grayish_frac'] > 0.55 and f['neon_frac'] < 0.05 and f['edge_density'] > 0.03:
        scores['real-screencast'] += 1.0; why['real-screencast'].append(f"малонасыщенный хром {f['grayish_frac']}")

    # --- hero-footage: фотореализм, высокая энтропия, БЕЗ UI-сетки/текст-строк/неона/заливки ---
    if f['entropy'] > 4.2 and not ui_structure:
        scores['hero-footage'] += 2.0; why['hero-footage'].append(f"высокая энтропия {f['entropy']}")
    if f['ui_grid'] <= 3 and f['text_rows_frac'] < 0.08 and f['neon_frac'] < 0.05:
        scores['hero-footage'] += 1.4; why['hero-footage'].append("нет UI-сетки/строк/неона")
    if 0.18 <= f['sat_mean'] <= 0.45 and f['fill_frac'] < 0.20 and not f['dom_is_dark']:
        scores['hero-footage'] += 1.2; why['hero-footage'].append("богатый цвет, нет плоского доминанта")
    if f['dom_frac'] < 0.20 and f['entropy'] > 3.9 and f['neon_frac'] < 0.05 and f['ui_grid'] <= 5:
        scores['hero-footage'] += 1.0; why['hero-footage'].append("текстурный кадр без неона")

    best = max(scores, key=scores.get)
    s = sorted(scores.values(), reverse=True)
    top, second = s[0], (s[1] if len(s) > 1 else 0.0)
    if top <= 0.8:
        conf = 0.0
    else:
        margin = (top - second) / max(top, 1e-3)
        strength = min(top / 4.0, 1.0)
        conf = round(0.45*strength + 0.55*margin, 2)
        conf = max(0.0, min(conf, 0.97))
    reason = '; '.join(why[best][:3]) if why[best] else 'слабые сигналы'
    return best, conf, reason, scores

# ---------------------------------------------------------------------------
# UI-спека для animated-ui-mock
# ---------------------------------------------------------------------------
def dominant_colors(rgb, k=4):
    a = rgb.reshape(-1, 3).astype(np.float32)
    if a.shape[0] > 12000:
        idx = np.random.RandomState(0).choice(a.shape[0], 12000, replace=False)
        a = a[idx]
    np.random.seed(0)
    centers = a[np.random.choice(a.shape[0], k, replace=False)].copy()
    lab = np.zeros(a.shape[0], dtype=int)
    for _ in range(6):
        d = ((a[:,None,:] - centers[None,:,:])**2).sum(axis=2)
        lab = d.argmin(axis=1)
        for j in range(k):
            m = lab == j
            if m.any():
                centers[j] = a[m].mean(axis=0)
    counts = np.bincount(lab, minlength=k)
    order = np.argsort(counts)[::-1]
    out = []
    for j in order:
        if counts[j] == 0:
            continue
        r,g,b = centers[j].astype(int)
        out.append(('#%02X%02X%02X' % (max(0,min(255,r)),max(0,min(255,g)),max(0,min(255,b))),
                    round(float(counts[j]/counts.sum()), 2)))
    return out

def big_text_present(rgb, f):
    return (f['text_rows_frac'] < 0.14 and f['edge_density'] > 0.012 and f['fill_frac'] > 0.20)

# ---------------------------------------------------------------------------
# Действие репликации по классу
# ---------------------------------------------------------------------------
def action_for(cls, conf, spec):
    if cls == 'full-author':
        return "—  (говорящая голова, не UI-зона)"
    if cls == 'real-screencast':
        hint = spec.get('screencast_hint', 'тот же сервис/инструмент что у автора')
        return f"footage-fetch.sh: записать/добыть скринкаст — {hint}"
    if cls == 'animated-ui-mock':
        cols = spec.get('colors', [])
        col_s = ', '.join(h for h,_ in cols[:3]) if cols else 'см. кадр'
        big = 'текст КРУПНЫЙ' if spec.get('big_text') else 'текст мелкий/нет'
        return f"G-ui-mocks блок (motion-blocks/_INDEX.md) + цвета {col_s}, {big}"
    if cls == 'hero-footage':
        return "footage-fetch.sh галерея ИЛИ Higgsfield-generate (фотореал-вставка)"
    return "—"

# ---------------------------------------------------------------------------
# Главный проход
# ---------------------------------------------------------------------------
def analyze(mp4, fps=1.0, debug=False):
    dur = duration(mp4); dm = dims(mp4)
    if not dur or not dm:
        return None, "не удалось прочитать видео (ffprobe не дал длительность/размеры)"
    W, H = dm
    n = max(3, int(dur * fps))
    samples = []
    DEFAULT_SPLIT = 0.78

    for i in range(n):
        t = dur * (i + 0.5) / n
        png = grab(mp4, t, scale='540:-1')
        if not png:
            continue
        hpx_img = Image.open(png).height
        face = detect_face_frac(png, H=hpx_img)
        im = Image.open(png).convert('RGB')
        full = np.asarray(im, dtype=np.uint8)
        hpx = full.shape[0]

        if face and face['cy'] > 0.55 and face['h_frac'] > 0.12:
            split = max(0.30, face['y0'] - 0.02)
            cls_face = None
        elif face and face['cy'] <= 0.55 and face['h_frac'] > 0.20:
            split = DEFAULT_SPLIT
            cls_face = 'full-author'
        else:
            split = DEFAULT_SPLIT
            cls_face = None

        top = full[0:int(hpx*split), :, :]
        os.remove(png)
        if top.shape[0] < 20:
            continue

        feats = zone_features(top)
        if cls_face == 'full-author':
            cls, conf, reason = 'full-author', 0.80, f"лицо занимает верх (cy={face['cy']:.2f})"
            scores = {}
        else:
            cls, conf, reason, scores = classify(feats)

        spec = {}
        if cls == 'animated-ui-mock':
            spec['colors'] = dominant_colors(top, k=4)
            spec['big_text'] = big_text_present(top, feats)
        elif cls == 'real-screencast':
            spec['screencast_hint'] = 'тот же сервис/инструмент что у автора (см. кадр)'

        samples.append(dict(t=round(t,2), cls=cls, conf=conf, reason=reason,
                            feats=feats, spec=spec, split=round(split,2)))
        if debug:
            print(f"t={t:5.1f}s split={split:.2f} -> {cls:16s} conf={conf:.2f} | {feats}", file=sys.stderr)

    if not samples:
        return None, "ни один кадр не прочитан"

    segs = []
    for s in samples:
        if segs and segs[-1]['cls'] == s['cls']:
            segs[-1]['t1'] = s['t']
            segs[-1]['members'].append(s)
        else:
            segs.append(dict(cls=s['cls'], t0=s['t'], t1=s['t'], members=[s]))
    for i, seg in enumerate(segs):
        seg['t1'] = segs[i+1]['t0'] if i+1 < len(segs) else round(dur, 2)

    return dict(dur=round(dur,2), dims=(W,H), n=len(samples), segs=segs, samples=samples), None

# ---------------------------------------------------------------------------
# Рендер markdown-отчёта
# ---------------------------------------------------------------------------
def render_report(mp4, res):
    L = []
    L.append("## UI-РЕПЛИКАЦИЯ ВЕРХА")
    L.append("")
    L.append(f"Источник: `{os.path.basename(mp4)}` · длит {res['dur']}с · {res['dims'][0]}x{res['dims'][1]} · кадров проанализировано {res['n']}")
    if not _has_tesseract():
        L.append("")
        L.append("> OCR (tesseract) не установлен — текст в моках НЕ распознан, оценка крупности текста по форме (честно, без распознавания слов).")
    L.append("")
    L.append("| сегмент (t0-t1) | класс | conf | почему | действие репликации |")
    L.append("|---|---|---|---|---|")
    for seg in res['segs']:
        confs = [m['conf'] for m in seg['members']]
        conf = round(sum(confs)/len(confs), 2)
        m0 = seg['members'][0]
        spec = m0['spec']
        for m in seg['members']:
            if m['spec']:
                spec = m['spec']; break
        unsure = " (не уверен)" if conf < 0.45 else ""
        reason = m0['reason']
        act = action_for(seg['cls'], conf, spec)
        L.append(f"| {seg['t0']:.1f}-{seg['t1']:.1f}с | {seg['cls']}{unsure} | {conf:.2f} | {reason} | {act} |")
    L.append("")
    cnt = Counter()
    for s in res['samples']:
        cnt[s['cls']] += 1
    dom = cnt.most_common(1)[0][0]
    L.append(f"**Доминирующий тип верха:** {dom} ({cnt[dom]}/{res['n']} кадров). Раскладка: " +
             ', '.join(f"{k}={v}" for k,v in cnt.most_common()))
    L.append("")
    L.append("_Эвристики (без платных API), точность не 100% — сверяй conf и помеченные (не уверен) сегменты с кадрами._")
    return '\n'.join(L)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out', default=None)
    ap.add_argument('--fps', type=float, default=1.0)
    ap.add_argument('--debug', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(a.video):
        print(f"FAIL: нет файла {a.video}", file=sys.stderr); sys.exit(2)
    res, err = analyze(a.video, fps=a.fps, debug=a.debug)
    if err:
        print(f"FAIL: {err}", file=sys.stderr); sys.exit(2)
    report = render_report(a.video, res)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as fh:
            fh.write(report + '\n')
        print(f"OK -> {a.out}")
    else:
        print(report)
    sys.exit(0)

if __name__ == '__main__':
    main()
