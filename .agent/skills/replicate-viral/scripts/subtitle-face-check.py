#!/usr/bin/env python3
"""subtitle-face-check.py — ГАРАНТИЯ: ни один текст-оверлей не лежит на лице аватара.
Прецедент: автор ≥10 раз ловил «субтитры на лице» руками, т.к. машинная проверка
reel-layout-audit.py была ОСИРОТЕВШЕЙ (selftest её не звал). Этот гейт точечный:
берёт subs-manifest.json (каждый оверлей = время + Y-полоса) и для кадров внутри
времени оверлея детектит лицо (cv2 Haar, медиана по кадрам — устойчиво к ложным),
FAIL если Y-полоса текста пересекает лицо.

КЛЮЧ: лицо детектим на ЧИСТОМ исходнике (face_src), а не на рендере — иначе текст
ПОВЕРХ лица перекрывает его и детектор не находит лицо (гарантия побеждалась самим дефектом).
subs-manifest.json: [{"label":"cta","start":39.9,"end":43.2,"y0":760,"y1":1160,
                      "face_src":"heygen/seg-4.mp4","src_t0":5.96,"src_t1":8.96}, ...]
(если face_src нет → бит без спикера, пропуск).
Usage: subtitle-face-check.py <render.mp4> <subs-manifest.json> [project_root]
Exit 0 PASS / 1 FAIL. Пишет <dir>/.subface-verdict.json
"""
import sys, os, json, subprocess, statistics

def faces_at(render, t, casA, casB):
    import cv2
    subprocess.run(f'ffmpeg -y -v error -ss {t} -i "{render}" -frames:v 1 /tmp/_sf.png',
                   shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    img = cv2.imread('/tmp/_sf.png')
    if img is None: return []
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bs = []
    for c in (casA, casB):
        for b in c.detectMultiScale(g, 1.08, 5, minSize=(150,150)):
            bs.append(tuple(int(x) for x in b))
    return bs

def main():
    render, manifest = sys.argv[1], sys.argv[2]
    root = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(os.path.abspath(render))
    if not os.path.isfile(render): print("FAIL: no render"); sys.exit(1)
    subs = json.load(open(manifest))
    try:
        import cv2
    except ImportError:
        print("FAIL: cv2 не установлен — гарантия off-face НЕ может быть проверена"); sys.exit(1)
    casA = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    casB = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_alt2.xml')
    fails, facts = [], []
    for s in subs:
        t0, t1, y0, y1 = float(s["start"]), float(s["end"]), int(s["y0"]), int(s["y1"])
        # face detected on CLEAN source (face_src) — text can't occlude it there
        fsrc = s.get("face_src")
        if fsrc:
            src = os.path.join(root, fsrc) if not os.path.isabs(fsrc) else fsrc
            st0, st1 = float(s.get("src_t0", t0)), float(s.get("src_t1", t1))
        else:
            src, st0, st1 = render, t0, t1   # no speaker source declared -> use render
        n = max(2, min(6, int((st1-st0)/0.3)+1)); step = (st1-st0)/n
        tops=[]
        for i in range(n):
            t = st0 + step*(i+0.5)
            for (x,y,w,h) in faces_at(src, round(t,2), casA, casB):
                tops.append((w*h, y, y+h))
        if not tops:
            facts.append(f"{s['label']}: лицо не найдено (вероятно UI/тайтл-бит) — пропуск"); continue
        tops.sort(reverse=True)  # largest faces first
        big = tops[:max(3,len(tops)//2)]
        med_top = statistics.median(b[1] for b in big)
        med_bot = statistics.median(b[2] for b in big)
        overlap = not (y1 < med_top or y0 > med_bot)
        facts.append(f"{s['label']}: текст[{y0}..{y1}] vs лицо[{int(med_top)}..{int(med_bot)}] {'ПЕРЕСЕЧЕНИЕ' if overlap else 'ok'}")
        if overlap:
            fails.append(f"СУБТИТР НА ЛИЦЕ [{s['label']}]: текст y[{y0}..{y1}] пересекает лицо y[{int(med_top)}..{int(med_bot)}] — опусти текст ниже {int(med_bot)+30} или подними над {int(med_top)-30}")
    verdict = "FAIL" if fails else "PASS"
    json.dump({"verdict":verdict,"render":os.path.basename(render),"fails":fails,"facts":facts},
              open(os.path.join(os.path.dirname(render) or ".", ".subface-verdict.json"),"w"),
              ensure_ascii=False, indent=2)
    print(f"========== SUBTITLE-FACE: {verdict} ==========")
    for f in facts: print("  ·", f)
    for f in fails: print("  ✗", f)
    sys.exit(0 if verdict=="PASS" else 1)

if __name__ == "__main__":
    main()
