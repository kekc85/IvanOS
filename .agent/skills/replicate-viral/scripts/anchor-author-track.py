#!/usr/bin/env python3
"""anchor-author-track.py — ПОКАДРОВЫЙ детект автора для continuous-anchor реплик
(МЕТОД v7). Корень: пер-битный детект (раз на бит, на midpoint) ПРОТЕКАЕТ на
переходах/краях бита — автор появляется/съезжает/меняет PiP↔full внутри секунды
. Лечение: КАЖДЫЙ кадр.

Автор отличается от двойника и от галерейных лиц инструмента ТЁМНЫМ ФОНОМ СТУДИИ
(bg V < BG_DARK); двойник = тёплый фон, выводы сервиса = светлый/пёстрый фон.

Состояние на кадр:
  FULL  — крупный автор (talking-head) → в реплике этот бит = двойник на весь экран
  PIP   — автор в верхней панели (cy<SY) как кружок/комментарий → значок поверх (cx,cy,r)
  NONE  — автора нет ИЛИ он в нижней панели (cy>=SY, split его срежет) → чистый split

FULL «липкий» + дилатация: крупный автор НИКОГДА не должен стать угловым значком
(сглаживание не перебивает FULL→PIP). PIP-позиция сглажена медианой окна.

usage: anchor-author-track.py <src.mp4> --out track.json [--sy 900] [--bg-dark 125]
"""
import argparse, cv2, numpy as np, json, os
from collections import Counter
YUNET=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","models","yunet.onnx")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("--out",required=True)
    ap.add_argument("--sy",type=int,default=900); ap.add_argument("--bg-dark",type=int,default=125)
    a=ap.parse_args(); SY=a.sy
    cap=cv2.VideoCapture(a.src); det=cv2.FaceDetectorYN.create(YUNET,"",(1080,1920))
    FPS=cap.get(cv2.CAP_PROP_FPS); raw=[]
    while True:
        ok,fr=cap.read()
        if not ok: break
        h,w=fr.shape[:2]; det.setInputSize((w,h)); _,faces=det.detect(fr)
        cand=[]
        for f in (faces if faces is not None else []):
            x,y,fw,fh=[int(v) for v in f[:4]]; cf=float(f[14])
            if cf<0.70 or fw<85: continue
            x0=max(0,x-fw//2);x1=min(w,x+fw+fw//2);y0=max(0,y-fh//2);y1=min(h,y+fh+fh//2)
            bg=cv2.cvtColor(fr[y0:y1,x0:x1],cv2.COLOR_BGR2HSV)[:,:,2].mean()
            if bg>=a.bg_dark: continue          # светлый фон = двойник/галерея, не автор-студия
            cand.append((x+fw//2,y+fh//2,fw,fh))
        big=[c for c in cand if c[2]>240 or c[3]>290]
        if big: raw.append(["FULL",None]); continue
        top=[c for c in cand if c[1]<SY+50]
        if top:
            cx,cy,fw,fh=max(top,key=lambda c:c[2]*c[3])
            r=int(min(360,max(260,fh*1.7))); raw.append(["PIP",[cx,int(cy-fh*0.22),r]])
        else: raw.append(["NONE",None])
    cap.release()
    states=[r[0] for r in raw]
    full=set(i for i,s in enumerate(states) if s=="FULL")
    dil=set(j for i in full for j in range(i-6,i+7))
    def mode_win(i,wd=7):
        aa=[states[j] for j in range(max(0,i-wd),min(len(states),i+wd+1)) if states[j]!="FULL"]
        return Counter(aa).most_common(1)[0][0] if aa else "NONE"
    track=[]; lastb=None
    for i in range(len(raw)):
        st="FULL" if i in dil else mode_win(i); b=None
        if st=="PIP":
            near=[raw[j][1] for j in range(max(0,i-6),min(len(raw),i+7)) if raw[j][0]=="PIP" and raw[j][1]]
            if near: b=[int(np.median([n[k] for n in near])) for k in range(3)]; lastb=b
            else: b=lastb or [940,290,300]
        track.append({"f":i,"t":round(i/FPS,3),"s":st,"b":b})
    json.dump({"fps":FPS,"n":len(track),"sy":SY,"track":track},open(a.out,"w"))
    print("track ->",a.out,"states",dict(Counter(x["s"] for x in track)))

if __name__=="__main__": main()
