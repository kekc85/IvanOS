#!/usr/bin/env python3
"""make-icon-badge.py — круглый значок-бейдж для перекрытия PiP-кружка автора
(continuous-anchor реплики, МЕТОД v7). Вместо дубля лица двойника в PiP автора
кладём СТАТИЧНЫЙ значок (сервиса/Claude). Извлекает оранжевую/яркую марку логотипа
по цвету ИЛИ кладёт логотип целиком в круг + белое кольцо.

usage:
  make-icon-badge.py <logo.png> --out badge.png [--bg 20,22,20] [--d 600]
      [--extract-color]   # вырезать цветную марку (sunburst) и центрировать
"""
import argparse, numpy as np
from PIL import Image, ImageDraw

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("logo"); ap.add_argument("--out",required=True)
    ap.add_argument("--bg",default="20,22,20"); ap.add_argument("--d",type=int,default=600)
    ap.add_argument("--extract-color",action="store_true")
    a=ap.parse_args()
    D=a.d; bg=tuple(int(x) for x in a.bg.split(","))+(255,)
    src=Image.open(a.logo).convert("RGBA")
    badge=Image.new("RGBA",(D,D),(0,0,0,0)); dd=ImageDraw.Draw(badge)
    dd.ellipse([0,0,D-1,D-1],fill=bg)
    if a.extract_color:
        arr=np.array(src); r,g,b=arr[:,:,0].astype(int),arr[:,:,1].astype(int),arr[:,:,2].astype(int)
        col=(r>150)&(g>60)&(g<180)&(b<150)&(r-b>40)   # warm/orange brand mark
        ys,xs=np.where(col)
        if len(xs):
            pad=int((xs.max()-xs.min())*0.18)
            crop=src.crop((max(0,xs.min()-pad),max(0,ys.min()-pad),xs.max()+pad,ys.max()+pad))
            s=max(crop.size); sq=Image.new("RGBA",(s,s),(0,0,0,0)); sq.paste(crop,((s-crop.width)//2,(s-crop.height)//2))
            mark=sq.resize((int(D*0.56),int(D*0.56))); badge.paste(mark,((D-mark.width)//2,(D-mark.height)//2),mark)
    else:
        logo=src.resize((D,D)); mask=Image.new("L",(D,D),0); ImageDraw.Draw(mask).ellipse([0,0,D-1,D-1],fill=255)
        badge.paste(logo,(0,0),mask)
    ImageDraw.Draw(badge).ellipse([4,4,D-5,D-5],outline=(255,255,255,235),width=9)
    badge.save(a.out); print("badge ->",a.out,badge.size)

if __name__=="__main__": main()