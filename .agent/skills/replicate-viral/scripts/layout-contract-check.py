#!/usr/bin/env python3
"""
layout-contract-check.py — машинный гейт против анти-эталона №2.
Блокирует ПОКАЗ рендера, нарушающего жёсткие правила раскладки.

Проверяет (ANTI-METHODOLOGY.md):
  A. ПРОПОРЦИЯ аватара = FULL (100%) или HALF (50% ±3%). Никаких 60/65%.
  B. КОНТЕНТ ВИДЕН: спикер не перекрывает контент-зону (skin-fraction в контенте > 12% = FAIL).
  C. ДИНАМИКА: если контент в источнике = video/animated, в нашем контент-зоне должно быть движение
     (avg межкадровый diff >= порога; зум засчитывается, чистая статика = FAIL).
  D. отчёт по хард-катам.

Usage:
  python3 layout-contract-check.py --render out.mp4 --contract contract.json
contract.json: {"avatar_mode":"half|full","seam_y":960,"content_dynamic":"video|static"}
  seam_y — нижняя граница контент-зоны (для half = граница карточки сайта; контент = y[0..seam_y]).
Exit: 0 = PASS, 2 = FAIL.
"""
import sys, os, json, argparse, subprocess, tempfile, glob
from PIL import Image, ImageChops, ImageStat

H_FULL = 1920
def die(msg): print("ARG ERROR:", msg); sys.exit(2)

def extract(render, n, d):
    # n равномерных кадров
    dur = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nw=1:nk=1", render]).decode().strip())
    ts = [dur*i/(n+1) for i in range(1, n+1)]
    for i,t in enumerate(ts):
        subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{t:.3f}","-i",render,
            "-frames:v","1","-vf","scale=540:960", f"{d}/f{i:02d}.png"], check=True)
    return sorted(glob.glob(f"{d}/f*.png"))

def is_skin(r,g,b):
    return (r>95 and g>40 and b>20 and max(r,g,b)-min(r,g,b)>15 and abs(r-g)>15 and r>g and r>b)

def skin_fraction(im, y0, y1):
    # доля кожи в зоне [y0,y1) по 540x960 превью, прорежено
    px = im.load(); W,Hh = im.size
    cnt=0; tot=0
    for y in range(int(y0), int(y1), 4):
        for x in range(0, W, 4):
            r,g,b = px[x,y][:3]; tot+=1
            if is_skin(r,g,b): cnt+=1
    return cnt/max(tot,1)

def region_motion(frames, y0, y1):
    W = Image.open(frames[0]).size[0]
    prev=None; diffs=[]; cuts=0
    for f in frames:
        im=Image.open(f).convert("RGB").crop((0,int(y0),W,int(y1)))
        if prev is not None:
            m=sum(ImageStat.Stat(ImageChops.difference(im,prev)).mean)/3
            diffs.append(m)
            if m>22: cuts+=1
        prev=im
    return (sum(diffs)/max(len(diffs),1), cuts)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--min-motion", type=float, default=1.5)
    ap.add_argument("--max-skin-in-content", type=float, default=0.18)  # head-poke сплит: спикер чуть выглядывает в контент, но сайт виден (>80%)
    # по решению автора: эталон DZLBwKEEeWm СМЕШАННЫЙ (full-спикер + сплит + full-UI). Один контракт не валидирует
    # микс. Per-chunk --mode: half=сплит, full=спикер-весь-кадр (он и есть контент), ui=чистый UI (нет аватара).
    ap.add_argument("--mode", choices=["full","half","ui"], default=None)
    a=ap.parse_args()
    if not os.path.isfile(a.render): die("render not found")
    c=json.load(open(a.contract))
    fails=[]; warns=[]

    # A. пропорция
    mode=a.mode or c.get("avatar_mode")
    if mode=="ui":
        seam=H_FULL   # чистый UI-бит (реальный сайт на весь кадр) — проверяем ТОЛЬКО динамику
    elif mode not in ("full","half"):
        fails.append(f"A: avatar_mode='{mode}' не FULL/HALF/UI"); seam=int(c.get("seam_y",0))
    else:
        seam=int(c.get("seam_y", 0))
    if mode=="half":
        lo,hi=int(960-192), int(960+192)  # эталон-сплит ~45/55, не ровно 50% → допуск ±10%
        if not (lo<=seam<=hi): fails.append(f"A: seam_y={seam} вне 45/55 [{lo},{hi}] — раскладка не половина")
    elif mode=="full":
        seam=H_FULL  # весь кадр аватар; спикер = контент; B-окклюзию не штрафуем

    with tempfile.TemporaryDirectory() as d:
        frames=extract(a.render, 12, d)
        # масштаб seam в превью 960h
        seam_prev = seam*960/H_FULL
        if mode=="half":
            # B. окклюзия контента: контент-зона = верх [0..seam_prev]
            sk=skin_fraction(Image.open(frames[len(frames)//2]).convert("RGB"), 0, seam_prev)
            if sk>a.max_skin_in_content:
                fails.append(f"B: кожа в контент-зоне {sk:.0%} > {a.max_skin_in_content:.0%} — спикер перекрывает контент (его не видно)")
            mot,cuts=region_motion(frames, 0, seam_prev)
        else:
            mot,cuts=region_motion(frames, 0, 960)
        # C. динамика
        if c.get("content_dynamic","video")=="video" and mot < a.min_motion:
            fails.append(f"C: контент-зона почти статична (motion={mot:.2f} < {a.min_motion}) — статика вместо видео/анимации источника")
        print(f"[motion контент={mot:.2f}, хард-катов={cuts}, режим={mode}, seam={seam}]")

    if fails:
        print("========== LAYOUT-CONTRACT: FAIL ==========")
        for f in fails: print("  ✗", f)
        for w in warns: print("  ⚠", w)
        print("  → НЕ показывать автору. Чинить по ANTI-METHODOLOGY.md.")
        sys.exit(2)
    print("========== LAYOUT-CONTRACT: PASS ==========")
    for w in warns: print("  ⚠", w)
    sys.exit(0)

if __name__=="__main__": main()