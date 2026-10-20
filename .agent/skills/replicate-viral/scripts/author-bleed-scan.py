#!/usr/bin/env python3
"""author-bleed-scan.py — машинный гейт: НИГДЕ в выходе не должно остаться ЛИЦА АВТОРА.

Корень (сессия <твой-прошлый-проект> по решению автора): агент проверял ВЫБОРКОЙ и трижды пропускал
автора — он лез full-frame в открытии и перед CTA (детектор смотрел только низ),
а не только в нижней панели сплита. Лечение: сплошной ПОКАДРОВЫЙ скан всего кадра.

Метод: в ОРИГИНАЛЕ покадрово ищем лицо (по всему кадру). Где у автора есть лицо —
сравниваем тот же бокс в НАШЕМ выходе с оригиналом. Если регион ПОЧТИ СОВПАДАЕТ
с оригиналом (мы НЕ заменили автора двойником/контентом) → BLEED = FAIL с таймкодом.
Если отличается (там наш двойник или контент) → OK.

Usage: author-bleed-scan.py --orig ORIGINAL.mp4 --out FINAL.mp4 [--step 0.1] [--sim 0.86]
Exit 0 = чисто / 2 = найден автор в выходе.
"""
import sys, argparse, cv2, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--step", type=float, default=0.1)
    ap.add_argument("--sim", type=float, default=0.86,
                    help="порог схожести регион-лица ориг↔выход: выше = автор не заменён (BLEED)")
    a = ap.parse_args()
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    co = cv2.VideoCapture(a.orig); cu = cv2.VideoCapture(a.out)
    dur = min(co.get(7)/co.get(5), cu.get(7)/cu.get(5))
    H = int(co.get(4)); W = int(co.get(3))
    bleeds = []; checked = 0; t = 0.0
    while t < dur:
        co.set(cv2.CAP_PROP_POS_MSEC, t*1000); cu.set(cv2.CAP_PROP_POS_MSEC, t*1000)
        ok1, fo = co.read(); ok2, fu = cu.read()
        if not (ok1 and ok2): break
        g = cv2.cvtColor(fo, cv2.COLOR_BGR2GRAY)
        faces = sorted(face.detectMultiScale(g, 1.12, 5, minSize=(110,110)),
                       key=lambda b: -b[2]*b[3])
        if faces:
            checked += 1
            x,y,w,h = faces[0]
            ro = fo[y:y+h, x:x+w]; ru = fu[y:y+h, x:x+w]
            if ro.shape == ru.shape and ro.size:
                # гистограммная корреляция по серому = насколько регион тот же
                go = cv2.cvtColor(ro, cv2.COLOR_BGR2GRAY); gu = cv2.cvtColor(ru, cv2.COLOR_BGR2GRAY)
                ho = cv2.calcHist([go],[0],None,[64],[0,256]); hu = cv2.calcHist([gu],[0],None,[64],[0,256])
                cv2.normalize(ho,ho); cv2.normalize(hu,hu)
                sim = cv2.compareHist(ho, hu, cv2.HISTCMP_CORREL)
                # плюс пиксельная схожесть (структура)
                diff = 1.0 - float(np.mean(cv2.absdiff(go, gu)))/255.0
                if sim > a.sim and diff > 0.80:
                    bleeds.append((round(t,2), int(y+h//2), round(sim,3)))
        t += a.step
    if bleeds:
        print(f"FAIL: автор в выходе на {len(bleeds)} кадрах (из {checked} с лицом). Примеры:")
        for b in bleeds[:25]: print(f"  t={b[0]}s  face_cy={b[1]}  sim={b[2]}")
        sys.exit(2)
    print(f"PASS: автор заменён везде ({checked} кадров с лицом проверено, 0 утечек)")
    sys.exit(0)

if __name__ == "__main__":
    main()
