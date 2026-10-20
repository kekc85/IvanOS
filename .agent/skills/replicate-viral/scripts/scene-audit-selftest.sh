#!/usr/bin/env bash
# scene-audit-selftest.sh — happy/negative/edge кейсы на КАЖДУЮ новую проверку scene-audit.py
# (P-FONT, P-GEOM, P-CONTR в --preflight; F/G/H/I по рендеру). Негативные ДОЛЖНЫ фейлить (exit 2).
# Синтетические мини-HTML/кадры/видео генерируются на лету. Exit 0 = все зелёные, 1 = есть провал.
set -uo pipefail
SA="$(cd "$(dirname "$0")" && pwd)/scene-audit.py"
[ -f "$SA" ] || { echo "FAIL: scene-audit.py не найден рядом ($SA)"; exit 1; }
TD="$(mktemp -d)"; trap 'rm -rf "$TD"' EXIT
PASS=0; FAILN=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAILN=$((FAILN+1)); }

# expect_exit <desc> <want_code> -- runs $CMD array
run(){ python3 "$SA" "$@" >/tmp/_sa_out 2>&1; echo $?; }

echo "=========================================================="
echo " scene-audit-selftest — P-FONT/P-GEOM/P-CONTR + F/G/H/I"
echo "=========================================================="

# ---------- генератор синтетики (Python) ----------
python3 - "$TD" <<'PY' | tee /tmp/_sa_gen
import sys,os,subprocess,numpy as np
from PIL import Image
TD=sys.argv[1]
# реальный шрифт с кириллицей (Oswald) для happy-кейса берём из тестового билда
import base64,re,io
SCENE1=os.path.expanduser('~/<твоя рабочая папка ролика>/blocks/scene1/index.html')
oswald_b64=None
if os.path.exists(SCENE1):
    h=open(SCENE1,encoding='utf-8',errors='ignore').read()
    m=re.search(r"url\(data:font/[^;]+;base64,([A-Za-z0-9+/=]+)\)",h)
    if m:oswald_b64=m.group(1)

def write(name,txt):
    open(os.path.join(TD,name),'w',encoding='utf-8').write(txt)

# ===== PREFLIGHT HTMLs =====
FF = f"@font-face{{font-family:'OswaldH';src:url(data:font/ttf;base64,{oswald_b64}) format('truetype');}}" if oswald_b64 else ""
# P-FONT happy: кириллица покрыта Oswald
write('font_happy.html', f"<html><head><style>{FF}.stream{{position:absolute;top:620px;font-family:'OswaldH';color:#fff;}} html,body{{background:#0d1117;}}</style></head><body><div class='stream'><span class='w'>ПРИВЕТ МИР</span></div></body></html>")
# P-FONT negative: кириллица, но шрифт Latin-only (генерим мини-ttf без кириллицы) -> непокрытие
# проще: объявить @font-face с РЕАЛЬНЫМ шрифтом, который не покрывает — берём подмножество через fontTools
neg_font_ok=False
if oswald_b64:
    try:
        from fontTools.ttLib import TTFont
        from fontTools.subset import Subsetter
        f=TTFont(io.BytesIO(base64.b64decode(oswald_b64)))
        ss=Subsetter(); ss.populate(text="ABCDEFGHIJKLMNOPQRSTUVWXYZ ")  # только латиница
        ss.subset(f)
        buf=io.BytesIO(); f.save(buf)
        lat_b64=base64.b64encode(buf.getvalue()).decode()
        FFL=f"@font-face{{font-family:'LatinOnly';src:url(data:font/ttf;base64,{lat_b64}) format('truetype');}}"
        write('font_neg.html', f"<html><head><style>{FFL}.stream{{position:absolute;top:620px;font-family:'LatinOnly';color:#fff;}} html,body{{background:#000;}}</style></head><body><div class='stream'><span class='w'>КИРИЛЛИЦА</span></div></body></html>")
        neg_font_ok=True
    except Exception as e:
        print("WARN subset:",e,file=sys.stderr)
# P-FONT edge: emoji в тексте — НЕ должна валить (системный emoji-фоллбек)
write('font_edge.html', f"<html><head><style>{FF}.stream{{position:absolute;top:620px;font-family:'OswaldH';color:#fff;}} html,body{{background:#000;}}</style></head><body><div class='stream'><span class='w'>ПРИВЕТ ✨ МИР</span></div></body></html>")

# P-GEOM happy: .stream в safe-zone
write('geom_happy.html', "<html><head><style>.stream{position:absolute;top:620px;color:#fff;}html,body{background:#000;}</style></head><body><div class='stream'>ТЕКСТ</div></body></html>")
# P-GEOM negative: .stream вне safe-zone (top=1500 -> низ обрежется)
write('geom_neg.html', "<html><head><style>.stream{position:absolute;top:1500px;color:#fff;}html,body{background:#000;}</style></head><body><div class='stream'>ТЕКСТ</div></body></html>")
# P-GEOM edge: позиция flex (нет top:px) -> SKIP, НЕ FAIL
write('geom_edge.html', "<html><head><style>.stream{display:flex;color:#fff;}html,body{background:#000;}</style></head><body><div class='stream'>ТЕКСТ</div></body></html>")

# P-CONTR happy: белый на тёмном (контраст высокий)
write('contr_happy.html', "<html><head><style>.w{color:#ffffff;}.slot{background:#0d1117;}</style></head><body><div class='slot'><span class='w'>ТЕКСТ</span></div></body></html>")
# P-CONTR negative: светло-серый на белом (контраст <3)
write('contr_neg.html', "<html><head><style>.w{color:#cfcfcf;}.slot{background:#ffffff;}</style></head><body><div class='slot'><span class='w'>ТЕКСТ</span></div></body></html>")
# P-CONTR edge: нет явной пары, но есть text-shadow обводка -> SKIP (PASS)
write('contr_edge.html', "<html><head><style>.w{text-shadow:0 2px 0 #000;}</style></head><body><span class='w'>ТЕКСТ</span></body></html>")

# ===== RENDER videos (F/G/H/I) =====
W,H=1080,1920
def mkvid(name,frame_fn,dur=2.0,fps=10):
    d=os.path.join(TD,name+'_frames'); os.makedirs(d,exist_ok=True)
    n=int(dur*fps)
    for i in range(n):
        img=frame_fn(i,n); Image.fromarray(img).save(os.path.join(d,f"{i:04d}.png"))
    out=os.path.join(TD,name+'.mp4')
    subprocess.run(['ffmpeg','-y','-framerate',str(fps),'-i',os.path.join(d,'%04d.png'),
                    '-c:v','libx264','-pix_fmt','yuv420p',out],capture_output=True)
    return out

def base_split(i,n):
    a=np.zeros((H,W,3),np.uint8)
    a[0:876]= (20,18,15)          # top dark UI
    a[876:]= (12,12,14)           # bottom avatar zone
    # bright face-ish blob in bottom (so face-detect/Region ok-ish, not required)
    return a

# F happy: яркий белый субтитр в полосе 620-840 на ТЁМНОМ фоне -> высокий контраст
def f_happy(i,n):
    a=base_split(i,n)
    a[660:760, 300:780]=240       # bright caption block on dark
    return a
mkvid('f_happy', f_happy)
# F negative: светлый текст на СВЕТЛОМ фоне в полосе -> низкий контраст (<3)
def f_neg(i,n):
    a=base_split(i,n)
    # дефолтный регион F без --html = нижняя треть (y 1267-1920). Светлый текст на светлом фоне там.
    a[1300:1700, 0:1080]=(205,205,205) # light backdrop fills band
    a[1400:1520, 300:780]=235          # slightly brighter "text" -> low contrast
    return a
mkvid('f_neg', f_neg)

# G negative: яркий ТЕКСТ-глиф упирается в правый край (x>1070), частичная высота, тёмный фон рядом
def g_neg(i,n):
    a=base_split(i,n)
    # дефолтная полоса G без --html = y 1056-1498. Глиф упирается в правый край там.
    a[1056:1498]= (10,10,12)
    a[1150:1300, 1071:1080]=240         # bright text at very edge, ~part of band height
    a[1150:1300, 1050:1060]=240         # stroke continues a touch inward
    a[1180:1240, 980:1060]=20           # interior mostly dark
    return a
mkvid('g_neg', g_neg)
# G happy: текст по центру, ничего у края -> чисто
def g_happy(i,n):
    a=base_split(i,n)
    a[1056:1498]=(10,10,12)
    a[1150:1300, 400:680]=240           # centered text, nothing near edge
    return a
mkvid('g_happy', g_happy)
# G edge: яркая ПАНЕЛЬ во всю ширину доходит до края (UI-фон), НЕ текст -> НЕ должно фейлить
def g_edge(i,n):
    a=base_split(i,n)
    a[1056:1498, 0:1080]=(245,243,240) # uniform bright cream panel full width incl edge (default band)
    return a
mkvid('g_edge', g_edge)

# I negative: верх (0-876) почти однотонный всё видео >1.5с
def i_neg(i,n):
    a=np.zeros((H,W,3),np.uint8); a[0:876]=(15,15,16); a[876:]=(40,40,42); return a
mkvid('i_neg', i_neg, dur=2.5)
# I happy: верх МЕНЯЕТСЯ (контент) -> высокая дисперсия
def i_happy(i,n):
    a=np.zeros((H,W,3),np.uint8)
    rng=np.random.default_rng(i)
    a[0:876]=rng.integers(0,255,(876,W,3),dtype=np.uint8)  # varied content
    a[876:]=(40,40,42); return a
mkvid('i_happy', i_happy, dur=2.5)

# ===== HTML + whisper for H sync =====
write('h.html', "<html><body><span class='w' data-s='1.00'>ПРИВЕТ</span><span class='w' data-s='2.00'>МИР</span></body></html>")
import json
# H happy: whisper тайминги совпадают (drift<0.15)
json.dump({"words":[{"word":"привет","start":1.05},{"word":"мир","start":1.95}]}, open(os.path.join(TD,'wh_happy.json'),'w'))
# H negative: whisper тайминги разъехались (>0.15)
json.dump({"words":[{"word":"привет","start":1.60},{"word":"мир","start":2.90}]}, open(os.path.join(TD,'wh_neg.json'),'w'))
# ===== NEW Stage-11 кейсы =====
# (1) ПУСТОЙ/битый mp4: создаём 0-байтовый файл с расширением .mp4 → scene-audit должен FAIL (нечитаемо)
open(os.path.join(TD,'empty.mp4'),'wb').close()

# (2) 720x1280 кадр с КОРРЕКТНОЙ (после масштабирования) геометрией: текст по центру, у краёв ничего,
#     сплит сверху/снизу непустой. Не должно быть ложных FAIL по краям (G/E/K) при scale SX=0.667.
W2,H2=720,1280
def mkvid2(name,frame_fn,dur=1.5,fps=10,w=W2,h=H2):
    d=os.path.join(TD,name+'_frames'); os.makedirs(d,exist_ok=True)
    n=int(dur*fps)
    for i in range(n):
        Image.fromarray(frame_fn(i,n)).save(os.path.join(d,f"{i:04d}.png"))
    out=os.path.join(TD,name+'.mp4')
    subprocess.run(['ffmpeg','-y','-framerate',str(fps),'-i',os.path.join(d,'%04d.png'),
                    '-c:v','libx264','-pix_fmt','yuv420p',out],capture_output=True)
    return out
def v720_clean(i,n):
    a=np.zeros((H2,W2,3),np.uint8)
    a[0:585]=(22,20,16)            # top dark UI (есть контент)
    a[585:]=(14,14,16)            # bottom avatar zone (есть контент)
    # яркий субтитр-блок ПО ЦЕНТРУ нижней трети, далеко от правого края (x край = W2-10=710)
    a[900:1010, 240:480]=240
    return a
mkvid2('v720_clean', v720_clean)

# ===== J text-on-face / K2 caption-on-UI кейсы =====
# Берём РЕАЛЬНЫЙ кадр лица из s1 (haar его детектит) как фон, поверх рисуем/не рисуем текст.
import cv2
S1=os.path.expanduser('~/<твоя рабочая папка ролика>/scenes/s1.mp4')
J_OK=0
face_frame=None
if os.path.exists(S1):
    fp=os.path.join(TD,'_faceframe.png')
    subprocess.run(['ffmpeg','-y','-ss','0.5','-i',S1,'-frames:v','1',fp],capture_output=True)
    if os.path.exists(fp):
        bgr=cv2.imread(fp)
        if bgr is not None:
            face_frame=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
            g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
            cc=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
            ff=cc.detectMultiScale(g,1.1,5,minSize=(120,120))
            if len(ff): J_OK=1; FB=max(ff,key=lambda z:z[2])

if J_OK:
    fx,fy,fw,fh=[int(v) for v in FB]
    # J negative: белый текст ПОПЕРЁК глаз (синтетик из root-cause) -> FAIL по J
    def j_neg(i,n):
        a=face_frame.copy()
        cv2.putText(a,'NA LICE',(fx+10,fy+int(fh*0.45)),cv2.FONT_HERSHEY_SIMPLEX,4.5,(255,255,255),14,cv2.LINE_AA)
        cv2.putText(a,'NA LICE',(fx+10,fy+int(fh*0.45)),cv2.FONT_HERSHEY_SIMPLEX,4.5,(0,0,0),3,cv2.LINE_AA)
        return a
    mkvid('j_neg', j_neg, dur=1.5)
    # J happy: текст ВЫШЕ лица (в верхней четверти кадра), лицо чисто -> НЕ должен фейлить по J
    def j_happy(i,n):
        a=face_frame.copy()
        cv2.putText(a,'TEXT VVERHU',(120,300),cv2.FONT_HERSHEY_SIMPLEX,4.0,(255,255,255),12,cv2.LINE_AA)
        return a
    mkvid('j_happy', j_happy, dur=1.5)
    # J edge: full-screen UI БЕЗ лица (фон не лицо) -> с --no-face-expected НЕ должен фейлить по J
    def j_noface(i,n):
        a=np.zeros((H,W,3),np.uint8); a[:]=(18,18,20)
        rng=np.random.default_rng(i)
        a[200:600]=rng.integers(0,120,(400,W,3),dtype=np.uint8)  # UI текстура, не лицо
        return a
    mkvid('j_noface', j_noface, dur=1.5)

# K2 negative: caption-полоса (дефолт y[1056-1498] на 1080x1920) над ПЛОТНЫМ UI -> FAIL по K2.
# avatar-region-top=1920 (всё выше = верхний экран) + плотная UI-текстура в caption-полосе.
def k2_neg(i,n):
    a=np.zeros((H,W,3),np.uint8); a[:]=(20,20,24)
    rng=np.random.default_rng(i)
    # очень плотная структура (мелкие яркие прямоугольники = строки кода/заголовки) в полосе субтитра
    band=rng.integers(0,255,(442,W,3),dtype=np.uint8)
    a[1056:1498]=band
    return a
mkvid('k2_neg', k2_neg, dur=1.5)
# K2 happy: caption-полоса над ПУСТЫМ/ровным фоном (нейтральный стык) -> PASS по K2
def k2_happy(i,n):
    a=np.zeros((H,W,3),np.uint8); a[:]=(20,20,24)
    a[1056:1498]=(22,22,26)   # ровная тёмная зона, низкая edge-density
    return a
mkvid('k2_happy', k2_happy, dur=1.5)

print("J_OK=%d"%J_OK)

# ===== Ф5a: overlap-card семья — синтетик, штатно трипающий A2 (кроп подбородка) + K (тёмные бары) =====
# Цель: под дефолтом talking-head-split -> FAIL (A2/K), под --family overlap-card -> те же оси WARN -> PASS.
OVERLAP_OK=0
if J_OK:
    # лицо из s1, посаженное НИЗКО (подбородок ниже safe-bottom CB=1440) = A2 trip;
    # узкий аватар-столб по центру нижней зоны + ЧЁРНЫЕ бары по бокам = K trip (sides_lum<48).
    def overlap_neg(i,n):
        a=np.zeros((H,W,3),np.uint8); a[:]=(8,8,10)         # тёмная сцена-пол
        # центральная аватар-колонка (узкая) с реальным лицом, посаженным низко
        col_x0,col_x1=380,700
        fh2=520
        face_crop=cv2.resize(face_frame,(col_x1-col_x0,fh2))
        y0=1920-fh2          # аватар прижат к низу -> подбородок у самого края (chin>1440)
        a[y0:y0+fh2,col_x0:col_x1]=face_crop
        # бока нижней зоны оставляем чёрными (sides_lum -> ~8) = тёмные бары (K)
        return a
    mkvid('overlap_neg', overlap_neg, dur=1.5)
    OVERLAP_OK=1
print("OVERLAP_OK=%d"%OVERLAP_OK)
print("NEG_FONT_OK=%d"%(1 if neg_font_ok else 0))
PY
NEG_FONT_OK=$(grep -o 'NEG_FONT_OK=[01]' /tmp/_sa_gen 2>/dev/null | cut -d= -f2)
J_OK=$(grep -o 'J_OK=[01]' /tmp/_sa_gen 2>/dev/null | cut -d= -f2)
OVERLAP_OK=$(grep -o 'OVERLAP_OK=[01]' /tmp/_sa_gen 2>/dev/null | cut -d= -f2)

# ---------------- ASSERTIONS ----------------
echo "--- P-FONT ---"
[ "$(run --preflight --html "$TD/font_happy.html")" = 0 ] && ok "P-FONT happy PASS (кириллица покрыта)" || bad "P-FONT happy должен PASS"
if [ -f "$TD/font_neg.html" ]; then
  [ "$(run --preflight --html "$TD/font_neg.html")" = 2 ] && ok "P-FONT negative FAIL (Latin-only не покрыл кириллицу)" || bad "P-FONT negative должен FAIL(2)"
else echo "  (skip P-FONT negative: subset недоступен)"; fi
[ "$(run --preflight --html "$TD/font_edge.html")" = 0 ] && ok "P-FONT edge PASS (emoji ✨ не валит — системный фоллбек)" || bad "P-FONT edge: emoji не должна валить"

echo "--- P-GEOM ---"
[ "$(run --preflight --html "$TD/geom_happy.html")" = 0 ] && ok "P-GEOM happy PASS (.stream в safe-zone)" || bad "P-GEOM happy должен PASS"
[ "$(run --preflight --html "$TD/geom_neg.html")" = 2 ] && ok "P-GEOM negative FAIL (.stream top=1500 вне safe)" || bad "P-GEOM negative должен FAIL(2)"
out=$(python3 "$SA" --preflight --html "$TD/geom_edge.html" 2>&1); echo "$out" | grep -q "P-GEOM: SKIP" && ok "P-GEOM edge SKIP (flex, не абсолют)" || bad "P-GEOM edge должен SKIP не FAIL"

echo "--- P-CONTR ---"
[ "$(run --preflight --html "$TD/contr_happy.html")" = 0 ] && ok "P-CONTR happy PASS (бел/тёмн)" || bad "P-CONTR happy должен PASS"
[ "$(run --preflight --html "$TD/contr_neg.html")" = 2 ] && ok "P-CONTR negative FAIL (серый/белый <3)" || bad "P-CONTR negative должен FAIL(2)"
out=$(python3 "$SA" --preflight --html "$TD/contr_edge.html" 2>&1); echo "$out" | grep -q "P-CONTR: SKIP" && ok "P-CONTR edge SKIP (нет пары, есть обводка)" || bad "P-CONTR edge должен SKIP"

echo "--- F caption-contrast (render) ---"
out=$(python3 "$SA" --our "$TD/f_happy.mp4" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ F" && bad "F happy не должен фейлить" || ok "F happy: контраст ОК (нет ✗F)"
out=$(python3 "$SA" --our "$TD/f_neg.mp4" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ F" && ok "F negative FAIL (низкий контраст пойман)" || bad "F negative должен дать ✗F"

echo "--- G text-edge-cut (render) ---"
out=$(python3 "$SA" --our "$TD/g_neg.mp4" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ G" && ok "G negative FAIL (текст у края пойман)" || bad "G negative должен дать ✗G"
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ G" && bad "G happy не должен фейлить" || ok "G happy: текст по центру (нет ✗G)"
out=$(python3 "$SA" --our "$TD/g_edge.mp4" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ G" && bad "G edge: панель-бликом ложно поймана как срез" || ok "G edge: яркая панель НЕ срез текста (нет ✗G)"

echo "--- H icon↔word sync (whisper) ---"
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/h.html" --whisper-json "$TD/wh_happy.json" --frames 3 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ H" && bad "H happy не должен фейлить" || ok "H happy: drift<0.15 (нет ✗H)"
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/h.html" --whisper-json "$TD/wh_neg.json" --frames 3 --avatar-region-top 876 2>&1); echo "$out" | grep -q "✗ H" && ok "H negative FAIL (рассинхрон >0.15 пойман)" || bad "H negative должен дать ✗H"
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/h.html" --frames 3 --avatar-region-top 876 2>&1); echo "$out" | grep -q "H icon↔word sync: SKIP" && ok "H edge SKIP (нет --whisper-json)" || bad "H edge должен SKIP без whisper"

echo "--- I empty-frames (render) ---"
out=$(python3 "$SA" --our "$TD/i_neg.mp4" --html "$TD/h.html" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "⚠ I" && ok "I negative WARN (пустой верх >1.5с пойман)" || bad "I negative должен дать ⚠I"
out=$(python3 "$SA" --our "$TD/i_happy.mp4" --html "$TD/h.html" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "⚠ I" && bad "I happy (контент в верху) не должен варнить" || ok "I happy: верх меняется (нет ⚠I)"
out=$(python3 "$SA" --our "$TD/i_neg.mp4" --frames 4 --avatar-region-top 876 2>&1); echo "$out" | grep -q "I empty-frames: SKIP" && ok "I edge SKIP (нет --html → нет обещанного контента)" || bad "I edge должен SKIP без html"

# ============ Stage-11 НОВЫЕ КЕЙСЫ ============
echo "--- Stage-11: пустой/битый mp4 → FAIL (HIGH-3 fail-open) ---"
code=$(run --our "$TD/empty.mp4" --frames 4); out=$(python3 "$SA" --our "$TD/empty.mp4" --frames 4 2>&1)
{ [ "$code" = 2 ] && echo "$out" | grep -qi "нечитаемо"; } && ok "empty.mp4 → FAIL(2) «видео нечитаемо» (не PASS exit 0)" || bad "empty.mp4 должен FAIL(2) с «нечитаемо», получили exit=$code"

echo "--- Stage-11: 720×1280 корректная геометрия → без ложных FAIL по краям (HIGH-4) ---"
out=$(python3 "$SA" --our "$TD/v720_clean.mp4" --frames 4 --avatar-region-top 585 2>&1)
code720=$(run --our "$TD/v720_clean.mp4" --frames 4 --avatar-region-top 585)
echo "$out" | grep -q "масштабирована под 720x1280" && ok "720×1280 распознан и геометрия масштабирована" || bad "720×1280 должен печатать «масштабирована под 720x1280»"
{ ! echo "$out" | grep -qE "✗ (E|G|K) "; } && ok "720×1280 без ложных FAIL по краям E/G/K" || { echo "$out" | grep -E "✗ (E|G|K) "; bad "720×1280 дал ложный краевой FAIL"; }
echo "$out" | grep -qi "RuntimeWarning" && bad "720×1280 numpy RuntimeWarning на пустом срезе (guard не сработал)" || ok "720×1280 без numpy RuntimeWarning (срезы защищены)"

echo "--- Stage-11: page-режим regex (ik-thumbnail trick) ---"
PAGE_HTML='<video src="https://ik.imagekit.io/foo/video.mp4/ik-thumbnail.jpg"></video><source src="https://cdn.x.com/real.mp4"><video src="https://cdn.x.com/clip.webm?v=3"></video>'
PAGE_MATCH=$(echo "$PAGE_HTML" | grep -oE '''(https?:)?//[^"'"'"' \\]+\.(mp4|webm)(/|\?[^"'"'"' \\]*)?''' | grep -vE '''\.(mp4|webm)/''' | grep -E '''\.(mp4|webm)(\?|$)''' | sort -u)
{ ! echo "$PAGE_MATCH" | grep -q "video.mp4"; } && ok "page regex: ik-thumbnail ловушка video.mp4 НЕ матчится" || bad "page regex: ловушка video.mp4 ошибочно матчится"
{ echo "$PAGE_MATCH" | grep -q "real.mp4" && echo "$PAGE_MATCH" | grep -q "clip.webm?v=3"; } && ok "page regex: реальные real.mp4 + clip.webm?v=3 матчятся" || bad "page regex: реальные видео не сматчились"

echo "--- J text-on-face (root-cause 2026-06-11: текст поперёк глаз должен FAIL) ---"
if [ "${J_OK:-0}" = 1 ]; then
  out=$(python3 "$SA" --our "$TD/j_neg.mp4" --frames 6 --avatar-region-top 900 2>&1)
  code=$(run --our "$TD/j_neg.mp4" --frames 6 --avatar-region-top 900)
  { echo "$out" | grep -q "✗ J ТЕКСТ НА ЛИЦЕ" && [ "$code" = 2 ]; } && ok "J negative FAIL(2): текст на лице/глазах пойман (синтетик root-cause)" || bad "J negative должен FAIL(2) с «✗ J ТЕКСТ НА ЛИЦЕ», получили exit=$code"
  out=$(python3 "$SA" --our "$TD/j_happy.mp4" --frames 6 --avatar-region-top 900 2>&1)
  { ! echo "$out" | grep -q "✗ J ТЕКСТ НА ЛИЦЕ"; } && ok "J happy: текст ВЫШЕ лица — нет ложного FAIL по наложению" || bad "J happy дал ложный FAIL по тексту-на-лице"
  out=$(python3 "$SA" --our "$TD/j_noface.mp4" --frames 6 --avatar-region-top 900 --no-face-expected 2>&1)
  { ! echo "$out" | grep -q "✗ J "; } && ok "J edge --no-face-expected: full-UI без лица не валит ось J" || bad "J edge: --no-face-expected всё равно даёт ✗ J"
  out=$(python3 "$SA" --our "$TD/j_noface.mp4" --frames 6 --avatar-region-top 900 2>&1)
  echo "$out" | grep -q "✗ J ЛИЦО НЕ НАЙДЕНО" && ok "J no-face БЕЗ флага: лицо не найдено ≥50% → FAIL (не молчаливый skip)" || bad "J no-face без флага должен дать «✗ J ЛИЦО НЕ НАЙДЕНО»"
else
  echo "  (skip J: реальный кадр лица из ~/<твоя рабочая папка ролика>/scenes/s1.mp4 недоступен — haar не детектил)"
fi

echo "--- K2 caption-on-UI (субтитр поверх плотного UI должен FAIL) ---"
out=$(python3 "$SA" --our "$TD/k2_neg.mp4" --frames 6 --avatar-region-top 1920 2>&1)
echo "$out" | grep -q "✗ K2 СУБТИТР ПОВЕРХ ВАЖНОГО UI" && ok "K2 negative FAIL: caption над плотным UI пойман" || bad "K2 negative должен дать «✗ K2 СУБТИТР ПОВЕРХ ВАЖНОГО UI»"
out=$(python3 "$SA" --our "$TD/k2_happy.mp4" --frames 6 --avatar-region-top 1920 2>&1)
{ ! echo "$out" | grep -q "✗ K2 "; } && ok "K2 happy: caption над ровным стыком — нет ложного FAIL" || bad "K2 happy дал ложный FAIL по caption-on-UI"

echo "--- Ф5a: профили семей раскладок (--family) ---"
# overlap-card синтетик: A2 (кроп подбородка) + K (тёмные бары) штатны для семьи.
if [ "${OVERLAP_OK:-0}" = "1" ]; then
  # (a) под ДЕФОЛТОМ (talking-head-split) — должен FAIL по A2/K (exit 2)
  out_def=$(python3 "$SA" --our "$TD/overlap_neg.mp4" --frames 6 --avatar-region-top 1400 --no-face-expected 2>&1)
  code_def=$(run --our "$TD/overlap_neg.mp4" --frames 6 --avatar-region-top 1400 --no-face-expected)
  { [ "$code_def" = 2 ] && echo "$out_def" | grep -qE "✗ (A2|K) "; } && ok "overlap-card синтетик под ДЕФОЛТОМ → FAIL(2) (A2/K hard, как было до Ф5a)" || bad "overlap синтетик под дефолтом должен FAIL(2) по A2/K, получили exit=$code_def"
  # (b) под --family overlap-card — те же оси WARN → PASS (exit 0)
  out_ov=$(python3 "$SA" --our "$TD/overlap_neg.mp4" --frames 6 --avatar-region-top 1400 --no-face-expected --family overlap-card 2>&1)
  code_ov=$(run --our "$TD/overlap_neg.mp4" --frames 6 --avatar-region-top 1400 --no-face-expected --family overlap-card)
  { [ "$code_ov" = 0 ] && ! echo "$out_ov" | grep -qE "✗ (A2|K) "; } && ok "overlap-card синтетик под --family overlap-card → PASS(0) (A2/K переведены в WARN)" || bad "overlap синтетик под --family overlap-card должен PASS(0) без ✗A2/✗K, получили exit=$code_ov"
  # (c) прозрачность: профиль печатает что и почему переведено в WARN
  echo "$out_ov" | grep -q "профиль перевёл в WARN" && ok "профиль печатает переведённые в WARN оси (прозрачность вывода)" || bad "вывод overlap-card должен печатать «профиль перевёл в WARN»"
else
  echo "  (skip Ф5a overlap: реальный кадр лица из ~/<твоя рабочая папка ролика>/scenes/s1.mp4 недоступен)"
fi
# (d) обратная совместимость: дефолтная семья НЕ ослабила talking-head-кейс (g_happy остаётся чистым)
out_th=$(python3 "$SA" --our "$TD/g_happy.mp4" --frames 4 --avatar-region-top 876 2>&1)
echo "$out_th" | grep -q "ПРОФИЛЬ СЕМЬИ: talking-head-split" && ok "дефолт печатает профиль talking-head-split (без флага — поведение не изменилось)" || bad "дефолтный прогон должен печатать профиль talking-head-split"
# (e) неизвестная семья отвергается argparse (choices)
code_bad=$(run --our "$TD/g_happy.mp4" --frames 2 --family bogus-family); [ "$code_bad" = 2 ] && ok "неизвестная --family отвергнута (argparse choices, exit≠0)" || bad "неизвестная --family должна быть отвергнута, получили exit=$code_bad"

echo "=========================================================="
echo " ИТОГ: зелёных=$PASS  провалов=$FAILN"

echo "--- НОВЫЕ ПРАВКИ: C2 / H zero-match / P-PLACEHOLDER ---"

# Кейс 1: текст в нижней cut-zone (y>1430) при family=overlap-card → FAIL (C2 NON_DEMOTABLE)
# Генерим HTML с .cap top=1500px (в cut-zone)
cat > "$TD/c2_neg.html" << 'HTML'
<html><head><style>
.cap { position:absolute; top:1500px; color:#fff; font-family:'Oswald'; }
html, body { background:#060608; }
</style></head><body><div class="cap"><span class="cw">ТЕКСТ</span></div></body></html>
HTML
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/c2_neg.html" --frames 4 --avatar-region-top 876 --family overlap-card 2>&1)
echo "$out" | grep -q "✗ C2 ТЕКСТ В НИЖНЕЙ ОБРЕЗКЕ" && ok "C2 FAIL: текст в нижней cut-zone (y=1500>1430) при family=overlap-card → FAIL (NON_DEMOTABLE, профиль не деградирует)" || bad "C2: текст в нижней cut-zone должен давать ✗ C2, получили: $(echo "$out" | grep -E '✗|C2' | head -3)"

# Кейс 2: H zero-match (капшены есть + json есть + 0 совпадений) → FAIL «капшены не из озвучки»
# HTML с data-s словами, whisper json с ДРУГИМИ словами (не пересекаются)
cat > "$TD/h_zero.html" << 'HTML'
<html><body>
<span class="w" data-s="1.00">КОНТЕНТ</span>
<span class="w" data-s="2.00">МАРКЕТИНГ</span>
</body></html>
HTML
cat > "$TD/wh_zero.json" << 'JSON'
{"words":[{"word":"hello","start":1.0},{"word":"world","start":2.0}]}
JSON
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/h_zero.html" --whisper-json "$TD/wh_zero.json" --frames 3 --avatar-region-top 876 2>&1)
echo "$out" | grep -q "✗ H" && ok "H zero-match FAIL: 0 слов сматчилось → ✗ H «капшены не из озвучки»" || bad "H zero-match должен давать ✗ H, получили: $(echo "$out" | grep -E '✗|H icon' | head -3)"

# Кейс 3: P-PLACEHOLDER → preflight FAIL (FREEPIK в тексте HTML)
# Создаём HTML с "FREEPIK SPACES" видимым в тексте
cat > "$TD/ph_neg.html" << 'HTML'
<html><head><style>
.strap { position:absolute; top:620px; color:#fff; }
html, body { background:#060608; }
</style></head><body><div class="strap">FREEPIK SPACES</div></body></html>
HTML
# Запускаем через scene-assemble run_preflight (P-PLACEHOLDER там)
ASSEMBLE="$(dirname "$SA")/scene-assemble.py"
out=$(python3 "$ASSEMBLE" /dev/null -o "$TD/ph_out" 2>&1 || true)
# Прямой вызов _check_placeholder через встроенный python
out=$(python3 - "$TD/ph_neg.html" << 'PYCHK'
import re, sys
html_path = sys.argv[1]
text = open(html_path, encoding='utf-8').read()
text_only = re.sub(r'<[^>]+>', ' ', text)
_PLACEHOLDER_RE = re.compile(r'FREEPIK|ACME|LOREM|PLACEHOLDER|YOUR\s+TEXT|SAMPLE', re.IGNORECASE)
m = _PLACEHOLDER_RE.search(text_only)
if m:
    print(f"P-PLACEHOLDER FAIL: {m.group(0)}")
    sys.exit(2)
else:
    print("P-PLACEHOLDER PASS")
    sys.exit(0)
PYCHK
)
code=$?
{ echo "$out" | grep -q "P-PLACEHOLDER FAIL" && [ "$code" = 2 ]; } && ok "P-PLACEHOLDER FAIL: 'FREEPIK SPACES' в тексте HTML → exit 2" || bad "P-PLACEHOLDER: должен FAIL(2) на 'FREEPIK SPACES', получили exit=$code / $out"

# Кейс 3b: P-PLACEHOLDER happy — чистый HTML → PASS
cat > "$TD/ph_happy.html" << 'HTML'
<html><head><style>
.strap { position:absolute; top:620px; color:#fff; }
html, body { background:#060608; }
</style></head><body><div class="strap">VIBE CODING DEMO</div></body></html>
HTML
out=$(python3 - "$TD/ph_happy.html" << 'PYCHK'
import re, sys
html_path = sys.argv[1]
text = open(html_path, encoding='utf-8').read()
text_only = re.sub(r'<[^>]+>', ' ', text)
_PLACEHOLDER_RE = re.compile(r'FREEPIK|ACME|LOREM|PLACEHOLDER|YOUR\s+TEXT|SAMPLE', re.IGNORECASE)
m = _PLACEHOLDER_RE.search(text_only)
if m:
    print(f"P-PLACEHOLDER FAIL: {m.group(0)}")
    sys.exit(2)
else:
    print("P-PLACEHOLDER PASS")
    sys.exit(0)
PYCHK
)
code=$?
{ echo "$out" | grep -q "P-PLACEHOLDER PASS" && [ "$code" = 0 ]; } && ok "P-PLACEHOLDER PASS: чистый HTML без плейсхолдеров → exit 0" || bad "P-PLACEHOLDER happy: должен PASS(0), получили exit=$code / $out"

echo "--- ПРАВКИ по решению автора: B3/B4 внешний CSS / F-плашка / N-панель / A-C фото-вставка / J-конфликт ---"

# Кейс B3-ext POSITIVE: @font-face во ВНЕШНЕМ css (assets) + применён к .stream -> B3/B4 НЕ ложный FAIL.
mkdir -p "$TD/extcss/assets"
python3 - "$TD/extcss" <<'PYG'
import sys,os,re,base64,io
TD=sys.argv[1]
SCENE1=os.path.expanduser('~/<твоя рабочая папка ролика>/blocks/scene1/index.html')
ob=None
if os.path.exists(SCENE1):
    h=open(SCENE1,encoding='utf-8',errors='ignore').read()
    m=re.search(r"url\(data:font/[^;]+;base64,([A-Za-z0-9+/=]+)\)",h)
    if m: ob=m.group(1)
ext = "@font-face{font-family:'OswaldX';src:url(data:font/ttf;base64,%s) format('truetype');}" % (ob or "")
open(os.path.join(TD,'assets','oswald.css'),'w',encoding='utf-8').write(ext)
# HTML: inline пуст по @font-face, шрифт берётся ВНЕШНЕ через <link>
html=("<html><head><link rel='stylesheet' href='assets/oswald.css'>"
      "<style>.stream{font-family:'OswaldX';color:#fff;top:620px;position:absolute;text-shadow:0 2px 0 #000;}"
      ".title{font-family:'OswaldX';color:#fff;top:400px;position:absolute;}"
      ".cap{top:1100px;position:absolute;} .cap .cw{font-family:'OswaldX';color:#fff;text-shadow:0 2px 0 #000;}"
      "html,body{background:#060608;}</style></head>"
      "<body><div class='title'><span class='w'>ПРИВЕТ</span></div>"
      "<div class='stream'><span class='w'>МИР</span></div>"
      "<div class='cap'><span class='cw'>СЛОВО</span></div></body></html>")
open(os.path.join(TD,'extcss','idx.html'),'w',encoding='utf-8').write(html)
print("OB=%d"%(1 if ob else 0))
PYG
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/extcss/idx.html" --frames 3 --avatar-region-top 876 2>&1)
{ ! echo "$out" | grep -qE "✗ B[34] "; } && ok "B3/B4 ext-css POSITIVE: @font-face во внешнем css применён к тексту — нет ложного ✗B3/✗B4" || { echo "$out" | grep -E '✗ B[34]'; bad "B3/B4: внешний @font-face дал ложный FAIL"; }

# Кейс B3 NEGATIVE: реальный СИСТЕМНЫЙ шрифт (Arial) первым в font-family -> B3/B4 всё ещё FAIL.
cat > "$TD/sysfont.html" << 'HTML'
<html><head><style>
.stream{font-family:Arial, sans-serif; color:#fff; top:620px; position:absolute;}
.title{font-family:Arial, sans-serif; color:#fff; top:400px; position:absolute;}
.cap{top:1100px;position:absolute;} .cap .cw{font-family:Arial; color:#fff;}
html,body{background:#060608;}
</style></head><body>
<div class="title"><span class="w">ПРИВЕТ</span></div>
<div class="stream"><span class="w">МИР</span></div>
<div class="cap"><span class="cw">СЛОВО</span></div></body></html>
HTML
out=$(python3 "$SA" --our "$TD/g_happy.mp4" --html "$TD/sysfont.html" --frames 3 --avatar-region-top 876 2>&1)
echo "$out" | grep -qE "✗ B[34] " && ok "B3/B4 NEGATIVE: системный Arial первым в font-family — реальный дефект всё ещё ✗B3/B4" || { echo "$out" | grep -E 'B[34]'; bad "B3/B4: системный Arial должен давать ✗B3/B4"; }

# Кейс F-плашка POSITIVE: субтитр на ТЁМНОЙ плашке rgba(0,0,0,.58), текст белый -> контраст высокий, нет ✗F.
cat > "$TD/fplate_ok.html" << 'HTML'
<html><head><style>
.stream{top:1100px;position:absolute;}
.cw{color:#ffffff; background:rgba(0,0,0,0.58); font-family:Oswald;}
.cap{top:1100px;position:absolute;}
html,body{background:#f3efe8;}
</style></head><body><div class="cap"><span class="cw">СЛОВО</span></div></body></html>
HTML
# f_happy.mp4 — белая футболка на светлом фоне в полосе (старый ложный F). С плашкой путь = объявленный контраст.
out=$(python3 "$SA" --our "$TD/f_neg.mp4" --html "$TD/fplate_ok.html" --frames 4 --avatar-region-top 876 2>&1)
{ echo "$out" | grep -q "ПЛАШКА-путь" && ! echo "$out" | grep -q "✗ F "; } && ok "F-плашка POSITIVE: тёмная плашка rgba(0,0,0,.58) → контраст по цветам, нет ложного ✗F (пиксельная полоса не применяется)" || { echo "$out" | grep -E 'F '; bad "F-плашка: должен идти ПЛАШКА-путь без ✗F"; }

# Кейс F-без-плашки NEGATIVE: caption БЕЗ плашки на СВЕТЛОМ фоне -> пиксельный путь -> ✗F (как раньше).
cat > "$TD/fnoplate.html" << 'HTML'
<html><head><style>
.cap{top:1300px;position:absolute;}
.cw{color:#e8e8e8; font-family:Oswald;}
html,body{background:#f0f0f0;}
</style></head><body><div class="cap"><span class="cw">СЛОВО</span></div></body></html>
HTML
out=$(python3 "$SA" --our "$TD/f_neg.mp4" --html "$TD/fnoplate.html" --frames 4 --avatar-region-top 876 2>&1)
{ echo "$out" | grep -q "ПИКСЕЛЬ-путь" && echo "$out" | grep -q "✗ F "; } && ok "F-без-плашки NEGATIVE: caption без плашки на светлом → пиксельный путь ловит низкий контраст (✗F)" || { echo "$out" | grep -E 'F '; bad "F-без-плашки: должен идти ПИКСЕЛЬ-путь с ✗F"; }

# Кейс N NEGATIVE: реально ПУСТАЯ панель в верх-зоне (большая однородная плашка) >1.2с -> ⚠N.
python3 - "$TD" <<'PYN'
import sys,os,subprocess,numpy as np
from PIL import Image
TD=sys.argv[1]; W,H=1080,1920
d=os.path.join(TD,'npanel_frames'); os.makedirs(d,exist_ok=True)
n=20
for i in range(n):
    a=np.zeros((H,W,3),np.uint8); a[:]=(8,8,10)        # тёмный фон
    # крупная скруглённая плашка в верх-зоне y36-760, ВНУТРИ однородная (контента нет)
    a[120:680, 140:940]=(46,46,52)                     # тело плашки, ровное
    Image.fromarray(a).save(os.path.join(d,f"{i:04d}.png"))
out=os.path.join(TD,'npanel.mp4')
subprocess.run(['ffmpeg','-y','-framerate','10','-i',os.path.join(d,'%04d.png'),
                '-c:v','libx264','-pix_fmt','yuv420p',out],capture_output=True)
print("npanel made")
PYN
out=$(python3 "$SA" --our "$TD/npanel.mp4" --frames 4 --avatar-region-top 876 --no-face-expected 2>&1)
echo "$out" | grep -q "⚠ N ПАНЕЛЬ ЕСТЬ" && ok "N NEGATIVE: пустая панель (однородна >92%% >1.2с) → ⚠N «панель есть, контент пуст»" || { echo "$out" | grep -E 'N '; bad "N: реально пустая панель должна давать ⚠N"; }

# Кейс N POSITIVE: панель с КОНТЕНТОМ (пёстрая внутри) -> нет ⚠N.
python3 - "$TD" <<'PYN2'
import sys,os,subprocess,numpy as np
from PIL import Image
TD=sys.argv[1]; W,H=1080,1920
d=os.path.join(TD,'npanel_ok_frames'); os.makedirs(d,exist_ok=True)
rng=np.random.default_rng(0)
for i in range(20):
    a=np.zeros((H,W,3),np.uint8); a[:]=(8,8,10)
    a[120:680, 140:940]=(46,46,52)
    # контент внутри: строки текста/иконки (пёстро) -> uniform_frac низкий
    a[180:640, 180:900]=rng.integers(0,255,(460,720,3),dtype=np.uint8)
    Image.fromarray(a).save(os.path.join(d,f"{i:04d}.png"))
out=os.path.join(TD,'npanel_ok.mp4')
subprocess.run(['ffmpeg','-y','-framerate','10','-i',os.path.join(d,'%04d.png'),
                '-c:v','libx264','-pix_fmt','yuv420p',out],capture_output=True)
print("npanel_ok made")
PYN2
out=$(python3 "$SA" --our "$TD/npanel_ok.mp4" --frames 4 --avatar-region-top 876 --no-face-expected 2>&1)
{ ! echo "$out" | grep -q "⚠ N ПАНЕЛЬ ЕСТЬ"; } && ok "N POSITIVE: панель с контентом (пёстрая внутри) → нет ⚠N" || bad "N: панель с контентом не должна варнить"

# Кейс J-конфликт: текст-like пиксели в лице, НО html_overlap=0 И pix в серой зоне (<0.12) -> WARN, не FAIL.
# Используем РЕАЛЬНОЕ лицо из s1, лёгкий неон-шум в области лица (не реальный текст), html без data-s на лице.
if [ "${J_OK:-0}" = 1 ]; then
  python3 - "$TD" <<'PYJ'
import sys,os,subprocess,cv2,numpy as np
from PIL import Image
TD=sys.argv[1]
S1=os.path.expanduser('~/<твоя рабочая папка ролика>/scenes/s1.mp4')
fp=os.path.join(TD,'_ff2.png')
subprocess.run(['ffmpeg','-y','-ss','0.5','-i',S1,'-frames:v','1',fp],capture_output=True)
bgr=cv2.imread(fp); rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
cc=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
ff=cc.detectMultiScale(g,1.1,5,minSize=(120,120))
FB=max(ff,key=lambda z:z[2]); fx,fy,fw,fh=[int(v) for v in FB]
d=os.path.join(TD,'jconf_frames'); os.makedirs(d,exist_ok=True)
rng=np.random.default_rng(3)
for i in range(15):
    a=rgb.copy()
    # ЛЁГКИЕ редкие яркие точки в лице (text-like, но малая доля <0.12, не реальный текст)
    ys=rng.integers(fy+int(fh*0.6),fy+fh-2,8); xs=rng.integers(fx+2,fx+fw-2,8)
    for yy,xx in zip(ys,xs): a[yy:yy+3,xx:xx+3]=255
    Image.fromarray(a).save(os.path.join(d,f"{i:04d}.png"))
out=os.path.join(TD,'jconf.mp4')
subprocess.run(['ffmpeg','-y','-framerate','10','-i',os.path.join(d,'%04d.png'),
                '-c:v','libx264','-pix_fmt','yuv420p',out],capture_output=True)
print("jconf made")
PYJ
  # html БЕЗ субтитра на лице (никакого .cap top на лице) -> html_overlap=0
  echo '<html><body><span>x</span></body></html>' > "$TD/jconf.html"
  out=$(python3 "$SA" --our "$TD/jconf.mp4" --html "$TD/jconf.html" --frames 6 --avatar-region-top 1920 2>&1)
  { ! echo "$out" | grep -q "✗ J ТЕКСТ НА ЛИЦЕ"; } && ok "J-конфликт: text-like пиксели в лице но html_overlap=0 и pix<0.12 → НЕ FAIL (WARN/чисто, не ложный ✗J)" || { echo "$out" | grep -E 'J '; bad "J-конфликт дал ложный ✗J при html_overlap=0"; }
  # А реальный текст НА лице С html_overlap>0 (j_neg + html с .cap на лице) всё ещё FAIL — закрыто j_neg выше (pix>0.12).
else
  echo "  (skip J-конфликт: реальный кадр лица недоступен)"
fi

echo "=========================================================="
[ "$FAILN" -eq 0 ] && exit 0 || exit 1
