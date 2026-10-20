#!/usr/bin/env python3
"""
reel-layout-audit.py — машинный гейт ПЕРЕД показом рилза: ловит ровно те дефекты,
которые автор дефектовал руками в сессии в даты запуска.2026 (цикл самоулучшения — не повторять).

Проверяет (по ФИНАЛЬНОМУ рендеру + layout.json проекта):
  1. CAPTION-ON-FACE  — реальное лицо аватара ниже полосы субтитров (face.top >= caption_band[1])
  2. CARD-ON-FACE     — лицо ниже нижней грани верхней UI-карточки (face.top >= card_bottom)
  3. IG-SAFE-ZONE     — карточка ниже верхнего выреза (card_top>=ig_top), субтитр выше нижнего (cap_bottom<=ig_bottom)
  4. LOUDNESS         — Integrated LUFS >= loudness_min (HeyGen-TTS тихий → нормализовать до -14)

layout.json в корне проекта (или fullreel/), напр.:
  {"caption_band":[872,952],"card_bottom":858,"face_min_top":760,
   "ig_top":288,"ig_bottom":1440,"loudness_min":-16}

Usage: reel-layout-audit.py <render.mp4> <layout.json>
Exit 0 = PASS, 1 = FAIL. Пишет <render_dir>/.layout-audit-verdict.json
"""
import sys, os, json, subprocess, re

def loudness(path):
    try:
        out = subprocess.run(["ffmpeg","-i",path,"-af","loudnorm=print_format=json","-f","null","-"],
                             capture_output=True, text=True, timeout=180).stderr
        j = json.loads(out[out.rfind("{"):out.rfind("}")+1])
        return float(j.get("input_i", 0))
    except Exception:
        return None

def main():
    if len(sys.argv) < 3:
        print("usage: reel-layout-audit.py <render.mp4> <layout.json>"); sys.exit(2)
    render, lpath = sys.argv[1], sys.argv[2]
    if not os.path.isfile(render): print("FAIL: no render"); sys.exit(1)
    L = json.load(open(lpath))
    cap_band = L.get("caption_band", [0,0])
    card_bottom = L.get("card_bottom", 0)
    fmin = L.get("face_min_top", 700)
    ig_top, ig_bottom = L.get("ig_top",288), L.get("ig_bottom",1440)
    lmin = L.get("loudness_min", -16)

    fails, facts = [], []

    # ---- LOUDNESS ----
    li = loudness(render)
    if li is None:
        facts.append("loudness: не измерено")
    else:
        facts.append(f"loudness: {li:.1f} LUFS (мин {lmin})")
        if li < lmin: fails.append(f"ТИХО: {li:.1f} LUFS < {lmin} — нормализуй loudnorm I=-14 (HeyGen-TTS тихий)")

    # ---- IG SAFE-ZONE (config) ----
    card_top = L.get("card_top")
    if card_top is not None and card_top < ig_top:
        fails.append(f"КАРТОЧКА В IG-ВЫРЕЗЕ: card_top={card_top} < {ig_top} — площадка съест верх")
    if cap_band[1] > ig_bottom:
        fails.append(f"СУБТИТР В IG-ВЫРЕЗЕ: caption низ {cap_band[1]} > {ig_bottom} — обрежет плеер-UI")
    facts.append(f"safe-zone: card_top={card_top} cap_band={cap_band} ig=[{ig_top},{ig_bottom}]")

    # ---- FACE vs CAPTION/CARD (per-frame face-detect) ----
    try:
        import cv2, numpy as np
        cap = cv2.VideoCapture(render)
        cas  = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
        casa = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_alt2.xml')
        def rface(fr):
            g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); bs=[]
            for c in (cas,casa):
                for b in c.detectMultiScale(g,1.1,5,minSize=(160,160)):
                    if b[1] > fmin: bs.append(tuple(int(x) for x in b))   # real avatar face only (below UI)
            return max(bs,key=lambda f:f[2]*f[3]) if bs else None
        capf=conf=0; n=0; mintop=9999
        t=0.3
        while t < 60:
            cap.set(cv2.CAP_PROP_POS_MSEC, t*1000); ok,fr=cap.read()
            if not ok: break
            fb=rface(fr); t+=0.3
            if fb is None: continue
            n+=1; ftop=fb[1]; fbot=fb[1]+fb[3]; mintop=min(mintop,ftop)
            # caption band must be ABOVE the face
            if not (cap_band[1] < ftop or cap_band[0] > fbot): capf+=1
            # card bottom must be ABOVE the face
            if ftop < card_bottom: conf+=1
        facts.append(f"face: проверено {n} кадров, min top={mintop}")
        if capf>0: fails.append(f"СУБТИТР НА ЛИЦЕ: {capf} кадров — caption_band {cap_band} пересекает лицо")
        if conf>0: fails.append(f"КАРТОЧКА НА ЛИЦЕ: {conf} кадров — лицо выше card_bottom {card_bottom}")
    except ImportError:
        facts.append("face-detect: cv2 не установлен — пропущено")

    verdict = "FAIL" if fails else "PASS"
    json.dump({"verdict":verdict,"render":os.path.basename(render),"fails":fails,"facts":facts},
              open(os.path.join(os.path.dirname(render) or ".", ".layout-audit-verdict.json"),"w"),
              ensure_ascii=False, indent=2)
    print(f"========== LAYOUT-AUDIT: {verdict} ==========")
    for f in facts: print("  ·", f)
    for f in fails: print("  ✗", f)
    sys.exit(0 if verdict=="PASS" else 1)

if __name__ == "__main__":
    main()
