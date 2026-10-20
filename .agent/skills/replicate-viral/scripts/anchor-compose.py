#!/usr/bin/env python3
"""anchor-compose.py — ПОКАДРОВАЯ сборка continuous-anchor реплики (МЕТОД v7).
Двойник = непрерывный якорь; автор закрыт ВЕЗДЕ:
  FULL → двойник на весь экран
  PIP  → split (верх=AIR-контент source[0:SY], низ=двойник) + СТАТИЧНЫЙ значок
         поверх кружка автора (центр в центр, радиус автора + запас = перекрытие 1:1)
  NONE → split без значка (нижний автор срезан кропом)
🔴 Значок (НЕ дубль лица двойника) ставится ТОЛЬКО где реально лицо автора (track=PIP);
   на галерейные/демо-лица инструмента НЕ ставим (они = продукт, держим 1:1).

usage:
  anchor-compose.py --src <src.mp4> --avatar <avatar.mp4> --track track.json
      --icon badge.png --out body.mp4 [--sy 900] [--work build/_anchor]
"""
import argparse, cv2, json, os, subprocess, statistics as st
from PIL import Image
YUNET=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","models","yunet.onnx")

def avatar_face_center(path):
    cap=cv2.VideoCapture(path); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    det=cv2.FaceDetectorYN.create(YUNET,"",(320,320)); xs=[];ys=[]
    for r in (0.2,0.4,0.6,0.8):
        cap.set(cv2.CAP_PROP_POS_FRAMES,int(n*r)); ok,fr=cap.read()
        if not ok: continue
        h,w=fr.shape[:2]; det.setInputSize((w,h)); _,f=det.detect(fr)
        if f is not None and len(f): a=max(f,key=lambda z:z[2]*z[3]); xs.append(a[0]+a[2]/2); ys.append(a[1]+a[3]/2)
    cap.release(); return (int(st.median(xs)) if xs else 540, int(st.median(ys)) if ys else 540)

def main():
    ap=argparse.ArgumentParser()
    for k in ("src","avatar","track","icon","out"): ap.add_argument("--"+k,required=True)
    ap.add_argument("--sy",type=int,default=900); ap.add_argument("--work",default="build/_anchor")
    a=ap.parse_args(); SY=a.sy; W,H=1080,1920; botH=H-SY
    fsd=os.path.join(a.work,"fs"); fad=os.path.join(a.work,"fa"); fod=os.path.join(a.work,"fo")
    for d in (fsd,fad,fod): os.makedirs(d,exist_ok=True)
    fps=cv2.VideoCapture(a.src).get(cv2.CAP_PROP_FPS) or 23.976
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",a.src,"-q:v","3",fsd+"/%05d.jpg","-y"],check=True)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",a.avatar,"-vf","fps=%f"%fps,"-q:v","3",fad+"/%05d.jpg","-y"],check=True)
    AVX,AVY=avatar_face_center(a.avatar); avy=int(max(0,min(H-botH,AVY-botH*0.40)))
    track=json.load(open(a.track))["track"]
    badge=Image.open(a.icon).convert("RGBA")
    fs=sorted(os.listdir(fsd)); fa=sorted(os.listdir(fad)); n=min(len(fs),len(fa),len(track))
    for i in range(n):
        e=track[i]; stt=e["s"]; b=e["b"]
        if stt=="PIP" and b and 380<b[0]<700 and b[2]>300: stt="FULL"   # центр+крупный → full, не центр-значок
        av=Image.open(os.path.join(fad,fa[i])).convert("RGB")
        if av.size!=(W,H): av=av.resize((W,H))
        if stt=="FULL": out=av
        else:
            src=Image.open(os.path.join(fsd,fs[i])).convert("RGB")
            if src.size!=(W,H): src=src.resize((W,H))
            out=Image.new("RGB",(W,H)); out.paste(src.crop((0,0,W,SY)),(0,0)); out.paste(av.crop((0,avy,W,avy+botH)),(0,SY))
            if stt=="PIP" and b:
                cx,cy,r=b; bd=badge.resize((2*r,2*r)); out.paste(bd,(cx-r,cy-r),bd)
        out.save(os.path.join(fod,"%05d.jpg"%(i+1)),quality=92)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-framerate",str(fps),"-i",fod+"/%05d.jpg",
                    "-r","30","-c:v","libx264","-crf","17","-preset","veryfast","-pix_fmt","yuv420p",a.out,"-y"],check=True)
    print("body ->",a.out,"frames",n,"avatar-face",(AVX,AVY))

if __name__=="__main__": main()
