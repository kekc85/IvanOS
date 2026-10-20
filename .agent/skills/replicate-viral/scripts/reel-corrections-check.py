#!/usr/bin/env python3
"""
reel-corrections-check.py — машинная проверка ПРАВОК автора по Reels, чтобы они НИКОГДА не повторялись.
Каждая правка, которую автор прислал по ролику и которую можно проверить регуляркой/таймингом,
кодируется здесь как блокирующий чек. Вызывается из selftest.sh (FAIL = нельзя заявлять «готово»).
Цикл самоулучшения: новая правка по Reels → строка сюда → больше не повторяется.

Usage: python3 reel-corrections-check.py <project-dir>
Exit 0 = все правки соблюдены, 1 = нарушение (печатает какие + дату правки).
"""
import sys, os, re, json, glob

proj = sys.argv[1] if len(sys.argv) > 1 else "."
html_paths = (glob.glob(os.path.join(proj, "index.html"))
              + glob.glob(os.path.join(proj, "fullreel", "index.html"))
              + glob.glob(os.path.join(proj, "opening", "index.html")))
fails, warns = [], []

html = ""
for p in html_paths:
    try: html += open(p, encoding="utf-8", errors="ignore").read()
    except Exception: pass
# strip comments (anti-cheat)
src = re.sub(r"/\*.*?\*/", "", html, flags=re.S)
src = re.sub(r"(?m)//.*$", "", src)

# ===== ПРАВКИ АВТОРА (Reels) — каждая = блокирующий чек =====

# [по решению автора] «зачем блюр на лицо налепил» — GSAP fromTo с filter:blur на аватаре = immediateRender
# применяет blur с t=0, лицо размыто весь ролик. Запрет: fromTo blur на #av/#avwrap без immediateRender:false.
for m in re.finditer(r"fromTo\(\s*['\"]#av(?:wrap)?['\"][^;]*?\}\s*,\s*\{[^}]*\}", src):
    seg = m.group(0)
    if "blur" in seg and "immediateRender" not in seg:
        fails.append("[по решению автора] БЛЮР НА ЛИЦЕ: fromTo с filter:blur на #av/#avwrap без immediateRender:false — "
                     "blur применится с t=0, лицо размыто весь ролик. Добавь immediateRender:false или убери блюр.")
        break

# [по решению автора] «при зум-ине всё выезжает за края» — зум всей UI-карточки выталкивает текст за границы.
# Запрет: scale-твин на '.frame .zoom' UI-карточек (динамика — анимация элементов, не зум карточки).
if re.search(r"\.frame \.zoom['\"]\s*,\s*\{\s*scale", src) or re.search(r"#c-(gh|cfg|mdl) \.frame \.zoom['\"][^)]*scale", src):
    fails.append("[по решению автора] ЗУМ UI-КАРТОЧКИ: scale-твин на '.frame.zoom' — выталкивает текст за края ('выезжает'). "
                 "Убери зум карточки; динамику делай анимацией элементов (печать/курсор/фильтр/draw-in).")

# [по решению автора] «статичные сраные скриншоты, нет динамики» — UI должен быть анимированным HTML (живой DOM),
# не <img src=...png> как UI. Запрет: <img src=...(github|config|models|terminal).png> внутри .card.
if re.search(r"<img[^>]+src=['\"][^'\"]*(github|config|models|terminal|repo)[^'\"]*\.png", html, re.I):
    warns.append("[по решению автора] СТАТИЧНЫЙ UI-СКРИН: <img...png> как UI-карточка — автор забраковал ('сраные скриншоты'). "
                 "Строй UI анимированным HTML-мокапом (живые DOM-элементы).")

# [по решению автора] «highlight в пустоте / при зуме съезжает» — подсветки привязывать к элементу
# (hlOnEl/getBoundingClientRect), не по литеральным %/px. Запрет: hl-бокс позиционируется литералом.
if re.search(r"(?:hl|hlOnEl)\(\s*['\"][\w-]+['\"]\s*,\s*\{\s*left:\s*['\"]?\d", src):
    fails.append("[по решению автора] HIGHLIGHT В ПУСТОТЕ: подсветка задана литеральными left/top (%/px), не привязана к элементу. "
                 "Используй hlOnEl(hlId, targetSelector) с getBoundingClientRect — рамка липнет к контенту, не съезжает.")

# [по решению автора] «субтитры не выровнены, ставки короткие/длинные» — тайминг караоке ровный, без мельканий.
karaoke = glob.glob(os.path.join(proj, "fullreel", "assets", "karaoke.json"))
if karaoke:
    try:
        KAR = json.load(open(karaoke[0], encoding="utf-8"))
        short = [g for g in KAR if (g[1] - g[0]) < 0.34]
        if short:
            fails.append("[по решению автора] РВАНЫЙ ТАЙМИНГ СУБТИТРОВ: %d групп <0.34с (мелькают). Нормализуй мин ~0.4с." % len(short))
    except Exception:
        pass

# ===== [по решению автора council-reel] RENDER-based чеки (нужен fullreel/layout.json) =====
import subprocess
def _loud(path):
    try:
        out=subprocess.run(["ffmpeg","-i",path,"-af","loudnorm=print_format=json","-f","null","-"],capture_output=True,text=True,timeout=180).stderr
        return float(json.loads(out[out.rfind("{"):out.rfind("}")+1]).get("input_i",0))
    except Exception: return None

# GSAP scale на элементе, у которого CSS transform содержит scale()/rotate() как БАЗУ — GSAP-анимация scale
# задаёт АБСОЛЮТНОЕ значение и затирает базу → элемент скачет в размере/вылезает/на лицо.
# (Чистый translate%/translateX(-50%) центрирование НЕ опасен: GSAP декомпозирует матрицу и сохраняет translate —
#  именно поэтому council/router с translateX(-50%)+scale работают и одобрены. Прецедент бага: #plate{transform:scale(.64)} + tl.to(#plate,{scale}).)
_css_tf=set(m.group(1) for m in re.finditer(r"#([\w-]+)\s*\{[^}]*?transform\s*:\s*([^;}]*)", html)
            if re.search(r"\b(scale|rotate|matrix)\s*\(", m.group(2)))
gtc=[e for e in re.findall(r"(?:to|fromTo)\(\s*['\"]#([\w-]+)['\"][^)]*?\bscale\b", src) if e in _css_tf]
if gtc:
    fails.append("[по решению автора] GSAP-TRANSFORM: scale-анимация на #%s, у которого ЕСТЬ CSS transform — ЗАТИРАЕТ его → элемент вылезает/на лицо. Анимируй обёртку или xPercent." % ",".join(sorted(set(gtc))))

lj=glob.glob(os.path.join(proj,"fullreel","layout.json"))+glob.glob(os.path.join(proj,"layout.json"))
rends=[f for f in glob.glob(os.path.join(proj,"**","*.mp4"),recursive=True)
       if not any(s in f for s in ("/node_modules/","/assets/","/public/")) and not re.search(r"avatar|voice|seg\d|norm-|full-avatar",os.path.basename(f))]
if lj and rends:
    L=json.load(open(lj[0])); render=max(rends,key=os.path.getmtime)
    li=_loud(render); lmin=L.get("loudness_min",-16)
    if li is not None and li<lmin: fails.append("[по решению автора] ТИХО: %.1f LUFS < %d — HeyGen-TTS тихий, нормализуй loudnorm I=-14 («голос охереть тихий»)" % (li,lmin))
    ct=L.get("card_top"); cb=L.get("caption_band",[0,0])
    if ct is not None and ct<L.get("ig_top",288): fails.append("[по решению автора] IG-ВЫРЕЗ ВЕРХ: card_top=%s < 288 — площадка съест верх карточки («графика высоко»)" % ct)
    if cb[1] and cb[1]>L.get("ig_bottom",1440): fails.append("[по решению автора] IG-ВЫРЕЗ НИЗ: субтитр %d > 1440 — обрежет плеер-UI («субтитры на дне»)" % cb[1])
    try:
        import cv2
        cap=cv2.VideoCapture(render)
        cas=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
        casa=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_alt2.xml')
        fmin=L.get("face_min_top",700); cardb=L.get("card_bottom",0); capf=conf=black=0; t=0.3
        while t<60:
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,fr=cap.read()
            if not ok: break
            t+=0.3
            if ct is not None:
                reg=fr[ct:(cardb or ct+400),60:1020]
                if reg.size and float(reg.mean())<12: black+=1
            g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); bs=[]
            for c in (cas,casa):
                for b in c.detectMultiScale(g,1.1,5,minSize=(160,160)):
                    if int(b[1])>fmin: bs.append((int(b[0]),int(b[1]),int(b[2]),int(b[3])))
            if not bs: continue
            fb=max(bs,key=lambda f:f[2]*f[3]); ftop=fb[1]; fbot=fb[1]+fb[3]
            if cb[1] and not(cb[1]<ftop or cb[0]>fbot): capf+=1
            if cardb and ftop<cardb: conf+=1
        if capf>0: fails.append("[по решению автора] СУБТИТР НА ЛИЦЕ: %d кадров — caption_band пересекает лицо («субтитры на лице, не смей»)" % capf)
        if conf>0: fails.append("[по решению автора] КАРТОЧКА НА ЛИЦЕ: %d кадров — лицо выше card_bottom («вставки на лице и голове»)" % conf)
        if black>5: fails.append("[по решению автора] ЧЁРНЫЙ ЭКРАН: ~%.1fс пустой чёрный верх («нахер чёрный экран поставил»)" % (black*0.3))
    except ImportError: pass
elif not lj:
    warns.append("[по решению автора] layout.json не задан — render-гео-чеки (субтитр/карточка-на-лице, громкость, safe-zone) пропущены")

if fails:
    print("REEL-CORRECTIONS: FAIL")
    for f in fails: print("  ✗ " + f)
    for w in warns: print("  ⚠ " + w)
    sys.exit(1)
print("REEL-CORRECTIONS: PASS (правки автора соблюдены)")
for w in warns: print("  ⚠ " + w)
sys.exit(0)
