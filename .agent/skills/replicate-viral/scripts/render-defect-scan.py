#!/usr/bin/env python3
"""
render-defect-scan.py — машинный гейт против ПОВТОРЯЮЩИХСЯ дефектов рилза, которые
оператор пропускает глазом по 2-3 кадрам (прецедент reel-DXBt1opj, 4 круга правок).
Сканирует КАЖДУЮ секунду (fps>=4) во временных окнах битов и проверяет ПО ВСЕМ кадрам:

  A. BOX-FILL (рамка сайта не наполовину пустая): в указанном прямоугольнике
     доля «пустых» строк (near-uniform, дисперсия<thr) НЕ должна превышать порог.
     Ловит «верх белый/синий, сайт только снизу, воздух».
  B. POKE (голова вылезает над гранью карточки спикера, не обрезана): в head-x-полосе
     над seam_y должна быть НЕ-фоновая масса (волосы/кожа), И она должна быть
     НЕПРЕРЫВНА через грань (нет резкого обрыва = «волосы обрезаны»).
  C. CORNERS (верхние углы карточки одинаково скруглены): сравнить угловые патчи —
      asymmetry (один острый, другой круглый) = FAIL.
  D. BG-RICH (фон бита не near-uniform-black): дисперсия фоновых зон > порога.

Usage:
  render-defect-scan.py --render out.mp4 --spec scan-spec.json
scan-spec.json:
{
 "beats":[
   {"name":"hook","t0":0.6,"t1":4.9,"box":[60,150,1020,726],"check":["fill"]},
   {"name":"steps","t0":7.4,"t1":23.8,"card":[140,1010,920,1920],"seam_y":1010,"head_x":[300,820],
     "content_box":[90,110,990,940],"check":["poke","corners","bgrich"]},
   {"name":"result","t0":24.6,"t1":30.0,"box":[90,250,990,790],"card":[140,1010,920,1920],
     "seam_y":1010,"head_x":[300,820],"check":["fill","poke","corners"]}
 ]
}
Exit: 0 PASS, 2 FAIL. Печатает per-кадр находки.
"""
import sys, os, json, argparse, subprocess, tempfile, glob, statistics
from PIL import Image

def dur(p):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nw=1:nk=1", p]).decode().strip())

def frames(render, t0, t1, fps, d):
    n=max(2,int((t1-t0)*fps))
    ts=[t0+(t1-t0)*i/(n-1) for i in range(n)]
    out=[]
    for i,t in enumerate(ts):
        f=f"{d}/{int(t*1000):07d}.png"
        subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{t:.3f}","-i",render,
            "-frames:v","1", f], check=True)
        out.append((t,f))
    return out

def row_stats(px,x0,x1,y,step=6):
    vals=[sum(px[x,y][:3])//3 for x in range(x0,x1,step)]
    if len(vals)<2: return 0,0
    return statistics.pvariance(vals), statistics.mean(vals)

def fill_fail(im,box,empty_var=16,max_empty_frac=0.22):
    """МАКС НЕПРЕРЫВНАЯ полоса светлых почти-однотонных строк / высоту box = пустой воздух
       (как навигация-на-пустом-синем у AdCentri или белый верх TATTOO). Разбросанные светлые
       строки цветного сайта НЕ считаются — только КОНТИНУАЛЬНАЯ полоса void."""
    x0,y0,x1,y1=box; px=im.load(); W,H=im.size
    x0,x1=max(0,x0),min(W,x1); y0,y1=max(0,y0),min(H,y1)
    rows=list(range(y0,y1,4));
    if not rows: return 0.0
    run=best=0
    for y in rows:
        v,m=row_stats(px,x0,x1,y)
        if v<empty_var and m>52: run+=1; best=max(best,run)   # uniform И ЯРКИЙ
        else: run=0
    return best/len(rows)   # доля высоты, занятая самой длинной пустой полосой

def blackband_frac(im,frame_box):
    """макс непрерывная полоса near-BLACK однотонных строк во ВСЁМ кадре-окне / высоту
       = пустая чёрная рамка (прецедент: опущенный аватар открыл чёрный фон сверху).
       Не считаем самый низ (platform-bleed)."""
    x0,y0,x1,y1=frame_box; px=im.load(); W,H=im.size
    x0,x1=max(0,x0),min(W,x1); y0,y1=max(0,y0),min(H,y1)
    rows=list(range(y0,y1,4)); run=best=0
    for y in rows:
        v,m=row_stats(px,x0,x1,y)
        if v<4 and m<8: run+=1; best=max(best,run)   # ПУРЕ #000 void (#spk-фон); тёмный сайт/grid lum>10 не ловим
        else: run=0
    return best/max(len(rows),1)

def bg_lum_var(im,zones):
    px=im.load(); vals=[]
    for (x0,y0,x1,y1) in zones:
        for y in range(y0,y1,12):
            for x in range(x0,x1,12):
                vals.append(sum(px[x,y][:3])//3)
    return statistics.pvariance(vals) if len(vals)>1 else 0

_CC=None
def poke_state(fp,seam_y):
    """face-detect: макушка < seam => вылет (1); макушка >= seam => обрезана/внутри (0); нет лица => None (skip)"""
    global _CC
    import cv2
    if _CC is None: _CC=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    img=cv2.imread(fp); g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    f=_CC.detectMultiScale(g,1.1,5,minSize=(120,120))
    if f is None or len(f)==0: return None
    x,y,w,h=sorted(f,key=lambda b:-b[2])[0]
    hairtop=max(0,y-int(h*0.42))
    return 1 if hairtop < seam_y-8 else 0   # вылет если макушка выше грани

def box_hardcuts(frames_list,box):
    """число РЕЗКИХ межкадровых скачков в box (loop-reset/дёрганье). Легитимные смены сайта = 1-2;
       больше = зацикленный короткий клип прыгает назад = дёргается (прецедент workplace-loop)."""
    from PIL import ImageChops, ImageStat
    x0,y0,x1,y1=box; prev=None; cuts=0
    for (t,fp) in frames_list:
        im=Image.open(fp).convert("RGB").crop((x0,y0,x1,y1))
        if prev is not None:
            d=ImageChops.difference(prev,im); m=ImageStat.Stat(d).mean
            if sum(m)/3 > 44: cuts+=1   # большой прыжок (loop-reset), не плавная анимация
        prev=im
    return cuts

def intro_topbar_rows(im, top_box, flat_var=14):
    """Правило 4 (intro без полос): сколько ПОДРЯД верхних строк = однотонная
    горизонтальная серая/белая ПОЛОСА (дисперсия яркости по ширине ~0, средняя яркость
    «серый/белый» = не контентная картинка). Ловит «intro не на весь экран, полоса сверху».
    Возвращает (max_continuous_bar_rows, scanned_rows). top_box=[x0,y0,x1,y1] = верхняя зона."""
    x0,y0,x1,y1=top_box; px=im.load(); W,H=im.size
    x0,x1=max(0,x0),min(W,x1); y0,y1=max(0,y0),min(H,y1)
    rows=list(range(y0,y1,2)); run=best=0
    for y in rows:
        v,m=row_stats(px,x0,x1,y,step=4)
        # «полоса» = почти нулевая вариация ПО ШИРИНЕ (плоский цвет) И яркость серо/белая (>120)
        if v<flat_var and m>120: run+=1; best=max(best,run)
        else: run=0
    return best, max(len(rows),1)

def corner_round(im,card):
    """возвращает (left_bgfrac,right_bgfrac) угловых патчей 28x28 у верхних углов;
       скруглённый угол => угол патча = фон (прозрачность/тёмный) => высокая bgfrac."""
    x0,y0,x1,y1=card; px=im.load(); W,H=im.size; s=30
    def bgfrac(cx,cy,corner):
        cnt=tot=0
        for dy in range(s):
            for dx in range(s):
                x=cx+dx if corner=='L' else cx-dx
                y=cy+dy
                if 0<=x<W and 0<=y<H:
                    r,g,b=px[x,y][:3]; tot+=1
                    # «угол скруглён» если внешний треугольник тёмный (фон)
                    if dx+dy< s*0.7 and (r+g+b)//3<40: cnt+=1
        return cnt/max(tot,1)
    return bgfrac(x0,y0,'L'), bgfrac(x1-1,y0,'R')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--render",required=True); ap.add_argument("--spec",required=True)
    ap.add_argument("--fps",type=float,default=5.0)
    a=ap.parse_args()
    spec=json.load(open(a.spec))
    D=dur(a.render); fails=[]; facts=[]
    with tempfile.TemporaryDirectory() as td:
        for beat in spec["beats"]:
            t0=max(0,beat["t0"]); t1=min(D,beat["t1"]); checks=beat.get("check",[])
            fr=frames(a.render,t0,t1,a.fps,td)
            fillbad=pokebad=cornerbad=bgbad=pokeseen=blackbad=introbad=0
            intro_maxbar=0
            for (t,fp) in fr:
                im=Image.open(fp).convert("RGB")
                if "intro" in checks:
                    tb=beat.get("top_box",[0,0,1080,beat.get("bar_max_h",200)])
                    bar_rows=beat.get("bar_min_rows",24)  # ~48px подряд = реальная полоса, не тонкая кромка
                    nbar,_nrows=intro_topbar_rows(im,tb)
                    intro_maxbar=max(intro_maxbar,nbar)
                    if nbar>=bar_rows: introbad+=1
                if "fill" in checks and "box" in beat:
                    ef=fill_fail(im,beat["box"])
                    if ef>0.40: fillbad+=1  # >40% непрерывной пустой полосы = реальный void (не белый хедер сайта)
                if "noblack" in checks:
                    fb=beat.get("frame_box",[0,0,1080,1440])
                    if blackband_frac(im,fb)>0.22: blackbad+=1  # >22% непрерывной чёрной полосы = пустая рамка
                if "poke" in checks and "card" in beat:
                    ps=poke_state(fp,beat["seam_y"])
                    if ps is not None:
                        pokeseen+=1
                        if ps==0: pokebad+=1   # макушка не выше грани = обрезано/внутри
                if "corners" in checks and "card" in beat:
                    lf,rf=corner_round(im,beat["card"])
                    if abs(lf-rf)>0.22: cornerbad+=1   # один угол острый, другой круглый
                if "bgrich" in checks and "content_box" in beat:
                    cb=beat["content_box"]
                    zones=[[20,300,120,1700],[960,300,1060,1700]]  # боковые поля
                    if bg_lum_var(im,zones)<8: bgbad+=1
                im.close()
            N=len(fr)
            hardcuts=0
            if "jitter" in checks and "box" in beat:
                hardcuts=box_hardcuts(fr,beat["box"])
            facts.append(f'[{beat["name"]}] кадров={N} fill_bad={fillbad} poke_bad={pokebad}/{pokeseen} corner_bad={cornerbad} bg_bad={bgbad} black_bad={blackbad} hardcuts={hardcuts} intro_bad={introbad} intro_maxbar={intro_maxbar}')
            if "intro" in checks and introbad> N*0.15: fails.append(f'{beat["name"]}: INTRO НЕ НА ВЕСЬ ЭКРАН — однотонная серая/белая ПОЛОСА сверху в {introbad}/{N} кадрах (макс {intro_maxbar} строк подряд). Ролик в интро должен быть на весь экран как в оригинале, без полос/пустых зон сверху')
            if "noblack" in checks and blackbad> N*0.12: fails.append(f'{beat["name"]}: ПУСТАЯ ЧЁРНАЯ ПОЛОСА (рамка) в {blackbad}/{N} кадрах — закрыть контентом/фоном')
            if "jitter" in checks and hardcuts> beat.get("max_cuts",2): fails.append(f'{beat["name"]}: ДЁРГАНЬЕ/ЛУП — {hardcuts} резких скачков в рамке (>порога {beat.get("max_cuts",2)}); короткий клип зациклен. Брать ПОЛНОЕ окно, single play без stream_loop')
            if "fill" in checks and fillbad> N*0.15: fails.append(f'{beat["name"]}: РАМКА ПОЛУПУСТАЯ (воздух) в {fillbad}/{N} кадрах')
            if "poke" in checks and pokeseen>0 and pokebad> pokeseen*0.2: fails.append(f'{beat["name"]}: ГОЛОВА ОБРЕЗАНА/НЕТ ВЫЛЕТА над гранью в {pokebad}/{pokeseen} кадрах с лицом')
            if "corners" in checks and cornerbad> N*0.15: fails.append(f'{beat["name"]}: УГЛЫ КАРТОЧКИ АСИММЕТРИЧНЫ в {cornerbad}/{N} кадрах')
            if "bgrich" in checks and bgbad> N*0.5: fails.append(f'{beat["name"]}: ФОН near-uniform-BLACK в {bgbad}/{N} кадрах')
    print("== render-defect-scan ==")
    for f in facts: print("  ·",f)
    if fails:
        print("-- FAIL --")
        for f in fails: print("  ✗",f)
        print("verdict: FAIL"); sys.exit(2)
    print("verdict: PASS"); sys.exit(0)

if __name__=="__main__": main()
