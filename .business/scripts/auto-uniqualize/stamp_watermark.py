#!/usr/bin/env python3
"""Водяная подпись <твой-хэндл> (PNG/JPG/MP4), ЕДИНАЯ позиция на ВСЕХ слайдах (не скачет).
Видео — оверлей PNG-водяка (ffmpeg drawtext недоступен). Usage: stamp_watermark.py <in> <idx> <out>
автор: «зачем ты хаотично на некоторые слайды watermark делаешь» — ротация по углам выглядела
хаотично и лезла на контент. Теперь ОДНА консистентная позиция (низ-право), субтильно, на каждом слайде."""
import sys, subprocess, tempfile, os, json
HANDLE="<твой-хэндл>"
FONT="/System/Library/Fonts/HelveticaNeue.ttc"
# ЕДИНАЯ позиция для ВСЕХ слайдов (консистентно, не скачет по углам)
FIXED_POS=("right","bottom")
def pos_for(i): return FIXED_POS
def _wm_png(W):
    from PIL import Image,ImageDraw,ImageFont
    fs=max(13,W//64); font=ImageFont.truetype(FONT,fs)
    d0=ImageDraw.Draw(Image.new("RGBA",(10,10))); tw=int(d0.textlength(HANDLE,font=font))
    wm=Image.new("RGBA",(tw+8,fs+10),(0,0,0,0)); d=ImageDraw.Draw(wm)
    d.text((4+1,3+1),HANDLE,font=font,fill=(0,0,0,70)); d.text((4,3),HANDLE,font=font,fill=(255,255,255,120))
    return wm,fs
def normalize_45(im,TW=1080,TH=1350):
    """IG-карусель = ЕДИНОЕ соотношение 4:5 (1080x1350) на ВСЕХ слайдах. GPT выдаёт разнобой
    (0.667/0.75/0.80/0.854) → IG применяет одно соотношение и РЕЖЕТ контент. Приводим к 1080x1350
    БЕЗ обрезки: fit-inside + паддинг медианным цветом 4 углов (для full-bleed дизайна с однородным
    фоном = бесшовно). автор: «у нас одно расширение, чтобы ничего не обрезалось»."""
    from PIL import Image
    im=im.convert("RGB"); w,h=im.size
    if (w,h)==(TW,TH): return im
    cs=[im.getpixel((2,2)),im.getpixel((w-3,2)),im.getpixel((2,h-3)),im.getpixel((w-3,h-3))]
    bg=tuple(int(sum(c[i] for c in cs)/4) for i in range(3))
    s=min(TW/w,TH/h); nw,nh=max(1,round(w*s)),max(1,round(h*s))
    cv=Image.new("RGB",(TW,TH),bg); cv.paste(im.resize((nw,nh),Image.LANCZOS),((TW-nw)//2,(TH-nh)//2))
    return cv
def stamp_image(inp,idx,out):
    from PIL import Image
    im=normalize_45(Image.open(inp)).convert("RGBA"); W,H=im.size
    wm,fs=_wm_png(W); ww,wh=wm.size; m=max(14,W//55)
    hx,hy=pos_for(idx)
    x={"left":m,"center":(W-ww)//2,"right":W-ww-m}[hx]
    y={"top":m,"center":(H-wh)//2,"bottom":H-wh-m}[hy]
    im.alpha_composite(wm,(int(x),int(y)))
    im.convert("RGB").save(out,"PNG" if out.lower().endswith("png") else "JPEG",quality=95)
def stamp_video(inp,idx,out):
    pr=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",str(inp)],capture_output=True,text=True)
    s=json.loads(pr.stdout)["streams"][0]; W=s["width"]
    wm,fs=_wm_png(W); p=tempfile.mktemp(suffix=".png"); wm.save(p)
    hx,hy=pos_for(idx)
    xe={"left":"W*0.035","center":"(W-w)/2","right":"W-w-W*0.035"}[hx]
    ye={"top":"H*0.03","center":"(H-h)/2","bottom":"H-h-H*0.03"}[hy]
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(inp),"-i",p,"-filter_complex",
                    f"[0:v][1:v]overlay=x={xe}:y={ye}","-c:a","copy","-c:v","libx264","-pix_fmt","yuv420p","-crf","20",str(out)],check=True)
    os.remove(p)
def stamp(inp,idx,out):
    (stamp_video if str(inp).lower().endswith(".mp4") else stamp_image)(inp,idx,out)
if __name__=="__main__":
    stamp(sys.argv[1],int(sys.argv[2]),sys.argv[3])
