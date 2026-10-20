#!/usr/bin/env python3
"""
benchmark-pairs.py — МАШИННАЯ пиксельная сверка НАШЕГО рилза с конкурентом И с
внутренними эталонами по ФИКСИРОВАННЫМ парам таймкодов (label + ref_t + our_t).

Корень провала по решению автора: бенчмарк-точки держались «в голове агента», side-by-side
как артефакта НЕ существовало, старый план «напланировал» эффекты, которых у
конкурента нет. Этот скрипт делает бенчмарк ДЕТЕРМИНИРОВАННЫМ артефактом:
оркестратор пишет пары из карты деконструкции (Г2), скрипт по каждой паре кладёт
контакт-кадр (ref|our) + три машинные оси + сводный отчёт и вердикт.

Переиспользует функции замера из scene-audit.py (motion / face / text-mask).

Оси пары:
  (а) MOTION  — motion-density в окне +/-1.0с с обеих сторон. PASS если
                our >= 70% от ref ИЛИ our >= внутреннего пола (--internal-floor, дефолт 2.0
                соб-экв/с по motion-прокси). Вердикт по max(планка_конкурента, пол).
  (б) FILL    — заполненность контент-зоны: доля «непустых» (не фон) пикселей в верхних
                60% кадра у нас vs ref. our < 50% от ref = WARN «панель пустее автора».
  (в) TEXT    — наличие текст-пикселей (титр/саб) у ref и у нас. У ref есть, у нас нет =
                WARN рассинхрон.

Свод:
  <project>/_benchmark/pair_<label>.png   — контакт-кадры (вход для vision-критика и автору)
  <project>/_benchmark/benchmark-report.md
  <project>/_benchmark/benchmark-verdict.json {verdict, pairs:[...]}

Вердикт FAIL если: >=2 пар провалили MOTION-ось ИЛИ >=1 пустая панель при заявленном UI
(--ui-claimed; иначе FILL остаётся WARN, не валит).

Exit 0 = PASS, 2 = FAIL (как у хуков), не 1.

usage:
  benchmark-pairs.py --pairs pairs.json [--project DIR] [--internal-floor 2.0] [--window 1.0] [--ui-claimed]
  pairs.json: {"ref":"<comp.mp4>","our":"<our.mp4>",
               "pairs":[{"label":"hook","ref_t":0.5,"our_t":1.0}, ...]}  (5-7 пар)
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# -- переиспользуем замеры из scene-audit (импортом, единый источник истины) --
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scene-audit.py')
_spec = importlib.util.spec_from_file_location('scene_audit', _p)
_sa = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_sa)

grab       = _sa.grab
grab_arr   = _sa.grab_arr
duration   = _sa.duration
dims       = _sa.dims
motion     = _sa.motion          # mean abs frame-diff в окне (соб-экв-прокси)
_text_mask = _sa._text_mask

# Пороги осей
MOTION_RATIO   = 0.70            # our >= 70% от ref по motion
FILL_RATIO     = 0.50            # our < 50% от ref по заполненности -> WARN
TOP_FRAC       = 0.60            # «контент-зона» = верхние 60% кадра
TEXT_MASK_MIN  = 0.004          # доля текст-пикселей чтобы считать «текст есть»


# ----- ось (а) MOTION -----
def motion_window(mp4, t, window, n=6):
    """motion-density (соб-экв-прокси) в окне [t-window, t+window], клипованном к длине."""
    d = duration(mp4)
    if d is None:
        return None
    t0 = max(0.0, t - window)
    t1 = min(d, t + window)
    if t1 - t0 < 0.1:                       # окно у самого края -> расширим внутрь
        t1 = min(d, t0 + 2 * window)
    return motion(mp4, n=n, t0=t0, t1=t1)   # region=None -> весь кадр


# ----- ось (б) FILL -----
def content_fill(mp4, t, top_frac=TOP_FRAC):
    """Доля «непустых» (не фон) пикселей в верхних top_frac кадра.
    Фон = доминирующий (модальный по гистограмме яркости) тон; «непустой» = пиксель,
    чья яркость отличается от модального фона больше чем на порог (структура/UI/текст)."""
    a = grab_arr(mp4, t)
    if a is None:
        return None
    g = np.asarray(Image.fromarray(a).convert('L'), dtype=np.uint8)
    h = g.shape[0]
    top = g[0:int(h * top_frac)]
    if top.size == 0:
        return None
    hist = np.bincount(top.reshape(-1), minlength=256)
    bg = int(hist.argmax())                 # модальная яркость = фон
    thr = 18                                # +/-18 уровней = «тот же фон»
    nonbg = float((np.abs(top.astype(np.int16) - bg) > thr).mean())
    return round(nonbg, 4)


# ----- ось (в) TEXT -----
def has_text(mp4, t):
    """Есть ли отчётливый текст-кластер (титр/саб) в кадре - через _text_mask scene-audit."""
    import cv2
    a = grab_arr(mp4, t)
    if a is None:
        return None
    gray = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    tm = _text_mask(gray)
    ratio = float((tm > 0).mean())
    return (ratio >= TEXT_MASK_MIN, round(ratio, 4))


# ----- контакт-кадр ref|our -----
def _load_font(size):
    for p in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf',
              '/System/Library/Fonts/Supplemental/Arial.ttf',
              '/System/Library/Fonts/Helvetica.ttc'):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def contact_sheet(ref_mp4, our_mp4, label, ref_t, our_t, out_png, cell_h=900):
    """ref|our рядом (9:16 вертикали), подпись label + таймкоды. PNG для критика и автора."""
    def cell(mp4, t, side, tlabel):
        p = grab(mp4, t)
        im = Image.open(p).convert('RGB') if p else None
        if p and os.path.exists(p):
            os.remove(p)
        if im is None:
            im = Image.new('RGB', (int(cell_h * 9 / 16), cell_h), (40, 40, 40))
        w = int(cell_h * im.width / im.height)
        im = im.resize((w, cell_h))
        band = Image.new('RGB', (im.width, 46), (15, 15, 15))
        d = ImageDraw.Draw(band)
        d.text((10, 8), f"{side}  t={tlabel}s", font=_load_font(26), fill=(255, 230, 80))
        stacked = Image.new('RGB', (im.width, cell_h + 46), (15, 15, 15))
        stacked.paste(band, (0, 0)); stacked.paste(im, (0, 46))
        return stacked

    left = cell(ref_mp4, ref_t, "REF (konkurent)", ref_t)
    right = cell(our_mp4, our_t, "OUR (nash)", our_t)
    gap = 8
    W = left.width + gap + right.width
    title_h = 54
    canvas = Image.new('RGB', (W, title_h + max(left.height, right.height)), (10, 10, 10))
    dt = ImageDraw.Draw(canvas)
    dt.text((12, 14), f"PAIR: {label}   ref_t={ref_t}s  our_t={our_t}s",
            font=_load_font(30), fill=(255, 255, 255))
    canvas.paste(left, (0, title_h))
    canvas.paste(right, (left.width + gap, title_h))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    canvas.save(out_png)
    return out_png


# ----- оркестрация -----
def run_pair(ref_mp4, our_mp4, pr, bench_dir, floor, window, ui_claimed):
    label = str(pr['label']); ref_t = float(pr['ref_t']); our_t = float(pr['our_t'])
    png = os.path.join(bench_dir, f"pair_{label}.png")
    contact_sheet(ref_mp4, our_mp4, label, ref_t, our_t, png)

    # (а) MOTION
    rm = motion_window(ref_mp4, ref_t, window)
    om = motion_window(our_mp4, our_t, window)
    planka = max(MOTION_RATIO * rm, floor) if rm else floor
    m_ok = (om is not None) and (om >= planka)
    m_verdict = 'PASS' if m_ok else 'FAIL'

    # (б) FILL
    rf = content_fill(ref_mp4, ref_t)
    of = content_fill(our_mp4, our_t)
    fill_ratio = round(of / rf, 3) if (rf and of is not None) else None
    empty_panel = (rf is not None and of is not None and rf > 0 and of < FILL_RATIO * rf)
    if empty_panel:
        f_verdict = 'FAIL' if ui_claimed else 'WARN'
    else:
        f_verdict = 'PASS'

    # (в) TEXT
    rt = has_text(ref_mp4, ref_t)
    ot = has_text(our_mp4, our_t)
    text_desync = (rt is not None and ot is not None and rt[0] and not ot[0])
    t_verdict = 'WARN' if text_desync else 'PASS'

    return {
        'label': label, 'ref_t': ref_t, 'our_t': our_t, 'contact_sheet': png,
        'motion': {'ref': rm, 'our': om, 'floor': floor,
                   'planka': round(planka, 3) if planka else None,
                   'ratio_vs_ref': round(om / rm, 3) if (rm and om is not None) else None,
                   'verdict': m_verdict},
        'fill': {'ref': rf, 'our': of, 'ratio': fill_ratio,
                 'empty_panel': empty_panel, 'verdict': f_verdict},
        'text': {'ref': rt[1] if rt else None, 'our': ot[1] if ot else None,
                 'ref_has': bool(rt[0]) if rt else None,
                 'our_has': bool(ot[0]) if ot else None,
                 'desync': text_desync, 'verdict': t_verdict},
    }


def write_report(bench_dir, ref_mp4, our_mp4, floor, results, verdict, reasons):
    md = os.path.join(bench_dir, 'benchmark-report.md')
    lines = []
    lines.append("# Бенчмарк пар - пиксельная сверка наш <-> конкурент")
    lines.append("")
    lines.append(f"- REF (конкурент): `{ref_mp4}`")
    lines.append(f"- OUR (наш): `{our_mp4}`")
    lines.append(f"- Внутренний пол (motion-прокси, соб-экв/с): **{floor}**  "
                 f"(эталоны: g0dm0d3/scene2 ~4.2, karkas/opening ~2.2)")
    lines.append(f"- **ИТОГ: {verdict}**")
    if reasons:
        for r in reasons:
            lines.append(f"  - {r}")
    lines.append("")
    lines.append("| label | MOTION our/ref (планка) | вердикт | FILL our/ref (доля) | вердикт | TEXT ref/our | вердикт | контакт-кадр |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        m, f, t = r['motion'], r['fill'], r['text']
        m_cell = f"{m['our']}/{m['ref']} (>={m['planka']})"
        f_cell = f"{f['our']}/{f['ref']} ({f['ratio']})"
        t_cell = (f"{'есть' if t['ref_has'] else 'нет'}/"
                  f"{'есть' if t['our_has'] else 'нет'}")
        lines.append(f"| {r['label']} | {m_cell} | {m['verdict']} | {f_cell} | "
                     f"{f['verdict']} | {t_cell} | {t['verdict']} | `{os.path.basename(r['contact_sheet'])}` |")
    lines.append("")
    lines.append("## Планки вердикта")
    lines.append("- MOTION: our >= max(70% от ref, внутренний пол). Обе планки в колонке.")
    lines.append("- FILL: our < 50% от ref = пустее автора. FAIL только при --ui-claimed, иначе WARN.")
    lines.append("- TEXT: у ref есть текст, у нас нет = рассинхрон (WARN).")
    lines.append("- ИТОГ FAIL если >=2 пар провалили MOTION ИЛИ >=1 пустая панель при заявленном UI.")
    lines.append("")
    lines.append("## Контакт-кадры (вход для vision-критика и для показа автору)")
    for r in results:
        lines.append(f"- **{r['label']}** (ref_t={r['ref_t']}s, our_t={r['our_t']}s): `{r['contact_sheet']}`")
    open(md, 'w', encoding='utf-8').write("\n".join(lines) + "\n")
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pairs', required=True, help='pairs.json {ref, our, pairs:[{label,ref_t,our_t}]}')
    ap.add_argument('--project', help='корень проекта (куда писать _benchmark/); дефолт = папка our.mp4')
    ap.add_argument('--internal-floor', dest='floor', type=float, default=2.0,
                    help='внутренний пол (соб-экв/с по motion-прокси); дефолт 2.0')
    ap.add_argument('--window', type=float, default=1.0, help='пол-окна замера motion в секундах (+/-)')
    ap.add_argument('--ui-claimed', action='store_true',
                    help='в кадре ЗАЯВЛЕН UI - тогда пустая панель (FILL<50%% от ref) = FAIL, иначе WARN')
    ap.add_argument('--anchors', default='',
                    help='опоры бенчмарка через запятую: A=конкурент-источник · B=эталон формата · '
                         'C=канон best-practice. Для полного куска нужны ВСЕ ТРИ (chunk-review-gate). '
                         'Можно взять из pairs.json["anchors"].')
    a = ap.parse_args()

    if not os.path.exists(a.pairs):
        print(f"ERROR: нет файла пар {a.pairs}"); sys.exit(2)
    spec = json.load(open(a.pairs, encoding='utf-8'))
    ref_mp4, our_mp4 = spec.get('ref'), spec.get('our')
    pairs = spec.get('pairs', [])
    if not ref_mp4 or not our_mp4 or not pairs:
        print("ERROR: pairs.json должен содержать ref, our и непустой pairs[]"); sys.exit(2)
    for mp4, name in ((ref_mp4, 'ref'), (our_mp4, 'our')):
        if not os.path.exists(mp4):
            print(f"ERROR: {name} mp4 не найден: {mp4}"); sys.exit(2)
        if duration(mp4) is None:
            print(f"ERROR: {name} mp4 нечитаем (ffprobe не дал длительность): {mp4}"); sys.exit(2)
    if not (5 <= len(pairs) <= 7):
        print(f"  ! ожидается 5-7 пар, получено {len(pairs)} - продолжаю")

    project = a.project or os.path.dirname(os.path.abspath(our_mp4))
    bench_dir = os.path.join(project, '_benchmark')
    os.makedirs(bench_dir, exist_ok=True)

    results = []
    for pr in pairs:
        if not all(k in pr for k in ('label', 'ref_t', 'our_t')):
            print(f"  ! пара без label/ref_t/our_t пропущена: {pr}"); continue
        print(f"  - пара '{pr['label']}' ref_t={pr['ref_t']} our_t={pr['our_t']} ...")
        results.append(run_pair(ref_mp4, our_mp4, pr, bench_dir, a.floor, a.window, a.ui_claimed))

    motion_fails = sum(1 for r in results if r['motion']['verdict'] == 'FAIL')
    panel_fails = sum(1 for r in results if r['fill']['verdict'] == 'FAIL')
    reasons = []
    if motion_fails >= 2:
        reasons.append(f"MOTION провалили {motion_fails} пар (>=2) - темп ниже планки")
    if panel_fails >= 1:
        reasons.append(f"пустая UI-панель в {panel_fails} пар при заявленном UI (--ui-claimed)")
    verdict = 'FAIL' if reasons else 'PASS'

    # опоры бенчмарка (A конкурент · B эталон формата · C канон best-practice) — из --anchors или pairs.json.
    # ЗАПИСЬ в вердикт; ТРЕБОВАНИЕ всех 3 опор энфорсит chunk-review-gate (тут не валим — backward-compat smoke).
    anchors = [x.strip().upper() for x in (a.anchors or '').split(',') if x.strip()]
    if not anchors:
        anchors = [x.strip().upper() for x in spec.get('anchors', []) if str(x).strip()]
    miss_anchors = [x for x in ('A', 'B', 'C') if x not in anchors]
    if miss_anchors:
        print("  ! опоры бенчмарка неполны: нет %s (chunk-review-gate потребует все 3)" % miss_anchors)

    md = write_report(bench_dir, ref_mp4, our_mp4, a.floor, results, verdict, reasons)
    vj = os.path.join(bench_dir, 'benchmark-verdict.json')
    json.dump({'verdict': verdict, 'reasons': reasons, 'floor': a.floor, 'anchors': anchors,
               'ref': ref_mp4, 'our': our_mp4, 'pairs': results},
              open(vj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f"========== BENCHMARK-PAIRS: {verdict} ==========")
    for r in results:
        print(f"  [{r['label']}] MOTION {r['motion']['verdict']} "
              f"(our={r['motion']['our']} ref={r['motion']['ref']} planka>={r['motion']['planka']}) | "
              f"FILL {r['fill']['verdict']} (ratio={r['fill']['ratio']}) | "
              f"TEXT {r['text']['verdict']} (ref={r['text']['ref_has']} our={r['text']['our_has']})")
    for rs in reasons:
        print(f"  x {rs}")
    print(f"  отчёт: {md}")
    print(f"  вердикт-json: {vj}")
    sys.exit(0 if verdict == 'PASS' else 2)


if __name__ == '__main__':
    main()
