#!/usr/bin/env python3
"""Классический сплит: сверху футаж донора, снизу двойник ЦЕЛИКОМ.
Никаких вырезок, обрезки плеч и чёрных квадратов."""
import sys, os, subprocess, json
import numpy as np, cv2
det = cv2.FaceDetectorYN.create("$HOME/.claude/skills/replicate-viral/models/yunet.onnx", "", (320, 320))

proj, donor, out = sys.argv[1], sys.argv[2], sys.argv[3]
W, H = 1080, 1920
SPLIT = int(H * 0.50)          # шов посередине

# двойники подряд
tw = sorted([f for f in os.listdir(f"{proj}/heygen") if f.startswith("twin-") and f.endswith(".mp4")])
caps = [cv2.VideoCapture(f"{proj}/heygen/{f}") for f in tw]
dcap = cv2.VideoCapture(donor)
dn = int(dcap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = 25.0

raw = out + ".raw.mp4"
vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
ci, n = 0, 0
while ci < len(caps):
    ok, tf = caps[ci].read()
    if not ok:
        ci += 1
        continue
    # верх: кадр донора по нормированному времени, зона ЕГО спикера отрезана
    dcap.set(cv2.CAP_PROP_POS_FRAMES, min(dn - 1, int(n / max(1, sum(int(c.get(cv2.CAP_PROP_FRAME_COUNT)) for c in caps)) * dn)))
    okd, df = dcap.read()
    top = np.full((SPLIT, W, 3), 245, np.uint8)
    if okd:
        dh, dw = df.shape[:2]
        # ПОКАДРОВО: где именно у автора начинается лицо. Замер: обычно 0.57H,
        # но на крупных планах поднимается до 0.25H — фиксированный рез тащил его лицо.
        # ФИКСИРОВАННЫЙ верх, как у донора: его панель занимает верхние 0.50H.
        # Умный рез по фону срезал саму панель — отказался от него.
        cut_to = int(dh * 0.50)
        # где у донора КРУПНЫЙ ПЛАН (верх кадра тёмный/телесный, панели нет) — верх не берём
        g = cv2.cvtColor(df[0:int(dh*0.45)], cv2.COLOR_BGR2HSV)
        skin = ((g[:,:,0] < 30) & (g[:,:,1] > 40) & (g[:,:,2] > 55)).mean()
        if skin > 0.10:
            cut_to = 0
        if cut_to > int(dh * 0.10):
            cut = df[0:cut_to, :]
            k = W / dw
            rs = cv2.resize(cut, (W, int(cut.shape[0] * k)), interpolation=cv2.INTER_LANCZOS4)
            hh = min(SPLIT, rs.shape[0])
            top[0:hh] = rs[0:hh]
            if hh < SPLIT:
                top[hh:] = rs[-1] if rs.shape[0] else 245
        else:
            top[:] = last_panel if 'last_panel' in dir() else 245
    # низ: двойник ЦЕЛИКОМ, вписан по ширине, ничего не режем
    th, tww = tf.shape[:2]
    k2 = W / tww
    tr = cv2.resize(tf, (W, int(th * k2)), interpolation=cv2.INTER_LANCZOS4)
    bot_h = H - SPLIT
    if tr.shape[0] >= bot_h:
        y0 = int((tr.shape[0] - bot_h) * 0.18)        # берём верхнюю часть - там лицо
        bot = tr[y0:y0 + bot_h]
    else:
        bot = np.full((bot_h, W, 3), 20, np.uint8)
        bot[0:tr.shape[0]] = tr
    frame = np.vstack([top, bot])
    vw.write(frame)
    n += 1
for c in caps: c.release()
dcap.release(); vw.release()
print(f"· кадров {n}")

# звук из двойников
lst = "/tmp/tw.txt"
open(lst, "w").write("".join(f"file '{proj}/heygen/{f}'\n" for f in tw))
subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",lst,"-vn","-c:a","aac","-b:a","192k","-ar","48000","/tmp/tw.m4a"],check=True)
subprocess.run(["ffmpeg","-y","-v","error","-i",raw,"-i","/tmp/tw.m4a","-map","0:v:0","-map","1:a:0",
                "-c:v","libx264","-crf","18","-preset","medium","-pix_fmt","yuv420p","-c:a","copy","-shortest",out],check=True)
os.remove(raw)
print(f"OK {out}")
