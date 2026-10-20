#!/usr/bin/env python3
"""motion-check.py — ГАРАНТИЯ: UI/сайт-вставки ДВИГАЮТСЯ (не статичная картинка).
Прецедент: автор ≥50 раз требовал «не статичную картинку, а видео» — машинной проверки не было.
Для каждого окна-вставки сэмплит подряд идущие кадры и считает средний межкадровый
пиксель-diff. Ниже порога = СТАТИКА = FAIL. (Тайтл-карты и чистый спикер в spec НЕ включаем.)
motion-spec.json: [{"label":"framer","t0":11.7,"t1":14.8,"min":0.35}, ...]
Usage: motion-check.py <render.mp4> <motion-spec.json>  Exit 0 PASS / 1 FAIL."""
import sys, os, json, subprocess
import numpy as np
try: import cv2
except ImportError: print("FAIL: cv2 нет — гарантия движения не проверена"); sys.exit(1)
render, spec = sys.argv[1], sys.argv[2]
wins = json.load(open(spec))
cap = cv2.VideoCapture(render)
fails, facts = [], []
def diff_at(t0,t1,n=7):
    ds=[]; prev=None
    for i in range(n):
        t=t0+(t1-t0)*(i+0.5)/n
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,fr=cap.read()
        if not ok: break
        fr=cv2.resize(fr,(270,480))
        if prev is not None: ds.append(float(np.abs(fr.astype(int)-prev.astype(int)).mean()))
        prev=fr
    return sum(ds)/len(ds) if ds else 0.0
for w in wins:
    mv=diff_at(float(w["t0"]),float(w["t1"])); mn=float(w.get("min",0.35))
    facts.append(f"{w['label']}: motion {mv:.2f} (min {mn})")
    if mv < mn: fails.append(f"СТАТИЧНАЯ ВСТАВКА [{w['label']}]: motion {mv:.2f} < {mn} — это картинка, а не видео. Нужна анимация/движение")
verdict="FAIL" if fails else "PASS"
json.dump({"verdict":verdict,"fails":fails,"facts":facts},
          open(os.path.join(os.path.dirname(render) or ".",".motion-verdict.json"),"w"),ensure_ascii=False,indent=2)
print(f"========== MOTION: {verdict} ==========")
for f in facts: print("  ·",f)
for f in fails: print("  ✗",f)
sys.exit(0 if verdict=="PASS" else 1)