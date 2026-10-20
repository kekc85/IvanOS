#!/usr/bin/env python3
"""scan_all.py - СПЛОШНОЙ ПОКАДРОВЫЙ СКАН, КАЖДЫЙ КАДР, без выборки.

Автор по решению автора: «сам осматривай каждую миллисекунду». По ЗАКОНУ 0a скилла
разреженная выборка запрещена - именно она была корнем всех повторов.

Проверяет 6 классов дефектов, каждый из которых уже вылезал в этой работе:
  D1 автор в кадре        - лицо/кожа автора там, где кадр идёт из футажа донора
  D2 чужой текст          - латиница автора не закрыта нашим субтитром
  D3 заливка поперёк тела - подложка легла на двойника (бежевая полоса)
  D4 обрезанный лоб       - лицо двойника упирается в верхний край
  D5 пустой кадр          - заливка/чернота без содержания
  D6 субтитр вне кадра    - наш текст обрезан краями
"""
import sys, json
import numpy as np
import cv2

YUNET = "$HOME/.claude/skills/replicate-viral/models/yunet.onnx"


def scan(ours_path, orig_path):
    det = cv2.FaceDetectorYN.create(YUNET, "", (320, 320))
    ours = cv2.VideoCapture(ours_path)
    orig = cv2.VideoCapture(orig_path)
    no = int(ours.get(cv2.CAP_PROP_FRAME_COUNT))
    nd = int(orig.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = ours.get(cv2.CAP_PROP_FPS) or 25.0
    d = {k: [] for k in ("D1", "D2", "D3", "D4", "D5", "D6")}
    i = 0
    while True:
        ok, fr = ours.read()
        if not ok:
            break
        t = round(i / fps, 2)
        H, W = fr.shape[:2]
        S = H // 2
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)

        det.setInputSize((W, H))
        _, ff = det.detect(fr)
        face = None
        if ff is not None and len(ff):
            b = max(ff, key=lambda x: x[2] * x[3])
            if float(b[14]) >= 0.7:
                face = b

        # кадр пришёл из футажа донора? (почти совпадает с кадром донора)
        di = min(nd - 1, int(i / max(1, no) * nd))
        orig.set(cv2.CAP_PROP_POS_FRAMES, di)
        ok2, dfr = orig.read()
        from_donor = False
        if ok2:
            a = cv2.resize(fr, (120, 213))
            bb = cv2.resize(dfr, (120, 213))
            from_donor = float(np.abs(a.astype(int) - bb.astype(int)).mean()) < 18

        # --- D1: автор в кадре ---
        if from_donor:
            hit = face is not None and float(face[3]) > H * 0.08
            if not hit:
                hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
                sk = ((hsv[:, :, 0] < 28) & (hsv[:, :, 1] > 38) &
                      (hsv[:, :, 1] < 190) & (hsv[:, :, 2] > 50)).astype(np.uint8)
                sk = cv2.morphologyEx(sk, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
                nk, _, st, _ = cv2.connectedComponentsWithStats(sk, 8)
                if max((st[c, cv2.CC_STAT_AREA] for c in range(1, nk)), default=0) > W * H * 0.03:
                    hit = True
            if hit:
                d["D1"].append(t)

        # --- D2: чужой текст (крупные буквы вне зоны нашего субтитра) ---
        m = (g > 200).astype(np.uint8)
        m[int(H * 0.80):] = 0            # наш субтитр внизу не считаем
        m[int(S * 0.86):S + 30] = 0      # зона нашего субтитра у шва
        nn, _, st2, _ = cv2.connectedComponentsWithStats(m, 8)
        for c in range(1, nn):
            bh = st2[c, cv2.CC_STAT_HEIGHT]
            bw = st2[c, cv2.CC_STAT_WIDTH]
            ba = st2[c, cv2.CC_STAT_AREA]
            by = st2[c, cv2.CC_STAT_TOP]
            # 🔴 ЛАТИНИЦА АВТОРА, а не элементы интерфейса. Логотипы и надписи внутри
            # UI (Kimi, Gemini, API KEYS) - законный футаж по ЗАКОНУ 1, их не считаем:
            # они мелкие и в верхней части панели, субтитр автора крупный и у шва.
            # 🔴 ЗОНА ДВОЙНИКА ИСКЛЮЧЕНА: срабатывания на y=1044-1357 - это блики на
            # лице и белой футболке аватара, а не текст автора. Чужой субтитр физически
            # может быть только в панели донора, выше шва.
            if 45 < bh < 200 and 20 < bw < 750 and 900 < ba < 60000 \
               and (H * 0.30 < by < S * 0.86):
                d["D2"].append(t)
                break

        # --- D3: плоская заливка поперёк ТЕЛА двойника ---
        if face is not None:
            fy, fh = int(face[1]), int(face[3])
            for y0 in range(fy + fh, min(H - 80, fy + fh * 3), 20):
                band = fr[y0:y0 + 80]
                if band.size and band.std() < 3.0:
                    d["D3"].append(t)
                    break

        # --- D4: лоб двойника у края ---
        if face is not None:
            fy = float(face[1])
            if fy < 18 or (S < fy < S + 22):
                d["D4"].append(t)

        # --- D5: пустой кадр ---
        if float((cv2.Canny(g, 60, 160) > 0).mean()) < 0.0022:
            d["D5"].append(t)

        # --- D6: наш субтитр обрезан краем ---
        # 🔴 БЕЛЫЙ ФОН ≠ СУБТИТР. Первый заход считал 406к белых пикселей на всю
        # ширину (это фон панели) за «обрезанный текст». Ищем компоненты размером
        # с букву, а не просто светлые пиксели.
        zone = g[int(H * 0.80):]
        sm = (zone > 235).astype(np.uint8)
        if 0 < sm.mean() < 0.35:
            nb, _, sb, _ = cv2.connectedComponentsWithStats(sm, 8)
            lets = [c for c in range(1, nb)
                    if 20 < sb[c, cv2.CC_STAT_HEIGHT] < 90 and 5 < sb[c, cv2.CC_STAT_WIDTH] < 140]
            if lets:
                x0 = min(sb[c, cv2.CC_STAT_LEFT] for c in lets)
                x1 = max(sb[c, cv2.CC_STAT_LEFT] + sb[c, cv2.CC_STAT_WIDTH] for c in lets)
                if x0 < 6 or x1 > W - 7:
                    d["D6"].append(t)

        i += 1
    ours.release()
    orig.release()
    return d, i, fps


if __name__ == "__main__":
    res, n, fps = scan(sys.argv[1], sys.argv[2])
    names = {"D1": "автор в кадре", "D2": "чужой текст", "D3": "заливка на теле",
             "D4": "лоб у края", "D5": "пустой кадр", "D6": "субтитр обрезан"}
    print(f"СКАН {sys.argv[1]}: {n} кадров, каждый\n")
    total = 0
    for k in ("D1", "D2", "D3", "D4", "D5", "D6"):
        v = res[k]
        total += len(v)
        mark = "ЧИСТО" if not v else f"{len(v)} кадров  {v[:6]}"
        print(f"  {k} {names[k]:18s}: {mark}")
    print(f"\nИТОГО дефектных срабатываний: {total}")
    json.dump(res, open(sys.argv[1] + ".scan.json", "w"))
